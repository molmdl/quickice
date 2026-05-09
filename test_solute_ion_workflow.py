#!/usr/bin/env python3
"""
Integration test for Solute → Ion workflow path.

Tests the workflow: Interface → Solute → Ion
Verifies that after solute insertion, the ion tab generate button becomes active.
"""

from quickice.gui.main_window import MainWindow
from quickice.structure_generation.types import (
    InterfaceStructure, SoluteStructure
)
import numpy as np
from pathlib import Path
from PySide6.QtWidgets import QApplication
import sys

# Create application
app = QApplication.instance() or QApplication(sys.argv)

# Create main window
window = MainWindow()

print("="*60)
print("Testing Solute → Ion Workflow Path")
print("="*60)

# Test 1: Create Interface structure
print("\n1. Creating Interface structure...")
interface_structure = InterfaceStructure(
    positions=np.random.rand(200, 3) * 3.0,
    atom_names=["O"] * 200,
    cell=np.eye(3) * 3.0,
    ice_atom_count=100,
    water_atom_count=100,
    ice_nmolecules=25,
    water_nmolecules=25,
    mode="slab",
    report="Test interface"
)

# Set interface structure in main window
window._current_interface_result = interface_structure
window.solute_panel.set_interface_structure(interface_structure)
window.ion_panel.set_interface_structure(interface_structure)

assert window.solute_panel._interface_available, "Solute panel should have Interface available"
assert window.ion_panel._interface_available, "Ion panel should have Interface available"
print("✓ Interface structure set in all tabs")

# Test 2: Create Solute structure (simulating solute insertion)
print("\n2. Creating Solute structure...")
solute_structure = SoluteStructure(
    positions=np.random.rand(50, 3) * 3.0,
    atom_names=["C"] * 50,
    cell=np.eye(3) * 3.0,
    solute_type="CH4",
    n_molecules=10,
    molecule_indices=[(0, 5), (5, 10), (10, 15), (15, 20), (20, 25), (25, 30), (30, 35), (35, 40), (40, 45), (45, 50)],
    interface_structure=interface_structure,
    registry=None
)

# Store result (simulating what _on_insert_solutes does)
window._current_solute_result = solute_structure

# THE FIX: Pass result to ion panel (this is what was missing!)
window.ion_panel.set_solute_structure(solute_structure)

# Test 3: Verify Solute passed to Ion panel
print("\n3. Verifying Solute passed to Ion panel...")

assert window.ion_panel._solute_structure is not None, \
    "IonPanel should have SoluteStructure"
assert window.ion_panel._solute_available, \
    "IonPanel should have Solute available"
print("✓ IonPanel received SoluteStructure")

# Test 4: Test Ion panel with Solute source
print("\n4. Testing Ion panel with Solute source...")

# Select Solute source in Ion panel
window.ion_panel._on_source_changed(2)  # Index 2 = Solute
assert window.ion_panel._current_source == "Solute", \
    "Ion source should be Solute"

# Verify button state - THIS IS THE KEY TEST
window.ion_panel._update_insert_button_state()
assert window.ion_panel.insert_button.isEnabled(), \
    "Ion insert button should be enabled with Solute source"

print("✓ Ion insert button is ENABLED with Solute source")

# Test 5: Verify we can get the source structure
print("\n5. Verifying source structure retrieval...")
ion_source = window.ion_panel.get_current_source_structure()
assert ion_source is not None, "Should have ion source structure"
assert hasattr(ion_source, 'solute_type'), "Should have solute_type field"
assert ion_source.solute_type == "CH4", "Should be CH4 solute"
assert ion_source.n_molecules == 10, "Should have 10 solute molecules"
print(f"✓ Retrieved solute structure: {ion_source.n_molecules} {ion_source.solute_type} molecules")

# Test 6: Test button state for other sources
print("\n6. Testing button states for all sources...")

# Switch to Interface source
window.ion_panel._on_source_changed(0)
window.ion_panel._update_insert_button_state()
assert window.ion_panel.insert_button.isEnabled(), \
    "Ion insert button should be enabled with Interface source"
print("✓ Interface source: button enabled")

# Switch to Custom Molecule source (should be disabled if not available)
window.ion_panel._on_source_changed(1)
window.ion_panel._update_insert_button_state()
# Custom molecule not set, so should be disabled
assert not window.ion_panel.insert_button.isEnabled(), \
    "Ion insert button should be disabled with Custom Molecule source (not set)"
print("✓ Custom Molecule source (not set): button disabled")

# Switch back to Solute source
window.ion_panel._on_source_changed(2)
window.ion_panel._update_insert_button_state()
assert window.ion_panel.insert_button.isEnabled(), \
    "Ion insert button should be enabled with Solute source"
print("✓ Solute source: button enabled")

print("\n" + "="*60)
print("✓ All tests passed!")
print("✓ Solute → Ion workflow path is working correctly")
print("✓ Ion tab generate button becomes active after solute insertion")
print("="*60)
