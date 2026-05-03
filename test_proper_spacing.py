"""Test fix with properly spaced molecules (no artificial overlaps)."""

import numpy as np
import sys
sys.path.insert(0, '/share/home/nglokwan/quickice')

from quickice.structure_generation.water_filler import tile_structure

def test_with_proper_spacing():
    """Test with molecules that have proper spacing (no artificial close pairs)."""
    
    print("=" * 70)
    print("TEST WITH PROPERLY SPACED MOLECULES")
    print("=" * 70)
    
    # Create molecules with minimum 0.3 nm spacing (realistic for water)
    cell_dims = np.array([2.46, 2.46, 1.2])
    target_region = np.array([7.451, 7.451, 3.601])
    atoms_per_molecule = 4
    
    # Create a regular grid of molecules with proper spacing
    spacing = 0.3  # 0.3 nm minimum spacing
    n_mol_x = int(cell_dims[0] / spacing)
    n_mol_y = int(cell_dims[1] / spacing)
    n_mol_z = int(cell_dims[2] / spacing)
    
    test_positions = []
    for i in range(n_mol_x):
        for j in range(n_mol_y):
            for k in range(n_mol_z):
                base_pos = np.array([
                    i * spacing + 0.05,
                    j * spacing + 0.05,
                    k * spacing + 0.05
                ])
                # Create 4 atoms for TIP4P molecule
                test_positions.append(base_pos)  # OW
                test_positions.append(base_pos + [0.1, 0, 0])  # HW1
                test_positions.append(base_pos + [-0.1, 0, 0])  # HW2
                test_positions.append(base_pos + [0, 0, 0.01])  # MW
    
    positions = np.array(test_positions)
    n_molecules = len(positions) // atoms_per_molecule
    
    print(f"\nCreated {n_molecules} molecules with {spacing} nm spacing")
    print(f"Cell dimensions: {cell_dims}")
    print(f"Target region: {target_region}")
    
    # Check minimum spacing in original molecules
    molecule_centers = []
    for mol_idx in range(n_molecules):
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        mol_atoms = positions[start_atom:end_atom]
        com = mol_atoms.mean(axis=0)
        molecule_centers.append(com)
    
    molecule_centers = np.array(molecule_centers)
    
    from scipy.spatial import cKDTree
    tree = cKDTree(molecule_centers)
    close_pairs = tree.query_pairs(0.25)
    
    print(f"Close pairs (< 0.25 nm) in original data: {len(close_pairs)}")
    
    # Now test tile_structure
    print(f"\n{'='*70}")
    print("TESTING tile_structure")
    print(f"{'='*70}")
    
    tiled_positions, n_tiled_molecules = tile_structure(
        positions, cell_dims, target_region, atoms_per_molecule
    )
    
    print(f"\nResult: {n_tiled_molecules} molecules")
    print(f"Expected: {n_molecules * 27} molecules (27 tiles)")
    
    # Check for duplicates in result
    tiled_centers = []
    for mol_idx in range(n_tiled_molecules):
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        mol_atoms = tiled_positions[start_atom:end_atom]
        com = mol_atoms.mean(axis=0)
        tiled_centers.append(com)
    
    tiled_centers = np.array(tiled_centers)
    
    tree = cKDTree(tiled_centers)
    duplicate_pairs = tree.query_pairs(0.25)
    
    print(f"\nDuplicate pairs in tiled result: {len(duplicate_pairs)}")
    
    if len(duplicate_pairs) == 0:
        print("✅ SUCCESS! No duplicates created by tiling!")
    else:
        print(f"⚠️  Found {len(duplicate_pairs)} pairs < 0.25 nm")
        
        # Check if these are from original close pairs or from tiling
        # If from tiling, we'd have much more than expected
        expected_from_original = len(close_pairs) * 27
        print(f"   Expected from original close pairs: {expected_from_original}")
        print(f"   Actual: {len(duplicate_pairs)}")
        
        if len(duplicate_pairs) <= expected_from_original * 1.1:  # Allow 10% margin
            print("   ✅ Duplicates are from original close pairs, NOT from tiling bug")
        else:
            print("   ❌ More duplicates than expected - tiling bug still present")
    
    print(f"\n{'='*70}")
    print("TEST COMPLETE")
    print(f"{'='*70}")

if __name__ == "__main__":
    test_with_proper_spacing()
