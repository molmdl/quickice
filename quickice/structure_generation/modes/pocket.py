"""Pocket mode: water cavity in ice matrix.

Creates a spherical water cavity inside an ice matrix at the box center.
Ice molecules inside the cavity are removed, water fills the cavity,
and overlapping water molecules at the boundary are removed.
"""

import numpy as np

from quickice.structure_generation.types import Candidate, InterfaceConfig, InterfaceStructure
from quickice.structure_generation.errors import InterfaceGenerationError
from quickice.structure_generation.water_filler import tile_structure, fill_region_with_water
from quickice.structure_generation.overlap_resolver import (
    detect_overlaps,
    remove_overlapping_molecules,
)


def assemble_pocket(candidate: Candidate, config: InterfaceConfig) -> InterfaceStructure:
    """Assemble pocket interface structure: water cavity in ice matrix.

    Creates a spherical cavity at the box center, removes ice molecules
    inside the cavity, fills the cavity with water, and removes overlapping
    water molecules at the ice-water boundary.

    For v3.0 MVP, only spherical cavities are supported. Ellipsoid support
    is planned for future versions.

    Args:
        candidate: Ice structure candidate from GenIce (3 atoms per molecule: O, H, H).
        config: Interface configuration with pocket_diameter and pocket_shape.

    Returns:
        InterfaceStructure with ice (outside cavity) + water (in cavity).

    Raises:
        InterfaceGenerationError: If pocket_shape is not "sphere" or if generation fails.
    """
    # Check pocket shape (v3.0 only supports sphere)
    if config.pocket_shape != "sphere":
        raise InterfaceGenerationError(
            f"Ellipsoid pockets not yet supported. pocket_shape must be 'sphere', got '{config.pocket_shape}'.",
            mode="pocket"
        )

    # Get ice cell diagonal dimensions (orthogonal boxes only for v3.0)
    ice_cell_dims = np.array([
        candidate.cell[0, 0],
        candidate.cell[1, 1],
        candidate.cell[2, 2]
    ])

    # Box dimensions
    box_dims = np.array([config.box_x, config.box_y, config.box_z])

    # Cavity center and radius
    center = box_dims / 2.0
    radius = config.pocket_diameter / 2.0

    # Tile ice to fill entire box
    ice_positions, ice_nmolecules = tile_structure(
        candidate.positions,
        ice_cell_dims,
        box_dims
    )

    if len(ice_positions) == 0:
        raise InterfaceGenerationError(
            "Ice tiling produced zero atoms. Check candidate structure and box dimensions.",
            mode="pocket"
        )

    # Remove ice molecules inside the spherical cavity
    # Ice O atoms: indices [0, 3, 6, ...] (3 atoms per molecule from GenIce)
    ice_o_positions = ice_positions[::3]

    # Calculate distances from cavity center (no PBC needed - cavity is fully inside box)
    distances = np.linalg.norm(ice_o_positions - center, axis=1)

    # Molecules inside cavity: remove these
    ice_inside_cavity = set(np.where(distances < radius)[0])

    # Remove ice molecules inside cavity
    if ice_inside_cavity:
        ice_positions, ice_nmolecules = remove_overlapping_molecules(
            ice_positions,
            ice_inside_cavity,
            atoms_per_molecule=3  # GenIce: O, H, H
        )

    # Build ice atom names
    ice_atom_names = ["O", "H", "H"] * ice_nmolecules

    # Fill entire box with water
    water_positions, water_atom_names, water_nmolecules = fill_region_with_water(
        box_dims,
        config.overlap_threshold
    )

    if len(water_positions) == 0:
        raise InterfaceGenerationError(
            "Water filling produced zero molecules. Check box dimensions.",
            mode="pocket"
        )

    # Remove water molecules OUTSIDE the cavity (keep only water IN cavity)
    # Water O atoms: indices [0, 4, 8, ...] (4 atoms per molecule from TIP4P)
    water_o_positions = water_positions[::4]

    # Calculate distances from cavity center
    water_distances = np.linalg.norm(water_o_positions - center, axis=1)

    # Molecules outside cavity: remove these (keep water_distances < radius)
    water_outside = set(np.where(water_distances >= radius)[0])

    # Remove water molecules outside cavity
    if water_outside:
        water_positions, water_nmolecules = remove_overlapping_molecules(
            water_positions,
            water_outside,
            atoms_per_molecule=4  # TIP4P: OW, HW1, HW2, MW
        )
        # Trim atom names
        water_atom_names = water_atom_names[:water_nmolecules * 4]

    # Detect overlaps between remaining ice and cavity water
    if len(ice_positions) > 0 and len(water_positions) > 0:
        ice_o_positions = ice_positions[::3]
        water_o_positions = water_positions[::4]

        overlapping_mol_indices = detect_overlaps(
            ice_o_positions,
            water_o_positions,
            box_dims,
            config.overlap_threshold
        )
    else:
        overlapping_mol_indices = set()

    # Remove overlapping water molecules from cavity water (not ice)
    if overlapping_mol_indices:
        water_positions, water_nmolecules = remove_overlapping_molecules(
            water_positions,
            overlapping_mol_indices,
            atoms_per_molecule=4
        )
        water_atom_names = water_atom_names[:water_nmolecules * 4]

    # Combine: ice (outside cavity) FIRST, then water (in cavity)
    if len(ice_positions) > 0 and len(water_positions) > 0:
        all_positions = np.vstack([ice_positions, water_positions])
    elif len(ice_positions) > 0:
        all_positions = ice_positions
    elif len(water_positions) > 0:
        all_positions = water_positions
    else:
        all_positions = np.zeros((0, 3), dtype=float)

    # Combine atom names
    all_atom_names = ice_atom_names + water_atom_names

    # Compute counts
    ice_atom_count = len(ice_positions)
    water_atom_count = len(water_positions)

    # Build cell matrix
    cell = np.diag([config.box_x, config.box_y, config.box_z])

    # Build report (gmx solvate convention)
    total_molecules = ice_nmolecules + water_nmolecules
    report = (
        f"Generated pocket interface structure\n"
        f"  Ice molecules: {ice_nmolecules}\n"
        f"  Water molecules: {water_nmolecules}\n"
        f"  Total molecules: {total_molecules}\n"
        f"  Cavity diameter: {config.pocket_diameter:.2f} nm\n"
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
        mode="pocket",
        report=report
    )
