#!/usr/bin/env python
"""Test that cross-molecule bonds are prevented.

This test verifies the CRITICAL fix: when multiple molecules are rendered,
bonds should ONLY be detected within each molecule, NOT across molecules.
"""

import numpy as np
from quickice.gui.solute_renderer import create_solute_actor, get_element_from_atom_name


def test_no_cross_molecule_bonds():
    """Test that bonds are NOT created between different molecules."""
    print("\n" + "="*70)
    print("CROSS-MOLECULE BOND PREVENTION TEST")
    print("="*70)
    
    # Create 2 molecules that are CLOSE TOGETHER
    # If the fix is wrong, bonds will be created between them
    # If the fix is correct, bonds will only be within each molecule
    
    # Molecule 1: Simple 4-atom molecule (C, O, H, H)
    # Bonds: C-O, C-H, C-H (3 bonds)
    mol1_positions = np.array([
        [0.0, 0.0, 0.0],   # C at origin
        [0.15, 0.0, 0.0],  # O at 0.15 nm (C-O bond)
        [0.0, 0.11, 0.0],  # H at 0.11 nm (C-H bond)
        [0.0, -0.11, 0.0], # H at 0.11 nm (C-H bond)
    ])
    mol1_names = ['C', 'O', 'H', 'H']
    
    # Molecule 2: Same structure, translated to be CLOSE to molecule 1
    # Place it very close (0.5 nm away) - close enough that atoms from
    # different molecules could bond if the fix is wrong
    translation = np.array([0.5, 0.0, 0.0])
    mol2_positions = mol1_positions + translation
    mol2_names = mol1_names.copy()
    
    # Combine
    all_positions = np.vstack([mol1_positions, mol2_positions])
    all_names = mol1_names + mol2_names
    
    # Molecule indices: two molecules, 4 atoms each
    molecule_indices = [(0, 4), (4, 8)]
    
    print(f"Two molecules, 4 atoms each, placed 0.5 nm apart")
    print(f"Molecule 1: atoms 0-3 at x=0")
    print(f"Molecule 2: atoms 4-7 at x=0.5")
    print(f"\nMolecule indices: {molecule_indices}")
    
    # Create actor WITH molecule_indices
    cell = np.eye(3) * 5.0
    print("\nRendering WITH molecule_indices...")
    actor = create_solute_actor(all_positions, all_names, cell, molecule_indices=molecule_indices)
    
    if actor is None:
        print("✗ Failed to create actor")
        return False
    
    mapper = actor.GetMapper()
    mol_data = mapper.GetInput()
    n_atoms = mol_data.GetNumberOfAtoms()
    n_bonds = mol_data.GetNumberOfBonds()
    
    print(f"  Atoms: {n_atoms}")
    print(f"  Bonds: {n_bonds}")
    
    # Each molecule should have 3 bonds
    # Total: 6 bonds (3 per molecule)
    expected_bonds = 6
    
    if n_bonds == expected_bonds:
        print(f"✓ Correct number of bonds: {n_bonds} (expected {expected_bonds})")
        print("✓ Bonds detected ONLY within each molecule")
        print("✓ NO cross-molecule bonds created")
        correct_bonds = True
    else:
        print(f"✗ Wrong number of bonds: {n_bonds} (expected {expected_bonds})")
        if n_bonds > expected_bonds:
            print("✗ Too many bonds - may have cross-molecule bonding!")
        correct_bonds = False
    
    # Now test WITHOUT molecule_indices (should detect cross-molecule bonds)
    print("\n" + "-"*70)
    print("Control test: Rendering WITHOUT molecule_indices")
    print("This should detect bonds between molecules (WRONG behavior)")
    print("-"*70)
    
    actor_no_indices = create_solute_actor(all_positions, all_names, cell, molecule_indices=None)
    
    if actor_no_indices is None:
        print("✗ Failed to create actor")
        return False
    
    mapper_no = actor_no_indices.GetMapper()
    mol_data_no = mapper_no.GetInput()
    n_bonds_no = mol_data_no.GetNumberOfBonds()
    
    print(f"  Bonds without molecule_indices: {n_bonds_no}")
    
    if n_bonds_no > expected_bonds:
        print(f"✓ Control test passed: {n_bonds_no} bonds detected (more than {expected_bonds})")
        print("  This shows that WITHOUT molecule_indices, cross-molecule bonds ARE created")
        print("  This confirms the molecule_indices fix is working correctly!")
    
    print("\n" + "="*70)
    print("RESULT")
    print("="*70)
    
    if correct_bonds:
        print("✓ PASS: molecule_indices correctly prevents cross-molecule bonds")
        return True
    else:
        print("✗ FAIL: Cross-molecule bonds detected")
        return False


def test_thf_no_cross_bonds():
    """Test that THF molecules don't have cross-molecule bonds."""
    print("\n" + "="*70)
    print("THF CROSS-MOLECULE BOND TEST")
    print("="*70)
    
    # Create simplified THF-like molecules (no MW for simplicity)
    # THF: O, CA, CA, CB, CB, H, H, H, H, H, H, H, H (13 atoms)
    # We'll use a simplified version with just a few atoms
    
    # Molecule 1: O, C, C, H (3 bonds)
    mol1_positions = np.array([
        [0.0, 0.0, 0.0],   # O
        [0.14, 0.0, 0.0],  # C (O-C bond)
        [0.29, 0.0, 0.0],  # C (C-C bond)
        [0.14, 0.11, 0.0], # H (C-H bond)
    ])
    mol1_names = ['O', 'C', 'C', 'H']
    
    # Molecule 2: Same, translated close
    translation = np.array([0.6, 0.0, 0.0])
    mol2_positions = mol1_positions + translation
    mol2_names = mol1_names.copy()
    
    # Combine
    all_positions = np.vstack([mol1_positions, mol2_positions])
    all_names = mol1_names + mol2_names
    molecule_indices = [(0, 4), (4, 8)]
    
    print(f"Two THF-like molecules, 4 atoms each, 0.6 nm apart")
    print(f"Molecule indices: {molecule_indices}")
    
    # Create actor
    cell = np.eye(3) * 5.0
    actor = create_solute_actor(all_positions, all_names, cell, molecule_indices=molecule_indices)
    
    if actor is None:
        print("✗ Failed to create actor")
        return False
    
    mapper = actor.GetMapper()
    mol_data = mapper.GetInput()
    n_bonds = mol_data.GetNumberOfBonds()
    
    expected_bonds = 6  # 3 bonds per molecule
    
    print(f"  Atoms: {mol_data.GetNumberOfAtoms()}")
    print(f"  Bonds: {n_bonds}")
    
    if n_bonds == expected_bonds:
        print(f"✓ Correct: {n_bonds} bonds (no cross-molecule bonds)")
        return True
    else:
        print(f"✗ Wrong: {n_bonds} bonds (expected {expected_bonds})")
        return False


if __name__ == '__main__':
    test1 = test_no_cross_molecule_bonds()
    test2 = test_thf_no_cross_bonds()
    
    print("\n" + "="*70)
    if test1 and test2:
        print("✓ ALL TESTS PASSED")
        print("✓ Cross-molecule bonds correctly prevented")
        exit(0)
    else:
        print("✗ TESTS FAILED")
        exit(1)
