#!/usr/bin/env python
"""Debug script to analyze Ice II vs Ice V interface coverage."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.water_filler import get_cell_extent, is_cell_orthogonal


def analyze_coverage(positions, box_dims, name="Interface", grid_resolution=50):
    """Analyze atom coverage by dividing box into grid cells and checking occupancy."""
    if len(positions) == 0:
        print(f"{name}: No atoms!")
        return
    
    # Create grid
    nx, ny, nz = grid_resolution, grid_resolution, grid_resolution
    grid = np.zeros((nx, ny, nz), dtype=int)
    
    # Normalize positions to grid indices
    x_idx = np.clip((positions[:, 0] / box_dims[0] * nx).astype(int), 0, nx-1)
    y_idx = np.clip((positions[:, 1] / box_dims[1] * ny).astype(int), 0, ny-1)
    z_idx = np.clip((positions[:, 2] / box_dims[2] * nz).astype(int), 0, nz-1)
    
    # Mark occupied cells
    for i in range(len(positions)):
        grid[x_idx[i], y_idx[i], z_idx[i]] = 1
    
    # Calculate coverage
    total_cells = nx * ny * nz
    occupied_cells = np.sum(grid)
    coverage = occupied_cells / total_cells * 100
    
    # Check for large empty regions (gaps)
    # Look at XY slices
    xy_slices_empty = []
    for z in range(nz):
        slice_occupied = np.sum(grid[:, :, z])
        if slice_occupied == 0:
            xy_slices_empty.append(z)
    
    print(f"\n{name}:")
    print(f"  Total atoms: {len(positions)}")
    print(f"  Box: {box_dims[0]:.3f} x {box_dims[1]:.3f} x {box_dims[2]:.3f} nm")
    print(f"  Grid: {nx}x{ny}x{nz} = {total_cells} cells")
    print(f"  Occupied cells: {occupied_cells} ({coverage:.1f}%)")
    if xy_slices_empty:
        print(f"  Empty XY slices: {len(xy_slices_empty)}/{nz} ({len(xy_slices_empty)/nz*100:.1f}%)")
    
    # Check 2D XY coverage (aggregate over Z)
    xy_occupied = np.sum(grid, axis=2) > 0
    xy_coverage = np.sum(xy_occupied) / (nx * ny) * 100
    print(f"  XY coverage: {xy_coverage:.1f}%")
    
    # Find gaps in XY plane
    empty_x_rows = []
    empty_y_cols = []
    for x in range(nx):
        if np.sum(xy_occupied[x, :]) == 0:
            empty_x_rows.append(x)
    for y in range(ny):
        if np.sum(xy_occupied[:, y]) == 0:
            empty_y_cols.append(y)
    
    if empty_x_rows:
        print(f"  Empty X rows: {len(empty_x_rows)}/{nx} ({len(empty_x_rows)/nx*100:.1f}%)")
    if empty_y_cols:
        print(f"  Empty Y cols: {len(empty_y_cols)}/{ny} ({len(empty_y_cols)/ny*100:.1f}%)")
    
    return coverage


def main():
    print("="*60)
    print("Ice II vs Ice V Interface Coverage Analysis")
    print("="*60)
    
    # Test parameters
    box_x, box_y, box_z = 5.0, 5.0, 8.0
    ice_thickness = 2.0
    water_thickness = 4.0
    
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
    
    print(f"Ice II cell matrix:\n{ice_ii.cell}")
    print(f"Ice II cell extent: {get_cell_extent(ice_ii.cell)}")
    print(f"Is orthogonal: {is_cell_orthogonal(ice_ii.cell)}")
    print(f"Positions min: {ice_ii.positions.min(axis=0)}")
    print(f"Positions max: {ice_ii.positions.max(axis=0)}")
    
    # Generate Ice V candidate
    print("\nGenerating Ice V candidate...")
    phase_info_v = {
        "phase_id": "ice_v",
        "phase_name": "Ice V",
        "density": 1.24,
        "temperature": 253,
        "pressure": 500,
    }
    result_v = generate_candidates(phase_info_v, nmolecules=50, n_candidates=1)
    ice_v = result_v.candidates[0]
    
    print(f"Ice V cell matrix:\n{ice_v.cell}")
    print(f"Ice V cell extent: {get_cell_extent(ice_v.cell)}")
    print(f"Is orthogonal: {is_cell_orthogonal(ice_v.cell)}")
    print(f"Positions min: {ice_v.positions.min(axis=0)}")
    print(f"Positions max: {ice_v.positions.max(axis=0)}")
    
    # Generate Ice II slab interface
    print("\n" + "="*60)
    print("SLAB MODE COMPARISON")
    print("="*60)
    
    config = InterfaceConfig(
        mode="slab",
        box_x=box_x,
        box_y=box_y,
        box_z=box_z,
        seed=42,
        ice_thickness=ice_thickness,
        water_thickness=water_thickness,
    )
    
    print(f"\nConfig: box={box_x}x{box_y}x{box_z}nm, ice_thickness={ice_thickness}nm, water_thickness={water_thickness}nm")
    
    print("\nGenerating Ice II slab...")
    interface_ii = generate_interface(ice_ii, config)
    print(interface_ii.report)
    
    # Extract ice positions (first ice_atom_count atoms)
    ice_pos_ii = interface_ii.positions[:interface_ii.ice_atom_count]
    analyze_coverage(ice_pos_ii, [interface_ii.cell[0,0], interface_ii.cell[1,1], interface_ii.cell[2,2]], "Ice II Slab Ice")
    
    print("\nGenerating Ice V slab...")
    interface_v = generate_interface(ice_v, config)
    print(interface_v.report)
    
    ice_pos_v = interface_v.positions[:interface_v.ice_atom_count]
    analyze_coverage(ice_pos_v, [interface_v.cell[0,0], interface_v.cell[1,1], interface_v.cell[2,2]], "Ice V Slab Ice")
    
    # Pocket mode comparison
    print("\n" + "="*60)
    print("POCKET MODE COMPARISON")
    print("="*60)
    
    config_pocket = InterfaceConfig(
        mode="pocket",
        box_x=4.0,
        box_y=4.0,
        box_z=4.0,
        seed=42,
        pocket_diameter=2.0,
        pocket_shape="sphere",
    )
    
    print("\nGenerating Ice II pocket...")
    interface_ii_pocket = generate_interface(ice_ii, config_pocket)
    print(interface_ii_pocket.report)
    
    ice_pos_ii_pocket = interface_ii_pocket.positions[:interface_ii_pocket.ice_atom_count]
    analyze_coverage(ice_pos_ii_pocket, [interface_ii_pocket.cell[0,0], interface_ii_pocket.cell[1,1], interface_ii_pocket.cell[2,2]], "Ice II Pocket Ice")
    
    print("\nGenerating Ice V pocket...")
    interface_v_pocket = generate_interface(ice_v, config_pocket)
    print(interface_v_pocket.report)
    
    ice_pos_v_pocket = interface_v_pocket.positions[:interface_v_pocket.ice_atom_count]
    analyze_coverage(ice_pos_v_pocket, [interface_v_pocket.cell[0,0], interface_v_pocket.cell[1,1], interface_v_pocket.cell[2,2]], "Ice V Pocket Ice")
    
    print("\n" + "="*60)
    print("POSITION DISTRIBUTION ANALYSIS")
    print("="*60)
    
    print("\nIce II slab - Ice positions X range:")
    print(f"  Min X: {ice_pos_ii[:, 0].min():.4f}")
    print(f"  Max X: {ice_pos_ii[:, 0].max():.4f}")
    print(f"  Box X: {interface_ii.cell[0,0]:.4f}")
    print(f"  Coverage: {(ice_pos_ii[:, 0].max() - ice_pos_ii[:, 0].min()) / interface_ii.cell[0,0] * 100:.1f}%")
    
    print("\nIce II slab - Ice positions Y range:")
    print(f"  Min Y: {ice_pos_ii[:, 1].min():.4f}")
    print(f"  Max Y: {ice_pos_ii[:, 1].max():.4f}")
    print(f"  Box Y: {interface_ii.cell[1,1]:.4f}")
    print(f"  Coverage: {(ice_pos_ii[:, 1].max() - ice_pos_ii[:, 1].min()) / interface_ii.cell[1,1] * 100:.1f}%")
    
    print("\nIce V slab - Ice positions X range:")
    print(f"  Min X: {ice_pos_v[:, 0].min():.4f}")
    print(f"  Max X: {ice_pos_v[:, 0].max():.4f}")
    print(f"  Box X: {interface_v.cell[0,0]:.4f}")
    print(f"  Coverage: {(ice_pos_v[:, 0].max() - ice_pos_v[:, 0].min()) / interface_v.cell[0,0] * 100:.1f}%")
    
    print("\nIce V slab - Ice positions Y range:")
    print(f"  Min Y: {ice_pos_v[:, 1].min():.4f}")
    print(f"  Max Y: {ice_pos_v[:, 1].max():.4f}")
    print(f"  Box Y: {interface_v.cell[1,1]:.4f}")
    print(f"  Coverage: {(ice_pos_v[:, 1].max() - ice_pos_v[:, 1].min()) / interface_v.cell[1,1] * 100:.1f}%")


if __name__ == "__main__":
    main()