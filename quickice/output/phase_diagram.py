"""Phase diagram generator for ice polymorph visualization.

Generates publication-quality phase diagrams with curved boundaries
derived from IAPWS-certified melting curve equations.

Outputs PNG, SVG, and text data files.
"""

import json
from pathlib import Path
from typing import Optional, Tuple, List
import warnings

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection

from quickice.phase_mapping.data.ice_boundaries import (
    TRIPLE_POINTS,
    MELTING_CURVE_COEFFICIENTS,
    get_melting_pressure,
    get_triple_point,
)


# Phase colors for visualization
PHASE_COLORS = {
    "ice_ih": "#ADD8E6",   # Light blue
    "ice_ic": "#87CEEB",   # Sky blue
    "ice_ii": "#4169E1",   # Royal blue
    "ice_iii": "#90EE90",  # Light green
    "ice_v": "#228B22",    # Forest green
    "ice_vi": "#FFA500",   # Orange
    "ice_vii": "#FF6B6B",  # Light red
    "ice_viii": "#DC143C", # Crimson
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
    "liquid": "Liquid water",
}


def _load_phase_data() -> dict:
    """Load ice phase metadata from JSON file.
    
    Returns:
        Dictionary with phase information
    """
    data_path = Path(__file__).parent.parent / "phase_mapping" / "data" / "ice_phases.json"
    with open(data_path, "r") as f:
        return json.load(f)


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


def _get_phase_region_boundaries() -> dict:
    """Get phase region boundaries defined by melting curves and triple points.
    
    Returns:
        Dictionary mapping phase names to their boundary specifications
    """
    # Phase regions defined by which curves/triple points bound them
    # Format: list of (curve_type, curve_name, direction)
    # direction: 'left' or 'right' indicates which side of curve
    
    return {
        "ice_ih": {
            "boundaries": [
                ("curve", "ice_ih_melting", "left"),  # Left of Ih melting curve
                ("point", "ih_iii_liquid", None),
                ("point", "ih_ii_iii", None),
            ],
            "T_range": (100, 273.16),
            "P_range": (0.1, 250),
        },
        "ice_iii": {
            "boundaries": [
                ("curve", "ice_ih_melting", "right"),  # Right of Ih melting
                ("curve", "ice_iii_melting", "left"),  # Left of III melting
            ],
            "T_range": (238.55, 251.165),
            "P_range": (200, 400),
        },
        "ice_ii": {
            "boundaries": [
                ("point", "ih_ii_iii", None),
                ("point", "ii_iii_v", None),
                ("point", "ii_v_vi", None),
            ],
            "T_range": (200, 280),
            "P_range": (200, 700),
        },
        "ice_v": {
            "boundaries": [
                ("curve", "ice_v_melting", "left"),
                ("point", "ii_v_vi", None),
            ],
            "T_range": (240, 280),
            "P_range": (340, 700),
        },
        "ice_vi": {
            "boundaries": [
                ("curve", "ice_vi_melting", "left"),
                ("point", "vi_vii_viii", None),
            ],
            "T_range": (220, 360),
            "P_range": (600, 2200),
        },
        "ice_vii": {
            "boundaries": [
                ("curve", "ice_vii_melting", "left"),
                ("point", "vi_vii_viii", None),
            ],
            "T_range": (280, 500),
            "P_range": (2100, 10000),
        },
        "ice_viii": {
            "boundaries": [],
            "T_range": (100, 280),
            "P_range": (2100, 10000),
        },
    }


def _calculate_phase_centroid(phase_id: str) -> Tuple[float, float]:
    """Calculate centroid position for placing phase labels.
    
    Uses triple point positions to find the center of each phase region.
    
    Args:
        phase_id: Phase identifier
        
    Returns:
        Tuple of (temperature, pressure) for label placement
    """
    tp = TRIPLE_POINTS
    
    # Centroids calculated from triple points and typical phase regions
    centroids = {
        "ice_ih": (240, 30),                    # Low pressure region
        "ice_ii": (220, 400),                  # Moderate pressure, low T
        "ice_iii": (245, 280),                 # Narrow triangular region
        "ice_v": (260, 480),                   # Moderate-high pressure
        "ice_vi": (300, 1200),                 # High pressure
        "ice_vii": (350, 4000),                # Very high pressure, high T
        "ice_viii": (180, 5000),               # Very high pressure, low T
        "ice_ic": (150, 50),                   # Metastable, low T/P
    }
    return centroids.get(phase_id, (250, 500))


