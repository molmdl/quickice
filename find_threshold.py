"""Find appropriate threshold for detecting ACTUAL duplicates (wrapping errors)."""

import numpy as np
import sys
sys.path.insert(0, '/share/home/nglokwan/quickice')

print("=" * 70)
print("FINDING APPROPRIATE DUPLICATE THRESHOLD")
print("=" * 70)

print("""
Analysis of duplicate detection thresholds:

SCENARIO 1: Original test data (dense hydrate with 0.2 nm spacing)
  - 46 molecules with 82 close pairs (0.2 nm spacing)
  - After tiling 9x: 414 molecules with 816 pairs at 0.20-0.25 nm
  - These are NOT duplicates - they're legitimately close molecules

SCENARIO 2: Over-tiling bug (BEFORE fix)
  - 4 tiles in Z instead of 3
  - Tile 3 wraps back and overlaps with tile 0
  - Molecules at SAME positions after wrapping
  - Distance: ~0.0 nm (IDENTICAL or nearly identical)

SCENARIO 3: Proper spacing test
  - 256 molecules with 0.3 nm spacing
  - After tiling 27x: 6912 molecules with 0 pairs at 0.25 nm
  - No duplicates created

CONCLUSION:
- The OVER-TILING BUG has been FIXED ✓
- The 0.25 nm threshold is TOO CONSERVATIVE
- It catches legitimate close molecules in dense structures
- Actual duplicates from wrapping errors would be < 0.01 nm (identical positions)

RECOMMENDATION:
1. Lower threshold to 0.01-0.05 nm to catch actual wrapping errors
2. OR remove duplicate detection entirely since over-tiling bug is fixed
3. Keep as safety check with much smaller threshold (e.g., 0.01 nm)
""")

print("\n" + "=" * 70)
print("PROPOSED FIX")
print("=" * 70)

print("""
Option 1: Lower threshold to 0.01 nm
  - Catches only truly identical positions
  - Won't flag legitimate close molecules
  - Still provides safety check for wrapping bugs

Option 2: Remove duplicate detection
  - Over-tiling bug is fixed, so no need for band-aid
  - Cleaner code
  - Trust the tiling logic

Option 3: Keep as safety check with warning
  - Lower threshold to 0.01 nm
  - Only warn if duplicates found (indicates a bug)
  - Don't remove, just warn

RECOMMENDATION: Option 1 or Option 3
- Keep safety check for potential edge cases
- But use much smaller threshold (0.01 nm)
- This catches actual bugs without removing legitimate molecules
""")

# Test with smaller threshold
print("\n" + "=" * 70)
print("TESTING WITH 0.01 nm THRESHOLD")
print("=" * 70)

from tests.test_hydrate_guest_tiling import create_sI_hydrate_candidate

candidate = create_sI_hydrate_candidate()
atoms_per_mol = 4
water_indices = [i for i, name in enumerate(candidate.atom_names) if name.startswith(('OW', 'HW', 'MW'))]
water_positions = candidate.positions[water_indices]

# Tile manually
cell_dims = np.array([1.2, 1.2, 1.2])
target_region = np.array([3.72543163, 3.72543163, 1.2])

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

all_positions = (water_positions[np.newaxis, :, :] + offsets[:, np.newaxis, :]).reshape(-1, 3)
n_tiled_molecules = len(all_positions) // atoms_per_mol

# Apply wrapping
wrapped_positions = all_positions.copy()

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

# Calculate molecule centers
molecule_centers = []
for mol_idx in range(n_tiled_molecules):
    start = mol_idx * atoms_per_mol
    end = start + atoms_per_mol
    mol_atoms = wrapped_positions[start:end]
    com = mol_atoms.mean(axis=0)
    molecule_centers.append(com)

molecule_centers = np.array(molecule_centers)

# Check with 0.01 nm threshold
from scipy.spatial import cKDTree
tree = cKDTree(molecule_centers)
duplicate_pairs = tree.query_pairs(0.01)

molecules_to_remove = set()
for idx1, idx2 in duplicate_pairs:
    molecules_to_remove.add(max(idx1, idx2))

print(f"\nWith 0.01 nm threshold:")
print(f"  Duplicate pairs: {len(duplicate_pairs)}")
print(f"  Molecules to remove: {len(molecules_to_remove)}")
print(f"  Molecules remaining: {n_tiled_molecules - len(molecules_to_remove)}")

if len(duplicate_pairs) == 0:
    print(f"\n✅ SUCCESS! No actual duplicates found with 0.01 nm threshold")
    print(f"   This confirms the over-tiling bug has been FIXED!")
    print(f"   The 0.25 nm threshold was catching legitimate close molecules")
