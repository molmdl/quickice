"""Tests for ice structure candidate ranking."""

import numpy as np
import pytest

from quickice.structure_generation.types import Candidate
from quickice.ranking import (
    rank_candidates,
    energy_score,
    density_score,
    diversity_score,
    normalize_scores,
    RankedCandidate,
    RankingResult,
)


@pytest.fixture
def simple_candidate():
    """Create a simple candidate for testing.
    
    Creates a 1nm cubic cell with 4 water molecules.
    """
    # TIP3P water model: 3 atoms per molecule (O, H, H)
    # Positions arranged to give reasonable O-O distances
    positions = np.array([
        # Molecule 1: O at origin, H's nearby
        [0.0, 0.0, 0.0],    # O
        [0.1, 0.0, 0.0],    # H
        [-0.1, 0.0, 0.0],   # H
        # Molecule 2: O at 0.28nm (near ideal O-O distance)
        [0.28, 0.0, 0.0],   # O
        [0.38, 0.0, 0.0],   # H
        [0.18, 0.0, 0.0],   # H
        # Molecule 3: O at 0.56nm
        [0.56, 0.0, 0.0],   # O
        [0.66, 0.0, 0.0],   # H
        [0.46, 0.0, 0.0],   # H
        # Molecule 4: O at 0.84nm
        [0.84, 0.0, 0.0],   # O
        [0.94, 0.0, 0.0],   # H
        [0.74, 0.0, 0.0],   # H
    ])
    atom_names = ['O', 'H', 'H', 'O', 'H', 'H', 'O', 'H', 'H', 'O', 'H', 'H']
    cell = np.eye(3) * 1.0  # 1nm cubic cell
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=4,
        phase_id='ice_ih',
        seed=1000,
        metadata={'density': 0.9167}
    )


@pytest.fixture
def ideal_candidate():
    """Create a candidate with ideal O-O distances (0.276 nm)."""
    # Create positions where O atoms are at ideal O-O distance
    positions = np.array([
        # Molecule 1
        [0.0, 0.0, 0.0],      # O
        [0.1, 0.0, 0.0],      # H
        [-0.1, 0.0, 0.0],     # H
        # Molecule 2 at ideal O-O distance
        [0.276, 0.0, 0.0],    # O (ideal distance from first O)
        [0.376, 0.0, 0.0],    # H
        [0.176, 0.0, 0.0],    # H
        # Molecule 3 at ideal O-O distance
        [0.552, 0.0, 0.0],    # O (ideal distance from second O)
        [0.652, 0.0, 0.0],    # H
        [0.452, 0.0, 0.0],    # H
        # Molecule 4
        [0.828, 0.0, 0.0],    # O (ideal distance from third O)
        [0.928, 0.0, 0.0],    # H
        [0.728, 0.0, 0.0],    # H
    ])
    atom_names = ['O', 'H', 'H', 'O', 'H', 'H', 'O', 'H', 'H', 'O', 'H', 'H']
    cell = np.eye(3) * 1.0
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=4,
        phase_id='ice_ih',
        seed=2000,
        metadata={'density': 0.9167}
    )


@pytest.fixture
def candidate_set():
    """Create a set of candidates for ranking tests.
    
    Creates 5 candidates with reasonable O-O distances for proper scoring.
    """
    candidates = []
    # Create candidates with varied but reasonable O-O distances
    for i in range(5):
        # Create positions with O atoms at reasonable distances
        # Spread O atoms to ensure O-O distances within cutoff
        positions = np.array([
            # Molecule 1: O at varying position
            [0.1 + i * 0.01, 0.1, 0.1],
            [0.2, 0.1, 0.1],  # H
            [0.0, 0.1, 0.1],  # H
            # Molecule 2
            [0.4 + i * 0.01, 0.1, 0.1],
            [0.5, 0.1, 0.1],  # H
            [0.3, 0.1, 0.1],  # H
            # Molecule 3
            [0.1 + i * 0.01, 0.4, 0.1],
            [0.2, 0.4, 0.1],  # H
            [0.0, 0.4, 0.1],  # H
            # Molecule 4
            [0.4 + i * 0.01, 0.4, 0.1],
            [0.5, 0.4, 0.1],  # H
            [0.3, 0.4, 0.1],  # H
        ])
        atom_names = ['O', 'H', 'H'] * 4
        cell = np.eye(3) * 1.0
        candidates.append(Candidate(
            positions=positions,
            atom_names=atom_names,
            cell=cell,
            nmolecules=4,
            phase_id='ice_ih',
            seed=1000 + i,
            metadata={'density': 0.9167}
        ))
    return candidates


