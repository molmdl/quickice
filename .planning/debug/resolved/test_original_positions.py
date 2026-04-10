#!/usr/bin/env python3
"""Compare original positions: Ih vs Ic vs III."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates

PHASE_CONDITIONS = {
    "ice_ih": (273, 0.1),
    "ice_ic": (200, 0.1),
    "ice_iii": (250, 250),
    "ice_vii": (300, 2500),
}

def check_original_positions(phase_id: str, nmolecules: int = 64, seed: int = 42):
    """Check if original positions are within [0, cell)."""
    T, P = PHASE_CONDITIONS.get(phase_id, (273, 0.1))
    phase_info = lookup_phase(T, P)
    phase_info["phase_id"] = phase_id
    phase_info["phase_name"] = {"ice_ih": "Ice Ih", "ice_ic": "Ice Ic", "ice_iii": "Ice III", "ice_vii": "Ice VII"}[phase_id]
    
    result = generate_candidates(phase_info, nmolecules, n_candidates=1, base_seed=seed)
    candidate = result.candidates[0]
    
    cell_dims = np.array([candidate.cell[0, 0], candidate.cell[1, 1], candidate.cell[2, 2]])
    
    print(f"\n=== {phase_id} ===")
    print(f"Cell: {cell_dims}")
    
    for dim, name in enumerate(['X', 'Y', 'Z']):
        pos = candidate.positions[:, dim]
        cell_dim = cell_dims[dim]
        
        below_0 = pos < 0
        above_cell = pos >= cell_dim
        inside = (pos >= 0) & (pos < cell_dim)
        
        print(f"  {name}: range [{pos.min():.4f}, {pos.max():.4f}], cell_dim={cell_dim:.4f}")
        print(f"    < 0: {np.sum(below_0)}, >= cell: {np.sum(above_cell)}, inside: {np.sum(inside)}")

if __name__ == "__main__":
    print("Checking if original positions are within [0, cell)...")
    
    for phase in ["ice_ih", "ice_ic", "ice_iii", "ice_vii"]:
        check_original_positions(phase)
