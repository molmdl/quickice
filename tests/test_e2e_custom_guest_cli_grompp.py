"""End-to-end GROMACS grompp validation for the CLI custom-guest hydrate path.

Proves EXPORT-06 (CLI half) for plan 41-11: ``gmx grompp`` exits 0 on a
custom ethanol guest hydrate exported via the CLI interface writers
(``write_interface_gro_file`` + ``write_interface_top_file`` with
``custom_guest_info``), with the custom ITP staged via the transformed-staging
helper ``_stage_custom_guest_itp`` (plan 41-09).

The writers (fixed by plans 41-04 / 41-05) emit:
  - ``.gro`` with ``MOL_H`` residues for the 9-atom ethanol guest
    (chunked by the matching ``molecule_index`` entry's ``.count``, NOT the
    ``count_guest_atoms`` heuristic that miscounted ethanol as 5 atoms — P3 fix)
  - ``.top`` with ``[molecules] MOL_H`` + ``[atomtypes]`` oh/ho merged+deduped
    via ``_merge_custom_atomtypes`` + ``#include "etoh.itp"`` (basename
    preserved by the staging helper)

``_stage_custom_guest_itp`` overwrites the under-transformed etoh.itp
(moleculetype ``etoh``) with the fully-transformed copy (moleculetype
``MOL_H``, ``[atoms]`` resname ``MOL_H``), making the staged ITP internally
consistent with the ``.top [molecules] MOL_H`` entry — the prerequisite for
``gmx grompp`` to succeed.

The GUI half of EXPORT-06 is plan 41-10 (already merged). This test follows
the established repo convention (call writers directly + ``_stage_itp_files``
+ ``_stage_custom_guest_itp`` + ``run_gmx_grompp``) used by
``tests/test_e2e_gmx_validation.py``. ``gmx`` IS on PATH so this test runs
(not skipped).
"""

import sys
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

from tests.conftest import gmx_skipif  # noqa: E402
from quickice.output.gromacs_writer import (  # noqa: E402
    write_interface_gro_file,
    write_interface_top_file,
)
from quickice.structure_generation.types import (  # noqa: E402
    InterfaceStructure,
    MoleculeIndex,
)
from quickice.structure_generation.hydrate_generator import (  # noqa: E402
    HydrateStructureGenerator,
)
from quickice.structure_generation.modes.slab import assemble_slab  # noqa: E402
from quickice.structure_generation.custom_molecule_inserter import (  # noqa: E402
    CustomMoleculeInserter,
)
from quickice.structure_generation.types import (  # noqa: E402
    CustomMoleculeConfig,
    HydrateConfig,
    InterfaceConfig,
)
from quickice.cli.pipeline import CLIPipeline  # noqa: E402
from e2e_export_helpers import (  # noqa: E402
    _stage_itp_files,
    _stage_custom_guest_itp,
    _insert_solutes,
    _insert_ions,
    run_gmx_grompp,
    MDP_PATH,
    ETOH_GRO,
    ETOH_ITP,
    parse_top_molecules,
    parse_gro_residue_names,
    assert_itp_completeness,
    assert_gro_top_consistent,
)


# Module-scope synthetic 2-water + 1-custom-ethanol-guest system (17 atoms).
# Immutable-ish and cheap, so module-scope is fine (matches the convention in
# test_e2e_gmx_validation.py of building fixtures outside the test body).
_ATOM_NAMES = [
    "OW", "HW1", "HW2", "MW",  # water 1
    "OW", "HW1", "HW2", "MW",  # water 2
    "H", "C", "H", "H", "C", "H", "H", "O", "H",  # ethanol (9 atoms)
]
_POSITIONS = np.zeros((17, 3))
_POSITIONS[:, 0] = np.linspace(0.01, 0.17, 17)
# Box must exceed 2*cutoff (rcoulomb=rvdw=1.0 nm in em.mdp). 3.0 nm gives a
# comfortable margin and matches the repo's interface-test box convention.
# Do NOT use 2.0 nm — grompp rejects a box exactly at 2*cutoff with
# "cut-off length longer than half the shortest box vector" (lesson from 41-10).
_CELL = np.eye(3) * 3.0
_MOLECULE_INDEX = [
    MoleculeIndex(0, 4, "water"),
    MoleculeIndex(4, 4, "water"),
    MoleculeIndex(8, 9, "etoh_e2e"),  # custom guest mol_type
]
_IFACE = InterfaceStructure(
    positions=_POSITIONS,
    atom_names=_ATOM_NAMES,
    cell=_CELL,
    ice_atom_count=0,
    water_atom_count=8,
    ice_nmolecules=0,
    water_nmolecules=2,
    mode="hydrate",
    report="test",
    guest_atom_count=9,
    guest_nmolecules=1,
    molecule_index=_MOLECULE_INDEX,
)
_CGI = {
    "mol_type": "etoh_e2e",
    "residue_name": "MOL_H",
    "itp_path": Path("quickice/data/custom/etoh.itp"),
}


