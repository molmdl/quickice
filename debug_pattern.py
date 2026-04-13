#!/usr/bin/env python
"""Analyze if Ice II gaps follow a crystallographic pattern."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.water_filler import get_cell_extent


def analyze_gap_pattern(interface, ice_candidate, name="Ice"):
    """Analyze if gaps follow a specific pattern related to crystal structure."""
    ice_pos = interface.positions[:interface.ice_atom_count]
    box_dims = [interface.cell[0, 0], interface.cell[1, 1], interface.cell[2, 2]]
    cell_matrix = ice_candidate.cell
    
    print(f"\n{name} gap pattern analysis:")
    
    # Create density map
    grid_size = 20
    hist, x_edges, y_edges = np.histogram2d(
        ice_pos[:, 0], ice_pos[:, 1], 
        bins=grid_size, 
        range=[[0, box_dims[0]], [0, box_dims[1]]]
    )
    
    # Normalize
    expected = len(ice_pos) / (grid_size * grid_size)
    normalized = hist / expected
    
    # Find low density regions
    threshold = 0.5
    low_density = np.where(normalized < threshold)
    
    print(f"  Low density regions (< {threshold*100:.0f}%): {len(low_density[0])}")
    
    if len(low_density[0]) > 0:
        # Get gap locations
        gap_x = []
        gap_y = []
        for i in range(len(low_density[0])):
            x_idx = low_density[0][i]
            y_idx = low_density[1][i]
            x_center = (x_edges[x_idx] + x_edges[x_idx + 1]) / 2
            y_center = (y_edges[y_idx] + y_edges[y_idx + 1]) / 2
            gap_x.append(x_center)
            gap_y.append(y_center)
        
        gap_x = np.array(gap_x)
        gap_y = np.array(gap_y)
        
        print(f"  Gap locations:")
        print(f"    X range: {gap_x.min():.2f} to {gap_x.max():.2f} nm")
        print(f"    Y range: {gap_y.min():.2f} to {gap_y.max():.2f} nm")
        
        # Check if gaps align with box edges
        x_near_edge = (gap_x < box_dims[0] * 0.1) | (gap_x > box_dims[0] * 0.9)
        y_near_edge = (gap_y < box_dims[1] * 0.1) | (gap_y > box_dims[1] * 0.9)
        
        print(f"    Gaps near X edge: {np.sum(x_near_edge)} / {len(gap_x)}")
        print(f"    Gaps near Y edge: {np.sum(y_near_edge)} / {len(gap_y)}")
        
        # Check if gaps align with unit cell boundaries
        cell_extent = get_cell_extent(cell_matrix)
        
        # Check alignment with X cell boundaries
        x_at_cell_boundary = False
        for n in range(1, 10):
            boundary = n * cell_extent[0]
            if boundary < box_dims[0]:
                # Check if any gap is near this boundary
                near_boundary = np.abs(gap_x - boundary) < box_dims[0] / grid_size
                if np.any(near_boundary):
                    x_at_cell_boundary = True
                    print(f"    Gaps near X cell boundary at {boundary:.2f} nm: {np.sum(near_boundary)}")
        
        # Check alignment with Y cell boundaries
        y_at_cell_boundary = False
        for n in range(1, 10):
            boundary = n * cell_extent[1]
            if boundary < box_dims[1]:
                near_boundary = np.abs(gap_y - boundary) < box_dims[1] / grid_size
                if np.any(near_boundary):
                    y_at_cell_boundary = True
                    print(f"    Gaps near Y cell boundary at {boundary:.2f} nm: {np.sum(near_boundary)}")
        
        # Check if gaps form a line or cluster
        if len(gap_x) > 1:
            # Calculate centroid and spread
            centroid_x = gap_x.mean()
            centroid_y = gap_y.mean()
            spread_x = gap_x.std()
            spread_y = gap_y.std()
            
            print(f"  Gap cluster centroid: ({centroid_x:.2f}, {centroid_y:.2f}) nm")
            print(f"  Gap cluster spread: X={spread_x:.2f} nm, Y={spread_y:.2f} nm")
            
            # Check if gaps are clustered (small spread) or scattered (large spread)
            if spread_x < box_dims[0] * 0.1 and spread_y < box_dims[1] * 0.1:
                print(f"  Pattern: Clustered gaps (small spread)")
            else:
                print(f"  Pattern: Scattered gaps (large spread)")


def main():
    print("="*60)
    print("GAP PATTERN ANALYSIS")
    print("="*60)
    
    # Generate candidates
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
    
    # Slab config
    config = InterfaceConfig(
        mode="slab",
        box_x=5.0,
        box_y=5.0,
        box_z=8.0,
        seed=42,
        ice_thickness=2.0,
        water_thickness=4.0,
    )
    
    # Generate interfaces
    interface_ii = generate_interface(ice_ii, config)
    interface_v = generate_interface(ice_v, config)
    
    # Analyze patterns
    analyze_gap_pattern(interface_ii, ice_ii, "Ice II")
    analyze_gap_pattern(interface_v, ice_v, "Ice V")


if __name__ == "__main__":
    main()