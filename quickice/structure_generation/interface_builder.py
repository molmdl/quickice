"""Interface builder orchestrator with validation and mode routing.

This module provides the main entry point for interface generation:
- validate_interface_config: Pre-generation validation
- generate_interface: Route to correct mode and generate interface

All validation failures raise InterfaceGenerationError with descriptive messages.
"""

import numpy as np

from quickice.structure_generation.types import Candidate, InterfaceConfig, InterfaceStructure
from quickice.structure_generation.cell_utils import is_cell_orthogonal
from quickice.structure_generation.errors import InterfaceGenerationError
from quickice.structure_generation.modes.slab import assemble_slab
from quickice.structure_generation.modes.pocket import assemble_pocket
from quickice.structure_generation.modes.piece import assemble_piece


# Physical constants for validation
MINIMUM_BOX_DIMENSION = 1.0  # nm - Minimum box dimension for physical validity
# Rationale: Water molecule diameter ~0.28 nm, ice unit cells 0.6-0.9 nm
# Conservative minimum ensures enough space for at least one unit cell


def validate_interface_config(config: InterfaceConfig, candidate: Candidate) -> None:
    """Validate interface configuration before generation.

    Performs common checks and mode-specific validation. Raises
    InterfaceGenerationError if any validation fails, allowing
    fail-fast behavior before expensive generation operations.

    Args:
        config: Interface configuration to validate.
        candidate: Ice structure candidate to validate against.

    Raises:
        InterfaceGenerationError: If configuration is invalid.
    """
    # Common checks: box dimensions must be positive
    if config.box_x <= 0:
        raise InterfaceGenerationError(
            f"Box X dimension must be positive, got {config.box_x:.2f} nm. "
            f"Box dimensions define the simulation cell size. "
            f"Use positive values (e.g., 5.0 nm for typical systems).",
            mode=config.mode
        )
    if config.box_y <= 0:
        raise InterfaceGenerationError(
            f"Box Y dimension must be positive, got {config.box_y:.2f} nm. "
            f"Box dimensions define the simulation cell size. "
            f"Use positive values (e.g., 5.0 nm for typical systems).",
            mode=config.mode
        )
    if config.box_z <= 0:
        raise InterfaceGenerationError(
            f"Box Z dimension must be positive, got {config.box_z:.2f} nm. "
            f"Box dimensions define the simulation cell size. "
            f"Use positive values (e.g., 10.0 nm for slab interfaces).",
            mode=config.mode
        )

    # Check minimum box dimensions for physical validity
    if config.box_x < MINIMUM_BOX_DIMENSION:
        raise InterfaceGenerationError(
            f"Box X dimension ({config.box_x:.3f} nm) is too small. "
            f"Minimum is {MINIMUM_BOX_DIMENSION:.1f} nm. "
            f"Water molecules have diameter ~0.28 nm; boxes smaller than 1.0 nm "
            f"cause numerical issues and cannot fit realistic structures.",
            mode=config.mode
        )
    if config.box_y < MINIMUM_BOX_DIMENSION:
        raise InterfaceGenerationError(
            f"Box Y dimension ({config.box_y:.3f} nm) is too small. "
            f"Minimum is {MINIMUM_BOX_DIMENSION:.1f} nm. "
            f"Water molecules have diameter ~0.28 nm; boxes smaller than 1.0 nm "
            f"cause numerical issues and cannot fit realistic structures.",
            mode=config.mode
        )
    if config.box_z < MINIMUM_BOX_DIMENSION:
        raise InterfaceGenerationError(
            f"Box Z dimension ({config.box_z:.3f} nm) is too small. "
            f"Minimum is {MINIMUM_BOX_DIMENSION:.1f} nm. "
            f"Water molecules have diameter ~0.28 nm; boxes smaller than 1.0 nm "
            f"cause numerical issues and cannot fit realistic structures.",
            mode=config.mode
        )

    # Check candidate has valid positions and cell
    if candidate.positions is None or len(candidate.positions) == 0:
        raise InterfaceGenerationError(
            "Candidate has no positions. Cannot generate interface.",
            mode=config.mode
        )

    if candidate.cell is None or candidate.cell.shape != (3, 3):
        raise InterfaceGenerationError(
            "Candidate has invalid cell matrix. Cannot generate interface.",
            mode=config.mode
        )

    # Check for Ice II - rhombohedral phase that cannot have orthogonal supercell
    # Ice II has both b[0] < 0 and c[0] < 0, creating triangular gaps when forced into orthogonal box
    if candidate.phase_id == "ice_ii":
        raise InterfaceGenerationError(
            f"[{config.mode}] Ice II (rhombohedral, space group R-3) is not supported for interface generation. "
            f"\n\nIce II has a rhombohedral crystal structure that cannot be transformed to an orthogonal supercell "
            f"(this is a fundamental crystallographic constraint). When forced into an orthogonal simulation box, "
            f"Ice II develops triangular gaps at the corners, leaving significant empty regions. "
            f"\n\nSupported phases for interfaces:\n"
            f"  • Ice V (monoclinic): Works correctly (rectangular XY projection)\n"
            f"  • Ice VI (tetragonal): Works correctly (already orthogonal)\n"
            f"  • All other orthogonal phases (Ice Ih, Ic, III, VII, VIII): Work correctly\n"
            f"\nFor Ice II interfaces, consider using a different phase or contact support for future triclinic box output.",
            mode=config.mode
        )

    # Mode-specific checks
    if config.mode == "slab":
        # Validate box_z matches ice + water thicknesses
        # Slab structure: bottom ice | water | top ice
        # Each ice layer has thickness ice_thickness
        # Water layer has thickness water_thickness
        # Therefore: box_z = 2*ice_thickness + water_thickness
        expected_z = 2 * config.ice_thickness + config.water_thickness
        if abs(config.box_z - expected_z) > 0.01:  # 0.01 nm tolerance
            raise InterfaceGenerationError(
                f"Box Z dimension ({config.box_z:.2f} nm) does not match layer thicknesses. "
                f"\n\nFor slab mode, the simulation box contains three layers stacked along Z:\n"
                f"  • Bottom ice: {config.ice_thickness:.2f} nm\n"
                f"  • Water layer: {config.water_thickness:.2f} nm\n"
                f"  • Top ice: {config.ice_thickness:.2f} nm\n\n"
                f"Required box_z = 2×ice_thickness + water_thickness\n"
                f"              = 2×{config.ice_thickness:.2f} + {config.water_thickness:.2f}\n"
                f"              = {expected_z:.2f} nm\n\n"
                f"Your box_z = {config.box_z:.2f} nm differs by {abs(config.box_z - expected_z):.2f} nm.\n\n"
                f"How to fix:\n"
                f"  Option 1: Set box_z to {expected_z:.2f} nm (matches current thicknesses)\n"
                f"  Option 2: Adjust ice/water thicknesses to sum to {config.box_z:.2f} nm\n"
                f"  Example: ice=3.0 nm, water=4.0 nm → box_z = 10.0 nm",
                mode=config.mode
            )

        if config.ice_thickness <= 0:
            raise InterfaceGenerationError(
                f"Ice thickness must be positive for slab mode, got {config.ice_thickness:.2f} nm. "
                f"Ice thickness defines the thickness of each ice layer (top and bottom). "
                f"Typical values: 2–10 nm for surface studies. "
                f"Use positive values (e.g., 3.0 nm).",
                mode=config.mode
            )

        if config.water_thickness <= 0:
            raise InterfaceGenerationError(
                f"Water thickness must be positive for slab mode, got {config.water_thickness:.2f} nm. "
                f"Water thickness defines the liquid water layer between ice slabs. "
                f"Typical values: 2–10 nm for surface studies. "
                f"Use positive values (e.g., 4.0 nm).",
                mode=config.mode
            )

    elif config.mode == "pocket":
        # Pocket diameter must be smaller than box dimensions
        # The pocket is carved out of ice and must fit inside the box
        min_box = min(config.box_x, config.box_y, config.box_z)
        if config.pocket_diameter >= min_box:
            raise InterfaceGenerationError(
                f"Pocket diameter ({config.pocket_diameter:.2f} nm) must be smaller than "
                f"box dimensions (minimum: {min_box:.2f} nm). "
                f"\n\nThe pocket is a spherical water cavity carved inside the ice matrix. "
                f"It must fit entirely within the simulation box. "
                f"\n\nHow to fix:\n"
                f"  Option 1: Reduce pocket diameter to < {min_box:.2f} nm (e.g., {min_box - 0.5:.2f} nm)\n"
                f"  Option 2: Increase all box dimensions to > {config.pocket_diameter:.2f} nm\n"
                f"  Example: For 3.0 nm pocket, use box of 4.0×4.0×4.0 nm",
                mode=config.mode
            )

        if config.pocket_diameter <= 0:
            raise InterfaceGenerationError(
                f"Pocket diameter must be positive, got {config.pocket_diameter:.2f} nm. "
                f"Pocket diameter defines the size of the water-filled cavity inside ice. "
                f"Typical values: 1–5 nm for confined water studies. "
                f"Use positive values (e.g., 2.0 nm).",
                mode=config.mode
            )

        # Check pocket_shape is valid
        valid_shapes = {"sphere", "cubic"}
        if config.pocket_shape not in valid_shapes:
            raise InterfaceGenerationError(
                f"Invalid pocket shape: '{config.pocket_shape}'. "
                f"Valid shapes are: sphere and cubic. "
                f"\n\nHow to fix: Select a valid pocket shape in the UI.",
                mode=config.mode
            )

    elif config.mode == "piece":
        # Box dimensions must be larger than candidate cell diagonal
        # The ice piece is centered in the water box and must fit with space for water
        ice_dims = np.array([
            candidate.cell[0, 0],
            candidate.cell[1, 1],
            candidate.cell[2, 2]
        ])

        if config.box_x <= ice_dims[0]:
            raise InterfaceGenerationError(
                f"Box X dimension ({config.box_x:.2f} nm) must be larger than ice piece X ({ice_dims[0]:.2f} nm). "
                f"\n\nIn piece mode, an ice crystal fragment is centered inside a water box. "
                f"The ice piece comes from the selected candidate and has dimensions "
                f"{ice_dims[0]:.2f} × {ice_dims[1]:.2f} × {ice_dims[2]:.2f} nm. "
                f"\n\nHow to fix:\n"
                f"  Increase box X to at least {ice_dims[0] + 1.0:.2f} nm (allows ~0.5 nm water on each side)\n"
                f"  Example: For ice piece of {ice_dims[0]:.2f} nm, use box X = {ice_dims[0] + 1.0:.2f} nm or larger",
                mode=config.mode
            )
        if config.box_y <= ice_dims[1]:
            raise InterfaceGenerationError(
                f"Box Y dimension ({config.box_y:.2f} nm) must be larger than ice piece Y ({ice_dims[1]:.2f} nm). "
                f"\n\nIn piece mode, an ice crystal fragment is centered inside a water box. "
                f"The ice piece comes from the selected candidate and has dimensions "
                f"{ice_dims[0]:.2f} × {ice_dims[1]:.2f} × {ice_dims[2]:.2f} nm. "
                f"\n\nHow to fix:\n"
                f"  Increase box Y to at least {ice_dims[1] + 1.0:.2f} nm (allows ~0.5 nm water on each side)\n"
                f"  Example: For ice piece of {ice_dims[1]:.2f} nm, use box Y = {ice_dims[1] + 1.0:.2f} nm or larger",
                mode=config.mode
            )
        if config.box_z <= ice_dims[2]:
            raise InterfaceGenerationError(
                f"Box Z dimension ({config.box_z:.2f} nm) must be larger than ice piece Z ({ice_dims[2]:.2f} nm). "
                f"\n\nIn piece mode, an ice crystal fragment is centered inside a water box. "
                f"The ice piece comes from the selected candidate and has dimensions "
                f"{ice_dims[0]:.2f} × {ice_dims[1]:.2f} × {ice_dims[2]:.2f} nm. "
                f"\n\nHow to fix:\n"
                f"  Increase box Z to at least {ice_dims[2] + 1.0:.2f} nm (allows ~0.5 nm water on each side)\n"
                f"  Example: For ice piece of {ice_dims[2]:.2f} nm, use box Z = {ice_dims[2] + 1.0:.2f} nm or larger",
                mode=config.mode
            )

        # Validate minimum water layer thickness
        # Water molecules within overlap_threshold of ice surface are removed.
        # For any water to survive, the water layer must be at least overlap_threshold thick.
        # This ensures the box has enough space for viable water filling.
        min_water_layer = config.overlap_threshold
        water_layer_x = config.box_x - ice_dims[0]
        water_layer_y = config.box_y - ice_dims[1]
        water_layer_z = config.box_z - ice_dims[2]

        if water_layer_x < min_water_layer:
            raise InterfaceGenerationError(
                f"Water layer too thin in X dimension. "
                f"\n\nCalculation:\n"
                f"  Water layer X = Box X ({config.box_x:.2f} nm) - Ice X ({ice_dims[0]:.2f} nm)\n"
                f"               = {water_layer_x:.3f} nm\n\n"
                f"Why this matters:\n"
                f"  Water molecules placed too close to ice (within {min_water_layer:.2f} nm) "
                f"are removed to avoid atomic overlaps. A water layer thinner than "
                f"{min_water_layer:.2f} nm (overlap threshold) would have all water molecules "
                f"removed, leaving only ice.\n\n"
                f"How to fix:\n"
                f"  Increase box X by at least {min_water_layer - water_layer_x:.2f} nm\n"
                f"  Minimum box X = {ice_dims[0] + min_water_layer:.2f} nm\n"
                f"  Recommended box X = {ice_dims[0] + 1.0:.2f} nm (for ~0.5 nm water on each side)",
                mode=config.mode
            )
        if water_layer_y < min_water_layer:
            raise InterfaceGenerationError(
                f"Water layer too thin in Y dimension. "
                f"\n\nCalculation:\n"
                f"  Water layer Y = Box Y ({config.box_y:.2f} nm) - Ice Y ({ice_dims[1]:.2f} nm)\n"
                f"               = {water_layer_y:.3f} nm\n\n"
                f"Why this matters:\n"
                f"  Water molecules placed too close to ice (within {min_water_layer:.2f} nm) "
                f"are removed to avoid atomic overlaps. A water layer thinner than "
                f"{min_water_layer:.2f} nm (overlap threshold) would have all water molecules "
                f"removed, leaving only ice.\n\n"
                f"How to fix:\n"
                f"  Increase box Y by at least {min_water_layer - water_layer_y:.2f} nm\n"
                f"  Minimum box Y = {ice_dims[1] + min_water_layer:.2f} nm\n"
                f"  Recommended box Y = {ice_dims[1] + 1.0:.2f} nm (for ~0.5 nm water on each side)",
                mode=config.mode
            )
        if water_layer_z < min_water_layer:
            raise InterfaceGenerationError(
                f"Water layer too thin in Z dimension. "
                f"\n\nCalculation:\n"
                f"  Water layer Z = Box Z ({config.box_z:.2f} nm) - Ice Z ({ice_dims[2]:.2f} nm)\n"
                f"               = {water_layer_z:.3f} nm\n\n"
                f"Why this matters:\n"
                f"  Water molecules placed too close to ice (within {min_water_layer:.2f} nm) "
                f"are removed to avoid atomic overlaps. A water layer thinner than "
                f"{min_water_layer:.2f} nm (overlap threshold) would have all water molecules "
                f"removed, leaving only ice.\n\n"
                f"How to fix:\n"
                f"  Increase box Z by at least {min_water_layer - water_layer_z:.2f} nm\n"
                f"  Minimum box Z = {ice_dims[2] + min_water_layer:.2f} nm\n"
                f"  Recommended box Z = {ice_dims[2] + 1.0:.2f} nm (for ~0.5 nm water on each side)",
                mode=config.mode
            )

    else:
        # Unknown mode
        raise InterfaceGenerationError(
            f"Unknown interface mode: '{config.mode}'. Supported modes: slab, pocket, piece.",
            mode=config.mode
        )


