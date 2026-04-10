#!/usr/bin/env python3
"""Compare z-positions of Ih vs Ic candidates from GenIce."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates

# Phase stability conditions (T in K, P in MPa)
PHASE_CONDITIONS = {
    "ice_ih": (273, 0.1),      # Ice Ih: low P, near melting
    "ice_ic": (200, 0.1),      # Ice Ic: low T, low P (metastable, but GenIce can generate)
    "ice_iii": (250, 250),    # Ice III: 250 K, 250 MPa
    "ice_vii": (300, 2500),   # Ice VII: 300 K, 2500 MPa
    "ice_viii": (200, 2500),  # Ice VIII: 200 K, 2500 MPa
}

def check_candidate_z_positions(phase_id: str, nmolecules: int = 64, seed: int = 42):
    """Generate a candidate and analyze z-positions."""
    T, P = PHASE_CONDITIONS.get(phase_id, (273, 0.1))
    phase_info = lookup_phase(T, P)
    # Override with correct phase_id if needed
    phase_info["phase_id"] = phase_id
    phase_info["phase_name"] = {"ice_ih": "Ice Ih", "ice_ic": "Ice Ic", "ice_iii": "Ice III", "ice_vii": "Ice VII", "ice_viii": "Ice VIII"}[phase_id]
    
    result = generate_candidates(phase_info, nmolecules, n_candidates=1, base_seed=seed)
    candidate = result.candidates[0]
    
    z_positions = candidate.positions[:, 2]
    cell_z = candidate.cell[2, 2]
    
    print(f"\n=== {phase_id} ===")
    print(f"Cell Z: {cell_z:.4f} nm")
    print(f"Z positions range: [{z_positions.min():.4f}, {z_positions.max():.4f}] nm")
    print(f"Z positions span: {z_positions.max() - z_positions.min():.4f} nm")
    print(f"Number of atoms: {len(z_positions)}")
    
    # Check if positions are relative to box (0 to cell_z) or absolute
    print(f"\nPosition analysis:")
    print(f"  Min Z: {z_positions.min():.4f} (expected ~0)")
    print(f"  Max Z: {z_positions.max():.4f} (expected ~{cell_z:.4f})")
    print(f"  Z < 0: {np.sum(z_positions < 0)}")
    print(f"  Z >= cell_z: {np.sum(z_positions >= cell_z)}")
    print(f"  Z in [0, cell_z): {np.sum((z_positions >= 0) & (z_positions < cell_z))}")
    
    return candidate

if __name__ == "__main__":
    print("Comparing z-positions for Ih vs Ic...")
    
    # Test phases that work (Ih, III)
    for phase in ["ice_ih", "ice_iii"]:
        check_candidate_z_positions(phase, nmolecules=64)
    
    # Test phases that fail (Ic, VII, VIII)
    for phase in ["ice_ic", "ice_vii", "ice_viii"]:
        try:
            check_candidate_z_positions(phase, nmolecules=64)
        except Exception as e:
            print(f"\n=== {phase} ===")
            print(f"ERROR: {e}")
