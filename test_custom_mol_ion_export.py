#!/usr/bin/env python3
"""
Test for custom molecule export in ion workflow.

Workflow: Interface → Custom → Solute → Ion
Tests that custom molecules are correctly exported in TOP and GRO files.
"""

import sys
import numpy as np
from pathlib import Path
import tempfile
import shutil

# Test imports
from quickice.structure_generation.types import (
    InterfaceStructure, CustomMoleculeStructure, SoluteStructure, IonStructure, MoleculeIndex
)
from quickice.output.gromacs_writer import write_ion_gro_file, write_ion_top_file

print("=" * 70)
print("Testing: Custom Molecule Export in Ion Workflow")
print("=" * 70)

# Create test directory
test_dir = Path(tempfile.mkdtemp(prefix="test_custom_mol_export_"))
print(f"\nTest directory: {test_dir}")

# Test 1: Create Interface structure
print("\n1. Creating Interface structure...")
interface_structure = InterfaceStructure(
    positions=np.random.rand(300, 3) * 3.0,
    atom_names=["O"] * 300,
    cell=np.eye(3) * 3.0,
    ice_atom_count=150,
    water_atom_count=150,
    ice_nmolecules=50,
    water_nmolecules=50,
    mode="slab",
    report="Test interface"
)
print("   ✓ Interface structure created")

# Test 2: Create Custom Molecule structure
print("\n2. Creating Custom Molecule structure...")
custom_positions = np.random.rand(50, 3) * 3.0  # 50 custom molecule atoms
custom_atom_names = ["C"] * 25 + ["O"] * 25  # Example: 10 molecules with 5 atoms each

custom_structure = CustomMoleculeStructure(
    positions=np.vstack([interface_structure.positions, custom_positions]),  # Interface + custom
    atom_names=interface_structure.atom_names + custom_atom_names,
    cell=np.eye(3) * 3.0,
    molecule_index=[
        MoleculeIndex(start_idx=i*5, count=5, mol_type="custom") for i in range(10)
    ],
    ice_atom_count=150,
    water_atom_count=150,
    custom_molecule_atom_count=50,
    guest_atom_count=0,
    config=None,
    moleculetype_name="ETOH",
    gro_path=Path("etoh.gro"),
    itp_path=Path("etoh.itp"),
    residue_name="ETOH",
    custom_molecule_count=10,
    interface_structure=interface_structure
)
print("   ✓ Custom molecule structure created (10 molecules, 50 atoms)")

# Test 3: Create Solute structure
print("\n3. Creating Solute structure...")
solute_positions = np.random.rand(35, 3) * 3.0  # 7 CH4 molecules * 5 atoms
solute_atom_names = ["C"] * 7 + ["H"] * 28  # CH4: 1 C + 4 H per molecule

solute_structure = SoluteStructure(
    positions=solute_positions,
    atom_names=solute_atom_names,
    cell=np.eye(3) * 3.0,
    solute_type="CH4",
    n_molecules=7,
    molecule_indices=[(i*5, i*5+5) for i in range(7)],
    registry=None,
    interface_structure=interface_structure
)
print("   ✓ Solute structure created (7 CH4 molecules)")

# Test 4: Create Ion structure with custom molecule info
print("\n4. Creating Ion structure with custom molecule and solute info...")
# Simulate ion structure with custom molecules and solutes
ion_positions = np.random.rand(350, 3) * 3.0  # Interface + some ions
ion_atom_names = ["O"] * 300 + ["NA"] * 25 + ["CL"] * 25

ion_structure = IonStructure(
    positions=ion_positions,
    atom_names=ion_atom_names,
    cell=np.eye(3) * 3.0,
    molecule_index=[
        MoleculeIndex(start_idx=i*4, count=4, mol_type="water") for i in range(75)
    ] + [
        MoleculeIndex(start_idx=300+i, count=1, mol_type="na") for i in range(25)
    ] + [
        MoleculeIndex(start_idx=325+i, count=1, mol_type="cl") for i in range(25)
    ],
    na_count=25,
    cl_count=25,
    report="Test ion insertion",
    # Solute info
    solute_type="CH4",
    solute_positions=solute_positions,
    solute_atom_names=solute_atom_names,
    solute_n_molecules=7,
    solute_molecule_indices=[(i*5, i*5+5) for i in range(7)],
    solute_registry=None,
    # Custom molecule info (THE FIX)
    custom_molecule_count=10,
    custom_molecule_atom_count=50,
    custom_molecule_positions=custom_positions,
    custom_molecule_atom_names=custom_atom_names,
    custom_molecule_moleculetype="ETOH",
    custom_gro_path=Path("etoh.gro"),
    custom_itp_path=Path("etoh.itp")
)
print("   ✓ Ion structure created with custom molecule and solute info")

