"""Scoring functions for ranking ice structure candidates.

This module implements three scoring functions for evaluating ice structure candidates:

1. energy_score: Estimates energy based on O-O distance deviation from ideal
2. density_score: Calculates deviation from expected phase density
3. diversity_score: Rewards structural uniqueness (O-O distance distribution fingerprint)

All functions use heuristic approaches appropriate for "vibe coding" - no actual
physics simulations are performed.
"""

import numpy as np
# Note: Counter import removed — diversity_score now uses structural fingerprints
from scipy.spatial import cKDTree

from quickice.structure_generation.types import Candidate
from quickice.structure_generation.ion_inserter import AVOGADRO
from quickice.ranking.types import RankedCandidate, RankingResult, ScoringConfig


def _is_orthorhombic(cell: np.ndarray, tol: float = 1e-10) -> bool:
    """Check if a cell matrix is orthorhombic (diagonal).
    
    An orthorhombic cell has negligible off-diagonal elements, meaning
    the cell vectors are aligned with the coordinate axes. This is the
    case for cubic, tetragonal, and orthorhombic crystal systems.
    
    Args:
        cell: (3, 3) cell matrix in nm
        tol: Absolute tolerance for off-diagonal elements
    
    Returns:
        True if cell is orthorhombic (off-diagonal elements negligible)
    """
    return np.allclose(cell - np.diag(np.diag(cell)), 0, atol=tol)


def _calculate_oo_distances_pbc(
    positions: np.ndarray,
    atom_names: list[str],
    cell: np.ndarray,
    cutoff: float = 0.35  # nm - default from ScoringConfig.oo_cutoff
) -> np.ndarray:
    """Calculate O-O distances with periodic boundary conditions.
    
    Uses cKDTree for O(n log n) neighbor search. For orthorhombic cells, uses boxsize
    parameter for automatic PBC handling (1x memory). For triclinic cells, uses 3x3x3
    supercell (27x memory) as fallback since boxsize only supports orthorhombic PBC.
    
    Args:
        positions: (N_atoms, 3) coordinates in nm
        atom_names: List of atom names
        cell: (3, 3) cell vectors in nm
        cutoff: Maximum distance to consider (nm)
    
    Returns:
        Array of O-O distances within cutoff
    """
    # Extract O positions (oxygen atoms by name, works for both TIP3P and TIP4P)
    # TIP3P: 'O', TIP4P: 'OW'
    o_indices = [i for i, name in enumerate(atom_names) if name in ('O', 'OW')]
    
    if len(o_indices) < 2:
        return np.array([])
    
    o_positions = positions[o_indices]
    n_oxygen = len(o_indices)
    
    # Get cell dimensions
    cell_dims = np.diag(cell)
    
    if _is_orthorhombic(cell):
        # Orthorhombic: use boxsize parameter for automatic PBC handling (1x memory)
        # Pattern from overlap_resolver.py — wrap coordinates into [0, box_dims) first
        o_wrapped = o_positions.copy()
        for dim in range(3):
            o_wrapped[:, dim] = np.mod(o_wrapped[:, dim], cell_dims[dim])
        
        # Handle floating-point edge case: np.mod(-tiny, L) can return exactly L
        # due to float64 precision limits. cKDTree requires data < boxsize,
        # so values exactly on the PBC boundary must wrap to 0.
        for dim in range(3):
            on_boundary = o_wrapped[:, dim] >= cell_dims[dim]
            o_wrapped[on_boundary, dim] -= cell_dims[dim]
        
        box_list = cell_dims.tolist()
        tree = cKDTree(o_wrapped, boxsize=box_list)
        
        pairs = tree.query_pairs(cutoff)
        
        # Compute minimum image distances for each pair
        # query_pairs with boxsize identifies pairs by minimum image distance,
        # but direct Euclidean distance between wrapped coords may differ
        # (e.g., atoms at x=0.1 and x=1.4 in a 1.5 nm box have direct distance
        # 1.3 nm but minimum image distance 0.2 nm)
        distances = []
        for i, j in pairs:
            delta = o_wrapped[j] - o_wrapped[i]
            # Minimum image convention: shift delta to nearest image
            delta = delta - cell_dims * np.round(delta / cell_dims)
            dist = np.linalg.norm(delta)
            distances.append(dist)
    else:
        # Triclinic: use 3x3x3 supercell fallback (27x memory)
        # boxsize only supports orthorhombic PBC; triclinic needs explicit images
        supercell_o = []
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for k in (-1, 0, 1):
                    offset = np.array([i, j, k]) * cell_dims
                    supercell_o.append(o_positions + offset)
        
        supercell_o = np.vstack(supercell_o)
        
        tree = cKDTree(supercell_o)
        
        pairs = tree.query_pairs(cutoff)
        
        # Extract distances using set-based deduplication
        # The old filter (i < n_oxygen, i < j_original) missed cross-block PBC pairs
        # where atom i in the first image and atom j in another image had j_original < i
        # Use canonical pair deduplication to correctly count all unique pairs
        seen_pairs = set()
        distances = []
        for i, j in pairs:
            i_orig = i % n_oxygen
            j_orig = j % n_oxygen
            if i_orig != j_orig:
                canonical = (min(i_orig, j_orig), max(i_orig, j_orig))
                if canonical not in seen_pairs:
                    seen_pairs.add(canonical)
                    dist = np.linalg.norm(supercell_o[j] - supercell_o[i])
                    distances.append(dist)
    
    return np.array(distances)


