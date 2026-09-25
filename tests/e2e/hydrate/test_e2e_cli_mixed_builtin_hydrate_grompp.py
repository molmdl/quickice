"""E2E CLI hydrate-branch export regression: mixed built-in guests mislabeled.

Bug (b) from the 48.3-25 exit audit (.planning/STATE.md "Status"): the CLI
hydrate branch (pipeline.py:924-969) wraps the HydrateStructure in an
InterfaceStructure but never threads ``guest_descriptors`` /
``guest_atom_counts``, so ``write_interface_gro_file`` /
``write_interface_top_file`` fall to the single-stream
``detect_guest_type_from_atoms`` path and ALL guests collapse to CH4_H. The
writers ALREADY have correct mixed-built-in paths (interface_writer.py
GRO/TOP mixed_builtin gates — added by the 48.3-05/45-15 line of fixes);
they were just never activated on this path. Live-verified before the fix:
mixed sII (CH4 small + THF large) exports ``[molecules] = SOL 1088 /
CH4_H 192`` and stages only ch4_hydrate.itp.

Fix (quick task 029, Task 2): thread the metadata into the existing path
(pipeline.py hydrate-branch wrapper gains ``guest_descriptors`` +
``guest_atom_counts=_derive_guest_atom_counts(...)`` kwargs — the 44.1-02
..07 precedent) and stage every distinct built-in guest ITP
(``_detect_builtin_guest_types``, the 48.3-05 config-driven staging
precedent). Do NOT reroute through the multi-molecule writers — the
minimal threading fix was live-verified to grompp rc=0.

RED-first: ``test_cli_mixed_builtin_hydrate_export_grompp`` FAILS before
the fix at assertion 1 (THF_H missing from the .gro residues — all 192
guests labeled CH4_H; only ch4_hydrate.itp staged — live-verified
2026-09-25). After the fix: ``[molecules] = SOL 1088 / CH4_H 128 /
THF_H 64``, both ch4_hydrate.itp + thf_hydrate.itp staged + included,
grompp rc=0.

Box-size pitfall (filled-ice Pitfall 1): sII 1x1x1 has a shortest box
vector of ~1.73 nm < 2*rcoulomb (2.0 nm) — grompp fatal "cut-off length is
longer than half the shortest box vector". 2x2x2 (~3.46 nm) passes
(live-verified). sII cage counts per unit cell: 16 small + 8 large
(42-00 precedent) -> 2x2x2 = 128 CH4 + 64 THF = 192 guests.

Fixture sanity asserts (live-verified empirical values): guest_count == 192;
both ch4 + thf in guest_descriptors; _derive_guest_atom_counts ==
{"ch4": 5, "thf": 13}. If any fails the repro precondition changed — STOP.

CLI surface: ``CLIPipeline(args=SimpleNamespace())`` with only
``_hydrate_result`` set -> export priority picks the HYDRATE branch (the
HydrateStructure -> InterfaceStructure wrapper path). NO PySide6/VTK
imports. Module-scoped fixture amortizes the GenIce2 sII 2x2x2 call
(~0.4s per AGENTS.md). ``gmx`` is on PATH so grompp runs (@gmx_skipif).
"""

import shutil
from types import SimpleNamespace

import pytest

from quickice.cli.pipeline import CLIPipeline
from quickice.structure_generation.hydrate_generator import (
    HydrateStructureGenerator,
)
from quickice.structure_generation.types import (
    CageGuestAssignment,
    HydrateConfig,
    _derive_guest_atom_counts,
)

from tests.conftest import gmx_skipif
from tests.e2e_export_helpers import (
    MDP_PATH,
    run_gmx_grompp,
    parse_top_molecules,
    parse_gro_residue_names,
    assert_itp_completeness,
    assert_gro_top_consistent,
)


