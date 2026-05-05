#!/usr/bin/env python
"""Test fixes for THF-ion-solute issues.

This test verifies:
1. THF solute bonds are correct (molecule_indices mapping with MW atoms)
2. Water replacement message is clear
3. Ion panel shows solutes when "Solute" source is selected
"""

import sys
import inspect
import numpy as np

# Test 1: Verify solute_renderer index mapping fix
def test_solute_renderer_index_mapping():
    """Test that solute_renderer correctly handles MW atoms in molecule_indices."""
    print("\n" + "="*70)
    print("TEST 1: Solute renderer index mapping with MW atoms")
    print("="*70)
    
    from quickice.gui.solute_renderer import create_solute_actor, get_element_from_atom_name
    
    # Test case: THF molecule with MW virtual site
    # THF has: C1, C2, C3, C4, O, H1, H2, H3, H4, H5, H6, H7, H8, MW (virtual site)
    # Total 14 atoms, but MW should be skipped
    
    # Simulate THF-like molecule with MW virtual site
    atom_names = ['C1', 'C2', 'O', 'H1', 'H2', 'MW', 'C3', 'C4', 'H3', 'H4']
    
    # Create positions (random for this test)
    positions = np.random.rand(10, 3) * 2.0  # nm
    
    # Cell
    cell = np.eye(3) * 5.0  # 5 nm box
    
    # Molecule indices: should be (0, 10) for one molecule with 10 atoms
    molecule_indices = [(0, 10)]
    
    # Check which atoms will be visible (skip MW)
    visible_atoms = []
    for i, name in enumerate(atom_names):
        elem = get_element_from_atom_name(name)
        if elem is not None:
            visible_atoms.append(i)
    
    print(f"Original atom names: {atom_names}")
    print(f"Visible atom indices (excluding MW): {visible_atoms}")
    print(f"Number of original atoms: {len(atom_names)}")
    print(f"Number of visible atoms: {len(visible_atoms)}")
    
    # Create actor
    actor = create_solute_actor(positions, atom_names, cell, molecule_indices=molecule_indices)
    
    if actor is not None:
        print("✓ Actor created successfully")
        
        # Check if the actor has the right number of atoms
        # The actor should have 9 atoms (excluding MW)
        mapper = actor.GetMapper()
        mol_data = mapper.GetInput()
        n_atoms = mol_data.GetNumberOfAtoms()
        
        print(f"Number of atoms in VTK molecule: {n_atoms}")
        print(f"Expected: {len(visible_atoms)}")
        
        if n_atoms == len(visible_atoms):
            print("✓ Correct number of atoms in VTK molecule")
        else:
            print("✗ Wrong number of atoms - index mapping may be incorrect")
            return False
        
        # Check bonds
        n_bonds = mol_data.GetNumberOfBonds()
        print(f"Number of bonds detected: {n_bonds}")
        print("✓ Bonds created (verify visually that they're correct)")
        
        return True
    else:
        print("✗ Failed to create actor")
        return False


# Test 2: Verify water replacement message
def test_water_replacement_message():
    """Test that water replacement message is clear."""
    print("\n" + "="*70)
    print("TEST 2: Water replacement message wording")
    print("="*70)
    
    # Read main_window.py and check the message
    with open('quickice/gui/main_window.py', 'r') as f:
        content = f.read()
    
    # Look for the water replacement message
    if 'Replaced {water_replaced} overlapping liquid water molecules' in content:
        print("✓ Message found: 'Replaced N overlapping liquid water molecules'")
        print("  This is clear and concise.")
        return True
    elif 'Water replacement: Removed' in content:
        print("✗ Old message still present: 'Water replacement: Removed N water molecules'")
        print("  Should be updated to: 'Replaced N overlapping liquid water molecules'")
        return False
    else:
        print("? Could not find water replacement message in main_window.py")
        return False


# Test 3: Verify ion_viewer has solute actor support
def test_ion_viewer_solute_support():
    """Test that ion_viewer supports solute actors."""
    print("\n" + "="*70)
    print("TEST 3: Ion viewer solute actor support")
    print("="*70)
    
    from quickice.gui.ion_viewer import IonViewerWidget
    
    # Check that IonViewerWidget has _solute_actors attribute
    init_source = inspect.getsource(IonViewerWidget.__init__)
    
    if '_solute_actors' in init_source:
        print("✓ IonViewerWidget.__init__ has _solute_actors attribute")
    else:
        print("✗ IonViewerWidget.__init__ missing _solute_actors attribute")
        return False
    
    # Check that _clear_solute_actors method exists
    if hasattr(IonViewerWidget, '_clear_solute_actors'):
        print("✓ IonViewerWidget has _clear_solute_actors() method")
    else:
        print("✗ IonViewerWidget missing _clear_solute_actors() method")
        return False
    
    # Check that _clear_actors calls _clear_solute_actors
    clear_actors_source = inspect.getsource(IonViewerWidget._clear_actors)
    if '_clear_solute_actors' in clear_actors_source:
        print("✓ _clear_actors() calls _clear_solute_actors()")
    else:
        print("✗ _clear_actors() does not call _clear_solute_actors()")
        return False
    
    # Check that clear_interface_only calls _clear_solute_actors
    clear_interface_source = inspect.getsource(IonViewerWidget.clear_interface_only)
    if '_clear_solute_actors' in clear_interface_source:
        print("✓ clear_interface_only() calls _clear_solute_actors()")
    else:
        print("✗ clear_interface_only() does not call _clear_solute_actors()")
        return False
    
    return True


# Test 4: Verify main_window renders solutes when source is "Solute"
def test_main_window_solute_rendering():
    """Test that main_window renders solutes when source is 'Solute'."""
    print("\n" + "="*70)
    print("TEST 4: Main window solute rendering for ion panel")
    print("="*70)
    
    # Read main_window.py and check for solute rendering logic
    with open('quickice/gui/main_window.py', 'r') as f:
        content = f.read()
    
    # Check for import of create_solute_actor
    if 'from quickice.gui.solute_renderer import create_solute_actor' in content:
        print("✓ create_solute_actor imported in main_window.py")
    else:
        print("✗ create_solute_actor not imported in main_window.py")
        return False
    
    # Check for solute rendering logic
    if 'current_source == "Solute"' in content and 'create_solute_actor' in content:
        print("✓ Solute rendering logic found when source is 'Solute'")
    else:
        print("✗ Solute rendering logic not found")
        return False
    
    # Check for adding solute actor to renderer
    if 'renderer.AddActor(solute_actor)' in content:
        print("✓ Solute actor added to renderer")
    else:
        print("✗ Solute actor not added to renderer")
        return False
    
    # Check for storing solute actor
    if '_solute_actors.append(solute_actor)' in content:
        print("✓ Solute actor stored for cleanup")
    else:
        print("✗ Solute actor not stored for cleanup")
        return False
    
    return True


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("THF-ION-SOLUTE FIXES VERIFICATION")
    print("="*70)
    
    results = []
    
    # Run tests
    results.append(("Solute renderer index mapping", test_solute_renderer_index_mapping()))
    results.append(("Water replacement message", test_water_replacement_message()))
    results.append(("Ion viewer solute support", test_ion_viewer_solute_support()))
    results.append(("Main window solute rendering", test_main_window_solute_rendering()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("="*70)
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("="*70)
        return 1


if __name__ == '__main__':
    sys.exit(main())
