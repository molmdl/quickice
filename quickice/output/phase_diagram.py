"""Phase diagram generator for ice polymorph visualization.

Generates publication-quality phase diagrams using curve-based boundaries
from Phase 2 melting_curves and solid_boundaries modules (single source of truth).

Outputs PNG, SVG, and text data files.
"""

import logging
from pathlib import Path
from typing import Tuple, List

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon

from quickice.phase_mapping import (
    melting_pressure,
    solid_boundary,
    TRIPLE_POINTS,
    get_triple_point,
)
from quickice.phase_mapping.solid_boundaries import (
    ih_ii_boundary,
    ii_iii_boundary,
    iii_v_boundary,
    ii_v_boundary,
    v_vi_boundary,
    vi_vii_boundary,
    vii_viii_boundary,
    x_boundary,
    VII_VIII_ORDERING_TEMP,
)


# Shared boundary sampling cache to ensure aligned vertices
_SHARED_BOUNDARY_CACHE = {}


def _get_shared_boundary_vertices(boundary_name: str, T_min: float, T_max: float, n_points: int = 50) -> List[Tuple[float, float]]:
    """Get pre-computed vertices for a shared boundary curve.
    
    Uses a cache to ensure all polygons sharing a boundary use the same vertices,
    preventing geometric overlaps caused by different sampling.
    
    Args:
        boundary_name: Name of boundary function (e.g., 'x_boundary', 'vii_viii_boundary')
        T_min: Minimum temperature
        T_max: Maximum temperature
        n_points: Number of points (used for cache key)
        
    Returns:
        List of (T, P) tuples along the boundary
    """
    # Get the boundary function
    boundary_funcs = {
        'ih_ii_boundary': ih_ii_boundary,
        'ii_iii_boundary': ii_iii_boundary,
        'iii_v_boundary': iii_v_boundary,
        'ii_v_boundary': ii_v_boundary,
        'v_vi_boundary': v_vi_boundary,
        'vi_vii_boundary': vi_vii_boundary,
        'vii_viii_boundary': vii_viii_boundary,
        'x_boundary': x_boundary,
    }
    
    if boundary_name not in boundary_funcs:
        raise ValueError(f"Unknown boundary: {boundary_name}")
    
    # Create cache key
    cache_key = (boundary_name, round(T_min, 2), round(T_max, 2), n_points)
    
    # Check cache
    if cache_key in _SHARED_BOUNDARY_CACHE:
        return _SHARED_BOUNDARY_CACHE[cache_key]
    
    # Compute vertices
    func = boundary_funcs[boundary_name]
    vertices = []
    
    # Include triple points as explicit vertices if they're within range
    triple_points_in_range = {
        'vii_viii_boundary': [
            ('VI_VII_VIII', 278.15, 2100.0),
            ('VII_VIII_X', 100.0, 62000.0),
        ],
        'x_boundary': [
            ('VII_VIII_X', 100.0, 62000.0),
            ('VII_X_Transition', 300.0, 30000.0),
        ],
    }
    
    # Generate temperature values
    T_vals = np.linspace(T_min, T_max, n_points)
    
    # Add explicit triple points if applicable
    T_explicit = set()
    if boundary_name in triple_points_in_range:
        for tp_name, tp_T, tp_P in triple_points_in_range[boundary_name]:
            if T_min <= tp_T <= T_max:
                T_explicit.add(tp_T)
    
    # Combine linspace values with explicit triple points
    all_T = sorted(set(T_vals) | T_explicit)
    
    for T in all_T:
        P = func(T)
        vertices.append((T, P))
    
    # Cache the result
    _SHARED_BOUNDARY_CACHE[cache_key] = vertices
    
    return vertices


# Phase colors for visualization (add new phases)
PHASE_COLORS = {
    "ice_ih": "#ADD8E6",   # Light blue
    "ice_ic": "#87CEEB",   # Sky blue
    "ice_ii": "#4169E1",   # Royal blue
    "ice_iii": "#90EE90",  # Light green
    "ice_v": "#228B22",    # Forest green
    "ice_vi": "#FFA500",   # Orange
    "ice_vii": "#FF6B6B",  # Light red
    "ice_viii": "#DC143C", # Crimson
    # NEW phases:
    "ice_xi": "#B0E0E6",   # Powder blue (lighter than Ih)
    "ice_ix": "#98FB98",   # Pale green (similar to III)
    "ice_x": "#8B0000",    # Dark red (distinct from VII/VIII)
    "ice_xv": "#FFD700",   # Gold (distinct from VI)
    "liquid": "#1E90FF",   # Dodger blue
}

# Phase display names (short form for labels on diagram)
PHASE_LABELS = {
    "ice_ih": "Ih",
    "ice_ic": "Ic",
    "ice_ii": "II",
    "ice_iii": "III",
    "ice_v": "V",
    "ice_vi": "VI",
    "ice_vii": "VII",
    "ice_viii": "VIII",
    # NEW phases:
    "ice_xi": "XI",
    "ice_ix": "IX",
    "ice_x": "X",
    "ice_xv": "XV",
    "liquid": "Liquid",
    "vapor": "Vapor",
}

