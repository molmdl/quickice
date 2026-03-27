"""
QuickIce Phase Mapping Module

Curve-based ice phase identification using IAPWS R14-08 melting curves
and linear interpolation for solid-solid boundaries.
"""

from quickice.phase_mapping.lookup import lookup_phase, IcePhaseLookup
from quickice.phase_mapping.errors import PhaseMappingError, UnknownPhaseError
from quickice.phase_mapping.triple_points import TRIPLE_POINTS, get_triple_point
from quickice.phase_mapping.melting_curves import melting_pressure
from quickice.phase_mapping.solid_boundaries import solid_boundary

__all__ = [
    "lookup_phase",
    "IcePhaseLookup",
    "PhaseMappingError",
    "UnknownPhaseError",
    "TRIPLE_POINTS",
    "get_triple_point",
    "melting_pressure",
    "solid_boundary",
]
