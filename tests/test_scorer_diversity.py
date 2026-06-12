"""Regression tests for BUG-04: diversity_score always returns 1.0.

BUG-04: The previous diversity_score implementation used seed counting
(Counter(all_seeds)[candidate.seed]), which ALWAYS returned 1.0 because
generate_all() assigns unique sequential seeds (0, 1, 2, ...) to every
candidate. This meant diversity_score provided zero discriminatory value
in ranking.

Fix: Replace seed-based approach with O-O distance distribution histogram
fingerprints compared via cosine similarity. Now diversity_score genuinely
differentiates between structurally different candidates.

Test classes:
- TestBUG04AlwaysOneBug: Verify the always-1.0 bug is FIXED
- TestBUG04StructuralDifferentiation: Verify structural differences produce score variation
- TestBUG04IdenticalStructures: Verify identical structures get same score
- TestBUG04HistogramHelper: Unit tests for _compute_oo_histogram and _histogram_cosine_similarity
- TestBUG04EdgeCases: Edge cases (single candidate, no O atoms, 1 O atom)
- TestBUG04Integration: Verify rank_candidates produces varied diversity scores
"""

import numpy as np
import pytest

from quickice.structure_generation.types import Candidate
from quickice.ranking.scorer import (
    diversity_score,
    _compute_oo_histogram,
    _histogram_cosine_similarity,
    rank_candidates,
)
from quickice.ranking.types import ScoringConfig


# ══════════════════════════════════════════════════════════════════════════════
# Helper: Build synthetic TIP4P-ICE candidates for testing
# ══════════════════════════════════════════════════════════════════════════════

# Use 256 molecules in a ~2.04 nm box for realistic ice density (~0.9 g/cm³)
# This satisfies density_score's 0.1-10.0 g/cm³ validation range
_NMOL = 256
_CELL_SIDE = 2.04  # nm → ~0.9 g/cm³ with 256 molecules


def _make_candidate(o_positions, cell_dims, nmolecules, phase_id='ice_ih', seed=0):
    """Build a Candidate with oxygen positions and TIP4P-ICE atom names.

    Args:
        o_positions: (N_oxygen, 3) array of oxygen positions in nm
        cell_dims: (3,) array of cell dimensions in nm
        nmolecules: Number of water molecules
        phase_id: Phase identifier string
        seed: Random seed (matches generate_all() sequential seeding)

    Returns:
        Candidate with TIP4P-ICE OW/HW1/HW2/MW atom pattern
    """
    n_oxygen = len(o_positions)
    positions = np.zeros((n_oxygen * 4, 3))
    atom_names = []
    oh_length = 0.0957  # nm
    om_length = 0.0157  # nm
    for i, o_pos in enumerate(o_positions):
        positions[i * 4] = o_pos                           # OW
        positions[i * 4 + 1] = o_pos + [oh_length, 0, 0]  # HW1
        positions[i * 4 + 2] = o_pos - [oh_length, 0, 0]  # HW2
        positions[i * 4 + 3] = o_pos + [om_length, 0, 0]  # MW
        atom_names.extend(['OW', 'HW1', 'HW2', 'MW'])
    cell = np.diag(cell_dims)
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=nmolecules,
        phase_id=phase_id,
        seed=seed,
    )


def _ice_like_oxygen_positions(n_mol, cell_side, spacing=0.276, rng_seed=42):
    """Generate ice-like oxygen positions at regular nearest-neighbor spacing.

    Places oxygen atoms on a simple cubic-like grid with the given spacing,
    wrapped into the cell for PBC compliance. This produces a realistic
    O-O distance distribution concentrated around the specified spacing.
    """
    rng = np.random.default_rng(rng_seed)
    n_per_side = int(np.ceil(n_mol ** (1/3)))
    positions = []
    idx = 0
    for ix in range(n_per_side):
        for iy in range(n_per_side):
            for iz in range(n_per_side):
                if idx >= n_mol:
                    break
                x = (spacing * ix + rng.uniform(-0.02, 0.02)) % cell_side
                y = (spacing * iy + rng.uniform(-0.02, 0.02)) % cell_side
                z = (spacing * iz + rng.uniform(-0.02, 0.02)) % cell_side
                positions.append([x, y, z])
                idx += 1
    return np.array(positions[:n_mol])


def _random_oxygen_positions(n_mol, cell_side, rng_seed=42):
    """Generate random oxygen positions (amorphous/unstructured distribution)."""
    rng = np.random.default_rng(rng_seed)
    return rng.random((n_mol, 3)) * cell_side


