#!/usr/bin/env python3
"""Test script for IonPanel Custom Molecule source handling."""

from quickice.gui.ion_panel import IonPanel
from quickice.structure_generation.types import CustomMoleculeStructure, MoleculeIndex, InterfaceStructure, SoluteStructure
import numpy as np
from pathlib import Path
from PySide6.QtWidgets import QApplication
import sys

# Create application
app = QApplication.instance() or QApplication(sys.argv)

# Create panel
panel = IonPanel()

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
assert hasattr(source, 'custom_molecule_count'), "Should have custom_molecule_count field"
print(f"✓ Retrieved source structure: {source.custom_molecule_count} custom molecules")

# Test 4: Button state
print("\nTest 4: Testing button state...")
panel._update_insert_button_state()
assert panel.insert_button.isEnabled(), "Insert button should be enabled with Custom Molecule source"
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

# Test 6: Switch to Interface source
print("\nTest 6: Switching to Interface source...")
panel._on_source_changed(0)  # Index 0 = Interface
assert panel._current_source == "Interface", "Source should be Interface"
source = panel.get_current_source_structure()
assert source is not None, "Should return InterfaceStructure"
assert hasattr(source, 'ice_nmolecules'), "Should have ice_nmolecules field"
print(f"✓ Retrieved interface structure: ice={source.ice_nmolecules}, water={source.water_nmolecules} molecules")

# Test 7: Solute structure handling
print("\nTest 7: Testing Solute structure handling...")
solute_structure = SoluteStructure(
    positions=np.random.rand(50, 3) * 3.0,
    atom_names=["C"] * 50,
    cell=np.eye(3) * 3.0,
    solute_type="CH4",
    n_molecules=10,
    molecule_indices=[(0, 5), (5, 10), (10, 15), (15, 20), (20, 25), (25, 30), (30, 35), (35, 40), (40, 45), (45, 50)],
    registry=None
)
panel.set_solute_structure(solute_structure)
assert panel._solute_structure is not None, "Solute structure should be set"
assert panel._solute_available, "Solute should be available"
print("✓ Solute structure set correctly")

# Test 8: Switch to Solute source
print("\nTest 8: Switching to Solute source...")
panel._on_source_changed(2)  # Index 2 = Solute
assert panel._current_source == "Solute", "Source should be Solute"
source = panel.get_current_source_structure()
assert source is not None, "Should return SoluteStructure"
assert hasattr(source, 'solute_type'), "Should have solute_type field"
print(f"✓ Retrieved solute structure: {source.n_molecules} {source.solute_type} molecules")
assert panel.insert_button.isEnabled(), "Insert button should be enabled with Solute source"
print("✓ Insert button enabled correctly for Solute source")

print("\n" + "="*60)
print("✓ All tests passed!")
print("✓ IonPanel handles Custom Molecule source correctly")
print("✓ IonPanel supports all three sources: Interface, Custom Molecule, Solute")
print("="*60)