def _build_phase_polygon_from_curves(phase_id: str, n_points: int = 50) -> Optional[List[Tuple[float, float]]]:
    """Build a polygon for a phase region using curved boundaries.
    
    This creates smooth boundaries by sampling along melting curves
    rather than using fixed polygon vertices. Phase regions are based
    on IAPWS-certified triple points and melting curves.
    
    Args:
        phase_id: Phase identifier
        n_points: Number of points per curve
        
    Returns:
        List of (T, P) vertices or None if not applicable
    """
    tp = TRIPLE_POINTS
    
    if phase_id == "ice_ih":
        # Ice Ih: Low pressure phase, bounded by:
        # - Ih melting curve (251.165 K to 273.16 K)
        # - Ih-II-III triple point (238.55 K, 212.9 MPa)
        # - Low temperature/pressure boundary
        
        T_ih_curve, P_ih_curve = _sample_melting_curve("ice_ih_melting", n_points)
        
        vertices = []
        # Start from low pressure at 0°C
        vertices.append((273.16, 0.1))
        # Add points along the Ih melting curve (P decreases as T increases)
        for T, P in zip(T_ih_curve[::-1], P_ih_curve[::-1]):
            vertices.append((T, P))
        # Add boundary to close the polygon
        vertices.append((tp["ih_ii_iii"]["T"], tp["ih_ii_iii"]["P"]))
        vertices.append((200, 100))
        vertices.append((150, 0.1))
        vertices.append((100, 0.1))
        return vertices
        
    elif phase_id == "ice_ii":
        # Ice II: Rhombohedral phase at moderate pressure
        # Bounded by: Ih-II-III TP, II-III-V TP, II-V-VI TP
        vertices = [
            (tp["ih_ii_iii"]["T"], tp["ih_ii_iii"]["P"]),  # Ih-II-III TP
            (tp["ii_iii_v"]["T"], tp["ii_iii_v"]["P"]),    # II-III-V TP
            (tp["ii_v_vi"]["T"], tp["ii_v_vi"]["P"]),      # II-V-VI TP
            (180, 620),                                     # Low T boundary
            (180, 300),                                     # Low T, lower P
            (220, 250),                                     # Return path
        ]
        return vertices
        
    elif phase_id == "ice_iii":
        # Ice III: Tetragonal phase, narrow stability region
        # Bounded by: Ih-II-III TP, Ih-III-Liquid TP, II-III-V TP
        vertices = [
            (tp["ih_ii_iii"]["T"], tp["ih_ii_iii"]["P"]),      # Ih-II-III TP
            (tp["ih_iii_liquid"]["T"], tp["ih_iii_liquid"]["P"]), # Ih-III-Liquid TP
            (tp["ii_iii_v"]["T"], tp["ii_iii_v"]["P"]),        # II-III-V TP
        ]
        return vertices
        
    elif phase_id == "ice_v":
        # Ice V: Monoclinic phase at moderate-high pressure
        # Bounded by: II-III-V TP, III-V-Liquid TP, V-VI-Liquid TP, II-V-VI TP
        
        T_v_curve, P_v_curve = _sample_melting_curve("ice_v_melting", n_points)
        
        vertices = []
        # Start at II-III-V triple point
        vertices.append((tp["ii_iii_v"]["T"], tp["ii_iii_v"]["P"]))
        # Add III-V-Liquid triple point
        vertices.append((tp["iii_v_liquid"]["T"], tp["iii_v_liquid"]["P"]))
        # Add melting curve points
        if len(T_v_curve) > 0:
            for T, P in zip(T_v_curve, P_v_curve):
                vertices.append((T, P))
        # Add V-VI-Liquid triple point
        vertices.append((tp["v_vi_liquid"]["T"], tp["v_vi_liquid"]["P"]))
        # Add II-V-VI triple point
        vertices.append((tp["ii_v_vi"]["T"], tp["ii_v_vi"]["P"]))
        
        return vertices
        
    elif phase_id == "ice_vi":
        # Ice VI: Tetragonal phase at high pressure
        # Bounded by: II-V-VI TP, V-VI-Liquid TP, VI-VII-Liquid TP, VI-VII-VIII TP
        
        T_vi_curve, P_vi_curve = _sample_melting_curve("ice_vi_melting", n_points)
        
        vertices = []
        # Start at II-V-VI triple point
        vertices.append((tp["ii_v_vi"]["T"], tp["ii_v_vi"]["P"]))
        # Add V-VI-Liquid triple point
        vertices.append((tp["v_vi_liquid"]["T"], tp["v_vi_liquid"]["P"]))
        # Add melting curve points
        if len(T_vi_curve) > 0:
            for T, P in zip(T_vi_curve, P_vi_curve):
                vertices.append((T, P))
        # Add VI-VII-Liquid triple point
        vertices.append((tp["vi_vii_liquid"]["T"], tp["vi_vii_liquid"]["P"]))
        # Add VI-VII-VIII triple point
        vertices.append((tp["vi_vii_viii"]["T"], tp["vi_vii_viii"]["P"]))
        # Close polygon with low temperature boundary
        vertices.append((220, 2100))
        vertices.append((220, 620))
        
        return vertices
        
    elif phase_id == "ice_vii":
        # Ice VII: Cubic phase at very high pressure
        # Bounded by: VI-VII-VIII TP, VI-VII-Liquid TP, high T/P boundary
        
        T_vii_curve, P_vii_curve = _sample_melting_curve("ice_vii_melting", n_points)
        
        vertices = []
        # Start at VI-VII-VIII triple point
        vertices.append((tp["vi_vii_viii"]["T"], tp["vi_vii_viii"]["P"]))
        # Add melting curve points
        if len(T_vii_curve) > 0:
            for T, P in zip(T_vii_curve, P_vii_curve):
                vertices.append((T, P))
        # Close polygon at high pressure/temperature
        vertices.append((450, 8000))
        vertices.append((280, 8000))
        
        return vertices
        
    elif phase_id == "ice_viii":
        # Ice VIII: Ordered form of Ice VII at low temperature
        # Bounded by: VI-VII-VIII TP and high pressure at low T
        vertices = [
            (100, 2100),                                       # Low T, lower P boundary
            (tp["vi_vii_viii"]["T"], tp["vi_vii_viii"]["P"]),  # VI-VII-VIII TP
            (280, 10000),                                       # High P at VI-VII-VIII T
            (100, 10000),                                       # High P at low T
        ]
        return vertices
    
    return None


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
    with smooth curved boundaries derived from IAPWS-certified melting curves.
    
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
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load phase metadata
    data = _load_phase_data()
    phases = data.get("phases", {})
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    
    # Set up logarithmic pressure scale if requested
    if use_log_scale:
        ax.set_xscale('log')
    
    # Define phases to plot (in order, back to front for proper layering)
    phases_to_plot = [
        "ice_viii",
        "ice_vii", 
        "ice_vi",
        "ice_v",
        "ice_ii",
        "ice_iii",
        "ice_ih",
    ]
    
    # Plot each phase region
    legend_patches = []
    for phase_id in phases_to_plot:
        if phase_id not in phases:
            continue
            
        # Build polygon using curved boundaries with many points for smoothness
        vertices = _build_phase_polygon_from_curves(phase_id, n_points=500)
        
        if vertices is None or len(vertices) < 3:
            continue
        
        # Convert (T, P) to plot coordinates
        # For log scale, need to handle carefully
        plot_vertices = np.array([[p, t] for t, p in vertices])
        
        # Create polygon patch
        color = PHASE_COLORS.get(phase_id, "#CCCCCC")
        poly = Polygon(plot_vertices, closed=True)
        poly.set_facecolor(color)
        poly.set_edgecolor("black")
        poly.set_linewidth(1.0)
        poly.set_alpha(0.6)
        ax.add_patch(poly)
        
        # Add label directly on the phase region
        centroid_T, centroid_P = _calculate_phase_centroid(phase_id)
        label = PHASE_LABELS.get(phase_id, phase_id)
        ax.text(
            centroid_P, centroid_T,
            label,
            fontsize=14,
            fontweight='bold',
            ha='center',
            va='center',
            color='black',
            alpha=0.8,
            zorder=5,
        )
        
        # Create legend entry (small patch)
        legend_patches.append(
            mpatches.Patch(color=color, label=PHASE_NAMES.get(phase_id, phase_id), alpha=0.6)
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
            ax.plot(P_curve, T_curve, color=color, linewidth=1.5, linestyle='-', alpha=0.8)
    
    # Mark triple points
    triple_point_names = [
        ("ih_iii_liquid", "Ih-III-L"),
        ("ih_ii_iii", "Ih-II-III"),
        ("ii_iii_v", "II-III-V"),
        ("iii_v_liquid", "III-V-L"),
        ("ii_v_vi", "II-V-VI"),
        ("v_vi_liquid", "V-VI-L"),
        ("vi_vii_liquid", "VI-VII-L"),
        ("vi_vii_viii", "VI-VII-VIII"),
    ]
    
    for tp_name, tp_label in triple_point_names:
        tp = get_triple_point(tp_name)
        ax.plot(
            tp["P"], tp["T"],
            'ko',  # Black circle
            markersize=5,
            markeredgecolor='white',
            markeredgewidth=0.5,
            zorder=6,
        )
        # Add small label
        ax.text(
            tp["P"] * 1.1, tp["T"],
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
        user_p, user_t,
        'ro',  # Red circle
        markersize=15,
        markeredgecolor='black',
        markeredgewidth=2,
        label=f"Your conditions\n({user_t:.1f} K, {user_p:.1f} MPa)",
        zorder=10,  # Ensure it's on top
    )
    
    # Set axis limits (using log scale range)
    if use_log_scale:
        ax.set_xlim(0.1, 10000)
    else:
        ax.set_xlim(0, 5000)
    ax.set_ylim(100, 500)
    
    # Add grid
    ax.grid(True, linestyle='--', alpha=0.5, which='both')
    
    # Labels and title
    ax.set_xlabel("Pressure (MPa)", fontsize=14, fontweight='bold')
    ax.set_ylabel("Temperature (K)", fontsize=14, fontweight='bold')
    ax.set_title("Water Ice Phase Diagram", fontsize=18, fontweight='bold', pad=20)
    
    # Add legend (smaller, in corner)
    ax.legend(
        handles=legend_patches,
        loc='upper right',
        fontsize=9,
        framealpha=0.9,
        ncol=1,
    )
    
    # Add note about data source
    ax.text(
        0.02, 0.02,
        "Data: IAPWS R14-08(2011)",
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
            f.write(f"# {tp_name}: T={tp['T']} K, P={tp['P']} MPa\n")
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
