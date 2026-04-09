"""Ice structure candidate ranking module."""

from quickice.ranking.types import (
    RankedCandidate,
    RankingResult,
    ScoringConfig,
)

from quickice.ranking.scorer import (
    rank_candidates,
    # Also export individual scoring functions for advanced use
    energy_score,
    density_score,
    diversity_score,
    normalize_scores,
)

__all__ = [
    # Types
    "RankedCandidate",
    "RankingResult",
    "ScoringConfig",
    # Main API
    "rank_candidates",
    # Individual scorers (for advanced use)
    "energy_score",
    "density_score",
    "diversity_score",
    "normalize_scores",
]
