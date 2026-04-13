#!/usr/bin/env python
"""Check if molecules are being filtered unnecessarily at boundaries."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.water_filler import get_cell_extent


def analyze_boundary_filtering(ice_candidate, ice_type, config):
    """Analyze how many molecules are filtered at boundaries."""
    from quickice.structure_generation.water_filler import tile_structure
    
    # Get the parameters used by slab mode
    cell_matrix = ice_candidate.cell
    ice_cell_dims = get_cell_extent(cell_matrix)
    
    # Periodicity adjustments (mimicking slab.py)
    def round_to_periodicity(target_dim, cell_dim, min_multiplier=1):
        import math
        if cell_dim <= 0:
            return target_dim, min_multiplier
        n_cells = max(min_multiplier, math.ceil(target_dim / cell_dim))
        adjusted_dim = n_cells * cell_dim
        return adjusted_dim, n_cells
    
    adjusted_box_x, nx = round_to_periodicity(config.box_x, ice_cell_dims[0])
    adjusted_box_y, ny = round_to_periodicity(config.box_y, ice_cell_dims[1])
    adjusted_ice_thickness, nz_ice = round_to_periodicity(config.ice_thickness, ice_cell_dims[2])
    
    print(f"\n{ice_type} boundary filtering analysis:")
    print(f"  Adjusted box: {adjusted_box_x:.3f} x {adjusted_box_y:.3f} nm")
    print(f"  Adjusted ice thickness: {adjusted_ice_thickness:.3f} nm")
    print(f"  Cell counts: nx={nx}, ny={ny}, nz_ice={nz_ice}")
    
    # Tile the ice (bottom layer)
    target_region = np.array([adjusted_box_x, adjusted_box_y, adjusted_ice_thickness])
    
    # Count molecules before and after tiling
    n_original_molecules = len(ice_candidate.positions) // 3
    expected_molecules = nx * ny * nz_ice * n_original_molecules
    
    print(f"  Original molecules: {n_original_molecules}")
    print(f"  Expected after tiling (nx*ny*nz): {expected_molecules}")
    
    # Actually tile
    tiled_positions, tiled_molecules = tile_structure(
        ice_candidate.positions,
        ice_cell_dims,
        target_region,
        atoms_per_molecule=3,
        cell_matrix=cell_matrix
    )
    
    print(f"  Actual after tiling: {tiled_molecules}")
    print(f"  Molecules lost: {expected_molecules - tiled_molecules}")
    print(f"  Loss percentage: {(expected_molecules - tiled_molecules) / expected_molecules * 100:.1f}%")
    
    # Analyze where molecules are lost
    # Generate all offsets and count molecules per tile
    is_triclinic = True  # For Ice II and Ice V
    
    inv_cell = np.linalg.inv(cell_matrix)
    pos_min = ice_candidate.positions.min(axis=0)
    pos_max = ice_candidate.positions.max(axis=0)
    
    offset_min_needed = -pos_max
    offset_max_needed = target_region - pos_min
    frac_min = offset_min_needed @ inv_cell.T
    frac_max = offset_max_needed @ inv_cell.T
    
    ix_min = int(np.floor(frac_min[0])) - 1
    ix_max = int(np.ceil(frac_max[0])) + 1
    iy_min = int(np.floor(frac_min[1])) - 1
    iy_max = int(np.ceil(frac_max[1])) + 1
    iz_min = int(np.floor(frac_min[2])) - 1
    iz_max = int(np.ceil(frac_max[2])) + 1
    
    lattice_a = cell_matrix[0]
    lattice_b = cell_matrix[1]
    lattice_c = cell_matrix[2]
    
    lx, ly, lz = target_region
    tol = 1e-10
    
    # Count valid molecules per tile
    valid_per_tile = {}
    for ix in range(ix_min, ix_max):
        for iy in range(iy_min, iy_max):
            for iz in range(iz_min, iz_max):
                offset = ix * lattice_a + iy * lattice_b + iz * lattice_c
                shifted = ice_candidate.positions + offset
                
                valid_count = 0
                for mol_idx in range(n_original_molecules):
                    start = mol_idx * 3
                    end = start + 3
                    mol = shifted[start:end]
                    
                    all_inside_x = np.all((mol[:, 0] >= 0) & (mol[:, 0] < lx - tol))
                    all_inside_y = np.all((mol[:, 1] >= 0) & (mol[:, 1] < ly - tol))
                    all_inside_z = np.all((mol[:, 2] >= 0) & (mol[:, 2] < lz - tol))
                    
                    if all_inside_x and all_inside_y and all_inside_z:
                        valid_count += 1
                
                if valid_count > 0:
                    valid_per_tile[(ix, iy, iz)] = valid_count
    
    print(f"  Tiles with valid molecules: {len(valid_per_tile)}")
    
    # Show distribution of valid molecules per tile
    counts = list(valid_per_tile.values())
    print(f"  Molecules per tile: min={min(counts)}, max={max(counts)}, avg={np.mean(counts):.1f}")
    
    # Compare to expected (all tiles should have ~n_original_molecules)
    full_tiles = sum(1 for c in counts if c == n_original_molecules)
    partial_tiles = sum(1 for c in counts if 0 < c < n_original_molecules)
    
    print(f"  Full tiles (all {n_original_molecules} molecules): {full_tiles}")
    print(f"  Partial tiles: {partial_tiles}")
    
    return tiled_molecules, expected_molecules


def main():
    print("="*60)
    print("BOUNDARY FILTERING ANALYSIS")
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
    
    # Analyze both
    analyze_boundary_filtering(ice_ii, "Ice II", config)
    analyze_boundary_filtering(ice_v, "Ice V", config)


if __name__ == "__main__":
    main()