"""Phase diagram generator for ice polymorph visualization.

Generates publication-quality phase diagrams using curve-based boundaries
from Phase 2 melting_curves and solid_boundaries modules (single source of truth).

Outputs PNG, SVG, and text data files.
"""

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
    VII_VIII_ORDERING_TEMP,
)
from quickice.phase_mapping.data.ice_boundaries import (
    MELTING_CURVE_COEFFICIENTS,
    get_melting_pressure,
)


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


def _sample_melting_curve(curve_name: str, n_points: int = 100, smooth: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """Sample points along a melting curve using IAPWS equations.
    
    Uses spline interpolation for smooth curves when smooth=True.
    
    Args:
        curve_name: Name of melting curve (e.g., "ice_ih_melting")
        n_points: Number of points to sample (output points)
        smooth: If True, use spline interpolation for smooth curves
        
    Returns:
        Tuple of (temperatures, pressures) arrays
    """
    if curve_name not in MELTING_CURVE_COEFFICIENTS:
        return np.array([]), np.array([])
    
    curve = MELTING_CURVE_COEFFICIENTS[curve_name]
    T_min = curve["T_min"]
    T_max = curve["T_max"]
    
    if smooth:
        # Use more sample points for spline interpolation
        n_sample = max(n_points * 5, 500)
        T_sample = np.linspace(T_min, T_max, n_sample)
        P_sample = np.zeros_like(T_sample)
        
        for i, T in enumerate(T_sample):
            try:
                P_sample[i] = get_melting_pressure(curve_name, T)
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
            except Exception:
                # Fallback if spline fails
                pass
        
        # Fallback: use sample points directly
        indices = np.linspace(0, len(T_sample) - 1, n_points, dtype=int)
        return T_sample[indices], P_sample[indices]
    else:
        # Direct sampling without smoothing
        temperatures = np.linspace(T_min, T_max, n_points)
        pressures = np.zeros_like(temperatures)
        
        for i, T in enumerate(temperatures):
            try:
                pressures[i] = get_melting_pressure(curve_name, T)
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
    else:
        return []


def _build_ice_ih_polygon() -> List[Tuple[float, float]]:
    """Ice Ih region: low pressure, bounded by melting curve and Ih-II boundary.
    
    Ih exists from T=100K to melting, and meets XI at T~72K boundary.
    """
    vertices = []
    
    # Lower boundary: P ≈ 0 (atmospheric)
    # Start at T=100K (lowest stable for Ih above XI)
    vertices.append((100.0, 0.1))
    
    # Ih melting curve from 251.165K to 273.16K
    T_vals = np.linspace(251.165, 273.16, 20)
    for T in T_vals[::-1]:  # Reverse to close polygon
        try:
            P = melting_pressure(T, "Ih")
            if P < 0.1:
                P = 0.1  # Clamp to atmospheric
            vertices.append((T, P))
        except ValueError:
            pass
    
    # Ih-III-Liquid triple point (251.165 K, 207.5 MPa)
    vertices.append((251.165, 207.5))
    
    # Ih-II-III triple point (238.55 K, 212.9 MPa)
    vertices.append((238.55, 212.9))
    
    # Ih-II boundary from TP down to T=72K (where XI takes over)
    T_vals = np.linspace(238.55, 72.0, 20)
    for T in T_vals:
        P = ih_ii_boundary(T)
        vertices.append((T, P))
    
    # Close back to start: go vertically down to P=0.1, then along bottom to (100, 0.1)
    # This avoids crossing the Ih-II boundary path
    T_end = vertices[-1][0]  # T=72
    P_end = vertices[-1][1]  # P~196
    
    # Vertical line from (72, ~196) down to (72, 0.1)
    vertices.append((T_end, 0.1))
    
    # Horizontal line from (72, 0.1) to (100, 0.1)
    T_bottom = np.linspace(72.0, 100.0, 5)
    for T in T_bottom[1:]:
        vertices.append((T, 0.1))
    
    return vertices


def _build_ice_ii_polygon() -> List[Tuple[float, float]]:
    """Ice II region: moderate pressure, bounded by Ih-II, II-III, II-V, and IX/XV boundaries.
    
    II exists in the region between Ih-II boundary and the XV/VI regions.
    At T < 140K, IX exists at P=200-400 MPa, so II must stay at P >= 400 MPa.
    At T < 100K, XV exists at P=950-2100 MPa, so II must stay at P <= 950 MPa.
    II should NOT overlap VI - trace just below VI boundary.
    """
    vertices = []
    
    # Start at Ih-II-III triple point
    T1, P1 = get_triple_point("Ih_II_III")
    vertices.append((T1, P1))
    
    # II-III boundary to II-III-V triple point
    T_vals = np.linspace(T1, 248.85, 10)
    for T in T_vals[1:]:
        P = ii_iii_boundary(T)
        vertices.append((T, P))
    
    # II-III-V triple point (248.85 K, 344.3 MPa)
    T2, P2 = get_triple_point("II_III_V")
    vertices.append((T2, P2))
    
    # II-V boundary to II-V-VI triple point
    T_vals = np.linspace(T2, 218.95, 10)
    for T in T_vals[1:]:
        P = ii_v_boundary(T)
        vertices.append((T, P))
    
    # II-V-VI triple point (218.95 K, 620.0 MPa)
    T3, P3 = get_triple_point("II_V_VI")
    vertices.append((T3, P3))
    
    # Cold edge: II traces just BELOW VI boundary
    # VI's left edge: from (218.95, 620) to (100, 1100)
    # Line equation: P = 620 + 480 * (218.95 - T) / 118.95
    T_cold = np.linspace(218.95, 140.0, 10)
    for T in T_cold[1:]:
        P_vi = 620.0 + 480.0 * (218.95 - T) / 118.95
        vertices.append((T, P_vi - 5.0))
    
    # At T=140K, IX ends. II continues down towards XV.
    # From T=140K to T=100K: II at P just below VI boundary, but capped at P=950 (XV's lower)
    T_cold2 = np.linspace(140.0, 100.0, 5)
    for T in T_cold2[1:]:
        P_vi = 620.0 + 480.0 * (218.95 - T) / 118.95
        # Cap at P=950 to avoid entering XV region
        P = min(P_vi - 5.0, 950.0)
        vertices.append((T, P))
    
    # At T=100K, II stops at P=950 (XV's lower boundary)
    # Go down to T=50K at P=950
    vertices.append((50.0, 950.0))
    
    # At T=50K, go to P=400 (IX's upper boundary for T < 140K)
    vertices.append((50.0, 400.0))
    
    # Up to T=140K at P=400 (IX upper boundary)
    vertices.append((140.0, 400.0))
    
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
    
    Ice VI exists at T >= 100K, P >= 620 MPa.
    Cold boundary touches XV at the VI-XV transition point (100K, 1100 MPa).
    At T < 100K, XV (ordered VI) exists instead of VI.
    """
    vertices = []
    
    # II-V-VI triple point - this is the cold temperature limit where II meets VI
    T1, P1 = get_triple_point("II_V_VI")
    vertices.append((T1, P1))
    
    # V-VI-Liquid triple point
    T2, P2 = get_triple_point("V_VI_Liquid")
    vertices.append((T2, P2))
    
    # VI-VII-Liquid triple point
    T3, P3 = get_triple_point("VI_VII_Liquid")
    vertices.append((T3, P3))
    
    # VI-VII-VIII triple point
    T4, P4 = get_triple_point("VI_VII_VIII")
    vertices.append((T4, P4))
    
    # Cold boundary: from VI-VII-VIII TP down to T=100K at P=2100 MPa
    # This touches XV's upper boundary (VIII's lower boundary)
    vertices.append((100.0, 2100.0))
    
    # Touch VI-XV transition point at (100K, 1100 MPa)
    # This is where VI meets XV (XV is rendered on top at T < 100K)
    vertices.append((100.0, 1100.0))
    
    # Back to II-V-VI TP - follow boundary from (100, 1100) to (218.95, 620)
    # This creates the cold edge that doesn't overlap XV
    vertices.append((T1, P1))  # Back to II-V-VI TP (218.95, 620)
    
    return vertices


def _build_ice_vii_polygon() -> List[Tuple[float, float]]:
    """Ice VII region: very high pressure, high temperature.
    
    Ice VII exists at T > 278K (no VIII above this temp) and T < 278K but P < VII-VIII boundary.
    Upper boundary: x_boundary (Ice X at very high pressure).
    Lower boundary: extends from VI-VII-VIII triple point at 278K.
    """
    from quickice.phase_mapping.solid_boundaries import x_boundary
    
    vertices = []
    
    # VI-VII-VIII triple point (where VII meets VIII and VI)
    T_tp, P_tp = get_triple_point("VI_VII_VIII")  # (278, 2100)
    
    # Start at VI-VII-VIII triple point
    vertices.append((T_tp, P_tp))
    
    # Go to high temperature (horizontal line at P=2100 MPa)
    T_high = 500.0
    vertices.append((T_high, P_tp))
    
    # Follow X boundary up from (500K, 2100 MPa) to (500K, X boundary)
    P_x_high = x_boundary(T_high)
    vertices.append((T_high, P_x_high))
    
    # Follow X boundary back down to T=278K
    T_vals = np.linspace(T_high, T_tp, 30)
    for T in T_vals[1:]:
        P = x_boundary(T)
        vertices.append((T, P))
    
    return vertices


def _build_ice_viii_polygon() -> List[Tuple[float, float]]:
    """Ice VIII region: ordered form of VII at low temperature.
    
    Upper boundary: x_boundary (Ice X at very high pressure)
    Lower boundary: VII-VIII boundary (curved from 278K/2100MPa to 100K/62000MPa)
    """
    from quickice.phase_mapping.solid_boundaries import x_boundary, vii_viii_boundary
    
    vertices = []
    
    # VI-VII-VIII triple point (bottom left corner)
    T1, P1 = get_triple_point("VI_VII_VIII")
    vertices.append((T1, P1))
    
    # Follow VII-VIII boundary down to T=100K (VII-VIII-X triple point)
    T_viii_x = 100.0
    T_vals_down = np.linspace(T1, T_viii_x, 20)
    for T in T_vals_down[1:]:
        P = vii_viii_boundary(T)
        vertices.append((T, P))
    
    # At T=100K, follow X boundary up to T=50K
    T_vals_x = np.linspace(T_viii_x, 50.0, 20)
    for T in T_vals_x[1:]:
        P = x_boundary(T)
        vertices.append((T, P))
    
    # Bottom edge at T=50K - connect back to VI-VII-VIII
    vertices.append((50.0, P1))
    
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
    from quickice.phase_mapping.solid_boundaries import x_boundary
    
    vertices = []
    
    T_low = 50.0
    T_high = 500.0
    P_max = 100000.0  # 100 GPa
    
    # Start at T=50K, using x_boundary(50) = 62000 MPa (clamped at T <= 100K)
    P_boundary_low = x_boundary(T_low)
    vertices.append((T_low, P_boundary_low))
    
    # Lower boundary: follow x_boundary from T=50K to T=500K
    # This creates a curved lower boundary that passes through all triple points
    T_vals = np.linspace(T_low, T_high, 50)
    for T in T_vals[1:]:
        P = x_boundary(T)
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
        "ice_x",      # NEW: highest pressure
        "ice_viii",
        "ice_vii", 
        "ice_vi",
        "ice_xv",     # NEW: ordered VI (rendered AFTER VI so it appears on top)
        "ice_v",
        "ice_ii",
        "ice_ix",     # NEW: ordered III (rendered AFTER II so it appears on top)
        "ice_iii",
        "ice_ih",
        "ice_xi",     # NEW: ordered Ih (rendered AFTER Ih so it appears on top)
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
        except:
            pass
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
        for curve_name in MELTING_CURVE_COEFFICIENTS:
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
