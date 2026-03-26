"""Data types for ranking ice structure candidates."""

from dataclasses import dataclass, field
from typing import Any

from quickice.structure_generation.types import Candidate


@dataclass
class RankedCandidate:
    """A candidate with its ranking scores.

    Attributes:
        candidate: Reference to the original Candidate from Phase 3
        energy_score: Raw energy score (lower = better)
        density_score: Raw density deviation (lower = better)
        diversity_score: Diversity score (higher = more diverse)
        combined_score: Normalized combined score (lower = better)
        rank: Final rank (1 = best)
    """

    candidate: Candidate
    energy_score: float
    density_score: float
    diversity_score: float
    combined_score: float = 0.0
    rank: int = 0


@dataclass
class RankingResult:
    """Complete ranking output for a set of candidates.

    Attributes:
        ranked_candidates: List of RankedCandidate sorted by combined_score
        scoring_metadata: Info like ideal_oo_distance, n_candidates, etc.
        weight_config: Weights used for combining scores
    """

    ranked_candidates: list[RankedCandidate]
    scoring_metadata: dict[str, Any] = field(default_factory=dict)
    weight_config: dict[str, float] = field(default_factory=dict)
