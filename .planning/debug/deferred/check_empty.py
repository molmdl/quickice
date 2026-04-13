#!/usr/bin/env python
"""Check for actual empty cells in the interface."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.water_filler import get_cell_extent


def check_empty_cells(positions, box_dims, grid_size=20):
    """Check for cells with zero molecules."""
    hist, x_edges, y_edges = np.histogram2d(
        positions[:, 0], positions[:, 1], 
        bins=grid_size, 
        range=[[0, box_dims[0]], [0, box_dims[1]]]
    )
    
    empty_cells = np.where(hist == 0)
    
    if len(empty_cells[0]) > 0:
        print(f"  EMPTY CELLS FOUND: {len(empty_cells[0])}")
        for i in range(min(5, len(empty_cells[0]))):
            x_idx = empty_cells[0][i]
            y_idx = empty_cells[1][i]
            x_center = (x_edges[x_idx] + x_edges[x_idx + 1]) / 2
            y_center = (y_edges[y_idx] + y_edges[y_idx + 1]) / 2
            print(f"    Empty cell at ({x_center:.2f}, {y_center:.2f}) nm")
        if len(empty_cells[0]) > 5:
            print(f"    ... and {len(empty_cells[0]) - 5} more")
    else:
        print(f"  No empty cells found")
    
    return len(empty_cells[0])


def main():
    print("="*60)
    print("EMPTY CELL CHECK")
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
    
    print("\n--- ICE II SLAB ---")
    interface_ii = generate_interface(ice_ii, config)
    ice_pos_ii = interface_ii.positions[:interface_ii.ice_atom_count]
    box_ii = [interface_ii.cell[0, 0], interface_ii.cell[1, 1], interface_ii.cell[2, 2]]
    print(f"Box: {box_ii[0]:.2f} x {box_ii[1]:.2f} nm")
    print(f"Molecules: {interface_ii.ice_nmolecules}")
    empty_ii = check_empty_cells(ice_pos_ii, box_ii, grid_size=20)
    
    print("\n--- ICE V SLAB ---")
    interface_v = generate_interface(ice_v, config)
    ice_pos_v = interface_v.positions[:interface_v.ice_atom_count]
    box_v = [interface_v.cell[0, 0], interface_v.cell[1, 1], interface_v.cell[2, 2]]
    print(f"Box: {box_v[0]:.2f} x {box_v[1]:.2f} nm")
    print(f"Molecules: {interface_v.ice_nmolecules}")
    empty_v = check_empty_cells(ice_pos_v, box_v, grid_size=20)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Ice II empty cells: {empty_ii}")
    print(f"Ice V empty cells: {empty_v}")
    
    if empty_ii > empty_v:
        print(f"\n⚠ Ice II has MORE empty cells than Ice V!")
    elif empty_ii == 0 and empty_v == 0:
        print(f"\n✓ Both have NO empty cells - no gaps!")


if __name__ == "__main__":
    main()