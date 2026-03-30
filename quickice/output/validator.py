"""Structure validation for ice structures.

Provides validation functions for:
- Space group detection using spglib
- Atomic overlap detection with periodic boundary conditions
"""

from typing import Any

import numpy as np
import spglib
from scipy.spatial import cKDTree

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

    Uses scipy's cKDTree for O(n log n) neighbor search.

    Args:
        candidate: Ice structure candidate to check
        min_distance: Minimum allowed distance between atoms in Angstrom
                      Default 0.8 Å avoids false positives from O-H bonds (~0.96 Å)

    Returns:
        True if overlap detected, False if no overlap

    Note:
        Candidate positions and cell are in nm, converted to Angstrom internally.
        Uses a 3x3x3 supercell approach for PBC handling.
    """
    # Handle edge cases
    if len(candidate.positions) <= 1:
        return False

    # Convert from nm to Angstrom
    positions = candidate.positions * 10.0
    cell = candidate.cell * 10.0
    
    n_atoms = len(positions)
    
    # Get cell dimensions (assuming orthorhombic for ice structures)
    cell_dims = np.diag(cell)
    
    # Build 3x3x3 supercell for PBC handling
    supercell_positions = []
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            for k in (-1, 0, 1):
                offset = np.array([i, j, k]) * cell_dims
                supercell_positions.append(positions + offset)
    
    supercell_positions = np.vstack(supercell_positions)
    
    # Build KDTree for supercell
    tree = cKDTree(supercell_positions)
    
    # Find pairs within min_distance
    pairs = tree.query_pairs(min_distance)
    
    # Filter: only count pairs where at least one atom is in central cell
    # Central cell indices are [0, n_atoms)
    for i, j in pairs:
        if i < n_atoms and j < n_atoms:
            # Both in central cell - real overlap
            return True
        elif i < n_atoms:
            # i in central, j is image - check if j's original is different from i
            j_original = j % n_atoms
            if j_original != i:
                return True
    
    return False