def energy_score(
    candidate: Candidate,
    config: ScoringConfig | None = None
) -> float:
    """Calculate energy score based on O-O distance deviation from ideal.
    
    This is a heuristic estimate of the energy based on the assumption that
    ideal ice structures have O-O distances close to the configured ideal value
    (default: 0.276 nm, the typical hydrogen bond length in ice). Structures
    with O-O distances close to this ideal value are assumed to have lower
    energy.
    
    The score is calculated as the mean absolute deviation of O-O distances
    from the ideal value, scaled for visibility. Lower scores indicate
    better structures (more ideal O-O distances).
    
    Args:
        candidate: A Candidate object from Phase 3
        config: Optional ScoringConfig with ideal_oo_distance and oo_cutoff.
            If None, uses default values (0.276 nm ideal, 0.35 nm cutoff).
    
    Returns:
        Energy score (lower = better, lower = closer to ideal O-O distances).
        Returns float('inf') if no O-O distances found (degenerate case).
    
    Note:
        This is NOT an actual energy calculation - it's a heuristic based on
        O-O distance statistics. For real energies, use MD simulations with
        appropriate force fields.
    """
    # Use default config if not provided
    if config is None:
        config = ScoringConfig()
    
    # Calculate O-O distances with PBC
    oo_distances = _calculate_oo_distances_pbc(
        candidate.positions,
        candidate.atom_names,
        candidate.cell,
        cutoff=config.oo_cutoff
    )
    
    # Handle edge case: no O-O pairs within cutoff
    if len(oo_distances) == 0:
        return float('inf')
    
    # Calculate mean absolute deviation from ideal
    deviations = np.abs(oo_distances - config.ideal_oo_distance)
    mean_deviation = np.mean(deviations)
    
    # Scale for visibility (multiply by 100)
    # This makes typical deviations (0.001-0.01 nm) visible in scores (0.1-1.0)
    return mean_deviation * 100.0


def density_score(candidate: Candidate) -> float:
    """Calculate density deviation from expected phase density.
    
    Returns absolute deviation in g/cm³ (lower = better match).
    
    This function compares the actual density of the candidate structure to
    the expected density for its phase. The expected density is taken from
    the candidate's metadata (set during Phase 2 phase mapping), with a
    default of 0.9167 g/cm³ (ice Ih reference density; actual Ice Ih uses IAPWS-calculated value).
    
    Args:
        candidate: A Candidate object from Phase 3
    
    Returns:
        Absolute density deviation in g/cm³ (lower = better match).
    
    Note:
        The density calculation uses:
        - Cell volume from the simulation box
        - Number of molecules
        - Water molecular mass (18.01528 g/mol)
        - Unit conversions: nm³ to cm³ (1e-21 factor)
    """
    # Get expected density from metadata (default: ice Ih density)
    expected_density = candidate.metadata.get('density', 0.9167)  # g/cm³ fallback; Ice Ih uses IAPWS-calculated value via lookup
    
    # Calculate cell volume in nm³
    volume_nm3 = abs(np.linalg.det(candidate.cell))
    
    # Constants for density calculation
    WATER_MASS = 18.01528  # g/mol
    
    # Convert volume from nm³ to cm³ (1 nm³ = 1e-21 cm³)
    volume_cm3 = volume_nm3 * 1e-21
    
    # Calculate actual density
    # density = (n_molecules * mass_per_molecule) / volume
    # mass_per_molecule = molecular_mass / avogadro
    actual_density = (candidate.nmolecules * WATER_MASS) / (AVOGADRO * volume_cm3)
    
    # Validate density is in reasonable range for water/ice
    # Water/ice densities are typically 0.5-1.2 g/cm³
    # Values far outside this range suggest unit mismatch (e.g., Å instead of nm)
    # Å coordinates would give volume 1000x too large → density 1000x too small
    if actual_density < 0.1 or actual_density > 10.0:
        raise ValueError(
            f"Calculated density {actual_density:.3f} g/cm³ is outside reasonable range "
            f"(0.1-10.0 g/cm³). This suggests unit mismatch: candidate.positions and "
            f"candidate.cell must be in nanometers (nm), not Angstroms (Å). "
            f"If coordinates are in Å, convert to nm by dividing by 10. "
            f"Volume: {volume_nm3:.3f} nm³, molecules: {candidate.nmolecules}"
        )
    
    # Return absolute deviation (lower = better)
    return abs(actual_density - expected_density)


