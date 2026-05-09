#!/usr/bin/env python3
"""
End-to-end test for custom molecule preservation in the workflow:
Interface → Custom → Solute → Ion

This test verifies that custom molecules are properly preserved through
the entire data flow when exporting at the Ion tab.
"""

import numpy as np
from pathlib import Path

from quickice.structure_generation.types import (
    InterfaceStructure,
    CustomMoleculeStructure,
    SoluteStructure,
    SoluteConfig,
    IonConfig,
)
from quickice.structure_generation.solute_inserter import SoluteInserter
from quickice.structure_generation.ion_inserter import IonInserter

print("=" * 70)
print("End-to-End Test: Custom Molecules in Interface → Custom → Solute → Ion")
print("=" * 70)

# Step 1: Create InterfaceStructure
print("\n1. Creating InterfaceStructure...")
ice_atom_names = ["OW"] * 100
water_atom_names = ["OW", "HW1", "HW2", "MW"] * 25
all_atom_names = ice_atom_names + water_atom_names

interface = InterfaceStructure(
    positions=np.random.rand(200, 3) * 3.0,
    atom_names=all_atom_names,
    cell=np.eye(3) * 3.0,
    ice_atom_count=100,
    water_atom_count=100,
    ice_nmolecules=25,
    water_nmolecules=25,
    mode="slab",
    report="Test interface",
    guest_atom_count=0,
    molecule_index=[],
    guest_nmolecules=0,
)
print(f"   ✓ Interface: {interface.ice_atom_count} ice + {interface.water_atom_count} water = {interface.positions.shape[0]} atoms")

# Step 2: Create CustomMoleculeStructure (simulate custom molecule insertion)
print("\n2. Adding custom molecules...")
custom_atoms = 20
custom_positions = np.random.rand(custom_atoms, 3) * 3.0
custom_atom_names = ["C"] * 20

complete_positions = np.vstack([interface.positions, custom_positions])
complete_atom_names = interface.atom_names + custom_atom_names

custom_structure = CustomMoleculeStructure(
    positions=complete_positions,
    atom_names=complete_atom_names,
    cell=interface.cell,
    molecule_index=[],
    ice_atom_count=interface.ice_atom_count,
    water_atom_count=interface.water_atom_count,
    custom_molecule_atom_count=custom_atoms,
    guest_atom_count=0,
    config=None,
    moleculetype_name="CUSTOM_MOL_1",
    gro_path=Path("test.gro"),
    itp_path=Path("test.itp"),
    residue_name="CST",
    custom_molecule_count=4,
    interface_structure=interface,
)
print(f"   ✓ Custom structure: {custom_structure.custom_molecule_count} molecules, {custom_structure.custom_molecule_atom_count} atoms")
print(f"   ✓ Total atoms: {custom_structure.positions.shape[0]}")

# Step 3: Insert solutes from CustomMoleculeStructure
print("\n3. Inserting solutes from custom structure...")
solute_config = SoluteConfig(
    solute_type="CH4",
    concentration_molar=2.0,
    min_separation=0.3,
    max_attempts=100,
)

solute_inserter = SoluteInserter(config=solute_config, seed=42)
# Pass full CustomMoleculeStructure (not just interface_structure)
solute_structure = solute_inserter.insert_solutes(custom_structure, solute_config)

print(f"   ✓ Solute structure: {solute_structure.n_molecules} molecules, {solute_structure.positions.shape[0]} atoms")
print(f"   ✓ Interface positions: {solute_structure.interface_structure.positions.shape[0]} atoms")

# Step 4: Verify custom molecules are preserved in interface_structure
print("\n4. Verifying custom molecule preservation in interface_structure...")
success = True

# Debug: check what attributes interface_structure has
print(f"   DEBUG: interface_structure type = {type(solute_structure.interface_structure)}")
print(f"   DEBUG: interface_structure positions shape = {solute_structure.interface_structure.positions.shape}")
print(f"   DEBUG: has custom_molecule_count? {hasattr(solute_structure.interface_structure, 'custom_molecule_count')}")
print(f"   DEBUG: has custom_molecule_positions? {hasattr(solute_structure.interface_structure, 'custom_molecule_positions')}")
print(f"   DEBUG: has custom_molecule_atom_names? {hasattr(solute_structure.interface_structure, 'custom_molecule_atom_names')}")

