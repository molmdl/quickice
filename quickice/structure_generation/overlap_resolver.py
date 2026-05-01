"""PBC-aware overlap detection and whole-molecule removal for interface generation.

This module provides functions to detect overlapping atoms between ice
and water structures using scipy's cKDTree with periodic boundary conditions,
and to remove entire overlapping molecules (never partial molecules).

All coordinates and thresholds are in nanometers (nm).
"""

import numpy as np
from scipy.spatial import cKDTree


def detect_overlaps(
    ice_o_positions_nm: np.ndarray,
    water_o_positions_nm: np.ndarray,
    box_dims_nm: np.ndarray,
    threshold_nm: float = 0.25,
) -> set[int]:
    """Detect water molecules whose oxygen overlaps with any ice oxygen.

    Uses scipy.spatial.cKDTree with the boxsize parameter for automatic
    periodic boundary condition (PBC) handling. The boxsize parameter
    implements minimum-image convention internally, so we do NOT
    hand-roll minimum-image calculations.

    Args:
        ice_o_positions_nm: (N_ice, 3) ice oxygen positions in nm.
        water_o_positions_nm: (N_water, 3) water oxygen positions in nm.
        box_dims_nm: [bx, by, bz] box dimensions in nm for PBC.
        threshold_nm: O-O distance threshold in nm (default 0.25 nm = 2.5 Å).
            Must be in range [0.1, 1.0] nm. Values outside this range suggest
            unit mismatch (e.g., passing Angstrom instead of nm).

    Returns:
        Set of water molecule indices to remove (0-based, indexing into
        water_o_positions_nm). Each index represents one water molecule
        whose oxygen is within threshold_nm of any ice oxygen.

    Raises:
        ValueError: If threshold_nm is outside reasonable range [0.1, 1.0] nm,
            which suggests a unit mismatch (e.g., Angstrom vs nm).
    """
    # Validate threshold to catch unit mismatches
    # Reasonable range: 0.1 nm (1 Å) to 1.0 nm (10 Å)
    # Values outside this range likely indicate wrong units
    if not (0.1 <= threshold_nm <= 1.0):
        raise ValueError(
            f"threshold_nm={threshold_nm} is outside reasonable range [0.1, 1.0] nm. "
            f"This suggests a unit mismatch. "
            f"If you have a value in Angstrom, divide by 10 to get nm "
            f"(e.g., 2.5 Å → 0.25 nm). "
            f"Default: 0.25 nm (2.5 Å) for typical O-O overlap detection."
        )

    if len(ice_o_positions_nm) == 0 or len(water_o_positions_nm) == 0:
        return set()

    # CRITICAL: Wrap coordinates into [0, box_dims_nm) for KDTree
    # Molecules spanning PBC boundaries can have atoms outside [0, boxsize)
    # We wrap each coordinate individually to ensure KDTree compatibility
    ice_o_wrapped = ice_o_positions_nm.copy()
    water_o_wrapped = water_o_positions_nm.copy()
    
    for dim in range(3):
        ice_o_wrapped[:, dim] = np.mod(ice_o_wrapped[:, dim], box_dims_nm[dim])
        water_o_wrapped[:, dim] = np.mod(water_o_wrapped[:, dim], box_dims_nm[dim])

    # Build cKDTree with PBC via boxsize parameter
    # CRITICAL: boxsize handles periodic boundaries automatically
    box_list = box_dims_nm.tolist()
    ice_tree = cKDTree(ice_o_wrapped, boxsize=box_list)
    water_tree = cKDTree(water_o_wrapped, boxsize=box_list)

    # Find all pairs within threshold
    # pairs[water_idx] contains list of ice indices within threshold
    pairs = water_tree.query_ball_tree(ice_tree, r=threshold_nm)

    # Collect water molecule indices that have at least one overlapping ice O
    overlapping = set()
    for water_idx, ice_neighbors in enumerate(pairs):
        if ice_neighbors:  # non-empty list = overlap found
            overlapping.add(water_idx)

    return overlapping


