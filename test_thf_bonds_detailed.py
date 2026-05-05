#!/usr/bin/env python
"""Test THF bond detection with realistic THF coordinates.

This test creates a realistic THF molecule and verifies that bonds are detected correctly.
"""

import numpy as np
from quickice.gui.solute_renderer import create_solute_actor, get_element_from_atom_name


def test_thf_bond_detection():
    """Test THF bond detection with realistic coordinates."""
    print("\n" + "="*70)
    print("THF BOND DETECTION TEST")
    print("="*70)
    
    # Realistic THF coordinates (approximate, in nm)
    # THF is a 5-membered ring: C-C-C-O-C
    # Each C has 2 H atoms (except some have different numbers)
    # Total: 4 C atoms + 1 O atom + 8 H atoms + 1 MW virtual site = 14 atoms
    
    # Approximate THF ring coordinates (in nm)
    # Ring is planar-ish, ~0.15 nm C-C bond length
    c1 = np.array([0.0, 0.0, 0.0])
    c2 = np.array([0.15, 0.0, 0.0])
    c3 = np.array([0.22, 0.14, 0.0])
    o = np.array([0.10, 0.22, 0.0])
    c4 = np.array([-0.02, 0.14, 0.0])
    
    # H atoms attached to each C (approximate positions)
    # H-C bonds ~0.11 nm
    h1a = c1 + np.array([0.0, -0.11, 0.0])
    h1b = c1 + np.array([-0.08, 0.08, 0.0])
    
    h2a = c2 + np.array([0.0, -0.11, 0.0])
    h2b = c2 + np.array([0.11, 0.0, 0.0])
    
    h3a = c3 + np.array([0.0, 0.0, 0.11])
    h3b = c3 + np.array([0.0, 0.0, -0.11])
    
    h4a = c4 + np.array([-0.11, 0.0, 0.0])
    h4b = c4 + np.array([0.0, 0.0, 0.11])
    
    # MW virtual site (positioned near oxygen)
    mw = o + np.array([0.0, 0.05, 0.0])
    
    # Assemble positions (THF atom order: C1, C2, C3, C4, O, H1, H2, H3, H4, H5, H6, H7, H8, MW)
    positions = np.array([
        c1, c2, c3, c4, o,  # Ring atoms
        h1a, h1b, h2a, h2b, h3a, h3b, h4a, h4b,  # H atoms
        mw  # Virtual site
    ])
    
    # Atom names
    atom_names = ['C1', 'C2', 'C3', 'C4', 'O', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'H7', 'H8', 'MW']
    
    # Cell (large enough to contain THF)
    cell = np.eye(3) * 5.0  # 5 nm box
    
    # Molecule indices: one THF molecule with 14 atoms
    molecule_indices = [(0, 14)]
    
    print(f"THF molecule: {len(atom_names)} atoms")
    print(f"Atom names: {atom_names}")
    
    # Check which atoms will be visible
    visible_atoms = []
    for i, name in enumerate(atom_names):
        elem = get_element_from_atom_name(name)
        if elem is not None:
            visible_atoms.append(i)
    
    print(f"\nVisible atoms (excluding MW): {len(visible_atoms)}")
    print(f"Visible indices: {visible_atoms}")
    
    # Create actor with molecule_indices
    print("\nCreating solute actor with molecule_indices...")
    actor = create_solute_actor(positions, atom_names, cell, molecule_indices=molecule_indices)
    
    if actor is None:
        print("✗ Failed to create actor")
        return False
    
    print("✓ Actor created")
    
    # Check the VTK molecule
    mapper = actor.GetMapper()
    mol_data = mapper.GetInput()
    n_atoms = mol_data.GetNumberOfAtoms()
    n_bonds = mol_data.GetNumberOfBonds()
    
    print(f"\nVTK molecule:")
    print(f"  Atoms: {n_atoms} (expected 13, excluding MW)")
    print(f"  Bonds: {n_bonds}")
    
    # Expected bonds for THF:
    # Ring bonds: C1-C2, C2-C3, C3-O, O-C4, C4-C1 (5 bonds)
    # H-C bonds: 2 per C = 8 bonds
    # Total: 13 bonds
    
    expected_bonds = 13
    
    if n_atoms == 13:
        print("✓ Correct number of atoms (MW excluded)")
    else:
        print(f"✗ Wrong number of atoms: {n_atoms} (expected 13)")
        return False
    
    if n_bonds == expected_bonds:
        print(f"✓ Correct number of bonds: {n_bonds} (expected {expected_bonds})")
        print("  Ring bonds: 5 (C1-C2, C2-C3, C3-O, O-C4, C4-C1)")
        print("  H-C bonds: 8 (2 H per C atom)")
        return True
    else:
        print(f"✗ Wrong number of bonds: {n_bonds} (expected {expected_bonds})")
        print("  Note: Bond detection uses 0.16 nm threshold")
        print("  If bonds are wrong, check if THF coordinates are realistic")
        return False