# ══════════════════════════════════════════════════════════════════════════════
# CLI custom-guest hydrate grompp (EXPORT-06, CLI half)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
def test_custom_guest_cli_grompp_passes(tmp_path):
    """gmx grompp exits 0 on a custom ethanol guest hydrate exported via the
    CLI interface writers (write_interface_gro_file +
    write_interface_top_file with custom_guest_info).

    Builds a tiny synthetic 2-water + 1-custom-ethanol-guest system IN MEMORY
    (no GenIce2 — fast, deterministic): 8 water atoms + 9 ethanol atoms = 17
    atoms.  Stages tip4p-ice.itp + the transformed etoh.itp (moleculetype
    MOL_H), then runs gmx grompp.
    """
    ws = tmp_path
    gro = ws / "hydrate.gro"
    top = ws / "hydrate.top"
    write_interface_gro_file(_IFACE, str(gro), custom_guest_info=_CGI)
    write_interface_top_file(_IFACE, str(top), custom_guest_info=_CGI)

    # Stage MDP + ITPs (repo convention: writers don't copy ITPs; staging does)
    shutil.copy(MDP_PATH, ws / "em.mdp")
    _stage_itp_files(str(top), ws)  # tip4p-ice.itp + etoh.itp (etoh under-transformed)
    _stage_custom_guest_itp(  # overwrite etoh.itp -> moleculetype MOL_H
        ws, Path("quickice/data/custom/etoh.itp"), "MOL"
    )

    # All #include'd ITPs present in the workspace.
    assert_itp_completeness(str(top), ws)
    # GRO residues <-> TOP [molecules] cross-check.
    assert_gro_top_consistent(str(gro), str(top))

    # Run gmx grompp — must exit 0 (topology is self-consistent + simulation-ready).
    exit_code, stderr = run_gmx_grompp(
        ws, gro_file="hydrate.gro", top_file="hydrate.top"
    )
    assert exit_code == 0, f"gmx grompp failed (CLI custom guest):\n{stderr}"

    # .top [molecules] lists SOL + MOL_H.
    mols = parse_top_molecules(str(top))
    assert "SOL" in mols and "MOL_H" in mols, (
        f"expected SOL + MOL_H in [molecules], got {mols}"
    )

    # .gro residues contain SOL + MOL_H.
    gro_res = set(parse_gro_residue_names(str(gro)))
    assert "SOL" in gro_res and "MOL_H" in gro_res, (
        f"expected SOL + MOL_H in .gro residues, got {gro_res}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# CLI custom-guest through each export branch (44.1-17)
# ══════════════════════════════════════════════════════════════════════════════
# These four tests exercise ``CLIPipeline._run_export_step`` (NOT the writers
# directly) for a custom ethanol cage guest through the interface / custom /
# solute / ion export branches. They prove the plan 44.1-17 wiring:
#   - Task 1: ``_run_export_step`` builds ``cgi`` from ``self._hydrate_result
#     .config`` and threads ``custom_guest_info=cgi`` to the 4 writer branches.
#   - Task 2: ``copy_itp_files_for_structure(..., hydrate_config=...)`` stages
#     the transformed custom ``etoh.itp`` (moleculetype ``MOL_H``) for those 4
#     branches via the reused ``copy_custom_guest_itp``.
#
# Each test constructs a REAL custom ethanol hydrate (sI 1x1x1, fast) via
# ``HydrateStructureGenerator`` -> ``assemble_slab`` -> (per-branch inserter),
# plugs the downstream structure into a ``CLIPipeline`` with
# ``_hydrate_result`` set (so ``.config`` is available), calls
# ``_run_export_step`` directly (the export-step-direct approach the plan
# allows), then stages the MDP + runs file-consistency assertions + gmx
# grompp. This directly validates the CLI threading + ITP staging, distinct
# from the GUI exporter tests (44.1-09/11/13/15) which test the GUI exporters.


@pytest.fixture(scope="module")
def _custom_ethanol_hydrate_and_iface():
    """Module-scope fixture: a REAL custom ethanol hydrate (sI 1x1x1) + its
    slab InterfaceStructure.

    Built ONCE and shared across the 4 branch tests (inserters return NEW
    structures and never mutate the input iface, V-17). Amortizes the GenIce2
    cost (~1s) across 4 tests. Returns ``(hydrate, iface, config)`` where
    ``hydrate`` carries ``.config`` (the HydrateConfig the CLI reads via
    ``self._hydrate_result.config``).

    Uses ABSOLUTE ``guest_gro_path``/``guest_itp_path`` (via ETOH_GRO/ETOH_ITP)
    so the ITP staging is CWD-independent, matching the convention in
    ``tests/test_cli/test_pipeline_custom_guest_export.py``.
    """
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="etoh_e2e",
        guest_residue_name="MOL",
        guest_gro_path=str(ETOH_GRO),
        guest_itp_path=str(ETOH_ITP),
        guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
        guest_atom_count=9,
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    hydrate = gen.generate(config)
    candidate = hydrate.to_candidate()
    iface = assemble_slab(
        candidate,
        InterfaceConfig(
            mode="slab",
            box_x=3.0,
            box_y=3.0,
            box_z=8.0,
            seed=42,
            ice_thickness=2.0,
            water_thickness=4.0,
        ),
    )
    # Custom ethanol (9 atoms/mol) must be threaded correctly through slab
    # mode (44.1-05): guest_atom_count == 9 * guest_nmolecules.
    assert iface.guest_nmolecules > 0, "custom ethanol slab should have guests"
    assert iface.guest_atom_count == 9 * iface.guest_nmolecules, (
        f"custom ethanol slab guest_atom_count={iface.guest_atom_count} != "
        f"9 * guest_nmolecules={9 * iface.guest_nmolecules}"
    )
    return hydrate, iface, config


def _make_cli_pipeline(tmp_path, hydrate, downstream_attr, downstream_struct):
    """Construct a ``CLIPipeline`` with ``_hydrate_result``=hydrate (carries
    ``.config``) and the downstream structure set on ``_<downstream_attr>_result``
    so the ``_run_export_step`` priority selection picks that branch.

    All other ``_*_result`` stay at their ``__init__`` default of ``None``.
    """
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = tmp_path
    pipe._hydrate_result = hydrate
    setattr(pipe, downstream_attr, downstream_struct)
    return pipe


@gmx_skipif
def test_custom_guest_cli_interface_export_grompp(
    tmp_path, _custom_ethanol_hydrate_and_iface
):
    """gmx grompp exits 0 on a custom ethanol guest hydrate exported via the
    CLI ``_run_export_step`` interface branch (plan 44.1-17, Task 1+2).

    The CLI interface branch (pipeline.py) threads ``custom_guest_info=cgi``
    (built from ``self._hydrate_result.config``) to ``write_interface_gro_file``
    / ``write_interface_top_file``, and ``copy_itp_files_for_structure`` stages
    the transformed ``etoh.itp`` (moleculetype ``MOL_H``) via the new
    custom-guest block. The previous broken path (no ``custom_guest_info``
    threading; ``_detect_guest_type`` -> None for custom -> no custom ITP
    staged) would fail at grompp with ``File not found: 'etoh.itp'`` and a
    ``GUE`` moleculetype no ITP defines.
    """
    hydrate, iface, _config = _custom_ethanol_hydrate_and_iface

    pipe = _make_cli_pipeline(tmp_path, hydrate, "_interface_result", iface)
    code = pipe._run_export_step()
    assert code == 0, "_run_export_step should succeed for the interface branch"

    gro = tmp_path / "interface.gro"
    top = tmp_path / "interface.top"
    assert gro.exists(), f"interface.gro not written: {gro}"
    assert top.exists(), f"interface.top not written: {top}"
    assert (tmp_path / "tip4p-ice.itp").exists(), "tip4p-ice.itp not staged"
    assert (tmp_path / "etoh.itp").exists(), (
        "custom guest etoh.itp not staged by copy_itp_files_for_structure"
    )
    # The staged etoh.itp must be the TRANSFORMED copy (moleculetype MOL_H).
    staged_etoh = (tmp_path / "etoh.itp").read_text()
    assert "MOL_H" in staged_etoh, (
        "staged etoh.itp missing MOL_H moleculetype -- copy_custom_guest_itp "
        "was not applied by the custom-guest staging block"
    )

    # Stage MDP + file-consistency assertions (always run).
    shutil.copy(MDP_PATH, tmp_path / "em.mdp")
    assert_itp_completeness(str(top), tmp_path)
    assert_gro_top_consistent(str(gro), str(top))

    # gmx grompp -> rc == 0 (topology self-consistent + simulation-ready).
    exit_code, stderr = run_gmx_grompp(
        tmp_path, gro_file="interface.gro", top_file="interface.top"
    )
    assert exit_code == 0, (
        f"gmx grompp failed (CLI interface custom guest):\n{stderr}"
    )

    mols = parse_top_molecules(str(top))
    assert "SOL" in mols and "MOL_H" in mols, (
        f"expected SOL + MOL_H in [molecules], got {mols}"
    )
    assert "GUE" not in mols, (
        f"GUE must NOT appear in [molecules] (custom_guest_info not threaded): "
        f"{mols}"
    )
    gro_res = set(parse_gro_residue_names(str(gro)))
    assert "SOL" in gro_res and "MOL_H" in gro_res, (
        f"expected SOL + MOL_H in .gro residues, got {gro_res}"
    )
    assert "GUE" not in gro_res, (
        f"GUE must NOT appear in .gro residues (custom_guest_info not threaded): "
        f"{gro_res}"
    )


@gmx_skipif
def test_custom_guest_cli_custom_molecule_export_grompp(
    tmp_path, _custom_ethanol_hydrate_and_iface
):
    """gmx grompp exits 0 on a custom ethanol guest hydrate exported via the
    CLI ``_run_export_step`` custom-molecule branch (plan 44.1-17, Task 1+2).

    Mirrors the GUI ``CustomMoleculeGROMACSExporter`` test (44.1-13) but
    exercises the CLI custom branch. A custom-molecule export has TWO kinds of
    "custom" molecules: (1) the hydrate CAGE GUEST (ethanol in cages) staged
    as ``etoh.itp`` (moleculetype ``MOL_H``) via the custom-guest block, and
    (2) the USER-PROVIDED custom molecule inserted via
    ``CustomMoleculeInserter``. Both use the same source ``etoh.itp``/``etoh.gro``
    — to avoid a filename collision (the custom-molecule ITP copy would
    overwrite the transformed cage-guest ITP) and a duplicate ``#include``, the
    custom molecule uses a RENAMED COPY (``cmet.itp``/``cmet.gro``) with the
    ``[ moleculetype ]`` name renamed from ``etoh`` to ``MOL``.
    """
    hydrate, iface, _config = _custom_ethanol_hydrate_and_iface

    # Renamed cmet.gro/cmet.itp so the custom-molecule ITP (cmet.itp) does NOT
    # collide with the cage-guest ITP (etoh.itp, staged as MOL_H). The
    # [moleculetype] name is renamed "etoh" -> "MOL" so the .top [molecules]
    # name ("MOL" from parse_itp_file) matches the .gro residue ("MOL").
    cmet_gro = tmp_path / "cmet.gro"
    cmet_itp = tmp_path / "cmet.itp"
    shutil.copy(ETOH_GRO, cmet_gro)
    cmet_lines = ETOH_ITP.read_text().splitlines(keepends=True)
    _in_moltype = False
    for i, line in enumerate(cmet_lines):
        if "[ moleculetype ]" in line:
            _in_moltype = True
        elif _in_moltype and line.strip() and not line.strip().startswith(";"):
            cmet_lines[i] = line.replace("etoh", "MOL", 1)
            break
    cmet_itp.write_text("".join(cmet_lines))

    cm_config = CustomMoleculeConfig(
        placement_mode="random",
        gro_path=cmet_gro,
        itp_path=cmet_itp,
        molecule_count=1,
    )
    inserter = CustomMoleculeInserter(cm_config, seed=42)
    custom_structure = inserter.place_random(iface, 1)
    assert custom_structure.custom_molecule_count > 0, (
        "custom molecule inserter should place 1 molecule in the water region"
    )
    assert custom_structure.guest_atom_count > 0, (
        "CustomMoleculeStructure.guest_atom_count must be propagated from the "
        "interface for copy_itp_files_for_structure's custom-guest block"
    )

    pipe = _make_cli_pipeline(tmp_path, hydrate, "_custom_result", custom_structure)
    code = pipe._run_export_step()
    assert code == 0, "_run_export_step should succeed for the custom branch"

    gro = tmp_path / "custom.gro"
    top = tmp_path / "custom.top"
    assert gro.exists(), f"custom.gro not written: {gro}"
    assert top.exists(), f"custom.top not written: {top}"
    assert (tmp_path / "tip4p-ice.itp").exists(), "tip4p-ice.itp not staged"
    assert (tmp_path / "etoh.itp").exists(), (
        "cage-guest etoh.itp not staged by the custom-guest block"
    )
    assert (tmp_path / "cmet.itp").exists(), (
        "custom molecule ITP (cmet.itp) not copied by the custom branch"
    )
    staged_etoh = (tmp_path / "etoh.itp").read_text()
    assert "MOL_H" in staged_etoh, (
        "staged etoh.itp missing MOL_H moleculetype -- copy_custom_guest_itp "
        "was not applied by the custom-guest staging block"
    )

    shutil.copy(MDP_PATH, tmp_path / "em.mdp")
    assert_itp_completeness(str(top), tmp_path)
    assert_gro_top_consistent(str(gro), str(top))

    exit_code, stderr = run_gmx_grompp(
        tmp_path, gro_file="custom.gro", top_file="custom.top"
    )
    assert exit_code == 0, (
        f"gmx grompp failed (CLI custom-molecule custom guest):\n{stderr}"
    )

    mols = parse_top_molecules(str(top))
    assert "SOL" in mols and "MOL_H" in mols and "MOL" in mols, (
        f"expected SOL + MOL_H + MOL in [molecules], got {mols}"
    )
    assert "GUE" not in mols, (
        f"GUE must NOT appear in [molecules] (custom_guest_info not threaded): "
        f"{mols}"
    )
    gro_res = set(parse_gro_residue_names(str(gro)))
    assert "SOL" in gro_res and "MOL_H" in gro_res and "MOL" in gro_res, (
        f"expected SOL + MOL_H + MOL in .gro residues, got {gro_res}"
    )
    assert "GUE" not in gro_res, (
        f"GUE must NOT appear in .gro residues (custom_guest_info not threaded): "
        f"{gro_res}"
    )


@gmx_skipif
def test_custom_guest_cli_solute_export_grompp(
    tmp_path, _custom_ethanol_hydrate_and_iface
):
    """gmx grompp exits 0 on a custom ethanol guest hydrate exported via the
    CLI ``_run_export_step`` solute branch (plan 44.1-17, Task 1+2).

    Mirrors the GUI ``SoluteGROMACSExporter`` test (44.1-11) but exercises the
    CLI solute branch (ice+water+guest+CH4 solute). The solute branch threads
    ``custom_guest_info=cgi`` to ``write_solute_gro_file`` /
    ``write_solute_top_file`` (extended in 44.1-11) and stages ``etoh.itp``
    (cage guest, MOL_H) + ``ch4_liquid.itp`` (solute) +
    ``tip4p-ice.itp``. The previous broken path (``write_solute_top_file``
    emitted ``guest_res_name="GUE"`` + no ``#include`` for the custom ITP;
    ``_detect_guest_type`` -> None -> no custom ITP staged) would fail at
    grompp with ``File not found: 'etoh.itp'`` and a ``GUE`` moleculetype.
    """
    hydrate, iface, _config = _custom_ethanol_hydrate_and_iface

    solute_structure = _insert_solutes(iface, solute_type='CH4', concentration=0.3)
    assert solute_structure.n_molecules > 0, (
        "solute inserter should place CH4 molecules in the water region"
    )
    assert solute_structure.interface_structure is not None, (
        "SoluteStructure.interface_structure must be populated for staging"
    )

    pipe = _make_cli_pipeline(tmp_path, hydrate, "_solute_result", solute_structure)
    code = pipe._run_export_step()
    assert code == 0, "_run_export_step should succeed for the solute branch"

    gro = tmp_path / "solute.gro"
    top = tmp_path / "solute.top"
    assert gro.exists(), f"solute.gro not written: {gro}"
    assert top.exists(), f"solute.top not written: {top}"
    assert (tmp_path / "tip4p-ice.itp").exists(), "tip4p-ice.itp not staged"
    assert (tmp_path / "etoh.itp").exists(), (
        "cage-guest etoh.itp not staged by the custom-guest block"
    )
    assert (tmp_path / "ch4_liquid.itp").exists(), (
        "solute ITP (ch4_liquid.itp) not copied by the solute branch"
    )
    staged_etoh = (tmp_path / "etoh.itp").read_text()
    assert "MOL_H" in staged_etoh, (
        "staged etoh.itp missing MOL_H moleculetype -- copy_custom_guest_itp "
        "was not applied by the custom-guest staging block"
    )

    shutil.copy(MDP_PATH, tmp_path / "em.mdp")
    assert_itp_completeness(str(top), tmp_path)
    assert_gro_top_consistent(str(gro), str(top))

    exit_code, stderr = run_gmx_grompp(
        tmp_path, gro_file="solute.gro", top_file="solute.top"
    )
    assert exit_code == 0, (
        f"gmx grompp failed (CLI solute custom guest):\n{stderr}"
    )

    mols = parse_top_molecules(str(top))
    assert "SOL" in mols and "MOL_H" in mols and "CH4_L" in mols, (
        f"expected SOL + MOL_H + CH4_L in [molecules], got {mols}"
    )
    assert "GUE" not in mols, (
        f"GUE must NOT appear in [molecules] (custom_guest_info not threaded): "
        f"{mols}"
    )
    gro_res = set(parse_gro_residue_names(str(gro)))
    assert "SOL" in gro_res and "MOL_H" in gro_res and "CH4_L" in gro_res, (
        f"expected SOL + MOL_H + CH4_L in .gro residues, got {gro_res}"
    )
    assert "GUE" not in gro_res, (
        f"GUE must NOT appear in .gro residues (custom_guest_info not threaded): "
        f"{gro_res}"
    )


@gmx_skipif
def test_custom_guest_cli_ion_export_grompp(
    tmp_path, _custom_ethanol_hydrate_and_iface
):
    """gmx grompp exits 0 on a custom ethanol guest hydrate exported via the
    CLI ``_run_export_step`` ion branch (plan 44.1-17, Task 1+2).

    Mirrors the GUI ``IonGROMACSExporter`` test (44.1-15) but exercises the
    CLI ion branch (ice+water+guest+Na+Cl ions). ``IonStructure`` (types.py)
    has NO ``interface_structure`` field — only ``guest_nmolecules`` /
    ``guest_atom_count`` propagated by ``IonInserter`` from the source
    interface. The ion branch threads ``custom_guest_info=cgi`` to
    ``write_ion_gro_file`` / ``write_ion_top_file`` (extended in 44.1-15) and
    stages ``etoh.itp`` (cage guest, MOL_H) + ``ion.itp`` (generated) +
    ``tip4p-ice.itp``. The previous broken path (``write_ion_top_file``
    emitted ``guest_res_name="GUE"`` + ``#include "guest.itp"``;
    ``_detect_guest_type`` -> None -> no custom ITP staged) would fail at
    grompp with ``File not found: 'guest.itp'`` and a ``GUE`` moleculetype.
    """
    hydrate, iface, _config = _custom_ethanol_hydrate_and_iface

    ion_structure = _insert_ions(iface, concentration=0.15)
    assert (ion_structure.na_count > 0 or ion_structure.cl_count > 0), (
        "ion inserter should place Na+ / Cl- ions in the water region"
    )
    assert ion_structure.guest_atom_count > 0, (
        "IonStructure.guest_atom_count must be propagated from the source "
        "interface for the custom-guest staging block"
    )
    assert ion_structure.guest_nmolecules > 0, (
        "IonStructure.guest_nmolecules must be propagated from the source "
        "interface for the custom-guest staging block"
    )

    pipe = _make_cli_pipeline(tmp_path, hydrate, "_ion_result", ion_structure)
    code = pipe._run_export_step()
    assert code == 0, "_run_export_step should succeed for the ion branch"

    gro = tmp_path / "ion.gro"
    top = tmp_path / "ion.top"
    assert gro.exists(), f"ion.gro not written: {gro}"
    assert top.exists(), f"ion.top not written: {top}"
    assert (tmp_path / "tip4p-ice.itp").exists(), "tip4p-ice.itp not staged"
    assert (tmp_path / "ion.itp").exists(), (
        "ion ITP (ion.itp) not written by write_ion_itp"
    )
    assert (tmp_path / "etoh.itp").exists(), (
        "cage-guest etoh.itp not staged by the custom-guest block"
    )
    staged_etoh = (tmp_path / "etoh.itp").read_text()
    assert "MOL_H" in staged_etoh, (
        "staged etoh.itp missing MOL_H moleculetype -- copy_custom_guest_itp "
        "was not applied by the custom-guest staging block"
    )

    shutil.copy(MDP_PATH, tmp_path / "em.mdp")
    assert_itp_completeness(str(top), tmp_path)
    assert_gro_top_consistent(str(gro), str(top))

    exit_code, stderr = run_gmx_grompp(
        tmp_path, gro_file="ion.gro", top_file="ion.top"
    )
    assert exit_code == 0, (
        f"gmx grompp failed (CLI ion custom guest):\n{stderr}"
    )

    mols = parse_top_molecules(str(top))
    assert "SOL" in mols and "MOL_H" in mols, (
        f"expected SOL + MOL_H in [molecules], got {mols}"
    )
    if ion_structure.na_count > 0:
        assert "NA" in mols, f"expected NA in [molecules] (na_count>0), got {mols}"
    if ion_structure.cl_count > 0:
        assert "CL" in mols, f"expected CL in [molecules] (cl_count>0), got {mols}"
    assert "GUE" not in mols, (
        f"GUE must NOT appear in [molecules] (custom_guest_info not threaded): "
        f"{mols}"
    )
    gro_res = set(parse_gro_residue_names(str(gro)))
    assert "SOL" in gro_res and "MOL_H" in gro_res, (
        f"expected SOL + MOL_H in .gro residues, got {gro_res}"
    )
    if ion_structure.na_count > 0:
        assert "NA" in gro_res, (
            f"expected NA in .gro residues (na_count>0), got {gro_res}"
        )
    if ion_structure.cl_count > 0:
        assert "CL" in gro_res, (
            f"expected CL in .gro residues (cl_count>0), got {gro_res}"
        )
    assert "GUE" not in gro_res, (
        f"GUE must NOT appear in .gro residues (custom_guest_info not threaded): "
        f"{gro_res}"
    )
