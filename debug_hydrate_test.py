"""Detailed investigation of hydrate test case to understand duplicates."""

import numpy as np
import sys
sys.path.insert(0, '/share/home/nglokwan/quickice')

from quickice.structure_generation.types import Candidate, InterfaceConfig
from quickice.structure_generation.modes.slab import assemble_slab
from quickice.structure_generation.water_filler import tile_structure

# Patch tile_structure to log parameters
original_tile_structure = tile_structure
call_count = 0

def logged_tile_structure(positions, cell_dims, target_region, atoms_per_molecule=None, cell_matrix=None):
    global call_count
    call_count += 1
    
    print(f"\n{'='*70}")
    print(f"tile_structure CALL #{call_count}")
    print(f"{'='*70}")
    print(f"Positions: {len(positions)} atoms")
    print(f"Cell dims: {cell_dims}")
    print(f"Target region: {target_region}")
    print(f"Atoms per molecule: {atoms_per_molecule}")
    print(f"Cell matrix: {cell_matrix}")
    
    # Calculate expected tile counts
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
    
    print(f"\nExpected tile counts: nx={nx}, ny={ny}, nz={nz} (total {nx*ny*nz})")
    
    for i, (target, cell) in enumerate(zip(target_region, cell_dims)):
        ratio = target / cell
        rounded = round(ratio)
        exact = rounded * cell
        diff = abs(target - exact)
        rel_diff = diff / target if target > 0 else 0
        
        print(f"  Dim {i}: target={target:.6f}, cell={cell:.6f}, ratio={ratio:.6f}")
        print(f"         rounded={rounded}, exact={exact:.6f}, rel_diff={rel_diff:.6f} ({rel_diff*100:.3f}%)")
    
    result = original_tile_structure(positions, cell_dims, target_region, atoms_per_molecule, cell_matrix)
    
    print(f"\nResult: {result[1]} molecules")
    
    # Check for duplicates
    if result[1] > 0:
        from scipy.spatial import cKDTree
        
        molecule_centers = []
        n_mol = result[1]
        for mol_idx in range(n_mol):
            start = mol_idx * atoms_per_molecule if atoms_per_molecule else mol_idx * 4
            end = start + (atoms_per_molecule if atoms_per_molecule else 4)
            mol_atoms = result[0][start:end]
            com = mol_atoms.mean(axis=0)
            molecule_centers.append(com)
        
        molecule_centers = np.array(molecule_centers)
        tree = cKDTree(molecule_centers)
        duplicate_pairs = tree.query_pairs(0.25)
        
        print(f"Duplicate pairs in result: {len(duplicate_pairs)}")
    
    return result

# Monkey patch
import quickice.structure_generation.modes.slab as slab_module
slab_module.tile_structure = logged_tile_structure

# Now run the test
from tests.test_hydrate_guest_tiling import create_sI_hydrate_candidate, test_slab_hydrate_guest_tiling

print("=" * 70)
print("RUNNING HYDRATE TEST WITH DETAILED LOGGING")
print("=" * 70)

try:
    test_slab_hydrate_guest_tiling()
    print("\n✅ Test passed!")
except Exception as e:
    print(f"\n❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
