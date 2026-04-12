"""Pocket mode: water cavity in ice matrix.

Creates a water-filled cavity inside an ice matrix at the box center.
Supports two cavity shapes: sphere and cubic.
Ice molecules inside the cavity are removed, water fills the cavity,
and overlapping water molecules at the boundary are removed.
"""

import numpy as np

# Ice atom names template (GenIce: 3 atoms per molecule)
# Memory note: Creates O(n) list for n molecules (~240KB for 10k molecules).
# Acceptable for typical use. For very large systems (>10k), this is modest overhead.
ICE_ATOM_NAMES_TEMPLATE = ["O", "H", "H"]

from quickice.structure_generation.types import Candidate, InterfaceConfig, InterfaceStructure
from quickice.structure_generation.errors import InterfaceGenerationError
from quickice.structure_generation.water_filler import tile_structure, fill_region_with_water, round_to_periodicity
from quickice.structure_generation.overlap_resolver import (
    detect_overlaps,
    remove_overlapping_molecules,
    filter_atom_names,
)
from quickice.phase_mapping.water_density import water_density_gcm3
from quickice.structure_generation.transformer import TriclinicTransformer


def assemble_pocket(candidate: Candidate, config: InterfaceConfig) -> InterfaceStructure:
    """Assemble pocket interface structure: water cavity in ice matrix.

    Creates a cavity at the box center, removes ice molecules
    inside the cavity, fills the cavity with water, and removes overlapping
    water molecules at the ice-water boundary.

    Supports two cavity shapes:
    - sphere: spherical void with diameter = pocket_diameter
    - cubic: cube with side = pocket_diameter

    IMPORTANT: Box dimensions are adjusted to ensure continuous periodic images.
    The adjustments are reported in the InterfaceStructure.report field.

    Args:
        candidate: Ice structure candidate from GenIce (3 atoms per molecule: O, H, H).
        config: Interface configuration with pocket_diameter and pocket_shape.

    Returns:
        InterfaceStructure with ice (outside cavity) + water (in cavity).

    Raises:
        InterfaceGenerationError: If pocket_shape is not valid or if generation fails.
    """
    # Get ice cell dimensions using bounding box calculation
    # This works for both orthogonal and transformed cells
    transformer = TriclinicTransformer()
    ice_cell_dims = transformer.get_cell_extent(candidate.cell)

    # ADJUST DIMENSIONS FOR PERIODICITY
    # Round box dimensions to multiples of ice unit cell
    # This ensures continuous periodic images without gaps at boundaries
    adjusted_box_x, nx = round_to_periodicity(config.box_x, ice_cell_dims[0])
    adjusted_box_y, ny = round_to_periodicity(config.box_y, ice_cell_dims[1])
    adjusted_box_z, nz = round_to_periodicity(config.box_z, ice_cell_dims[2])

    # Track adjustments for reporting
    adjustments = []
    if abs(adjusted_box_x - config.box_x) > 0.001:
        adjustments.append(f"  box_x: {config.box_x:.3f} → {adjusted_box_x:.3f} nm ({nx} cells)")
    if abs(adjusted_box_y - config.box_y) > 0.001:
        adjustments.append(f"  box_y: {config.box_y:.3f} → {adjusted_box_y:.3f} nm ({ny} cells)")
    if abs(adjusted_box_z - config.box_z) > 0.001:
        adjustments.append(f"  box_z: {config.box_z:.3f} → {adjusted_box_z:.3f} nm ({nz} cells)")

    # Box dimensions (using adjusted values)
    box_dims = np.array([adjusted_box_x, adjusted_box_y, adjusted_box_z])

    # Cavity center and radius
    center = box_dims / 2.0
    radius = config.pocket_diameter / 2.0

    # Tile ice to fill entire box (using adjusted dimensions)
    ice_positions, ice_nmolecules = tile_structure(
        candidate.positions,
        ice_cell_dims,
        box_dims,
        atoms_per_molecule=3  # GenIce ice: O, H, H
    )

    if len(ice_positions) == 0:
        raise InterfaceGenerationError(
            "Ice tiling produced zero atoms. Check candidate structure and box dimensions.",
            mode="pocket"
        )

    # Build ice atom names BEFORE removing molecules (CRITICAL for correct filtering)
    # Ice has 3 atoms per molecule: O, H, H from GenIce
    ice_atom_names = ICE_ATOM_NAMES_TEMPLATE * ice_nmolecules

    # Remove ice molecules inside the cavity (shape-dependent)
    # Ice O atoms: indices [0, 3, 6, ...] (3 atoms per molecule from GenIce)
    ice_o_positions = ice_positions[::3]
    
    # Calculate which ice molecules are inside the cavity based on shape
    if config.pocket_shape == "sphere":
        # Spherical cavity: distance from center < radius
        distances = np.linalg.norm(ice_o_positions - center, axis=1)
        ice_inside_cavity = set(np.where(distances < radius)[0])

    elif config.pocket_shape == "cubic":
        # Cubic cavity: |x - cx| < radius, |y - cy| < radius, |z - cz| < radius
        dx = np.abs(ice_o_positions[:, 0] - center[0])
        dy = np.abs(ice_o_positions[:, 1] - center[1])
        dz = np.abs(ice_o_positions[:, 2] - center[2])
        ice_inside_cavity = set(np.where((dx < radius) & (dy < radius) & (dz < radius))[0])

    else:
        raise InterfaceGenerationError(
            f"Unknown pocket shape: '{config.pocket_shape}'. "
            f"Valid shapes: sphere, cubic.",
            mode="pocket"
        )

    # Remove ice molecules inside cavity
    if ice_inside_cavity:
        ice_positions, ice_nmolecules = remove_overlapping_molecules(
            ice_positions,
            ice_inside_cavity,
            atoms_per_molecule=3  # GenIce: O, H, H
        )
        # Filter ice atom names to match positions (CRITICAL: must use same ice_inside_cavity)
        ice_atom_names = filter_atom_names(
            ice_atom_names,
            ice_inside_cavity,
            atoms_per_molecule=3
        )

    # OPTIMIZATION: Fill only the bounding box of the cavity instead of entire box
    # For a sphere of radius r centered at (cx, cy, cz):
    #   - Bounding box: [cx-r, cx+r] x [cy-r, cy+r] x [cz-r, cz+r]
    #   - Dimensions: 2r x 2r x 2r
    # This reduces water generation from box volume to (2r)^3,
    # which is much smaller for large boxes with small pockets.
    # Example: 10nm box with 2nm radius pocket -> 1000nm³ reduced to 64nm³ (94% reduction)
    fill_dims = np.array([2 * radius, 2 * radius, 2 * radius])

    # Calculate water density from ice temperature/pressure
    T = candidate.metadata.get('temperature', 273.15)
    P = candidate.metadata.get('pressure', 0.101325)
    target_water_density = water_density_gcm3(T, P)

    # Fill the bounding box with water (positions start at origin [0, 0, 0])
    water_positions, water_atom_names, water_nmolecules = fill_region_with_water(
        fill_dims,
        target_density=target_water_density
    )

    if len(water_positions) == 0:
        raise InterfaceGenerationError(
            "Water filling produced zero molecules. Check pocket dimensions.",
            mode="pocket"
        )

    # Translate water positions from [0, 2r] to [center-r, center+r]
    # This places the water molecules around the cavity center
    fill_origin = center - radius
    water_positions = water_positions + fill_origin

    # Remove water molecules OUTSIDE the cavity (keep only water IN cavity)
    # Water O atoms: indices [0, 4, 8, ...] (4 atoms per molecule from TIP4P)
    water_o_positions = water_positions[::4]
    
    # Calculate which water molecules are OUTSIDE the cavity based on shape
    if config.pocket_shape == "sphere":
        # Spherical cavity: distance from center >= radius -> outside
        water_distances = np.linalg.norm(water_o_positions - center, axis=1)
        water_outside = set(np.where(water_distances >= radius)[0])

    elif config.pocket_shape == "cubic":
        # Cubic cavity: outside if any coordinate exceeds half-size
        dx = np.abs(water_o_positions[:, 0] - center[0])
        dy = np.abs(water_o_positions[:, 1] - center[1])
        dz = np.abs(water_o_positions[:, 2] - center[2])
        water_outside = set(np.where((dx >= radius) | (dy >= radius) | (dz >= radius))[0])

    else:
        raise InterfaceGenerationError(
            f"Unknown pocket shape: '{config.pocket_shape}'.",
            mode="pocket"
        )

    # Remove water molecules outside cavity
    if water_outside:
        water_positions, water_nmolecules = remove_overlapping_molecules(
            water_positions,
            water_outside,
            atoms_per_molecule=4  # TIP4P: OW, HW1, HW2, MW
        )
        # Filter atom names to match positions (CRITICAL: must use same water_outside)
        water_atom_names = filter_atom_names(
            water_atom_names,
            water_outside,
            atoms_per_molecule=4
        )

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
        # Filter atom names to match positions (CRITICAL: must use same overlapping_mol_indices)
        water_atom_names = filter_atom_names(
            water_atom_names,
            overlapping_mol_indices,
            atoms_per_molecule=4
        )

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

    # Build cell matrix (using adjusted dimensions)
    cell = np.diag([adjusted_box_x, adjusted_box_y, adjusted_box_z])

    # Build report (gmx solvate convention)
    total_molecules = ice_nmolecules + water_nmolecules
    
    # Include periodicity adjustments in report
    adjustment_report = ""
    if adjustments:
        adjustment_report = (
            f"\n\nPeriodicity adjustments (for continuous images):\n" +
            "\n".join(adjustments)
        )
    
    report = (
        f"Generated pocket interface structure\n"
        f"  Ice molecules: {ice_nmolecules}\n"
        f"  Water molecules: {water_nmolecules}\n"
        f"  Total molecules: {total_molecules}\n"
        f"  Cavity diameter: {config.pocket_diameter:.2f} nm\n"
        f"  Box: {adjusted_box_x:.2f} x {adjusted_box_y:.2f} x {adjusted_box_z:.2f} nm"
        f"{adjustment_report}"
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