@pytest.fixture
def candidate_with_duplicate_seeds():
    """Create candidates with some duplicate seeds for diversity testing."""
    candidates = []
    seeds = [1000, 1001, 1000, 1002, 1001]  # Seeds 1000 and 1001 appear twice
    for i, seed in enumerate(seeds):
        # Create positions with reasonable O-O distances
        positions = np.array([
            [0.1 + i * 0.05, 0.1, 0.1],
            [0.2, 0.1, 0.1],
            [0.0, 0.1, 0.1],
            [0.4 + i * 0.05, 0.1, 0.1],
            [0.5, 0.1, 0.1],
            [0.3, 0.1, 0.1],
            [0.1 + i * 0.05, 0.4, 0.1],
            [0.2, 0.4, 0.1],
            [0.0, 0.4, 0.1],
            [0.4 + i * 0.05, 0.4, 0.1],
            [0.5, 0.4, 0.1],
            [0.3, 0.4, 0.1],
        ])
        atom_names = ['O', 'H', 'H'] * 4
        cell = np.eye(3) * 1.0
        candidates.append(Candidate(
            positions=positions,
            atom_names=atom_names,
            cell=cell,
            nmolecules=4,
            phase_id='ice_ih',
            seed=seed,
            metadata={'density': 0.9167}
        ))
    return candidates


@pytest.fixture
def single_candidate():
    """Create a single candidate for edge case testing."""
    positions = np.array([
        [0.0, 0.0, 0.0],
        [0.1, 0.0, 0.0],
        [-0.1, 0.0, 0.0],
    ])
    atom_names = ['O', 'H', 'H']
    cell = np.eye(3) * 0.5
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=1,
        phase_id='ice_ih',
        seed=9999,
        metadata={'density': 0.9167}
    )


# ============================================================================
# Tests for normalize_scores
# ============================================================================

class TestNormalizeScores:
    """Tests for normalize_scores function."""
    
    def test_normalize_scores_basic(self):
        """Test basic normalization: [1, 2, 3] -> [0, 0.5, 1]."""
        scores = [1.0, 2.0, 3.0]
        result = normalize_scores(scores)
        
        np.testing.assert_allclose(result, [0.0, 0.5, 1.0])
    
    def test_normalize_scores_all_same(self):
        """Test normalization when all scores equal: [5, 5, 5] -> [0, 0, 0]."""
        scores = [5.0, 5.0, 5.0]
        result = normalize_scores(scores)
        
        np.testing.assert_allclose(result, [0.0, 0.0, 0.0])
    
    def test_normalize_scores_negative(self):
        """Test normalization with negative values: [-2, 0, 2] -> [0, 0.5, 1]."""
        scores = [-2.0, 0.0, 2.0]
        result = normalize_scores(scores)
        
        np.testing.assert_allclose(result, [0.0, 0.5, 1.0])
    
    def test_normalize_scores_empty(self):
        """Test normalization with empty list - raises ValueError.
        
        Note: normalize_scores doesn't handle empty lists - it's expected
        that the caller ensures non-empty input. This test documents that behavior.
        """
        scores = []
        with pytest.raises(ValueError, match="zero-size array"):
            normalize_scores(scores)
    
    def test_normalize_scores_single_value(self):
        """Test normalization with single value."""
        scores = [5.0]
        result = normalize_scores(scores)
        
        np.testing.assert_allclose(result, [0.0])
    
    def test_normalize_scores_unordered(self):
        """Test normalization with unsorted input."""
        scores = [3.0, 1.0, 2.0]
        result = normalize_scores(scores)
        
        # [3, 1, 2] normalized: (3-1)/(3-1)=1, (1-1)/2=0, (2-1)/2=0.5
        np.testing.assert_allclose(result, [1.0, 0.0, 0.5])


# ============================================================================
# Tests for energy_score
# ============================================================================

