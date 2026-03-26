"""
Ice phase boundary data module.

Contains IAPWS-certified phase boundary definitions for ice polymorphs.
"""

from .ice_boundaries import (
    TRIPLE_POINTS,
    MELTING_CURVE_COEFFICIENTS,
    PHASE_POLYGONS,
    get_melting_pressure,
    get_triple_point,
    get_phase_polygon,
    is_temperature_in_melting_range,
)

__all__ = [
    "TRIPLE_POINTS",
    "MELTING_CURVE_COEFFICIENTS",
    "PHASE_POLYGONS",
    "get_melting_pressure",
    "get_triple_point",
    "get_phase_polygon",
    "is_temperature_in_melting_range",
]