# Phase display names (long form)
PHASE_NAMES = {
    "ice_ih": "Ice Ih",
    "ice_ic": "Ice Ic",
    "ice_ii": "Ice II",
    "ice_iii": "Ice III",
    "ice_v": "Ice V",
    "ice_vi": "Ice VI",
    "ice_vii": "Ice VII",
    "ice_viii": "Ice VIII",
    # NEW phases:
    "ice_xi": "Ice XI",
    "ice_ix": "Ice IX",
    "ice_x": "Ice X",
    "ice_xv": "Ice XV",
    "liquid": "Liquid water",
}


# IAPWS melting curve ranges (from melting_curves.py - single source of truth)
IAPWS_MELTING_RANGES = {
    "ice_ih_melting": {"T_min": 251.165, "T_max": 273.16, "ice_type": "Ih"},
    "ice_iii_melting": {"T_min": 251.165, "T_max": 256.164, "ice_type": "III"},
    "ice_v_melting": {"T_min": 256.164, "T_max": 273.31, "ice_type": "V"},
    "ice_vi_melting": {"T_min": 273.31, "T_max": 355.0, "ice_type": "VI"},
    "ice_vii_melting": {"T_min": 355.0, "T_max": 715.0, "ice_type": "VII"},
}


def _sample_melting_curve(curve_name: str, n_points: int = 100, smooth: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """Sample points along a melting curve using IAPWS equations.
    
    Uses the correct IAPWS melting pressure functions from melting_curves.py,
    not the Simon-Glatzel approximation from ice_boundaries.py.
    
    Args:
        curve_name: Name of melting curve (e.g., "ice_ih_melting")
        n_points: Number of points to sample (output points)
        smooth: If True, use spline interpolation for smooth curves
        
    Returns:
        Tuple of (temperatures, pressures) arrays
    """
    if curve_name not in IAPWS_MELTING_RANGES:
        return np.array([]), np.array([])
    
    curve = IAPWS_MELTING_RANGES[curve_name]
    T_min = curve["T_min"]
    T_max = curve["T_max"]
    ice_type = curve["ice_type"]
    
    if smooth:
        # Use more sample points for spline interpolation
        n_sample = max(n_points * 5, 500)
        T_sample = np.linspace(T_min, T_max, n_sample)
        P_sample = np.zeros_like(T_sample)
        
        for i, T in enumerate(T_sample):
            try:
                P_sample[i] = melting_pressure(T, ice_type)
            except ValueError:
                P_sample[i] = np.nan
        
        # Filter valid points
        valid = ~np.isnan(P_sample)
        T_sample = T_sample[valid]
        P_sample = P_sample[valid]
        
        # Use spline interpolation for smooth curve
        if len(T_sample) > 3:
            from scipy.interpolate import UnivariateSpline
            try:
                spline = UnivariateSpline(T_sample, P_sample, k=3, s=0)
                T_smooth = np.linspace(T_min, T_max, n_points)
                P_smooth = spline(T_smooth)
                return T_smooth, P_smooth
            except ImportError:
                # Fallback if scipy not available
                pass
            except Exception as e:
                # Fallback if spline fails - log for debugging
                logging.debug(f"Spline interpolation failed: {type(e).__name__}: {e}")
        
        # Fallback: use sample points directly
        indices = np.linspace(0, len(T_sample) - 1, n_points, dtype=int)
        return T_sample[indices], P_sample[indices]
    else:
        # Direct sampling without smoothing
        temperatures = np.linspace(T_min, T_max, n_points)
        pressures = np.zeros_like(temperatures)
        
        for i, T in enumerate(temperatures):
            try:
                pressures[i] = melting_pressure(T, ice_type)
            except ValueError:
                pressures[i] = np.nan
        
        valid = ~np.isnan(pressures)
        return temperatures[valid], pressures[valid]


def _build_phase_polygon_from_curves(phase_id: str) -> List[Tuple[float, float]]:
    """Build polygon vertices for a phase region using boundary curves.
    
    Returns list of (T, P) tuples defining the polygon.
    Uses melting curves and solid boundaries from Phase 2 (single source of truth).
    
    Args:
        phase_id: Phase identifier (e.g., "ice_ih", "ice_vii")
        
    Returns:
        List of (T, P) tuples forming the polygon boundary
    """
    # Define phase region boundaries using curve functions
    if phase_id == "ice_ih":
        return _build_ice_ih_polygon()
    elif phase_id == "ice_ii":
        return _build_ice_ii_polygon()
    elif phase_id == "ice_iii":
        return _build_ice_iii_polygon()
    elif phase_id == "ice_v":
        return _build_ice_v_polygon()
    elif phase_id == "ice_vi":
        return _build_ice_vi_polygon()
    elif phase_id == "ice_vii":
        return _build_ice_vii_polygon()
    elif phase_id == "ice_viii":
        return _build_ice_viii_polygon()
    elif phase_id == "ice_xi":
        return _build_ice_xi_polygon()
    elif phase_id == "ice_ix":
        return _build_ice_ix_polygon()
    elif phase_id == "ice_x":
        return _build_ice_x_polygon()
    elif phase_id == "ice_xv":
        return _build_ice_xv_polygon()
    elif phase_id == "ice_ic":
        return _build_ice_ic_polygon()
    else:
        return []


def _build_ice_ic_polygon() -> List[Tuple[float, float]]:
    """Ice Ic region: metastable cubic ice at low temperature and pressure.
    
    Ice Ic (cubic ice) is metastable with respect to Ice Ih but can form
    at very low temperatures (72-150 K) at pressures up to the Ih-II boundary.
    
    The upper pressure boundary follows the Ih-II boundary (~196-204 MPa),
    reflecting that Ice Ic can exist metastably wherever Ice Ih is stable.
    
    Scientific basis:
    - Ice Ic is metastable with respect to Ice Ih
    - At T=72K: Ih-II boundary is ~196 MPa
    - At T=150K: Ih-II boundary is ~204 MPa
    - Ice Ic can persist metastably in the same T-P region as Ice Ih
    - Lower boundary at 72K avoids overlap with Ice XI (stable below 72K)
    
    References:
    - Murray & Bertram (2007): Ice Ic formation conditions
    - Malkin et al. (2012): Ice polymorph metastability
    - IAPWS R14-08(2011): Ih-II thermodynamic boundary
    
    Note: Ice Ic is checked as a fallback in lookup_phase() when no other
    phase matches. The polygon here is for diagram visualization only.
    
    Returns:
        List of (T, P) tuples forming the polygon boundary
    """
    # Lower boundary at 72K to avoid overlap with Ice XI (which exists below 72K)
    # Upper boundary follows Ih-II boundary (Ice Ic is metastable where Ice Ih is stable)
    vertices = []
    
    # Bottom edge: from (72, 0.1) to (150, 0.1)
    vertices.append((72.0, 0.1))
    vertices.append((150.0, 0.1))
    
    # Right edge: from (150, 0.1) to (150, P_Ih_II_at_150K)
    # Upper pressure at T=150K using Ih-II boundary
    P_upper_150 = ih_ii_boundary(150.0)
    vertices.append((150.0, P_upper_150))
    
    # Top edge: trace Ih-II boundary from T=150K down to T=72K
    T_vals = np.linspace(150.0, 72.0, 20)
    for T in T_vals:
        P = ih_ii_boundary(T)
        vertices.append((T, P))
    
    # Close polygon back to start
    vertices.append((72.0, 0.1))
    
    return vertices


def _build_ice_ih_polygon() -> List[Tuple[float, float]]:
    """Ice Ih region: low pressure, bounded by melting curve and Ih-II boundary.
    
    Ih exists from T=150K to melting. Ice Ic (metastable) occupies T=72-150K region.
    At T < 72K, Ice XI is the stable phase.
    
    Note: Ice Ic is metastable with respect to Ice Ih and occupies the T=72-150K
    region at pressures below the Ih-II boundary. To avoid polygon overlap, Ice Ih
    polygon starts at T=150K where Ice Ic region ends.
    """
    vertices = []
    
    # Lower boundary: P ≈ 0 (atmospheric)
    # Start at T=150K (Ice Ic occupies T=72-150K)
    vertices.append((150.0, 0.1))
    
    # Ih melting curve from 251.165K to 273.16K
    T_vals = np.linspace(251.165, 273.16, 20)
    for T in T_vals[::-1]:  # Reverse to close polygon
        try:
            P = melting_pressure(T, "Ih")
            if P < 0.1:
                P = 0.1  # Clamp to atmospheric
            vertices.append((T, P))
        except ValueError as e:
            logging.debug(f"Melting pressure calculation failed at T={T}K: {e}")
    
    # Ih-III-Liquid triple point
    T_ih3l, P_ih3l = get_triple_point("Ih_III_Liquid")
    vertices.append((T_ih3l, P_ih3l))
    
    # Ih-II-III triple point
    T_ih23, P_ih23 = get_triple_point("Ih_II_III")
    vertices.append((T_ih23, P_ih23))
    
    # Ih-II boundary from TP down to T=150K (where Ice Ic region starts)
    # Note: We stop at T=150K to avoid overlap with Ice Ic polygon (T=72-150K)
    T_vals = np.linspace(T_ih23, 150.0, 15)
    for T in T_vals:
        P = ih_ii_boundary(T)
        vertices.append((T, P))
    
    # Close polygon: go vertically down from (150, P_Ih_II_at_150K) to (150, 0.1)
    # This creates the right edge of the polygon at T=150K
    P_at_150 = ih_ii_boundary(150.0)
    vertices.append((150.0, P_at_150))
    
    # Close back to start at (150, 0.1)
    vertices.append((150.0, 0.1))
    
    return vertices


def _build_ice_ii_polygon() -> List[Tuple[float, float]]:
    """Ice II region: moderate pressure, bounded by Ih-II, II-III, II-V, and IX/XV boundaries.
    
    II exists in the region between Ih-II boundary and the XV/VI regions.
    At T < 140K, IX exists at P=200-400 MPa, so II must stay at P >= 400 MPa.
    At T < 100K, XV exists at P=950-2100 MPa, so II must stay at P <= 950 MPa.
    II should NOT overlap VI - trace just below VI boundary.
    """
    vertices = []
    
    # Get all triple points first
    T1, P1 = get_triple_point("Ih_II_III")
    T2, P2 = get_triple_point("II_III_V")
    T3, P3 = get_triple_point("II_V_VI")
    
    # Start at Ih-II-III triple point
    vertices.append((T1, P1))
    
    # II-III boundary to II-III-V triple point
    T_vals = np.linspace(T1, T2, 10)
    for T in T_vals[1:]:
        P = ii_iii_boundary(T)
        vertices.append((T, P))
    
    # II-III-V triple point
    vertices.append((T2, P2))
    
    # II-V boundary to II-V-VI triple point
    T_vals = np.linspace(T2, T3, 10)
    for T in T_vals[1:]:
        P = ii_v_boundary(T)
        vertices.append((T, P))
    
    # II-V-VI triple point
    vertices.append((T3, P3))
    
    # Cold edge: below II-V-VI TP (T < 201.9K), VI still exists above V-VI boundary
    # So II traces just BELOW the extrapolated V-VI boundary
    # For T in [100, 201.9], trace below V-VI boundary
    
    T_cold = np.linspace(T3, 100.0, 10)
    for T in T_cold[1:]:
        P_vi = v_vi_boundary(T)  # This extrapolates for T < 201.9K
        vertices.append((T, P_vi - 5.0))  # Just below VI boundary
    
    # At T=100K, V-VI boundary extrapolates to P≈726 MPa
    # XV exists at P=950-2100 MPa for T <= 100K
    # So at T=100K, II ends at P < 726 (below V-VI boundary)
    # Then for T < 100K, II needs to connect to the lower pressure region
    
    # At T < 100K, XV occupies P=950-2100 MPa, so II stays at P < 950
    # But we need to properly close the polygon
    # The II polygon at T=100K ends at P ≈ 720 (just below V-VI)
    # For T < 100K, II extends up to P < 950 (below XV)
    
    # First, go vertically up at T=100K to close the gap
    # This creates the edge between T=100K line and T<100K region
    # But wait - VI exists at T=100K, P in [726, 950], so II can't go there!
    
    # Correct approach: at T=100K, II is at P < 726 (below V-VI boundary)
    # For T < 100K, II is at P < 950 (below XV)
    # So there's a narrow VI strip at T=100K between P=[726, 950]
    
    # Connect from (100, 720.6) diagonally to (50, 945)
    # This avoids the VI strip at T=100K
    vertices.append((50.0, 945.0))  # Just below XV at T=50K
    
    # At T=50K, go to P=400 (IX's upper boundary for T < 140K)
    vertices.append((50.0, 400.0))
    
    # Up to T=140K at P=400 (IX upper boundary)
    vertices.append((140.0, 400.0))
    
    # IMPORTANT: Close the gap at T=140K by going to Ih-II boundary
    # This ensures II touches the Ih-II boundary at T=140K before tracing back
    P_at_140 = ih_ii_boundary(140.0)
    vertices.append((140.0, P_at_140))
    
    # Lower boundary: follow Ih-II boundary back to start
    T_vals = np.linspace(140.0, T1, 15)
    for T in T_vals[1:]:
        P = ih_ii_boundary(T)
        vertices.append((T, P))
    
    return vertices


def _build_ice_iii_polygon() -> List[Tuple[float, float]]:
    """Ice III region: narrow stability between Ih, II, V, and liquid."""
    vertices = []
    
    # Ih-II-III triple point
    T1, P1 = get_triple_point("Ih_II_III")
    vertices.append((T1, P1))
    
    # Ih-III-Liquid triple point
    T2, P2 = get_triple_point("Ih_III_Liquid")
    vertices.append((T2, P2))
    
    # III-V-Liquid triple point
    T3, P3 = get_triple_point("III_V_Liquid")
    vertices.append((T3, P3))
    
    # II-III-V triple point
    T4, P4 = get_triple_point("II_III_V")
    vertices.append((T4, P4))
    
    # II-III boundary back to start
    T_vals = np.linspace(T4, T1, 10)
    for T in T_vals[1:-1]:
        P = ii_iii_boundary(T)
        vertices.append((T, P))
    
    return vertices


def _build_ice_v_polygon() -> List[Tuple[float, float]]:
    """Ice V region: moderate-high pressure."""
    vertices = []
    
    # II-III-V triple point
    T1, P1 = get_triple_point("II_III_V")
    vertices.append((T1, P1))
    
    # III-V-Liquid triple point
    T2, P2 = get_triple_point("III_V_Liquid")
    vertices.append((T2, P2))
    
    # V-VI-Liquid triple point
    T3, P3 = get_triple_point("V_VI_Liquid")
    vertices.append((T3, P3))
    
    # II-V-VI triple point
    T4, P4 = get_triple_point("II_V_VI")
    vertices.append((T4, P4))
    
    # II-V boundary back to start
    T_vals = np.linspace(T4, T1, 10)
    for T in T_vals[1:-1]:
        P = ii_v_boundary(T)
        vertices.append((T, P))
    
    return vertices


def _build_ice_vi_polygon() -> List[Tuple[float, float]]:
    """Ice VI region: high pressure.
    
    Ice VI exists at T >= 201.9K (II-V-VI TP), P above V-VI boundary.
    Cold boundary is at II-V-VI triple point (201.9K, 670.8 MPa).
    At T < 201.9K, VI doesn't exist - it's Ice II or Ice V instead.
    At T < 100K, XV (ordered VI) exists in a separate region.
    """
    vertices = []
    
    # II-V-VI triple point - this is the cold temperature limit of VI
    T1, P1 = get_triple_point("II_V_VI")  # (201.9, 670.8)
    vertices.append((T1, P1))
    
    # V-VI-Liquid triple point
    T2, P2 = get_triple_point("V_VI_Liquid")  # (273.31, 632.4)
    vertices.append((T2, P2))
    
    # VI-VII-Liquid triple point
    T3, P3 = get_triple_point("VI_VII_Liquid")  # (355, 2216)
    vertices.append((T3, P3))
    
    # VI-VII-VIII triple point
    T4, P4 = get_triple_point("VI_VII_VIII")  # (278, 2100)
    vertices.append((T4, P4))
    
    # Cold boundary: from VI-VII-VIII TP down to T=100K at P=2100 MPa
    # This touches XV's upper boundary (VIII's lower boundary)
    vertices.append((100.0, 2100.0))
    
    # VI-XV transition point at (100K, 1100 MPa)
    # This is where VI meets XV (XV is rendered on top at T <= 100K)
    vertices.append((100.0, 1100.0))
    
    # IMPORTANT: At T=100K, VI also extends down to V-VI boundary (~726 MPa)
    # This closes the gap between VI polygon and the V-VI boundary
    P_at_100 = v_vi_boundary(100.0)  # ≈ 726 MPa
    vertices.append((100.0, P_at_100 + 5.0))  # Just above V-VI boundary
    
    # From T=100K back to II-V-VI TP, trace along extrapolated V-VI boundary
    # The V-VI boundary extrapolates correctly for T < 201.9K
    T_cold = np.linspace(100.0, T1, 10)
    for T in T_cold[1:-1]:  # Skip endpoints
        P_vi = v_vi_boundary(T)  # This extrapolates for T < 201.9K
        vertices.append((T, P_vi + 5.0))  # Just above boundary
    
    # Back to II-V-VI TP to close polygon
    vertices.append((T1, P1))
    
    return vertices


def _build_ice_vii_polygon() -> List[Tuple[float, float]]:
    """Ice VII region: exists between VII-VIII/VII-melting boundary and X boundary.
    
    Ice VII exists in two regimes:
    1. T >= 278K: Pressures from lower boundary up to X boundary
       - For T < 354.75K: lower boundary is VI-VII boundary (linear)
       - For T >= 354.75K: lower boundary is VII melting curve
    2. 100K <= T < 278K: Thin strip between VII-VIII boundary and X boundary
    
    The polygon traces:
    - Bottom edge: from VI-VII-VIII TP along VI-VII boundary to VI-VII-Liquid TP,
                   then along VII melting curve to high T
    - Right edge: up to X boundary at high T
    - Top edge: along X boundary from 500K down to 100K (VII-VIII-X triple point)
    - Left edge: along VII-VIII boundary from 100K back up to 278K
    """
    from quickice.phase_mapping.melting_curves import melting_pressure
    
    vertices = []
    
    # VI-VII-VIII triple point (where VII meets VIII and VI)
    T_tp, P_tp = get_triple_point("VI_VII_VIII")  # (278, 2100)
    
    # VII-VIII-X triple point (where VII meets VIII and X at low T)
    T_tp_x, P_tp_x = get_triple_point("VII_VIII_X")  # (100, 62000)
    
    # VI-VII-Liquid triple point (where VII meets VI and Liquid)
    T_tp_liq, P_tp_liq = get_triple_point("VI_VII_Liquid")  # (354.75, 2200)
    
    # 1. Start at VI-VII-VIII triple point (bottom-left corner)
    vertices.append((T_tp, P_tp))
    
    # 2. Bottom edge part 1: follow VI-VII boundary from 278K to 354.75K
    T_vals_vi_vii = np.linspace(T_tp, T_tp_liq, 15)
    for T in T_vals_vi_vii[1:]:
        P = vi_vii_boundary(T)
        vertices.append((T, P))
    
    # 3. Bottom edge part 2: follow VII melting curve from 354.75K to 500K
    #    The melting curve is the boundary between Ice VII and Liquid
    T_high = 500.0
    T_vals_melt = np.linspace(T_tp_liq, T_high, 30)
    for T in T_vals_melt[1:]:
        try:
            P = melting_pressure(T, "VII")
            vertices.append((T, P))
        except ValueError:
            # Fallback: extrapolate linearly if outside range
            P_prev = vertices[-1][1]
            vertices.append((T, P_prev + 2.0))  # ~2 MPa/K slope
    
    # 4. Right edge: up to X boundary at high T
    P_x_high = x_boundary(T_high)
    vertices.append((T_high, P_x_high))
    
    # 5. Top edge: follow X boundary DOWN from 500K to 100K (using shared boundary vertices)
    x_boundary_vertices = _get_shared_boundary_vertices('x_boundary', T_tp_x, T_high, n_points=50)
    # Reverse to go from high T to low T
    for T, P in reversed(x_boundary_vertices):
        if T_tp_x <= T <= T_high:
            vertices.append((T, P))
    
    # Remove duplicates and sort
    vertices = list(dict.fromkeys(vertices))
    
    # 6. Left edge: follow VII-VIII boundary UP from 100K to 278K (using shared boundary vertices)
    vii_viii_boundary_vertices = _get_shared_boundary_vertices('vii_viii_boundary', T_tp_x, T_tp, n_points=30)
    for T, P in vii_viii_boundary_vertices:
        if T_tp_x < T <= T_tp:  # Exclude the starting point (already added)
            vertices.append((T, P))
    
    return vertices


def _build_ice_viii_polygon() -> List[Tuple[float, float]]:
    """Ice VIII region: ordered form of VII at low temperature.
    
    Upper boundary: x_boundary (Ice X at very high pressure)
    Lower boundary: VII-VIII boundary (curved from 278K/2100MPa to 100K/62000MPa)
    """
    vertices = []
    
    # VI-VII-VIII triple point (bottom left corner)
    T1, P1 = get_triple_point("VI_VII_VIII")
    vertices.append((T1, P1))
    
    # Follow VII-VIII boundary down to T=100K (using shared boundary vertices)
    T_viii_x = 100.0
    vii_viii_boundary_vertices = _get_shared_boundary_vertices('vii_viii_boundary', T_viii_x, T1, n_points=20)
    # Reverse to go from high T to low T
    for T, P in reversed(vii_viii_boundary_vertices):
        vertices.append((T, P))
    
    # At T=100K, follow X boundary up to T=50K (using shared boundary vertices)
    T_low = 50.0
    x_boundary_vertices = _get_shared_boundary_vertices('x_boundary', T_low, T_viii_x, n_points=20)
    # Reverse to go from T=100 to T=50
    for T, P in reversed(x_boundary_vertices):
        vertices.append((T, P))
    
    # Bottom edge at T=50K - connect back to VI-VII-VIII
    vertices.append((T_low, P1))
    
    return vertices


def _build_ice_xi_polygon() -> List[Tuple[float, float]]:
    """Ice XI region: T < 72K at low pressure (proton-ordered Ih).
    
    Ice XI is stable at T < 72K, P < ~200 MPa (low pressure).
    This region sits below the Ih-II boundary.
    """
    vertices = []
    
    # Start at T=72K (XI upper temperature limit), P=0.1 MPa
    vertices.append((72.0, 0.1))
    
    # Upper boundary: Ih-II boundary at T=72K (around 196 MPa)
    # XI exists below this boundary
    P_upper = ih_ii_boundary(72.0)  # ~196 MPa
    vertices.append((72.0, P_upper))
    
    # Right boundary: trace Ih-II boundary down to T=50K
    T_vals = np.linspace(72.0, 50.0, 10)
    for T in T_vals:
        P = ih_ii_boundary(T)
        vertices.append((T, P))
    
    # Lower-left corner at T=50K, low pressure
    vertices.append((50.0, 0.1))
    
    # Bottom edge: from T=50K to T=72K at P=0.1
    vertices.append((72.0, 0.1))
    
    return vertices


def _build_ice_ix_polygon() -> List[Tuple[float, float]]:
    """Ice IX region: T < 140K, P = 200-400 MPa (proton-ordered III).
    
    Ice IX is the proton-ordered form of Ice III at low temperatures.
    Extends from T=50K to T=140K.
    Lower boundary touches the Ih-II boundary (~200 MPa).
    Upper boundary at P=400 MPa.
    """
    vertices = []
    
    # Start at T=50K, lower boundary (touching Ih-II boundary)
    P_low_at_50 = ih_ii_boundary(50.0)  # ~197.9 MPa
    vertices.append((50.0, P_low_at_50))
    
    # Trace along lower boundary from T=50K to T=140K (following Ih-II boundary)
    T_vals = np.linspace(50.0, 140.0, 20)
    for T in T_vals[1:]:
        P = ih_ii_boundary(T)
        vertices.append((T, P))
    
    # Upper boundary at P=400 MPa - go up to T=140K
    vertices.append((140.0, 400.0))
    
    # Left edge: go back along P=400 MPa to T=50K
    T_vals = np.linspace(140.0, 50.0, 10)
    for T in T_vals[1:]:
        vertices.append((T, 400.0))
    
    # Close back to start
    vertices.append((50.0, P_low_at_50))
    
    return vertices


def _build_ice_x_polygon() -> List[Tuple[float, float]]:
    """Ice X region: P > x_boundary(T) (symmetric hydrogen bonds).
    
    Extended to T=50K per user request.
    Lower boundary uses x_boundary function which interpolates through:
    - VII_VIII_X at (100K, 62000 MPa)
    - VII_X_Transition at (300K, 30000 MPa)
    - VII_X_Liquid at (1000K, 43000 MPa)
    """
    vertices = []
    
    T_low = 50.0
    T_high = 500.0
    P_max = 100000.0  # 100 GPa
    
    # Start at T=50K, using x_boundary(50) = 62000 MPa (clamped at T <= 100K)
    P_boundary_low = x_boundary(T_low)
    vertices.append((T_low, P_boundary_low))
    
    # Lower boundary: follow x_boundary from T=50K to T=500K (using shared boundary vertices)
    x_boundary_vertices = _get_shared_boundary_vertices('x_boundary', T_low, T_high, n_points=50)
    for T, P in x_boundary_vertices:
        vertices.append((T, P))
    
    # Upper boundary at P_max
    vertices.append((T_high, P_max))
    vertices.append((T_low, P_max))
    
    # Close back to start
    vertices.append((T_low, P_boundary_low))
    
    return vertices


def _build_ice_xv_polygon() -> List[Tuple[float, float]]:
    """Ice XV region: T = 50-100K, P = 950-2100 MPa (proton-ordered VI).
    
    Ice XV is the proton-ordered form of Ice VI at low temperatures.
    Extends from T=50K to T=100K where it meets VI.
    Pressure spans from II's upper boundary (P~950 MPa) to VIII's lower boundary (P=2100 MPa).
    The VI-XV transition point (100K, 1100 MPa) is at the top of this region.
    """
    from quickice.phase_mapping.solid_boundaries import xv_boundary
    
    vertices = []
    
    # XV lower boundary at P=950 MPa (touching II's upper boundary)
    # XV upper boundary at P=2100 MPa (touching VIII's lower boundary)
    P_lower = 950.0
    P_upper = 2100.0
    
    # Start at T=50K, lower boundary
    vertices.append((50.0, P_lower))
    
    # Lower boundary to T=100K
    vertices.append((100.0, P_lower))
    
    # Upper boundary at T=100K (touching VIII)
    vertices.append((100.0, P_upper))
    
    # Back along upper boundary to T=50K
    vertices.append((50.0, P_upper))
    
    # Close back to start
    vertices.append((50.0, P_lower))
    
    return vertices


def generate_phase_diagram(
    user_t: float,
    user_p: float,
    output_dir: str | Path,
    figsize: tuple[float, float] = (12, 10),
    dpi: int = 300,
    use_log_scale: bool = True,
) -> list[str]:
    """Generate phase diagram with curved boundaries and user's conditions marked.
    
    Creates publication-quality phase diagrams showing ice polymorph regions
    using curve-based boundaries from Phase 2 (melting_pressure and solid_boundary
    functions) as single source of truth.
    
    Args:
        user_t: User's temperature in Kelvin
        user_p: User's pressure in MPa
        output_dir: Directory to save output files
        figsize: Figure size as (width, height) in inches
        dpi: Resolution for PNG output
        use_log_scale: Use logarithmic scale for pressure (like Wikipedia diagram)
        
    Returns:
        List of paths to generated files
        
    Raises:
        FileNotFoundError: If phase data files not found
    """
    from shapely.geometry import Polygon as ShapelyPolygon
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    
    # Set up logarithmic pressure scale if requested
    if use_log_scale:
        ax.set_yscale('log')
    
    # Define phases to plot (in order, back to front for proper layering)
    # Sub-phases (XI, IX, XV) should be rendered AFTER their parent phases
    phases_to_plot = [
        "ice_x",      # highest pressure
        "ice_viii",
        "ice_vii", 
        "ice_vi",
        "ice_xv",     # ordered VI (rendered AFTER VI so it appears on top)
        "ice_v",
        "ice_ii",
        "ice_ix",     # ordered III (rendered AFTER II so it appears on top)
        "ice_iii",
        "ice_ih",
        "ice_xi",     # ordered Ih (rendered AFTER Ih so it appears on top)
        "ice_ic",     # metastable cubic ice (rendered LAST so it appears on top of XI/Ih)
    ]
    
    # Plot each phase region using curve-based boundaries
    from shapely.geometry import Polygon as ShapelyPolygon
    
    for phase_id in phases_to_plot:
        # Build polygon from curves (single source of truth)
        vertices = _build_phase_polygon_from_curves(phase_id)
        
        if len(vertices) < 3:
            continue
        
        # Vertices are (T, P) pairs, use directly for plotting
        plot_vertices = np.array(vertices)
        
        # Create polygon patch
        color = PHASE_COLORS.get(phase_id, "#CCCCCC")
        poly = Polygon(plot_vertices, closed=True)
        poly.set_facecolor(color)
        poly.set_edgecolor("black")
        poly.set_linewidth(1.5)
        poly.set_alpha(0.6)
        ax.add_patch(poly)
        
        # Label using shapely centroid
        shapely_poly = ShapelyPolygon(vertices)
        centroid = shapely_poly.centroid
        label = PHASE_LABELS.get(phase_id, phase_id)
        ax.text(
            centroid.x, centroid.y,  # x=T, y=P (correct orientation)
            label,
            fontsize=14,
            fontweight='bold',
            ha='center',
            va='center',
            color='black',
            alpha=0.8,
            zorder=5,
        )
    
    # Plot melting curves as lines (on top of filled regions)
    melting_curves = [
        ("ice_ih_melting", "#000000", "Ice Ih melting"),
        ("ice_iii_melting", "#333333", "Ice III melting"),
        ("ice_v_melting", "#555555", "Ice V melting"),
        ("ice_vi_melting", "#777777", "Ice VI melting"),
        ("ice_vii_melting", "#999999", "Ice VII melting"),
    ]
    
    for curve_name, color, label in melting_curves:
        T_curve, P_curve = _sample_melting_curve(curve_name, n_points=200)
        if len(T_curve) > 0:
            ax.plot(T_curve, P_curve, color=color, linewidth=3.0, linestyle='-', alpha=0.8)
    
    # Liquid-Vapor boundary using IAPWS saturation curve
    from iapws import IAPWS97
    lv_T = np.linspace(273.16, 500, 50)
    lv_P = []
    for T in lv_T:
        try:
            st = IAPWS97(T=T, x=0)  # saturated liquid
            lv_P.append(st.P)
        except Exception as e:
            logging.warning(f"IAPWS97 calculation failed at T={T}K: {type(e).__name__}: {e}")
    if len(lv_P) > 0:
        lv_T = lv_T[:len(lv_P)]
        ax.plot(lv_T, lv_P, color='blue', linewidth=3.0, linestyle='-', alpha=0.8)
    
    # Add Liquid and Vapor labels
    ax.text(
        340, 50,  # T=340K, P=50 MPa (liquid region above melting curves)
        "Liquid",
        fontsize=14,
        fontweight='bold',
        ha='center',
        va='center',
        color='black',
        alpha=0.8,
        zorder=5,
    )
    ax.text(
        460, 0.5,  # T=460K, P=0.5 MPa (vapor region, below saturation curve)
        "Vapor",
        fontsize=14,
        fontweight='bold',
        ha='center',
        va='center',
        color='black',
        alpha=0.8,
        zorder=5,
    )
    
    # Mark triple points
    # Note: Ih-XI-Vapor triple point is at P=0.0001 MPa, outside graph bounds (P >= 0.1 MPa)
    # So it's not included here
    triple_point_names = [
        ("Ih_III_Liquid", "Ih-III-L"),
        ("Ih_II_III", "Ih-II-III"),
        ("II_III_V", "II-III-V"),
        ("III_V_Liquid", "III-V-L"),
        ("II_V_VI", "II-V-VI"),
        ("V_VI_Liquid", "V-VI-L"),
        ("VI_VII_Liquid", "VI-VII-L"),
        ("VI_VII_VIII", "VI-VII-VIII"),
        # NEW triple points (within graph bounds):
        ("III_IX_Transition", "III-IX"),
        ("VII_X_Transition", "VII-X"),
        ("VI_XV_Transition", "VI-XV"),
        ("VII_VIII_X", "VII-VIII-X"),
    ]
    
    for tp_name, tp_label in triple_point_names:
        tp_T, tp_P = get_triple_point(tp_name)
        ax.plot(
            tp_T, tp_P,
            'ko',  # Black circle
            markersize=5,
            markeredgecolor='white',
            markeredgewidth=0.5,
            zorder=6,
        )
        # Add small label near the triple point
        # For very low pressure points (P < 1 MPa), position label to avoid log scale issues
        if tp_P < 1.0:
            ax.text(
                tp_T + 5, 0.3,  # Position to the right at a visible pressure
                tp_label,
                fontsize=8,
                ha='left',
                va='center',
                color='black',
                alpha=0.7,
                zorder=6,
            )
        else:
            ax.text(
                tp_T, tp_P * 1.1,
                tp_label,
                fontsize=8,
                ha='left',
                va='center',
                color='black',
                alpha=0.7,
                zorder=6,
            )
    
    # Plot user's T,P point
    ax.plot(
        user_t, user_p,
        'ro',  # Red circle
        markersize=15,
        markeredgecolor='black',
        markeredgewidth=2,
        label=f"Your conditions\n({user_t:.1f} K, {user_p:.1f} MPa)",
        zorder=10,  # Ensure it's on top
    )
    
    # Set axis limits (Temperature on X, Pressure on Y with log scale)
    ax.set_xlim(50, 500)  # Extended from 100 to 50K for Ice XI
    if use_log_scale:
        ax.set_ylim(0.1, 100000)  # Extended from 10000 to 100000 MPa (100 GPa) for Ice X
    else:
        ax.set_ylim(0, 50000)  # Extended for Ice X
    
    # Add grid
    ax.grid(True, linestyle='--', alpha=0.5, which='both')
    
    # Labels and title
    ax.set_xlabel("Temperature (K)", fontsize=14, fontweight='bold')
    ax.set_ylabel("Pressure (MPa)", fontsize=14, fontweight='bold')
    ax.set_title("Water Ice Phase Diagram", fontsize=18, fontweight='bold', pad=20)
    
    # Add note about data source
    ax.text(
        0.02, 0.02,
        "Data: IAPWS R14-08(2011) + Literature values for XI, IX, X, XV",
        transform=ax.transAxes,
        fontsize=8,
        ha='left',
        va='bottom',
        color='gray',
        style='italic',
    )
    
    # Tight layout
    plt.tight_layout()
    
    # Generate output paths
    png_path = output_dir / "phase_diagram.png"
    svg_path = output_dir / "phase_diagram.svg"
    txt_path = output_dir / "phase_diagram_data.txt"
    
    # Save files
    plt.savefig(png_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.savefig(svg_path, format='svg', bbox_inches='tight', facecolor='white')
    
    # Write text data file with curve data
    with open(txt_path, 'w') as f:
        f.write("# Water Ice Phase Diagram Data\n")
        f.write("# Source: IAPWS R14-08(2011), IAPWS R10-06(2009)\n")
        f.write("# Boundary type: Curved (IAPWS Simon-Glatzel melting curves)\n")
        f.write("#\n")
        f.write("# TRIPLE POINTS\n")
        for tp_name, tp in TRIPLE_POINTS.items():
            f.write(f"# {tp_name}: T={tp[0]} K, P={tp[1]} MPa\n")
        f.write("#\n")
        f.write("# MELTING CURVES\n")
        for curve_name in IAPWS_MELTING_RANGES:
            T_curve, P_curve = _sample_melting_curve(curve_name, n_points=50)
            f.write(f"# {curve_name}:\n")
            for T, P in zip(T_curve, P_curve):
                f.write(f"#   T={T:.2f} K, P={P:.2f} MPa\n")
        f.write("#\n")
        f.write("# USER CONDITIONS\n")
        f.write(f"# Temperature: {user_t} K\n")
        f.write(f"# Pressure: {user_p} MPa\n")
    
    # Close figure to prevent memory leak
    plt.close(fig)
    
    return [str(png_path), str(svg_path), str(txt_path)]


# For testing
if __name__ == "__main__":
    import sys
    
    # Default test conditions
    user_t = 250.0  # K
    user_p = 500.0  # MPa
    
    # Use command line args if provided
    if len(sys.argv) >= 3:
        user_t = float(sys.argv[1])
        user_p = float(sys.argv[2])
    
    output_dir = Path(__file__).parent.parent.parent / "output"
    
    files = generate_phase_diagram(user_t, user_p, output_dir)
    print(f"Generated files:")
    for f in files:
        print(f"  {f}")
