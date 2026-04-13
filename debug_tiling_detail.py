#!/usr/bin/env python
"""Deep debug of tiling behavior for Ice II vs Ice V."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.water_filler import get_cell_extent, is_cell_orthogonal


def analyze_tiling_detail(ice_type, candidate, target_region, atoms_per_molecule=3):
    """Detailed analysis of tiling parameters."""
    print(f"\n{'='*60}")
    print(f"{ice_type} TILING ANALYSIS")
    print(f"{'='*60}")
    
    positions = candidate.positions
    cell_matrix = candidate.cell
    cell_dims = get_cell_extent(cell_matrix)
    
    print(f"\nUnit Cell:")
    print(f"  Matrix:\n{cell_matrix}")
    print(f"  Extent: {cell_dims}")
    print(f"  Is orthogonal: {is_cell_orthogonal(cell_matrix)}")
    
    print(f"\nInput Positions:")
    print(f"  Shape: {positions.shape}")
    print(f"  Min: {positions.min(axis=0)}")
    print(f"  Max: {positions.max(axis=0)}")
    print(f"  Range: {positions.max(axis=0) - positions.min(axis=0)}")
    
    print(f"\nTarget Region: {target_region}")
    
    # Manual calculation of tiling parameters (mimicking tile_structure)
    is_triclinic = not is_cell_orthogonal(cell_matrix)
    
    if is_triclinic:
        print(f"\nTriclinic Tiling Parameters:")
        
        lattice_a = cell_matrix[0]
        lattice_b = cell_matrix[1]
        lattice_c = cell_matrix[2]
        
        print(f"  Lattice vectors:")
        print(f"    a = {lattice_a}")
        print(f"    b = {lattice_b}")
        print(f"    c = {lattice_c}")
        
        # Position bounds
        pos_min = positions.min(axis=0)
        pos_max = positions.max(axis=0)
        
        print(f"\n  Position bounds:")
        print(f"    pos_min = {pos_min}")
        print(f"    pos_max = {pos_max}")
        
        # Required offset range
        offset_min_needed = -pos_max
        offset_max_needed = target_region - pos_min
        
        print(f"\n  Required offset range:")
        print(f"    offset_min_needed = {offset_min_needed}")
        print(f"    offset_max_needed = {offset_max_needed}")
        
        # Inverse cell matrix
        inv_cell = np.linalg.inv(cell_matrix)
        print(f"\n  Inverse cell matrix:\n{inv_cell}")
        
        # Fractional coordinates of offset bounds
        frac_min = offset_min_needed @ inv_cell.T
        frac_max = offset_max_needed @ inv_cell.T
        
        print(f"\n  Fractional coordinates of offset bounds:")
        print(f"    frac_min = {frac_min}")
        print(f"    frac_max = {frac_max}")
        
        # Index ranges
        ix_min = int(np.floor(frac_min[0])) - 1
        ix_max = int(np.ceil(frac_max[0])) + 1
        iy_min = int(np.floor(frac_min[1])) - 1
        iy_max = int(np.ceil(frac_max[1])) + 1
        iz_min = int(np.floor(frac_min[2])) - 1
        iz_max = int(np.ceil(frac_max[2])) + 1
        
        print(f"\n  Index ranges:")
        print(f"    ix: [{ix_min}, {ix_max}) -> {ix_max - ix_min} values")
        print(f"    iy: [{iy_min}, {iy_max}) -> {iy_max - iy_min} values")
        print(f"    iz: [{iz_min}, {iz_max}) -> {iz_max - iz_min} values")
        print(f"    Total tiles: {(ix_max - ix_min) * (iy_max - iy_min) * (iz_max - iz_min)}")
        
        # Show example offsets
        print(f"\n  Example tile offsets:")
        for ix in [ix_min, 0, ix_max-1]:
            for iy in [iy_min, 0, iy_max-1]:
                for iz in [iz_min, 0, iz_max-1]:
                    offset = ix * lattice_a + iy * lattice_b + iz * lattice_c
                    print(f"    [{ix}, {iy}, {iz}]: offset = {offset}")
        
        # Check coverage
        print(f"\n  Coverage check:")
        print(f"    If all positions + offset are in [0, target_region):")
        
        # Test with index 0, 0, 0
        offset_000 = np.array([0.0, 0.0, 0.0])
        shifted_000 = positions + offset_000
        print(f"      [0,0,0]: min = {shifted_000.min(axis=0)}, max = {shifted_000.max(axis=0)}")
        print(f"              in range? min >= 0: {np.all(shifted_000 >= 0)}, max < target: {np.all(shifted_000 < target_region)}")
        
        # Test with index that should shift to [0, target)
        # We need offset such that pos_min + offset >= 0
        # The min index should be: floor(frac_min[0]) - 1
        offset_min_idx = np.array([ix_min, iy_min, iz_min])
        offset_min = ix_min * lattice_a + iy_min * lattice_b + iz_min * lattice_c
        shifted_min = positions + offset_min
        print(f"      [{ix_min},{iy_min},{iz_min}]: offset = {offset_min}")
        print(f"              shifted min = {shifted_min.min(axis=0)}, max = {shifted_min.max(axis=0)}")
        print(f"              in range? min >= 0: {np.all(shifted_min >= 0)}, max < target: {np.all(shifted_min < target_region)}")
        
        offset_max_idx = np.array([ix_max-1, iy_max-1, iz_max-1])
        offset_max = (ix_max-1) * lattice_a + (iy_max-1) * lattice_b + (iz_max-1) * lattice_c
        shifted_max = positions + offset_max
        print(f"      [{ix_max-1},{iy_max-1},{iz_max-1}]: offset = {offset_max}")
        print(f"              shifted min = {shifted_max.min(axis=0)}, max = {shifted_max.max(axis=0)}")
        print(f"              in range? min >= 0: {np.all(shifted_max >= 0)}, max < target: {np.all(shifted_max < target_region)}")
    
    return positions, cell_matrix, target_region


def main():
    print("="*60)
    print("DETAILED TILING ANALYSIS: Ice II vs Ice V")
    print("="*60)
    
    # Generate Ice II
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
    
    # Generate Ice V
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
    
    # Get cell extents
    extent_ii = get_cell_extent(ice_ii.cell)
    extent_v = get_cell_extent(ice_v.cell)
    
    # Target region: 2 unit cells in X and Y, 1 in Z
    target_ii = extent_ii * np.array([2, 2, 1])
    target_v = extent_v * np.array([2, 2, 1])
    
    print(f"\nTarget regions:")
    print(f"  Ice II: {target_ii}")
    print(f"  Ice V: {target_v}")
    
    # Analyze tiling
    analyze_tiling_detail("Ice II", ice_ii, target_ii)
    analyze_tiling_detail("Ice V", ice_v, target_v)
    
    # Now test the actual tiling
    from quickice.structure_generation.water_filler import tile_structure
    
    print("\n" + "="*60)
    print("ACTUAL TILING RESULTS")
    print("="*60)
    
    # Tile Ice II
    print("\nTiling Ice II...")
    tiled_ii, nmol_ii = tile_structure(
        ice_ii.positions,
        extent_ii,
        target_ii,
        atoms_per_molecule=3,
        cell_matrix=ice_ii.cell
    )
    print(f"  Input: {len(ice_ii.positions)} atoms, {len(ice_ii.positions)//3} molecules")
    print(f"  Output: {len(tiled_ii)} atoms, {nmol_ii} molecules")
    print(f"  Expected molecules: {2*2*1 * len(ice_ii.positions)//3} = {2*2*1 * len(ice_ii.positions)//3}")
    if len(tiled_ii) > 0:
        print(f"  Tiled positions min: {tiled_ii.min(axis=0)}")
        print(f"  Tiled positions max: {tiled_ii.max(axis=0)}")
        print(f"  Coverage X: {(tiled_ii[:, 0].max() - tiled_ii[:, 0].min()) / target_ii[0] * 100:.1f}%")
        print(f"  Coverage Y: {(tiled_ii[:, 1].max() - tiled_ii[:, 1].min()) / target_ii[1] * 100:.1f}%")
        print(f"  Coverage Z: {(tiled_ii[:, 2].max() - tiled_ii[:, 2].min()) / target_ii[2] * 100:.1f}%")
    
    # Tile Ice V
    print("\nTiling Ice V...")
    tiled_v, nmol_v = tile_structure(
        ice_v.positions,
        extent_v,
        target_v,
        atoms_per_molecule=3,
        cell_matrix=ice_v.cell
    )
    print(f"  Input: {len(ice_v.positions)} atoms, {len(ice_v.positions)//3} molecules")
    print(f"  Output: {len(tiled_v)} atoms, {nmol_v} molecules")
    print(f"  Expected molecules: {2*2*1 * len(ice_v.positions)//3} = {2*2*1 * len(ice_v.positions)//3}")
    if len(tiled_v) > 0:
        print(f"  Tiled positions min: {tiled_v.min(axis=0)}")
        print(f"  Tiled positions max: {tiled_v.max(axis=0)}")
        print(f"  Coverage X: {(tiled_v[:, 0].max() - tiled_v[:, 0].min()) / target_v[0] * 100:.1f}%")
        print(f"  Coverage Y: {(tiled_v[:, 1].max() - tiled_v[:, 1].min()) / target_v[1] * 100:.1f}%")
        print(f"  Coverage Z: {(tiled_v[:, 2].max() - tiled_v[:, 2].min()) / target_v[2] * 100:.1f}%")


if __name__ == "__main__":
    main()