def _clustered_oxygen_positions(n_mol, cell_side, n_clusters=4, rng_seed=42):
    """Generate clustered oxygen positions (non-uniform distribution).

    Creates a few cluster centers and places oxygen atoms near them,
    producing a very different O-O distance distribution compared to
    ice-like or random arrangements.
    """
    rng = np.random.default_rng(rng_seed)
    cluster_centers = rng.uniform(0.3, cell_side - 0.3, (n_clusters, 3))
    positions = []
    for i in range(n_mol):
        center = cluster_centers[i % n_clusters]
        offset = rng.normal(0, 0.05, 3)  # tight clusters (σ=0.05 nm)
        pos = center + offset
        pos = np.mod(pos, cell_side)  # wrap into cell
        positions.append(pos)
    return np.array(positions)


# ══════════════════════════════════════════════════════════════════════════════
# TestBUG04AlwaysOneBug: Core regression test — always-1.0 bug is FIXED
# ══════════════════════════════════════════════════════════════════════════════


class TestBUG04AlwaysOneBug:
    """Verify that diversity_score no longer always returns 1.0.

    The old implementation used seed counting: Counter(all_seeds)[candidate.seed]
    which ALWAYS returned 1 because generate_all() assigns unique sequential
    seeds (0, 1, 2, ...). These tests mimic that scenario and verify the bug
    is fixed.
    """

    def test_five_candidates_sequential_seeds_not_all_one(self):
        """5 candidates with sequential seeds (0-4) should NOT all score 1.0."""
        cell_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])

        # Create structurally different candidates with sequential seeds
        # (mimicking generate_all() which assigns 0, 1, 2, ...)
        structures = [
            _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276, rng_seed=0),
            _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.30, rng_seed=1),
            _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.33, rng_seed=2),
            _random_oxygen_positions(_NMOL, _CELL_SIDE, rng_seed=3),
            _clustered_oxygen_positions(_NMOL, _CELL_SIDE, rng_seed=4),
        ]
        candidates = []
        for i, o_pos in enumerate(structures):
            candidates.append(
                _make_candidate(o_pos, cell_dims, _NMOL, seed=i)
            )

        scores = [diversity_score(c, candidates) for c in candidates]

        # CORE REGRESSION TEST: old code always returned 1.0
        assert not all(s == 1.0 for s in scores), (
            f"BUG-04 regression: all diversity scores are 1.0 — "
            f"seed-based bug may have returned! Scores: {scores}"
        )

    def test_scores_in_valid_range(self):
        """Diversity scores should be in [0, 1] range."""
        cell_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])

        structures = [
            _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276, rng_seed=0),
            _random_oxygen_positions(_NMOL, _CELL_SIDE, rng_seed=1),
            _clustered_oxygen_positions(_NMOL, _CELL_SIDE, rng_seed=2),
        ]
        candidates = []
        for i, o_pos in enumerate(structures):
            candidates.append(
                _make_candidate(o_pos, cell_dims, _NMOL, seed=i)
            )

        scores = [diversity_score(c, candidates) for c in candidates]

        for s in scores:
            assert 0.0 <= s <= 1.0, f"Diversity score {s} out of [0, 1] range"

    def test_not_all_identical_scores_with_different_structures(self):
        """Structurally different candidates should get different diversity scores."""
        cell_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])

        # Ice-like vs random vs clustered — very different O-O distributions
        o_ice = _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276, rng_seed=0)
        o_random = _random_oxygen_positions(_NMOL, _CELL_SIDE, rng_seed=1)
        o_clustered = _clustered_oxygen_positions(_NMOL, _CELL_SIDE, rng_seed=2)

        c_a = _make_candidate(o_ice, cell_dims, _NMOL, seed=0)
        c_b = _make_candidate(o_random, cell_dims, _NMOL, seed=1)
        c_c = _make_candidate(o_clustered, cell_dims, _NMOL, seed=2)

        candidates = [c_a, c_b, c_c]
        scores = [diversity_score(c, candidates) for c in candidates]

        # At least some scores should differ (structurally different)
        assert len(set(round(s, 6) for s in scores)) > 1, (
            f"All diversity scores identical despite different structures: {scores}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestBUG04StructuralDifferentiation: Verify structural differences produce variation
# ══════════════════════════════════════════════════════════════════════════════


class TestBUG04StructuralDifferentiation:
    """Verify that structural differences produce score variation.

    A candidate with a duplicate structure in the batch should score
    LOWER (less diverse) than a candidate with a unique structure.
    """

    def test_diversity_decreases_with_structural_duplicate(self):
        """A's diversity with a structural duplicate (C) is lower than without."""
        cell_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])

        # A: ice-like at 0.276 nm spacing
        # B: random (very different distribution)
        # C: ice-like at 0.276 nm (same as A)
        o_a = _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276, rng_seed=10)
        o_b = _random_oxygen_positions(_NMOL, _CELL_SIDE, rng_seed=11)
        o_c = _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276, rng_seed=10)  # same as A

        c_a = _make_candidate(o_a, cell_dims, _NMOL, seed=0)
        c_b = _make_candidate(o_b, cell_dims, _NMOL, seed=1)
        c_c = _make_candidate(o_c, cell_dims, _NMOL, seed=2)

        # A's score WITH C present (duplicate structure)
        score_with_dup = diversity_score(c_a, [c_a, c_b, c_c])

        # A's score WITHOUT C (no duplicate)
        score_without_dup = diversity_score(c_a, [c_a, c_b])

        assert score_with_dup < score_without_dup, (
            f"Diversity should decrease with structural duplicate: "
            f"with_dup={score_with_dup:.4f} >= without_dup={score_without_dup:.4f}"
        )

    def test_unique_structure_more_diverse(self):
        """B (unique random structure) is more diverse than A in batch [A, A-like, B]."""
        cell_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])

        o_a = _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276, rng_seed=10)
        o_b = _random_oxygen_positions(_NMOL, _CELL_SIDE, rng_seed=11)
        o_c = _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276, rng_seed=10)  # same as A

        c_a = _make_candidate(o_a, cell_dims, _NMOL, seed=0)
        c_b = _make_candidate(o_b, cell_dims, _NMOL, seed=1)
        c_c = _make_candidate(o_c, cell_dims, _NMOL, seed=2)

        score_a = diversity_score(c_a, [c_a, c_b, c_c])
        score_b = diversity_score(c_b, [c_a, c_b, c_c])

        assert score_b > score_a, (
            f"B (unique structure) should be more diverse than A (has duplicate C): "
            f"B={score_b:.4f}, A={score_a:.4f}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestBUG04IdenticalStructures: Identical structures → same score
# ══════════════════════════════════════════════════════════════════════════════


class TestBUG04IdenticalStructures:
    """Verify that candidates with identical structures get the same diversity score.

    Old code gave both 1.0 (because both had unique seeds), but that was
    coincidental. New code should give same score because structural fingerprints
    are identical, and the score should be < 1.0 (they're similar to each other).
    """

    def test_identical_positions_same_score(self):
        """Two candidates with IDENTICAL positions (different seeds) → same score."""
        cell_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])
        o_pos = _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276, rng_seed=20)

        # Same positions, different seeds (mimicking generate_all sequential seeds)
        c1 = _make_candidate(o_pos.copy(), cell_dims, _NMOL, seed=0)
        c2 = _make_candidate(o_pos.copy(), cell_dims, _NMOL, seed=1)

        score1 = diversity_score(c1, [c1, c2])
        score2 = diversity_score(c2, [c1, c2])

        assert score1 == score2, (
            f"Identical structures should get same diversity score: "
            f"s1={score1:.6f}, s2={score2:.6f}"
        )

    def test_identical_structures_score_below_one(self):
        """Identical structures in same batch → score < 1.0 (they're similar)."""
        cell_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])
        o_pos = _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276, rng_seed=20)

        c1 = _make_candidate(o_pos.copy(), cell_dims, _NMOL, seed=0)
        c2 = _make_candidate(o_pos.copy(), cell_dims, _NMOL, seed=1)

        score1 = diversity_score(c1, [c1, c2])

        assert score1 < 1.0, (
            f"Identical structures should score < 1.0 (not maximally diverse): "
            f"score={score1:.6f}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestBUG04HistogramHelper: Unit tests for helper functions
# ══════════════════════════════════════════════════════════════════════════════


class TestBUG04HistogramHelper:
    """Unit tests for _compute_oo_histogram and _histogram_cosine_similarity."""

    def test_histogram_returns_correct_shape(self):
        """_compute_oo_histogram returns array of shape (n_bins,)."""
        cell_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])
        o_pos = _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276)
        c = _make_candidate(o_pos, cell_dims, _NMOL)

        hist = _compute_oo_histogram(c, n_bins=20)

        assert hist.shape == (20,), f"Expected shape (20,), got {hist.shape}"
        assert hist.dtype == np.float64

    def test_histogram_is_normalized(self):
        """Histogram sums to ~1.0 when O-O distances exist."""
        cell_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])
        o_pos = _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276)
        c = _make_candidate(o_pos, cell_dims, _NMOL)

        hist = _compute_oo_histogram(c, n_bins=20)

        assert hist.sum() == pytest.approx(1.0, abs=1e-10), (
            f"Normalized histogram should sum to 1.0, got {hist.sum()}"
        )

    def test_histogram_zeros_no_oxygen(self):
        """_compute_oo_histogram returns zeros when no O-O pairs exist."""
        cell_dims = np.array([2.0, 2.0, 2.0])
        # Only 1 oxygen atom → no O-O pairs
        pos = np.array([[0.276, 0, 0], [0.276 + 0.0957, 0, 0],
                        [0.276 - 0.0957, 0, 0], [0.276 + 0.0157, 0, 0]])
        names = ['OW', 'HW1', 'HW2', 'MW']
        c = Candidate(positions=pos, atom_names=names, cell=np.diag(cell_dims),
                      nmolecules=1, phase_id='ice_ih', seed=0)

        hist = _compute_oo_histogram(c, n_bins=15)

        assert hist.shape == (15,)
        assert np.all(hist == 0.0), "Single oxygen should produce zero histogram"

    def test_cosine_similarity_identical_histograms(self):
        """Identical histograms → cosine similarity = 1.0."""
        hist = np.array([0.4, 0.3, 0.2, 0.1])
        assert _histogram_cosine_similarity(hist, hist) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal_histograms(self):
        """Completely orthogonal histograms → cosine similarity = 0.0."""
        hist_a = np.array([0.5, 0.5, 0.0, 0.0])
        hist_b = np.array([0.0, 0.0, 0.5, 0.5])
        assert _histogram_cosine_similarity(hist_a, hist_b) == pytest.approx(0.0)

    def test_cosine_similarity_zero_norm_returns_zero(self):
        """Zero-norm histogram → cosine similarity = 0.0."""
        hist_a = np.array([0.5, 0.5])
        hist_z = np.zeros(2)
        assert _histogram_cosine_similarity(hist_a, hist_z) == 0.0
        assert _histogram_cosine_similarity(hist_z, hist_a) == 0.0
        assert _histogram_cosine_similarity(hist_z, hist_z) == 0.0

    def test_cosine_similarity_symmetric(self):
        """Cosine similarity is symmetric: sim(a,b) == sim(b,a)."""
        hist_a = np.array([0.5, 0.3, 0.2])
        hist_b = np.array([0.2, 0.5, 0.3])
        assert _histogram_cosine_similarity(hist_a, hist_b) == pytest.approx(
            _histogram_cosine_similarity(hist_b, hist_a)
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestBUG04EdgeCases: Edge cases for diversity_score
# ══════════════════════════════════════════════════════════════════════════════


class TestBUG04EdgeCases:
    """Edge cases: single candidate, no oxygen, single oxygen."""

    def test_single_candidate_returns_neutral(self):
        """Single candidate → diversity_score = 0.5 (neutral)."""
        cell_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])
        o_pos = _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276)
        c = _make_candidate(o_pos, cell_dims, _NMOL)

        assert diversity_score(c, [c]) == 0.5

    def test_two_identical_candidates_same_score(self):
        """Two identical candidates → both get same diversity score."""
        cell_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])
        o_pos = _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276, rng_seed=30)

        c1 = _make_candidate(o_pos.copy(), cell_dims, _NMOL, seed=0)
        c2 = _make_candidate(o_pos.copy(), cell_dims, _NMOL, seed=1)

        score1 = diversity_score(c1, [c1, c2])
        score2 = diversity_score(c2, [c1, c2])

        assert score1 == score2

    def test_no_oxygen_atoms_returns_neutral(self):
        """Candidate with no oxygen atoms → diversity_score = 0.5."""
        cell_dims = np.array([2.0, 2.0, 2.0])
        pos = np.array([[0.5, 0.5, 0.5]])
        names = ['HW1']  # No oxygen
        c_no_o = Candidate(positions=pos, atom_names=names, cell=np.diag(cell_dims),
                           nmolecules=1, phase_id='ice_ih', seed=0)

        # Need another candidate to form a batch
        o_pos = _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276)
        full_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])
        c_with_o = _make_candidate(o_pos, full_dims, _NMOL, seed=1)

        score = diversity_score(c_no_o, [c_no_o, c_with_o])
        assert score == 0.5, f"No-oxygen candidate should return 0.5, got {score}"

    def test_single_oxygen_atom_returns_neutral(self):
        """Candidate with only 1 oxygen atom → diversity_score = 0.5 (no O-O pairs)."""
        cell_dims = np.array([2.0, 2.0, 2.0])
        # Only 1 oxygen → no O-O pairs → zero histogram → 0.5
        pos = np.array([[0.276, 0, 0], [0.276 + 0.0957, 0, 0],
                        [0.276 - 0.0957, 0, 0], [0.276 + 0.0157, 0, 0]])
        names = ['OW', 'HW1', 'HW2', 'MW']
        c1 = Candidate(positions=pos, atom_names=names, cell=np.diag(cell_dims),
                        nmolecules=1, phase_id='ice_ih', seed=0)

        # Another candidate with many oxygens
        o_pos = _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276)
        full_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])
        c2 = _make_candidate(o_pos, full_dims, _NMOL, seed=1)

        score = diversity_score(c1, [c1, c2])
        assert score == 0.5, f"Single-oxygen candidate should return 0.5, got {score}"


