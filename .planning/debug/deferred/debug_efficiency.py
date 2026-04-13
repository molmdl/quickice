#!/usr/bin/env python
"""Simplified tiling efficiency comparison: Ice II vs Ice V."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.water_filler import get_cell_extent, is_cell_orthogonal


def analyze_tiling_efficiency(positions, cell_matrix, target_region, atoms_per_molecule=3, name="Ice"):
    """Analyze tiling efficiency - how many tiles actually contribute."""
    print(f"\n{'='*60}")
    print(f"{name} TILING EFFICIENCY")
    print(f"{'='*60}")
    
    cell_dims = get_cell_extent(cell_matrix)
    is_triclinic = not is_cell_orthogonal(cell_matrix)
    
    print(f"\nCell matrix:\n{cell_matrix}")
    print(f"Cell extent: {cell_dims}")
    print(f"Target region: {target_region}")
    
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
    
    # Calculate index ranges using inverse cell matrix
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
    
    print(f"\nIndex ranges:")
    print(f"  ix: [{ix_min}, {ix_max}) = {ix_max - ix_min} values")
    print(f"  iy: [{iy_min}, {iy_max}) = {iy_max - iy_min} values")
    print(f"  iz: [{iz_min}, {iz_max}) = {iz_max - iz_min} values")
    
    # Generate all offsets and count valid ones
    lx, ly, lz = target_region
    tol = 1e-10
    
    ix_vals = np.arange(ix_min, ix_max)
    iy_vals = np.arange(iy_min, iy_max)
    iz_vals = np.arange(iz_min, iz_max)
    
    valid_tiles = 0
    invalid_tiles = 0
    total_molecules = 0
    
    # Track which lattice vector combinations contribute
    contributing_ix = set()
    contributing_iy = set()
    contributing_iz = set()
    
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
                    valid_tiles += 1
                    total_molecules += molecules_in_this_tile
                    contributing_ix.add(ix)
                    contributing_iy.add(iy)
                    contributing_iz.add(iz)
                else:
                    invalid_tiles += 1
    
    total_tiles = len(ix_vals) * len(iy_vals) * len(iz_vals)
    
    print(f"\nTiling efficiency:")
    print(f"  Total tiles generated: {total_tiles}")
    print(f"  Valid tiles (contribute molecules): {valid_tiles} ({valid_tiles/total_tiles*100:.1f}%)")
    print(f"  Invalid tiles (no molecules inside): {invalid_tiles} ({invalid_tiles/total_tiles*100:.1f}%)")
    print(f"  Total molecules from valid tiles: {total_molecules}")
    print(f"  Expected molecules (2x2x1): {len(positions) // atoms_per_molecule * 4}")
    
    print(f"\nContributing index ranges:")
    print(f"  ix: [{min(contributing_ix)}, {max(contributing_ix)}] ({len(contributing_ix)} values)")
    print(f"  iy: [{min(contributing_iy)}, {max(contributing_iy)}] ({len(contributing_iy)} values)")
    print(f"  iz: [{min(contributing_iz)}, {max(contributing_iz)}] ({len(contributing_iz)} values)")
    
    # Show the actual lattice vectors
    print(f"\nLattice vectors:")
    print(f"  a = {lattice_a}")
    print(f"  b = {lattice_b}")
    print(f"  c = {lattice_c}")
    
    # Check if lattice vectors have mixed signs
    print(f"\nLattice vector signs (indicates tilt direction):")
    for i, (name, vec) in enumerate([("a", lattice_a), ("b", lattice_b), ("c", lattice_c)]):
        signs = ["+" if v > 0 else "-" if v < 0 else "0" for v in vec]
        print(f"  {name}: [{signs[0]}, {signs[1]}, {signs[2]}]")
    
    return valid_tiles, total_tiles, total_molecules


def main():
    print("="*60)
    print("TILING EFFICIENCY COMPARISON: Ice II vs Ice V")
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
    
    # Analyze both
    ii_result = analyze_tiling_efficiency(ice_ii.positions, ice_ii.cell, target_ii, name="Ice II")
    v_result = analyze_tiling_efficiency(ice_v.positions, ice_v.cell, target_v, name="Ice V")
    
    print("\n" + "="*60)
    print("COMPARISON SUMMARY")
    print("="*60)
    print(f"\nIce II:")
    print(f"  Efficiency: {ii_result[0]}/{ii_result[1]} tiles ({ii_result[0]/ii_result[1]*100:.1f}%)")
    print(f"  Molecules: {ii_result[2]}")
    
    print(f"\nIce V:")
    print(f"  Efficiency: {v_result[0]}/{v_result[1]} tiles ({v_result[0]/v_result[1]*100:.1f}%)")
    print(f"  Molecules: {v_result[2]}")


if __name__ == "__main__":
    main()