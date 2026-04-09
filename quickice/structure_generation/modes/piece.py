"""Piece mode: ice crystal embedded in water box.

Centers an ice crystal inside a water box. The ice piece dimensions
are derived from the candidate cell, and overlapping water molecules
are removed.
"""

import numpy as np

from quickice.structure_generation.types import Candidate, InterfaceConfig, InterfaceStructure
from quickice.structure_generation.errors import InterfaceGenerationError
from quickice.structure_generation.water_filler import tile_structure, fill_region_with_water
from quickice.structure_generation.overlap_resolver import (
    detect_overlaps,
    remove_overlapping_molecules,
)

# Ice atom names template (GenIce: 3 atoms per molecule)
# Memory note: Creates O(n) list for n molecules (~240KB for 10k molecules).
# Acceptable for typical use. For very large systems (>10k), this is modest overhead.
ICE_ATOM_NAMES_TEMPLATE = ["O", "H", "H"]


def assemble_piece(candidate: Candidate, config: InterfaceConfig) -> InterfaceStructure:
    """Assemble piece interface structure: ice centered in water box.

    The ice piece is centered in the water box. Overlapping water molecules
    are removed. The ice piece dimensions are derived from the candidate cell.

    For v3.0, only orthogonal boxes are supported (cube/rectangular prism).

    Args:
        candidate: Ice structure candidate from GenIce (3 atoms per molecule: O, H, H).
        config: Interface configuration with box dimensions.

    Returns:
        InterfaceStructure with ice (centered) + water positions.

    Raises:
        InterfaceGenerationError: If box is smaller than ice piece or generation fails.
    """
    # Get ice piece dimensions from candidate cell diagonal
    ice_dims = np.array([
        candidate.cell[0, 0],
        candidate.cell[1, 1],
        candidate.cell[2, 2]
    ])

    # Validate: box dimensions must be larger than ice piece
    if config.box_x <= ice_dims[0]:
        raise InterfaceGenerationError(
            f"Box X dimension ({config.box_x:.2f} nm) must be larger than ice piece X ({ice_dims[0]:.2f} nm).",
            mode="piece"
        )
    if config.box_y <= ice_dims[1]:
        raise InterfaceGenerationError(
            f"Box Y dimension ({config.box_y:.2f} nm) must be larger than ice piece Y ({ice_dims[1]:.2f} nm).",
            mode="piece"
        )
    if config.box_z <= ice_dims[2]:
        raise InterfaceGenerationError(
            f"Box Z dimension ({config.box_z:.2f} nm) must be larger than ice piece Z ({ice_dims[2]:.2f} nm).",
            mode="piece"
        )

    # Box dimensions
    box_dims = np.array([config.box_x, config.box_y, config.box_z])

    # Tile ice to fill piece region (essentially just the candidate itself)
    tiled_ice_positions, ice_nmolecules = tile_structure(
        candidate.positions,
        ice_dims,
        ice_dims,
        atoms_per_molecule=3  # GenIce ice: O, H, H
    )

    if len(tiled_ice_positions) == 0:
        raise InterfaceGenerationError(
            "Ice tiling produced zero atoms. Check candidate structure.",
            mode="piece"
        )

    # Center the ice piece in the box
    offset = box_dims / 2.0 - ice_dims / 2.0
    centered_ice_positions = tiled_ice_positions + offset

    # Build ice atom names (3 atoms per molecule: O, H, H from GenIce)
    # Uses module-level template for consistency
    ice_atom_names = ICE_ATOM_NAMES_TEMPLATE * ice_nmolecules

    # Fill entire box with water
    water_positions, water_atom_names, water_nmolecules = fill_region_with_water(
        box_dims
    )

    # Detect overlaps between centered ice O and water O
    # Ice O atoms: indices [0, 3, 6, ...] (3 atoms per molecule)
    # Water O atoms: indices [0, 4, 8, ...] (4 atoms per molecule)
    if len(centered_ice_positions) > 0 and len(water_positions) > 0:
        ice_o_positions = centered_ice_positions[::3]
        water_o_positions = water_positions[::4]

        overlapping_mol_indices = detect_overlaps(
            ice_o_positions,
            water_o_positions,
            box_dims,
            config.overlap_threshold
        )
    else:
        overlapping_mol_indices = set()

    # Remove overlapping water molecules
    if overlapping_mol_indices:
        water_positions, water_nmolecules = remove_overlapping_molecules(
            water_positions,
            overlapping_mol_indices,
            atoms_per_molecule=4  # TIP4P: OW, HW1, HW2, MW
        )
        water_atom_names = water_atom_names[:water_nmolecules * 4]

    # Combine: ice (centered) FIRST, then water
    if len(centered_ice_positions) > 0 and len(water_positions) > 0:
        all_positions = np.vstack([centered_ice_positions, water_positions])
    elif len(centered_ice_positions) > 0:
        all_positions = centered_ice_positions
    elif len(water_positions) > 0:
        all_positions = water_positions
    else:
        all_positions = np.zeros((0, 3), dtype=float)

    # Combine atom names
    all_atom_names = ice_atom_names + water_atom_names

    # Compute counts
    ice_atom_count = len(centered_ice_positions)
    water_atom_count = len(water_positions)

    # Build cell matrix
    cell = np.diag([config.box_x, config.box_y, config.box_z])

    # Build report (gmx solvate convention)
    total_molecules = ice_nmolecules + water_nmolecules
    report = (
        f"Generated piece interface structure\n"
        f"  Ice molecules: {ice_nmolecules}\n"
        f"  Water molecules: {water_nmolecules}\n"
        f"  Total molecules: {total_molecules}\n"
        f"  Ice piece: {ice_dims[0]:.2f} x {ice_dims[1]:.2f} x {ice_dims[2]:.2f} nm\n"
        f"  Box: {config.box_x:.2f} x {config.box_y:.2f} x {config.box_z:.2f} nm"
    )

    return InterfaceStructure(
        positions=all_positions,
        atom_names=all_atom_names,
        cell=cell,
        ice_atom_count=ice_atom_count,
        water_atom_count=water_atom_count,
        ice_nmolecules=ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="piece",
        report=report
    )
