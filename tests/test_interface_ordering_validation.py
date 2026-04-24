"""Test atom ordering validation in interface_to_vtk_molecules."""

import numpy as np
import pytest
from quickice.structure_generation.types import InterfaceStructure
from quickice.gui.vtk_utils import interface_to_vtk_molecules


def test_interface_ice_atom_ordering_validation():
    """Test that ice atom ordering is validated in interface_to_vtk_molecules."""
    # Valid ice: O, H, H pattern
    ice_positions = np.array([
        [0.0, 0.0, 0.0],   # O1
        [0.1, 0.0, 0.0],   # H1 of ice mol 1
        [-0.1, 0.0, 0.0],  # H2 of ice mol 1
        [1.0, 0.0, 0.0],   # O2
        [1.1, 0.0, 0.0],   # H1 of ice mol 2
        [0.9, 0.0, 0.0],   # H2 of ice mol 2
    ])
    ice_atom_names = ["O", "H", "H", "O", "H", "H"]
    ice_atom_count = 6
    ice_nmolecules = 2
    
    # Valid water: OW, HW1, HW2, MW pattern
    water_positions = np.array([
        [2.0, 0.0, 0.0],   # OW1
        [2.1, 0.0, 0.0],   # HW1 of water mol 1
        [1.9, 0.0, 0.0],   # HW2 of water mol 1
        [2.0, 0.0, 0.0],   # MW1 (virtual site)
    ])
    water_atom_names = ["OW", "HW1", "HW2", "MW"]
    water_nmolecules = 1
    
    # Combine
    positions = np.vstack([ice_positions, water_positions])
    atom_names = ice_atom_names + water_atom_names
    
    iface = InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=np.eye(3) * 3.0,
        ice_atom_count=ice_atom_count,
        water_atom_count=len(water_atom_names),
        ice_nmolecules=ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="test",
        report=""
    )
    
    # Should succeed
    ice_mol, water_mol, guest_mol = interface_to_vtk_molecules(iface)
    assert ice_mol.GetNumberOfAtoms() == 6
    assert ice_mol.GetNumberOfBonds() == 4  # 2 bonds per ice molecule
    assert water_mol.GetNumberOfAtoms() == 3  # MW skipped
    assert water_mol.GetNumberOfBonds() == 2  # 2 bonds for 1 water
    assert guest_mol is None  # No guests in this test


def test_interface_invalid_ice_ordering_detected():
    """Test that invalid ice atom ordering is detected."""
    # Invalid ice: H, O, H pattern
    ice_positions = np.array([
        [0.0, 0.0, 0.0],   # H (wrong!)
        [0.1, 0.0, 0.0],   # O (wrong!)
        [-0.1, 0.0, 0.0],  # H
    ])
    ice_atom_names = ["H", "O", "H"]  # Invalid
    ice_atom_count = 3
    ice_nmolecules = 1
    
    # Valid water
    water_positions = np.array([
        [2.0, 0.0, 0.0],
        [2.1, 0.0, 0.0],
        [1.9, 0.0, 0.0],
        [2.0, 0.0, 0.0],
    ])
    water_atom_names = ["OW", "HW1", "HW2", "MW"]
    water_nmolecules = 1
    
    positions = np.vstack([ice_positions, water_positions])
    atom_names = ice_atom_names + water_atom_names
    
    iface = InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=np.eye(3) * 3.0,
        ice_atom_count=ice_atom_count,
        water_atom_count=len(water_atom_names),
        ice_nmolecules=ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="test",
        report=""
    )
    
    # Should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        interface_to_vtk_molecules(iface)
    
    assert "Invalid ice atom ordering" in str(exc_info.value)


def test_interface_invalid_water_ordering_detected():
    """Test that invalid water atom ordering is detected."""
    # Valid ice
    ice_positions = np.array([
        [0.0, 0.0, 0.0],
        [0.1, 0.0, 0.0],
        [-0.1, 0.0, 0.0],
    ])
    ice_atom_names = ["O", "H", "H"]
    ice_atom_count = 3
    ice_nmolecules = 1
    
    # Invalid water: HW1, OW, HW2, MW (wrong order)
    water_positions = np.array([
        [2.0, 0.0, 0.0],   # HW1 (wrong!)
        [2.1, 0.0, 0.0],   # OW (wrong!)
        [1.9, 0.0, 0.0],   # HW2
        [2.0, 0.0, 0.0],   # MW
    ])
    water_atom_names = ["HW1", "OW", "HW2", "MW"]  # Invalid
    water_nmolecules = 1
    
    positions = np.vstack([ice_positions, water_positions])
    atom_names = ice_atom_names + water_atom_names
    
    iface = InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=np.eye(3) * 3.0,
        ice_atom_count=ice_atom_count,
        water_atom_count=len(water_atom_names),
        ice_nmolecules=ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="test",
        report=""
    )
    
    # Should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        interface_to_vtk_molecules(iface)
    
    assert "Invalid water atom ordering" in str(exc_info.value)


