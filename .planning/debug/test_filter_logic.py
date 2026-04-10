#!/usr/bin/env python3
"""Debug the tile_structure filtering for Ic."""

import numpy as np
import math
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates

# Phase stability conditions
PHASE_CONDITIONS = {
    "ice_ic": (200, 0.1),
}

def debug_tile_filtering(phase_id: str, nmolecules: int = 64, seed: int = 42):
    """Debug the filtering logic in tile_structure."""
    T, P = PHASE_CONDITIONS.get(phase_id, (273, 0.1))
    phase_info = lookup_phase(T, P)
    phase_info["phase_id"] = phase_id
    phase_info["phase_name"] = "Ice Ic"
    
    result = generate_candidates(phase_info, nmolecules, n_candidates=1, base_seed=seed)
    candidate = result.candidates[0]
    
    print(f"\n=== Debugging {phase_id} ===")
    
    # Get cell dimensions
    positions = candidate.positions
    cell_dims = np.array([candidate.cell[0, 0], candidate.cell[1, 1], candidate.cell[2, 2]])
    
    print(f"Original positions count: {len(positions)}")
    print(f"Original Z range: [{positions[:, 2].min():.4f}, {positions[:, 2].max():.4f}] nm")
    print(f"Cell dimensions: {cell_dims}")
    
    # Manual tiling logic (from tile_structure)
    lx, ly, lz = 3.0, 3.0, 3.0  # target region
    a, b, c = cell_dims
    
    nx = math.ceil(lx / a)
    ny = math.ceil(ly / b)
    nz = math.ceil(lz / c)
    
    print(f"\nTiling counts: nx={nx}, ny={ny}, nz={nz}")
    print(f"  Z direction: ceil(3.0 / {c:.4f}) = ceil({3.0/c:.4f}) = {nz}")
    print(f"  Z offsets: 0, {c:.4f}, {2*c:.4f}")
    
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
    
    print(f"\nZ offsets: {offsets[:, 2]}")
    
    # Tile
    n_tiles = nx * ny * nz
    all_positions = (positions[np.newaxis, :, :] + offsets[:, np.newaxis, :]).reshape(-1, 3)
    
    print(f"\nTotal tiled positions (before filter): {len(all_positions)}")
    
    # Check Z range of all tiled positions
    all_z = all_positions[:, 2]
    print(f"Tiled Z range (before filter): [{all_z.min():.4f}, {all_z.max():.4f}] nm")
    print(f"  Z >= 3.0: {np.sum(all_z >= 3.0)} atoms")
    
    # Check molecules at different Z offsets
    atoms_per_molecule = 3
    n_molecules_total = len(all_positions) // atoms_per_molecule
    
    print(f"\nAnalyzing molecules by Z offset:")
    for iz in range(nz):
        # Molecules from this Z offset
        z_offset = iz * c
        
        # Calculate which molecules came from this offset
        # Each tile has (original_molecules) molecules
        # Tiles are ordered by (ix, iy, iz) in 'ij' indexing
        molecules_per_xy = nx * ny * len(positions) // atoms_per_molecule
        molecules_per_z = molecules_per_xy
        
        # This is getting complex. Let me just check the Z positions directly.
        pass
    
    # Actually, let's check specific atoms
    print(f"\nAtoms with Z >= 3.0 nm (should be filtered):")
    above_3_mask = all_z >= 3.0
    above_3_indices = np.where(above_3_mask)[0]
    
    for idx in above_3_indices[:5]:  # Show first 5
        atom_z = all_positions[idx, 2]
        mol_idx = idx // atoms_per_molecule
        mol_start = mol_idx * atoms_per_molecule
        mol_end = mol_start + atoms_per_molecule
        mol_atoms = all_positions[mol_start:mol_end]
        
        print(f"  Atom {idx}: Z={atom_z:.4f}, molecule {mol_idx}")
        print(f"    Molecule Z range: [{mol_atoms[:, 2].min():.4f}, {mol_atoms[:, 2].max():.4f}]")
        
        # Check if molecule should be filtered
        tol = 1e-10
        all_inside_z = np.all(mol_atoms[:, 2] < lz - tol)
        print(f"    all_inside_z = {all_inside_z}")

if __name__ == "__main__":
    debug_tile_filtering("ice_ic")