def remove_overlapping_molecules(
    all_positions: np.ndarray,
    overlapping_mol_indices: set[int],
    atoms_per_molecule: int,
) -> tuple[np.ndarray, int]:
    """Remove entire molecules from a positions array.

    Removes ALL atoms of each molecule in overlapping_mol_indices.
    NEVER removes partial molecules — this is critical for maintaining
    molecular integrity in the output structure.

    Args:
        all_positions: (N_total, 3) all atom positions.
        overlapping_mol_indices: Set of molecule indices to remove (0-based).
        atoms_per_molecule: Number of atoms per molecule.
            3 for ice (O, H, H from GenIce).
            4 for water (OW, HW1, HW2, MW from tip4p.gro).

    Returns:
        Tuple of (filtered_positions, n_molecules_remaining):
            - filtered_positions: (M, 3) positions with overlapping molecules removed
            - n_molecules_remaining: number of molecules after removal
    """
    if len(all_positions) == 0:
        return all_positions, 0

    n_molecules = len(all_positions) // atoms_per_molecule

    if not overlapping_mol_indices:
        # Nothing to remove
        return all_positions, n_molecules

    # Create molecule-level keep mask
    keep_mask = np.ones(n_molecules, dtype=bool)
    for mol_idx in overlapping_mol_indices:
        if 0 <= mol_idx < n_molecules:
            keep_mask[mol_idx] = False

    # Expand to atom-level mask
    atom_mask = np.repeat(keep_mask, atoms_per_molecule)

    # Filter positions
    filtered_positions = all_positions[atom_mask]
    n_remaining = int(np.sum(keep_mask))

    return filtered_positions, n_remaining


def filter_atom_names(
    atom_names: list[str],
    overlapping_mol_indices: set[int],
    atoms_per_molecule: int,
) -> list[str]:
    """Filter atom names to match positions filtered by remove_overlapping_molecules.

    Removes atom names for molecules in overlapping_mol_indices.
    MUST be called with the same overlapping_mol_indices that was passed
    to remove_overlapping_molecules to maintain consistency between
    positions and atom_names arrays.

    Args:
        atom_names: List of atom names (e.g., ["OW", "HW1", "HW2", "MW", ...]).
        overlapping_mol_indices: Set of molecule indices to remove (0-based).
            Must be the SAME set passed to remove_overlapping_molecules.
        atoms_per_molecule: Number of atoms per molecule.
            3 for ice (O, H, H from GenIce).
            4 for water (OW, HW1, HW2, MW from tip4p.gro).

    Returns:
        Filtered list of atom names with overlapping molecules removed.

    Example:
        >>> atom_names = ["OW", "HW1", "HW2", "MW", "OW", "HW1", "HW2", "MW"]
        >>> overlapping = {1}  # Remove molecule 1 (indices 4-7)
        >>> filter_atom_names(atom_names, overlapping, 4)
        ['OW', 'HW1', 'HW2', 'MW']  # Only molecule 0 remains
    """
    if not overlapping_mol_indices:
        # Nothing to remove
        return atom_names

    n_molecules = len(atom_names) // atoms_per_molecule

    # Create molecule-level keep mask (same logic as remove_overlapping_molecules)
    keep_mask = np.ones(n_molecules, dtype=bool)
    for mol_idx in overlapping_mol_indices:
        if 0 <= mol_idx < n_molecules:
            keep_mask[mol_idx] = False

    # Filter atom names using molecule-level mask
    filtered_names = []
    for mol_idx in range(n_molecules):
        if keep_mask[mol_idx]:
            start = mol_idx * atoms_per_molecule
            end = start + atoms_per_molecule
            filtered_names.extend(atom_names[start:end])

    return filtered_names


# Unit conversion helpers
def angstrom_to_nm(value_angstrom: float) -> float:
    """Convert distance from Angstrom to nanometers.

    Args:
        value_angstrom: Distance in Angstrom (Å)

    Returns:
        Distance in nanometers (nm)

    Example:
        >>> angstrom_to_nm(2.5)
        0.25
    """
    return value_angstrom / 10.0


def nm_to_angstrom(value_nm: float) -> float:
    """Convert distance from nanometers to Angstrom.

    Args:
        value_nm: Distance in nanometers (nm)

    Returns:
        Distance in Angstrom (Å)

    Example:
        >>> nm_to_angstrom(0.25)
        2.5
    """
    return value_nm * 10.0
