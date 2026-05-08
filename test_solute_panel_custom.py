#!/usr/bin/env python3
"""Test script for SolutePanel Custom Molecule source handling."""

from quickice.gui.solute_panel import SolutePanel
from quickice.structure_generation.types import CustomMoleculeStructure, MoleculeIndex, InterfaceStructure
import numpy as np
from pathlib import Path
from PySide6.QtWidgets import QApplication
import sys

# Create application
app = QApplication.instance() or QApplication(sys.argv)

# Create panel
panel = SolutePanel()

# Create test custom molecule structure
custom_structure = CustomMoleculeStructure(
    positions=np.random.rand(100, 3) * 3.0,
    atom_names=["O"] * 100,
    cell=np.eye(3) * 3.0,
    molecule_index=[MoleculeIndex(0, 100, "water")],
    ice_atom_count=30,
    water_atom_count=70,
    custom_molecule_atom_count=0,
    guest_atom_count=0,
    moleculetype_name="TEST",
    custom_molecule_count=10
)

# Test 1: Set custom molecule structure
print("Test 1: Setting custom molecule structure...")
panel.set_custom_molecule_structure(custom_structure)

# Verify state
assert panel._custom_molecule_structure is not None, "Custom molecule structure should be set"
assert panel._custom_molecule_available, "Custom molecule should be available"
print("✓ Custom molecule structure set correctly")

# Test 2: Select Custom Molecule source
print("\nTest 2: Selecting Custom Molecule source...")
panel._on_source_changed(1)  # Index 1 = Custom Molecule
assert panel._current_source == "Custom Molecule", "Source should be Custom Molecule"
print("✓ Source changed to Custom Molecule")

# Test 3: Get current source structure
print("\nTest 3: Getting current source structure...")
source = panel.get_current_source_structure()
assert source is not None, "Should return CustomMoleculeStructure"
assert hasattr(source, 'ice_atom_count'), "Should have interface structure fields"
print(f"✓ Retrieved source structure: ice={source.ice_atom_count}, water={source.water_atom_count} atoms")

# Test 4: Button state with solute type
print("\nTest 4: Testing button state...")
# Set solute type
panel.solute_type_combo.setCurrentText("CH₄")
panel._solute_type = "CH4"
panel._update_insert_button_state()
assert panel.insert_button.isEnabled(), "Insert button should be enabled with Custom Molecule source and solute type"
print("✓ Insert button enabled correctly")

# Test 5: Interface structure handling
print("\nTest 5: Testing Interface structure handling...")
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
panel.set_interface_structure(interface_structure)
assert panel._interface_structure is not None, "Interface structure should be set"
assert panel._interface_available, "Interface should be available"
print("✓ Interface structure set correctly")

# Test 6: Switch back to Interface source
print("\nTest 6: Switching back to Interface source...")
panel._on_source_changed(0)  # Index 0 = Interface
assert panel._current_source == "Interface", "Source should be Interface"
source = panel.get_current_source_structure()
assert source is not None, "Should return InterfaceStructure"
assert hasattr(source, 'ice_nmolecules'), "Should have ice_nmolecules field"
print(f"✓ Retrieved interface structure: ice={source.ice_nmolecules}, water={source.water_nmolecules} molecules")

print("\n" + "="*60)
print("✓ All tests passed!")
print("✓ SolutePanel handles Custom Molecule source correctly")
print("="*60)
