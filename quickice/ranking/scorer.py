"""Scoring functions for ranking ice structure candidates.

This module implements three scoring functions for evaluating ice structure candidates:

1. energy_score: Estimates energy based on O-O distance deviation from ideal
2. density_score: Calculates deviation from expected phase density
3. diversity_score: Rewards unique seeds (single-phase fallback)

All functions use heuristic approaches appropriate for "vibe coding" - no actual
physics simulations are performed.
"""

import numpy as np
from collections import Counter

from quickice.structure_generation.types import Candidate


# Constants for scoring
IDEAL_OO_DISTANCE = 0.276  # nm - ideal O-O distance in ice (H-bond length)
OO_CUTOFF = 0.35  # nm - cutoff for H-bond detection


def _calculate_oo_distances_pbc(
    positions: np.ndarray,
    atom_names: list[str],
    cell: np.ndarray,
    cutoff: float = OO_CUTOFF
) -> np.ndarray:
    """Calculate O-O distances with periodic boundary conditions.
    
    Uses minimum image convention for PBC handling.
    
    Args:
        positions: (N_atoms, 3) coordinates in nm
        atom_names: List of atom names
        cell: (3, 3) cell vectors in nm
        cutoff: Maximum distance to consider (nm)
    
    Returns:
        Array of O-O distances within cutoff
    """
    # Extract O atom indices (O atoms at indices 0, 3, 6... for TIP3P)
    o_indices = [i for i, name in enumerate(atom_names) if name == 'O']
    
    if len(o_indices) < 2:
        return np.array([])
    
    # Get O positions
    o_positions = positions[o_indices]
    
    # Convert to fractional coordinates
    inv_cell = np.linalg.inv(cell)
    frac_coords = o_positions @ inv_cell
    
    # Calculate pairwise distances with minimum image convention
    distances = []
    n_oxygen = len(o_indices)
    
    for i in range(n_oxygen):
        for j in range(i + 1, n_oxygen):
            # Fractional displacement with minimum image
            delta_frac = frac_coords[j] - frac_coords[i]
            delta_frac = delta_frac - np.floor(delta_frac + 0.5)
            
            # Convert back to Cartesian
            delta_cart = delta_frac @ cell
            
            # Calculate distance
            dist = np.linalg.norm(delta_cart)
            
            if dist < cutoff:
                distances.append(dist)
    
    return np.array(distances)


def energy_score(candidate: Candidate) -> float:
    """Calculate energy score based on O-O distance deviation from ideal.
    
    This is a heuristic estimate of the energy based on the assumption that
    ideal ice structures have O-O distances close to 0.276 nm (the typical
    hydrogen bond length in ice). Structures with O-O distances close to
    this ideal value are assumed to have lower energy.
    
    The score is calculated as the mean absolute deviation of O-O distances
    from the ideal value, scaled for visibility. Lower scores indicate
    better structures (more ideal O-O distances).
    
    Args:
        candidate: A Candidate object from Phase 3
    
    Returns:
        Energy score (lower = better, lower = closer to ideal O-O distances).
        Returns float('inf') if no O-O distances found (degenerate case).
    
    Note:
        This is NOT an actual energy calculation - it's a heuristic based on
        O-O distance statistics. For real energies, use MD simulations with
        appropriate force fields.
    """
    # Calculate O-O distances with PBC
    oo_distances = _calculate_oo_distances_pbc(
        candidate.positions,
        candidate.atom_names,
        candidate.cell
    )
    
    # Handle edge case: no O-O pairs within cutoff
    if len(oo_distances) == 0:
        return float('inf')
    
    # Calculate mean absolute deviation from ideal
    deviations = np.abs(oo_distances - IDEAL_OO_DISTANCE)
    mean_deviation = np.mean(deviations)
    
    # Scale for visibility (multiply by 100)
    # This makes typical deviations (0.001-0.01 nm) visible in scores (0.1-1.0)
    return mean_deviation * 100.0
