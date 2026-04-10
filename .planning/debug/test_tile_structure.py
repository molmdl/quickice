#!/usr/bin/env python3
"""Debug tile_structure behavior for different phases."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.water_filler import tile_structure

# Phase stability conditions (T in K, P in MPa)
PHASE_CONDITIONS = {
    "ice_ih": (273, 0.1),
    "ice_ic": (200, 0.1),
    "ice_iii": (250, 250),
    "ice_vii": (300, 2500),
    "ice_viii": (200, 2500),
}

def debug_tile_structure(phase_id: str, nmolecules: int = 64, seed: int = 42):
    """Debug tile_structure for a specific phase."""
    T, P = PHASE_CONDITIONS.get(phase_id, (273, 0.1))
    phase_info = lookup_phase(T, P)
    phase_info["phase_id"] = phase_id
    phase_info["phase_name"] = {"ice_ih": "Ice Ih", "ice_ic": "Ice Ic", "ice_iii": "Ice III", "ice_vii": "Ice VII", "ice_viii": "Ice VIII"}[phase_id]
    
    result = generate_candidates(phase_info, nmolecules, n_candidates=1, base_seed=seed)
    candidate = result.candidates[0]
    
    print(f"\n=== {phase_id} ===")
    
    # Get cell dimensions
    cell_dims = np.array([candidate.cell[0, 0], candidate.cell[1, 1], candidate.cell[2, 2]])
    print(f"Cell dimensions: {cell_dims}")
    
    # Original positions
    print(f"Original Z range: [{candidate.positions[:, 2].min():.4f}, {candidate.positions[:, 2].max():.4f}] nm")
    
    # Tile to fill [3, 3, 3] (ice_thickness region)
    target_region = np.array([3.0, 3.0, 3.0])
    
    print(f"\nTiling to target region: {target_region}")
    
    tiled_positions, n_molecules = tile_structure(
        candidate.positions,
        cell_dims,
        target_region,
        atoms_per_molecule=3
    )
    
    print(f"Tiled positions count: {len(tiled_positions)}")
    print(f"Tiled Z range: [{tiled_positions[:, 2].min():.4f}, {tiled_positions[:, 2].max():.4f}] nm")
    
    # Check for atoms outside [0, 3)
    z = tiled_positions[:, 2]
    below_zero = z < 0
    above_3 = z >= 3.0
    
    print(f"  Z < 0: {np.sum(below_zero)} atoms")
    print(f"  Z >= 3: {np.sum(above_3)} atoms")
    print(f"  Z in [0, 3): {np.sum((z >= 0) & (z < 3.0))} atoms")
    
    # Now shift to create top layer
    print(f"\nAfter shifting by 6.0 nm (ice_thickness + water_thickness):")
    shifted_z = tiled_positions[:, 2] + 6.0
    print(f"  Shifted Z range: [{shifted_z.min():.4f}, {shifted_z.max():.4f}] nm")
    
    below_zero_shifted = shifted_z < 0
    above_9 = shifted_z >= 9.0
    
    print(f"  Z < 0: {np.sum(below_zero_shifted)} atoms")
    print(f"  Z >= 9: {np.sum(above_9)} atoms")
    print(f"  Z in [0, 9): {np.sum((shifted_z >= 0) & (shifted_z < 9.0))} atoms")

if __name__ == "__main__":
    print("Debugging tile_structure for different phases...")
    
    for phase in ["ice_ih", "ice_iii", "ice_ic", "ice_vii", "ice_viii"]:
        debug_tile_structure(phase)