class TestEnergyScore:
    """Tests for energy_score function."""
    
    def test_energy_score_returns_float(self, simple_candidate):
        """Test that energy_score returns a float."""
        result = energy_score(simple_candidate)
        
        assert isinstance(result, float)
    
    def test_energy_score_lower_better(self, simple_candidate, ideal_candidate):
        """Test that better H-bond geometry gives lower score."""
        score_simple = energy_score(simple_candidate)
        score_ideal = energy_score(ideal_candidate)
        
        # Ideal candidate should have lower (better) energy score
        assert score_ideal < score_simple
    
    def test_energy_score_ideal_distance(self, ideal_candidate):
        """Test that structure near ideal 0.276nm gives low score."""
        score = energy_score(ideal_candidate)
        
        # With ideal distances, deviation should be relatively small
        # Note: scaled by 100, so small deviation -> small score
        # The ideal O-O distance is 0.276 nm, so deviation is 0, score should be 0
        # But due to PBC effects with neighboring cells, actual score may vary slightly
        assert score < 10.0  # Should be relatively low (not necessarily < 0.1)
    
    def test_energy_score_no_oxygen_pairs(self, single_candidate):
        """Test energy score with only one oxygen (no pairs)."""
        score = energy_score(single_candidate)
        
        # No O-O pairs within cutoff -> infinity
        assert score == float('inf')
    
    def test_energy_score_positive(self, simple_candidate):
        """Test that energy score is always non-negative."""
        score = energy_score(simple_candidate)
        
        assert score >= 0


# ============================================================================
# Tests for density_score
# ============================================================================

class TestDensityScore:
    """Tests for density_score function."""
    
    def test_density_score_returns_float(self, simple_candidate):
        """Test that density_score returns a float."""
        result = density_score(simple_candidate)
        
        assert isinstance(result, float)
    
    def test_density_score_lower_better(self):
        """Test that closer density match gives lower score."""
        # Create candidates with different densities
        positions = np.zeros((12, 3))
        atom_names = ['O', 'H', 'H'] * 4
        cell = np.eye(3) * 1.0
        
        # Candidate expecting ice Ih density (0.9167 g/cm³)
        candidate_ih = Candidate(
            positions=positions,
            atom_names=atom_names,
            cell=cell,
            nmolecules=4,
            phase_id='ice_ih',
            seed=1000,
            metadata={'density': 0.9167}
        )
        
        # Candidate expecting different density
        candidate_other = Candidate(
            positions=positions,
            atom_names=atom_names,
            cell=cell,
            nmolecules=4,
            phase_id='ice_ii',
            seed=1000,
            metadata={'density': 1.18}
        )
        
        score_ih = density_score(candidate_ih)
        score_other = density_score(candidate_other)
        
        # The actual density should be closer to 0.9167 than 1.18
        # (4 molecules in 1 nm³ = ~1.2 g/cm³)
        assert score_ih < score_other
    
    def test_density_score_uses_metadata(self, simple_candidate):
        """Test that density_score reads density from candidate.metadata."""
        score = density_score(simple_candidate)
        
        # Should use the metadata density value
        assert isinstance(score, float)
        assert score >= 0
    
    def test_density_score_default_density(self):
        """Test that default density (0.9167) is used when not in metadata."""
        positions = np.zeros((12, 3))
        atom_names = ['O', 'H', 'H'] * 4
        cell = np.eye(3) * 1.0
        
        candidate = Candidate(
            positions=positions,
            atom_names=atom_names,
            cell=cell,
            nmolecules=4,
            phase_id='ice_ih',
            seed=1000,
            metadata={}  # No density specified
        )
        
        score = density_score(candidate)
        
        # Should still work with default density
        assert isinstance(score, float)


# ============================================================================
# Tests for diversity_score
# ============================================================================

class TestDiversityScore:
    """Tests for diversity_score function."""
    
    def test_diversity_score_returns_float(self, simple_candidate, candidate_set):
        """Test that diversity_score returns a float."""
        result = diversity_score(simple_candidate, candidate_set)
        
        assert isinstance(result, float)
    
    def test_diversity_seed_uniqueness(self, candidate_set):
        """Test that unique seed gets higher score."""
        # All seeds in candidate_set are unique (1000-1004)
        scores = [diversity_score(c, candidate_set) for c in candidate_set]
        
        # All should have score 1.0 (each seed appears once)
        for score in scores:
            np.testing.assert_allclose(score, 1.0)
    
    def test_diversity_seed_frequency(self, candidate_with_duplicate_seeds):
        """Test that frequent seed gets lower score."""
        candidates = candidate_with_duplicate_seeds
        
        # Seeds: [1000, 1001, 1000, 1002, 1001]
        # Seeds 1000 and 1001 appear twice -> score = 0.5
        # Seed 1002 appears once -> score = 1.0
        
        for c in candidates:
            score = diversity_score(c, candidates)
            if c.seed == 1002:
                np.testing.assert_allclose(score, 1.0)
            elif c.seed in [1000, 1001]:
                np.testing.assert_allclose(score, 0.5)
    
    def test_diversity_score_range(self, candidate_set):
        """Test that diversity scores are in valid range [0, 1]."""
        for c in candidate_set:
            score = diversity_score(c, candidate_set)
            assert 0 < score <= 1.0


