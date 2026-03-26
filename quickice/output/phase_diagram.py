"""Phase diagram generator for ice polymorph visualization.

Generates publication-quality phase diagrams showing user's operating conditions.
Outputs PNG, SVG, and text data files.
"""

import json
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


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
}


def _load_phase_data() -> dict:
    """Load ice phase boundary data from JSON file.
    
    Returns:
        Dictionary with phase information
    """
    data_path = Path(__file__).parent.parent / "phase_mapping" / "data" / "ice_phases.json"
    with open(data_path, "r") as f:
        return json.load(f)


def _create_phase_polygon(phase_info: dict) -> Optional[mpatches.Polygon]:
    """Create a polygon patch for a phase region.
    
    Args:
        phase_info: Dictionary with phase boundaries
        
    Returns:
        Polygon patch or None if boundaries invalid
    """
    boundaries = phase_info.get("boundaries", {})
    t_bounds = boundaries.get("temperature", {})
    p_bounds = boundaries.get("pressure", {})
    
    t_min = t_bounds.get("min", 0)
    t_max = t_bounds.get("max", 500)
    p_min = p_bounds.get("min", 0)
    p_max = p_bounds.get("max", 10000)
    
    # Create rectangle vertices (P on x-axis, T on y-axis)
    vertices = np.array([
        [p_min, t_min],
        [p_max, t_min],
        [p_max, t_max],
        [p_min, t_max],
    ])
    
    return mpatches.Polygon(vertices, closed=True)


def generate_phase_diagram(
    user_t: float,
    user_p: float,
    output_dir: str | Path,
    figsize: tuple[float, float] = (10, 8),
    dpi: int = 300,
) -> list[str]:
    """Generate phase diagram with user's operating conditions marked.
    
    Args:
        user_t: User's temperature in Kelvin
        user_p: User's pressure in MPa
        output_dir: Directory to save output files
        figsize: Figure size as (width, height) in inches
        dpi: Resolution for PNG output
        
    Returns:
        List of paths to generated files
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load phase data
    data = _load_phase_data()
    phases = data.get("phases", {})
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    
    # Plot each phase region
    legend_patches = []
    for phase_id, phase_info in phases.items():
        poly = _create_phase_polygon(phase_info)
        if poly is not None:
            color = PHASE_COLORS.get(phase_id, "#CCCCCC")
            poly.set_facecolor(color)
            poly.set_edgecolor("black")
            poly.set_linewidth(0.5)
            poly.set_alpha(0.7)
            ax.add_patch(poly)
            
            # Create legend entry
            legend_patches.append(
                mpatches.Patch(color=color, label=phase_info.get("name", phase_id), alpha=0.7)
            )
    
    # Plot user's T,P point
    ax.plot(
        user_p, user_t,
        'ro',  # Red circle
        markersize=15,
        markeredgecolor='black',
        markeredgewidth=2,
        label=f"Your conditions ({user_t:.1f} K, {user_p:.1f} MPa)",
        zorder=10,  # Ensure it's on top
    )
    
    # Set axis limits
    ax.set_xlim(0, 5000)
    ax.set_ylim(0, 500)
    
    # Add grid
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Labels and title
    ax.set_xlabel("Pressure (MPa)", fontsize=14)
    ax.set_ylabel("Temperature (K)", fontsize=14)
    ax.set_title("Water Ice Phase Diagram", fontsize=16)
    
    # Add legend
    ax.legend(handles=legend_patches, loc='upper right', fontsize=10)
    
    # Tight layout
    plt.tight_layout()
    
    # Generate output paths
    png_path = output_dir / "phase_diagram.png"
    svg_path = output_dir / "phase_diagram.svg"
    txt_path = output_dir / "phase_diagram_data.txt"
    
    # Save files
    plt.savefig(png_path, dpi=dpi, bbox_inches='tight')
    plt.savefig(svg_path, format='svg', bbox_inches='tight')
    
    # Write text data file
    with open(txt_path, 'w') as f:
        f.write("# Water Ice Phase Diagram Data\n")
        f.write("# Source: Scientific literature (NIST, Wikipedia Phases of Ice)\n")
        f.write("# Columns: T(K)\tP(MPa)\tPhase\tCrystalForm\tDensity(g/cm³)\n")
        f.write("#\n")
        
        for phase_id, phase_info in phases.items():
            boundaries = phase_info.get("boundaries", {})
            t_bounds = boundaries.get("temperature", {})
            p_bounds = boundaries.get("pressure", {})
            
            t_min = t_bounds.get("min", 0)
            t_max = t_bounds.get("max", 500)
            p_min = p_bounds.get("min", 0)
            p_max = p_bounds.get("max", 10000)
            
            name = phase_info.get("name", phase_id)
            crystal = phase_info.get("crystal_form", "unknown")
            density = phase_info.get("density", 0.0)
            
            f.write(f"{t_min}\t{p_min}\t{name}\t{crystal}\t{density}\n")
            f.write(f"{t_max}\t{p_max}\t{name}\t{crystal}\t{density}\n")
    
    # Close figure to prevent memory leak
    plt.close(fig)
    
    return [str(png_path), str(svg_path), str(txt_path)]
