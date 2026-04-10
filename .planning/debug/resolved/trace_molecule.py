#!/usr/bin/env python3
"""Trace through a specific molecule to understand the issue."""

import numpy as np
import math
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates

PHASE_CONDITIONS = {
    "ice_ic": (200, 0.1),
}

def trace_molecule(phase_id: str, nmolecules: int = 64, seed: int = 42):
    """Trace a specific molecule through tiling and wrapping."""
    T, P = PHASE_CONDITIONS.get(phase_id, (273, 0.1))
    phase_info = lookup_phase(T, P)
    phase_info["phase_id"] = phase_id
    phase_info["phase_name"] = "Ice Ic"
    
    result = generate_candidates(phase_info, nmolecules, n_candidates=1, base_seed=seed)
    candidate = result.candidates[0]
    
    positions = candidate.positions
    cell_dims = np.array([candidate.cell[0, 0], candidate.cell[1, 1], candidate.cell[2, 2]])
    
    # Find a molecule with negative Z
    atoms_per_molecule = 3
    n_molecules = len(positions) // atoms_per_molecule
    
    print(f"Looking for molecule with negative Z...")
    
    for mol_idx in range(n_molecules):
        start = mol_idx * atoms_per_molecule
        end = start + atoms_per_molecule
        mol_positions = positions[start:end]
        
        if np.any(mol_positions[:, 2] < 0):
            print(f"\n=== Molecule {mol_idx} (has negative Z) ===")
            print(f"Original positions:")
            for i, atom_name in enumerate(['O', 'H1', 'H2']):
                print(f"  {atom_name}: {mol_positions[i]}")
            
            # Cell dimension
            c = cell_dims[2]
            print(f"\nCell Z dimension: {c:.4f} nm")
            
            # Calculate tiling
            lz = 3.0  # target region Z
            nz = math.ceil(lz / c)
            
            print(f"\nTiling to Z = {lz:.4f} nm:")
            print(f"  nz = ceil({lz:.4f} / {c:.4f}) = {nz}")
            print(f"  Z offsets: {', '.join([f'{i * c:.4f}' for i in range(nz)])} nm")
            
            # Show tiled positions
            print(f"\nTiled positions (all copies):")
            for iz in range(nz):
                offset_z = iz * c
                print(f"  iz={iz}, offset={offset_z:.4f} nm:")
                for i, atom_name in enumerate(['O', 'H1', 'H2']):
                    tiled_z = mol_positions[i, 2] + offset_z
                    print(f"    {atom_name}: Z = {mol_positions[i, 2]:.4f} + {offset_z:.4f} = {tiled_z:.4f} nm")
            
            # Check which copies pass the filter
            print(f"\nFilter check (molecule must have ALL atoms < {lz:.4f} nm):")
            tol = 1e-10
            for iz in range(nz):
                offset_z = iz * c
                mol_z = mol_positions[:, 2] + offset_z
                
                all_inside_z = np.all(mol_z < lz - tol)
                print(f"  iz={iz}: Z range [{mol_z.min():.4f}, {mol_z.max():.4f}], all_inside_z = {all_inside_z}")
                
                if all_inside_z:
                    # This copy passes the filter
                    print(f"    -> This copy is KEPT")
                    
                    # Now check wrapping
                    o_pos = mol_positions[0].copy()
                    o_pos[2] += offset_z
                    
                    print(f"\n  Wrapping (using O as reference):")
                    print(f"    O position: {o_pos}")
                    print(f"    floor(O_Z / {lz}) = floor({o_pos[2]:.4f} / {lz:.4f}) = floor({o_pos[2]/lz:.4f}) = {np.floor(o_pos[2]/lz):.0f}")
                    
                    shift_z = -np.floor(o_pos[2] / lz) * lz
                    print(f"    shift_z = -{np.floor(o_pos[2]/lz):.0f} * {lz:.4f} = {shift_z:.4f} nm")
                    
                    print(f"\n  After wrapping:")
                    for i, atom_name in enumerate(['O', 'H1', 'H2']):
                        tiled_z = mol_positions[i, 2] + offset_z
                        wrapped_z = tiled_z + shift_z
                        print(f"    {atom_name}: {tiled_z:.4f} + {shift_z:.4f} = {wrapped_z:.4f} nm")
                    
                    if np.any((mol_positions[:, 2] + offset_z + shift_z) >= lz):
                        print(f"    *** WARNING: Wrapped Z >= {lz}! ***")
                    if np.any((mol_positions[:, 2] + offset_z + shift_z) < 0):
                        print(f"    *** WARNING: Wrapped Z < 0! ***")
            
            break  # Only trace first molecule with negative Z

if __name__ == "__main__":
    trace_molecule("ice_ic")