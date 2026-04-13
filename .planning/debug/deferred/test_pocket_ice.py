#!/usr/bin/env python
"""Test pocket interface generation to check if ice is missing."""

from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface

def test_pocket_interface():
    print("="*60)
    print("POCKET INTERFACE ICE TEST")
    print("="*60)
    
    # Generate Ice II candidate
    print("\nGenerating Ice II candidate...")
    phase_info = {
        "phase_id": "ice_ii",
        "phase_name": "Ice II",
        "density": 1.18,
        "temperature": 238,
        "pressure": 300,
    }
    result = generate_candidates(phase_info, nmolecules=50, n_candidates=1)
    candidate = result.candidates[0]
    
    print(f"Candidate molecules: {candidate.nmolecules}")
    print(f"Candidate positions: {len(candidate.positions)}")
    
    # Generate pocket interface
    config = InterfaceConfig(
        mode="pocket",
        box_x=4.0,
        box_y=4.0,
        box_z=4.0,
        seed=42,
        pocket_diameter=2.0,
        pocket_shape="sphere",
    )
    
    print(f"\nGenerating pocket interface...")
    print(f"Config: box={config.box_x}x{config.box_y}x{config.box_z}, pocket_diameter={config.pocket_diameter}")
    
    interface = generate_interface(candidate, config)
    
    print(f"\nInterface results:")
    print(f"  Ice molecules: {interface.ice_nmolecules}")
    print(f"  Water molecules: {interface.water_nmolecules}")
    print(f"  Ice atom count: {interface.ice_atom_count}")
    print(f"  Water atom count: {interface.water_atom_count}")
    print(f"  Total positions: {len(interface.positions)}")
    
    print(f"\nReport:\n{interface.report}")
    
    if interface.ice_nmolecules == 0:
        print("\n*** ERROR: Ice nmolecules is 0! ***")
        print("This explains the empty regions - there's no ice!")
        return False
    else:
        print("\n✓ Ice nmolecules > 0")
        return True

if __name__ == "__main__":
    success = test_pocket_interface()
    exit(0 if success else 1)