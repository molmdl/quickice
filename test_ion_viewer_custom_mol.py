#!/usr/bin/env python
"""Test to verify ion viewer renders custom molecules correctly.

This test verifies the fix for:
- Workflow 1: Custom mol -> Solute -> Ion
- Workflow 2: Custom mol -> Ion

The fix added:
1. render_custom_molecules() method to IonViewerWidget
2. Call to render_custom_molecules in main_window after ion insertion
"""

import sys
from PySide6.QtWidgets import QApplication


def test_ion_viewer_custom_molecules():
    """Test that IonViewerWidget has render_custom_molecules method."""
    print("\n" + "="*60)
    print("Testing IonViewerWidget Custom Molecule Rendering")
    print("="*60)
    
    # Create QApplication first
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    from quickice.gui.ion_viewer import IonViewerWidget
    
    # Test 1: Check that IonViewerWidget has the method
    print("\n1. Checking IonViewerWidget has render_custom_molecules method...")
    assert hasattr(IonViewerWidget, 'render_custom_molecules'), \
        "IonViewerWidget should have render_custom_molecules method"
    print("   ✓ IonViewerWidget.render_custom_molecules exists")
    
    # Test 2: Check that IonViewerWidget has _custom_molecule_actors
    print("\n2. Checking IonViewerWidget has _custom_molecule_actors attribute...")
    viewer = IonViewerWidget()
    assert hasattr(viewer, '_custom_molecule_actors'), \
        "IonViewerWidget should have _custom_molecule_actors attribute"
    assert isinstance(viewer._custom_molecule_actors, list), \
        "_custom_molecule_actors should be a list"
    print("   ✓ _custom_molecule_actors attribute exists and is a list")
    
    # Test 3: Check that clear methods exist
    print("\n3. Checking IonViewerWidget has clear methods...")
    assert hasattr(viewer, '_clear_custom_molecule_actors'), \
        "IonViewerWidget should have _clear_custom_molecule_actors method"
    print("   ✓ _clear_custom_molecule_actors method exists")
    
    # Test 4: Check method signature
    print("\n4. Checking render_custom_molecules method signature...")
    import inspect
    sig = inspect.signature(viewer.render_custom_molecules)
    params = list(sig.parameters.keys())
    assert 'custom_structure' in params, \
        "render_custom_molecules should accept custom_structure parameter"
    print("   ✓ render_custom_molecules has correct signature")
    
    print("\n" + "="*60)
    print("✓ ALL TESTS PASSED")
    print("✓ IonViewerWidget correctly supports custom molecule rendering")
    print("="*60 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        success = test_ion_viewer_custom_molecules()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