@pytest.fixture(scope="module")
def mixed_sii_hydrate():
    """Mixed built-in sII hydrate (CH4 in small cages + THF in large cages).

    2x2x2 supercell (~3.46 nm shortest box vector) required so the grompp
    box check passes (sII 1x1x1 ~1.73 nm < 2*rcoulomb — filled-ice Pitfall
    1). Empirical counts (42-00 precedent): 16 small + 8 large guests per
    unit cell x 8 = 128 CH4 + 64 THF = 192.
    """
    hydrate = HydrateStructureGenerator().generate(
        HydrateConfig(
            lattice_type="sII",
            guest_type="ch4",
            cage_guest_assignments={
                "small": CageGuestAssignment(guest_type="ch4", occupancy=100.0),
                "large": CageGuestAssignment(guest_type="thf", occupancy=100.0),
            },
            supercell_x=2, supercell_y=2, supercell_z=2,
        )
    )
    # Sanity asserts (live-verified empirical values, 42-00 precedent).
    # If any fails, the repro precondition changed — STOP and re-diagnose.
    assert hydrate.guest_count == 192, (
        f"mixed sII 2x2x2 factual guest count changed: {hydrate.guest_count} "
        "(expected 128 CH4 + 64 THF = 192)"
    )
    mol_types = {d.mol_type for d in hydrate.guest_descriptors}
    assert {"ch4", "thf"} <= mol_types, (
        f"guest_descriptors must carry both ch4 + thf, got {mol_types}"
    )
    atom_counts = _derive_guest_atom_counts(
        hydrate.molecule_index, hydrate.guest_descriptors
    )
    assert atom_counts == {"ch4": 5, "thf": 13}, (
        f"_derive_guest_atom_counts changed: {atom_counts} (expected ch4=5, thf=13)"
    )
    return hydrate


@gmx_skipif
def test_cli_mixed_builtin_hydrate_export_grompp(tmp_path, mixed_sii_hydrate):
    """Mixed built-in CLI hydrate export: per-type [molecules] runs matching
    the .gro, BOTH {ch4,thf}_hydrate.itp staged + included, grompp rc==0.

    RED before the fix: assertion 1 fails (all 192 guests collapse to CH4_H
    in the .gro; [molecules] shows CH4_H 192; only ch4_hydrate.itp staged —
    live-verified 2026-09-25).
    """
    ws = tmp_path
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = ws
    pipe._hydrate_result = mixed_sii_hydrate  # carries .config for ITP staging
    # Only _hydrate_result set -> export priority picks the hydrate branch.
    rc = pipe._run_export_step()
    assert rc == 0, f"_run_export_step (hydrate branch, mixed sII) rc={rc}"

    gro_path = ws / "hydrate.gro"
    top_path = ws / "hydrate.top"
    assert gro_path.exists(), f"hydrate.gro not written in {ws}"
    assert top_path.exists(), f"hydrate.top not written in {ws}"

    # 1. .gro residues contain BOTH CH4_H and THF_H (fails first today —
    #    all 192 guests labeled CH4_H).
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert "CH4_H" in gro_res, f"CH4_H missing from .gro residues: {gro_res}"
    assert "THF_H" in gro_res, (
        f"THF_H missing from .gro residues (all guests collapsed to CH4_H — "
        f"the bug (b) signature): {gro_res}"
    )

    # 2. [molecules] per-type counts match the .gro (128 CH4 + 64 THF,
    #    empirical sII 2x2x2: 16 small + 8 large per cell x 8 cells).
    mols = parse_top_molecules(str(top_path))
    assert mols.get("CH4_H") == 128, (
        f"[molecules] CH4_H count {mols.get('CH4_H')} != 128: {mols}"
    )
    assert mols.get("THF_H") == 64, (
        f"[molecules] THF_H count {mols.get('THF_H')} != 64: {mols}"
    )

    # 3. Both guest ITPs staged (thf_hydrate.itp missing today).
    assert (ws / "ch4_hydrate.itp").exists(), (
        f"ch4_hydrate.itp not staged in {ws}"
    )
    assert (ws / "thf_hydrate.itp").exists(), (
        f"thf_hydrate.itp not staged in {ws}"
    )

    # 4. hydrate.top #includes BOTH guest ITPs.
    top_text = top_path.read_text()
    assert '#include "ch4_hydrate.itp"' in top_text, (
        "hydrate.top missing #include for ch4_hydrate.itp"
    )
    assert '#include "thf_hydrate.itp"' in top_text, (
        "hydrate.top missing #include for thf_hydrate.itp"
    )

    # 5. File consistency.
    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # 6. grompp rc==0.
    shutil.copy(MDP_PATH, ws / "em.mdp")
    rc, stderr = run_gmx_grompp(ws, gro_file="hydrate.gro", top_file="hydrate.top")
    assert rc == 0, (
        f"gmx grompp failed for mixed built-in CLI hydrate export:\n"
        f"{stderr[-1000:]}"
    )
