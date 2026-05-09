#!/usr/bin/env python3
"""
Test to verify custom molecules are preserved when inserting solutes.

Workflow: Interface → Custom → Solute → Ion

The fix ensures that:
1. When solutes are inserted from a CustomMoleculeStructure
2. The interface_structure in SoluteStructure contains custom molecules
3. Custom molecule attributes are preserved (positions, atom_names, count, etc.)
"""

import numpy as np
from pathlib import Path

from quickice.structure_generation.types import (
    InterfaceStructure,
    CustomMoleculeStructure,
    SoluteStructure,
    SoluteConfig,
)
from quickice.structure_generation.solute_inserter import SoluteInserter

print("=" * 70)
print("Testing: Custom Molecules Preserved in Solute Insertion")
print("=" * 70)

# Step 1: Create a basic InterfaceStructure (ice + water)
print("\n1. Creating InterfaceStructure (ice + water)...")
# Create proper atom names: 100 ice atoms + 100 water atoms (25 molecules × 4 atoms each)
ice_atom_names = ["OW"] * 100  # Simplified: using OW for all ice atoms
water_atom_names = ["OW", "HW1", "HW2", "MW"] * 25  # 25 water molecules, 4 atoms each
all_atom_names = ice_atom_names + water_atom_names

interface = InterfaceStructure(
    positions=np.random.rand(200, 3) * 3.0,  # 200 atoms total
    atom_names=all_atom_names,
    cell=np.eye(3) * 3.0,
    ice_atom_count=100,  # 100 ice atoms
    water_atom_count=100,  # 100 water atoms (25 molecules)
    ice_nmolecules=25,
    water_nmolecules=25,
    mode="slab",
    report="Test interface",
    guest_atom_count=0,
    molecule_index=[],
    guest_nmolecules=0,
)
print(f"   ✓ Interface created: {interface.ice_atom_count} ice atoms, {interface.water_atom_count} water atoms")

# Step 2: Create a CustomMoleculeStructure (ice + water + custom molecules)
print("\n2. Creating CustomMoleculeStructure (adding custom molecules)...")
# Add 20 custom molecule atoms (e.g., 4 molecules × 5 atoms each)
custom_atoms = 20
custom_positions = np.random.rand(custom_atoms, 3) * 3.0
custom_atom_names = ["C"] * 20

# Combine: interface positions + custom molecule positions
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
print(f"   ✓ Custom structure created: {custom_structure.custom_molecule_count} molecules, {custom_structure.custom_molecule_atom_count} atoms")

# Step 3: Insert solutes from the CustomMoleculeStructure
print("\n3. Inserting solutes from CustomMoleculeStructure...")
config = SoluteConfig(
    solute_type="CH4",
    concentration_molar=2.0,  # Higher concentration to ensure molecules placed
    min_separation=0.3,
    max_attempts=100,
)

inserter = SoluteInserter(config=config, seed=42)

# This is where the fix is needed:
# - The custom_structure should be passed (not just interface_structure)
# - But currently, main_window.py passes custom_structure.interface_structure
# Let's test both scenarios

print("\n   Testing scenario A: Passing interface_structure (CURRENT BUG)")
solute_structure_A = inserter.insert_solutes(custom_structure.interface_structure, config)
print(f"   - Solute positions: {solute_structure_A.positions.shape}")
print(f"   - Interface positions: {solute_structure_A.interface_structure.positions.shape}")
print(f"   - Interface has custom molecules? {hasattr(solute_structure_A.interface_structure, 'custom_molecule_atom_count')}")
if hasattr(solute_structure_A.interface_structure, 'custom_molecule_atom_count'):
    print(f"   - Custom molecule atoms: {solute_structure_A.interface_structure.custom_molecule_atom_count}")
else:
    print(f"   - ✗ BUG: Custom molecules lost!")

print("\n   Testing scenario B: Passing full CustomMoleculeStructure (THE FIX)")
solute_structure_B = inserter.insert_solutes(custom_structure, config)
print(f"   - Solute positions: {solute_structure_B.positions.shape}")
print(f"   - Interface positions: {solute_structure_B.interface_structure.positions.shape}")
print(f"   - Interface has custom molecules? {hasattr(solute_structure_B.interface_structure, 'custom_molecule_atom_count')}")
if hasattr(solute_structure_B.interface_structure, 'custom_molecule_atom_count'):
    print(f"   - Custom molecule atoms: {solute_structure_B.interface_structure.custom_molecule_atom_count}")
    print(f"   - ✓ FIXED: Custom molecules preserved!")
else:
    print(f"   - ✗ Fix not working: Custom molecules still lost!")

# Step 4: Verify the fix
print("\n4. Verifying custom molecule preservation...")
success = True

# Check that custom molecule attributes exist
if not hasattr(solute_structure_B.interface_structure, 'custom_molecule_count'):
    print("   ✗ Missing: custom_molecule_count")
    success = False
else:
    print(f"   ✓ custom_molecule_count = {solute_structure_B.interface_structure.custom_molecule_count}")

if not hasattr(solute_structure_B.interface_structure, 'custom_molecule_atom_count'):
    print("   ✗ Missing: custom_molecule_atom_count")
    success = False
else:
    print(f"   ✓ custom_molecule_atom_count = {solute_structure_B.interface_structure.custom_molecule_atom_count}")

if not hasattr(solute_structure_B.interface_structure, 'custom_molecule_positions'):
    print("   ✗ Missing: custom_molecule_positions")
    success = False
else:
    print(f"   ✓ custom_molecule_positions shape = {solute_structure_B.interface_structure.custom_molecule_positions.shape}")

if not hasattr(solute_structure_B.interface_structure, 'custom_molecule_atom_names'):
    print("   ✗ Missing: custom_molecule_atom_names")
    success = False
else:
    print(f"   ✓ custom_molecule_atom_names count = {len(solute_structure_B.interface_structure.custom_molecule_atom_names)}")

if not hasattr(solute_structure_B.interface_structure, 'custom_molecule_moleculetype'):
    print("   ✗ Missing: custom_molecule_moleculetype")
    success = False
else:
    print(f"   ✓ custom_molecule_moleculetype = {solute_structure_B.interface_structure.custom_molecule_moleculetype}")

# Check that positions array includes custom molecules
expected_total_atoms = (solute_structure_B.interface_structure.ice_atom_count + 
                        solute_structure_B.interface_structure.water_atom_count +
                        solute_structure_B.interface_structure.guest_atom_count +
                        solute_structure_B.interface_structure.custom_molecule_atom_count)
actual_total_atoms = solute_structure_B.interface_structure.positions.shape[0]

if actual_total_atoms == expected_total_atoms:
    print(f"   ✓ Total atoms correct: {actual_total_atoms}")
else:
    print(f"   ✗ Total atoms mismatch: expected {expected_total_atoms}, got {actual_total_atoms}")
    success = False

print("\n" + "=" * 70)
if success:
    print("✓ ALL TESTS PASSED - FIX WORKING")
    print("=" * 70)
    print("\nSummary:")
    print("  When solutes are inserted from a CustomMoleculeStructure:")
    print("  - Custom molecule positions are preserved in interface_structure.positions")
    print("  - Custom molecule attributes are preserved")
    print("  - Total atom count is correct")
    print("  - Ready for downstream ion insertion")
else:
    print("✗ SOME TESTS FAILED - FIX NEEDS WORK")
    print("=" * 70)
print()
