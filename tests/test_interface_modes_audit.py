"""Test all 3 interface modes with hydrate sources.

Verifies that piece, slab, and pocket modes correctly handle hydrate candidates
(ICE + guest molecules) and produce valid InterfaceStructure with
matching atom_names and positions lengths.
"""

import numpy as np
import pytest

from quickice.structure_generation.types import Candidate, InterfaceConfig, InterfaceStructure
from quickice.structure_generation.modes.piece import assemble_piece
from quickice.structure_generation.modes.slab import assemble_slab
from quickice.structure_generation.modes.pocket import assemble_pocket


def create_mock_ice_candidate(ice_atoms: int = 12) -> Candidate:
    """Create a simple mock ice candidate (GenIce style: 3 atoms per molecule O, H, H)."""
    nmol = ice_atoms // 3
    
    # Create realistic positions - simple cubic lattice, ALL POSITIVE coordinates
    # Each molecule ~0.45nm apart (ice Ih lattice)
    positions = []
    atom_names = []
    for i in range(nmol):
        x = (i % 2) * 0.45
        y = ((i // 2) % 2) * 0.45
        z = (i // 4) * 0.45
        positions.extend([
            [x, y, z],  # O - all positive
            [x + 0.1, y, z + 0.05],  # H1 - offset but positive
            [x + 0.05, y + 0.1, z + 0.1]  # H2 - offset but positive
        ])
        atom_names.extend(["O", "H", "H"])
    
    positions = np.array(positions)
    
    # Cell is the bounding box extent
    cell = np.array([[0.9, 0.0, 0.0], [0.0, 0.9, 0.0], [0.0, 0.0, 0.9]])
    
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=nmol,
        phase_id="ice_ih",
        seed=42,
        metadata={"temperature": 273.15, "pressure": 0.101325}
    )


def create_mock_hydrate_candidate(n_water: int = 8, n_guest: int = 1) -> Candidate:
    """Create a mock hydrate candidate with water framework + guest molecules.
    
    Structure:
    - Water framework: TIP4P style (OW, HW1, HW2, MW) x n_water
    - Guest molecules: Me (united-atom methane) x n_guest
    
    Total atoms: n_water * 4 + n_guest * 1
    """
    # Water framework (TIP4P: 4 atoms per molecule)
    # Create realistic TIP4P lattice - ALL POSITIVE coordinates, ~0.45nm apart
    positions = []
    atom_names = []
    
    for i in range(n_water):
        x = 0.1 + (i % 2) * 0.45
        y = 0.1 + ((i // 2) % 2) * 0.45
        z = 0.1 + (i // 4) * 0.45
        positions.extend([
            [x, y, z],       # OW - all positive
            [x + 0.07, y, z + 0.05],  # HW1
            [x + 0.05, y + 0.07, z + 0.03],    # HW2
            [x, y + 0.15, z + 0.05]          # MW
        ])
        atom_names.extend(["OW", "HW1", "HW2", "MW"])
    
    # Guest molecules (Me: 1 atom each) - offset from water framework
    for i in range(n_guest):
        x = 0.3 + (i * 0.3)  # Offset from water framework
        y = 0.3 + (i * 0.2)
        z = 0.3 + (i * 0.2)
        positions.append([x, y, z])
        atom_names.append("Me")
    
    positions = np.array(positions)
    
    # Cell is bounding box extent
    cell = np.array([[0.9, 0.0, 0.0], [0.0, 0.9, 0.0], [0.0, 0.0, 0.9]])
    
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=n_water,
        phase_id="ice_ih",
        seed=42,
        metadata={
            "temperature": 273.15,
            "pressure": 0.101325,
            "original_hydrate": True
        }
    )


def test_piece_mode_with_ice():
    """Test piece mode with regular ice candidate (no guests)."""
    candidate = create_mock_ice_candidate(ice_atoms=12)
    config = InterfaceConfig(
        mode="piece",
        box_x=3.0,
        box_y=3.0,
        box_z=3.0,
        seed=42
    )
    
    iface = assemble_piece(candidate, config)
    
    # Verify atom counts match
    assert len(iface.atom_names) == len(iface.positions), \
        f"MISMATCH: atom_names={len(iface.atom_names)}, positions={len(iface.positions)}"
    
    print(f"piece + ice: OK (positions={len(iface.positions)}, atom_names={len(iface.atom_names)})")


def test_piece_mode_with_hydrate():
    """Test piece mode with hydrate candidate (ice + guests)."""
    candidate = create_mock_hydrate_candidate(n_water=8, n_guest=2)
    config = InterfaceConfig(
        mode="piece",
        box_x=3.0,
        box_y=3.0,
        box_z=3.0,
        seed=42
    )
    
    iface = assemble_piece(candidate, config)
    
    # Verify atom counts match
    assert_len = len(iface.atom_names) == len(iface.positions)
    assert assert_len, \
        f"PIECE MISMATCH: atom_names={len(iface.atom_names)}, positions={len(iface.positions)}"
    
    print(f"piece + hydrate: {'OK' if assert_len else 'FAIL'}")
    if not assert_len:
        print(f"  positions={len(iface.positions)}, atom_names={len(iface.atom_names)}")


def test_slab_mode_with_ice():
    """Test slab mode with regular ice candidate."""
    candidate = create_mock_ice_candidate(ice_atoms=12)
    config = InterfaceConfig(
        mode="slab",
        box_x=3.0,
        box_y=3.0,
        box_z=6.0,
        seed=42,
        ice_thickness=2.0,
        water_thickness=2.0
    )
    
    iface = assemble_slab(candidate, config)
    
    # Verify atom counts match
    assert len(iface.atom_names) == len(iface.positions), \
        f"MISMATCH: atom_names={len(iface.atom_names)}, positions={len(iface.positions)}"
    
    print(f"slab + ice: OK (positions={len(iface.positions)}, atom_names={len(iface.atom_names)})")


def test_slab_mode_with_hydrate():
    """Test slab mode with hydrate candidate (ice + guests)."""
    candidate = create_mock_hydrate_candidate(n_water=8, n_guest=2)
    config = InterfaceConfig(
        mode="slab",
        box_x=3.0,
        box_y=3.0,
        box_z=6.0,
        seed=42,
        ice_thickness=2.0,
        water_thickness=2.0
    )
    
    iface = assemble_slab(candidate, config)
    
    # Verify atom counts match
    assert_len = len(iface.atom_names) == len(iface.positions)
    assert assert_len, \
        f"SLAB MISMATCH: atom_names={len(iface.atom_names)}, positions={len(iface.positions)}"
    
    print(f"slab + hydrate: {'OK' if assert_len else 'FAIL'}")
    if not assert_len:
        print(f"  positions={len(iface.positions)}, atom_names={len(iface.atom_names)}")


def test_pocket_mode_with_ice():
    """Test pocket mode with regular ice candidate."""
    candidate = create_mock_ice_candidate(ice_atoms=12)
    config = InterfaceConfig(
        mode="pocket",
        box_x=3.0,
        box_y=3.0,
        box_z=3.0,
        seed=42,
        pocket_diameter=1.0,
        pocket_shape="sphere"
    )
    
    iface = assemble_pocket(candidate, config)
    
    # Verify atom counts match
    assert len(iface.atom_names) == len(iface.positions), \
        f"MISMATCH: atom_names={len(iface.atom_names)}, positions={len(iface.positions)}"
    
    print(f"pocket + ice: OK (positions={len(iface.positions)}, atom_names={len(iface.atom_names)})")


def test_pocket_mode_with_hydrate():
    """Test pocket mode with hydrate candidate (ice + guests)."""
    candidate = create_mock_hydrate_candidate(n_water=8, n_guest=2)
    config = InterfaceConfig(
        mode="pocket",
        box_x=3.0,
        box_y=3.0,
        box_z=3.0,
        seed=42,
        pocket_diameter=1.0,
        pocket_shape="sphere"
    )
    
    iface = assemble_pocket(candidate, config)
    
    # Verify atom counts match
    assert_len = len(iface.atom_names) == len(iface.positions)
    assert assert_len, \
        f"POCKET MISMATCH: atom_names={len(iface.atom_names)}, positions={len(iface.positions)}"
    
    print(f"pocket + hydrate: {'OK' if assert_len else 'FAIL'}")
    if not assert_len:
        print(f"  positions={len(iface.positions)}, atom_names={len(iface.atom_names)}")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing all 3 interface modes")
    print("=" * 60)
    
    # Test with ice
    test_piece_mode_with_ice()
    test_slab_mode_with_ice()
    test_pocket_mode_with_ice()
    
    print()
    
    # Test with hydrate
    test_piece_mode_with_hydrate()
    test_slab_mode_with_hydrate()
    test_pocket_mode_with_hydrate()