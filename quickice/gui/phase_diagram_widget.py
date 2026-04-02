"""Interactive phase diagram widget for QuickIce GUI.

Provides a matplotlib canvas embedded in PySide6 that displays the ice phase diagram,
allows users to hover for coordinates, and click to select temperature/pressure conditions.
Detects the ice phase at the selected point and handles boundary clicks.

Classes:
    PhaseDiagramCanvas: Matplotlib canvas with phase diagram rendering
    PhaseDetector: Helper for detecting phase at given T,P
    PhaseDiagramPanel: Complete widget with canvas and info panel
"""

from typing import Tuple, Optional, Dict, List

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
from shapely.geometry import Point, Polygon as ShapelyPolygon

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Signal, Qt

from quickice.output.phase_diagram import (
    _build_phase_polygon_from_curves,
    _sample_melting_curve,
    PHASE_COLORS,
    PHASE_LABELS,
    IAPWS_MELTING_RANGES,
)
from quickice.phase_mapping import get_triple_point


class PhaseDetector:
    """Detects ice phase at given T,P conditions using shapely polygons.
    
    Builds phase polygons once at initialization for efficient lookup.
    Handles boundary detection using shapely's touches() method.
    """
    
    def __init__(self):
        """Initialize detector by building shapely polygons for all 12 phases."""
        self._phase_polygons: Dict[str, ShapelyPolygon] = {}
        
        # Build polygons for all 12 ice phases
        phase_ids = [
            "ice_ih", "ice_ic", "ice_ii", "ice_iii", "ice_v", "ice_vi",
            "ice_vii", "ice_viii", "ice_xi", "ice_ix", "ice_x", "ice_xv"
        ]
        
        for phase_id in phase_ids:
            vertices = _build_phase_polygon_from_curves(phase_id)
            if len(vertices) >= 3:
                # Vertices are (T, P) in MPa
                self._phase_polygons[phase_id] = ShapelyPolygon(vertices)
        
        # Build vapor polygon using IAPWS saturation curve
        # Vapor region is BELOW the liquid-vapor saturation curve
        # The polygon traces: bottom of graph → saturation curve → back along bottom
        try:
            from iapws import IAPWS97
            
            vapor_vertices = []
            
            # Start at bottom-left corner (50 K, P_min)
            P_min = 0.0001  # Minimum pressure on graph (log scale)
            vapor_vertices.append((50.0, P_min))
            
            # Go along bottom to the triple point temperature
            vapor_vertices.append((273.16, P_min))
            
            # Trace up along the saturation curve from 273.16K to 500K
            # The saturation curve is the UPPER boundary of the vapor region
            for T in np.linspace(273.16, 500, 50):
                try:
                    st = IAPWS97(T=T, x=0)  # Saturated liquid
                    vapor_vertices.append((T, st.P))
                except Exception:
                    pass
            
            # From the end of saturation curve (500K, P_sat), go down to bottom
            vapor_vertices.append((500.0, P_min))
            
            # Back along bottom to start
            vapor_vertices.append((50.0, P_min))
            
            if len(vapor_vertices) > 3:
                self._phase_polygons["vapor"] = ShapelyPolygon(vapor_vertices)
        except ImportError:
            pass  # IAPWS not available
    
    # Tolerance for boundary detection (pressure only)
    # Uses relative tolerance: 5% of pressure with 0.01 MPa floor
    #   - At P=0.1 MPa: tolerance = 0.01 MPa (avoids false boundary at low P)
    #   - At P=100 MPa: tolerance = 5.0 MPa
    #   - At P=1000 MPa: tolerance = 50.0 MPa (appropriate for high P)
    BOUNDARY_TOLERANCE_PRESSURE_FRAC = 0.05
    
    def detect_phase(self, temperature: float, pressure_mpa: float) -> Tuple[Optional[str], bool]:
        """Detect phase at given temperature and pressure.
        
        Args:
            temperature: Temperature in Kelvin
            pressure_mpa: Pressure in MPa (polygons use MPa)
        
        Returns:
            Tuple of (phase_name, is_boundary)
            - phase_name: Short form (e.g., "Ih") or "Multiple phases possible" or "Vapor" or "Liquid"
            - is_boundary: True if point is on boundary line between phases
        """
        point = Point(temperature, pressure_mpa)
        
        # Check containment in ice phase polygons first
        # Use covers() instead of contains() to include boundary points
        contained_phases: List[str] = []
        for phase_id, polygon in self._phase_polygons.items():
            if phase_id == "vapor":
                continue  # Check vapor separately after ice phases
            if polygon.covers(point):  # covers() includes boundary points
                contained_phases.append(phase_id)
        
        # If point is inside exactly one ice phase
        if len(contained_phases) == 1:
            # Check if near boundary (for practical clicks)
            near_boundary_phases = self._check_near_boundary(point, contained_phases[0])
            if len(near_boundary_phases) >= 2:
                names = [PHASE_LABELS.get(p, p) for p in near_boundary_phases]
                return f"{names[0]}/{names[1]}", True
            phase_short = PHASE_LABELS.get(contained_phases[0], contained_phases[0])
            return phase_short, False
        
        # If point is on boundary of multiple phases (covers catches this)
        if len(contained_phases) >= 2:
            names = [PHASE_LABELS.get(p, p) for p in contained_phases[:2]]
            return f"{names[0]}/{names[1]}", True
        
        # Check if in vapor region
        if "vapor" in self._phase_polygons:
            if self._phase_polygons["vapor"].covers(point):  # covers() includes boundary points
                return "Vapor", False
        
        # Check if on boundary (using buffer tolerance)
        boundary_phases = self._check_near_boundary(point)
        
        if len(boundary_phases) >= 2:
            # Format as "Phase1/Phase2" if exactly 2 phases
            if len(boundary_phases) == 2:
                names = [PHASE_LABELS.get(p, p) for p in boundary_phases]
                return f"{names[0]}/{names[1]}", True
            return "Multiple phases possible", True
        
        # No match - assume liquid region
        return "Liquid", False
    
    def _check_near_boundary(self, point: Point, inside_phase: Optional[str] = None) -> List[str]:
        """Check if point is near the boundary of multiple phases.
        
        Uses relative tolerance for pressure to handle both low and high pressure
        regions correctly. At low pressure (P=0.1 MPa), a small absolute tolerance
        avoids false boundary detection. At high pressure (P=1000 MPa), the relative
        tolerance scales appropriately.
        
        Args:
            point: Shapely Point to check (coordinates are T, P in MPa)
            inside_phase: If provided, check neighbors of this phase
        
        Returns:
            List of phase IDs that are near the boundary
        """
        boundary_phases: List[str] = []
        
        # Extract coordinates for relative tolerance calculation
        pressure = point.y
        
        # Calculate pressure tolerance: relative with minimum floor
        # At P=0.1 MPa: tol = max(0.01, 0.1*0.05) = 0.01 MPa
        # At P=100 MPa: tol = max(0.01, 5.0) = 5.0 MPa
        # At P=1000 MPa: tol = max(0.01, 50.0) = 50.0 MPa
        # Use only pressure tolerance for distance (T tolerance doesn't apply to P)
        tolerance = max(0.01, pressure * self.BOUNDARY_TOLERANCE_PRESSURE_FRAC)
        
        for phase_id, polygon in self._phase_polygons.items():
            # Check if the point is near the polygon boundary
            distance = polygon.boundary.distance(point)
            if distance < tolerance:
                # Also verify point is inside or very close to polygon
                # Use covers() to include boundary points
                if polygon.covers(point) or polygon.distance(point) < tolerance:
                    boundary_phases.append(phase_id)
        
        # If checking neighbors of an inside phase, ensure it's included
        if inside_phase and inside_phase not in boundary_phases:
            boundary_phases.insert(0, inside_phase)
        
        return boundary_phases


