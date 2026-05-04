"""Test that water filler doesn't overlap with CH4 guests in top ice region.

This test verifies the fix for the water-guest overlap issue:
- Water filler molecules near the upper boundary were overlapping with CH4 guests
- Root cause: Overlap detection only checked ice OW vs water OW, not water OW vs guests
- Fix: Added second overlap check after guest tiling
"""

import numpy as np
from quickice.structure_generation.modes.slab import assemble_slab
from quickice.structure_generation.types import Candidate, InterfaceConfig


def create_structure_i_hydrate_candidate():
    """Create a mock structure I hydrate candidate with CH4 guests."""
    # Structure I hydrate unit cell: ~1.2 nm cubic
    # Contains 46 water molecules (184 atoms) and up to 8 CH4 guests (40 atoms)
    
    cell = np.array([
        [1.2, 0.0, 0.0],
        [0.0, 1.2, 0.0],
        [0.0, 0.0, 1.2]
    ])
    
    # Create water framework (TIP4P: OW, HW1, HW2, MW)
    n_water = 46
    water_positions = np.random.rand(n_water * 4, 3) * 1.2
    water_atom_names = []
    for _ in range(n_water):
        water_atom_names.extend(["OW", "HW1", "HW2", "MW"])
    
    # Create CH4 guests (united atom: Me) or all-atom (C, H, H, H, H)
    n_guest = 8
    # Use all-atom CH4
    guest_positions = np.random.rand(n_guest * 5, 3) * 1.2
    guest_atom_names = []
    for _ in range(n_guest):
        # GenIce order: H, H, H, H, C
        guest_atom_names.extend(["H", "H", "H", "H", "C"])
    
    # Combine: water framework first, then guests
    positions = np.vstack([water_positions, guest_positions])
    atom_names = water_atom_names + guest_atom_names
    
    metadata = {
        "original_hydrate": True,
        "temperature": 273.15,
        "pressure": 0.101325
    }
    
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=n_water,
        phase_id="sI",
        seed=12345,
        metadata=metadata
    )


def check_water_ch4_overlaps(positions, atom_names, box, overlap_threshold=0.3):
    """Check for overlaps between water OW and CH4 C atoms."""
    # Find water OW atoms
    ow_mask = np.array([name == 'OW' for name in atom_names])
    ow_positions = positions[ow_mask]
    
    # Find CH4 C atoms
    ch4_c_mask = np.array([name == 'C' for name in atom_names])
    ch4_c_positions = positions[ch4_c_mask]
    
    if len(ow_positions) == 0 or len(ch4_c_positions) == 0:
        return 0, []
    
    # Calculate minimum image distances
    def min_image_dist(pos1, pos2, box):
        delta = pos1 - pos2
        delta = delta - box * np.round(delta / box)
        return np.linalg.norm(delta)
    
    overlaps = []
    for i, ow_pos in enumerate(ow_positions):
        for j, ch4_pos in enumerate(ch4_c_positions):
            dist = min_image_dist(ow_pos, ch4_pos, box)
            if dist < overlap_threshold:
                overlaps.append((i, j, dist))
    
    return len(overlaps), overlaps


def test_water_ch4_no_overlap():
    """Test that water filler doesn't overlap with CH4 guests."""
    # Create hydrate candidate
    candidate = create_structure_i_hydrate_candidate()
    
    # Create slab configuration
    # Use dimensions that will trigger the overlap issue
    config = InterfaceConfig(
        mode="slab",
        box_x=3.6,  # 3 * 1.2 nm
        box_y=3.6,
        box_z=10.8,  # Will be adjusted
        seed=12345,
        ice_thickness=3.4,  # Will be adjusted to 3.6 nm (3 cells)
        water_thickness=3.9,  # Will be adjusted to 3.726 nm (2 cells)
        overlap_threshold=0.3
    )
    
    # Generate structure
    interface = assemble_slab(candidate, config)
    
    print(f"Generated structure:")
    print(f"  Box: {interface.cell[0,0]:.3f} x {interface.cell[1,1]:.3f} x {interface.cell[2,2]:.3f} nm")
    print(f"  Ice molecules: {interface.ice_nmolecules}")
    print(f"  Water molecules: {interface.water_nmolecules}")
    print(f"  Guest molecules: {interface.guest_nmolecules}")
    print(f"  Total atoms: {len(interface.positions)}")
    
    # Check for water-CH4 overlaps
    box = np.array([interface.cell[0,0], interface.cell[1,1], interface.cell[2,2]])
    overlap_count, overlaps = check_water_ch4_overlaps(
        interface.positions,
        interface.atom_names,
        box,
        overlap_threshold=config.overlap_threshold
    )
    
    print(f"\nOverlap check (threshold {config.overlap_threshold} nm):")
    print(f"  Water-CH4 overlaps: {overlap_count}")
    
    if overlap_count > 0:
        print(f"\nSample overlaps (first 10):")
        for i, (ow_idx, ch4_idx, dist) in enumerate(overlaps[:10]):
            ow_z = interface.positions[ow_idx * 4, 2]  # OW is at index ow_idx * 4
            ch4_z = interface.positions[interface.ice_atom_count + interface.water_atom_count + ch4_idx * 5 + 4, 2]  # C is last atom in CH4
            print(f"    OW at Z={ow_z:.3f}, CH4 at Z={ch4_z:.3f}, distance={dist:.3f} nm")
    
    # Verify no overlaps
    assert overlap_count == 0, f"Found {overlap_count} water-CH4 overlaps!"
    print(f"\n✓ No water-CH4 overlaps found!")


if __name__ == "__main__":
    test_water_ch4_no_overlap()
