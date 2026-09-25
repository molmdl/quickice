"""E2E CLI ion-branch export regression: 0-ion orphan ``ion.itp`` include.

Bug (a) from the 48.3-25 exit audit (.planning/STATE.md "Status"): a CLI
export after an ion step that inserted 0 ions (na_count == cl_count == 0,
e.g. a tiny concentration that rounds to 0 ion pairs) still writes
``#include "ion.itp"`` into ion.top and stages ion.itp. The NA/CL
``[atomtypes]`` block in ion.top is gated on the counts
(ion_writer.py:824) while the ``#include`` is NOT (ion_writer.py:951), and
ion.itp's ``[atoms]`` reference atomtypes NA/CL -> ``gmx grompp`` fatal:
``ERROR 1 [file ion.itp, line 8]: Atomtype NA not found``.

Fix (quick task 029, Task 1): skip the ``#include "ion.itp"`` in
``write_ion_top_file`` AND skip ion.itp staging in the
``copy_itp_files_for_structure`` ion branch when na_count == cl_count == 0.
Ion-present exports are byte-identical to before (ion.itp still staged +
included, grompp rc==0).

RED-first: ``test_zero_ion_export_has_no_orphan_ion_include`` FAILS before
the fix at the grompp assert (rc=1, "Atomtype NA not found" — live-verified
2026-09-25); ``test_ion_present_export_keeps_ion_include`` PASSES before
AND after the fix (regression guard for real ion users).

Fixture mirrors the real CLI pipeline (pipeline.py:838-846): liquid volume
is derived from water_nmolecules x WATER_VOLUME_NM3 (insert_ions' None
default), exactly like the pipeline does. 0.001 M rounds to 0 ion pairs
(live-verified: 2587 waters -> n ~ 0.046 -> 0); the sanity assert on
na_count/cl_count == 0 catches any repro-precondition drift. 0.5 M inserts
real ions for the regression guard.

CLI surface: ``CLIPipeline(args=SimpleNamespace())`` with only
``_ion_result`` set -> export priority (ion > solute > custom > interface >
hydrate > ice) picks the ION branch (write_ion_gro_file /
write_ion_top_file + copy_itp_files_for_structure ion branch). NO
PySide6/VTK/GenIce2 top-level imports (lazy-import rule AGENTS.md); GenIce2
is lazy-imported inside HydrateStructureGenerator method bodies.

Module-scoped fixture amortizes the GenIce2 + interface + ion-insertion
calls (per AGENTS.md testing guidance). ``gmx`` is on PATH so grompp runs
(``@gmx_skipif`` skips when absent).
"""

import shutil
from types import SimpleNamespace

import pytest

from quickice.cli.pipeline import CLIPipeline
from quickice.structure_generation.hydrate_generator import (
    HydrateStructureGenerator,
)
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.types import HydrateConfig, InterfaceConfig
from quickice.structure_generation.water_filler import get_cell_extent
from quickice.structure_generation.ion_inserter import insert_ions

from tests.conftest import gmx_skipif
from tests.e2e_export_helpers import (
    MDP_PATH,
    run_gmx_grompp,
    parse_top_molecules,
    assert_itp_completeness,
    assert_gro_top_consistent,
)


def _slab_config(candidate):
    """Slab InterfaceConfig from the hydrate candidate cell (mixed_ion pattern)."""
    cell_ext = get_cell_extent(candidate.cell)
    box_x = max(cell_ext[0] * 2, 4.0)
    box_y = max(cell_ext[1] * 2, 4.0)
    ice_thickness = max(cell_ext[2], 2.0)
    water_thickness = 3.0
    box_z = 2 * ice_thickness + water_thickness
    return InterfaceConfig(
        mode="slab", box_x=box_x, box_y=box_y, box_z=box_z,
        seed=42, ice_thickness=ice_thickness, water_thickness=water_thickness,
    )


