"""Test THF bond creation in interface_to_vtk_molecules.

This test verifies that the fix for THF missing bonds works correctly.
"""

import numpy as np
from quickice.gui.vtk_utils import interface_to_vtk_molecules, _count_guest_atoms_for_rendering
from quickice.structure_generation.types import InterfaceStructure


def test_count_guest_atoms_for_thf():
    """Test that _count_guest_atoms_for_rendering correctly counts THF atoms."""
    # Single THF molecule (13 atoms): O, CA, CA, CB, CB, + 8H
    thf_atoms = ["O", "CA", "CA", "CB", "CB"] + ["H"] * 8
    
    count = _count_guest_atoms_for_rendering(thf_atoms, 0)
    assert count == 13, f"Expected 13 atoms for single THF, got {count}"
    print(f"✓ Single THF: {count} atoms (expected 13)")
    
    # Two THF molecules followed by water
    two_thf_plus_water = (
        ["O", "CA", "CA", "CB", "CB"] + ["H"] * 8 +  # First THF
        ["O", "CA", "CA", "CB", "CB"] + ["H"] * 8 +  # Second THF
        ["OW", "HW1", "HW2", "MW"]  # Water molecule
    )
    
    # Count first THF
    count1 = _count_guest_atoms_for_rendering(two_thf_plus_water, 0)
    assert count1 == 13, f"Expected 13 atoms for first THF, got {count1}"
    print(f"✓ First THF in sequence: {count1} atoms (expected 13)")
    
    # Count second THF (starts at index 13)
    count2 = _count_guest_atoms_for_rendering(two_thf_plus_water, 13)
    assert count2 == 13, f"Expected 13 atoms for second THF, got {count2}"
    print(f"✓ Second THF in sequence: {count2} atoms (expected 13)")
    
    print("\n✓ All _count_guest_atoms_for_rendering tests passed!")


def test_thf_bonds_in_interface():
    """Test that THF bonds are created correctly in interface_to_vtk_molecules."""
    # Create a mock InterfaceStructure with:
    # - 1 water molecule (ice, 3 atoms)
    # - 2 THF molecules (guests, 26 atoms total)
    # - 1 water molecule (water box, 4 atoms)
    
    # Ice: 1 water molecule (O, H, H)
    ice_positions = np.array([
        [0.0, 0.0, 0.0],  # O
        [0.1, 0.0, 0.0],  # H
        [-0.1, 0.0, 0.0], # H
    ])
    ice_names = ["O", "H", "H"]
    
    # THF 1: 13 atoms
    thf1_positions = np.array([
        [1.0, 0.0, 0.0],   # O
        [1.1, 0.1, 0.0],   # CA
        [1.1, -0.1, 0.0],  # CA
        [1.2, 0.15, 0.0],  # CB
        [1.2, -0.15, 0.0], # CB
        [1.05, 0.15, 0.0], # H
        [1.05, -0.15, 0.0],# H
        [1.25, 0.2, 0.0],  # H
        [1.25, -0.2, 0.0], # H
        [1.15, 0.25, 0.0], # H
        [1.15, -0.25, 0.0],# H
        [1.3, 0.1, 0.0],   # H
        [1.3, -0.1, 0.0],  # H
    ])
    thf1_names = ["O", "CA", "CA", "CB", "CB"] + ["H"] * 8
    
    # THF 2: 13 atoms (offset by 2nm)
    thf2_positions = thf1_positions + np.array([3.0, 0.0, 0.0])
    thf2_names = thf1_names.copy()
    
    # Water: 1 TIP4P molecule (OW, HW1, HW2, MW)
    water_positions = np.array([
        [5.0, 0.0, 0.0],  # OW
        [5.1, 0.0, 0.0],  # HW1
        [4.9, 0.0, 0.0],  # HW2
        [5.0, 0.0, 0.0],  # MW (virtual site, same as OW)
    ])
    water_names = ["OW", "HW1", "HW2", "MW"]
    
    # Combine all atoms
    all_positions = np.vstack([ice_positions, thf1_positions, thf2_positions, water_positions])
    all_names = ice_names + thf1_names + thf2_names + water_names
    
    # Create InterfaceStructure
    iface = InterfaceStructure(
        positions=all_positions,
        atom_names=all_names,
        cell=np.diag([10.0, 10.0, 10.0]),
        ice_atom_count=3,  # 1 ice water molecule
        water_atom_count=4,  # 1 water box molecule
        ice_nmolecules=1,
        water_nmolecules=1,
        mode="slab",
        report="Test interface",
        guest_atom_count=26,  # 2 THF molecules
        guest_nmolecules=2,
    )
    
    # Convert to VTK molecules
    ice_mol, water_mol, guest_mol = interface_to_vtk_molecules(iface)
    
    # Check guest molecule
    assert guest_mol is not None, "guest_mol should not be None"
    
    n_guest_atoms = guest_mol.GetNumberOfAtoms()
    n_guest_bonds = guest_mol.GetNumberOfBonds()
    
    print(f"\nGuest molecule stats:")
    print(f"  Atoms: {n_guest_atoms} (expected 26)")
    print(f"  Bonds: {n_guest_bonds}")
    
    # THF should have bonds:
    # - Ring bonds: O-CB (2), CA-CA (1), CA-CB (2) = 5 ring bonds
    # - C-H bonds: ~8 C-H bonds (depends on hydrogen positions)
    # Total: should have at least 10 bonds per THF
    # For 2 THF: at least 20 bonds
    
    assert n_guest_bonds > 0, f"Expected bonds to be created, but got 0 bonds!"
    assert n_guest_bonds >= 20, f"Expected at least 20 bonds for 2 THF molecules, got {n_guest_bonds}"
    
    print(f"\n✓ THF bonds created successfully! {n_guest_bonds} bonds for 2 THF molecules")
    print(f"✓ Fix verified!")


if __name__ == "__main__":
    test_count_guest_atoms_for_thf()
    test_thf_bonds_in_interface()