# Test 5: Export GRO file
print("\n5. Exporting GRO file...")
gro_path = test_dir / "test_ion.gro"
write_ion_gro_file(ion_structure, str(gro_path))

# Check GRO file
with open(gro_path, 'r') as f:
    gro_lines = f.readlines()
    
# Check title line
title = gro_lines[0].strip()
print(f"   Title: {title}")
assert "custom molecules" in title.lower() or "ETOH" in title, \
    "GRO title should mention custom molecules"
print("   ✓ GRO title includes custom molecules")

# Check atom count
atom_count = int(gro_lines[1].strip())
expected_atoms = 75 * 4 + 25 + 25 + 7 * 5 + 10 * 5  # water + ions + solutes + custom
print(f"   Atoms: {atom_count} (expected: {expected_atoms})")
assert atom_count == expected_atoms, f"Atom count mismatch: {atom_count} != {expected_atoms}"
print("   ✓ GRO atom count correct")

# Test 6: Export TOP file
print("\n6. Exporting TOP file...")
top_path = test_dir / "test_ion.top"
write_ion_top_file(ion_structure, str(top_path))

# Check TOP file
with open(top_path, 'r') as f:
    top_content = f.read()

# Check for custom molecules in header
assert "custom molecules" in top_content.lower() or "ETOH" in top_content, \
    "TOP header should mention custom molecules"
print("   ✓ TOP header includes custom molecules")

# Check for [molecules] section
assert "[ molecules ]" in top_content, "TOP should have [molecules] section"
print("   ✓ TOP has [molecules] section")

# Check for custom molecule entry in [molecules]
lines = top_content.split('\n')
molecules_section = False
has_custom_mol = False
for line in lines:
    if "[ molecules ]" in line:
        molecules_section = True
        continue
    if molecules_section and line.strip() and not line.startswith(';'):
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "ETOH":
            has_custom_mol = True
            print(f"   ✓ Found custom molecule in [molecules]: {line.strip()}")
            break

assert has_custom_mol, "TOP [molecules] section should include custom molecule entry"

# Test 7: Check molecule order in [molecules]
print("\n7. Checking molecule order in [molecules]...")
molecule_entries = []
in_molecules_section = False
for line in lines:
    if "[ molecules ]" in line:
        in_molecules_section = True
        continue
    if in_molecules_section:
        if line.strip() and not line.startswith(';'):
            parts = line.split()
            if len(parts) >= 2:
                molecule_entries.append((parts[0], int(parts[1])))
        elif line.strip().startswith('['):
            # End of molecules section
            break

print(f"   Molecule entries: {molecule_entries}")
expected_entries = [("SOL", 75), ("ETOH", 10), ("CH4_LIQ", 7), ("NA", 25), ("CL", 25)]
assert molecule_entries == expected_entries, f"Molecule entries mismatch: {molecule_entries} != {expected_entries}"
print("   ✓ Molecule order and counts are correct (SOL → custom → solute → ions)")

# Test 8: Check for custom ITP include
print("\n8. Checking for custom ITP include...")
assert '#include "etoh.itp"' in top_content or '#include "ETOH.itp"' in top_content, \
    "TOP should include custom molecule ITP"
print("   ✓ TOP includes custom molecule ITP")

print("\n" + "=" * 70)
print("✓ ALL EXPORT TESTS PASSED")
print("=" * 70)

print("\nSummary:")
print("  - Custom molecules are correctly included in GRO file")
print("  - Custom molecules are correctly listed in TOP file [molecules] section")
print("  - Custom molecule ITP is included in TOP file")
print("  - Molecule order is correct: SOL → custom → solute → ions")
print("=" * 70)

# Cleanup
shutil.rmtree(test_dir)
print(f"\nCleaned up test directory: {test_dir}")
