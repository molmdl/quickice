"""Detailed investigation of remaining 27 duplicates."""

import numpy as np
import sys
sys.path.insert(0, '/share/home/nglokwan/quickice')

def investigate_remaining_duplicates():
    """Investigate why there are still 27 duplicates after the fix."""
    
    print("=" * 70)
    print("INVESTIGATING REMAINING 27 DUPLICATES")
    print("=" * 70)
    
    # Simulate the tiling process manually with the fix
    cell_dims = np.array([2.46, 2.46, 1.2])
    target_region = np.array([7.451, 7.451, 3.601])
    atoms_per_molecule = 4
    
    # Create test positions: 10 molecules at KNOWN positions
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
    
    # Calculate correct tile counts with fix
    nx, ny, nz = 3, 3, 3  # From previous debug
    
    # Generate all tiles
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
    
    print(f"\nTile offsets: {len(offsets)} tiles")
    print(f"Coverage: x=[0, {nx*a:.6f}), y=[0, {ny*b:.6f}), z=[0, {nz*c:.6f})")
    print(f"Target:   x=[0, {target_region[0]:.6f}), y=[0, {target_region[1]:.6f}), z=[0, {target_region[2]:.6f})")
    
    # Apply offsets
    all_positions = (positions[np.newaxis, :, :] + offsets[:, np.newaxis, :]).reshape(-1, 3)
    n_tiled_molecules = len(all_positions) // atoms_per_molecule
    
    print(f"\nCreated {n_tiled_molecules} molecules from {n_test_molecules} original × {len(offsets)} tiles")
    
    # Track origins
    molecule_origins = []
    for tile_idx, offset in enumerate(offsets):
        ix = int(offset[0] / a)
        iy = int(offset[1] / b)
        iz = int(offset[2] / c)
        for mol_idx in range(n_test_molecules):
            molecule_origins.append((mol_idx, ix, iy, iz))
    
    # Apply wrapping (simulate tile_structure wrapping logic)
    print(f"\n{'='*70}")
    print("APPLYING WRAPPING")
    print(f"{'='*70}")
    
    wrapped_positions = all_positions.copy()
    
    wrapping_log = []
    for mol_idx in range(n_tiled_molecules):
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        mol_atoms = wrapped_positions[start_atom:end_atom]
        
        original_com = mol_atoms.mean(axis=0)
        shifts = []
        
        for dim in range(3):
            com = mol_atoms[:, dim].mean()
            shift_applied = 0.0
            
            if com < 0:
                n_boxes = int(np.ceil(-com / target_region[dim]))
                wrapped_positions[start_atom:end_atom, dim] += n_boxes * target_region[dim]
                shift_applied = n_boxes * target_region[dim]
            elif com >= target_region[dim]:
                n_boxes = int(np.floor(com / target_region[dim]))
                wrapped_positions[start_atom:end_atom, dim] -= n_boxes * target_region[dim]
                shift_applied = -n_boxes * target_region[dim]
            
            shifts.append(shift_applied)
        
        if np.any(np.array(shifts) != 0):
            wrapping_log.append({
                'mol_idx': mol_idx,
                'origin': molecule_origins[mol_idx],
                'original_com': original_com,
                'wrapped_com': wrapped_positions[start_atom:end_atom].mean(axis=0),
                'shifts': shifts
            })
    
    print(f"Molecules wrapped: {len(wrapping_log)} / {n_tiled_molecules}")
    
    # Show wrapped molecules by tile
    print(f"\nWrapped molecules by tile index:")
    from collections import defaultdict
    wrapped_by_tile = defaultdict(list)
    for entry in wrapping_log:
        tile_key = entry['origin'][1:]  # (ix, iy, iz)
        wrapped_by_tile[tile_key].append(entry)
    
    for tile_key in sorted(wrapped_by_tile.keys())[:10]:
        entries = wrapped_by_tile[tile_key]
        print(f"  Tile {tile_key}: {len(entries)} molecules wrapped")
        for entry in entries[:2]:
            print(f"    Mol {entry['origin'][0]}: COM {entry['original_com']} -> {entry['wrapped_com']}")
    
    # Check for duplicates
    print(f"\n{'='*70}")
    print("DUPLICATE DETECTION")
    print(f"{'='*70}")
    
    molecule_centers = []
    for mol_idx in range(n_tiled_molecules):
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        mol_atoms = wrapped_positions[start_atom:end_atom]
        com = mol_atoms.mean(axis=0)
        molecule_centers.append(com)
    
    molecule_centers = np.array(molecule_centers)
    
    from scipy.spatial import cKDTree
    tree = cKDTree(molecule_centers)
    duplicate_pairs = tree.query_pairs(0.25)
    
    print(f"\nFound {len(duplicate_pairs)} duplicate pairs (COM < 0.25 nm)")
    
    if duplicate_pairs:
        print(f"\nAnalyzing duplicate pairs:")
        
        # Group by type
        same_original_diff_tile = []
        diff_original_same_tile = []
        diff_original_diff_tile = []
        
        for idx1, idx2 in list(duplicate_pairs)[:20]:
            origin1 = molecule_origins[idx1]
            origin2 = molecule_origins[idx2]
            distance = np.linalg.norm(molecule_centers[idx1] - molecule_centers[idx2])
            
            same_mol = origin1[0] == origin2[0]
            same_tile = origin1[1:] == origin2[1:]
            
            if same_mol and not same_tile:
                same_original_diff_tile.append((idx1, idx2, distance, origin1, origin2))
            elif not same_mol and same_tile:
                diff_original_same_tile.append((idx1, idx2, distance, origin1, origin2))
            elif not same_mol and not same_tile:
                diff_original_diff_tile.append((idx1, idx2, distance, origin1, origin2))
        
        print(f"\n  Same original molecule, different tiles: {len(same_original_diff_tile)}")
        print(f"  Different original molecules, same tile: {len(diff_original_same_tile)}")
        print(f"  Different original molecules, different tiles: {len(diff_original_diff_tile)}")
        
        if same_original_diff_tile:
            print(f"\n  Examples of same original, different tiles:")
            for idx1, idx2, dist, o1, o2 in same_original_diff_tile[:5]:
                print(f"    Mols {idx1},{idx2}: orig mol {o1[0]}, tiles {o1[1:]} vs {o2[1:]}, dist {dist:.4f} nm")
        
        if diff_original_same_tile:
            print(f"\n  Examples of different originals, same tile:")
            for idx1, idx2, dist, o1, o2 in diff_original_same_tile[:5]:
                print(f"    Mols {idx1},{idx2}: orig mols {o1[0]},{o2[0]}, tile {o1[1:]}, dist {dist:.4f} nm")
        
        if diff_original_diff_tile:
            print(f"\n  Examples of different originals, different tiles:")
            for idx1, idx2, dist, o1, o2 in diff_original_diff_tile[:5]:
                print(f"    Mols {idx1},{idx2}: orig mols {o1[0]},{o2[0]}, tiles {o1[1:]} vs {o2[1:]}, dist {dist:.4f} nm")
    
    print(f"\n{'='*70}")
    print("INVESTIGATION COMPLETE")
    print(f"{'='*70}")

if __name__ == "__main__":
    investigate_remaining_duplicates()
