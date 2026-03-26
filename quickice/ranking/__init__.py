"""Ice structure candidate ranking module."""

from quickice.ranking.types import (
    RankedCandidate,
    RankingResult,
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
    # Main API
    "rank_candidates",
    # Individual scorers (for advanced use)
    "energy_score",
    "density_score",
    "diversity_score",
    "normalize_scores",
]