class PhaseDiagramCanvas(FigureCanvasQTAgg):
    """Interactive matplotlib canvas displaying the ice phase diagram.
    
    Renders all 12 ice phases using curve-based boundaries from IAPWS data.
    Emits signals when user hovers (for coordinate display) or clicks (for phase selection).
    """
    
    # Signal emitted when user clicks on diagram
    coordinates_selected = Signal(float, float)  # (temperature, pressure)
    
    # Signal emitted when phase info is available
    phase_info_ready = Signal(str, float, float)  # (phase_id, T, P)
    
    def __init__(self, parent=None):
        """Initialize the canvas with phase diagram rendering.
        
        Args:
            parent: Parent widget (optional)
        """
        # Create figure with wider aspect ratio for split view
        # Wider than CLI (12, 10) to fit in 600px wide panel while keeping short height
        self.fig = Figure(figsize=(14, 8), dpi=100)
        self.axes = self.fig.add_subplot(111)
        
        # Initialize parent
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Initialize state
        self._marker = None
        self._phase_detector = PhaseDetector()
        
        # Setup the phase diagram
        self._setup_diagram()
        
        # Connect event handlers
        self.mpl_connect('motion_notify_event', self._on_hover)
        self.mpl_connect('button_press_event', self._on_click)
    
    def _setup_diagram(self):
        """Render the complete phase diagram with all 12 phases."""
        # Set up logarithmic pressure scale (scientific convention)
        self.axes.set_yscale('log')
        
        # Set axis limits
        self.axes.set_xlim(50, 500)  # Temperature in Kelvin
        self.axes.set_ylim(0.1, 100000)  # Pressure in MPa (log scale: 0.1 to 100000 MPa)
        
        # Labels and title
        self.axes.set_xlabel("Temperature (K)", fontsize=12, fontweight='bold')
        self.axes.set_ylabel("Pressure (MPa)", fontsize=12, fontweight='bold')
        self.axes.set_title("Ice Phase Diagram", fontsize=14, fontweight='bold')
        
        # Define phases to plot (in order, back to front for proper layering)
        phases_to_plot = [
            "ice_x",      # Highest pressure
            "ice_viii",
            "ice_vii",
            "ice_vi",
            "ice_xv",     # Ordered VI (rendered after VI)
            "ice_v",
            "ice_ii",
            "ice_ix",     # Ordered III (rendered after II)
            "ice_iii",
            "ice_ih",
            "ice_xi",     # Ordered Ih (rendered after Ih)
            "ice_ic",     # Metastable
        ]
        
        # Plot each phase region
        for phase_id in phases_to_plot:
            self._plot_phase_region(phase_id)
        
        # Plot melting curves as lines (on top of filled regions)
        self._plot_melting_curves()
        
        # Plot liquid-vapor boundary
        self._plot_liquid_vapor_boundary()
        
        # Mark triple points
        self._plot_triple_points()
        
        # Add "Liquid" label
        self.axes.text(
            340, 50,  # T=340K, P=50 MPa
            "Liquid",
            fontsize=12,
            fontweight='bold',
            ha='center',
            va='center',
            color='black',
            alpha=0.8,
            zorder=5,
        )
        
        # Add "Vapor" label
        # Position: T=460K, P=0.5 MPa (same as CLI, below saturation curve)
        # At T=460K, P_sat=1.17 MPa, so P=0.5 MPa is in vapor region
        self.axes.text(
            460, 0.5,  # T=460K, P=0.5 MPa (same as CLI)
            "Vapor",
            fontsize=12,
            fontweight='bold',
            ha='center',
            va='center',
            color='black',
            alpha=0.8,
            zorder=5,
        )
        
        # Add grid
        self.axes.grid(True, linestyle='--', alpha=0.3, which='both')
        
        # Explicit margins to ensure labels are fully visible
        # Left margin needs to be larger for log-scale y-axis labels
        self.fig.subplots_adjust(left=0.15, right=0.98, top=0.92, bottom=0.12)
    
    def _plot_phase_region(self, phase_id: str):
        """Plot a single phase region with label at centroid.
        
        Args:
            phase_id: Phase identifier (e.g., "ice_ih")
        """
        vertices = _build_phase_polygon_from_curves(phase_id)
        
        if len(vertices) < 3:
            return
        
        # Convert vertices to numpy array for plotting
        plot_vertices = np.array(vertices)
        
        # Get phase color
        color = PHASE_COLORS.get(phase_id, "#CCCCCC")
        
        # Create polygon patch
        poly = Polygon(plot_vertices, closed=True)
        poly.set_facecolor(color)
        poly.set_edgecolor("black")
        poly.set_linewidth(1.5)
        poly.set_alpha(0.6)
        self.axes.add_patch(poly)
        
        # Add label at centroid using shapely
        shapely_poly = ShapelyPolygon(vertices)
        centroid = shapely_poly.centroid
        label = PHASE_LABELS.get(phase_id, phase_id)
        
        self.axes.text(
            centroid.x, centroid.y,
            label,
            fontsize=12,
            fontweight='bold',
            ha='center',
            va='center',
            color='black',
            alpha=0.8,
            zorder=5,
        )
    
    def _plot_melting_curves(self):
        """Plot melting curves as black lines on top of phase regions."""
        melting_curves = [
            ("ice_ih_melting", "#000000"),
            ("ice_iii_melting", "#333333"),
            ("ice_v_melting", "#555555"),
            ("ice_vi_melting", "#777777"),
            ("ice_vii_melting", "#999999"),
        ]
        
        for curve_name, color in melting_curves:
            T_curve, P_curve_mpa = _sample_melting_curve(curve_name, n_points=200)
            
            if len(T_curve) > 0:
                # Data is already in MPa
                self.axes.plot(
                    T_curve, P_curve_mpa,
                    color=color,
                    linewidth=2.0,
                    linestyle='-',
                    alpha=0.8,
                    zorder=7
                )
    
    def _plot_liquid_vapor_boundary(self):
        """Plot liquid-vapor boundary using IAPWS saturation curve."""
        try:
            from iapws import IAPWS97
            
            lv_T = np.linspace(273.16, 500, 50)
            lv_P = []
            
            for T in lv_T:
                try:
                    st = IAPWS97(T=T, x=0)  # Saturated liquid
                    # IAPWS returns MPa
                    lv_P.append(st.P)
                except Exception:
                    pass
            
            if len(lv_P) > 0:
                lv_T = lv_T[:len(lv_P)]
                self.axes.plot(
                    lv_T, lv_P,
                    color='blue',
                    linewidth=2.0,
                    linestyle='-',
                    alpha=0.8,
                    zorder=7
                )
        except ImportError:
            # IAPWS not available, skip liquid-vapor boundary
            pass
    
    def _plot_triple_points(self):
        """Mark triple points on the diagram."""
        triple_point_names = [
            ("Ih_III_Liquid", "Ih-III-L"),
            ("Ih_II_III", "Ih-II-III"),
            ("II_III_V", "II-III-V"),
            ("III_V_Liquid", "III-V-L"),
            ("II_V_VI", "II-V-VI"),
            ("V_VI_Liquid", "V-VI-L"),
            ("VI_VII_Liquid", "VI-VII-L"),
            ("VI_VII_VIII", "VI-VII-VIII"),
            ("III_IX_Transition", "III-IX"),
            ("VII_X_Transition", "VII-X"),
            ("VI_XV_Transition", "VI-XV"),
            ("VII_VIII_X", "VII-VIII-X"),
        ]
        
        for tp_name, tp_label in triple_point_names:
            tp_T, tp_P_mpa = get_triple_point(tp_name)
            # Data is already in MPa
            
            self.axes.plot(
                tp_T, tp_P_mpa,
                'o',  # Circle marker
                markersize=4,
                markerfacecolor='black',
                markeredgecolor='white',
                markeredgewidth=0.5,
                zorder=8,
            )
            
            # Add label
            if tp_P_mpa < 1.0:
                # For very low pressure, position label to the right
                self.axes.text(
                    tp_T + 5, 0.3,
                    tp_label,
                    fontsize=7,
                    ha='left',
                    va='center',
                    color='black',
                    alpha=0.7,
                    zorder=8,
                )
            else:
                self.axes.text(
                    tp_T, tp_P_mpa * 1.15,
                    tp_label,
                    fontsize=7,
                    ha='left',
                    va='center',
                    color='black',
                    alpha=0.7,
                    zorder=8,
                )
    
    def _on_hover(self, event):
        """Handle mouse motion for hover tooltip.
        
        Note: The actual tooltip/coordinate display is handled by the
        PhaseDiagramPanel's info_label. This method is a placeholder
        for potential future enhancements.
        
        Args:
            event: MouseEvent from matplotlib
        """
        # Hover is handled by PhaseDiagramPanel via coordinates signal
        # This placeholder allows future enhancements (e.g., custom tooltips)
        pass
    
    def _on_click(self, event):
        """Handle mouse click for phase selection.
        
        Args:
            event: MouseEvent from matplotlib
        """
        # Check if click is within axes and has valid coordinates
        if not event.inaxes or event.xdata is None or event.ydata is None:
            return
        
        temperature = event.xdata
        pressure_mpa = event.ydata  # Already in MPa from axes
        
        # Place marker at clicked position
        self.set_marker(temperature, pressure_mpa)
        
        # Emit signal with selected coordinates
        self.coordinates_selected.emit(temperature, pressure_mpa)
        
        # Detect phase at click location and emit phase info
        phase_name, is_boundary = self._phase_detector.detect_phase(temperature, pressure_mpa)
        # Use phase_name if available, otherwise "unknown"
        phase_id = phase_name if phase_name else "unknown"
        self.phase_info_ready.emit(phase_id, temperature, pressure_mpa)
    
    def set_marker(self, temperature: float, pressure: float):
        """Place a red circle marker at the specified coordinates.
        
        Removes any existing marker before placing new one.
        
        Args:
            temperature: Temperature in Kelvin
            pressure: Pressure in MPa
        """
        # Remove existing marker if present
        if self._marker is not None:
            self._marker.remove()
        
        # Create new marker
        self._marker, = self.axes.plot(
            temperature, pressure,
            'o',  # Circle marker
            markersize=8,
            markerfacecolor='red',
            markeredgecolor='black',
            markeredgewidth=1.5,
            zorder=10,  # Place on top
        )
        
        # Redraw
        self.draw_idle()
    
    def detect_phase_at(self, temperature: float, pressure_mpa: float) -> Tuple[Optional[str], bool]:
        """Detect ice phase at given coordinates.
        
        Args:
            temperature: Temperature in Kelvin
            pressure_mpa: Pressure in MPa
        
        Returns:
            Tuple of (phase_name, is_boundary) from PhaseDetector
        """
        return self._phase_detector.detect_phase(temperature, pressure_mpa)


