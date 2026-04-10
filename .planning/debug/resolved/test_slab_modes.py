#!/usr/bin/env python3
"""Debug slab mode PBC overlap for different phases."""

import numpy as np
from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.modes.slab import assemble_slab

# Phase stability conditions (T in K, P in MPa)
PHASE_CONDITIONS = {
    "ice_ih": (273, 0.1),      # Ice Ih: low P, near melting
    "ice_ic": (200, 0.1),      # Ice Ic: low T, low P (metastable, but GenIce can generate)
    "ice_iii": (250, 250),    # Ice III: 250 K, 250 MPa
    "ice_vii": (300, 2500),   # Ice VII: 300 K, 2500 MPa
    "ice_viii": (200, 2500),  # Ice VIII: 200 K, 2500 MPa
}

def test_slab_mode(phase_id: str, nmolecules: int = 64, seed: int = 42):
    """Test slab mode for a specific phase."""
    T, P = PHASE_CONDITIONS.get(phase_id, (273, 0.1))
    phase_info = lookup_phase(T, P)
    # Override with correct phase_id if needed
    phase_info["phase_id"] = phase_id
    phase_info["phase_name"] = {"ice_ih": "Ice Ih", "ice_ic": "Ice Ic", "ice_iii": "Ice III", "ice_vii": "Ice VII", "ice_viii": "Ice VIII"}[phase_id]
    
    result = generate_candidates(phase_info, nmolecules, n_candidates=1, base_seed=seed)
    candidate = result.candidates[0]
    
    print(f"\n=== Testing slab mode for {phase_id} ===")
    print(f"Cell: {candidate.cell}")
    print(f"Cell Z: {candidate.cell[2, 2]:.4f} nm")
    
    z_positions = candidate.positions[:, 2]
    print(f"Original Z range: [{z_positions.min():.4f}, {z_positions.max():.4f}] nm")
    
    # Try slab mode with standard dimensions
    config = InterfaceConfig(
        mode="slab",
        box_x=3.0,
        box_y=3.0,
        box_z=9.0,  # 2*3 + 3
        seed=seed,
        ice_thickness=3.0,
        water_thickness=3.0
    )
    
    try:
        interface = assemble_slab(candidate, config)
        print(f"SUCCESS! Generated slab interface")
        print(f"  Ice atoms: {interface.ice_atom_count}")
        print(f"  Water atoms: {interface.water_atom_count}")
        
        # Check final Z positions
        final_z = interface.positions[:, 2]
        print(f"  Final Z range: [{final_z.min():.4f}, {final_z.max():.4f}] nm")
        
    except Exception as e:
        print(f"FAILED: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Testing slab mode for different phases...")
    
    # Test phases that work (Ih, III)
    for phase in ["ice_ih", "ice_iii"]:
        test_slab_mode(phase)
    
    # Test phases that fail (Ic, VII, VIII)
    for phase in ["ice_ic", "ice_vii", "ice_viii"]:
        test_slab_mode(phase)
