"""Mapping layer between QuickIce phase IDs and GenIce lattice names."""

import math

import numpy as np

from quickice.structure_generation.errors import UnsupportedPhaseError

# Phase ID to GenIce lattice name mapping
PHASE_TO_GENICE = {
    "ice_ih": "ice1h",
    "ice_ic": "ice1c",
    "ice_ii": "ice2",
    "ice_iii": "ice3",
    "ice_v": "ice5",
    "ice_vi": "ice6",
    "ice_vii": "ice7",
    "ice_viii": "ice8",
}

# Molecules per unit cell for each GenIce lattice
UNIT_CELL_MOLECULES = {
    "ice1h": 4,
    "ice1c": 8,
    "ice2": 12,
    "ice3": 12,
    "ice5": 28,
    "ice6": 10,  # double network
    "ice7": 16,  # double network
    "ice8": 16,  # double network
}


def get_genice_lattice_name(phase_id: str) -> str:
    """Convert QuickIce phase ID to GenIce lattice name.

    Args:
        phase_id: QuickIce phase identifier (e.g., "ice_ih")

    Returns:
        GenIce lattice name (e.g., "ice1h")

    Raises:
        UnsupportedPhaseError: If phase_id is not in supported phases
    """
    if phase_id not in PHASE_TO_GENICE:
        raise UnsupportedPhaseError(
            f"Phase '{phase_id}' is not supported", phase_id
        )
    return PHASE_TO_GENICE[phase_id]


def calculate_supercell(
    target_molecules: int, molecules_per_unit_cell: int
) -> tuple[np.ndarray, int]:
    """Calculate supercell size to achieve at least target_molecules.

    Finds the smallest n such that molecules_per_unit_cell × n³ ≥ target_molecules.

    Args:
        target_molecules: Desired number of water molecules
        molecules_per_unit_cell: Number of molecules in one unit cell

    Returns:
        Tuple of (reshape_matrix, actual_molecules)
        - reshape_matrix: 3x3 diagonal matrix for n×n×n supercell
        - actual_molecules: Actual count (>= target_molecules)
    """
    # Calculate minimum supercell size
    # We need n such that molecules_per_unit_cell * n^3 >= target_molecules
    # n >= (target_molecules / molecules_per_unit_cell)^(1/3)
    ratio = target_molecules / molecules_per_unit_cell
    n = math.ceil(ratio ** (1/3))

    # Ensure minimum of 1
    n = max(1, n)

    # Calculate actual number of molecules
    actual_molecules = molecules_per_unit_cell * (n ** 3)

    # Create supercell matrix
    supercell = np.array([[n, 0, 0], [0, n, 0], [0, 0, n]], dtype=int)

    return supercell, actual_molecules