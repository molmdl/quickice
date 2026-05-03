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
print(f"  Atom names: {candidate.atom_names[:20]} ... (showing first 20)")

# Check if it's a hydrate
if candidate.metadata and 'candidate_type' in candidate.metadata:
    print(f"  Type: {candidate.metadata['candidate_type']}")

# Get water framework positions
from quickice.structure_generation.modes.slab import extract_water_framework

water_positions, water_atom_names, atoms_per_mol = extract_water_framework(
    candidate.positions,
    candidate.atom_names
)

print(f"\nWater framework:")
print(f"  Positions shape: {water_positions.shape}")
print(f"  Atoms per molecule: {atoms_per_mol}")
print(f"  Number of molecules: {len(water_positions) // atoms_per_mol}")

# Check spacing of water molecules
molecule_centers = []
n_molecules = len(water_positions) // atoms_per_mol

for mol_idx in range(n_molecules):
    start = mol_idx * atoms_per_mol
    end = start + atoms_per_mol
    mol_atoms = water_positions[start:end]
    com = mol_atoms.mean(axis=0)
    molecule_centers.append(com)

molecule_centers = np.array(molecule_centers)

print(f"\nMolecule centers:")
print(f"  Min: {molecule_centers.min(axis=0)}")
print(f"  Max: {molecule_centers.max(axis=0)}")

# Check distances between molecules
from scipy.spatial import cKDTree
tree = cKDTree(molecule_centers)
close_pairs = tree.query_pairs(0.25)

print(f"\nClose pairs (< 0.25 nm) in original water framework: {len(close_pairs)}")

if close_pairs:
    print("First 10 close pairs:")
    for i, (idx1, idx2) in enumerate(list(close_pairs)[:10]):
        dist = np.linalg.norm(molecule_centers[idx1] - molecule_centers[idx2])
        print(f"  Pair {i+1}: Mols {idx1},{idx2}, distance {dist:.4f} nm")
        print(f"    Mol {idx1} COM: {molecule_centers[idx1]}")
        print(f"    Mol {idx2} COM: {molecule_centers[idx2]}")

# Check if molecules are all at the same position (or very close)
if len(close_pairs) > n_molecules * 0.9:
    print("\n⚠️  WARNING: Most molecules are very close together!")
    print("This suggests the test data has molecules clustered at the same positions.")

# Now tile and see what happens
print(f"\n{'='*70}")
print("TESTING TILING")
print(f"{'='*70}")

from quickice.structure_generation.water_filler import tile_structure

cell_dims = np.array([1.2, 1.2, 1.2])
target_region = np.array([3.72543163, 3.72543163, 1.2])

print(f"\nInput: {n_molecules} molecules")
print(f"Cell dims: {cell_dims}")
print(f"Target region: {target_region}")

tiled_positions, n_tiled_molecules = tile_structure(
    water_positions,
    cell_dims,
    target_region,
    atoms_per_molecule=atoms_per_mol
)

print(f"\nResult: {n_tiled_molecules} molecules")

# Calculate expected
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

expected_molecules = n_molecules * nx * ny * nz
print(f"Expected: {expected_molecules} molecules ({n_molecules} * {nx}*{ny}*{nz})")

if n_tiled_molecules < expected_molecules * 0.5:
    print(f"\n⚠️  SIGNIFICANTLY FEWER MOLECULES THAN EXPECTED!")
    print(f"   This is because the ORIGINAL test data has molecules at nearly identical positions.")
    print(f"   When tiled, they create duplicates that are then removed.")
