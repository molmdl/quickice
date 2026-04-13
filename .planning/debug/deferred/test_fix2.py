#!/usr/bin/env python
"""Test a more sophisticated fix for Ice II density variation."""

import numpy as np
import math
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.water_filler import get_cell_extent, is_cell_orthogonal


def tile_structure_improved(positions, cell_dims, target_region, atoms_per_molecule=3, cell_matrix=None):
    """Improved tiling that generates a denser coverage for triclinic cells."""
    
    if len(positions) == 0:
        return np.zeros((0, 3), dtype=float), 0
    
    lx, ly, lz = target_region
    a, b, c = cell_dims
    
    # Determine if triclinic
    is_triclinic = False
    if cell_matrix is not None:
        is_triclinic = not is_cell_orthogonal(cell_matrix)
    
    if is_triclinic and cell_matrix is not None:
        lattice_a = cell_matrix[0]
        lattice_b = cell_matrix[1]
        lattice_c = cell_matrix[2]
        
        pos_min = positions.min(axis=0)
        pos_max = positions.max(axis=0)
        
        inv_cell = np.linalg.inv(cell_matrix)
        
        # The key insight: we need to ensure that for every point in the target region,
        # there's at least one tile whose unit cell covers it.
        # 
        # For competing lattice vectors, the coverage can have holes because different
        # (ix, iy, iz) combinations produce overlapping offsets.
        #
        # Solution: Generate a denser grid of tiles by using a finer sampling of the
        # offset space.
        
        # Calculate the range of offsets needed
        offset_min_needed = -pos_max  # Minimum offset to bring all atoms >= 0
        offset_max_needed = target_region - pos_min  # Maximum offset to keep atoms < target
        
        # Convert to fractional coordinates
        frac_min = offset_min_needed @ inv_cell.T
        frac_max = offset_max_needed @ inv_cell.T
        
        # Base index ranges
        ix_min = int(np.floor(frac_min[0])) - 2  # Extra margin for competing vectors
        ix_max = int(np.ceil(frac_max[0])) + 2
        iy_min = int(np.floor(frac_min[1])) - 2
        iy_max = int(np.ceil(frac_max[1])) + 2
        iz_min = int(np.floor(frac_min[2])) - 2
        iz_max = int(np.ceil(frac_max[2])) + 2
        
        # For Ice II specifically: expand the iy range because b[0] < 0
        # causes tiles to shift left, leaving gaps on the right
        if lattice_b[0] < 0:
            # Need more tiles with higher iy to fill the right side
            iy_max += 2
        
        if lattice_c[0] < 0:
            iz_max += 2
        
        # Ensure at least 1 tile in each direction
        if ix_max <= ix_min:
            ix_min, ix_max = 0, 1
        if iy_max <= iy_min:
            iy_min, iy_max = 0, 1
        if iz_max <= iz_min:
            iz_min, iz_max = 0, 1
        
        ix_vals = np.arange(ix_min, ix_max)
        iy_vals = np.arange(iy_min, iy_max)
        iz_vals = np.arange(iz_min, iz_max)
    else:
        # Orthogonal
        nx = math.ceil(lx / a) if a > 0 else 1
        ny = math.ceil(ly / b) if b > 0 else 1
        nz = math.ceil(lz / c) if c > 0 else 1
        
        ix_vals = np.arange(nx)
        iy_vals = np.arange(ny)
        iz_vals = np.arange(nz)
    
    # Generate offsets
    ix_grid, iy_grid, iz_grid = np.meshgrid(ix_vals, iy_vals, iz_vals, indexing='ij')
    
    if is_triclinic and cell_matrix is not None:
        offsets = np.stack([
            ix_grid.ravel() * lattice_a[0] + iy_grid.ravel() * lattice_b[0] + iz_grid.ravel() * lattice_c[0],
            ix_grid.ravel() * lattice_a[1] + iy_grid.ravel() * lattice_b[1] + iz_grid.ravel() * lattice_c[1],
            ix_grid.ravel() * lattice_a[2] + iy_grid.ravel() * lattice_b[2] + iz_grid.ravel() * lattice_c[2],
        ], axis=1)
    else:
        offsets = np.stack([
            ix_grid.ravel() * a,
            iy_grid.ravel() * b,
            iz_grid.ravel() * c
        ], axis=1)
    
    # Broadcast positions with all offsets
    all_positions = (positions[np.newaxis, :, :] + offsets[:, np.newaxis, :]).reshape(-1, 3)
    
    # Filter molecules
    tol = 1e-10
    n_tiled_molecules = len(all_positions) // atoms_per_molecule
    
    keep_molecules = []
    for mol_idx in range(n_tiled_molecules):
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        mol_atoms = all_positions[start_atom:end_atom]
        
        all_inside_x = np.all((mol_atoms[:, 0] >= 0) & (mol_atoms[:, 0] < lx - tol))
        all_inside_y = np.all((mol_atoms[:, 1] >= 0) & (mol_atoms[:, 1] < ly - tol))
        all_inside_z = np.all((mol_atoms[:, 2] >= 0) & (mol_atoms[:, 2] < lz - tol))
        
        if all_inside_x and all_inside_y and all_inside_z:
            keep_molecules.append(mol_idx)
    
    if not keep_molecules:
        return np.zeros((0, 3), dtype=float), 0
    
    keep_mask = np.zeros(len(all_positions), dtype=bool)
    for mol_idx in keep_molecules:
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        keep_mask[start_atom:end_atom] = True
    
    filtered = all_positions[keep_mask]
    n_molecules = len(keep_molecules)
    
    return filtered, n_molecules


