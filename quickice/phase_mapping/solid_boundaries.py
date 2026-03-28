"""
Solid-solid phase boundary curves using linear interpolation.

These boundaries connect triple points where three phases coexist.
Unlike IAPWS melting curves, solid-solid transitions use linear approximation
(MEDIUM confidence - exact equations not readily available in literature).

Additional boundaries for proton-ordered phases (XI, IX, XV) and
symmetrized hydrogen bond phase (X).
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


def xi_boundary(T: float) -> float:
    """
    Ice XI boundary: T < 72K at low P.
    
    Ice XI is the proton-ordered form of Ice Ih, stable at low temperatures.
    Returns 0.1 MPa (essentially atmospheric) if T < 72K.
    Returns very high pressure (no Ice XI) otherwise.
    """
    return 0.1 if T < 72.0 else 1e9


def ix_boundary(T: float) -> float:
    """
    Ice IX boundary: forms from Ice III at T < 140K.
    
    Ice IX is the proton-ordered form of Ice III.
    Ice IX exists in narrow P band: 200-400 MPa at T < 140K.
    Returns the lower pressure boundary for Ice IX.
    """
    if T >= 140.0:
        return 1e9  # No Ice IX at T >= 140K
    # Linear: P decreases slightly with T in Ice IX region
    # At T=140K, P=200 MPa (boundary with Ice III)
    # At T=100K, P=250 MPa (extrapolated)
    return 200.0 + 1.25 * (140.0 - T)


def x_boundary(T: float) -> float:
    """
    Ice X boundary: interpolates between triple points.
    
    Uses:
    - VII_VIII_X at (100K, 62000 MPa) for T <= 100K
    - VII_X_Transition at (300K, 30000 MPa) for T = 300K
    - VII_X_Liquid at (1000K, 43000 MPa) for T >= 1000K
    
    Linear interpolation between these points.
    """
    if T <= 100.0:
        return 62000.0  # VII_VIII_X triple point
    elif T <= 300.0:
        # Linear interpolation: (100K, 62000) to (300K, 30000)
        return 62000.0 + (30000.0 - 62000.0) * (T - 100.0) / (300.0 - 100.0)
    elif T <= 1000.0:
        # Linear interpolation: (300K, 30000) to (1000K, 43000)
        return 30000.0 + (43000.0 - 30000.0) * (T - 300.0) / (1000.0 - 300.0)
    else:
        return 43000.0 + 10.0 * (T - 1000.0)  # Slight increase at very high T


def xv_boundary(T: float) -> float:
    """
    Ice XV boundary: proton-ordered Ice VI at T=80-108K, P≈1.1 GPa.
    
    Ice XV is the proton-ordered form of Ice VI.
    Returns pressure threshold for Ice XV at temperature T.
    """
    if not (80.0 <= T <= 108.0):
        return 1e9  # No Ice XV outside temperature range
    # Ice XV exists around 1.1 GPa in this T range
    # Narrow pressure band, approximate as ~1100 MPa
    return 1100.0


def solid_boundary(boundary: str, T: float) -> float:
    """
    Unified solid boundary function.
    
    Args:
        boundary: One of "Ih-II", "II-III", "III-V", "II-V", "V-VI", "VI-VII",
                        "XI", "IX", "X", "XV"
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
        "XI": xi_boundary,
        "IX": ix_boundary,
        "X": x_boundary,
        "XV": xv_boundary,
    }
    if boundary not in boundaries:
        raise ValueError(f"Unknown boundary: {boundary}. Available: {list(boundaries.keys())}")
    return boundaries[boundary](T)


# VII-VIII ordering transition (temperature threshold, not pressure boundary)
VII_VIII_ORDERING_TEMP = 278.0  # K