def _compute_oo_histogram(
    candidate: Candidate,
    config: ScoringConfig | None = None,
    n_bins: int = 20
) -> np.ndarray:
    """Compute O-O distance distribution histogram as a structural fingerprint.
    
    Creates a normalized histogram of O-O distances, which serves as a
    structural fingerprint for comparing candidate structures. Candidates
    with similar O-O distance distributions will have similar fingerprints.
    
    Args:
        candidate: A Candidate object with positions, atom_names, cell
        config: Optional ScoringConfig for oo_cutoff. If None, uses default (0.35 nm).
        n_bins: Number of histogram bins (default 20)
    
    Returns:
        Normalized histogram as float64 array of shape (n_bins,).
        Returns zeros array if no O-O distances are found.
    """
    if config is None:
        config = ScoringConfig()
    
    # Calculate O-O distances with PBC
    oo_distances = _calculate_oo_distances_pbc(
        candidate.positions,
        candidate.atom_names,
        candidate.cell,
        cutoff=config.oo_cutoff
    )
    
    if len(oo_distances) == 0:
        return np.zeros(n_bins, dtype=np.float64)
    
    # Create histogram over [0, oo_cutoff] range
    hist, _ = np.histogram(oo_distances, bins=n_bins, range=(0.0, config.oo_cutoff))
    
    # Normalize to probability distribution
    hist = hist.astype(np.float64)
    total = hist.sum()
    if total > 0:
        hist = hist / total
    
    return hist


def _histogram_cosine_similarity(hist_a: np.ndarray, hist_b: np.ndarray) -> float:
    """Compute cosine similarity between two histogram fingerprints.
    
    Args:
        hist_a: First normalized histogram
        hist_b: Second normalized histogram
    
    Returns:
        Cosine similarity in [0, 1] where 1 = identical distributions,
        0 = completely different (orthogonal). Returns 0.0 if either
        histogram has zero norm (degenerate case).
    """
    norm_a = np.linalg.norm(hist_a)
    norm_b = np.linalg.norm(hist_b)
    
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    
    return float(np.dot(hist_a, hist_b) / (norm_a * norm_b))


def diversity_score(candidate: Candidate, all_candidates: list[Candidate], config: ScoringConfig | None = None) -> float:
    """Calculate diversity score based on O-O distance distribution fingerprint.
    
    Higher score = more structurally unique compared to other candidates.
    
    Uses O-O distance distribution histograms as structural fingerprints.
    Each candidate's fingerprint is compared to all others using cosine
    similarity. The diversity score is 1 minus the mean cosine similarity
    with all other candidates, meaning:
    - Score ~1.0 = very different from others (diverse)
    - Score ~0.0 = very similar to others (not diverse)
    
    This replaces the previous seed-based approach which always returned 1.0
    because generate_all() assigns unique sequential seeds.
    
    Args:
        candidate: The candidate to score
        all_candidates: All candidates in the generation batch
        config: Optional ScoringConfig for oo_cutoff. If None, uses default (0.35 nm).
    
    Returns:
        Diversity score (higher = more unique). Range approximately [0, 1].
        Returns 0.5 (neutral) for single-candidate batches or if fingerprint
        cannot be computed.
    """
    if len(all_candidates) <= 1:
        return 0.5  # Neutral score for single candidate
    
    if config is None:
        config = ScoringConfig()
    
    # Compute fingerprint for this candidate
    target_hist = _compute_oo_histogram(candidate, config)
    
    if np.linalg.norm(target_hist) == 0:
        return 0.5  # Degenerate: no O-O distances
    
    # Compute fingerprints for all OTHER candidates
    similarities = []
    for other in all_candidates:
        if other is candidate:
            continue
        other_hist = _compute_oo_histogram(other, config)
        sim = _histogram_cosine_similarity(target_hist, other_hist)
        similarities.append(sim)
    
    if not similarities:
        return 0.5  # Only candidate
    
    # Diversity = 1 - mean_similarity
    # High similarity → low diversity, low similarity → high diversity
    mean_sim = np.mean(similarities)
    return 1.0 - float(mean_sim)