def generate_interface(
    candidate: Candidate,
    config: InterfaceConfig
) -> InterfaceStructure:
    """Generate interface structure by routing to correct mode.

    Validates configuration first, then routes to the appropriate
    mode implementation (slab, pocket, or piece).

    Args:
        candidate: Ice structure candidate from GenIce.
        config: Interface configuration specifying mode and parameters.

    Returns:
        InterfaceStructure with combined ice + water positions.

    Raises:
        InterfaceGenerationError: If validation fails or generation fails.
    """
    print(f"[DEBUG interface_builder.py] generate_interface() START - mode={config.mode}")
    print(f"[DEBUG interface_builder.py] Candidate phase_id: {candidate.phase_id}, nmol={candidate.nmolecules}")
    
    # Validate configuration before generation
    validate_interface_config(config, candidate)
    print("[DEBUG interface_builder.py] Validation passed")
    
    # Route to mode
    try:
        print(f"[DEBUG interface_builder.py] Routing to mode: {config.mode}")
        if config.mode == "slab":
            result = assemble_slab(candidate, config)
            print(f"[DEBUG interface_builder.py] assemble_slab() returned")
            return result
        elif config.mode == "pocket":
            result = assemble_pocket(candidate, config)
            print(f"[DEBUG interface_builder.py] assemble_pocket() returned")
            return result
        elif config.mode == "piece":
            result = assemble_piece(candidate, config)
            print(f"[DEBUG interface_builder.py] assemble_piece() returned")
            return result
        else:
            # Should never reach here due to validation, but just in case
            raise InterfaceGenerationError(
                f"Unknown interface mode: {config.mode}",
                mode=config.mode
            )
    except InterfaceGenerationError:
        # Re-raise InterfaceGenerationError as-is
        raise
    except Exception as e:
        # Wrap unexpected errors
        raise InterfaceGenerationError(
            f"Unexpected error during {config.mode} mode generation: {str(e)}",
            mode=config.mode
        ) from e
