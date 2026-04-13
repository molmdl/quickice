#!/usr/bin/env python
"""Analyze how Ice II's lattice vector structure causes gaps."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.water_filler import get_cell_extent, is_cell_orthogonal


def analyze_lattice_interaction(cell_matrix, name="Ice"):
    """Analyze how lattice vectors interact during tiling."""
    print(f"\n{'='*60}")
    print(f"{name} LATTICE VECTOR ANALYSIS")
    print(f"{'='*60}")
    
    a = cell_matrix[0]
    b = cell_matrix[1]
    c = cell_matrix[2]
    
    print(f"\nLattice vectors:")
    print(f"  a = {a}")
    print(f"  b = {b}")
    print(f"  c = {c}")
    
    # Calculate the "effective" step size in each direction
    # For a triclinic cell, the step in X when we increment ix by 1 is a[0]
    # But the step in X when we increment iy by 1 is b[0] (which can be negative!)
    
    print(f"\nStep sizes along each axis for each lattice direction:")
    print(f"  X-axis: a_x={a[0]:.3f}, b_x={b[0]:.3f}, c_x={c[0]:.3f}")
    print(f"  Y-axis: a_y={a[1]:.3f}, b_y={b[1]:.3f}, c_y={c[1]:.3f}")
    print(f"  Z-axis: a_z={a[2]:.3f}, b_z={b[2]:.3f}, c_z={c[2]:.3f}")
    
    # Check for competing directions
    print(f"\nCompeting directions analysis:")
    
    # In X: if a[0] > 0 and b[0] < 0, they move in opposite directions
    if b[0] != 0:
        if np.sign(a[0]) != np.sign(b[0]):
            print(f"  X-axis: a and b have OPPOSITE signs - competing!")
            print(f"    This causes partial cancellation when tiling in X")
        else:
            print(f"  X-axis: a and b have same sign - cooperative")
    
    if c[0] != 0:
        if np.sign(a[0]) != np.sign(c[0]):
            print(f"  X-axis: a and c have OPPOSITE signs - competing!")
    
    # In Y: similar analysis
    if c[1] != 0:
        if np.sign(b[1]) != np.sign(c[1]):
            print(f"  Y-axis: b and c have OPPOSITE signs - competing!")
            print(f"    This causes partial cancellation when tiling in Y")
    
    # Show how offset combinations create coverage patterns
    print(f"\nOffset pattern analysis (for iz=0, varying ix and iy):")
    print(f"  Showingo first few combinations:")
    
    for ix in range(4):
        for iy in range(4):
            offset = ix * a + iy * b
            print(f"    (ix={ix}, iy={iy}): offset = ({offset[0]:.3f}, {offset[1]:.3f})")
        print()
    
    # Calculate coverage overlap
    print(f"\nCoverage overlap analysis:")
    
    # For a 2x2 tiling in the XY plane, we need offsets that span:
    # X: [0, 2*extent_x]
    # Y: [0, 2*extent_y]
    
    extent = get_cell_extent(cell_matrix)
    target_x = 2 * extent[0]
    target_y = 2 * extent[1]
    
    print(f"  Target region: ({target_x:.3f}, {target_y:.3f}) nm")
    
    # Calculate which (ix, iy) combinations produce offsets in the target region
    valid_combos = []
    for ix in range(-5, 10):
        for iy in range(-5, 10):
            offset = ix * a + iy * b
            if 0 <= offset[0] <= target_x and 0 <= offset[1] <= target_y:
                valid_combos.append((ix, iy, offset))
    
    print(f"  Valid (ix, iy) combinations: {len(valid_combos)}")
    print(f"  Showing first 10:")
    for ix, iy, offset in valid_combos[:10]:
        print(f"    (ix={ix}, iy={iy}): offset = ({offset[0]:.3f}, {offset[1]:.3f})")
    
    # Check for gaps in the offset pattern
    if len(valid_combos) > 1:
        offsets = np.array([c[2] for c in valid_combos])
        
        # Sort by X offset
        sorted_by_x = sorted(valid_combos, key=lambda c: c[2][0])
        x_gaps = []
        for i in range(len(sorted_by_x) - 1):
            x_diff = sorted_by_x[i+1][2][0] - sorted_by_x[i][2][0]
            if x_diff > extent[0] * 0.5:  # Gap larger than half unit cell
                x_gaps.append((sorted_by_x[i][2][0], sorted_by_x[i+1][2][0], x_diff))
        
        # Sort by Y offset
        sorted_by_y = sorted(valid_combos, key=lambda c: c[2][1])
        y_gaps = []
        for i in range(len(sorted_by_y) - 1):
            y_diff = sorted_by_y[i+1][2][1] - sorted_by_y[i][2][1]
            if y_diff > extent[1] * 0.5:
                y_gaps.append((sorted_by_y[i][2][1], sorted_by_y[i+1][2][1], y_diff))
        
        print(f"\n  X-direction gaps in offset coverage: {len(x_gaps)}")
        for start, end, diff in x_gaps[:3]:
            print(f"    Gap from {start:.3f} to {end:.3f} nm (width: {diff:.3f} nm)")
        
        print(f"  Y-direction gaps in offset coverage: {len(y_gaps)}")
        for start, end, diff in y_gaps[:3]:
            print(f"    Gap from {start:.3f} to {end:.3f} nm (width: {diff:.3f} nm)")


def main():
    print("="*60)
    print("LATTICE VECTOR INTERACTION ANALYSIS")
    print("="*60)
    
    # Generate Ice II candidate
    print("\nGenerating Ice II candidate...")
    phase_info_ii = {
        "phase_id": "ice_ii",
        "phase_name": "Ice II",
        "density": 1.18,
        "temperature": 238,
        "pressure": 300,
    }
    result_ii = generate_candidates(phase_info_ii, nmolecules=50, n_candidates=1)
    ice_ii = result_ii.candidates[0]
    
    # Generate Ice V candidate
    print("Generating Ice V candidate...")
    phase_info_v = {
        "phase_id": "ice_v",
        "phase_name": "Ice V",
        "density": 1.24,
        "temperature": 253,
        "pressure": 500,
    }
    result_v = generate_candidates(phase_info_v, nmolecules=50, n_candidates=1)
    ice_v = result_v.candidates[0]
    
    # Analyze both
    analyze_lattice_interaction(ice_ii.cell, "Ice II")
    analyze_lattice_interaction(ice_v.cell, "Ice V")


if __name__ == "__main__":
    main()