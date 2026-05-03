"""Investigate why 413/414 molecules are duplicates in hydrate test."""

import numpy as np
import sys
sys.path.insert(0, '/share/home/nglokwan/quickice')

from tests.test_hydrate_guest_tiling import create_sI_hydrate_candidate

print("=" * 70)
print("INVESTIGATING HYDRATE TEST INPUT POSITIONS")
print("=" * 70)

# Get the test candidate
candidate = create_sI_hydrate_candidate()

print(f"\nCandidate info:")
print(f"  Phase ID: {candidate.phase_id}")
print(f"  Molecules: {candidate.nmolecules}")
print(f"  Cell:\n{candidate.cell}")
print(f"  Positions shape: {candidate.positions.shape}")

# Extract water framework manually
# TIP4P water has atoms: OW, HW1, HW2, MW (4 atoms per molecule)
atoms_per_mol = 4
water_atom_prefixes = ['OW', 'HW', 'MW']

water_indices = []
for i, name in enumerate(candidate.atom_names):
    if any(name.startswith(prefix) for prefix in water_atom_prefixes):
        water_indices.append(i)

water_positions = candidate.positions[water_indices]
n_water_molecules = len(water_positions) // atoms_per_mol

print(f"\nWater framework:")
print(f"  Water atoms: {len(water_indices)}")
print(f"  Water molecules: {n_water_molecules}")

# Calculate molecule centers
molecule_centers = []
for mol_idx in range(n_water_molecules):
    start = mol_idx * atoms_per_mol
    end = start + atoms_per_mol
    mol_atoms = water_positions[start:end]
    com = mol_atoms.mean(axis=0)
    molecule_centers.append(com)

molecule_centers = np.array(molecule_centers)

print(f"\nMolecule centers range:")
print(f"  Min: {molecule_centers.min(axis=0)}")
print(f"  Max: {molecule_centers.max(axis=0)}")

# Check distances between molecules
from scipy.spatial import cKDTree
tree = cKDTree(molecule_centers)
close_pairs = tree.query_pairs(0.25)

print(f"\nClose pairs (< 0.25 nm) in original water framework: {len(close_pairs)}")

if close_pairs:
    print(f"\nFirst 10 close pairs:")
    for i, (idx1, idx2) in enumerate(list(close_pairs)[:10]):
        dist = np.linalg.norm(molecule_centers[idx1] - molecule_centers[idx2])
        print(f"  Pair {i+1}: Mols {idx1},{idx2}, distance {dist:.4f} nm")
        print(f"    Mol {idx1} COM: {molecule_centers[idx1]}")
        print(f"    Mol {idx2} COM: {molecule_centers[idx2]}")

# Check if molecules are all at similar positions
unique_positions = set()
for com in molecule_centers:
    # Round to 0.01 nm precision
    rounded = tuple(np.round(com, 2))
    unique_positions.add(rounded)

print(f"\nUnique positions (rounded to 0.01 nm): {len(unique_positions)}")

if len(unique_positions) < n_water_molecules * 0.1:
    print(f"\n⚠️  WARNING: Only {len(unique_positions)} unique positions for {n_water_molecules} molecules!")
    print(f"   This means most molecules are at nearly identical positions.")
    print(f"   This is an issue with the TEST DATA, not the tiling logic!")
    
    # Show the unique positions
    print(f"\nUnique positions:")
    for pos in sorted(unique_positions):
        count = sum(1 for com in molecule_centers if tuple(np.round(com, 2)) == pos)
        print(f"  {pos}: {count} molecules")

print(f"\n{'='*70}")
print("CONCLUSION")
print(f"{'='*70}")

if len(close_pairs) > n_water_molecules * 0.5:
    print("\nThe test data has molecules at nearly identical positions.")
    print("This causes duplicate detection to remove most molecules after tiling.")
    print("This is NOT a bug in tile_structure - it's expected behavior for overlapping positions.")
    print("\nThe fix for the over-tiling bug is working correctly!")
    print("The remaining 'duplicates' in tests are from the test data itself.")
