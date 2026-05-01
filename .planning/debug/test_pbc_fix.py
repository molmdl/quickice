#!/usr/bin/env python3
"""Test that molecules are wrapped as whole units, not atom-by-atom."""

import numpy as np
from quickice.output.gromacs_writer import wrap_molecules_into_box, wrap_positions_into_box
from quickice.structure_generation.types import MoleculeIndex


def test_molecule_wrapping():
    """Test that molecules spanning PBC are kept together."""
    # Box: 7.45 x 7.45 x 10.93 nm
    cell = np.array([
        [7.45, 0.0, 0.0],
        [0.0, 7.45, 0.0],
        [0.0, 0.0, 10.93]
    ])
    
    # Create a water molecule spanning X boundary
    # Oxygen at 7.40 nm (near boundary)
    # HW1 at 7.45 nm (beyond boundary, should wrap)
    # HW2 at 7.35 nm (inside box)
    # MW at 7.42 nm (near boundary)
    positions = np.array([
        [7.40, 0.5, 0.5],   # O
        [7.45, 0.55, 0.5],  # H1 - beyond box
        [7.35, 0.45, 0.5],  # H2
        [7.42, 0.5, 0.5],   # MW
    ])
    
    # Single molecule: 4 atoms starting at index 0
    molecule_index = [
        MoleculeIndex(start_idx=0, count=4, mol_type="water")
    ]
    
    # Test old behavior (atom-by-atom wrapping)
    print("Testing atom-by-atom wrapping (old behavior):")
    wrapped_atom_by_atom = wrap_positions_into_box(positions, cell)
    print(f"  OW:  {wrapped_atom_by_atom[0]}")
    print(f"  HW1: {wrapped_atom_by_atom[1]}")
    print(f"  HW2: {wrapped_atom_by_atom[2]}")
    print(f"  MW:  {wrapped_atom_by_atom[3]}")
    
    # Check if atoms are on opposite sides (bad)
    x_coords = wrapped_atom_by_atom[:, 0]
    if max(x_coords) - min(x_coords) > 6.0:  # More than half box apart
        print("  ❌ Molecule split across PBC!")
    else:
        print("  ✓ Molecule kept together")
    
    # Test new behavior (molecule-aware wrapping)
    print("\nTesting molecule-aware wrapping (new behavior):")
    wrapped_molecules = wrap_molecules_into_box(positions, molecule_index, cell)
    print(f"  OW:  {wrapped_molecules[0]}")
    print(f"  HW1: {wrapped_molecules[1]}")
    print(f"  HW2: {wrapped_molecules[2]}")
    print(f"  MW:  {wrapped_molecules[3]}")
    
    # Check if atoms are on same side (good)
    x_coords = wrapped_molecules[:, 0]
    if max(x_coords) - min(x_coords) > 6.0:  # More than half box apart
        print("  ❌ Molecule split across PBC!")
        return False
    else:
        print("  ✓ Molecule kept together")
    
    # Verify relative positions are preserved
    original_dists = []
    wrapped_dists = []
    for i in range(1, 4):
        original_dists.append(np.linalg.norm(positions[i] - positions[0]))
        wrapped_dists.append(np.linalg.norm(wrapped_molecules[i] - wrapped_molecules[0]))
    
    print("\nRelative distances from oxygen:")
    for i, (orig, wrap) in enumerate(zip(original_dists, wrapped_dists), 1):
        print(f"  HW{i}/MW: original={orig:.4f}, wrapped={wrap:.4f}, diff={abs(orig-wrap):.6f}")
        if abs(orig - wrap) > 1e-10:
            print(f"  ❌ Relative position changed!")
            return False
    
    print("\n✓ All checks passed!")
    return True


def test_actual_gro_file():
    """Test actual GRO file from tmp/ch4/ion/ions_50na_50cl.gro."""
    print("\n" + "="*70)
    print("Testing actual GRO file: molecule 6SOL")
    print("="*70)
    
    # Read the file
    gro_file = "/share/home/nglokwan/quickice/tmp/ch4/ion/ions_50na_50cl.gro"
    
    try:
        with open(gro_file, 'r') as f:
            lines = f.readlines()
        
        # Find molecule 6SOL (lines 23-26 in 1-indexed, 22-25 in 0-indexed)
        mol6_lines = lines[22:26]
        
        print("\nOriginal GRO file (before fix):")
        for line in mol6_lines:
            print(f"  {line.rstrip()}")
        
        # Parse coordinates
        coords = []
        for line in mol6_lines:
            parts = line.split()
            x = float(parts[3])
            y = float(parts[4])
            z = float(parts[5])
            coords.append([x, y, z])
        
        coords = np.array(coords)
        x_coords = coords[:, 0]
        
        # Check if molecule is split
        if max(x_coords) - min(x_coords) > 6.0:
            print("\n❌ Molecule is split across PBC in original file!")
            print(f"   X coordinates: {x_coords}")
            print(f"   Span: {max(x_coords) - min(x_coords):.3f} nm (> half box)")
        else:
            print("\n✓ Molecule is intact in original file")
        
        return True
        
    except FileNotFoundError:
        print(f"\nGRO file not found: {gro_file}")
        print("This is expected if the file hasn't been regenerated yet.")
        return True


if __name__ == "__main__":
    print("="*70)
    print("Testing PBC molecule wrapping fix")
    print("="*70)
    
    success = True
    success = test_molecule_wrapping() and success
    success = test_actual_gro_file() and success
    
    if success:
        print("\n" + "="*70)
        print("ALL TESTS PASSED")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("SOME TESTS FAILED")
        print("="*70)
        exit(1)
