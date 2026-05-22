"""Shared conftest.py for E2E export tests.

Provides all structure fixtures, mock dialog fixtures, and chain dependency
fixtures needed by plans 01-08 of the e2e-export-test phase.

Structure fixtures:
    - simple_candidate: 1-molecule ice Candidate
    - ranked_candidate: RankedCandidate wrapping simple_candidate
    - simple_hydrate_config: minimal HydrateConfig
    - simple_hydrate_structure: minimal HydrateStructure
    - simple_interface: 2 ice + 2 water InterfaceStructure (no guests)
    - interface_with_ch4_guests: extends simple_interface with CH4 guests
    - interface_with_thf_guests: variant with THF guests

Chain dependency fixtures (incremental):
    - custom_structure: CustomMoleculeStructure using etoh.itp
    - solute_structure: SoluteStructure with CH4 solute
    - ion_structure: minimal IonStructure with Na+/Cl-

Mock dialog fixtures:
    - mock_save_dialog: factory for export.py QFileDialog mocking
    - mock_hydrate_save_dialog: factory for hydrate_export.py QFileDialog mocking
    - mock_cancel_dialog: factory for cancelled QFileDialog simulation
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch

from quickice.structure_generation.types import (
    Candidate, InterfaceStructure, HydrateStructure, HydrateConfig,
    HydrateLatticeInfo, MoleculeIndex, IonStructure, SoluteStructure,
    CustomMoleculeStructure, CustomMoleculeConfig
)
from quickice.ranking.types import RankedCandidate
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry


# ---------------------------------------------------------------------------
# Structure fixtures (basic — standalone)
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_candidate():
    """1-molecule ice Candidate with 3 atoms (O, H, H).

    Uses a hexagonal-like cell for realism.
    """
    positions = np.array([
        [0.1, 0.1, 0.1],
        [0.15, 0.12, 0.1],
        [0.08, 0.12, 0.1],
    ])
    atom_names = ["O", "H", "H"]
    cell = np.array([
        [0.9, 0.0, 0.0],
        [0.0, 0.78, 0.0],
        [0.0, 0.0, 0.72],
    ])
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=1,
        phase_id="ice_ih",
        seed=42,
        metadata={},
    )


@pytest.fixture
def ranked_candidate(simple_candidate):
    """RankedCandidate wrapping simple_candidate with zero scores."""
    return RankedCandidate(
        candidate=simple_candidate,
        energy_score=0.0,
        density_score=0.0,
        diversity_score=0.0,
        combined_score=0.0,
        rank=1,
    )


@pytest.fixture
def simple_hydrate_config():
    """Minimal HydrateConfig: sI lattice with CH4 guest, 1x1x1 supercell."""
    return HydrateConfig(
        lattice_type="sI",
        guest_type="ch4",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )


@pytest.fixture
def simple_hydrate_structure(simple_hydrate_config):
    """Minimal HydrateStructure with 2 water + 1 CH4 guest.

    13 atoms total:
        - 8 water atoms: 2 × (OW, HW1, HW2, MW)
        - 5 CH4 atoms: 1 × (C, H, H, H, H)
    """
    positions = np.zeros((13, 3))
    # Give water atoms some non-zero positions
    for i in range(8):
        positions[i] = [0.01 * i, 0.01 * i, 0.01 * i]
    for i in range(5):
        positions[8 + i] = [0.1 + 0.01 * i, 0.1, 0.1]

    atom_names = [
        "OW", "HW1", "HW2", "MW",  # water mol 1
        "OW", "HW1", "HW2", "MW",  # water mol 2
        "C", "H", "H", "H", "H",   # CH4 guest
    ]

    cell = np.eye(3) * 1.2  # 1.2 nm cubic box

    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 5, "ch4"),
    ]

    lattice_info = HydrateLatticeInfo.from_lattice_type("sI")

    return HydrateStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        molecule_index=molecule_index,
        config=simple_hydrate_config,
        lattice_info=lattice_info,
        report="test",
        guest_count=1,
        water_count=2,
    )


@pytest.fixture
def simple_interface():
    """InterfaceStructure: 2 ice molecules + 2 water molecules, NO guests.

    14 atoms total:
        - 6 ice atoms:  2 × (O, H, H)
        - 8 water atoms: 2 × (OW, HW1, HW2, MW)
    """
    positions = np.zeros((14, 3))
    # Give some non-zero positions for realism
    positions[0:3] = np.array([[0.1, 0.1, 0.1], [0.15, 0.12, 0.1], [0.08, 0.12, 0.1]])
    positions[3:6] = np.array([[0.2, 0.1, 0.1], [0.25, 0.12, 0.1], [0.18, 0.12, 0.1]])
    positions[6:10] = np.array([[0.5, 0.5, 2.0], [0.55, 0.52, 2.0],
                                [0.48, 0.52, 2.0], [0.50, 0.51, 2.0]])
    positions[10:14] = np.array([[1.0, 0.5, 2.0], [1.05, 0.52, 2.0],
                                  [0.98, 0.52, 2.0], [1.00, 0.51, 2.0]])

    atom_names = [
        "O", "H", "H",           # ice mol 1
        "O", "H", "H",           # ice mol 2
        "OW", "HW1", "HW2", "MW",  # water mol 1
        "OW", "HW1", "HW2", "MW",  # water mol 2
    ]

    cell = np.eye(3) * 3.0

    molecule_index = [
        MoleculeIndex(0, 3, "ice"),
        MoleculeIndex(3, 3, "ice"),
        MoleculeIndex(6, 4, "water"),
        MoleculeIndex(10, 4, "water"),
    ]

    return InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        ice_atom_count=6,
        water_atom_count=8,
        ice_nmolecules=2,
        water_nmolecules=2,
        mode="slab",
        report="test",
        guest_atom_count=0,
        guest_nmolecules=0,
        molecule_index=molecule_index,
    )


@pytest.fixture
def interface_with_ch4_guests(simple_interface):
    """InterfaceStructure extending simple_interface with 1 CH4 guest molecule.

    19 atoms total:
        - 6 ice atoms (from simple_interface)
        - 8 water atoms (from simple_interface)
        - 5 guest atoms: 1 × (C, H, H, H, H)
    """
    # Extend positions with CH4 guest
    guest_positions = np.array([
        [1.5, 1.0, 2.5],
        [1.55, 1.02, 2.5],
        [1.48, 1.02, 2.5],
        [1.50, 1.05, 2.5],
        [1.50, 0.98, 2.5],
    ])
    positions = np.vstack([simple_interface.positions, guest_positions])

    # Extend atom names with CH4 guest
    atom_names = simple_interface.atom_names + ["C", "H", "H", "H", "H"]

    # Extend molecule_index with guest entry
    molecule_index = simple_interface.molecule_index + [
        MoleculeIndex(14, 5, "guest"),
    ]

    return InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=simple_interface.cell.copy(),
        ice_atom_count=6,
        water_atom_count=8,
        ice_nmolecules=simple_interface.ice_nmolecules,
        water_nmolecules=simple_interface.water_nmolecules,
        mode=simple_interface.mode,
        report=simple_interface.report,
        guest_atom_count=5,
        guest_nmolecules=1,
        molecule_index=molecule_index,
    )


@pytest.fixture
def interface_with_thf_guests():
    """InterfaceStructure with 2 ice + 2 water + 1 THF guest molecule.

    27 atoms total:
        - 6 ice atoms: 2 × (O, H, H)
        - 8 water atoms: 2 × (OW, HW1, HW2, MW)
        - 13 guest atoms: 1 THF (O,CA,CA,CB,CB,H,H,H,H,H,H,H,H)
    """
    positions = np.zeros((27, 3))
    # Ice atoms
    positions[0:3] = np.array([[0.1, 0.1, 0.1], [0.15, 0.12, 0.1], [0.08, 0.12, 0.1]])
    positions[3:6] = np.array([[0.2, 0.1, 0.1], [0.25, 0.12, 0.1], [0.18, 0.12, 0.1]])
    # Water atoms
    positions[6:10] = np.array([[0.5, 0.5, 2.0], [0.55, 0.52, 2.0],
                                [0.48, 0.52, 2.0], [0.50, 0.51, 2.0]])
    positions[10:14] = np.array([[1.0, 0.5, 2.0], [1.05, 0.52, 2.0],
                                  [0.98, 0.52, 2.0], [1.00, 0.51, 2.0]])
    # THF guest atoms (13 atoms)
    for i in range(13):
        positions[14 + i] = [1.5 + 0.05 * i, 1.0, 2.5]

    atom_names = [
        # Ice
        "O", "H", "H", "O", "H", "H",
        # Water
        "OW", "HW1", "HW2", "MW", "OW", "HW1", "HW2", "MW",
        # THF guest (13 atoms)
        "O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H",
    ]

    cell = np.eye(3) * 3.0

    molecule_index = [
        MoleculeIndex(0, 3, "ice"),
        MoleculeIndex(3, 3, "ice"),
        MoleculeIndex(6, 4, "water"),
        MoleculeIndex(10, 4, "water"),
        MoleculeIndex(14, 13, "guest"),
    ]

    return InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        ice_atom_count=6,
        water_atom_count=8,
        ice_nmolecules=2,
        water_nmolecules=2,
        mode="slab",
        report="test",
        guest_atom_count=13,
        guest_nmolecules=1,
        molecule_index=molecule_index,
    )


# ---------------------------------------------------------------------------
# Chain dependency fixtures (incremental)
# ---------------------------------------------------------------------------


@pytest.fixture
def custom_structure(simple_interface):
    """CustomMoleculeStructure: interface + 1 ethanol molecule from etoh.itp.

    Uses existing quickice/data/custom/etoh.itp file (9 atoms per ethanol).
    23 atoms total:
        - 6 ice atoms (from simple_interface)
        - 8 water atoms (from simple_interface)
        - 9 custom molecule atoms: 1 × ethanol (H,C,H,H,C,H,H,O,H)
    """
    # Ethanol has 9 atoms as per etoh.itp
    custom_positions = np.zeros((9, 3))
    # Give custom atoms some positions in the liquid region
    for i in range(9):
        custom_positions[i] = [1.5 + 0.02 * i, 1.0, 2.5]

    positions = np.vstack([simple_interface.positions, custom_positions])

    # Ethanol atom names from etoh.itp: H, C, H, H, C, H, H, O, H
    custom_atom_names = ["H", "C", "H", "H", "C", "H", "H", "O", "H"]

    atom_names = simple_interface.atom_names + custom_atom_names

    # ice (6) + water (8) + custom (9) = 23 total
    molecule_index = simple_interface.molecule_index + [
        MoleculeIndex(14, 9, "custom"),
    ]

    itp_path = Path("quickice/data/custom/etoh.itp")

    return CustomMoleculeStructure(
        positions=positions,
        atom_names=atom_names,
        cell=simple_interface.cell.copy(),
        molecule_index=molecule_index,
        ice_atom_count=6,
        water_atom_count=8,
        custom_molecule_atom_count=9,
        guest_atom_count=0,
        moleculetype_name="ETOH",
        itp_path=itp_path,
        custom_molecule_count=1,
        interface_structure=simple_interface,
    )


@pytest.fixture
def solute_structure(interface_with_ch4_guests):
    """SoluteStructure with 1 CH4 solute molecule.

    5 atoms: C, H, H, H, H
    Uses interface_with_ch4_guests as source so that
    interface.guest_nmolecules > 0 triggers guest ITP code path.
    """
    positions = np.array([
        [1.5, 1.0, 2.5],
        [1.55, 1.02, 2.5],
        [1.48, 1.02, 2.5],
        [1.50, 1.05, 2.5],
        [1.50, 0.98, 2.5],
    ])

    atom_names = ["C", "H", "H", "H", "H"]

    registry = MoleculetypeRegistry()
    registry.register_liquid_solute("CH4")

    return SoluteStructure(
        positions=positions,
        atom_names=atom_names,
        cell=interface_with_ch4_guests.cell.copy(),
        solute_type="CH4",
        n_molecules=1,
        molecule_indices=[(0, 5)],
        registry=registry,
        interface_structure=interface_with_ch4_guests,
    )


@pytest.fixture
def ion_structure(simple_interface):
    """Minimal IonStructure: 2 water + 1 Na + 1 Cl.

    10 atoms total:
        - 8 water atoms: 2 × (OW, HW1, HW2, MW)
        - 1 NA
        - 1 CL
    """
    positions = np.zeros((10, 3))
    # Water positions
    positions[0:4] = np.array([[0.5, 0.5, 2.0], [0.55, 0.52, 2.0],
                                [0.48, 0.52, 2.0], [0.50, 0.51, 2.0]])
    positions[4:8] = np.array([[1.0, 0.5, 2.0], [1.05, 0.52, 2.0],
                                [0.98, 0.52, 2.0], [1.00, 0.51, 2.0]])
    # Ion positions
    positions[8] = [1.5, 1.0, 2.5]
    positions[9] = [1.5, 1.0, 2.0]

    atom_names = [
        "OW", "HW1", "HW2", "MW",  # water mol 1
        "OW", "HW1", "HW2", "MW",  # water mol 2
        "NA",                       # sodium
        "CL",                       # chloride
    ]

    cell = np.eye(3) * 3.0

    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 1, "na"),
        MoleculeIndex(9, 1, "cl"),
    ]

    return IonStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        molecule_index=molecule_index,
        na_count=1,
        cl_count=1,
        report="test",
    )


# ---------------------------------------------------------------------------
# Mock dialog fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_save_dialog(tmp_path):
    """Factory fixture for export.py QFileDialog mocking.

    Returns a callable that creates (save_path, dialog_patch, mb_patch).

    Usage in tests::

        def test_example(mock_save_dialog):
            save_path, dialog_patch, mb_patch = mock_save_dialog("output.gro")
            with dialog_patch, mb_patch:
                # code under test that calls QFileDialog.getSaveFileName
                ...
            assert Path(save_path).exists()
    """
    def _create(filename="test.gro"):
        save_path = str(tmp_path / filename)
        dialog_patch = patch(
            'quickice.gui.export.QFileDialog.getSaveFileName',
            return_value=(save_path, "GRO Files (*.gro)")
        )
        mb_patch = patch('quickice.gui.export.QMessageBox')
        return save_path, dialog_patch, mb_patch
    return _create


@pytest.fixture
def mock_hydrate_save_dialog(tmp_path):
    """Factory fixture for hydrate_export.py QFileDialog mocking.

    Same pattern as mock_save_dialog but patches the hydrate_export module.

    Usage in tests::

        def test_example(mock_hydrate_save_dialog):
            save_path, dialog_patch, mb_patch = mock_hydrate_save_dialog("hydrate.gro")
            with dialog_patch, mb_patch:
                # code under test that calls hydrate_export QFileDialog
                ...
    """
    def _create(filename="hydrate_test.gro"):
        save_path = str(tmp_path / filename)
        dialog_patch = patch(
            'quickice.gui.hydrate_export.QFileDialog.getSaveFileName',
            return_value=(save_path, "GRO Files (*.gro)")
        )
        mb_patch = patch('quickice.gui.hydrate_export.QMessageBox')
        return save_path, dialog_patch, mb_patch
    return _create


@pytest.fixture
def mock_cancel_dialog():
    """Factory fixture for cancelled QFileDialog simulation.

    Returns empty string ("", "") from getSaveFileName to simulate user
    cancelling the dialog.

    Usage in tests::

        def test_cancel(mock_cancel_dialog):
            dialog_patch, mb_patch = mock_cancel_dialog('quickice.gui.export')
            with dialog_patch, mb_patch:
                # code under test — should handle cancel gracefully
                ...
    """
    def _create(module_path='quickice.gui.export'):
        dialog_patch = patch(
            f'{module_path}.QFileDialog.getSaveFileName',
            return_value=("", "")
        )
        mb_patch = patch(f'{module_path}.QMessageBox')
        return dialog_patch, mb_patch
    return _create