def test_multiple_thf_molecules():
    """Test multiple THF molecules with correct bond detection."""
    print("\n" + "="*70)
    print("MULTIPLE THF MOLECULES TEST")
    print("="*70)
    
    # Create 2 THF molecules
    # Each has 14 atoms (including MW)
    
    # THF 1 coordinates
    thf1_atoms = [
        ('C1', np.array([0.0, 0.0, 0.0])),
        ('C2', np.array([0.15, 0.0, 0.0])),
        ('C3', np.array([0.22, 0.14, 0.0])),
        ('C4', np.array([-0.02, 0.14, 0.0])),
        ('O', np.array([0.10, 0.22, 0.0])),
        ('H1', np.array([0.0, -0.11, 0.0])),
        ('H2', np.array([-0.08, 0.08, 0.0])),
        ('H3', np.array([0.0, -0.11, 0.0]) + np.array([0.15, 0.0, 0.0])),
        ('H4', np.array([0.11, 0.0, 0.0]) + np.array([0.15, 0.0, 0.0])),
        ('H5', np.array([0.0, 0.0, 0.11]) + np.array([0.22, 0.14, 0.0])),
        ('H6', np.array([0.0, 0.0, -0.11]) + np.array([0.22, 0.14, 0.0])),
        ('H7', np.array([-0.11, 0.0, 0.0]) + np.array([-0.02, 0.14, 0.0])),
        ('H8', np.array([0.0, 0.0, 0.11]) + np.array([-0.02, 0.14, 0.0])),
        ('MW', np.array([0.10, 0.27, 0.0])),
    ]
    
    # THF 2 coordinates (translated)
    translation = np.array([1.0, 1.0, 1.0])
    thf2_atoms = [(name, pos + translation) for name, pos in thf1_atoms]
    
    # Combine
    all_names = [name for name, pos in thf1_atoms] + [name for name, pos in thf2_atoms]
    all_positions = np.array([pos for name, pos in thf1_atoms] + [pos for name, pos in thf2_atoms])
    
    # Molecule indices
    molecule_indices = [(0, 14), (14, 28)]
    
    print(f"Total atoms: {len(all_names)}")
    print(f"Molecule indices: {molecule_indices}")
    
    # Create actor
    cell = np.eye(3) * 5.0
    actor = create_solute_actor(all_positions, all_names, cell, molecule_indices=molecule_indices)
    
    if actor is None:
        print("✗ Failed to create actor")
        return False
    
    mapper = actor.GetMapper()
    mol_data = mapper.GetInput()
    n_atoms = mol_data.GetNumberOfAtoms()
    n_bonds = mol_data.GetNumberOfBonds()
    
    print(f"\nVTK molecule:")
    print(f"  Atoms: {n_atoms} (expected 26, 2 THF x 13 visible atoms)")
    print(f"  Bonds: {n_bonds} (expected 26, 2 THF x 13 bonds)")
    
    # Each THF has 13 visible atoms and 13 bonds
    if n_atoms == 26 and n_bonds == 26:
        print("✓ Multiple THF molecules rendered correctly")
        print("✓ Bonds detected WITHIN each molecule (no cross-molecule bonds)")
        return True
    else:
        print(f"✗ Incorrect rendering")
        print(f"  Expected: 26 atoms, 26 bonds")
        print(f"  Got: {n_atoms} atoms, {n_bonds} bonds")
        if n_bonds > 26:
            print("  ⚠ Too many bonds - possible cross-molecule bonding!")
        return False


if __name__ == '__main__':
    print("\n" + "="*70)
    print("DETAILED THF BOND DETECTION VERIFICATION")
    print("="*70)
    
    test1 = test_thf_bond_detection()
    test2 = test_multiple_thf_molecules()
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if test1 and test2:
        print("✓ ALL TESTS PASSED")
        print("✓ THF bond detection working correctly")
        print("✓ Index mapping with MW atoms is correct")
        exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        exit(1)