# ══════════════════════════════════════════════════════════════════════════════
# TestBUG04Integration: Verify rank_candidates produces varied diversity scores
# ══════════════════════════════════════════════════════════════════════════════


class TestBUG04Integration:
    """Verify rank_candidates produces varied diversity scores (not all 1.0)."""

    def test_rank_candidates_diversity_not_all_one(self):
        """rank_candidates diversity_scores are NOT all 1.0."""
        cell_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])

        # 3 candidates with different structures
        structures = [
            _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276, rng_seed=0),
            _random_oxygen_positions(_NMOL, _CELL_SIDE, rng_seed=1),
            _clustered_oxygen_positions(_NMOL, _CELL_SIDE, rng_seed=2),
        ]
        candidates = []
        for i, o_pos in enumerate(structures):
            candidates.append(
                _make_candidate(o_pos, cell_dims, _NMOL, seed=i)
            )

        result = rank_candidates(candidates)

        diversity_scores = [rc.diversity_score for rc in result.ranked_candidates]
        assert not all(s == 1.0 for s in diversity_scores), (
            f"BUG-04 regression in rank_candidates: all diversity scores are 1.0"
        )

    def test_rank_candidates_diversity_range_varied(self):
        """diversity_range in metadata is NOT (1.0, 1.0)."""
        cell_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])

        structures = [
            _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276, rng_seed=0),
            _random_oxygen_positions(_NMOL, _CELL_SIDE, rng_seed=1),
            _clustered_oxygen_positions(_NMOL, _CELL_SIDE, rng_seed=2),
        ]
        candidates = []
        for i, o_pos in enumerate(structures):
            candidates.append(
                _make_candidate(o_pos, cell_dims, _NMOL, seed=i)
            )

        result = rank_candidates(candidates)

        d_min, d_max = result.scoring_metadata['diversity_range']
        assert not (d_min == 1.0 and d_max == 1.0), (
            f"diversity_range should not be (1.0, 1.0), got ({d_min}, {d_max})"
        )

    def test_rank_candidates_combined_scores_differ(self):
        """Combined scores differ between candidates (ranking is not arbitrary)."""
        cell_dims = np.array([_CELL_SIDE, _CELL_SIDE, _CELL_SIDE])

        # Use candidates with enough structural difference
        structures = [
            _ice_like_oxygen_positions(_NMOL, _CELL_SIDE, spacing=0.276, rng_seed=0),
            _random_oxygen_positions(_NMOL, _CELL_SIDE, rng_seed=1),
            _clustered_oxygen_positions(_NMOL, _CELL_SIDE, rng_seed=2),
        ]
        candidates = []
        for i, o_pos in enumerate(structures):
            candidates.append(
                _make_candidate(o_pos, cell_dims, _NMOL, seed=i)
            )

        result = rank_candidates(candidates)

        combined_scores = [rc.combined_score for rc in result.ranked_candidates]
        assert len(set(round(s, 8) for s in combined_scores)) > 1, (
            f"All combined scores identical — ranking is arbitrary: {combined_scores}"
        )