@pytest.fixture(scope="module")
def zero_ion_export(tmp_path_factory):
    """Build sI-hydrate -> slab -> 0-ion -> CLI export through the ion branch.

    sI ch4 1x1x1 hydrate -> to_candidate() -> slab interface -> insert_ions
    at 0.001 M with liquid_volume=None (the inserter derives volume from
    water_nmolecules x WATER_VOLUME_NM3, exactly mirroring
    pipeline.py:838-846) -> rounds to 0 ion pairs. Then the REAL CLI export
    surface (CLIPipeline._run_export_step with only _ion_result set) writes
    ion.gro/ion.top + stages ITPs.
    """
    hydrate = HydrateStructureGenerator().generate(
        HydrateConfig(
            lattice_type="sI", guest_type="ch4",
            supercell_x=1, supercell_y=1, supercell_z=1,
        )
    )
    candidate = hydrate.to_candidate()
    iface = generate_interface(candidate, _slab_config(candidate))

    # 0.001 M + real volume estimate (None) -> 0 ion pairs (live-verified:
    # 2587 waters -> n ~ 0.046 -> 0). insert_ions sets iface.molecule_index
    # on first call (duck-typing, CP-01); the second call below is safe
    # (verified idempotent path).
    ion0 = insert_ions(iface, 0.001, None, seed=42)
    assert ion0.na_count == 0 and ion0.cl_count == 0, (
        "0-ion repro precondition broken: insert_ions(0.001 M) inserted "
        f"{ion0.na_count} Na+ / {ion0.cl_count} Cl- — expected 0/0. The "
        "repro no longer matches the documented bug (a) cause; STOP and "
        "re-diagnose via /gsd-debug."
    )

    # Second insertion at 0.5 M on the SAME iface for the ion-present
    # regression guard (idempotent path — live-verified inserts >0 ions).
    ion_present = insert_ions(iface, 0.5, None, seed=42)
    assert ion_present.na_count > 0 or ion_present.cl_count > 0, (
        "ion-present regression guard precondition broken: insert_ions(0.5 M) "
        f"inserted {ion_present.na_count} Na+ / {ion_present.cl_count} Cl-"
    )

    ws = tmp_path_factory.mktemp("zero_ion_export")
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = ws
    pipe._ion_result = ion0  # only _ion_result set -> priority picks the ion branch
    rc = pipe._run_export_step()
    assert rc == 0, f"_run_export_step (ion branch, 0 ions) returned rc={rc}"

    return {"ws": ws, "ion0": ion0, "ion_present": ion_present}


@gmx_skipif
def test_zero_ion_export_has_no_orphan_ion_include(zero_ion_export):
    """0-ion CLI export: NO ion.itp staged, NO #include "ion.itp", grompp rc=0.

    BEFORE the fix this fails at the grompp assert with rc=1 and
    ``ERROR 1 [file ion.itp, line 8]: Atomtype NA not found`` — the orphan
    include pulls in ion.itp whose [atoms] reference NA/CL atomtypes that
    the count-gated [atomtypes] block never emitted (live-verified).
    """
    ws = zero_ion_export["ws"]
    gro_path = ws / "ion.gro"
    top_path = ws / "ion.top"

    assert gro_path.exists(), f"ion.gro not written in {ws}"
    assert top_path.exists(), f"ion.top not written in {ws}"

    top_text = top_path.read_text()
    # 1. No orphan include.
    assert '#include "ion.itp"' not in top_text, (
        "0-ion export must NOT #include ion.itp (no NA/CL atomtypes emitted)"
    )
    # 2. No ion.itp staged.
    assert not (ws / "ion.itp").exists(), (
        "0-ion export must NOT stage ion.itp in the export dir"
    )
    # 3. No NA/CL in [molecules].
    mols = parse_top_molecules(str(top_path))
    assert "NA" not in mols, f"NA in [molecules] for a 0-ion export: {mols}"
    assert "CL" not in mols, f"CL in [molecules] for a 0-ion export: {mols}"
    # 4. File consistency.
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))
    # 5. grompp rc==0 (the live-verified failure signature before the fix).
    shutil.copy(MDP_PATH, ws / "em.mdp")
    rc, stderr = run_gmx_grompp(ws, gro_file="ion.gro", top_file="ion.top")
    assert rc == 0, f"gmx grompp failed for 0-ion export:\n{stderr[-1000:]}"


@gmx_skipif
def test_ion_present_export_keeps_ion_include(zero_ion_export, tmp_path):
    """Ion-present CLI export UNCHANGED by the fix: ion.itp staged +
    included, NA/CL in [molecules] with matching counts, grompp rc==0.

    Regression guard for real ion users — the skip-when-empty gate must be
    strictly conditional on na_count == cl_count == 0 (byte-identical output
    when ions are present except the include blank-line split, which the
    explicit ``f.write("\\n")`` preserves).
    """
    ion_present = zero_ion_export["ion_present"]
    ws = tmp_path

    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = ws
    pipe._ion_result = ion_present
    rc = pipe._run_export_step()
    assert rc == 0, f"_run_export_step (ion branch, ions present) rc={rc}"

    gro_path = ws / "ion.gro"
    top_path = ws / "ion.top"
    assert gro_path.exists() and top_path.exists(), (
        f"ion export files missing in {ws}"
    )

    top_text = top_path.read_text()
    assert '#include "ion.itp"' in top_text, (
        "ion-present export lost its #include \"ion.itp\""
    )
    assert (ws / "ion.itp").exists(), (
        "ion-present export lost its staged ion.itp"
    )
    mols = parse_top_molecules(str(top_path))
    assert mols.get("NA") == ion_present.na_count, (
        f"NA count {mols.get('NA')} != inserted {ion_present.na_count}: {mols}"
    )
    assert mols.get("CL") == ion_present.cl_count, (
        f"CL count {mols.get('CL')} != inserted {ion_present.cl_count}: {mols}"
    )

    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))
    shutil.copy(MDP_PATH, ws / "em.mdp")
    rc, stderr = run_gmx_grompp(ws, gro_file="ion.gro", top_file="ion.top")
    assert rc == 0, f"gmx grompp failed for ion-present export:\n{stderr[-1000:]}"
