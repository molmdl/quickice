"""Deep dive into why 413/414 molecules are removed."""

import numpy as np
import sys
sys.path.insert(0, '/share/home/nglokwan/quickice')

from tests.test_hydrate_guest_tiling import create_sI_hydrate_candidate
from scipy.spatial import cKDTree

print("=" * 70)
print("DEEP DIVE: Why 413/414 molecules removed?")
print("=" * 70)

# Get test data
candidate = create_sI_hydrate_candidate()

# Extract water framework
atoms_per_mol = 4
water_indices = [i for i, name in enumerate(candidate.atom_names) if name.startswith(('OW', 'HW', 'MW'))]
water_positions = candidate.positions[water_indices]
n_water_molecules = len(water_positions) // atoms_per_mol

print(f"\nOriginal water framework: {n_water_molecules} molecules")

# Manually tile to see what happens
cell_dims = np.array([1.2, 1.2, 1.2])
target_region = np.array([3.72543163, 3.72543163, 1.2])

# Calculate tile counts (from our fix)
import math
tolerance = 0.05

def calc_tile_count(target_dim, cell_dim):
    if cell_dim <= 0:
        return 1
    ratio = target_dim / cell_dim
    rounded = round(ratio)
    if rounded >= 1:
        exact_dim = rounded * cell_dim
        if target_dim > 0 and abs(target_dim - exact_dim) / target_dim < tolerance:
            return rounded
    return max(1, math.ceil(ratio))

nx = calc_tile_count(target_region[0], cell_dims[0])
ny = calc_tile_count(target_region[1], cell_dims[1])
nz = calc_tile_count(target_region[2], cell_dims[2])

print(f"\nTile counts: nx={nx}, ny={ny}, nz={nz} (total {nx*ny*nz})")

# Generate tiles
ix_vals = np.arange(nx)
iy_vals = np.arange(ny)
iz_vals = np.arange(nz)

ix_grid, iy_grid, iz_grid = np.meshgrid(ix_vals, iy_vals, iz_vals, indexing='ij')

a, b, c = cell_dims
offsets = np.stack([
    ix_grid.ravel() * a,
    iy_grid.ravel() * b,
    iz_grid.ravel() * c
], axis=1)

print(f"\nTile offsets:")
for i, offset in enumerate(offsets):
    print(f"  Tile {i}: offset {offset}")

# Apply offsets
all_positions = (water_positions[np.newaxis, :, :] + offsets[:, np.newaxis, :]).reshape(-1, 3)
n_tiled_molecules = len(all_positions) // atoms_per_mol

print(f"\nAfter tiling: {n_tiled_molecules} molecules (should be {n_water_molecules * len(offsets)})")

# Apply wrapping (simulate tile_structure)
wrapped_positions = all_positions.copy()

print(f"\nApplying wrapping...")
for mol_idx in range(n_tiled_molecules):
    start = mol_idx * atoms_per_mol
    end = start + atoms_per_mol
    mol_atoms = wrapped_positions[start:end]
    
    for dim in range(3):
        com = mol_atoms[:, dim].mean()
        
        if com < 0:
            n_boxes = int(np.ceil(-com / target_region[dim]))
            wrapped_positions[start:end, dim] += n_boxes * target_region[dim]
            mol_atoms = wrapped_positions[start:end]
        elif com >= target_region[dim]:
            n_boxes = int(np.floor(com / target_region[dim]))
            wrapped_positions[start:end, dim] -= n_boxes * target_region[dim]
            mol_atoms = wrapped_positions[start:end]

# Calculate molecule centers after wrapping
molecule_centers = []
for mol_idx in range(n_tiled_molecules):
    start = mol_idx * atoms_per_mol
    end = start + atoms_per_mol
    mol_atoms = wrapped_positions[start:end]
    com = mol_atoms.mean(axis=0)
    molecule_centers.append(com)

molecule_centers = np.array(molecule_centers)

print(f"\nAfter wrapping, molecule centers range:")
print(f"  X: [{molecule_centers[:, 0].min():.6f}, {molecule_centers[:, 0].max():.6f}]")
print(f"  Y: [{molecule_centers[:, 1].min():.6f}, {molecule_centers[:, 1].max():.6f}]")
print(f"  Z: [{molecule_centers[:, 2].min():.6f}, {molecule_centers[:, 2].max():.6f}]")

# Check for duplicates
print(f"\n{'='*70}")
print("DUPLICATE DETECTION")
print(f"{'='*70}")

# Try different thresholds
for threshold in [0.25, 0.20, 0.15, 0.10, 0.05, 0.01]:
    tree = cKDTree(molecule_centers)
    duplicate_pairs = tree.query_pairs(threshold)
    
    # Count how many molecules would be removed
    molecules_to_remove = set()
    for idx1, idx2 in duplicate_pairs:
        molecules_to_remove.add(max(idx1, idx2))
    
    n_remaining = n_tiled_molecules - len(molecules_to_remove)
    
    print(f"\nThreshold {threshold:.2f} nm:")
    print(f"  Duplicate pairs: {len(duplicate_pairs)}")
    print(f"  Molecules to remove: {len(molecules_to_remove)}")
    print(f"  Molecules remaining: {n_remaining}")

# Check actual minimum distances
print(f"\n{'='*70}")
print("ACTUAL MINIMUM DISTANCES")
print(f"{'='*70}")

# Find the minimum distance between ANY two molecules
min_dist = float('inf')
min_pair = None

for i in range(len(molecule_centers)):
    for j in range(i+1, len(molecule_centers)):
        dist = np.linalg.norm(molecule_centers[i] - molecule_centers[j])
        if dist < min_dist:
            min_dist = dist
            min_pair = (i, j)

print(f"\nMinimum distance: {min_dist:.6f} nm")
print(f"Between molecules: {min_pair}")

# Check how many pairs are within different distance ranges
distance_ranges = [
    (0.0, 0.01, "IDENTICAL (0-0.01 nm)"),
    (0.01, 0.05, "Very close (0.01-0.05 nm)"),
    (0.05, 0.10, "Close (0.05-0.10 nm)"),
    (0.10, 0.15, "Nearby (0.10-0.15 nm)"),
    (0.15, 0.20, "Proximity (0.15-0.20 nm)"),
    (0.20, 0.25, "Threshold (0.20-0.25 nm)"),
]

print(f"\nPairs by distance range:")
for min_d, max_d, label in distance_ranges:
    count = 0
    for i in range(len(molecule_centers)):
        for j in range(i+1, len(molecule_centers)):
            dist = np.linalg.norm(molecule_centers[i] - molecule_centers[j])
            if min_d <= dist < max_d:
                count += 1
    print(f"  {label}: {count} pairs")

print(f"\n{'='*70}")
print("ANALYSIS")
print(f"{'='*70}")

if min_dist < 0.01:
    print(f"\n⚠️  CRITICAL: Found molecules at nearly identical positions ({min_dist:.6f} nm)")
    print(f"   This suggests a bug in the tiling or wrapping logic!")
elif min_dist < 0.05:
    print(f"\n⚠️  WARNING: Found very close molecules ({min_dist:.6f} nm)")
    print(f"   This might be from the original test data or over-tiling")
elif min_dist >= 0.10:
    print(f"\n✅ No severe overlaps found (minimum distance: {min_dist:.6f} nm)")
    print(f"   The 0.25 nm threshold is catching molecules that are legitimately close")
    print(f"   but not truly duplicate. Consider lowering the threshold.")
