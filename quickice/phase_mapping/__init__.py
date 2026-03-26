"""
Phase mapping module for QuickIce.

This module provides functionality to map temperature and pressure conditions
to the appropriate ice polymorph phase.

Key components:
- Phase boundary data (ice_phases.json)
- Error types for phase mapping failures
- Lookup functions (to be implemented in subsequent plans)
"""

from quickice.phase_mapping.errors import (
    PhaseMappingError,
    UnknownPhaseError,
)

__all__ = [
    "PhaseMappingError",
    "UnknownPhaseError",
]
