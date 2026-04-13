#!/usr/bin/env python
"""Test a potential fix for Ice II asymmetric coverage."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.water_filler import get_cell_extent, is_cell_orthogonal, tile_structure


def tile_structure_fixed(positions, cell_dims, target_region, atoms_per_molecule=3, cell_matrix=None):
    """Fixed tiling function that handles competing lattice vectors."""
    import math
    
    if len(positions) == 0:
        return np.zeros((0, 3), dtype=float), 0
    
    lx, ly, lz = target_region
    a, b, c = cell_dims
    
    # Calculate tiling counts (ceil to ensure full coverage)
    nx = math.ceil(lx / a) if a > 0 else 1
    ny = math.ceil(ly / b) if b > 0 else 1
    nz = math.ceil(lz / c) if c > 0 else 1
    
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
        
        # FIX: Expand index ranges when lattice vectors have competing signs
        # This ensures we have enough tiles to cover the full region even when
        # different (iy, iz) combinations produce overlapping X offsets
        
        # Check for competing signs in X direction
        if lattice_b[0] != 0 and np.sign(lattice_a[0]) != np.sign(lattice_b[0]):
            # a and b compete in X - expand iy range
            iy_min -= 1
            iy_max += 1
        
        if lattice_c[0] != 0 and np.sign(lattice_a[0]) != np.sign(lattice_c[0]):
            # a and c compete in X - expand iz range
            iz_min -= 1
            iz_max += 1
        
        # Check for competing signs in Y direction
        if lattice_c[1] != 0 and lattice_b[1] != 0 and np.sign(lattice_b[1]) != np.sign(lattice_c[1]):
            # b and c compete in Y - expand iz range
            iz_min -= 1
            iz_max += 1
        
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


def analyze_coverage(positions, box_dims, name="Interface", grid_size=20):
    """Analyze coverage density."""
    if len(positions) == 0:
        return 0, []
    
    hist, x_edges, y_edges = np.histogram2d(
        positions[:, 0], positions[:, 1], 
        bins=grid_size, 
        range=[[0, box_dims[0]], [0, box_dims[1]]]
    )
    
    expected = len(positions) / (grid_size * grid_size)
    normalized = hist / expected
    
    threshold = 0.5
    gaps = np.where(normalized < threshold)
    
    return len(gaps[0]), normalized


def main():
    print("="*60)
    print("FIX TEST: Competing Lattice Vector Handling")
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
    print("\n--- ORIGINAL TILING ---")
    tiled_orig, nmol_orig = tile_structure(
        ice_ii.positions, extent_ii, target,
        atoms_per_molecule=3,
        cell_matrix=ice_ii.cell
    )
    
    n_gaps_orig, norm_orig = analyze_coverage(tiled_orig, target, "Original", grid_size=20)
    
    print(f"Molecules: {nmol_orig}")
    print(f"X coverage: {(tiled_orig[:, 0].max() - tiled_orig[:, 0].min()) / target[0] * 100:.1f}%")
    print(f"Y coverage: {(tiled_orig[:, 1].max() - tiled_orig[:, 1].min()) / target[1] * 100:.1f}%")
    print(f"Low density areas (< 50%): {n_gaps_orig}")
    print(f"Min density: {norm_orig.min() * 100:.1f}%")
    
    # Test fixed tiling
    print("\n--- FIXED TILING ---")
    tiled_fixed, nmol_fixed = tile_structure_fixed(
        ice_ii.positions, extent_ii, target,
        atoms_per_molecule=3,
        cell_matrix=ice_ii.cell
    )
    
    n_gaps_fixed, norm_fixed = analyze_coverage(tiled_fixed, target, "Fixed", grid_size=20)
    
    print(f"Molecules: {nmol_fixed}")
    print(f"X coverage: {(tiled_fixed[:, 0].max() - tiled_fixed[:, 0].min()) / target[0] * 100:.1f}%")
    print(f"Y coverage: {(tiled_fixed[:, 1].max() - tiled_fixed[:, 1].min()) / target[1] * 100:.1f}%")
    print(f"Low density areas (< 50%): {n_gaps_fixed}")
    print(f"Min density: {norm_fixed.min() * 100:.1f}%")
    
    print("\n--- IMPROVEMENT ---")
    print(f"Molecules: {nmol_orig} -> {nmol_fixed} ({nmol_fixed - nmol_orig:+d})")
    print(f"Low density areas: {n_gaps_orig} -> {n_gaps_fixed} ({n_gaps_fixed - n_gaps_orig:+d})")
    print(f"Min density: {norm_orig.min() * 100:.1f}% -> {norm_fixed.min() * 100:.1f}% ({(norm_fixed.min() - norm_orig.min()) * 100:+.1f}%)")


if __name__ == "__main__":
    main()