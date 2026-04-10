#!/usr/bin/env python3
"""Debug the wrapping step in tile_structure."""

import numpy as np
import math
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates

PHASE_CONDITIONS = {
    "ice_ic": (200, 0.1),
}

def debug_tile_wrapping(phase_id: str, nmolecules: int = 64, seed: int = 42):
    """Debug the wrapping logic in tile_structure."""
    T, P = PHASE_CONDITIONS.get(phase_id, (273, 0.1))
    phase_info = lookup_phase(T, P)
    phase_info["phase_id"] = phase_id
    phase_info["phase_name"] = "Ice Ic"
    
    result = generate_candidates(phase_info, nmolecules, n_candidates=1, base_seed=seed)
    candidate = result.candidates[0]
    
    print(f"\n=== Debugging wrapping for {phase_id} ===")
    
    positions = candidate.positions
    cell_dims = np.array([candidate.cell[0, 0], candidate.cell[1, 1], candidate.cell[2, 2]])
    
    # Target region
    target_region = np.array([3.0, 3.0, 3.0])
    lx, ly, lz = target_region
    a, b, c = cell_dims
    
    # Tiling counts
    nx = math.ceil(lx / a)
    ny = math.ceil(ly / b)
    nz = math.ceil(lz / c)
    
    # Generate offsets
    ix_vals = np.arange(nx)
    iy_vals = np.arange(ny)
    iz_vals = np.arange(nz)
    
    ix_grid, iy_grid, iz_grid = np.meshgrid(ix_vals, iy_vals, iz_vals, indexing='ij')
    
    offsets = np.stack([
        ix_grid.ravel() * a,
        iy_grid.ravel() * b,
        iz_grid.ravel() * c
    ], axis=1)
    
    # Tile
    atoms_per_molecule = 3
    all_positions = (positions[np.newaxis, :, :] + offsets[:, np.newaxis, :]).reshape(-1, 3)
    
    # Filter molecules
    tol = 1e-10
    n_tiled_molecules = len(all_positions) // atoms_per_molecule
    
    keep_molecules = []
    for mol_idx in range(n_tiled_molecules):
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        mol_atoms = all_positions[start_atom:end_atom]
        
        all_inside_x = np.all(mol_atoms[:, 0] < lx - tol)
        all_inside_y = np.all(mol_atoms[:, 1] < ly - tol)
        all_inside_z = np.all(mol_atoms[:, 2] < lz - tol)
        
        if all_inside_x and all_inside_y and all_inside_z:
            keep_molecules.append(mol_idx)
    
    print(f"Molecules before filter: {n_tiled_molecules}")
    print(f"Molecules after filter: {len(keep_molecules)}")
    
    # Build keep mask
    keep_mask = np.zeros(len(all_positions), dtype=bool)
    for mol_idx in keep_molecules:
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        keep_mask[start_atom:end_atom] = True
    
    filtered = all_positions[keep_mask]
    
    print(f"\nFiltered positions count: {len(filtered)}")
    print(f"Filtered Z range: [{filtered[:, 2].min():.4f}, {filtered[:, 2].max():.4f}] nm")
    
    # NOW wrap the molecules
    print("\n=== Wrapping molecules ===")
    
    tiled_positions = np.zeros_like(filtered)
    n_filtered_molecules = len(filtered) // atoms_per_molecule
    
    molecules_with_issues = []
    
    for mol_idx in range(n_filtered_molecules):
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        mol_atoms = filtered[start_atom:end_atom]
        
        # Use first atom (oxygen) as reference for wrapping
        o_pos = mol_atoms[0].copy()
        
        # Calculate shift to wrap O into target region
        shift = np.zeros(3)
        for dim in range(3):
            shift[dim] = -np.floor(o_pos[dim] / target_region[dim]) * target_region[dim]
        
        # Apply same shift to ALL atoms in the molecule
        wrapped_atoms = mol_atoms + shift
        tiled_positions[start_atom:end_atom] = wrapped_atoms
        
        # Check if any atoms ended up outside [0, lz)
        if np.any(wrapped_atoms[:, 2] >= lz) or np.any(wrapped_atoms[:, 2] < 0):
            molecules_with_issues.append({
                'mol_idx': mol_idx,
                'o_pos': o_pos,
                'shift': shift,
                'before': mol_atoms.copy(),
                'after': wrapped_atoms.copy()
            })
    
    print(f"\nFinal Z range: [{tiled_positions[:, 2].min():.4f}, {tiled_positions[:, 2].max():.4f}] nm")
    print(f"Z >= 3.0: {np.sum(tiled_positions[:, 2] >= 3.0)} atoms")
    print(f"Z < 0: {np.sum(tiled_positions[:, 2] < 0)} atoms")
    
    if molecules_with_issues:
        print(f"\n{len(molecules_with_issues)} molecules have atoms outside [0, lz) after wrapping:")
        for i, issue in enumerate(molecules_with_issues[:3]):  # Show first 3
            print(f"\n  Molecule {issue['mol_idx']}:")
            print(f"    O position: {issue['o_pos']}")
            print(f"    Shift applied: {issue['shift']}")
            print(f"    Before wrapping: Z range [{issue['before'][:, 2].min():.4f}, {issue['before'][:, 2].max():.4f}]")
            print(f"    After wrapping: Z range [{issue['after'][:, 2].min():.4f}, {issue['after'][:, 2].max():.4f}]")

if __name__ == "__main__":
    debug_tile_wrapping("ice_ic")
