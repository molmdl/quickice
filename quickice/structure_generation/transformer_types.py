"""Data types for triclinic cell transformation."""

from dataclasses import dataclass
from enum import Enum

import numpy as np


class TransformationStatus(Enum):
    """Status of triclinic transformation.

    Attributes:
        SKIPPED: Cell was already orthogonal, no transformation needed.
        TRANSFORMED: Cell was successfully transformed to orthogonal.
        FAILED: Transformation attempted but failed.
    """

    SKIPPED = "skipped"
    TRANSFORMED = "transformed"
    FAILED = "failed"


@dataclass
class TransformationResult:
    """Result of triclinic transformation attempt.

    Attributes:
        status: Whether transformation was performed, skipped, or failed.
        cell: The resulting cell vectors (3, 3) in nm, stored as ROW vectors.
        positions: Atom positions (N, 3) in nm.
        multiplier: Number of times the original cell was replicated.
        message: Human-readable description of what happened.
    """

    status: TransformationStatus
    cell: np.ndarray
    positions: np.ndarray
    multiplier: int
    message: str
