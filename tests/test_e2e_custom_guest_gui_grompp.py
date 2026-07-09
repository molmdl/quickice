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
from quickice.structure_generation.custom_molecule_inserter import (  # noqa: E402
    CustomMoleculeInserter,
)
from quickice.structure_generation.types import (  # noqa: E402
    CustomMoleculeConfig,
    HydrateConfig,
    InterfaceConfig,
    MoleculeIndex,
)
from quickice.gui.export import (  # noqa: E402
    CustomMoleculeGROMACSExporter,
    InterfaceGROMACSExporter,
    IonGROMACSExporter,
    SoluteGROMACSExporter,
)
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


# ══════════════════════════════════════════════════════════════════════════════
# GUI CustomMoleculeGROMACSExporter custom-guest custom-molecule export (44.1-13)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
def test_custom_guest_custom_molecule_export_grompp(tmp_path):
    """gmx grompp exits 0 on a custom ethanol guest hydrate exported via the
    GUI ``CustomMoleculeGROMACSExporter.export_custom_molecule_gromacs`` method
    (plan 44.1-13).

    Mirrors ``test_custom_guest_solute_export_grompp`` (44.1-11) but exercises
    the CUSTOM MOLECULE exporter (ice+water+guest+custom molecule) instead of
    the solute exporter (ice+water+guest+solute). This is the THIRD of four
    per-exporter wiring plans (44.1-09 interface / 44.1-11 solute /
    44.1-13 custom-molecule / 44.1-15 ion).

    A custom-molecule export has TWO kinds of "custom" molecules:
      1. The hydrate CAGE GUEST (ethanol in cages) — staged via
         ``_stage_hydrate_guest_itps`` as ``etoh.itp`` (moleculetype MOL_H) and
         threaded to the writers via ``custom_guest_info``. This is the key
         thing this test verifies (the plan's must-have: "custom guest ITP
         staged + .top references MOL_H (not GUE)").
      2. The USER-PROVIDED custom molecule (also ethanol here) inserted via
         ``CustomMoleculeInserter`` — staged by the exporter's existing
         custom-molecule ITP copy (atomtypes commented).

    Both use the SAME source ``etoh.itp``/``etoh.gro``. To avoid a filename
    COLLISION (the cage-guest staging writes ``etoh.itp`` with moleculetype
    MOL_H, but the custom-molecule copy would overwrite it with the original
    moleculetype) and a DUPLICATE ``#include "etoh.itp"`` in the .top, the
    custom molecule uses a RENAMED COPY (``cmet.itp``/``cmet.gro``) with the
    ``[ moleculetype ]`` name changed from ``etoh`` to ``MOL``. This makes:
      - ``.top [molecules]`` use ``MOL`` (from ``parse_itp_file(cmet.itp)``)
      - ``.gro`` use ``MOL`` (from ``register_custom_molecule()``)
      so ``assert_gro_top_consistent`` passes (direct match). The cage guest
    still uses ``etoh.itp`` -> ``MOL_H``. No filename collision, no duplicate
    #include.

    Flow:
      1. Generate a REAL custom ethanol hydrate via
         ``HydrateStructureGenerator`` (sI 1x1x1, fast).
      2. ``hydrate.to_candidate()`` -> ``assemble_slab(...)`` ->
         InterfaceStructure (no IndexError -- plans 44.1-02/03/05 fixed the
         guest_atom_count threading through slab mode).
      3. Copy ``etoh.gro``/``etoh.itp`` to ``tmp_path/cmet.gro``/``cmet.itp``
         with the ``[ moleculetype ]`` name renamed from ``etoh`` to ``MOL``
         (so the .top ``[molecules]`` name matches the .gro residue name).
         Insert 1 custom molecule via ``CustomMoleculeInserter.place_random``
         -> ``CustomMoleculeStructure`` (carries ``interface_structure`` with
         the ethanol cage guests).
      4. Mock ``QFileDialog.getSaveFileName`` (under ``QT_QPA_PLATFORM=offscreen``
         it returns ``("", "")`` which makes the exporter return ``False``
         without writing any files). The exporter calls ``getSaveFileName`` ONCE
         for the .gro path; the .top path is derived from ``path.stem``.
         ``QMessageBox`` is mocked to suppress any warning/error dialogs.
      5. ``exporter.export_custom_molecule_gromacs(custom_structure,
         hydrate_config=config)`` calls the shared helper
         ``_stage_hydrate_guest_itps`` (plan 44.1-08) which:
           - builds ``custom_guest_info`` from the hydrate config
             ``[{mol_type='etoh_e2e', residue_name='MOL_H',
                itp_path=Path('quickice/data/custom/etoh.itp')}]``
           - transforms + writes the custom ``etoh.itp`` to the workspace
             (moleculetype ``MOL_H``, ``[atomtypes]`` commented, ``[atoms]``
             resname ``MOL_H``) via the reused ``transform_guest_itp``
         then threads ``custom_guest_info`` to BOTH
         ``write_custom_molecule_gro_file`` and ``write_custom_molecule_top_file``
         (extended in 44.1-13 to accept the kwarg -- previously they emitted
         ``guest_res_name="GUE"`` + a non-existent ``#include "guest.itp"``
         for custom guests, which made grompp fatal), then copies
         ``tip4p-ice.itp`` + the custom molecule ``cmet.itp`` (atomtypes
         commented).
      6. ``assert_itp_completeness`` + ``assert_gro_top_consistent`` (file
         consistency always runs).
      7. ``gmx grompp`` -> ``rc == 0`` (topology is self-consistent +
         simulation-ready).

    This verifies the plan's wiring: ``hydrate_config`` ->
    ``_stage_hydrate_guest_itps`` -> ``custom_guest_info`` -> custom-molecule
    writers -> valid GROMACS output. The previous broken path
    (``hydrate_config`` not accepted; ``write_custom_molecule_top_file`` used
    ``detect_guest_type_from_atoms`` -> None for custom ->
    ``guest_res_name="GUE"`` + ``#include "guest.itp"``;
    ``_detect_guest_type_from_structure`` -> None -> ``shutil.copy`` raised
    ``FileNotFoundError``) would fail at grompp with
    ``File not found: 'guest.itp'`` and a ``GUE`` moleculetype that no ITP
    defines.
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

    # 3. Build a renamed copy of the ethanol custom molecule data so the
    #    custom-molecule ITP (cmet.itp) does NOT collide with the cage-guest
    #    ITP (etoh.itp, staged as MOL_H by _stage_hydrate_guest_itps). Both
    #    the cage guest and the custom molecule use the same source etoh.itp;
    #    without the rename the exporter's custom-molecule ITP copy (atomtypes
    #    commented, moleculetype "etoh") would OVERWRITE the staged cage-guest
    #    ITP (moleculetype MOL_H), and the .top would have a DUPLICATE
    #    #include "etoh.itp". The [moleculetype] name is renamed from "etoh"
    #    to "MOL" so the .top [molecules] name ("MOL" from parse_itp_file)
    #    matches the .gro residue name ("MOL" from register_custom_molecule).
    #    The [atoms] resname is already "MOL" in etoh.itp.
    cmet_gro = tmp_path / "cmet.gro"
    cmet_itp = tmp_path / "cmet.itp"
    shutil.copy(ETOH_GRO, cmet_gro)
    cmet_lines = ETOH_ITP.read_text().splitlines(keepends=True)
    _in_moltype = False
    for i, line in enumerate(cmet_lines):
        if "[ moleculetype ]" in line:
            _in_moltype = True
        elif _in_moltype and line.strip() and not line.strip().startswith(";"):
            # First non-comment, non-empty line after [ moleculetype ] is the
            # moleculetype name ("etoh       3"); rename "etoh" -> "MOL".
            cmet_lines[i] = line.replace("etoh", "MOL", 1)
            break
    cmet_itp.write_text("".join(cmet_lines))

    # Insert 1 custom molecule into the interface. CustomMoleculeInserter
    # creates its own registry internally (register_custom_molecule() ->
    # "MOL"), so the .gro residue name is "MOL" and matches the renamed
    # cmet.itp moleculetype. place_random places the molecule in the water
    # region (no overlap with ice/water/guest regions).
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
    # The custom structure must carry the guest info propagated from the
    # interface (custom_molecule_inserter.py:782-783) so the exporter's
    # staging helper presence gate passes.
    assert custom_structure.guest_atom_count > 0, (
        "CustomMoleculeStructure.guest_atom_count must be propagated from the "
        "interface for the staging helper's presence gate"
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
        exporter = CustomMoleculeGROMACSExporter(parent_widget=None)
        ok = exporter.export_custom_molecule_gromacs(
            custom_structure, hydrate_config=config
        )
        assert ok is True, (
            "export_custom_molecule_gromacs returned False -- export failed "
            "(the QFileDialog mock may not have been picked up, or staging "
            "raised)"
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
    assert (tmp_path / "cmet.itp").exists(), (
        "custom molecule ITP (cmet.itp) not copied by the exporter"
    )
    # The staged etoh.itp must be the TRANSFORMED copy (moleculetype MOL_H),
    # not the raw source ITP (moleculetype etoh). This is the prerequisite for
    # grompp: the .top [molecules] lists MOL_H, so the #include'd ITP must
    # define moleculetype MOL_H.
    staged_etoh = (tmp_path / "etoh.itp").read_text()
    assert "MOL_H" in staged_etoh, (
        "staged etoh.itp is missing the MOL_H moleculetype -- transform_guest_itp "
        "was not applied by _stage_hydrate_guest_itps"
    )

    # 6. Stage the MDP for grompp + run file-consistency assertions.
    shutil.copy(MDP_PATH, tmp_path / "em.mdp")
    assert_itp_completeness(str(top_path), tmp_path)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # 7. Run gmx grompp -- must exit 0 (topology is self-consistent +
    #    simulation-ready). The previous broken path (write_custom_molecule_top_file
    #    emitted guest_res_name="GUE" + no #include for the custom ITP;
    #    _detect_guest_type_from_structure -> None -> shutil.copy raised
    #    FileNotFoundError) would fail here with "File not found: 'guest.itp'"
    #    and a GUE moleculetype that no ITP defines.
    exit_code, stderr = run_gmx_grompp(
        tmp_path, gro_file="output.gro", top_file="output.top"
    )
    assert exit_code == 0, (
        f"gmx grompp failed (GUI CustomMoleculeGROMACSExporter custom guest):\n{stderr}"
    )

    # 8. .top [molecules] lists SOL + MOL_H + MOL; .gro residues contain
    #    SOL + MOL_H + MOL. This proves the custom_guest_info threading
    #    reached the custom-molecule writers: the [molecules] block uses
    #    custom_guest_info['residue_name'] (MOL_H) for the cage guest and the
    #    ITP moleculetype name (MOL) for the custom molecule; the .gro emits
    #    MOL_H residues for the 9-atom ethanol cage-guest chunk and MOL
    #    residues for the custom molecule.
    mols = parse_top_molecules(str(top_path))
    assert "SOL" in mols and "MOL_H" in mols and "MOL" in mols, (
        f"expected SOL + MOL_H + MOL in [molecules], got {mols}"
    )
    assert "GUE" not in mols, (
        f"GUE must NOT appear in [molecules] (custom_guest_info not threaded): "
        f"{mols}"
    )
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    assert "SOL" in gro_res and "MOL_H" in gro_res and "MOL" in gro_res, (
        f"expected SOL + MOL_H + MOL in .gro residues, got {gro_res}"
    )
    assert "GUE" not in gro_res, (
        f"GUE must NOT appear in .gro residues (custom_guest_info not threaded): "
        f"{gro_res}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# GUI IonGROMACSExporter custom-guest ion export (44.1-15)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
def test_custom_guest_ion_export_grompp(tmp_path):
    """gmx grompp exits 0 on a custom ethanol guest hydrate exported via the
    GUI ``IonGROMACSExporter.export_ion_gromacs`` method (plan 44.1-15).

    Mirrors ``test_custom_guest_solute_export_grompp`` (44.1-11) and
    ``test_custom_guest_custom_molecule_export_grompp`` (44.1-13) but
    exercises the ION exporter (ice+water+guest+Na+Cl ions) instead of the
    solute / custom-molecule exporter. This is the FOURTH and LAST of the
    four per-exporter wiring plans (44.1-09 interface / 44.1-11 solute /
    44.1-13 custom-molecule / 44.1-15 ion).

    IMPORTANT DIFFERENCE from 44.1-11/13: ``IonStructure`` (types.py:826-876)
    has NO ``interface_structure`` field — only ``guest_nmolecules`` /
    ``guest_atom_count`` (populated by ``IonInserter.replace_water_with_ions``
    from the source interface, ion_inserter.py:243/287/312/538). The exporter
    passes the ion_structure ITSELF to the staging helper (config-driven
    Option A — no structure ref to follow, see 44.1-RESEARCH §5).

    Flow:
      1. Generate a REAL custom ethanol hydrate via
         ``HydrateStructureGenerator`` (sI 1x1x1, fast).
      2. ``hydrate.to_candidate()`` -> ``assemble_slab(...)`` ->
         InterfaceStructure (no IndexError — plans 44.1-02/03/05 fixed the
         guest_atom_count threading through slab mode).
      3. ``_insert_ions(iface, concentration=0.15)`` -> IonStructure. The
         IonInserter creates its own molecule_index internally (literal
         mol_type=="guest" entries, ion_inserter.py:150-153) and propagates
         guest_atom_count / guest_nmolecules from the source interface
         (ion_inserter.py:243/287/312/538). Na+ / Cl- ions replace water
         molecules in the water region (no overlap with ice/water/guest).
      4. Mock ``QFileDialog.getSaveFileName`` (under ``QT_QPA_PLATFORM=offscreen``
         it returns ``("", "")`` which makes the exporter return ``False``
         without writing any files). The exporter calls ``getSaveFileName`` ONCE
         for the .gro path; the .top path is derived from ``path.stem``.
         ``QMessageBox`` is mocked to suppress any warning/error dialogs.
      5. ``exporter.export_ion_gromacs(ion_structure, hydrate_config=config)``
         calls the shared helper ``_stage_hydrate_guest_itps`` (plan 44.1-08)
         with the ion_structure ITSELF as the structure argument (no
         interface_structure to follow), which:
           - builds ``custom_guest_info`` from the hydrate config
             ``[{mol_type='etoh_e2e', residue_name='MOL_H',
                itp_path=Path('quickice/data/custom/etoh.itp')}]``
           - transforms + writes the custom ``etoh.itp`` to the workspace
             (moleculetype ``MOL_H``, ``[atomtypes]`` commented, ``[atoms]``
             resname ``MOL_H``) via the reused ``transform_guest_itp``
         then threads ``custom_guest_info`` to BOTH ``write_ion_gro_file`` and
         ``write_ion_top_file`` (extended in 44.1-15 to accept the kwarg —
         previously they emitted ``guest_res_name="GUE"`` + a non-existent
         ``#include "guest.itp"`` for custom guests, which made grompp
         fatal), then copies ``tip4p-ice.itp`` + writes ``ion.itp`` (the Na+
         / Cl- combined ion ITP).
      6. ``assert_itp_completeness`` + ``assert_gro_top_consistent`` (file
         consistency always runs).
      7. ``gmx grompp`` -> ``rc == 0`` (topology is self-consistent +
         simulation-ready).

    This verifies the plan's wiring: ``hydrate_config`` ->
    ``_stage_hydrate_guest_itps`` -> ``custom_guest_info`` -> ion writers
    -> valid GROMACS output. The previous broken path (``hydrate_config`` not
    accepted; ``write_ion_top_file`` used ``detect_guest_type_from_atoms`` ->
    None for custom -> ``guest_res_name="GUE"`` + ``#include "guest.itp"``;
    ``_detect_guest_type_from_structure`` -> None -> ``shutil.copy`` raised
    ``FileNotFoundError``) would fail at grompp with
    ``File not found: 'guest.itp'`` and a ``GUE`` moleculetype that no ITP
    defines.
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

    # 3. Run the ion inserter to produce an IonStructure. IonInserter creates
    #    its own molecule_index internally (literal "guest" entries,
    #    ion_inserter.py:150-153) and propagates guest_atom_count /
    #    guest_nmolecules from the source interface
    #    (ion_inserter.py:243/287/312/538). Na+ / Cl- replace water molecules
    #    in the water region (no overlap with ice/water/guest).
    ion_structure = _insert_ions(iface, concentration=0.15)
    assert (ion_structure.na_count > 0 or ion_structure.cl_count > 0), (
        "ion inserter should place Na+ / Cl- ions in the water region"
    )
    # The ion structure must carry the guest info propagated from the
    # interface (ion_inserter.py:243/287/312/538) so the exporter's staging
    # helper presence gate passes.
    assert ion_structure.guest_atom_count > 0, (
        "IonStructure.guest_atom_count must be propagated from the source "
        "interface for the staging helper's presence gate"
    )
    assert ion_structure.guest_nmolecules > 0, (
        "IonStructure.guest_nmolecules must be propagated from the source "
        "interface for the staging helper's presence gate"
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
        exporter = IonGROMACSExporter(parent_widget=None)
        ok = exporter.export_ion_gromacs(
            ion_structure, hydrate_config=config
        )
        assert ok is True, (
            "export_ion_gromacs returned False — export failed (the "
            "QFileDialog mock may not have been picked up, or staging raised)"
        )

    # 5. Files were written by the exporter (writers + ITP staging).
    assert gro_path.exists(), f".gro not written: {gro_path}"
    assert top_path.exists(), f".top not written: {top_path}"
    assert (tmp_path / "tip4p-ice.itp").exists(), (
        "water ITP (tip4p-ice.itp) not staged by the exporter"
    )
    assert (tmp_path / "ion.itp").exists(), (
        "ion ITP (ion.itp) not written by write_ion_itp"
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

    # 6. Stage the MDP for grompp + run file-consistency assertions.
    shutil.copy(MDP_PATH, tmp_path / "em.mdp")
    assert_itp_completeness(str(top_path), tmp_path)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # 7. Run gmx grompp — must exit 0 (topology is self-consistent +
    #    simulation-ready). The previous broken path (write_ion_top_file
    #    emitted guest_res_name="GUE" + #include "guest.itp";
    #    _detect_guest_type_from_structure -> None -> shutil.copy raised
    #    FileNotFoundError) would fail here with "File not found: 'guest.itp'"
    #    and a GUE moleculetype that no ITP defines.
    exit_code, stderr = run_gmx_grompp(
        tmp_path, gro_file="output.gro", top_file="output.top"
    )
    assert exit_code == 0, (
        f"gmx grompp failed (GUI IonGROMACSExporter custom guest):\n{stderr}"
    )

    # 8. .top [molecules] lists SOL + MOL_H + NA + CL; .gro residues contain
    #    SOL + MOL_H + NA + CL. This proves the custom_guest_info threading
    #    reached the ion writers: the [molecules] block uses
    #    custom_guest_info['residue_name'] (MOL_H) for the cage guest and the
    #    ion labels (NA / CL) for the ions; the .gro emits MOL_H residues for
    #    the 9-atom ethanol cage-guest chunk and NA / CL residues for the ions.
    mols = parse_top_molecules(str(top_path))
    assert "SOL" in mols and "MOL_H" in mols, (
        f"expected SOL + MOL_H in [molecules], got {mols}"
    )
    # NA / CL appear when ions were placed.
    if ion_structure.na_count > 0:
        assert "NA" in mols, f"expected NA in [molecules] (na_count>0), got {mols}"
    if ion_structure.cl_count > 0:
        assert "CL" in mols, f"expected CL in [molecules] (cl_count>0), got {mols}"
    assert "GUE" not in mols, (
        f"GUE must NOT appear in [molecules] (custom_guest_info not threaded): "
        f"{mols}"
    )
    gro_res = set(parse_gro_residue_names(str(gro_path)))
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
