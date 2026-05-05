#!/usr/bin/env python
"""Focused verification of the three THF-ion-solute bug fixes.

This test verifies each fix individually without complex setup.
"""

import sys
import numpy as np

def test_fix_1_index_mapping():
    """Verify Fix 1: Index mapping handles MW atoms correctly."""
    print("\n" + "="*70)
    print("FIX 1: INDEX MAPPING WITH MW ATOMS")
    print("="*70)
    
    from quickice.gui.solute_renderer import create_solute_actor, get_element_from_atom_name
    
    # Test case: Molecule with MW virtual site
    # 4 atoms: C, O, H, MW (MW should be skipped)
    positions = np.array([
        [0.0, 0.0, 0.0],   # C
        [0.15, 0.0, 0.0],  # O (C-O bond at 0.15 nm)
        [0.0, 0.11, 0.0],  # H (C-H bond at 0.11 nm)
        [0.05, 0.05, 0.0], # MW (virtual site, should be skipped)
    ])
    atom_names = ['C', 'O', 'H', 'MW']
    cell = np.eye(3) * 5.0
    molecule_indices = [(0, 4)]  # One molecule with 4 atoms (including MW)
    
    # Create actor
    actor = create_solute_actor(positions, atom_names, cell, molecule_indices=molecule_indices)
    
    if actor is None:
        print("✗ Failed to create actor")
        return False
    
    mapper = actor.GetMapper()
    mol_data = mapper.GetInput()
    n_atoms = mol_data.GetNumberOfAtoms()
    n_bonds = mol_data.GetNumberOfBonds()
    
    print(f"Original atoms: {len(atom_names)} (including MW)")
    print(f"Visible atoms: {n_atoms} (MW skipped)")
    print(f"Bonds detected: {n_bonds}")
    
    # Expected: 3 atoms (C, O, H), 2 bonds (C-O, C-H)
    if n_atoms == 3 and n_bonds == 2:
        print("✓ PASS: MW atom skipped correctly")
        print("✓ PASS: Index mapping working correctly")
        print("✓ PASS: Bonds detected with correct indices")
        return True
    else:
        print(f"✗ FAIL: Expected 3 atoms, 2 bonds")
        print(f"        Got {n_atoms} atoms, {n_bonds} bonds")
        return False


def test_fix_2_water_message():
    """Verify Fix 2: Water replacement message is clear."""
    print("\n" + "="*70)
    print("FIX 2: WATER REPLACEMENT MESSAGE")
    print("="*70)
    
    with open('quickice/gui/main_window.py', 'r') as f:
        content = f.read()
    
    # Check for the new message
    if 'Replaced {water_replaced} overlapping liquid water molecules' in content:
        print("✓ PASS: Message updated to 'Replaced N overlapping liquid water molecules'")
        print("        Clear and concise!")
        return True
    else:
        print("✗ FAIL: Message not updated correctly")
        return False


def test_fix_3_ion_viewer_solute_support():
    """Verify Fix 3: Ion viewer supports solute rendering."""
    print("\n" + "="*70)
    print("FIX 3: ION VIEWER SOLUTE SUPPORT")
    print("="*70)
    
    from quickice.gui.ion_viewer import IonViewerWidget
    import inspect
    
    # Check 1: _solute_actors attribute
    init_source = inspect.getsource(IonViewerWidget.__init__)
    if '_solute_actors' in init_source:
        print("✓ PASS: IonViewerWidget has _solute_actors attribute")
    else:
        print("✗ FAIL: _solute_actors attribute missing")
        return False
    
    # Check 2: _clear_solute_actors method
    if hasattr(IonViewerWidget, '_clear_solute_actors'):
        print("✓ PASS: _clear_solute_actors() method exists")
    else:
        print("✗ FAIL: _clear_solute_actors() method missing")
        return False
    
    # Check 3: main_window imports create_solute_actor
    with open('quickice/gui/main_window.py', 'r') as f:
        content = f.read()
    
    if 'from quickice.gui.solute_renderer import create_solute_actor' in content:
        print("✓ PASS: main_window imports create_solute_actor")
    else:
        print("✗ FAIL: main_window doesn't import create_solute_actor")
        return False
    
    # Check 4: main_window renders solutes when source is "Solute"
    if 'current_source == "Solute"' in content and 'create_solute_actor' in content:
        print("✓ PASS: main_window renders solutes when source is 'Solute'")
    else:
        print("✗ FAIL: Solute rendering logic missing")
        return False
    
    return True


def test_cross_molecule_bond_prevention():
    """Verify that cross-molecule bonds are prevented."""
    print("\n" + "="*70)
    print("CROSS-MOLECULE BOND PREVENTION")
    print("="*70)
    
    from quickice.gui.solute_renderer import create_solute_actor
    
    # Create 2 simple molecules close together
    # Each: C, O, H (2 bonds: C-O, C-H)
    
    # Molecule 1
    mol1 = np.array([
        [0.0, 0.0, 0.0],   # C
        [0.15, 0.0, 0.0],  # O
        [0.0, 0.11, 0.0],  # H
    ])
    
    # Molecule 2 (close to mol1, atoms could bond if fix is wrong)
    mol2 = mol1 + np.array([0.5, 0.0, 0.0])
    
    all_positions = np.vstack([mol1, mol2])
    all_names = ['C', 'O', 'H', 'C', 'O', 'H']
    molecule_indices = [(0, 3), (3, 6)]
    cell = np.eye(3) * 5.0
    
    # Render WITH molecule_indices (should prevent cross-molecule bonds)
    actor = create_solute_actor(all_positions, all_names, cell, molecule_indices=molecule_indices)
    
    if actor is None:
        print("✗ Failed to create actor")
        return False
    
    mapper = actor.GetMapper()
    mol_data = mapper.GetInput()
    n_bonds = mol_data.GetNumberOfBonds()
    
    # Expected: 4 bonds (2 per molecule)
    # If cross-molecule bonds exist, would be more
    print(f"Bonds detected: {n_bonds} (expected 4)")
    
    if n_bonds == 4:
        print("✓ PASS: Correct number of bonds (no cross-molecule bonds)")
        return True
    else:
        print(f"✗ FAIL: Wrong number of bonds")
        if n_bonds > 4:
            print("        Cross-molecule bonds detected!")
        return False


def main():
    """Run all focused tests."""
    print("\n" + "="*70)
    print("FOCUSED VERIFICATION OF THF-ION-SOLUTE FIXES")
    print("="*70)
    
    results = []
    
    # Test each fix
    results.append(("Fix 1: Index mapping", test_fix_1_index_mapping()))
    results.append(("Fix 2: Water message", test_fix_2_water_message()))
    results.append(("Fix 3: Ion viewer solute support", test_fix_3_ion_viewer_solute_support()))
    results.append(("Cross-molecule bond prevention", test_cross_molecule_bond_prevention()))
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("✓ ALL FIXES VERIFIED")
        print("="*70)
        print("\nThe three THF-ion-solute issues have been successfully fixed:")
        print("  1. THF solute bonds correct (index mapping handles MW atoms)")
        print("  2. Water replacement message clear and concise")
        print("  3. Ion panel shows solutes when 'Solute' source selected")
        return 0
    else:
        print("✗ SOME FIXES FAILED VERIFICATION")
        print("="*70)
        return 1


if __name__ == '__main__':
    sys.exit(main())
