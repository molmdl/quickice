"""Piece mode: ice crystal embedded in water box.

Centers an ice crystal inside a water box. The ice piece dimensions
are derived from the candidate cell, and overlapping water molecules
are removed.
"""

import numpy as np

from quickice.structure_generation.types import Candidate, InterfaceConfig, InterfaceStructure
from quickice.structure_generation.errors import InterfaceGenerationError


def assemble_piece(candidate: Candidate, config: InterfaceConfig) -> InterfaceStructure:
    """Assemble piece interface structure: ice centered in water box.

    Placeholder implementation - will be completed in Task 2.
    """
    raise InterfaceGenerationError(
        "Piece mode not yet implemented. This is a placeholder.",
        mode="piece"
    )