def test_interface_tip3p_style_water():
    """Test that TIP3P-style water (O, H, H) works if used for water region."""
    # Note: This is unlikely in practice (water region uses TIP4P from template),
    # but the code should handle it if provided
    
    # Valid ice
    ice_positions = np.array([
        [0.0, 0.0, 0.0],
        [0.1, 0.0, 0.0],
        [-0.1, 0.0, 0.0],
    ])
    ice_atom_names = ["O", "H", "H"]
    ice_atom_count = 3
    ice_nmolecules = 1
    
    # TIP3P-style water (O, H, H) - but with 4 atoms to match code expectations
    # The interface_to_vtk_molecules code expects 4 atoms per water (OW, HW1, HW2, MW)
    # If we provide O, H, H pattern, it should detect the mismatch
    water_positions = np.array([
        [2.0, 0.0, 0.0],   # O
        [2.1, 0.0, 0.0],   # H
        [1.9, 0.0, 0.0],   # H
        [2.0, 0.0, 0.0],   # MW (but TIP3P doesn't have MW!)
    ])
    water_atom_names = ["O", "H", "H", "MW"]  # Invalid - TIP3P + MW mix
    water_nmolecules = 1
    
    positions = np.vstack([ice_positions, water_positions])
    atom_names = ice_atom_names + water_atom_names
    
    iface = InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=np.eye(3) * 3.0,
        ice_atom_count=ice_atom_count,
        water_atom_count=len(water_atom_names),
        ice_nmolecules=ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="test",
        report=""
    )
    
    # Should raise ValueError - TIP3P water with MW doesn't make sense
    with pytest.raises(ValueError) as exc_info:
        interface_to_vtk_molecules(iface)
    
    assert "Invalid water atom ordering" in str(exc_info.value)


def test_interface_tip4p_hydrate():
    """Test that TIP4P hydrate (OW, HW1, HW2, MW) works for ice region."""
    # TIP4P hydrate uses OW, HW1, HW2, MW instead of classic ice O, H, H
    # Note: MW is skipped during rendering, so 3 visible atoms per molecule
    ice_positions = np.array([
        [0.0, 0.0, 0.0],   # OW
        [0.1, 0.0, 0.0],   # HW1
        [-0.1, 0.0, 0.0],  # HW2
        [0.0, 0.0, 0.0],   # MW (virtual site, skipped in rendering)
    ])
    ice_atom_names = ["OW", "HW1", "HW2", "MW"]  # TIP4P hydrate
    ice_atom_count = 4  # 4 atoms including MW
    ice_nmolecules = 1
    
    # Valid water (TIP4P style)
    water_positions = np.array([
        [2.0, 0.0, 0.0],
        [2.1, 0.0, 0.0],
        [1.9, 0.0, 0.0],
        [2.0, 0.0, 0.0],
    ])
    water_atom_names = ["OW", "HW1", "HW2", "MW"]
    water_nmolecules = 1
    
    positions = np.vstack([ice_positions, water_positions])
    atom_names = ice_atom_names + water_atom_names
    
    iface = InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=np.eye(3) * 3.0,
        ice_atom_count=ice_atom_count,
        water_atom_count=len(water_atom_names),
        ice_nmolecules=ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="test",
        report=""
    )
    
    # Should succeed - TIP4P hydrate is now supported
    ice_mol, water_mol, guest_mol = interface_to_vtk_molecules(iface)
    assert ice_mol.GetNumberOfAtoms() == 3  # MW skipped, 3 visible atoms
    assert ice_mol.GetNumberOfBonds() == 2  # 2 bonds per ice molecule
    assert water_mol.GetNumberOfAtoms() == 3  # MW skipped
    assert water_mol.GetNumberOfBonds() == 2  # 2 bonds for 1 water
    assert guest_mol is None  # No guests in this test