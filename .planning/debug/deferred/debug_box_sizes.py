#!/usr/bin/env python
"""Test Ice II and Ice V with various box sizes to find gap patterns."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.water_filler import get_cell_extent


def analyze_gaps(positions, box_dims, threshold=0.3, grid_size=15):
    """Find gaps in the XY plane density distribution."""
    if len(positions) == 0:
        return 0, []
    
    # Create 2D histogram for XY plane
    hist, x_edges, y_edges = np.histogram2d(
        positions[:, 0], positions[:, 1], 
        bins=grid_size, 
        range=[[0, box_dims[0]], [0, box_dims[1]]]
    )
    
    # Normalize by expected density
    expected = len(positions) / (grid_size * grid_size)
    normalized = hist / expected
    
    # Find gaps (cells with density < threshold)
    gaps = np.where(normalized < threshold)
    
    # Get gap locations in nm
    gap_locations = []
    for i in range(len(gaps[0])):
        x_idx = gaps[0][i]
        y_idx = gaps[1][i]
        x_center = (x_edges[x_idx] + x_edges[x_idx + 1]) / 2
        y_center = (y_edges[y_idx] + y_edges[y_idx + 1]) / 2
        density = normalized[x_idx, y_idx]
        gap_locations.append((x_center, y_center, density))
    
    return len(gap_locations), gap_locations


def test_box_size(ice_candidate, ice_type, box_x, box_y, ice_thickness):
    """Test a specific box configuration."""
    config = InterfaceConfig(
        mode="slab",
        box_x=box_x,
        box_y=box_y,
        box_z=2 * ice_thickness + 4.0,  # 4.0 nm water
        seed=42,
        ice_thickness=ice_thickness,
        water_thickness=4.0,
    )
    
    interface = generate_interface(ice_candidate, config)
    ice_pos = interface.positions[:interface.ice_atom_count]
    box_dims = [interface.cell[0, 0], interface.cell[1, 1], interface.cell[2, 2]]
    
    # Analyze gaps
    n_gaps, gap_locations = analyze_gaps(ice_pos, box_dims, threshold=0.4, grid_size=15)
    
    # Calculate coverage
    if len(ice_pos) > 0:
        x_coverage = (ice_pos[:, 0].max() - ice_pos[:, 0].min()) / box_dims[0] * 100
        y_coverage = (ice_pos[:, 1].max() - ice_pos[:, 1].min()) / box_dims[1] * 100
    else:
        x_coverage = 0
        y_coverage = 0
    
    return {
        'ice_type': ice_type,
        'box_x': box_dims[0],
        'box_y': box_dims[1],
        'n_molecules': interface.ice_nmolecules,
        'n_gaps': n_gaps,
        'x_coverage': x_coverage,
        'y_coverage': y_coverage,
        'gap_locations': gap_locations[:5] if gap_locations else [],  # First 5 gaps
    }


def main():
    print("="*60)
    print("BOX SIZE SENSITIVITY TEST: Ice II vs Ice V")
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
    extent_ii = get_cell_extent(ice_ii.cell)
    print(f"Ice II unit cell extent: {extent_ii}")
    
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
    extent_v = get_cell_extent(ice_v.cell)
    print(f"Ice V unit cell extent: {extent_v}")
    
    # Test different box sizes
    test_configs = [
        # (box_x, box_y, ice_thickness)
        (5.0, 5.0, 2.0),  # Default
        (6.0, 6.0, 2.0),  # Larger
        (7.0, 7.0, 3.0),  # Even larger
        (8.0, 8.0, 3.0),  # Large
    ]
    
    print("\n" + "="*60)
    print("ICE II RESULTS")
    print("="*60)
    
    for box_x, box_y, ice_thickness in test_configs:
        result = test_box_size(ice_ii, "Ice II", box_x, box_y, ice_thickness)
        print(f"\nConfig: box={box_x}x{box_y}, ice_thickness={ice_thickness}")
        print(f"  Actual box: {result['box_x']:.2f} x {result['box_y']:.2f} nm")
        print(f"  Molecules: {result['n_molecules']}")
        print(f"  X coverage: {result['x_coverage']:.1f}%")
        print(f"  Y coverage: {result['y_coverage']:.1f}%")
        print(f"  Low density areas: {result['n_gaps']}")
        if result['gap_locations']:
            print(f"  Sample gaps (x, y, density%):")
            for x, y, d in result['gap_locations'][:3]:
                print(f"    ({x:.2f}, {y:.2f}): {d*100:.1f}%")
    
    print("\n" + "="*60)
    print("ICE V RESULTS")
    print("="*60)
    
    for box_x, box_y, ice_thickness in test_configs:
        result = test_box_size(ice_v, "Ice V", box_x, box_y, ice_thickness)
        print(f"\nConfig: box={box_x}x{box_y}, ice_thickness={ice_thickness}")
        print(f"  Actual box: {result['box_x']:.2f} x {result['box_y']:.2f} nm")
        print(f"  Molecules: {result['n_molecules']}")
        print(f"  X coverage: {result['x_coverage']:.1f}%")
        print(f"  Y coverage: {result['y_coverage']:.1f}%")
        print(f"  Low density areas: {result['n_gaps']}")
        if result['gap_locations']:
            print(f"  Sample gaps (x, y, density%):")
            for x, y, d in result['gap_locations'][:3]:
                print(f"    ({x:.2f}, {y:.2f}): {d*100:.1f}%")


if __name__ == "__main__":
    main()