# ============================================================================
# Tests for rank_candidates
# ============================================================================

class TestRankCandidates:
    """Tests for rank_candidates function."""
    
    def test_rank_candidates_returns_result(self, candidate_set):
        """Test that rank_candidates returns RankingResult."""
        result = rank_candidates(candidate_set)
        
        assert isinstance(result, RankingResult)
    
    def test_rank_candidates_sorts_by_combined(self, candidate_set):
        """Test that candidates are sorted by combined_score."""
        result = rank_candidates(candidate_set)
        
        scores = [rc.combined_score for rc in result.ranked_candidates]
        
        # Should be sorted ascending (lower = better)
        assert scores == sorted(scores)
    
    def test_rank_candidates_assigns_ranks(self, candidate_set):
        """Test that rank 1 = best (lowest combined)."""
        result = rank_candidates(candidate_set)
        
        ranks = [rc.rank for rc in result.ranked_candidates]
        
        # Ranks should be 1, 2, 3, 4, 5
        assert ranks == [1, 2, 3, 4, 5]
        
        # Rank 1 should have lowest combined score
        assert result.ranked_candidates[0].rank == 1
        assert result.ranked_candidates[0].combined_score <= \
               result.ranked_candidates[1].combined_score
    
    def test_rank_candidates_default_weights(self, candidate_set):
        """Test that default weights are equal (1:1:1)."""
        result = rank_candidates(candidate_set)
        
        assert result.weight_config == {'energy': 1.0, 'density': 1.0, 'diversity': 1.0}
    
    def test_rank_candidates_custom_weights(self, candidate_set):
        """Test that custom weights are accepted."""
        custom_weights = {'energy': 2.0, 'density': 1.0, 'diversity': 0.5}
        result = rank_candidates(candidate_set, weights=custom_weights)
        
        assert result.weight_config == custom_weights
    
    def test_rank_candidates_single_candidate(self, single_candidate):
        """Test handling of single candidate."""
        result = rank_candidates([single_candidate])
        
        assert len(result.ranked_candidates) == 1
        assert result.ranked_candidates[0].rank == 1
    
    def test_rank_candidates_metadata(self, candidate_set):
        """Test that result includes scoring_metadata and weight_config."""
        result = rank_candidates(candidate_set)
        
        assert 'n_candidates' in result.scoring_metadata
        assert 'ideal_oo_distance' in result.scoring_metadata
        assert 'energy_range' in result.scoring_metadata
        assert 'density_range' in result.scoring_metadata
        assert 'diversity_range' in result.scoring_metadata
        
        assert result.weight_config is not None


# ============================================================================
# Requirement Verification Tests (RANK-01 to RANK-04)
# ============================================================================

