#!/usr/bin/env python3
"""Detailed analysis of ice molecule positions before and after tiling.

This script traces the tiling process to understand how gaps are
inherited from the candidate and whether wrapping fixes them.
"""

import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from quickice.structure_generation.gro_parser import parse_gro_file
from quickice.structure_generation.water_filler import tile_structure, get_cell_extent


def analyze_tiling(gro_path: Path, target_z: float):
    """Analyze what happens during tiling of a hydrate candidate."""
    print(f"\n{'=' * 70}")
    print(f"Analyzing tiling for: {gro_path.name}")
    print(f"Target Z dimension: {target_z:.3f} nm")
    print(f"{'=' * 70}")
    
    positions, atom_names, cell = parse_gro_file(gro_path)
    
    # Get cell dimensions
    cell_dims = get_cell_extent(cell)
    print(f"\nOriginal candidate:")
    print(f"  Cell dimensions: {cell_dims}")
    
    # Find OW atoms
    ow_mask = np.array(atom_names) == "OW"
    ow_positions = positions[ow_mask]
    
    print(f"  OW atoms: {len(ow_positions)}")
    print(f"  OW Z range: {ow_positions[:, 2].min():.3f} to {ow_positions[:, 2].max():.3f} nm")
    
    # Simulate tiling with filter_molecules=True (OLD behavior)
    print(f"\nTiling with filter_molecules=True (OLD):")
    tiled_true, n_mol_true = tile_structure(
        positions,
        cell_dims,
        np.array([cell_dims[0], cell_dims[1], target_z]),
        atoms_per_molecule=4,
        cell_matrix=cell,
        filter_molecules=True
    )
    
    # Find OW atoms in tiled result
    ow_mask_true = np.array(atom_names * (len(tiled_true) // len(positions))) == "OW"
    if len(ow_mask_true) < len(tiled_true):
        # Adjust mask if tiling changed the count
        ow_mask_true = np.array(atom_names * (len(tiled_true) // len(atom_names)) + 
                                atom_names[:len(tiled_true) % len(atom_names)]) == "OW"
    
    ow_tiled_true = tiled_true[ow_mask_true]
    print(f"  Tiled OW atoms: {len(ow_tiled_true)}")
    print(f"  OW Z range: {ow_tiled_true[:, 2].min():.3f} to {ow_tiled_true[:, 2].max():.3f} nm")
    print(f"  Gap at Z=0: {ow_tiled_true[:, 2].min():.3f} nm")
    print(f"  Gap at Z=target: {target_z - ow_tiled_true[:, 2].max():.3f} nm")
    
    # Simulate tiling with filter_molecules=False (NEW behavior)
    print(f"\nTiling with filter_molecules=False (NEW):")
    tiled_false, n_mol_false = tile_structure(
        positions,
        cell_dims,
        np.array([cell_dims[0], cell_dims[1], target_z]),
        atoms_per_molecule=4,
        cell_matrix=cell,
        filter_molecules=False
    )
    
    # Find OW atoms in tiled result
    ow_mask_false = np.array(atom_names * (len(tiled_false) // len(atom_names))) == "OW"
    ow_tiled_false = tiled_false[ow_mask_false]
    print(f"  Tiled OW atoms: {len(ow_tiled_false)}")
    print(f"  OW Z range: {ow_tiled_false[:, 2].min():.3f} to {ow_tiled_false[:, 2].max():.3f} nm")
    print(f"  Gap at Z=0: {ow_tiled_false[:, 2].min():.3f} nm")
    print(f"  Gap at Z=target: {target_z - ow_tiled_false[:, 2].max():.3f} nm")
    
    # Compare
    print(f"\nComparison:")
    print(f"  filter_molecules=True: {len(ow_tiled_true)} OW atoms")
    print(f"  filter_molecules=False: {len(ow_tiled_false)} OW atoms")
    print(f"  Difference: {len(ow_tiled_false) - len(ow_tiled_true)} more OW atoms with filter=False")


def main():
    """Analyze tiling for both hydrates."""
    # Test with a larger target to see the tiling effect
    target_z = 3.0  # nm
    
    # CH4 hydrate
    ch4_hydrate = Path("tmp/ch4/hydrate_sI_ch4_1x1x1.gro")
    if ch4_hydrate.exists():
        analyze_tiling(ch4_hydrate, target_z)
    
    # THF hydrate
    thf_hydrate = Path("tmp/thf/hydrate_sII_thf_1x1x1.gro")
    if thf_hydrate.exists():
        analyze_tiling(thf_hydrate, target_z)
    
    print(f"\n{'=' * 70}")


if __name__ == "__main__":
    main()