if not hasattr(solute_structure.interface_structure, 'custom_molecule_count'):
    print("   ✗ Missing: custom_molecule_count")
    success = False
else:
    count = solute_structure.interface_structure.custom_molecule_count
    print(f"   ✓ custom_molecule_count = {count}")
    if count != custom_structure.custom_molecule_count:
        print(f"   ✗ Wrong count: expected {custom_structure.custom_molecule_count}, got {count}")
        success = False

if not hasattr(solute_structure.interface_structure, 'custom_molecule_atom_count'):
    print("   ✗ Missing: custom_molecule_atom_count")
    success = False
else:
    atom_count = solute_structure.interface_structure.custom_molecule_atom_count
    print(f"   ✓ custom_molecule_atom_count = {atom_count}")
    if atom_count != custom_atoms:
        print(f"   ✗ Wrong atom count: expected {custom_atoms}, got {atom_count}")
        success = False

if not hasattr(solute_structure.interface_structure, 'custom_molecule_positions'):
    print("   ✗ Missing: custom_molecule_positions")
    success = False
else:
    pos_shape = solute_structure.interface_structure.custom_molecule_positions.shape
    print(f"   ✓ custom_molecule_positions shape = {pos_shape}")
    if pos_shape[0] != custom_atoms:
        print(f"   ✗ Wrong positions: expected {custom_atoms}, got {pos_shape[0]}")
        success = False

if not hasattr(solute_structure.interface_structure, 'custom_molecule_atom_names'):
    print("   ✗ Missing: custom_molecule_atom_names")
    success = False
else:
    names_count = len(solute_structure.interface_structure.custom_molecule_atom_names)
    print(f"   ✓ custom_molecule_atom_names count = {names_count}")
    if names_count != custom_atoms:
        print(f"   ✗ Wrong names: expected {custom_atoms}, got {names_count}")
        success = False

# Step 5: Use the interface_structure for ion insertion
print("\n5. Inserting ions from solute structure...")
interface_for_ion = solute_structure.interface_structure

# Add solute attributes (as main_window.py does)
interface_for_ion.solute_type = solute_structure.solute_type
interface_for_ion.solute_positions = solute_structure.positions
interface_for_ion.solute_atom_names = solute_structure.atom_names
interface_for_ion.solute_n_molecules = solute_structure.n_molecules
interface_for_ion.solute_molecule_indices = solute_structure.molecule_indices
interface_for_ion.solute_registry = solute_structure.registry

ion_config = IonConfig(
    concentration_molar=0.15,
)

# Use standalone function instead of IonInserter method
from quickice.structure_generation.ion_inserter import insert_ions
ion_structure = insert_ions(
    structure=interface_for_ion,
    concentration_molar=ion_config.concentration_molar,
    seed=42
)

print(f"   ✓ Ion structure: {ion_structure.na_count} Na+ + {ion_structure.cl_count} Cl- ions")
print(f"   ✓ Total atoms: {ion_structure.positions.shape[0]}")

# Step 6: Verify custom molecules are still accessible for export
print("\n6. Verifying custom molecules accessible for export...")
if hasattr(interface_for_ion, 'custom_molecule_positions'):
    print(f"   ✓ Custom molecules accessible in interface_for_ion")
    print(f"   ✓ Ready for GROMACS export")
else:
    print(f"   ✗ Custom molecules NOT accessible")
    success = False

# Final summary
print("\n" + "=" * 70)
if success:
    print("✓ ALL TESTS PASSED - COMPLETE WORKFLOW WORKING")
    print("=" * 70)
    print("\nWorkflow verified:")
    print("  1. Interface created")
    print("  2. Custom molecules added")
    print("  3. Solutes inserted (preserving custom molecules)")
    print("  4. Ions inserted (custom molecules still accessible)")
    print("  5. Ready for export at Ion tab")
else:
    print("✗ SOME TESTS FAILED")
    print("=" * 70)
print()
