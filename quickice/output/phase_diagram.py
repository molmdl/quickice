"""Phase diagram generator for ice polymorph visualization.

Generates publication-quality phase diagrams using PHASE_POLYGONS
as single source of truth for consistency with phase lookup.

Outputs PNG, SVG, and text data files.
"""

from pathlib import Path
from typing import Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon

from quickice.phase_mapping.data.ice_boundaries import (
    TRIPLE_POINTS,
    MELTING_CURVE_COEFFICIENTS,
    PHASE_POLYGONS,
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
    using PHASE_POLYGONS as single source of truth for consistency with lookup.
    
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
    phases_to_plot = [
        "ice_viii",
        "ice_vii", 
        "ice_vi",
        "ice_v",
        "ice_ii",
        "ice_iii",
        "ice_ih",
    ]
    
    # Plot each phase region using PHASE_POLYGONS
    for phase_id in phases_to_plot:
        if phase_id not in PHASE_POLYGONS:
            continue
            
        # Get vertices from PHASE_POLYGONS (single source of truth)
        vertices = PHASE_POLYGONS[phase_id]
        
        if vertices is None or len(vertices) < 3:
            continue
        
        # Vertices are (T, P) tuples, use directly for plotting (x=T, y=P)
        plot_vertices = np.array(vertices)
        
        # Create polygon patch
        color = PHASE_COLORS.get(phase_id, "#CCCCCC")
        poly = Polygon(plot_vertices, closed=True)
        poly.set_facecolor(color)
        poly.set_edgecolor("black")
        poly.set_linewidth(1.5)
        poly.set_alpha(0.6)
        ax.add_patch(poly)
        
        # Add label directly on the phase region using shapely centroid
        # Note: vertices are (T, P), so centroid.x=T, centroid.y=P
        # Plot coordinates are (x=T, y=P), so we use directly
        shapely_poly = ShapelyPolygon(vertices)
        centroid = shapely_poly.centroid
        label = PHASE_LABELS.get(phase_id, phase_id)
        ax.text(
            centroid.x, centroid.y,  # Plot: x=T, y=P
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
            ax.plot(T_curve, P_curve, color=color, linewidth=1.5, linestyle='-', alpha=0.8)
    
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
            tp["T"], tp["P"],
            'ko',  # Black circle
            markersize=5,
            markeredgecolor='white',
            markeredgewidth=0.5,
            zorder=6,
        )
        # Add small label
        ax.text(
            tp["T"], tp["P"] * 1.1,
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
    ax.set_xlim(100, 500)  # Temperature range (linear)
    if use_log_scale:
        ax.set_ylim(0.1, 10000)  # Pressure range (log scale)
    else:
        ax.set_ylim(0, 5000)  # Pressure range (linear)
    
    # Add grid
    ax.grid(True, linestyle='--', alpha=0.5, which='both')
    
    # Labels and title
    ax.set_xlabel("Temperature (K)", fontsize=14, fontweight='bold')
    ax.set_ylabel("Pressure (MPa)", fontsize=14, fontweight='bold')
    ax.set_title("Water Ice Phase Diagram", fontsize=18, fontweight='bold', pad=20)
    
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
