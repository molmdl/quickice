#!/usr/bin/env python
"""Detailed density distribution analysis for Ice II vs Ice V interfaces."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.water_filler import get_cell_extent, is_cell_orthogonal


def analyze_density_distribution(positions, box_dims, name="Interface", bins=20):
    """Analyze density distribution across the box."""
    if len(positions) == 0:
        print(f"{name}: No atoms!")
        return
    
    print(f"\n{name} - Density Distribution Analysis")
    print(f"="*50)
    
    # Create histograms for each dimension
    for dim, dim_name in enumerate(['X', 'Y', 'Z']):
        hist, bin_edges = np.histogram(positions[:, dim], bins=bins, range=(0, box_dims[dim]))
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        bin_width = bin_edges[1] - bin_edges[0]
        
        # Normalize by expected uniform density
        expected = len(positions) / bins
        normalized = hist / expected
        
        print(f"\n{dim_name}-axis histogram (normalized by expected uniform density):")
        
        # Find gaps (bins with < 50% of expected density)
        gaps = np.where(normalized < 0.5)[0]
        if len(gaps) > 0:
            print(f"  GAPS FOUND: {len(gaps)} bins with <50% expected density")
            for g in gaps[:5]:  # Show first5 gaps
                print(f"    Bin {g}: [{bin_edges[g]:.3f}, {bin_edges[g+1]:.3f}) nm - density: {normalized[g]:.2%}")
            if len(gaps) > 5:
                print(f"    ... and {len(gaps) - 5} more gaps")
        else:
            print(f"  No gaps found - all bins have >= 50% expected density")
        
        # Statistics
        print(f"  Min density: {normalized.min():.2%}")
        print(f"  Max density: {normalized.max():.2%}")
        print(f"  Mean density: {normalized.mean():.2%}")
        print(f"  Std dev: {normalized.std():.2%}")
    
    # 2D density map for XY plane
    print(f"\nXY-plane 2D density map ({bins}x{bins} grid):")
    hist_2d, x_edges, y_edges = np.histogram2d(
        positions[:, 0], positions[:, 1], 
        bins=bins, 
        range=[[0, box_dims[0]], [0, box_dims[1]]]
    )
    expected_2d = len(positions) / (bins * bins)
    normalized_2d = hist_2d / expected_2d
    
    # Find empty cells
    empty_cells = np.where(hist_2d == 0)
    low_density_cells = np.where(normalized_2d < 0.5)
    
    print(f"  Total cells: {bins * bins}")
    print(f"  Empty cells (0 atoms): {len(empty_cells[0])} ({len(empty_cells[0])/(bins*bins)*100:.1f}%)")
    print(f"  Low density cells (<50%): {len(low_density_cells[0])} ({len(low_density_cells[0])/(bins*bins)*100:.1f}%)")
    
    # Show distribution of densities
    density_values = normalized_2d.flatten()
    print(f"  Density range: {density_values.min():.2%} to {density_values.max():.2%}")
    
    # Count cells by density bracket
    for threshold in [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
        count = np.sum((density_values >= threshold) & (density_values < threshold + 0.25))
        pct = count / len(density_values) * 100
        print(f"    [{threshold:.2f}, {threshold+0.25:.2f}): {count} cells ({pct:.1f}%)")


def main():
    print("="*60)
    print("Ice II vs Ice V Density Distribution Analysis")
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
    
    # Slab mode
    config = InterfaceConfig(
        mode="slab",
        box_x=5.0,
        box_y=5.0,
        box_z=8.0,
        seed=42,
        ice_thickness=2.0,
        water_thickness=4.0,
    )
    
    print("\n" + "="*60)
    print("SLAB MODE ANALYSIS")
    print("="*60)
    
    print("\nGenerating Ice II slab...")
    interface_ii = generate_interface(ice_ii, config)
    ice_pos_ii = interface_ii.positions[:interface_ii.ice_atom_count]
    box_ii = [interface_ii.cell[0,0], interface_ii.cell[1,1], interface_ii.cell[2,2]]
    analyze_density_distribution(ice_pos_ii, box_ii, "Ice II Slab Ice")
    
    print("\nGenerating Ice V slab...")
    interface_v = generate_interface(ice_v, config)
    ice_pos_v = interface_v.positions[:interface_v.ice_atom_count]
    box_v = [interface_v.cell[0,0], interface_v.cell[1,1], interface_v.cell[2,2]]
    analyze_density_distribution(ice_pos_v, box_v, "Ice V Slab Ice")
    
    # Pocket mode
    config_pocket = InterfaceConfig(
        mode="pocket",
        box_x=4.0,
        box_y=4.0,
        box_z=4.0,
        seed=42,
        pocket_diameter=2.0,
        pocket_shape="sphere",
    )
    
    print("\n" + "="*60)
    print("POCKET MODE ANALYSIS")
    print("="*60)
    
    print("\nGenerating Ice II pocket...")
    interface_ii_pocket = generate_interface(ice_ii, config_pocket)
    ice_pos_ii_pocket = interface_ii_pocket.positions[:interface_ii_pocket.ice_atom_count]
    box_ii_pocket = [interface_ii_pocket.cell[0,0], interface_ii_pocket.cell[1,1], interface_ii_pocket.cell[2,2]]
    analyze_density_distribution(ice_pos_ii_pocket, box_ii_pocket, "Ice II Pocket Ice")
    
    print("\nGenerating Ice V pocket...")
    interface_v_pocket = generate_interface(ice_v, config_pocket)
    ice_pos_v_pocket = interface_v_pocket.positions[:interface_v_pocket.ice_atom_count]
    box_v_pocket = [interface_v_pocket.cell[0,0], interface_v_pocket.cell[1,1], interface_v_pocket.cell[2,2]]
    analyze_density_distribution(ice_pos_v_pocket, box_v_pocket, "Ice V Pocket Ice")


if __name__ == "__main__":
    main()