"""Slab mode: ice-water-ice sandwich along Z-axis.

Creates a three-layer structure:
- Bottom ice: Z = [0, ice_thickness]
- Water: Z = [ice_thickness, ice_thickness + water_thickness]
- Top ice: Z = [ice_thickness + water_thickness, box_z]
"""

import numpy as np

# Ice atom names template (GenIce: 3 atoms per molecule)
# Memory note: Creates O(n) list for n molecules (~240KB for 10k molecules).
# Acceptable for typical use. For very large systems (>10k), this is modest overhead.
ICE_ATOM_NAMES_TEMPLATE = ["O", "H", "H"]

from quickice.structure_generation.types import Candidate, InterfaceConfig, InterfaceStructure
from quickice.structure_generation.water_filler import tile_structure, fill_region_with_water, round_to_periodicity
from quickice.structure_generation.overlap_resolver import (
    detect_overlaps,
    remove_overlapping_molecules,
    filter_atom_names,
)
from quickice.phase_mapping.water_density import water_density_gcm3


def assemble_slab(candidate: Candidate, config: InterfaceConfig) -> InterfaceStructure:
    """Assemble ice-water-ice slab interface structure.

    The ice-water-ice sandwich is stacked along the Z-axis. Ice layers are
    tiled from the candidate ice structure, water fills the middle region,
    and overlapping water molecules are removed.

    IMPORTANT: Box dimensions and ice thickness are adjusted to ensure
    continuous periodic images. The adjustments are reported in the
    InterfaceStructure.report field.

    Args:
        candidate: Ice structure candidate from GenIce (3 atoms per molecule: O, H, H).
        config: Interface configuration with mode, box dimensions, thicknesses, etc.

    Returns:
        InterfaceStructure with combined ice + water positions.
        Ice atoms come FIRST, then water atoms.

    Raises:
        InterfaceGenerationError: If generation fails or triclinic cell detected.
    """
    from quickice.structure_generation.errors import InterfaceGenerationError

    # Get ice cell dimensions for tiling
    # For orthogonal cells, use diagonal directly
    # For triclinic cells, use bounding box extent
    cell = candidate.cell
    corners = np.array([
        [0, 0, 0], cell[0], cell[1], cell[2],
        cell[0] + cell[1], cell[0] + cell[2],
        cell[1] + cell[2], cell[0] + cell[1] + cell[2]
    ])
    ice_cell_dims = corners.max(axis=0) - corners.min(axis=0)

    # ADJUST DIMENSIONS FOR PERIODICITY
    # Round box dimensions and ice thickness to multiples of ice unit cell
    # This ensures continuous periodic images without gaps at boundaries
    adjusted_box_x, nx = round_to_periodicity(config.box_x, ice_cell_dims[0])
    adjusted_box_y, ny = round_to_periodicity(config.box_y, ice_cell_dims[1])
    adjusted_ice_thickness, nz_ice = round_to_periodicity(config.ice_thickness, ice_cell_dims[2])

    # Track adjustments for reporting
    adjustments = []
    if abs(adjusted_box_x - config.box_x) > 0.001:
        adjustments.append(f"  box_x: {config.box_x:.3f} → {adjusted_box_x:.3f} nm ({nx} cells)")
    if abs(adjusted_box_y - config.box_y) > 0.001:
        adjustments.append(f"  box_y: {config.box_y:.3f} → {adjusted_box_y:.3f} nm ({ny} cells)")
    if abs(adjusted_ice_thickness - config.ice_thickness) > 0.001:
        adjustments.append(f"  ice_thickness: {config.ice_thickness:.3f} → {adjusted_ice_thickness:.3f} nm ({nz_ice} cells)")

    # Recalculate box_z to match adjusted ice thickness
    # box_z = 2 * ice_thickness + water_thickness
    adjusted_box_z = 2 * adjusted_ice_thickness + config.water_thickness
    if abs(adjusted_box_z - config.box_z) > 0.001:
        adjustments.append(f"  box_z: {config.box_z:.3f} → {adjusted_box_z:.3f} nm (auto-adjusted)")

    # Box dimensions (using adjusted values)
    box_dims = np.array([adjusted_box_x, adjusted_box_y, adjusted_box_z])

    # Tile ice for bottom layer: fill [adjusted_box_x, adjusted_box_y, adjusted_ice_thickness]
    bottom_ice_positions, bottom_ice_nmolecules = tile_structure(
        candidate.positions,
        ice_cell_dims,
        np.array([adjusted_box_x, adjusted_box_y, adjusted_ice_thickness]),
        atoms_per_molecule=3  # GenIce ice: O, H, H
    )

    # Tile ice for top layer: same target region, then shift Z
    top_ice_positions, top_ice_nmolecules = tile_structure(
        candidate.positions,
        ice_cell_dims,
        np.array([adjusted_box_x, adjusted_box_y, adjusted_ice_thickness]),
        atoms_per_molecule=3  # GenIce ice: O, H, H
    )
    # Shift top layer to Z = [adjusted_ice_thickness + water_thickness, adjusted_box_z]
    top_ice_positions = top_ice_positions.copy()
    top_ice_positions[:, 2] += adjusted_ice_thickness + config.water_thickness

    # PBC wrap check: ensure top ice atoms are within [0, adjusted_box_z)
    # After shift, atoms should be in [adjusted_ice_thickness + water_thickness, adjusted_box_z)
    # but we wrap defensively to handle floating-point precision issues
    # and catch any configuration errors early.
    top_ice_z = top_ice_positions[:, 2]
    if len(top_ice_z) > 0:
        # Check for atoms that would wrap to bottom layer (Z < 0 or Z >= adjusted_box_z)
        below_zero = top_ice_z < 0
        above_boxz = top_ice_z >= adjusted_box_z

        if np.any(below_zero) or np.any(above_boxz):
            # This should never happen if validation is correct, but handle defensively
            from quickice.structure_generation.errors import InterfaceGenerationError
            n_below = np.sum(below_zero)
            n_above = np.sum(above_boxz)
            raise InterfaceGenerationError(
                f"PBC overlap detected: {n_below} top ice atoms have Z < 0, "
                f"{n_above} atoms have Z >= box_z ({adjusted_box_z:.2f} nm). "
                f"This indicates a configuration error: box_z should equal "
                f"2*ice_thickness + water_thickness = {2*adjusted_ice_thickness + config.water_thickness:.2f} nm. "
                f"Got ice_thickness={adjusted_ice_thickness:.2f} nm, water_thickness={config.water_thickness:.2f} nm.",
                mode=config.mode
            )

    # Combine ice positions (bottom + top)
    if len(bottom_ice_positions) > 0 and len(top_ice_positions) > 0:
        combined_ice_positions = np.vstack([bottom_ice_positions, top_ice_positions])
    elif len(bottom_ice_positions) > 0:
        combined_ice_positions = bottom_ice_positions
    elif len(top_ice_positions) > 0:
        combined_ice_positions = top_ice_positions
    else:
        combined_ice_positions = np.zeros((0, 3), dtype=float)

    total_ice_nmolecules = bottom_ice_nmolecules + top_ice_nmolecules

    # Build ice atom names (3 atoms per molecule: O, H, H from GenIce)
    # Uses module-level template for consistency
    ice_atom_names = ICE_ATOM_NAMES_TEMPLATE * total_ice_nmolecules

    # Calculate water density from ice temperature/pressure
    T = candidate.metadata.get('temperature', 273.15)
    P = candidate.metadata.get('pressure', 0.101325)
    target_water_density = water_density_gcm3(T, P)

    # Fill water in middle region: [adjusted_box_x, adjusted_box_y, water_thickness]
    # Note: water thickness is NOT adjusted - it's the gap between ice layers
    water_positions, water_atom_names, water_nmolecules = fill_region_with_water(
        np.array([adjusted_box_x, adjusted_box_y, config.water_thickness]),
        target_density=target_water_density
    )

    # Shift water to Z = [adjusted_ice_thickness, adjusted_ice_thickness + water_thickness]
    if len(water_positions) > 0:
        water_positions = water_positions.copy()
        water_positions[:, 2] += adjusted_ice_thickness

    # Detect overlaps between ice O and water O
    # Ice O atoms: indices [0, 3, 6, ...] (3 atoms per molecule)
    # Water O atoms: indices [0, 4, 8, ...] (4 atoms per molecule)
    if len(combined_ice_positions) > 0 and len(water_positions) > 0:
        ice_o_positions = combined_ice_positions[::3]
        water_o_positions = water_positions[::4]

        overlapping_mol_indices = detect_overlaps(
            ice_o_positions,
            water_o_positions,
            box_dims,
            config.overlap_threshold
        )
    else:
        overlapping_mol_indices = set()

    # Remove overlapping water molecules (atoms_per_molecule=4 for TIP4P)
    if overlapping_mol_indices:
        trimmed_water_positions, water_nmolecules = remove_overlapping_molecules(
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
    else:
        trimmed_water_positions = water_positions

    # Combine all positions: ice FIRST, then water
    if len(combined_ice_positions) > 0 and len(trimmed_water_positions) > 0:
        all_positions = np.vstack([combined_ice_positions, trimmed_water_positions])
    elif len(combined_ice_positions) > 0:
        all_positions = combined_ice_positions
    elif len(trimmed_water_positions) > 0:
        all_positions = trimmed_water_positions
    else:
        all_positions = np.zeros((0, 3), dtype=float)

    # Combine atom names
    all_atom_names = ice_atom_names + water_atom_names

    # Compute counts
    ice_atom_count = len(combined_ice_positions)
    water_atom_count = len(trimmed_water_positions)

    # Build cell matrix (using adjusted dimensions)
    cell = np.diag([adjusted_box_x, adjusted_box_y, adjusted_box_z])

    # Build report (gmx solvate convention: molecules present, not removed)
    total_molecules = total_ice_nmolecules + water_nmolecules
    
    # Include periodicity adjustments in report
    adjustment_report = ""
    if adjustments:
        adjustment_report = (
            f"\n\nPeriodicity adjustments (for continuous images):\n" +
            "\n".join(adjustments)
        )
    
    report = (
        f"Generated slab interface structure\n"
        f"  Ice molecules: {total_ice_nmolecules}\n"
        f"  Water molecules: {water_nmolecules}\n"
        f"  Total molecules: {total_molecules}\n"
        f"  Box: {adjusted_box_x:.2f} x {adjusted_box_y:.2f} x {adjusted_box_z:.2f} nm"
        f"{adjustment_report}"
    )

    return InterfaceStructure(
        positions=all_positions,
        atom_names=all_atom_names,
        cell=cell,
        ice_atom_count=ice_atom_count,
        water_atom_count=water_atom_count,
        ice_nmolecules=total_ice_nmolecules,
        water_nmolecules=water_nmolecules,
        mode="slab",
        report=report
    )
