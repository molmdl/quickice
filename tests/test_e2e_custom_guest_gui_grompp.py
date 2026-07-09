"""End-to-end GROMACS grompp validation for the GUI custom-guest hydrate path.

Proves EXPORT-06 (GUI half) for plan 41-10: ``gmx grompp`` exits 0 on a
custom ethanol guest hydrate exported via the GUI multi-molecule writers
(``write_multi_molecule_gro_file`` + ``write_multi_molecule_top_file`` with
``custom_guest_info``), with the custom ITP staged via the transformed-staging
helper ``_stage_custom_guest_itp`` (plan 41-09).

The writers (fixed by plans 41-02 / 41-03) emit:
  - ``.gro`` with ``MOL_H`` residues for the 9-atom ethanol guest
  - ``.top`` with ``[molecules] MOL_H`` + ``[atomtypes]`` oh/ho merged+deduped
    + ``#include "etoh.itp"``

``_stage_custom_guest_itp`` overwrites the under-transformed etoh.itp
(moleculetype ``etoh``) with the fully-transformed copy (moleculetype
``MOL_H``, ``[atoms]`` resname ``MOL_H``), making the staged ITP internally
consistent with the ``.top [molecules] MOL_H`` entry — the prerequisite for
``gmx grompp`` to succeed.

The CLI half of EXPORT-06 is plan 41-11. This test follows the established
repo convention (call writers directly + ``_stage_itp_files`` +
``run_gmx_grompp``) used by ``tests/test_e2e_gmx_validation.py``.
``gmx`` IS on PATH so this test runs (not skipped).
"""

import sys
import shutil
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

from tests.conftest import gmx_skipif  # noqa: E402
from quickice.output.gromacs_writer import (  # noqa: E402
    write_multi_molecule_gro_file,
    write_multi_molecule_top_file,
)
from quickice.structure_generation.hydrate_generator import (  # noqa: E402
    HydrateStructureGenerator,
)
from quickice.structure_generation.modes.slab import assemble_slab  # noqa: E402
from quickice.structure_generation.types import (  # noqa: E402
    HydrateConfig,
    InterfaceConfig,
    MoleculeIndex,
)
from quickice.gui.export import InterfaceGROMACSExporter, SoluteGROMACSExporter  # noqa: E402
from e2e_export_helpers import (  # noqa: E402
    _stage_itp_files,
    _stage_custom_guest_itp,
    _insert_solutes,
    run_gmx_grompp,
    MDP_PATH,
    parse_top_molecules,
    parse_gro_residue_names,
    assert_itp_completeness,
    assert_gro_top_consistent,
)


