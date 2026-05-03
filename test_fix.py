"""Test the fix for duplicate prevention in tile_structure."""

import numpy as np
import sys
sys.path.insert(0, '/share/home/nglokwan/quickice')

from quickice.structure_generation.water_filler import tile_structure

def test_tile_structure_fix():
    """Test that the fix prevents duplicate creation."""
    
    print("=" * 70)
    print("TESTING FIX: Does new calc_tile_count prevent duplicates?")
    print("=" * 70)
    
    # Simulate the hydrate case
    cell_dims = np.array([2.46, 2.46, 1.2])
    target_region = np.array([7.451, 7.451, 3.601])
    atoms_per_molecule = 4
    
    # Create test positions: 10 molecules
    np.random.seed(42)
    n_test_molecules = 10
    test_positions = []
    for i in range(n_test_molecules):
        base_pos = np.random.rand(3) * cell_dims
        for j in range(4):
            offset = np.array([0.0, 0.0, 0.0]) if j == 0 else \
                     np.array([0.1, 0.0, 0.0]) if j == 1 else \
                     np.array([-0.1, 0.0, 0.0]) if j == 2 else \
                     np.array([0.0, 0.0, 0.01])
            test_positions.append(base_pos + offset)
    
    positions = np.array(test_positions)
    
    print(f"\nInput: {n_test_molecules} molecules ({len(positions)} atoms)")
    print(f"Cell dimensions: {cell_dims}")
    print(f"Target region: {target_region}")
    print(f"\nExpected tile counts:")
    print(f"  X: 7.451 / 2.46 = 3.029 → should be 3 (within 5% of 3*2.46=7.38)")
    print(f"  Y: 7.451 / 2.46 = 3.029 → should be 3")
    print(f"  Z: 3.601 / 1.2  = 3.001 → should be 3 (within 0.03% of 3*1.2=3.6)")
    
    # Call tile_structure with the fix
    print(f"\n{'='*70}")
    print("CALLING tile_structure WITH FIX")
    print(f"{'='*70}")
    
    tiled_positions, n_molecules = tile_structure(
        positions, cell_dims, target_region, atoms_per_molecule
    )
    
    print(f"\nResult: {n_molecules} molecules ({len(tiled_positions)} atoms)")
    print(f"Expected: {n_test_molecules * 3 * 3 * 3} = 270 molecules (if 3x3x3 tiles)")
    
    # Check for duplicates
    print(f"\n{'='*70}")
    print("CHECKING FOR DUPLICATES")
    print(f"{'='*70}")
    
    molecule_centers = []
    for mol_idx in range(n_molecules):
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        mol_atoms = tiled_positions[start_atom:end_atom]
        com = mol_atoms.mean(axis=0)
        molecule_centers.append(com)
    
    molecule_centers = np.array(molecule_centers)
    
    from scipy.spatial import cKDTree
    if len(molecule_centers) > 0:
        tree = cKDTree(molecule_centers)
        duplicate_pairs = tree.query_pairs(0.25)
        
        print(f"\nDuplicate pairs found: {len(duplicate_pairs)}")
        
        if len(duplicate_pairs) == 0:
            print("✅ SUCCESS! No duplicates created!")
        else:
            print(f"❌ FAILED! Still have {len(duplicate_pairs)} duplicates")
            
            # Show first few
            for i, (idx1, idx2) in enumerate(list(duplicate_pairs)[:5]):
                distance = np.linalg.norm(molecule_centers[idx1] - molecule_centers[idx2])
                print(f"  Pair {i+1}: Molecules {idx1} and {idx2}, distance {distance:.4f} nm")
    else:
        print("No molecules created")
    
    print(f"\n{'='*70}")
    print("TEST COMPLETE")
    print(f"{'='*70}")

if __name__ == "__main__":
    test_tile_structure_fix()
