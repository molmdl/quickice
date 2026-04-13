#!/usr/bin/env python
"""Trace molecule filtering to understand gap formation."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.water_filler import get_cell_extent, is_cell_orthogonal


def trace_molecule_filtering(positions, cell_matrix, target_region, atoms_per_molecule=3, name="Ice"):
    """Trace which molecules survive filtering and from which tiles."""
    print(f"\n{'='*60}")
    print(f"{name} MOLECULE FILTERING TRACE")
    print(f"{'='*60}")
    
    cell_dims = get_cell_extent(cell_matrix)
    is_triclinic = not is_cell_orthogonal(cell_matrix)
    
    lx, ly, lz = target_region
    pos_min = positions.min(axis=0)
    pos_max = positions.max(axis=0)
    
    # Calculate index ranges (triclinic)
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
    
    lattice_a = cell_matrix[0]
    lattice_b = cell_matrix[1]
    lattice_c = cell_matrix[2]
    
    tol = 1e-10
    n_original_molecules = len(positions) // atoms_per_molecule
    
    # Track molecules per XY region
    from collections import defaultdict
    molecules_per_region = defaultdict(int)  # (x_bin, y_bin) -> count
    n_bins = 10
    x_bin_size = lx / n_bins
    y_bin_size = ly / n_bins
    
    # Also track per tile
    molecules_per_tile = defaultdict(int)  # (ix, iy, iz) -> count
    
    total_molecules = 0
    
    # Process each tile
    for ix in range(ix_min, ix_max):
        for iy in range(iy_min, iy_max):
            for iz in range(iz_min, iz_max):
                offset = ix * lattice_a + iy * lattice_b + iz * lattice_c
                shifted = positions + offset
                
                # Check each molecule
                for mol_idx in range(n_original_molecules):
                    start = mol_idx * atoms_per_molecule
                    end = start + atoms_per_molecule
                    mol = shifted[start:end]
                    
                    all_inside_x = np.all((mol[:, 0] >= 0) & (mol[:, 0] < lx - tol))
                    all_inside_y = np.all((mol[:, 1] >= 0) & (mol[:, 1] < ly - tol))
                    all_inside_z = np.all((mol[:, 2] >= 0) & (mol[:, 2] < lz - tol))
                    
                    if all_inside_x and all_inside_y and all_inside_z:
                        total_molecules += 1
                        molecules_per_tile[(ix, iy, iz)] += 1
                        
                        # Track region
                        com_x = mol[:, 0].mean()
                        com_y = mol[:, 1].mean()
                        x_bin = min(int(com_x / x_bin_size), n_bins - 1)
                        y_bin = min(int(com_y / y_bin_size), n_bins - 1)
                        molecules_per_region[(x_bin, y_bin)] += 1
    
    print(f"\nTotal molecules after filtering: {total_molecules}")
    print(f"Tiles with molecules: {len(molecules_per_tile)}")
    
    # Show molecules per tile
    print(f"\nMolecules per contributing tile:")
    for (ix, iy, iz), count in sorted(molecules_per_tile.items())[:10]:
        print(f"  Tile ({ix}, {iy}, {iz}): {count} molecules")
    
    # Analyze density distribution
    print(f"\nDensity distribution across XY regions ({n_bins}x{n_bins} grid):")
    
    expected_per_region = total_molecules / (n_bins * n_bins)
    print(f"  Expected molecules per region: {expected_per_region:.1f}")
    
    # Find regions with low density
    low_density_regions = []
    for x_bin in range(n_bins):
        for y_bin in range(n_bins):
            count = molecules_per_region.get((x_bin, y_bin), 0)
            density = count / expected_per_region if expected_per_region > 0 else 0
            if density < 0.5:
                x_center = (x_bin + 0.5) * x_bin_size
                y_center = (y_bin + 0.5) * y_bin_size
                low_density_regions.append((x_bin, y_bin, x_center, y_center, count, density))
    
    print(f"  Regions with <50% expected density: {len(low_density_regions)}")
    for x_bin, y_bin, x_center, y_center, count, density in low_density_regions:
        print(f"    Region ({x_bin}, {y_bin}) at ({x_center:.2f}, {y_center:.2f}) nm: {count} molecules ({density*100:.1f}%)")
    
    # Check if low density regions are clustered
    if len(low_density_regions) > 0:
        print(f"\n  Low density region locations:")
        x_coords = [r[2] for r in low_density_regions]
        y_coords = [r[3] for r in low_density_regions]
        print(f"    X range: {min(x_coords):.2f} to {max(x_coords):.2f} nm")
        print(f"    Y range: {min(y_coords):.2f} to {max(y_coords):.2f} nm")
        
        # Check if they're near edges or scattered
        if max(x_coords) > lx * 0.8 or min(x_coords) < lx * 0.2:
            print(f"    Pattern: Some gaps near X edges")
        if max(y_coords) > ly * 0.8 or min(y_coords) < ly * 0.2:
            print(f"    Pattern: Some gaps near Y edges")
    
    return low_density_regions


def main():
    print("="*60)
    print("MOLECULE FILTERING ANALYSIS: Ice II vs Ice V")
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
    extent_ii = get_cell_extent(ice_ii.cell)
    
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
    extent_v = get_cell_extent(ice_v.cell)
    
    # Target regions (2x extent in X and Y)
    target_ii = extent_ii * np.array([2, 2, 1])
    target_v = extent_v * np.array([2, 2, 1])
    
    # Trace both
    ii_gaps = trace_molecule_filtering(ice_ii.positions, ice_ii.cell, target_ii, name="Ice II")
    v_gaps = trace_molecule_filtering(ice_v.positions, ice_v.cell, target_v, name="Ice V")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"\nIce II low density regions: {len(ii_gaps)}")
    print(f"Ice V low density regions: {len(v_gaps)}")


if __name__ == "__main__":
    main()