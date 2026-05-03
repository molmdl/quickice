"""Diagnostic script to find WHY duplicates are created in tile_structure.

This script traces through the tiling process to identify the root cause
of duplicate molecule creation.
"""

import numpy as np
from scipy.spatial import cKDTree

def diagnose_tile_duplicates():
    """Trace tile creation to find duplicate source."""
    
    # Simulate the hydrate case from previous debug
    # 46 water molecules, cell_dims = [2.46, 2.46, 1.2] nm (approximate)
    # target_region = [7.451, 7.451, 3.601] nm
    
    # Create a simple test case
    cell_dims = np.array([2.46, 2.46, 1.2])
    target_region = np.array([7.451, 7.451, 3.601])
    atoms_per_molecule = 4
    
    # Create test positions: 10 molecules at various positions
    np.random.seed(42)
    n_test_molecules = 10
    test_positions = []
    for i in range(n_test_molecules):
        # Place molecules at different positions in the unit cell
        base_pos = np.random.rand(3) * cell_dims
        # Create 4 atoms for each molecule (TIP4P: OW, HW1, HW2, MW)
        for j in range(4):
            # Small offset for each atom in molecule
            offset = np.array([0.0, 0.0, 0.0]) if j == 0 else \
                     np.array([0.1, 0.0, 0.0]) if j == 1 else \
                     np.array([-0.1, 0.0, 0.0]) if j == 2 else \
                     np.array([0.0, 0.0, 0.01])
            test_positions.append(base_pos + offset)
    
    positions = np.array(test_positions)
    
    print("=" * 70)
    print("DIAGNOSTIC: Why are duplicates created in tile_structure?")
    print("=" * 70)
    print(f"\nInput: {n_test_molecules} molecules ({len(positions)} atoms)")
    print(f"Cell dimensions: {cell_dims}")
    print(f"Target region: {target_region}")
    
    # Calculate tile counts
    lx, ly, lz = target_region
    a, b, c = cell_dims
    
    def calc_tile_count(target_dim, cell_dim, tolerance=0.05):
        if cell_dim <= 0:
            return 1
        ratio = target_dim / cell_dim
        if ratio <= 1.0 + tolerance:
            return 1
        else:
            return int(np.ceil(ratio))
    
    nx = calc_tile_count(lx, a)
    ny = calc_tile_count(ly, b)
    nz = calc_tile_count(lz, c)
    
    print(f"\nTile counts: nx={nx}, ny={ny}, nz={nz} (total {nx*ny*nz} tiles)")
    print(f"  X: {lx:.3f} / {a:.3f} = {lx/a:.3f} -> {nx} tiles")
    print(f"  Y: {ly:.3f} / {b:.3f} = {ly/b:.3f} -> {ny} tiles")
    print(f"  Z: {lz:.3f} / {c:.3f} = {lz/c:.3f} -> {nz} tiles")
    
    # Generate tile indices
    ix_vals = np.arange(nx)
    iy_vals = np.arange(ny)
    iz_vals = np.arange(nz)
    
    # Create meshgrid
    ix_grid, iy_grid, iz_grid = np.meshgrid(ix_vals, iy_vals, iz_vals, indexing='ij')
    
    # Compute offsets (orthogonal case)
    offsets = np.stack([
        ix_grid.ravel() * a,
        iy_grid.ravel() * b,
        iz_grid.ravel() * c
    ], axis=1)
    
    print(f"\nGenerated {len(offsets)} tile offsets")
    print(f"First few offsets:\n{offsets[:5]}")
    print(f"Last few offsets:\n{offsets[-5:]}")
    
    # Apply offsets to create tiled positions
    all_positions = (positions[np.newaxis, :, :] + offsets[:, np.newaxis, :]).reshape(-1, 3)
    n_tiled_molecules = len(all_positions) // atoms_per_molecule
    
    print(f"\nTiled structure: {n_tiled_molecules} molecules ({len(all_positions)} atoms)")
    
    # Track which original molecule each tile molecule came from
    molecule_origins = []  # (original_mol_idx, tile_ix, tile_iy, tile_iz)
    for tile_idx, offset in enumerate(offsets):
        ix = int(offset[0] / a)
        iy = int(offset[1] / b)
        iz = int(offset[2] / c)
        for mol_idx in range(n_test_molecules):
            molecule_origins.append((mol_idx, ix, iy, iz))
    
    print(f"\nMolecule origins tracked: {len(molecule_origins)}")
    
    # CRITICAL: Simulate the wrapping process
    print("\n" + "=" * 70)
    print("WRAPPING PROCESS")
    print("=" * 70)
    
    wrapped_positions = all_positions.copy()
    
    # Track wrapping for each molecule
    wrapping_log = []
    
    for mol_idx in range(n_tiled_molecules):
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        mol_atoms = wrapped_positions[start_atom:end_atom]
        
        # Store original position
        original_com = mol_atoms.mean(axis=0)
        
        # Wrap each dimension
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
        
        # Store wrapping info
        wrapped_com = wrapped_positions[start_atom:end_atom].mean(axis=0)
        origin = molecule_origins[mol_idx]
        
        if np.any(np.array(shifts) != 0):
            wrapping_log.append({
                'mol_idx': mol_idx,
                'origin': origin,
                'original_com': original_com,
                'wrapped_com': wrapped_com,
                'shifts': shifts
            })
    
    print(f"\nMolecules that were wrapped: {len(wrapping_log)} / {n_tiled_molecules}")
    
    # Show some wrapping examples
    if wrapping_log:
        print("\nFirst 10 wrapped molecules:")
        for entry in wrapping_log[:10]:
            print(f"  Mol {entry['mol_idx']:4d} from tile {entry['origin'][1:]}: "
                  f"COM {entry['original_com']} -> {entry['wrapped_com']}, "
                  f"shift {entry['shifts']}")
    
    # CRITICAL: Check for duplicates after wrapping
    print("\n" + "=" * 70)
    print("DUPLICATE DETECTION")
    print("=" * 70)
    
    # Calculate COM for all molecules
    molecule_centers = []
    for mol_idx in range(n_tiled_molecules):
        start_atom = mol_idx * atoms_per_molecule
        end_atom = start_atom + atoms_per_molecule
        mol_atoms = wrapped_positions[start_atom:end_atom]
        com = mol_atoms.mean(axis=0)
        molecule_centers.append(com)
    
    molecule_centers = np.array(molecule_centers)
    
    # Find duplicates
    tree = cKDTree(molecule_centers)
    duplicate_pairs = tree.query_pairs(0.25)
    
    print(f"\nFound {len(duplicate_pairs)} duplicate pairs (COM < 0.25 nm)")
    
    if duplicate_pairs:
        print("\nAnalyzing duplicate pairs:")
        for idx, (i, j) in enumerate(list(duplicate_pairs)[:10]):
            origin_i = molecule_origins[i]
            origin_j = molecule_origins[j]
            distance = np.linalg.norm(molecule_centers[i] - molecule_centers[j])
            
            print(f"\n  Pair {idx+1}: Molecules {i} and {j}")
            print(f"    Distance: {distance:.4f} nm")
            print(f"    Molecule {i}: original mol {origin_i[0]}, tile ({origin_i[1]}, {origin_i[2]}, {origin_i[3]})")
            print(f"    Molecule {j}: original mol {origin_j[0]}, tile ({origin_j[1]}, {origin_j[2]}, {origin_j[3]})")
            print(f"    COM {i}: {molecule_centers[i]}")
            print(f"    COM {j}: {molecule_centers[j]}")
            
            # Check if this is the same original molecule
            if origin_i[0] == origin_j[0]:
                print(f"    ⚠️  SAME ORIGINAL MOLECULE! Different tiles wrapped to same position!")
    
    # Analyze root cause
    print("\n" + "=" * 70)
    print("ROOT CAUSE ANALYSIS")
    print("=" * 70)
    
    # Check for tiles that wrap into the same region
    print("\nChecking tile overlap patterns:")
    
    # Group molecules by their tile index
    from collections import defaultdict
    tile_groups = defaultdict(list)
    
    for mol_idx in range(n_tiled_molecules):
        origin = molecule_origins[mol_idx]
        tile_key = (origin[1], origin[2], origin[3])  # (ix, iy, iz)
        tile_groups[tile_key].append(mol_idx)
    
    print(f"\nTotal tiles: {len(tile_groups)}")
    
    # Check if tiles cover overlapping regions
    tile_regions = []
    for tile_key, mol_indices in tile_groups.items():
        # Get the bounding box of molecules in this tile
        tile_positions = []
        for mol_idx in mol_indices:
            start_atom = mol_idx * atoms_per_molecule
            end_atom = start_atom + atoms_per_molecule
            tile_positions.extend(wrapped_positions[start_atom:end_atom])
        
        tile_positions = np.array(tile_positions)
        min_pos = tile_positions.min(axis=0)
        max_pos = tile_positions.max(axis=0)
        
        tile_regions.append({
            'tile_key': tile_key,
            'min': min_pos,
            'max': max_pos,
            'molecules': mol_indices
        })
    
    # Check for overlapping tiles (after wrapping)
    print("\nChecking for overlapping tiles after wrapping:")
    overlapping_tiles = []
    
    for i, region_i in enumerate(tile_regions):
        for j, region_j in enumerate(tile_regions):
            if i >= j:
                continue
            
            # Check if regions overlap
            overlap_x = region_i['min'][0] < region_j['max'][0] and region_i['max'][0] > region_j['min'][0]
            overlap_y = region_i['min'][1] < region_j['max'][1] and region_i['max'][1] > region_j['min'][1]
            overlap_z = region_i['min'][2] < region_j['max'][2] and region_i['max'][2] > region_j['min'][2]
            
            if overlap_x and overlap_y and overlap_z:
                overlapping_tiles.append((region_i['tile_key'], region_j['tile_key']))
    
    if overlapping_tiles:
        print(f"\n⚠️  Found {len(overlapping_tiles)} overlapping tile pairs!")
        print("First 10 overlapping pairs:")
        for i, (tile1, tile2) in enumerate(overlapping_tiles[:10]):
            print(f"  {i+1}. Tile {tile1} overlaps with tile {tile2}")
    else:
        print("\n✓ No overlapping tiles found")
    
    # Check for molecules wrapping across boundaries
    print("\n\nAnalyzing molecules that wrap across boundaries:")
    boundary_wrapping = [w for w in wrapping_log if any(abs(s) > 0 for s in w['shifts'])]
    print(f"Molecules that crossed boundaries during wrapping: {len(boundary_wrapping)}")
    
    if boundary_wrapping:
        print("\nFirst 5 boundary-crossing molecules:")
        for entry in boundary_wrapping[:5]:
            print(f"  Mol {entry['mol_idx']:4d}: tile {entry['origin'][1:]}")
            print(f"    Original COM: {entry['original_com']}")
            print(f"    Wrapped COM:  {entry['wrapped_com']}")
            print(f"    Shift: {entry['shifts']}")
    
    print("\n" + "=" * 70)
    print("DIAGNOSIS COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    diagnose_tile_duplicates()
