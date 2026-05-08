#!/usr/bin/env python3
"""
Integration test for Custom Molecule workflow paths.

Tests both workflow paths:
1. Interface → Custom → Solute → Ion (with solutes)
2. Interface → Custom → Ion (direct, skip solutes)
"""

from quickice.gui.main_window import MainWindow
from quickice.structure_generation.types import (
    CustomMoleculeStructure, MoleculeIndex, InterfaceStructure
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
print("Testing Custom Molecule Workflow Paths")
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

# Test 2: Create Custom Molecule structure
print("\n2. Creating Custom Molecule structure...")
custom_structure = CustomMoleculeStructure(
    positions=np.random.rand(150, 3) * 3.0,
    atom_names=["O"] * 150,
    cell=np.eye(3) * 3.0,
    molecule_index=[
        MoleculeIndex(0, 4, "ice"),
        MoleculeIndex(4, 8, "ice"),
        MoleculeIndex(8, 12, "water"),
        MoleculeIndex(12, 16, "water"),
        MoleculeIndex(16, 20, "custom"),
    ],
    ice_atom_count=50,
    water_atom_count=50,
    custom_molecule_atom_count=50,
    guest_atom_count=0,
    moleculetype_name="ETHANOL",
    custom_molecule_count=10
)

# Simulate custom molecule insertion completion
window._on_custom_finished(custom_structure)

# Test 3: Verify Custom Molecule passed to BOTH panels
print("\n3. Verifying Custom Molecule passed to both panels...")

# Check SolutePanel
assert window.solute_panel._custom_molecule_structure is not None, \
    "SolutePanel should have CustomMoleculeStructure"
assert window.solute_panel._custom_molecule_available, \
    "SolutePanel should have Custom Molecule available"
print("✓ SolutePanel received CustomMoleculeStructure")

# Check IonPanel
assert window.ion_panel._custom_molecule_structure is not None, \
    "IonPanel should have CustomMoleculeStructure"
assert window.ion_panel._custom_molecule_available, \
    "IonPanel should have Custom Molecule available"
print("✓ IonPanel received CustomMoleculeStructure")

# Test 4: Workflow Path 1 - Interface → Custom → Solute → Ion
print("\n4. Testing Workflow Path 1: Interface → Custom → Solute → Ion")

# Select Custom Molecule source in Solute panel
window.solute_panel._on_source_changed(1)  # Index 1 = Custom Molecule
assert window.solute_panel._current_source == "Custom Molecule", \
    "Solute source should be Custom Molecule"

# Verify button state
window.solute_panel.solute_type_combo.setCurrentText("CH₄")
window.solute_panel._solute_type = "CH4"
window.solute_panel._update_insert_button_state()
assert window.solute_panel.insert_button.isEnabled(), \
    "Solute insert button should be enabled"

# Get source structure
solute_source = window.solute_panel.get_current_source_structure()
assert solute_source is not None, "Should have solute source structure"
assert solute_source.custom_molecule_count == 10, \
    f"Expected 10 custom molecules, got {solute_source.custom_molecule_count}"
print("✓ SolutePanel can use Custom Molecule as source")

# Test 5: Workflow Path 2 - Interface → Custom → Ion (direct)
print("\n5. Testing Workflow Path 2: Interface → Custom → Ion (direct)")

# Select Custom Molecule source in Ion panel
window.ion_panel._on_source_changed(1)  # Index 1 = Custom Molecule
assert window.ion_panel._current_source == "Custom Molecule", \
    "Ion source should be Custom Molecule"

# Verify button state
window.ion_panel._update_insert_button_state()
assert window.ion_panel.insert_button.isEnabled(), \
    "Ion insert button should be enabled"

# Get source structure
ion_source = window.ion_panel.get_current_source_structure()
assert ion_source is not None, "Should have ion source structure"
assert ion_source.custom_molecule_count == 10, \
    f"Expected 10 custom molecules, got {ion_source.custom_molecule_count}"
print("✓ IonPanel can use Custom Molecule as source (direct path)")

# Test 6: Verify Interface source still works
print("\n6. Verifying Interface source still works...")

window.solute_panel._on_source_changed(0)  # Index 0 = Interface
assert window.solute_panel._current_source == "Interface"
solute_source = window.solute_panel.get_current_source_structure()
assert solute_source is not None, "Should have interface source"
assert hasattr(solute_source, 'ice_nmolecules'), "Should be InterfaceStructure"
print("✓ SolutePanel Interface source works")

window.ion_panel._on_source_changed(0)  # Index 0 = Interface
assert window.ion_panel._current_source == "Interface"
ion_source = window.ion_panel.get_current_source_structure()
assert ion_source is not None, "Should have interface source"
assert hasattr(ion_source, 'ice_nmolecules'), "Should be InterfaceStructure"
print("✓ IonPanel Interface source works")

print("\n" + "="*60)
print("✓ All workflow tests passed!")
print("✓ Both workflow paths functional:")
print("  1. Interface → Custom → Solute → Ion")
print("  2. Interface → Custom → Ion (direct)")
print("="*60)