# ══════════════════════════════════════════════════════════════════════════════
# GUI custom-guest hydrate grompp (EXPORT-06, GUI half)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
def test_custom_guest_gui_grompp_passes(tmp_path):
    """gmx grompp exits 0 on a custom ethanol guest hydrate exported via the
    GUI multi-molecule writers (write_multi_molecule_gro_file +
    write_multi_molecule_top_file with custom_guest_info).

    Builds a tiny synthetic 2-water + 1-custom-ethanol-guest system IN MEMORY
    (no GenIce2 — fast, deterministic): 8 water atoms + 9 ethanol atoms = 17
    atoms.  Stages tip4p-ice.itp + the transformed etoh.itp (moleculetype
    MOL_H), then runs gmx grompp.
    """
    # Synthetic 2-water + 1-ethanol-guest system (17 atoms total).
    positions = np.zeros((17, 3))
    positions[:, 0] = np.linspace(0.01, 0.17, 17)
    atom_names = [
        "OW", "HW1", "HW2", "MW",  # water 1
        "OW", "HW1", "HW2", "MW",  # water 2
        "H", "C", "H", "H", "C", "H", "H", "O", "H",  # ethanol (9 atoms)
    ]
    # Box must exceed 2*cutoff (rcoulomb=rvdw=1.0 nm in em.mdp); 3.0 nm gives a
    # comfortable margin and matches the repo's interface-test box convention.
    cell = np.eye(3) * 3.0
    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 9, "etoh_e2e"),  # custom guest mol_type
    ]
    cgi = {
        "mol_type": "etoh_e2e",
        "residue_name": "MOL_H",
        "itp_path": Path("quickice/data/custom/etoh.itp"),
    }
    itp_files = {"etoh_e2e": "etoh.itp"}

    ws = tmp_path
    gro = ws / "hydrate.gro"
    top = ws / "hydrate.top"
    write_multi_molecule_gro_file(
        positions,
        molecule_index,
        cell,
        str(gro),
        "custom guest hydrate",
        atom_names=atom_names,
        custom_guest_info=cgi,
    )
    write_multi_molecule_top_file(
        molecule_index,
        str(top),
        "custom guest hydrate",
        itp_files=itp_files,
        custom_guest_info=cgi,
    )

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
    assert exit_code == 0, f"gmx grompp failed (GUI custom guest):\n{stderr}"

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
# GUI InterfaceGROMACSExporter custom-guest interface export grompp (44.1-09)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
def test_custom_guest_interface_export_grompp(tmp_path):
    """gmx grompp exits 0 on a custom ethanol guest hydrate exported via the
    GUI ``InterfaceGROMACSExporter.export_interface_gromacs`` method (plan
    44.1-09).

    Unlike ``test_custom_guest_gui_grompp_passes`` (which calls the
    multi-molecule writers directly with synthetic data), this test exercises
    the EXPORTER METHOD end-to-end:

      1. Generate a REAL custom ethanol hydrate via
         ``HydrateStructureGenerator`` (the same path the Hydrate tab uses;
         fast — sI 1x1x1 generates in well under 1s).
      2. ``hydrate.to_candidate()`` -> ``assemble_slab(...)`` -> InterfaceStructure
         (no IndexError — plans 44.1-02/03/05 fixed the threading of
         guest_atom_count through the interface modes).
      3. Mock ``QFileDialog.getSaveFileName`` (under ``QT_QPA_PLATFORM=offscreen``
         it returns ``("", "")`` which makes the exporter return ``False``
         without writing any files). The exporter calls ``getSaveFileName`` ONCE
         for the .gro path; the .top path is derived from ``path.stem``.
         ``QMessageBox`` is mocked to suppress any warning dialogs during
         export.
      4. ``exporter.export_interface_gromacs(iface, hydrate_config=config)``
         calls the shared helper ``_stage_hydrate_guest_itps`` (plan 44.1-08)
         which:
           - builds ``custom_guest_info`` from the hydrate config
             ``[{mol_type='etoh_e2e', residue_name='MOL_H',
                itp_path=Path('quickice/data/custom/etoh.itp')}]``
           - transforms + writes the custom ``etoh.itp`` to the workspace
             (moleculetype ``MOL_H``, ``[atomtypes]`` commented, ``[atoms]``
             resname ``MOL_H``) via the reused ``transform_guest_itp``
         then threads ``custom_guest_info`` to BOTH
         ``write_interface_gro_file`` and ``write_interface_top_file`` (which
         already accept the kwarg from plans 41-04 / 41-05 — only the exporter
         never passed it before this plan), then copies ``tip4p-ice.itp``.
      5. ``assert_itp_completeness`` + ``assert_gro_top_consistent`` (file
         consistency always runs).
      6. ``gmx grompp`` -> ``rc == 0`` (topology is self-consistent +
         simulation-ready).

    This verifies the plan's wiring: ``hydrate_config`` ->
    ``_stage_hydrate_guest_itps`` -> ``custom_guest_info`` -> writers -> valid
    GROMACS output. The previous broken path (``hydrate_config`` not accepted;
    ``_detect_guest_type_from_structure`` returned ``None`` for custom guests;
    no ``etoh.itp`` staged) would fail at grompp with
    ``File not found: 'etoh.itp'``.
    """
    # 1. Generate a real custom ethanol hydrate (sI 1x1x1, fast).
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="etoh_e2e",
        guest_residue_name="MOL",
        guest_gro_path="quickice/data/custom/etoh.gro",
        guest_itp_path="quickice/data/custom/etoh.itp",
        guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
        guest_atom_count=9,
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    hydrate = gen.generate(config)

    # 2. to_candidate() -> assemble_slab() -> InterfaceStructure (44.1-02/05).
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
    # Custom ethanol (9 atoms/mol) must be threaded correctly through the slab
    # mode (44.1-05): guest_atom_count == 9 * guest_nmolecules.
    assert iface.guest_nmolecules > 0, "custom ethanol slab should have guests"
    assert iface.guest_atom_count == 9 * iface.guest_nmolecules, (
        f"custom ethanol slab guest_atom_count={iface.guest_atom_count} != "
        f"9 * guest_nmolecules={9 * iface.guest_nmolecules}"
    )

    # 3. Mock QFileDialog + QMessageBox so the exporter runs end-to-end
    #    without a real GUI. The exporter calls getSaveFileName ONCE for the
    #    .gro path; the .top path is derived from path.stem (no second dialog).
    gro_path = tmp_path / "output.gro"
    top_path = tmp_path / "output.top"
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = InterfaceGROMACSExporter(parent_widget=None)
        ok = exporter.export_interface_gromacs(iface, hydrate_config=config)
        assert ok is True, (
            "export_interface_gromacs returned False — export failed (the "
            "QFileDialog mock may not have been picked up, or staging raised)"
        )

    # 4. Files were written by the exporter (writers + ITP staging).
    assert gro_path.exists(), f".gro not written: {gro_path}"
    assert top_path.exists(), f".top not written: {top_path}"
    assert (tmp_path / "tip4p-ice.itp").exists(), (
        "water ITP (tip4p-ice.itp) not staged by the exporter"
    )
    assert (tmp_path / "etoh.itp").exists(), (
        "custom guest ITP (etoh.itp) not staged by _stage_hydrate_guest_itps"
    )
    # The staged etoh.itp must be the TRANSFORMED copy (moleculetype MOL_H),
    # not the raw source ITP (moleculetype etoh). This is the prerequisite for
    # grompp: the .top [molecules] lists MOL_H, so the #include'd ITP must
    # define moleculetype MOL_H.
    staged_etoh = (tmp_path / "etoh.itp").read_text()
    assert "MOL_H" in staged_etoh, (
        "staged etoh.itp is missing the MOL_H moleculetype — transform_guest_itp "
        "was not applied by _stage_hydrate_guest_itps"
    )

    # 5. Stage the MDP for grompp + run file-consistency assertions.
    shutil.copy(MDP_PATH, tmp_path / "em.mdp")
    assert_itp_completeness(str(top_path), tmp_path)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # 6. Run gmx grompp — must exit 0 (topology is self-consistent +
    #    simulation-ready). The previous broken path (no hydrate_config param,
    #    no custom_guest_info threading, no etoh.itp staging) would fail here
    #    with "File not found: 'etoh.itp'".
    exit_code, stderr = run_gmx_grompp(
        tmp_path, gro_file="output.gro", top_file="output.top"
    )
    assert exit_code == 0, (
        f"gmx grompp failed (GUI InterfaceGROMACSExporter custom guest):\n{stderr}"
    )

    # 7. .top [molecules] lists SOL + MOL_H; .gro residues contain SOL + MOL_H.
    #    This proves the custom_guest_info threading reached the writers: the
    #    [molecules] block uses custom_guest_info['residue_name'] (MOL_H) and
    #    the .gro emits MOL_H residues for the 9-atom ethanol chunk.
    mols = parse_top_molecules(str(top_path))
    assert "SOL" in mols and "MOL_H" in mols, (
        f"expected SOL + MOL_H in [molecules], got {mols}"
    )
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert "SOL" in gro_res and "MOL_H" in gro_res, (
        f"expected SOL + MOL_H in .gro residues, got {gro_res}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# GUI SoluteGROMACSExporter custom-guest solute export grompp (44.1-11)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
def test_custom_guest_solute_export_grompp(tmp_path):
    """gmx grompp exits 0 on a custom ethanol guest hydrate exported via the
    GUI ``SoluteGROMACSExporter.export_solute_gromacs`` method (plan 44.1-11).

    Mirrors ``test_custom_guest_interface_export_grompp`` (44.1-09) but
    exercises the SOLUTE exporter (ice+water+guest+CH4 solute) instead of the
    interface exporter (ice+water+guest). This is the SECOND of four
    per-exporter wiring plans (44.1-09 interface / 44.1-11 solute /
    44.1-13 custom-molecule / 44.1-15 ion).

    Flow:
      1. Generate a REAL custom ethanol hydrate via
         ``HydrateStructureGenerator`` (sI 1x1x1, fast).
      2. ``hydrate.to_candidate()`` -> ``assemble_slab(...)`` ->
         InterfaceStructure (no IndexError — plans 44.1-02/03/05 fixed the
         guest_atom_count threading through slab mode).
      3. ``_insert_solutes(iface, solute_type='CH4', concentration=0.3)`` ->
         SoluteStructure (SoluteInserter creates its own registry internally,
         so the registry is properly populated; CH4 solutes are placed in the
         water region, avoiding the ice/water/guest regions).
      4. Mock ``QFileDialog.getSaveFileName`` (under ``QT_QPA_PLATFORM=offscreen``
         it returns ``("", "")`` which makes the exporter return ``False``
         without writing any files). The exporter calls ``getSaveFileName`` ONCE
         for the .gro path; the .top path is derived from ``path.stem``.
         ``QMessageBox`` is mocked to suppress any warning dialogs.
      5. ``exporter.export_solute_gromacs(solute, hydrate_config=config)``
         calls the shared helper ``_stage_hydrate_guest_itps`` (plan 44.1-08)
         with ``solute_structure.interface_structure`` as the structure
         argument, which:
           - builds ``custom_guest_info`` from the hydrate config
             ``[{mol_type='etoh_e2e', residue_name='MOL_H',
                itp_path=Path('quickice/data/custom/etoh.itp')}]``
           - transforms + writes the custom ``etoh.itp`` to the workspace
             (moleculetype ``MOL_H``, ``[atomtypes]`` commented, ``[atoms]``
             resname ``MOL_H``) via the reused ``transform_guest_itp``
         then threads ``custom_guest_info`` to BOTH ``write_solute_gro_file``
         and ``write_solute_top_file`` (extended in 44.1-11 to accept the
         kwarg — previously they emitted ``guest_res_name="GUE"`` + a
         non-existent ``#include "guest.itp"`` for custom guests, which made
         grompp fatal), then copies ``tip4p-ice.itp`` + ``ch4_liquid.itp``.
      6. ``assert_itp_completeness`` + ``assert_gro_top_consistent`` (file
         consistency always runs).
      7. ``gmx grompp`` -> ``rc == 0`` (topology is self-consistent +
         simulation-ready).

    This verifies the plan's wiring: ``hydrate_config`` ->
    ``_stage_hydrate_guest_itps`` -> ``custom_guest_info`` -> solute writers
    -> valid GROMACS output. The previous broken path (``hydrate_config`` not
    accepted; ``write_solute_top_file`` used ``detect_guest_type_from_atoms``
    -> None for custom -> ``guest_res_name="GUE"`` + no ``#include`` for the
    custom ITP; ``_detect_guest_type_from_structure`` -> None ->
    ``shutil.copy({guest_type}_hydrate.itp)`` -> FileNotFoundError) would fail
    at grompp with ``File not found: 'etoh.itp'`` and a ``GUE`` moleculetype
    that no ITP defines.
    """
    # 1. Generate a real custom ethanol hydrate (sI 1x1x1, fast).
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="etoh_e2e",
        guest_residue_name="MOL",
        guest_gro_path="quickice/data/custom/etoh.gro",
        guest_itp_path="quickice/data/custom/etoh.itp",
        guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
        guest_atom_count=9,
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    hydrate = gen.generate(config)

    # 2. to_candidate() -> assemble_slab() -> InterfaceStructure (44.1-02/05).
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

    # 3. Run the solute inserter to produce a SoluteStructure. SoluteInserter
    #    creates its own registry internally (per test_e2e_solute_export.py),
    #    so no explicit registry setup is needed. CH4 solutes are placed in the
    #    water region, avoiding the ice/water/guest regions.
    solute_structure = _insert_solutes(
        iface, solute_type='CH4', concentration=0.3
    )
    assert solute_structure.n_molecules > 0, (
        "solute inserter should place CH4 molecules in the water region"
    )
    # The solute structure must carry the interface so the exporter can reach
    # guest_atom_count / guest_nmolecules via solute.interface_structure.
    assert solute_structure.interface_structure is not None, (
        "SoluteStructure.interface_structure must be populated for staging"
    )

    # 4. Mock QFileDialog + QMessageBox so the exporter runs end-to-end
    #    without a real GUI. The exporter calls getSaveFileName ONCE for the
    #    .gro path; the .top path is derived from path.stem (no second dialog).
    gro_path = tmp_path / "output.gro"
    top_path = tmp_path / "output.top"
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = SoluteGROMACSExporter(parent_widget=None)
        ok = exporter.export_solute_gromacs(
            solute_structure, hydrate_config=config
        )
        assert ok is True, (
            "export_solute_gromacs returned False — export failed (the "
            "QFileDialog mock may not have been picked up, or staging raised)"
        )

    # 5. Files were written by the exporter (writers + ITP staging).
    assert gro_path.exists(), f".gro not written: {gro_path}"
    assert top_path.exists(), f".top not written: {top_path}"
    assert (tmp_path / "tip4p-ice.itp").exists(), (
        "water ITP (tip4p-ice.itp) not staged by the exporter"
    )
    assert (tmp_path / "etoh.itp").exists(), (
        "custom guest ITP (etoh.itp) not staged by _stage_hydrate_guest_itps"
    )
    assert (tmp_path / "ch4_liquid.itp").exists(), (
        "solute ITP (ch4_liquid.itp) not copied by the exporter"
    )
    # The staged etoh.itp must be the TRANSFORMED copy (moleculetype MOL_H),
    # not the raw source ITP (moleculetype etoh). This is the prerequisite for
    # grompp: the .top [molecules] lists MOL_H, so the #include'd ITP must
    # define moleculetype MOL_H.
    staged_etoh = (tmp_path / "etoh.itp").read_text()
    assert "MOL_H" in staged_etoh, (
        "staged etoh.itp is missing the MOL_H moleculetype — transform_guest_itp "
        "was not applied by _stage_hydrate_guest_itps"
    )

    # 6. Stage the MDP for grompp + run file-consistency assertions.
    shutil.copy(MDP_PATH, tmp_path / "em.mdp")
    assert_itp_completeness(str(top_path), tmp_path)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # 7. Run gmx grompp — must exit 0 (topology is self-consistent +
    #    simulation-ready). The previous broken path (write_solute_top_file
    #    emitted guest_res_name="GUE" + no #include for the custom ITP;
    #    _detect_guest_type_from_structure -> None -> shutil.copy raised
    #    FileNotFoundError) would fail here with "File not found: 'etoh.itp'"
    #    and a GUE moleculetype that no ITP defines.
    exit_code, stderr = run_gmx_grompp(
        tmp_path, gro_file="output.gro", top_file="output.top"
    )
    assert exit_code == 0, (
        f"gmx grompp failed (GUI SoluteGROMACSExporter custom guest):\n{stderr}"
    )

    # 8. .top [molecules] lists SOL + MOL_H + CH4_L; .gro residues contain
    #    SOL + MOL_H + CH4_L. This proves the custom_guest_info threading
    #    reached the solute writers: the [molecules] block uses
    #    custom_guest_info['residue_name'] (MOL_H) for the guest and the
    #    registry name (CH4_L) for the solute; the .gro emits MOL_H residues
    #    for the 9-atom ethanol chunk and CH4_L residues for the solute.
    mols = parse_top_molecules(str(top_path))
    assert "SOL" in mols and "MOL_H" in mols and "CH4_L" in mols, (
        f"expected SOL + MOL_H + CH4_L in [molecules], got {mols}"
    )
    assert "GUE" not in mols, (
        f"GUE must NOT appear in [molecules] (custom_guest_info not threaded): "
        f"{mols}"
    )
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert "SOL" in gro_res and "MOL_H" in gro_res and "CH4_L" in gro_res, (
        f"expected SOL + MOL_H + CH4_L in .gro residues, got {gro_res}"
    )
    assert "GUE" not in gro_res, (
        f"GUE must NOT appear in .gro residues (custom_guest_info not threaded): "
        f"{gro_res}"
    )
