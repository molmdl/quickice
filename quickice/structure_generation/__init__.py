"""Structure generation module for QuickIce.

This module provides the mapping layer between QuickIce phase IDs
and GenIce lattice names, including supercell calculation logic.
"""

from quickice.structure_generation.errors import (
    StructureGenerationError,
    UnsupportedPhaseError,
)
from quickice.structure_generation.mapper import (
    PHASE_TO_GENICE,
    UNIT_CELL_MOLECULES,
    calculate_supercell,
    get_genice_lattice_name,
)
from quickice.structure_generation.types import Candidate, GenerationResult

__all__ = [
    # Types
    "Candidate",
    "GenerationResult",
    # Errors
    "StructureGenerationError",
    "UnsupportedPhaseError",
    # Mapper functions
    "get_genice_lattice_name",
    "calculate_supercell",
    # Constants
    "PHASE_TO_GENICE",
    "UNIT_CELL_MOLECULES",
]