class PhaseDiagramPanel(QWidget):
    """Complete phase diagram widget with canvas and info panel.
    
    Combines PhaseDiagramCanvas with a QLabel for displaying coordinates
    and phase information. Handles hover events to show live coordinates
    and click events to display selected phase.
    """
    
    def __init__(self, parent=None):
        """Initialize the panel with canvas and info label.
        
        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Create canvas
        self.diagram_canvas = PhaseDiagramCanvas(self)
        layout.addWidget(self.diagram_canvas)
        
        # Create info label
        self.info_label = QLabel("Click on diagram to select T, P")
        self.info_label.setStyleSheet(
            "padding: 8px; "
            "background-color: #f5f5f5; "
            "border: 1px solid #ddd; "
            "border-radius: 3px;"
        )
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)
        
        # Set crosshair cursor on canvas
        self.diagram_canvas.setCursor(Qt.CrossCursor)
        
        # Connect canvas signals
        self.diagram_canvas.coordinates_selected.connect(self._on_coordinates_selected)
        
        # Connect hover event for live coordinate display
        self.diagram_canvas.mpl_connect('motion_notify_event', self._on_hover)
    
    def _on_hover(self, event):
        """Handle hover over canvas to display live coordinates.
        
        Args:
            event: MouseEvent from matplotlib
        """
        if event.inaxes and event.xdata is not None and event.ydata is not None:
            temperature = event.xdata
            pressure = event.ydata
            
            # Update info label with current coordinates
            self.info_label.setText(
                f"T = {temperature:.1f} K, P = {pressure:.1f} MPa"
            )
            self.info_label.setStyleSheet(
                "padding: 8px; "
                "background-color: #e3f2fd; "
                "border: 1px solid #90caf9; "
                "border-radius: 3px;"
            )
    
    def _on_coordinates_selected(self, temperature: float, pressure: float):
        """Handle coordinate selection from canvas click.
        
        Detects the phase at the selected coordinates and updates
        the info label accordingly.
        
        Args:
            temperature: Temperature in Kelvin
            pressure: Pressure in MPa
        """
        # Detect phase at selected coordinates
        phase_name, is_boundary = self.diagram_canvas.detect_phase_at(temperature, pressure)
        
        # Update info label
        if is_boundary:
            self.info_label.setText(
                f"⚠️ {phase_name}\n"
                f"(T = {temperature:.1f} K, P = {pressure:.1f} MPa)"
            )
            self.info_label.setStyleSheet(
                "padding: 8px; "
                "background-color: #fff3cd; "
                "border: 1px solid #ffc107; "
                "border-radius: 3px;"
            )
        elif phase_name:
            # Handle Vapor and Liquid (not ice phases)
            if phase_name in ("Vapor", "Liquid"):
                self.info_label.setText(
                    f"Selected: {phase_name}\n"
                    f"(T = {temperature:.1f} K, P = {pressure:.1f} MPa)"
                )
            else:
                self.info_label.setText(
                    f"Selected: Ice {phase_name}\n"
                    f"(T = {temperature:.1f} K, P = {pressure:.1f} MPa)"
                )
            self.info_label.setStyleSheet(
                "padding: 8px; "
                "background-color: #d4edda; "
                "border: 1px solid #28a745; "
                "border-radius: 3px;"
            )
        else:
            # No phase detected (should not reach here after adding Liquid)
            self.info_label.setText(
                f"Unknown region\n"
                f"(T = {temperature:.1f} K, P = {pressure:.1f} MPa)"
            )
            self.info_label.setStyleSheet(
                "padding: 8px; "
                "background-color: #f5f5f5; "
                "border: 1px solid #ddd; "
                "border-radius: 3px;"
            )
    
    def set_coordinates(self, temperature: float, pressure: float):
        """Set marker position programmatically from external input.
        
        This creates bidirectional binding: typing in input fields
        updates the diagram marker.
        
        Args:
            temperature: Temperature in Kelvin
            pressure: Pressure in MPa
        """
        # Set marker on canvas
        self.diagram_canvas.set_marker(temperature, pressure)
        
        # Detect phase and update info label
        phase_name, is_boundary = self.diagram_canvas.detect_phase_at(temperature, pressure)
        
        # Reuse the _on_coordinates_selected logic for label update
        self._on_coordinates_selected(temperature, pressure)


# Convenience exports
__all__ = ['PhaseDiagramCanvas', 'PhaseDetector', 'PhaseDiagramPanel']