def analyze_coverage(positions, box_dims, grid_size=10):
    """Analyze coverage density."""
    if len(positions) == 0:
        return 0, 0, 0
    
    hist, _, _ = np.histogram2d(
        positions[:, 0], positions[:, 1], 
        bins=grid_size, 
        range=[[0, box_dims[0]], [0, box_dims[1]]]
    )
    
    expected = len(positions) / (grid_size * grid_size)
    normalized = hist / expected
    
    return normalized.min(), normalized.max(), len(np.where(normalized < 0.75)[0])


def main():
    print("="*60)
    print("IMPROVED FIX TEST")
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
    
    # Target region
    target = extent_ii * np.array([2, 2, 1])
    
    print(f"\nIce II cell extent: {extent_ii}")
    print(f"Target region: {target}")
    
    # Test original tiling
    from quickice.structure_generation.water_filler import tile_structure
    
    print("\n--- ORIGINAL TILING ---")
    tiled_orig, nmol_orig = tile_structure(
        ice_ii.positions, extent_ii, target,
        atoms_per_molecule=3,
        cell_matrix=ice_ii.cell
    )
    
    min_d, max_d, n_low = analyze_coverage(tiled_orig, target, grid_size=10)
    print(f"Molecules: {nmol_orig}")
    print(f"Density range: {min_d*100:.1f}% - {max_d*100:.1f}%")
    print(f"Low density areas (< 75%): {n_low}")
    
    # Test improved tiling
    print("\n--- IMPROVED TILING ---")
    tiled_new, nmol_new = tile_structure_improved(
        ice_ii.positions, extent_ii, target,
        atoms_per_molecule=3,
        cell_matrix=ice_ii.cell
    )
    
    min_d_new, max_d_new, n_low_new = analyze_coverage(tiled_new, target, grid_size=10)
    print(f"Molecules: {nmol_new}")
    print(f"Density range: {min_d_new*100:.1f}% - {max_d_new*100:.1f}%")
    print(f"Low density areas (< 75%): {n_low_new}")
    
    print("\n--- IMPROVEMENT ---")
    print(f"Molecules: {nmol_orig} -> {nmol_new} ({nmol_new - nmol_orig:+d})")
    print(f"Min density: {min_d*100:.1f}% -> {min_d_new*100:.1f}% ({(min_d_new - min_d)*100:+.1f}%)")
    print(f"Low density areas: {n_low} -> {n_low_new} ({n_low_new - n_low:+d})")


if __name__ == "__main__":
    main()