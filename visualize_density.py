#!/usr/bin/env python
"""Visualize density distribution to understand the gap issue."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.water_filler import get_cell_extent


def print_density_map(positions, box_dims, grid_size=10):
    """Print a text-based density map."""
    hist, x_edges, y_edges = np.histogram2d(
        positions[:, 0], positions[:, 1], 
        bins=grid_size, 
        range=[[0, box_dims[0]], [0, box_dims[1]]]
    )
    
    expected = len(positions) / (grid_size * grid_size)
    normalized = hist / expected
    
    print(f"\nDensity map ({grid_size}x{grid_size}), normalized by expected density:")
    print("Y-axis ↑")
    
    for y_idx in range(grid_size - 1, -1, -1):
        row = []
        for x_idx in range(grid_size):
            density = normalized[x_idx, y_idx]
            if density < 0.5:
                char = "!"  # Low density
            elif density < 0.75:
                char = "-"  # Below average
            elif density < 1.25:
                char = "."  # Near average
            elif density < 1.5:
                char = "+"  # Above average
            else:
                char = "*"  # High density
            row.append(char)
        y_center = (y_edges[y_idx] + y_edges[y_idx + 1]) / 2
        print(f"  {y_center:5.2f} | {''.join(row)}")
    
    print("        " + "-" * grid_size + "> X-axis")
    print("        " + "".join([f"{(x_edges[i] + x_edges[i+1])/2:5.2f}"[:5] for i in range(min(5, grid_size))]))
    
    print(f"\nLegend: ! (<50%)  - (50-75%)  . (75-125%)  + (125-150%)  * (>150%)")
    print(f"Min density: {normalized.min()*100:.1f}%, Max: {normalized.max()*100:.1f}%, Mean: {normalized.mean()*100:.1f}%")


def main():
    print("="*60)
    print("DENSITY VISUALIZATION: Ice II vs Ice V")
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
    
    # Generate Ice II interface
    print("\n" + "="*60)
    print("ICE II SLAB INTERFACE")
    print("="*60)
    
    interface_ii = generate_interface(ice_ii, config)
    ice_pos_ii = interface_ii.positions[:interface_ii.ice_atom_count]
    box_ii = [interface_ii.cell[0, 0], interface_ii.cell[1, 1], interface_ii.cell[2, 2]]
    
    print(f"\nBox: {box_ii[0]:.2f} x {box_ii[1]:.2f} x {box_ii[2]:.2f} nm")
    print(f"Ice molecules: {interface_ii.ice_nmolecules}")
    
    print_density_map(ice_pos_ii, box_ii, grid_size=10)
    
    # Generate Ice V interface
    print("\n" + "="*60)
    print("ICE V SLAB INTERFACE")
    print("="*60)
    
    interface_v = generate_interface(ice_v, config)
    ice_pos_v = interface_v.positions[:interface_v.ice_atom_count]
    box_v = [interface_v.cell[0, 0], interface_v.cell[1, 1], interface_v.cell[2, 2]]
    
    print(f"\nBox: {box_v[0]:.2f} x {box_v[1]:.2f} x {box_v[2]:.2f} nm")
    print(f"Ice molecules: {interface_v.ice_nmolecules}")
    
    print_density_map(ice_pos_v, box_v, grid_size=10)


if __name__ == "__main__":
    main()