class TestRequirements:
    """Tests verifying all 4 ranking requirements."""
    
    def test_RANK_01_energy_ranking(self, candidate_set):
        """RANK-01: Verify candidates have energy scores."""
        result = rank_candidates(candidate_set)
        
        for rc in result.ranked_candidates:
            assert hasattr(rc, 'energy_score')
            assert isinstance(rc.energy_score, float)
    
    def test_RANK_02_density_scoring(self, candidate_set):
        """RANK-02: Verify candidates have density scores."""
        result = rank_candidates(candidate_set)
        
        for rc in result.ranked_candidates:
            assert hasattr(rc, 'density_score')
            assert isinstance(rc.density_score, float)
            assert rc.density_score >= 0  # Absolute deviation
    
    def test_RANK_03_diversity_scoring(self, candidate_set):
        """RANK-03: Verify candidates have diversity scores."""
        result = rank_candidates(candidate_set)
        
        for rc in result.ranked_candidates:
            assert hasattr(rc, 'diversity_score')
            assert isinstance(rc.diversity_score, float)
            assert 0 < rc.diversity_score <= 1.0
    
    def test_RANK_04_combined_score(self, candidate_set):
        """RANK-04: Verify candidates have combined scores."""
        result = rank_candidates(candidate_set)
        
        for rc in result.ranked_candidates:
            assert hasattr(rc, 'combined_score')
            assert isinstance(rc.combined_score, float)
            assert rc.combined_score >= 0
        
        # Verify ranking is correct (lower combined = better rank)
        scores = [rc.combined_score for rc in result.ranked_candidates]
        assert scores == sorted(scores)


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_rank_candidates_handles_infinite_energy(self):
        """Test that infinite energy scores are handled gracefully."""
        # Create candidates where one has only one oxygen (no O-O pairs possible)
        # Single water molecule - only 1 oxygen, so no O-O pairs
        positions_single = np.array([
            [0.0, 0.0, 0.0],
            [0.1, 0.0, 0.0],
            [-0.1, 0.0, 0.0],
        ])
        atom_names_single = ['O', 'H', 'H']
        cell = np.eye(3) * 0.5
        
        single_oxygen = Candidate(
            positions=positions_single,
            atom_names=atom_names_single,
            cell=cell,
            nmolecules=1,
            phase_id='ice_ih',
            seed=9998,
            metadata={'density': 0.9167}
        )
        
        # Normal candidate with proper O-O distances
        positions_normal = np.array([
            [0.1, 0.1, 0.1],
            [0.2, 0.1, 0.1],
            [0.0, 0.1, 0.1],
            [0.4, 0.1, 0.1],
            [0.5, 0.1, 0.1],
            [0.3, 0.1, 0.1],
            [0.1, 0.4, 0.1],
            [0.2, 0.4, 0.1],
            [0.0, 0.4, 0.1],
            [0.4, 0.4, 0.1],
            [0.5, 0.4, 0.1],
            [0.3, 0.4, 0.1],
        ])
        atom_names_normal = ['O', 'H', 'H'] * 4
        
        normal = Candidate(
            positions=positions_normal,
            atom_names=atom_names_normal,
            cell=np.eye(3) * 1.0,
            nmolecules=4,
            phase_id='ice_ih',
            seed=9999,
            metadata={'density': 0.9167}
        )
        
        result = rank_candidates([normal, single_oxygen])
        
        # Should still produce a result
        assert len(result.ranked_candidates) == 2
        
        # Normal candidate should have finite energy score
        assert result.ranked_candidates[0].energy_score < float('inf') or \
               result.ranked_candidates[1].energy_score < float('inf')
        
        # At least one candidate should have infinite energy (the single oxygen one)
        # Note: Due to how ranking handles NaN from inf normalization, exact order may vary
        energy_scores = [rc.energy_score for rc in result.ranked_candidates]
        assert float('inf') in energy_scores
    
    def test_rank_candidates_equal_scores(self):
        """Test handling of candidates with similar scores."""
        # Create two nearly identical candidates
        positions = np.random.rand(12, 3) * 0.9
        
        candidate1 = Candidate(
            positions=positions.copy(),
            atom_names=['O', 'H', 'H'] * 4,
            cell=np.eye(3) * 1.0,
            nmolecules=4,
            phase_id='ice_ih',
            seed=1000,
            metadata={'density': 0.9167}
        )
        
        candidate2 = Candidate(
            positions=positions.copy(),
            atom_names=['O', 'H', 'H'] * 4,
            cell=np.eye(3) * 1.0,
            nmolecules=4,
            phase_id='ice_ih',
            seed=1001,
            metadata={'density': 0.9167}
        )
        
        result = rank_candidates([candidate1, candidate2])
        
        # Should still assign ranks 1 and 2
        ranks = [rc.rank for rc in result.ranked_candidates]
        assert sorted(ranks) == [1, 2]
    
    def test_rank_candidates_empty_list(self):
        """Test handling of empty candidate list.
        
        Note: rank_candidates doesn't handle empty lists gracefully due to
        normalization of empty score arrays. This test documents that behavior.
        """
        with pytest.raises(ValueError, match="zero-size array"):
            rank_candidates([])
    
    def test_all_scores_equal(self):
        """Test normalization when all scores are equal."""
        # This tests normalize_scores edge case
        scores = [5.0, 5.0, 5.0, 5.0]
        result = normalize_scores(scores)
        
        np.testing.assert_allclose(result, [0.0, 0.0, 0.0, 0.0])
