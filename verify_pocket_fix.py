"""Verify guest-water overlap fix in pocket mode.

This script generates a pocket mode structure with hydrate and checks:
1. Ice extends to all boundaries (no missing ice)
2. No guest-water overlaps exist
"""

import numpy as np
from quickice.structure_generation.modes.pocket import assemble_pocket
from quickice.structure_generation.types import Candidate, InterfaceConfig


def create_mock_hydrate_candidate(n_water: int = 8, n_guest: int = 1) -> Candidate:
    """Create a mock hydrate candidate with water framework + guest molecules.
    
    Structure:
    - Water framework: TIP4P style (OW, HW1, HW2, MW) x n_water
    - Guest molecules: Me (united-atom methane) x n_guest
    
    Total atoms: n_water * 4 + n_guest * 1
    """
    # Water framework (TIP4P: 4 atoms per molecule)
    # Create realistic TIP4P lattice - ALL POSITIVE coordinates, ~0.45nm apart
    positions = []
    atom_names = []
    
    for i in range(n_water):
        x = 0.1 + (i % 2) * 0.45
        y = 0.1 + ((i // 2) % 2) * 0.45
        z = 0.1 + (i // 4) * 0.45
        positions.extend([
            [x, y, z],       # OW - all positive
            [x + 0.07, y, z + 0.05],  # HW1
            [x + 0.05, y + 0.07, z + 0.03],    # HW2
            [x, y + 0.15, z + 0.05]          # MW
        ])
        atom_names.extend(["OW", "HW1", "HW2", "MW"])
    
    # Guest molecules (Me: 1 atom each) - offset from water framework
    for i in range(n_guest):
        x = 0.3 + (i * 0.3)  # Offset from water framework
        y = 0.3 + (i * 0.2)
        z = 0.3 + (i * 0.2)
        positions.append([x, y, z])
        atom_names.append("Me")
    
    positions = np.array(positions, dtype=float)
    
    # Create unit cell - cube large enough for all atoms
    max_coords = positions.max(axis=0)
    cell = np.diag(max_coords + 0.5)  # Add 0.5 nm margin
    
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=n_water,
        phase_id="hydrate_sI",
        seed=12345,
        metadata={
            'original_hydrate': True,
            'temperature': 273.15,
            'pressure': 0.101325
        }
    )


def check_ice_at_boundaries(positions, box_dims, atoms_per_mol=4):
    """Check if ice extends to all 6 boundaries."""
    # Get oxygen positions (first atom of each molecule)
    o_positions = positions[::atoms_per_mol]
    
    # Check each boundary
    boundaries = {
        'X=0': np.min(o_positions[:, 0]),
        'X=max': np.max(o_positions[:, 0]),
        'Y=0': np.min(o_positions[:, 1]),
        'Y=max': np.max(o_positions[:, 1]),
        'Z=0': np.min(o_positions[:, 2]),
        'Z=max': np.max(o_positions[:, 2]),
    }
    
    print("\nIce boundary coverage:")
    for boundary, value in boundaries.items():
        print(f"  {boundary}: {value:.3f} nm")
    
    # Check if ice reaches close to boundaries (within 0.5 nm is acceptable)
    tolerance = 0.5
    issues = []
    if boundaries['X=0'] > tolerance:
        issues.append(f"Ice doesn't reach X=0 boundary (min X = {boundaries['X=0']:.3f} nm)")
    if boundaries['Y=0'] > tolerance:
        issues.append(f"Ice doesn't reach Y=0 boundary (min Y = {boundaries['Y=0']:.3f} nm)")
    if boundaries['Z=0'] > tolerance:
        issues.append(f"Ice doesn't reach Z=0 boundary (min Z = {boundaries['Z=0']:.3f} nm)")
    
    max_expected = box_dims - 0.3  # Allow 0.3 nm from boundary
    if boundaries['X=max'] < max_expected[0]:
        issues.append(f"Ice doesn't reach X=max boundary (max X = {boundaries['X=max']:.3f} nm, box = {box_dims[0]:.3f} nm)")
    if boundaries['Y=max'] < max_expected[1]:
        issues.append(f"Ice doesn't reach Y=max boundary (max Y = {boundaries['Y=max']:.3f} nm, box = {box_dims[1]:.3f} nm)")
    if boundaries['Z=max'] < max_expected[2]:
        issues.append(f"Ice doesn't reach Z=max boundary (max Z = {boundaries['Z=max']:.3f} nm, box = {box_dims[2]:.3f} nm)")
    
    return issues


def check_guest_water_overlaps(interface_struct, threshold=0.25):
    """Check for overlaps between guest molecules and water molecules."""
    positions = interface_struct.positions
    atom_names = interface_struct.atom_names
    
    # Separate guests and water
    guest_indices = [i for i, name in enumerate(atom_names) if name not in ['O', 'H', 'OW', 'HW1', 'HW2', 'MW']]
    water_ow_indices = [i for i, name in enumerate(atom_names) if name == 'OW']
    
    if not guest_indices or not water_ow_indices:
        print("\nNo guests or water found")
        return []
    
    guest_positions = positions[guest_indices]
    water_ow_positions = positions[water_ow_indices]
    
    print(f"\nChecking guest-water overlaps:")
    print(f"  Guest atoms: {len(guest_positions)}")
    print(f"  Water OW atoms: {len(water_ow_positions)}")
    
    # Check for overlaps
    overlaps = []
    for i, guest_pos in enumerate(guest_positions):
        distances = np.linalg.norm(water_ow_positions - guest_pos, axis=1)
        close_water = np.where(distances < threshold)[0]
        if len(close_water) > 0:
            overlaps.append({
                'guest_idx': i,
                'guest_atom': atom_names[guest_indices[i]],
                'overlapping_water': len(close_water),
                'min_distance': np.min(distances[close_water])
            })
    
    if overlaps:
        print(f"  ⚠️  Found {len(overlaps)} guest atoms with overlapping water:")
        for overlap in overlaps[:5]:  # Show first 5
            print(f"    Guest atom {overlap['guest_idx']} ({overlap['guest_atom']}): "
                  f"{overlap['overlapping_water']} overlapping water, min dist = {overlap['min_distance']:.3f} nm")
        if len(overlaps) > 5:
            print(f"    ... and {len(overlaps) - 5} more")
    else:
        print(f"  ✓ No guest-water overlaps found (threshold: {threshold} nm)")
    
    return overlaps


def main():
    print("=" * 70)
    print("Verifying guest-water overlap fix in pocket mode")
    print("=" * 70)
    
    # Create hydrate candidate
    print("\n1. Creating mock hydrate candidate (water + CH4 guests)...")
    candidate = create_mock_hydrate_candidate(n_water=16, n_guest=8)
    
    # Generate pocket interface
    print("\n2. Generating pocket interface...")
    config = InterfaceConfig(
        mode="pocket",
        box_x=4.0,
        box_y=4.0,
        box_z=4.0,
        seed=42,
        pocket_diameter=2.0,
        pocket_shape="sphere"
    )
    
    interface_struct = assemble_pocket(candidate, config)
    
    print(f"\n3. Structure generated:")
    print(f"  Ice molecules: {interface_struct.ice_nmolecules}")
    print(f"  Guest molecules: {interface_struct.guest_nmolecules}")
    print(f"  Water molecules: {interface_struct.water_nmolecules}")
    print(f"  Box dimensions: {interface_struct.cell[0, 0]:.3f} x {interface_struct.cell[1, 1]:.3f} x {interface_struct.cell[2, 2]:.3f} nm")
    
    # Check ice at boundaries
    print("\n4. Checking ice at boundaries...")
    ice_positions = interface_struct.positions[:interface_struct.ice_atom_count]
    box_dims = np.array([interface_struct.cell[0, 0], interface_struct.cell[1, 1], interface_struct.cell[2, 2]])
    boundary_issues = check_ice_at_boundaries(ice_positions, box_dims, atoms_per_mol=4)
    
    if boundary_issues:
        print(f"\n  ⚠️  Found {len(boundary_issues)} boundary issues:")
        for issue in boundary_issues:
            print(f"    - {issue}")
    else:
        print("\n  ✓ Ice extends to all boundaries")
    
    # Check guest-water overlaps
    print("\n5. Checking guest-water overlaps...")
    overlap_issues = check_guest_water_overlaps(interface_struct)
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    all_passed = True
    
    if boundary_issues:
        print(f"❌ Ice boundary coverage: {len(boundary_issues)} issues")
        all_passed = False
    else:
        print("✓ Ice boundary coverage: OK")
    
    if overlap_issues:
        print(f"❌ Guest-water overlaps: {len(overlap_issues)} overlaps found")
        all_passed = False
    else:
        print("✓ Guest-water overlaps: None detected")
    
    print("=" * 70)
    
    if all_passed:
        print("✓ ALL VERIFICATIONS PASSED")
        return 0
    else:
        print("❌ SOME VERIFICATIONS FAILED")
        return 1


if __name__ == "__main__":
    exit(main())
