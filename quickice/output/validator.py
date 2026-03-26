"""Structure validation for ice structures.

Provides validation functions for:
- Space group detection using spglib
- Atomic overlap detection with periodic boundary conditions
"""

from typing import Any

import numpy as np
import spglib

from quickice.structure_generation.types import Candidate


def validate_space_group(
    candidate: Candidate, symprec: float = 1e-4
) -> dict[str, Any]:
    """Validate space group symmetry of a crystal structure.

    Args:
        candidate: Ice structure candidate to validate
        symprec: Symmetry tolerance in Angstrom (default: 1e-4)
                 Use 1e-4 for generated structures, not the default 1e-5

    Returns:
        Dictionary with keys:
        - spacegroup_number: International space group number (or None if invalid)
        - spacegroup_symbol: Space group symbol (or 'UNKNOWN' if invalid)
        - hall_number: Hall number (only if valid)
        - n_operations: Number of symmetry operations (only if valid)
        - valid: True if space group detected successfully

    Note:
        Candidate positions and cell are in nm, but spglib expects Angstrom.
        This function converts units internally (multiply by 10.0).
    """
    # Convert from nm to Angstrom
    lattice = candidate.cell * 10.0
    positions_cartesian = candidate.positions * 10.0

    # Map atom names to atomic numbers
    atom_name_to_number = {"O": 8, "H": 1}
    atom_types = np.array(
        [atom_name_to_number[name] for name in candidate.atom_names]
    )

    # Convert Cartesian positions to fractional coordinates
    # spglib expects fractional coordinates, not Cartesian
    inv_lattice = np.linalg.inv(lattice)
    positions = positions_cartesian @ inv_lattice

    # Get dataset from spglib
    # spglib expects (lattice, positions, numbers) tuple
    # where positions are in fractional coordinates
    cell_tuple = (lattice, positions, atom_types)
    dataset = spglib.get_symmetry_dataset(cell_tuple, symprec=symprec)

    if dataset is None:
        return {
            "spacegroup_number": None,
            "spacegroup_symbol": "UNKNOWN",
            "valid": False,
        }

    return {
        "spacegroup_number": dataset.number,
        "spacegroup_symbol": dataset.international,
        "hall_number": dataset.hall_number,
        "n_operations": len(dataset.rotations),
        "valid": True,
    }


def check_atomic_overlap(
    candidate: Candidate, min_distance: float = 0.8
) -> bool:
    """Check for overlapping atoms with periodic boundary conditions.

    Args:
        candidate: Ice structure candidate to check
        min_distance: Minimum allowed distance between atoms in Angstrom
                      Default 0.8 Å avoids false positives from O-H bonds (~0.96 Å)

    Returns:
        True if overlap detected, False if no overlap

    Note:
        Uses minimum image convention for PBC distance calculations.
        Candidate positions and cell are in nm, converted to Angstrom internally.
    """
    # Handle edge cases
    if len(candidate.positions) == 0:
        return False

    if len(candidate.positions) == 1:
        return False

    # Convert from nm to Angstrom
    positions = candidate.positions * 10.0
    cell = candidate.cell * 10.0

    # Calculate inverse cell for fractional coordinates
    inv_cell = np.linalg.inv(cell)

    # Convert to fractional coordinates
    frac = positions @ inv_cell

    # Check all pairs
    n_atoms = len(positions)
    for i in range(n_atoms):
        for j in range(i + 1, n_atoms):
            # Calculate delta in fractional coordinates
            delta = frac[j] - frac[i]

            # Apply minimum image convention
            # Wrap to [-0.5, 0.5] range
            delta = delta - np.floor(delta + 0.5)

            # Convert back to Cartesian
            cart_delta = delta @ cell

            # Calculate distance
            dist = np.linalg.norm(cart_delta)

            if dist < min_distance:
                return True

    return False
