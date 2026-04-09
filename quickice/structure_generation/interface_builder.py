"""Interface builder orchestrator with validation and mode routing.

This module provides the main entry point for interface generation:
- validate_interface_config: Pre-generation validation
- generate_interface: Route to correct mode and generate interface

All validation failures raise InterfaceGenerationError with descriptive messages.
"""

import numpy as np

from quickice.structure_generation.types import Candidate, InterfaceConfig, InterfaceStructure
from quickice.structure_generation.errors import InterfaceGenerationError
from quickice.structure_generation.modes.slab import assemble_slab
from quickice.structure_generation.modes.pocket import assemble_pocket
from quickice.structure_generation.modes.piece import assemble_piece


def is_cell_orthogonal(cell: np.ndarray, tol: float = 1e-10) -> bool:
    """Check if a cell matrix represents an orthogonal (rectangular) box.

    An orthogonal cell has non-zero elements only on the diagonal.
    Triclinic cells have off-diagonal elements representing tilt.

    Args:
        cell: (3, 3) cell matrix where each row is a lattice vector.
        tol: Tolerance for considering off-diagonal elements as zero.

    Returns:
        True if the cell is orthogonal, False if triclinic.
    """
    off_diagonal = cell.copy()
    np.fill_diagonal(off_diagonal, 0)
    return np.allclose(off_diagonal, 0, atol=tol)


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
            f"Box X dimension must be positive, got {config.box_x:.2f} nm.",
            mode=config.mode
        )
    if config.box_y <= 0:
        raise InterfaceGenerationError(
            f"Box Y dimension must be positive, got {config.box_y:.2f} nm.",
            mode=config.mode
        )
    if config.box_z <= 0:
        raise InterfaceGenerationError(
            f"Box Z dimension must be positive, got {config.box_z:.2f} nm.",
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

    # Check for triclinic (non-orthogonal) cells
    if not is_cell_orthogonal(candidate.cell):
        # Calculate the phase info for error message
        phase_id = getattr(candidate, 'phase_id', 'unknown')
        raise InterfaceGenerationError(
            f"Triclinic (non-orthogonal) cell detected for phase '{phase_id}'. "
            f"QuickIce v3.0 only supports orthogonal cells. "
            f"The cell has off-diagonal elements which indicate a tilted box. "
            f"Affected phases include: ice_ii, ice_v. "
            f"Please select a different ice phase or contact support for triclinic support.",
            mode=config.mode
        )

    # Mode-specific checks
    if config.mode == "slab":
        # Validate box_z matches ice + water thicknesses
        expected_z = 2 * config.ice_thickness + config.water_thickness
        if abs(config.box_z - expected_z) > 0.01:  # 0.01 nm tolerance
            raise InterfaceGenerationError(
                f"Box Z ({config.box_z:.2f} nm) must equal 2*ice_thickness + water_thickness "
                f"(expected {expected_z:.2f} nm = 2*{config.ice_thickness:.2f} + {config.water_thickness:.2f}).",
                mode=config.mode
            )

        if config.ice_thickness <= 0:
            raise InterfaceGenerationError(
                f"Ice thickness must be positive for slab mode, got {config.ice_thickness:.2f} nm.",
                mode=config.mode
            )

        if config.water_thickness <= 0:
            raise InterfaceGenerationError(
                f"Water thickness must be positive for slab mode, got {config.water_thickness:.2f} nm.",
                mode=config.mode
            )

    elif config.mode == "pocket":
        # Pocket diameter must be smaller than box dimensions
        min_box = min(config.box_x, config.box_y, config.box_z)
        if config.pocket_diameter >= min_box:
            raise InterfaceGenerationError(
                f"Pocket diameter ({config.pocket_diameter:.2f} nm) must be smaller than "
                f"box dimensions (min: {min_box:.2f} nm).",
                mode=config.mode
            )

        if config.pocket_diameter <= 0:
            raise InterfaceGenerationError(
                f"Pocket diameter must be positive, got {config.pocket_diameter:.2f} nm.",
                mode=config.mode
            )

        # Check pocket_shape (v3.0 only supports sphere)
        if config.pocket_shape != "sphere":
            raise InterfaceGenerationError(
                f"Ellipsoid pockets not yet supported. pocket_shape must be 'sphere', got '{config.pocket_shape}'.",
                mode=config.mode
            )

    elif config.mode == "piece":
        # Box dimensions must be larger than candidate cell diagonal
        ice_dims = np.array([
            candidate.cell[0, 0],
            candidate.cell[1, 1],
            candidate.cell[2, 2]
        ])

        if config.box_x <= ice_dims[0]:
            raise InterfaceGenerationError(
                f"Box X ({config.box_x:.2f} nm) must be larger than ice piece X ({ice_dims[0]:.2f} nm).",
                mode=config.mode
            )
        if config.box_y <= ice_dims[1]:
            raise InterfaceGenerationError(
                f"Box Y ({config.box_y:.2f} nm) must be larger than ice piece Y ({ice_dims[1]:.2f} nm).",
                mode=config.mode
            )
        if config.box_z <= ice_dims[2]:
            raise InterfaceGenerationError(
                f"Box Z ({config.box_z:.2f} nm) must be larger than ice piece Z ({ice_dims[2]:.2f} nm).",
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
    # Validate configuration before generation
    validate_interface_config(config, candidate)

    # Route to mode
    try:
        if config.mode == "slab":
            return assemble_slab(candidate, config)
        elif config.mode == "pocket":
            return assemble_pocket(candidate, config)
        elif config.mode == "piece":
            return assemble_piece(candidate, config)
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