def normalize_scores(scores: list[float]) -> np.ndarray:
    """Normalize scores to 0-1 range using min-max scaling.
    
    Lower raw scores become lower normalized scores (0 = min, 1 = max).
    If all scores equal, returns zeros.
    
    This normalization is used to bring all scoring components to a common
    0-1 scale before combining them with weights. The convention is:
    
    - Energy score: lower raw = better, so lower normalized = better
    - Density score: lower raw = better, so lower normalized = better  
    - Diversity score: higher raw = better, so higher normalized = better
      (will be inverted during combination to maintain lower=better convention)
    
    Args:
        scores: List of raw scores to normalize
    
    Returns:
        Normalized scores as numpy array (0.0 to 1.0 range).
        Returns array of zeros if all scores are equal.
    
    Example:
        >>> normalize_scores([1.0, 2.0, 3.0])
        array([0. , 0.5, 1. ])
    """
    scores_array = np.array(scores, dtype=float)
    
    # Get min and max
    min_score = np.min(scores_array)
    max_score = np.max(scores_array)
    
    # Handle edge case: all scores equal
    if max_score == min_score:
        return np.zeros_like(scores_array)
    
    # Min-max normalization
    normalized = (scores_array - min_score) / (max_score - min_score)
    
    return normalized


def rank_candidates(
    candidates: list[Candidate],
    weights: dict[str, float] | None = None,
    config: ScoringConfig | None = None
) -> RankingResult:
    """Rank candidates by combined scoring.
    
    Args:
        candidates: List of Candidate objects from Phase 3
        weights: Optional weight config (default: equal weights 1:1:1)
            Must contain 'energy', 'density', 'diversity' keys if provided.
        config: Optional ScoringConfig with ideal_oo_distance and oo_cutoff.
            If None, uses default values (0.276 nm ideal, 0.35 nm cutoff).
    
    Returns:
        RankingResult with sorted candidates and score breakdown.
        Candidates are sorted by combined_score (ascending, lower = better).
        Ranks are assigned with 1 = best.
    
    Note:
        The combined score follows the convention that lower = better:
        - Energy score: lower normalized = better (use directly)
        - Density score: lower normalized = better (use directly)
        - Diversity score: higher normalized = better (invert: 1 - norm_diversity)
        
        This ensures consistent ranking where combined_score 0 = best possible.
    
    Example:
        >>> result = rank_candidates(candidates)
        >>> print(result.ranked_candidates[0].rank)  # 1 (best)
    """
    # Use default config if not provided
    if config is None:
        config = ScoringConfig()
    
    # Default weights: equal weighting
    if weights is None:
        weights = {'energy': 1.0, 'density': 1.0, 'diversity': 1.0}
    
    n_candidates = len(candidates)
    
    # Calculate raw scores for each component
    energy_scores = [energy_score(c, config) for c in candidates]
    density_scores = [density_score(c) for c in candidates]
    diversity_scores = [diversity_score(c, candidates, config) for c in candidates]
    
    # Normalize each component to 0-1
    norm_energy = normalize_scores(energy_scores)
    norm_density = normalize_scores(density_scores)
    norm_diversity = normalize_scores(diversity_scores)
    
    # Calculate combined score for each candidate
    # For energy/density: lower normalized = better, use directly
    # For diversity: higher normalized = better, invert for lower=better convention
    ranked_candidates = []
    
    for i, candidate in enumerate(candidates):
        # Combined score: lower = better
        # Invert diversity: (1 - norm_diversity) so higher diversity gives lower combined
        combined_score = (
            weights['energy'] * norm_energy[i] +
            weights['density'] * norm_density[i] +
            weights['diversity'] * (1.0 - norm_diversity[i])
        )
        
        ranked_candidates.append(RankedCandidate(
            candidate=candidate,
            energy_score=energy_scores[i],
            density_score=density_scores[i],
            diversity_score=diversity_scores[i],
            combined_score=float(combined_score),
            rank=0  # Will be assigned after sorting
        ))
    
    # Sort by combined_score (ascending, lower = better)
    ranked_candidates.sort(key=lambda rc: rc.combined_score)
    
    # Assign ranks (1 = best)
    for rank, rc in enumerate(ranked_candidates, start=1):
        rc.rank = rank
    
    # Build metadata
    scoring_metadata = {
        'n_candidates': n_candidates,
        'ideal_oo_distance': config.ideal_oo_distance,
        'oo_cutoff': config.oo_cutoff,
        'energy_range': (float(min(energy_scores)), float(max(energy_scores))),
        'density_range': (float(min(density_scores)), float(max(density_scores))),
        'diversity_range': (float(min(diversity_scores)), float(max(diversity_scores))),
    }
    
    return RankingResult(
        ranked_candidates=ranked_candidates,
        scoring_metadata=scoring_metadata,
        weight_config=weights.copy()
    )