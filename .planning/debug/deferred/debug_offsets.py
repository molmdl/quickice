#!/usr/bin/env python
"""Investigate tiling offset calculation for Ice II vs Ice V."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.water_filler import get_cell_extent, is_cell_orthogonal


def simulate_tiling(positions, cell_matrix, target_region, atoms_per_molecule=3):
    """Simulate tiling and show detailed offset calculation."""
    print(f"\n{'='*60}")
    print("TILING SIMULATION")
    print(f"{'='*60}")
    
    cell_dims = get_cell_extent(cell_matrix)
    print(f"\nCell matrix:\n{cell_matrix}")
    print(f"Cell extent: {cell_dims}")
    print(f"Target region: {target_region}")
    
    is_triclinic = not is_cell_orthogonal(cell_matrix)
    print(f"Is triclinic: {is_triclinic}")
    
    if not is_triclinic:
        print("Orthogonal cell - standard tiling")
        return
    
    # Triclinic tiling simulation
    lattice_a = cell_matrix[0]
    lattice_b = cell_matrix[1]
    lattice_c = cell_matrix[2]
    
    pos_min = positions.min(axis=0)
    pos_max = positions.max(axis=0)
    
    print(f"\nPosition bounds:")
    print(f"  pos_min: {pos_min}")
    print(f"  pos_max: {pos_max}")
    
    # Calculate required offset range
    offset_min_needed = -pos_max
    offset_max_needed = target_region - pos_min
    
    print(f"\nRequired offset range:")
    print(f"  offset_min_needed: {offset_min_needed}")
    print(f"  offset_max_needed: {offset_max_needed}")
    
    # Calculate index ranges using inverse cell matrix
    inv_cell = np.linalg.inv(cell_matrix)
    frac_min = offset_min_needed @ inv_cell.T
    frac_max = offset_max_needed @ inv_cell.T
    
    print(f"\nFractional coordinates of offset bounds:")
    print(f"  frac_min: {frac_min}")
    print(f"  frac_max: {frac_max}")
    
    ix_min = int(np.floor(frac_min[0])) - 1
    ix_max = int(np.ceil(frac_max[0])) + 1
    iy_min = int(np.floor(frac_min[1])) - 1
    iy_max = int(np.ceil(frac_max[1])) + 1
    iz_min = int(np.floor(frac_min[2])) - 1
    iz_max = int(np.ceil(frac_max[2])) + 1
    
    print(f"\nIndex ranges:")
    print(f"  ix: [{ix_min}, {ix_max}) = {ix_max - ix_min} values")
    print(f"  iy: [{iy_min}, {iy_max}) = {iy_max - iy_min} values")
    print(f"  iz: [{iz_min}, {iz_max}) = {iz_max - iz_min} values")
    
    # Generate all offsets
    ix_vals = np.arange(ix_min, ix_max)
    iy_vals = np.arange(iy_min, iy_max)
    iz_vals = np.arange(iz_min, iz_max)
    
    # Count molecules that survive filtering
    lx, ly, lz = target_region
    tol = 1e-10
    
    all_positions_list = []
    valid_count = 0
    invalid_offsets = []
    
    for ix in ix_vals:
        for iy in iy_vals:
            for iz in iz_vals:
                offset = ix * lattice_a + iy * lattice_b + iz * lattice_c
                shifted = positions + offset
                
                # Check if any molecule is fully inside
                n_molecules = len(shifted) // atoms_per_molecule
                molecules_in_this_tile = 0
                
                for mol_idx in range(n_molecules):
                    start = mol_idx * atoms_per_molecule
                    end = start + atoms_per_molecule
                    mol = shifted[start:end]
                    
                    all_inside_x = np.all((mol[:, 0] >= 0) & (mol[:, 0] < lx - tol))
                    all_inside_y = np.all((mol[:, 1] >= 0) & (mol[:, 1] < ly - tol))
                    all_inside_z = np.all((mol[:, 2] >= 0) & (mol[:, 2] < lz - tol))
                    
                    if all_inside_x and all_inside_y and all_inside_z:
                        molecules_in_this_tile += 1
                
                if molecules_in_this_tile > 0:
                    valid_count += molecules_in_this_tile
                else:
                    invalid_offsets.append((ix, iy, iz, offset))
    
    print(f"\nTiling results:")
    print(f"  Total tiles: {len(ix_vals) * len(iy_vals) * len(iz_vals)}")
    print(f"  Invalid tiles (no molecules inside): {len(invalid_offsets)}")
    print(f"  Valid molecules: {valid_count}")
    print(f"  Expected molecules: {len(positions) // atoms_per_molecule * 4}")  # Roughly 2x2x1 tiling
    
    # Show some invalid offsets
    if invalid_offsets:
        print(f"\nSample invalid offsets (first 5):")
        for ix, iy, iz, offset in invalid_offsets[:5]:
            print(f"  [{ix}, {iy}, {iz}]: offset = {offset}")


def analyze_offset_distribution(positions, cell_matrix, target_region, atoms_per_molecule=3):
    """Analyze how offsets distribute atoms across the target region."""
    print(f"\n{'='*60}")
    print("OFFSET DISTRIBUTION ANALYSIS")
    print(f"{'='*60}")
    
    cell_dims = get_cell_extent(cell_matrix)
    is_triclinic = not is_cell_orthogonal(cell_matrix)
    
    if not is_triclinic:
        return
    
    lattice_a = cell_matrix[0]
    lattice_b = cell_matrix[1]
    lattice_c = cell_matrix[2]
    
    pos_min = positions.min(axis=0)
    pos_max = positions.max(axis=0)
    
    inv_cell = np.linalg.inv(cell_matrix)
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
    
    lx, ly, lz = target_region
    tol = 1e-10
    
    # Track which tiles contribute to which XY regions
    from collections import defaultdict
    xy_contributions = defaultdict(list)  # (x_bin, y_bin) -> list of tile indices
    
    n_bins = 10
    x_bin_size = lx / n_bins
    y_bin_size = ly / n_bins
    
    ix_vals = np.arange(ix_min, ix_max)
    iy_vals = np.arange(iy_min, iy_max)
    iz_vals = np.arange(iz_min, iz_max)
    
    all_shifted = []
    
    for ix in ix_vals:
        for iy in iy_vals:
            for iz in iz_vals:
                offset = ix * lattice_a + iy * lattice_b + iz * lattice_c
                shifted = positions + offset
                
                # Only keep atoms inside target region
                n_molecules = len(shifted) // atoms_per_molecule
                for mol_idx in range(n_molecules):
                    start = mol_idx * atoms_per_molecule
                    end = start + atoms_per_molecule
                    mol = shifted[start:end]
                    
                    all_inside_x = np.all((mol[:, 0] >= 0) & (mol[:, 0] < lx - tol))
                    all_inside_y = np.all((mol[:, 1] >= 0) & (mol[:, 1] < ly - tol))
                    all_inside_z = np.all((mol[:, 2] >= 0) & (mol[:, 2] < lz - tol))
                    
                    if all_inside_x and all_inside_y and all_inside_z:
                        all_shifted.append(mol)
                        
                        # Track contribution to XY bins
                        com_x = mol[:, 0].mean()
                        com_y = mol[:, 1].mean()
                        x_bin = min(int(com_x / x_bin_size), n_bins - 1)
                        y_bin = min(int(com_y / y_bin_size), n_bins - 1)
                        xy_contributions[(x_bin, y_bin)].append((ix, iy, iz))
    
    if all_shifted:
        all_shifted = np.vstack(all_shifted)
        print(f"\nTotal molecules after filtering: {len(all_shifted) // atoms_per_molecule}")
        
        # Analyze XY contribution distribution
        print(f"\nXY contribution analysis ({n_bins}x{n_bins} grid):")
        
        # Count molecules per bin
        mol_per_bin = np.zeros((n_bins, n_bins))
        for i, mol in enumerate(all_shifted):
            com_x = mol[:, 0].mean()
            com_y = mol[:, 1].mean()
            x_bin = min(int(com_x / x_bin_size), n_bins - 1)
            y_bin = min(int(com_y / y_bin_size), n_bins - 1)
            mol_per_bin[x_bin, y_bin] += 1
        
        expected_per_bin = len(all_shifted) // atoms_per_molecule / (n_bins * n_bins)
        print(f"Expected molecules per bin: {expected_per_bin:.1f}")
        
        # Find bins with low contribution
        low_bins = np.where(mol_per_bin < expected_per_bin * 0.5)
        print(f"\nLow density bins (< 50% of expected): {len(low_bins[0])}")
        
        for i in range(len(low_bins[0])):
            x_bin = low_bins[0][i]
            y_bin = low_bins[1][i]
            actual = mol_per_bin[x_bin, y_bin]
            pct = actual / expected_per_bin * 100
            print(f"  Bin ({x_bin}, {y_bin}): {actual:.0f} molecules ({pct:.1f}% of expected)")
            
            # Check which tiles contribute to this bin
            tiles = xy_contributions.get((x_bin, y_bin), [])
            unique_tiles = set((t[0], t[1]) for t in tiles)  # Unique (ix, iy) pairs
            print(f"    Contributing tiles (ix, iy): {len(unique_tiles)} unique")


def main():
    print("="*60)
    print("OFFSET CALCULATION ANALYSIS: Ice II vs Ice V")
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
    
    # Target regions (2x extent in X and Y)
    extent_ii = get_cell_extent(ice_ii.cell)
    extent_v = get_cell_extent(ice_v.cell)
    target_ii = extent_ii * np.array([2, 2, 1])
    target_v = extent_v * np.array([2, 2, 1])
    
    print("\n" + "="*60)
    print("ICE II ANALYSIS")
    print("="*60)
    simulate_tiling(ice_ii.positions, ice_ii.cell, target_ii)
    analyze_offset_distribution(ice_ii.positions, ice_ii.cell, target_ii)
    
    print("\n" + "="*60)
    print("ICE V ANALYSIS")
    print("="*60)
    simulate_tiling(ice_v.positions, ice_v.cell, target_v)
    analyze_offset_distribution(ice_v.positions, ice_v.cell, target_v)


if __name__ == "__main__":
    main()