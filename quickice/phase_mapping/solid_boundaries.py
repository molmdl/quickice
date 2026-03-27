"""
Solid-solid phase boundary curves using linear interpolation.

These boundaries connect triple points where three phases coexist.
Unlike IAPWS melting curves, solid-solid transitions use linear approximation
(MEDIUM confidence - exact equations not readily available in literature).
"""

from typing import Tuple
from quickice.phase_mapping.triple_points import TRIPLE_POINTS


def _linear_interpolate(T: float, T1: float, P1: float, T2: float, P2: float) -> float:
    """
    Linear interpolation between two endpoints.
    
    Args:
        T: Temperature to evaluate at
        T1, P1: First endpoint (temperature, pressure)
        T2, P2: Second endpoint (temperature, pressure)
    
    Returns:
        Pressure at temperature T
    """
    if T1 == T2:
        return P1  # Vertical line, return either pressure
    return P1 + (P2 - P1) * (T - T1) / (T2 - T1)


def ih_ii_boundary(T: float) -> float:
    """
    Ice Ih - Ice II boundary.
    Extends from Ih-II-III TP (238.55K, 212.9 MPa) to lower temperatures.
    Approximated with slight slope.
    """
    return 212.9 + 0.1 * (T - 238.55)


def ii_iii_boundary(T: float) -> float:
    """
    Ice II - Ice III boundary.
    Range: 238.55 K ≤ T ≤ 248.85 K
    """
    T1, P1 = TRIPLE_POINTS["Ih_II_III"]
    T2, P2 = TRIPLE_POINTS["II_III_V"]
    return _linear_interpolate(T, T1, P1, T2, P2)


def iii_v_boundary(T: float) -> float:
    """
    Ice III - Ice V boundary.
    Range: 248.85 K ≤ T ≤ 256.165 K
    """
    T1, P1 = TRIPLE_POINTS["II_III_V"]
    T2, P2 = TRIPLE_POINTS["III_V_Liquid"]
    return _linear_interpolate(T, T1, P1, T2, P2)


def ii_v_boundary(T: float) -> float:
    """
    Ice II - Ice V boundary.
    Range: 218.95 K ≤ T ≤ 248.85 K
    """
    T1, P1 = TRIPLE_POINTS["II_V_VI"]
    T2, P2 = TRIPLE_POINTS["II_III_V"]
    return _linear_interpolate(T, T1, P1, T2, P2)


def v_vi_boundary(T: float) -> float:
    """
    Ice V - Ice VI boundary.
    Range: 218.95 K ≤ T ≤ 273.31 K
    """
    T1, P1 = TRIPLE_POINTS["II_V_VI"]
    T2, P2 = TRIPLE_POINTS["V_VI_Liquid"]
    return _linear_interpolate(T, T1, P1, T2, P2)


def vi_vii_boundary(T: float) -> float:
    """
    Ice VI - Ice VII boundary.
    Range: 278.0 K ≤ T ≤ 354.75 K
    """
    T1, P1 = TRIPLE_POINTS["VI_VII_VIII"]
    T2, P2 = TRIPLE_POINTS["VI_VII_Liquid"]
    return _linear_interpolate(T, T1, P1, T2, P2)


def solid_boundary(boundary: str, T: float) -> float:
    """
    Unified solid boundary function.
    
    Args:
        boundary: One of "Ih-II", "II-III", "III-V", "II-V", "V-VI", "VI-VII"
        T: Temperature in K
    
    Returns:
        Pressure at boundary in MPa
    """
    boundaries = {
        "Ih-II": ih_ii_boundary,
        "II-III": ii_iii_boundary,
        "III-V": iii_v_boundary,
        "II-V": ii_v_boundary,
        "V-VI": v_vi_boundary,
        "VI-VII": vi_vii_boundary,
    }
    if boundary not in boundaries:
        raise ValueError(f"Unknown boundary: {boundary}. Available: {list(boundaries.keys())}")
    return boundaries[boundary](T)


# VII-VIII ordering transition (temperature threshold, not pressure boundary)
VII_VIII_ORDERING_TEMP = 278.0  # K
