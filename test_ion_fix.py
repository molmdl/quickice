#!/usr/bin/env python3
"""Test script to verify the ion overlap fix."""

import numpy as np
from scipy.spatial import cKDTree

def test_ion_distances(gro_file):
    """Check that all ions are >= MIN_SEPARATION from hydrate atoms."""
    
    MIN_SEPARATION = 0.3  # nm
    
    with open(gro_file) as f:
        lines = f.readlines()
    
    # Parse all atoms
    sol_positions = []
    ch4_positions = []
    na_positions = []
    cl_positions = []
    
    for line in lines[2:-1]:  # Skip header and box line
        if len(line) < 44:
            continue
        
        res_name = line[5:10].strip()
        atom_name = line[10:15].strip()
        
        try:
            x = float(line[20:28])
            y = float(line[28:36])
            z = float(line[36:44])
        except:
            continue
        
        pos = np.array([x, y, z])
        
        if res_name == 'SOL':
            sol_positions.append(pos)
        elif res_name == 'CH4':
            ch4_positions.append(pos)
        elif res_name == 'NA':
            na_positions.append(pos)
        elif res_name == 'CL':
            cl_positions.append(pos)
    
    sol_positions = np.array(sol_positions)
    ch4_positions = np.array(ch4_positions)
    na_positions = np.array(na_positions)
    cl_positions = np.array(cl_positions)
    
    print(f"Loaded {len(sol_positions)} SOL atoms, {len(ch4_positions)} CH4 atoms")
    print(f"Loaded {len(na_positions)} NA ions, {len(cl_positions)} CL ions")
    
    # Build KDTree for all hydrate atoms
    hydrate_atoms = np.vstack([sol_positions, ch4_positions])
    hydrate_tree = cKDTree(hydrate_atoms)
    
    # Check distances for NA ions
    print(f"\nChecking NA ions:")
    na_violations = 0
    na_dists = []
    for pos in na_positions:
        dist, _ = hydrate_tree.query(pos, k=1)
        na_dists.append(dist)
        if dist < MIN_SEPARATION:
            na_violations += 1
    
    na_dists = np.array(na_dists)
    print(f"  Min distance: {na_dists.min():.3f} nm")
    print(f"  Max distance: {na_dists.max():.3f} nm")
    print(f"  Mean distance: {na_dists.mean():.3f} nm")
    print(f"  Violations (< {MIN_SEPARATION} nm): {na_violations}/{len(na_positions)}")
    
    # Check distances for CL ions
    print(f"\nChecking CL ions:")
    cl_violations = 0
    cl_dists = []
    for pos in cl_positions:
        dist, _ = hydrate_tree.query(pos, k=1)
        cl_dists.append(dist)
        if dist < MIN_SEPARATION:
            cl_violations += 1
    
    cl_dists = np.array(cl_dists)
    print(f"  Min distance: {cl_dists.min():.3f} nm")
    print(f"  Max distance: {cl_dists.max():.3f} nm")
    print(f"  Mean distance: {cl_dists.mean():.3f} nm")
    print(f"  Violations (< {MIN_SEPARATION} nm): {cl_violations}/{len(cl_positions)}")
    
    # Summary
    total_violations = na_violations + cl_violations
    total_ions = len(na_positions) + len(cl_positions)
    
    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"  Total ions: {total_ions}")
    print(f"  Total violations: {total_violations}")
    
    if total_violations == 0:
        print(f"  ✓ PASS: All ions are >= {MIN_SEPARATION} nm from hydrate atoms")
        return True
    else:
        print(f"  ✗ FAIL: {total_violations} ions are < {MIN_SEPARATION} nm from hydrate atoms")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_fix.py <gro_file>")
        sys.exit(1)
    
    gro_file = sys.argv[1]
    success = test_ion_distances(gro_file)
    sys.exit(0 if success else 1)
