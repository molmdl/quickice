#!/usr/bin/env python
"""Fine-resolution gap detection for Ice II."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.water_filler import get_cell_extent


def find_gaps_at_resolution(interface, grid_size, density_threshold=0.4):
    """Find gaps at a specific grid resolution."""
    ice_pos = interface.positions[:interface.ice_atom_count]
    box_dims = [interface.cell[0, 0], interface.cell[1, 1], interface.cell[2, 2]]
    
    if len(ice_pos) == 0:
        return []
    
    # Create 2D histogram for XY plane
    hist, x_edges, y_edges = np.histogram2d(
        ice_pos[:, 0], ice_pos[:, 1], 
        bins=grid_size, 
        range=[[0, box_dims[0]], [0, box_dims[1]]]
    )
    
    # Normalize by expected density
    expected = len(ice_pos) / (grid_size * grid_size)
    normalized = hist / expected
    
    # Find gaps
    gaps = np.where(normalized < density_threshold)
    
    gap_info = []
    for i in range(len(gaps[0])):
        x_idx = gaps[0][i]
        y_idx = gaps[1][i]
        x_center = (x_edges[x_idx] + x_edges[x_idx + 1]) / 2
        y_center = (y_edges[y_idx] + y_edges[y_idx + 1]) / 2
        density = normalized[x_idx, y_idx]
        gap_info.append({
            'x_center': x_center,
            'y_center': y_center,
            'density': density,
            'count': hist[x_idx, y_idx],
            'expected': expected,
        })
    
    return gap_info


def main():
    print("="*60)
    print("FINE-RESOLUTION GAP ANALYSIS")
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
    from quickice.structure_generation import generate_candidates
    result_ii = generate_candidates(phase_info_ii, nmolecules=50, n_candidates=1)
    ice_ii = result_ii.candidates[0]
    
    # Generate interface
    config = InterfaceConfig(
        mode="slab",
        box_x=5.0,
        box_y=5.0,
        box_z=8.0,
        seed=42,
        ice_thickness=2.0,
        water_thickness=4.0,
    )
    
    interface_ii = generate_interface(ice_ii, config)
    box_dims = [interface_ii.cell[0, 0], interface_ii.cell[1, 1], interface_ii.cell[2, 2]]
    
    print(f"\nIce II Slab Interface:")
    print(f"  Box: {box_dims[0]:.2f} x {box_dims[1]:.2f} x {box_dims[2]:.2f} nm")
    print(f"  Ice molecules: {interface_ii.ice_nmolecules}")
    
    # Test different resolutions
    for grid_size in [10, 15, 20, 25, 30]:
        gaps = find_gaps_at_resolution(interface_ii, grid_size, density_threshold=0.4)
        print(f"\n  Grid {grid_size}x{grid_size}: {len(gaps)} low density areas")
        
        if gaps and len(gaps) <= 10:
            for gap in gaps:
                print(f"    ({gap['x_center']:.2f}, {gap['y_center']:.2f}): {gap['density']*100:.1f}% density ({gap['count']:.0f}/{gap['expected']:.1f})")
    
    # Now generate Ice V for comparison
    print("\n" + "="*60)
    print("ICE V COMPARISON")
    print("="*60)
    
    phase_info_v = {
        "phase_id": "ice_v",
        "phase_name": "Ice V",
        "density": 1.24,
        "temperature": 253,
        "pressure": 500,
    }
    result_v = generate_candidates(phase_info_v, nmolecules=50, n_candidates=1)
    ice_v = result_v.candidates[0]
    
    interface_v = generate_interface(ice_v, config)
    box_dims_v = [interface_v.cell[0, 0], interface_v.cell[1, 1], interface_v.cell[2, 2]]
    
    print(f"\nIce V Slab Interface:")
    print(f"  Box: {box_dims_v[0]:.2f} x {box_dims_v[1]:.2f} x {box_dims_v[2]:.2f} nm")
    print(f"  Ice molecules: {interface_v.ice_nmolecules}")
    
    for grid_size in [10, 15, 20, 25, 30]:
        gaps = find_gaps_at_resolution(interface_v, grid_size, density_threshold=0.4)
        print(f"\n  Grid {grid_size}x{grid_size}: {len(gaps)} low density areas")
        
        if gaps and len(gaps) <= 10:
            for gap in gaps:
                print(f"    ({gap['x_center']:.2f}, {gap['y_center']:.2f}): {gap['density']*100:.1f}% density ({gap['count']:.0f}/{gap['expected']:.1f})")


if __name__ == "__main__":
    main()