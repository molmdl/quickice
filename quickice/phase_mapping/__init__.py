"""
Phase mapping module for QuickIce.

This module provides functionality to map temperature and pressure conditions
to the appropriate ice polymorph phase.

Key components:
- Phase boundary data (ice_phases.json)
- Error types for phase mapping failures
- Lookup functions for T,P → ice phase mapping
"""

from quickice.phase_mapping.errors import (
    PhaseMappingError,
    UnknownPhaseError,
)
from quickice.phase_mapping.lookup import (
    lookup_phase,
    IcePhaseLookup,
)

__all__ = [
    "PhaseMappingError",
    "UnknownPhaseError",
    "lookup_phase",
    "IcePhaseLookup",
]
