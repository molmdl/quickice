# Phase 09: Interactive Phase Diagram - Research

**Researched:** 2026-04-01
**Domain:** PySide6 + Matplotlib interactive GUI development
**Confidence:** HIGH

## Summary

This phase implements an interactive ice phase diagram in the QuickIce GUI, allowing users to visually select thermodynamic conditions (temperature and pressure) by clicking on a rendered phase diagram. The implementation uses Matplotlib embedded in PySide6 via FigureCanvasQTAgg, with click and hover event handlers to capture user interactions. Phase region detection uses shapely's geometric predicates (contains/touches), and selected coordinates populate the input fields from Phase 8.

**Primary recommendation:** Use FigureCanvasQTAgg for embedding, connect to motion_notify_event for hover tooltips and button_press_event for click selection, use shapely Polygon.contains() for phase detection, and implement colorblind-friendly pastel colors per Paul Tol's color scheme.

## Standard Stack

The established libraries/tools for interactive matplotlib in PySide6:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PySide6-Essentials | >= 6.11.0 | Core Qt bindings | Qt Company official, LGPL licensed |
| PySide6-Addons | >= 6.11.0 | Additional widgets | Official Qt extensions |
| matplotlib | >= 3.8.0 | Plotting library | Standard Python plotting, supports Qt embedding |
| shapely | >= 2.0.0 | Geometric predicates | Point-in-polygon detection for phase regions |

### Installation
```bash
# NOT auto-installing per project constraints - add to env.yml first
conda install matplotlib shapely
# OR
pip install matplotlib shapely
```

### Alternative Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FigureCanvasQTAgg | FigureCanvasQTAgg from backend_qtagg | Qt-specific, required for PySide6 |
| shapely.contains() | Custom point-in-polygon | shapely is more robust, handles complex boundaries |
| PySide6 tooltips | Matplotlib annotations | PySide6 tooltips work at window level, matplotlib annotations track with plot |

## Architecture Patterns

### Recommended Project Structure
```
quickice/
├── gui/
│   ├── __init__.py
│   ├── main_window.py          # Contains split view layout
│   ├── view.py                 # InputPanel + PhaseDiagramPanel
│   ├── viewmodel.py            # Business logic
│   ├── phase_diagram.py        # NEW: Phase diagram rendering
│   └── workers.py              # QThread workers
├── phase_mapping/
│   ├── lookup.py               # Existing: lookup_phase function
│   └── solid_boundaries.py     # Existing: boundary curve functions
└── output/
    └── phase_diagram.py        # Existing: static diagram generation
```

### Pattern 1: Embedding Matplotlib in PySide6

**What:** Use FigureCanvasQTAgg to embed matplotlib figure in PySide6 widget
**When to use:** Always for Qt-embedded matplotlib

**Implementation:**
```python
# Source: Matplotlib documentation - Embed in Qt
# https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

class PhaseDiagramCanvas(FigureCanvasQTAgg):
    """Interactive phase diagram canvas."""
    
    def __init__(self, parent=None):
        fig = Figure(figsize=(6, 5), dpi=100)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.set_parent(parent)
        
        # Setup the phase diagram
        self._setup_diagram()
        
        # Connect event handlers
        self.mpl_connect('motion_notify_event', self._on_motion)
        self.mpl_connect('button_press_event', self._on_click)
    
    def _setup_diagram(self):
        """Render the phase diagram."""
        # Reuse logic from quickice.output.phase_diagram
        # Build polygons using _build_phase_polygon_from_curves
        # Set axis limits, labels, title
        pass
    
    def _on_motion(self, event):
        """Handle mouse motion for hover tooltip."""
        if event.inaxes and event.xdata is not None and event.ydata is not None:
            # Update tooltip with T, P coordinates
            self._update_tooltip(f"T={event.xdata:.1f} K, P={event.ydata:.0f} bar")
        else:
            self._hide_tooltip()
    
    def _on_click(self, event):
        """Handle mouse click for phase selection."""
        if event.inaxes and event.xdata is not None and event.ydata is not None:
            # Emit signal with selected T, P
            self.phase_selected.emit(event.xdata, event.ydata)
```

### Pattern 2: Click Event Handling and Coordinate Mapping

**What:** Convert pixel coordinates to data coordinates using matplotlib events
**When to use:** For any click/hover interaction on matplotlib figure

**Implementation:**
```python
# Source: Matplotlib documentation - Mouse move and click events
# https://matplotlib.org/stable/gallery/event_handling/coords_demo.html

def _on_click(self, event):
    """Handle button press event.
    
    Args:
        event: MouseEvent with xdata, ydata in data coordinates
    """
    # Check if click is within axes
    if not event.inaxes:
        return
    
    # event.xdata and event.ydata are already in data coordinates
    # (Temperature in K, Pressure in bar)
    temperature = event.xdata
    pressure = event.ydata
    
    print(f"Clicked at T={temperature:.1f} K, P={pressure:.0f} bar")
```

### Pattern 3: Phase Region Detection (Point-in-Polygon)

**What:** Use shapely to detect which phase region contains the clicked point
**When to use:** For determining phase at clicked T,P coordinates

**Implementation:**
```python
# Source: Shapely documentation - Geometric predicates
# https://shapely.readthedocs.io/en/stable/manual.html

from shapely.geometry import Point, Polygon
from quickice.output.phase_diagram import _build_phase_polygon_from_curves

class PhaseDetector:
    """Detects ice phase at given T,P conditions."""
    
    def __init__(self):
        # Build phase polygons once
        self._phase_polygons = {}
        for phase_id in ["ice_ih", "ice_ii", "ice_iii", "ice_v", "ice_vi", 
                         "ice_vii", "ice_viii", "ice_xi", "ice_ix", "ice_x", "ice_xv"]:
            vertices = _build_phase_polygon_from_curves(phase_id)
            if len(vertices) >= 3:
                self._phase_polygons[phase_id] = Polygon(vertices)
    
    def detect_phase(self, temperature: float, pressure: float) -> tuple[str, bool]:
        """Detect phase at given T,P.
        
        Args:
            temperature: Temperature in Kelvin
            pressure: Pressure in bar
            
        Returns:
            Tuple of (phase_id, is_boundary)
            phase_id: Phase identifier (e.g., "ice_ih") or None
            is_boundary: True if on boundary line between phases
        """
        from quickice.output.phase_diagram import PHASE_LABELS
        
        point = Point(temperature, pressure)
        
        # Check containment in each phase polygon
        contained_phases = []
        for phase_id, polygon in self._phase_polygons.items():
            if polygon.contains(point):
                contained_phases.append(phase_id)
        
        # Check boundary touches
        boundary_phases = []
        for phase_id, polygon in self._phase_polygons.items():
            if polygon.touches(point):
                boundary_phases.append(phase_id)
        
        if len(contained_phases) == 1:
            # Single phase - return the phase name
            phase_short = PHASE_LABELS.get(contained_phases[0], contained_phases[0])
            return phase_short, False
        elif len(boundary_phases) >= 2:
            # On boundary - multiple phases possible
            return "Multiple phases possible", True
        else:
            # No match or liquid region
            return None, False
```

### Pattern 4: Marker Rendering

**What:** Render selection marker (circle) at clicked position
**When to use:** For visual feedback after click

**Implementation:**
```python
# Source: Matplotlib documentation - Scatter plot markers
# https://matplotlib.org/stable/gallery/shapes_and_collections/scatter.html

class PhaseDiagramCanvas(FigureCanvasQTAgg):
    # ... continued from Pattern 1
    
    def __init__(self, ...):
        # ... previous code ...
        self._marker = None  # Store marker artist
    
    def set_marker(self, temperature: float, pressure: float):
        """Place marker at specified T,P coordinates.
        
        Args:
            temperature: Temperature in K
            pressure: Pressure in bar
        """
        # Remove existing marker
        if self._marker is not None:
            self._marker.remove()
        
        # Create new marker - small circle (5-8px)
        self._marker, = self.axes.plot(
            temperature, pressure,
            'o',  # Circle marker
            markersize=8,
            markerfacecolor='red',
            markeredgecolor='black',
            markeredgewidth=1.5,
            zorder=10,  # On top of everything
        )
        self.draw_idle()
    
    def remove_marker(self):
        """Remove selection marker."""
        if self._marker is not None:
            self._marker.remove()
            self._marker = None
            self.draw_idle()
```

### Pattern 5: Tooltip and Info Panel

**What:** Show live coordinates on hover, show phase name on click
**When to use:** Per CONTEXT.md requirements

**Implementation - Hover Tooltip:**
```python
# Use matplotlib's annotation for hover tooltip
# Source: Matplotlib documentation - Annotating plots
# https://matplotlib.org/stable/gallery/text_labels_and_annotations/annotation_basic.html

class PhaseDiagramCanvas(FigureCanvasQTAgg):
    def __init__(self, ...):
        # ... previous code ...
        
        # Create annotation for tooltip
        self._tooltip = self.axes.annotate(
            "",
            xy=(0, 0),
            xytext=(-20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
            visible=False,
        )
    
    def _update_tooltip(self, text: str, x: float, y: float):
        """Update tooltip position and text."""
        self._tooltip.set_text(text)
        self._tooltip.xy = (x, y)
        self._tooltip.set_visible(True)
        self.draw_idle()
```

**Implementation - Info Panel (Qt):**
```python
# In view.py - create dedicated info panel below diagram
from PySide6.QtWidgets import QLabel, QVBoxLayout

class PhaseDiagramPanel(QWidget):
    """Panel containing phase diagram and info display."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Diagram canvas
        self.diagram_canvas = PhaseDiagramCanvas()
        layout.addWidget(self.diagram_canvas)
        
        # Info panel below diagram
        self.info_label = QLabel("Click on diagram to select T, P")
        self.info_label.setStyleSheet("padding: 4px; background: #f0f0f0;")
        layout.addWidget(self.info_label)
        
        # Connect canvas signals
        self.diagram_canvas.phase_selected.connect(self._on_phase_selected)
    
    def _on_phase_selected(self, temperature: float, pressure: float):
        """Handle phase selection."""
        # Detect phase
        detector = PhaseDetector()
        phase_name, is_boundary = detector.detect_phase(temperature, pressure)
        
        # Update info panel
        if is_boundary:
            self.info_label.setText(f"{phase_name}")
            self.info_label.setStyleSheet("padding: 4px; background: #fff3cd;")
        else:
            self.info_label.setText(f"Selected: {phase_name} (T={temperature:.1f} K, P={pressure:.0f} bar)")
            self.info_label.setStyleSheet("padding: 4px; background: #d4edda;")
```

### Pattern 6: Integration with Phase 8 Input Fields

**What:** When user clicks diagram, populate the existing T,P input fields
**When to use:** Per CONTEXT.md requirement DIAGRAM-04

**Implementation:**
```python
# In main_window.py - connect diagram to input panel
class MainWindow(QMainWindow):
    def __init__(self, ...):
        # ... existing setup ...
        
        # Create phase diagram panel
        self.diagram_panel = PhaseDiagramPanel()
        
        # Connect diagram selection to input panel
        self.diagram_panel.diagram_canvas.phase_selected.connect(
            self._on_diagram_selected
        )
    
    def _on_diagram_selected(self, temperature: float, pressure: float):
        """Handle diagram selection - populate input fields."""
        # Set values in input panel
        self.input_panel.temp_input.setText(f"{temperature:.1f}")
        self.input_panel.pressure_input.setText(f"{pressure:.0f}")
```

### Pattern 7: Colorblind-Friendly Color Palette

**What:** Use publication-style colors distinguishable by colorblind users
**When to use:** Per CONTEXT.md visual rendering requirements

**Implementation - Paul Tol's Color Scheme (Bright, Colorblind-friendly):**
```python
# Source: Paul Tol's color schemes (https://www.sron.nl/~pault/)
# "Bright" scheme - colorblind-friendly, grayscale-printable

PHASE_COLORS_COLORBLIND = {
    "ice_ih": "#BBCCEE",   # Light blue (distinct from II)
    "ice_ic": "#A0CBE2",   # Sky blue
    "ice_ii": "#0000FF",   # Blue (distinct from Ih)
    "ice_iii": "#00DD00",  # Green (distinct from V)
    "ice_v": "#00BB00",    # Dark green
    "ice_vi": "#FFA500",   # Orange (distinct from VII)
    "ice_vii": "#FF0000",  # Red
    "ice_viii": "#880000", # Dark red
    "ice_xi": "#CCBBFF",   # Light purple (distinct from Ic)
    "ice_ix": "#00EE00",   # Bright green
    "ice_x": "#8800BB",    # Purple
    "ice_xv": "#DDDDDD",   # Gray (distinct from all)
    "liquid": "#44CCFF",   # Light blue (distinct from all ice)
}

# Alternative: Matplotlib's qualitative colormaps are also colorblind-friendly
# Use "Pastel1" or "Paired" for phase regions
```

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Point-in-polygon | Custom ray-casting | shapely.contains() | Handles complex boundaries, numerical robustness |
| Qt + Matplotlib integration | Raw QWidget + draw | FigureCanvasQTAgg | Event handling, resize, DPI scaling built-in |
| Coordinate conversion | Manual pixel-to-data | event.xdata, event.ydata | Already handles axis transforms, log scales |
| Crosshair cursor | Qt cursor changes | CSS cursor or Qt override | Can conflict with matplotlib event handling |

**Key insight:** Matplotlib's event system (event.xdata, event.ydata) already handles coordinate transformations including log scales. shapely provides robust geometric predicates that handle numerical edge cases.

## Common Pitfalls

### Pitfall 1: Log Scale Pressure Axis
**What goes wrong:** Click coordinates don't match display coordinates
**Why it happens:** Pressure axis uses log scale (per CONTEXT.md), pixel-to-data conversion must account for this
**How to avoid:** matplotlib's event.xdata/ydata already handles this; verify by testing at known T,P points

### Pitfall 2: Click Outside Axes
**What goes wrong:** Click handlers fire with None values
**Why it happens:** Event.inaxes is False when clicking on axis labels, margins, etc.
**How to avoid:** Always check `if event.inaxes and event.xdata is not None`

### Pitfall 3: Phase Boundary Detection
**What goes wrong:** Clicking on boundary line returns ambiguous or no phase
**Why it happens:** Point exactly on polygon edge may not be detected as "inside"
**How to avoid:** Use shapely's touches() in addition to contains(), implement "Multiple phases possible" message per CONTEXT.md

### Pitfall 4: Memory Leaks with Matplotlib in Qt
**What goes wrong:** Figure objects not cleaned up, memory grows
**Why it happens:** Not calling figure.clear() or using deleteLater pattern
**How to avoid:** Reuse single Figure instance, clear artists before redrawing

### Pitfall 5: Pressure Unit Mismatch
**What goes wrong:** Phase lookup fails because units wrong
**Why it happens:** Diagram shows bar, lookup_phase expects MPa
**How to avoid:** Convert bar to MPa (1 bar = 0.1 MPa) before calling lookup_phase

### Pitfall 6: Missing Boundary Curves
**What goes wrong:** Phase regions have gaps or overlaps
**Why it happens:** Reusing only filled regions without melting curves
**How to avoid:** Include melting curve rendering from phase_diagram.py for proper boundaries

## Code Examples

### Example 1: Complete Phase Diagram Panel with Events
```python
# Source: Based on Matplotlib Qt embedding + event handling examples
# https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html
# https://matplotlib.org/stable/gallery/event_handling/coords_demo.html

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Signal
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from quickice.output.phase_diagram import (
    generate_phase_diagram,
    PHASE_COLORS,
    PHASE_LABELS,
)

class PhaseDiagramPanel(QWidget):
    """Interactive phase diagram panel."""
    
    # Signal emitted when T,P selected from diagram
    coordinates_selected = Signal(float, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._detector = PhaseDetector()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create matplotlib canvas
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.axes = self.figure.add_subplot(111)
        
        # Setup diagram
        self._draw_diagram()
        
        # Connect events
        self.canvas.mpl_connect('motion_notify_event', self._on_hover)
        self.canvas.mpl_connect('button_press_event', self._on_click)
        
        layout.addWidget(self.canvas)
        
        # Info label
        self.info_label = QLabel("Click on diagram to select T, P")
        self.info_label.setStyleSheet("padding: 4px; background: #f5f5f5;")
        layout.addWidget(self.info_label)
    
    def _draw_diagram(self):
        """Draw the phase diagram regions."""
        # Use logic from quickice.output.phase_diagram
        # Plot filled polygons for each phase
        # Add melting curves and boundary lines
        # Set axis labels and limits
        self.axes.set_xlabel("Temperature (K)")
        self.axes.set_ylabel("Pressure (bar)")
        self.axes.set_title("Ice Phase Diagram")
        self.axes.set_xlim(0, 500)
        self.axes.set_ylim(0, 10000)
        
        # Set cursor to crosshair
        self.canvas.setCursor(Qt.CrossCursor)
    
    def _on_hover(self, event):
        """Handle hover - show coordinates."""
        if event.inaxes and event.xdata is not None:
            self.info_label.setText(
                f"T={event.xdata:.1f} K, P={event.ydata:.0f} bar"
            )
    
    def _on_click(self, event):
        """Handle click - select coordinates."""
        if not event.inaxes or event.xdata is None:
            return
        
        temperature = event.xdata
        pressure = event.ydata
        
        # Detect phase
        phase_name, is_boundary = self._detector.detect_phase(temperature, pressure)
        
        # Update info display
        if is_boundary:
            self.info_label.setText(f"⚠️ {phase_name}")
        else:
            self.info_label.setText(f"Selected: {phase_name} (T={temperature:.1f} K, P={pressure:.0f} bar)")
        
        # Emit coordinates for input panel
        self.coordinates_selected.emit(temperature, pressure)
```

### Example 2: Phase Detector Class
```python
from shapely.geometry import Point, Polygon

class PhaseDetector:
    """Detects ice phase at given T,P using shapely polygons."""
    
    def __init__(self):
        from quickice.output.phase_diagram import (
            _build_phase_polygon_from_curves,
            PHASE_LABELS,
        )
        
        self._polygons = {}
        for phase_id in ["ice_ih", "ice_ii", "ice_iii", "ice_v", "ice_vi",
                         "ice_vii", "ice_viii", "ice_xi", "ice_ix", "ice_x", "ice_xv"]:
            vertices = _build_phase_polygon_from_curves(phase_id)
            if vertices and len(vertices) >= 3:
                self._polygons[phase_id] = Polygon(vertices)
    
    def detect_phase(self, temperature: float, pressure: float):
        """Detect phase at T (K), P (bar).
        
        Converts bar to MPa before lookup.
        """
        # Convert bar to MPa for lookup
        pressure_mpa = pressure * 0.1
        
        point = Point(temperature, pressure_mpa)
        
        # Check contained phases
        contained = [
            pid for pid, poly in self._polygons.items()
            if poly.contains(point)
        ]
        
        if len(contained) == 1:
            return PHASE_LABELS.get(contained[0], contained[0]), False
        elif len(contained) > 1:
            return "Multiple phases possible", True
        
        # Check boundary (touches)
        touching = [
            pid for pid, poly in self._polygons.items()
            if poly.touches(point)
        ]
        
        if len(touching) >= 2:
            phases = ", ".join(PHASE_LABELS.get(p, p) for p in touching)
            return f"Boundary: {phases}", True
        
        return None, False
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static PNG diagram | Interactive Matplotlib in Qt | Phase 9 | Enables visual T,P selection |
| Manual coordinate conversion | event.xdata/ydata | Matplotlib 2.x+ | Handles transforms automatically |
| Custom point-in-polygon | shapely.contains() | shapely 2.0+ | Robust numerical handling |

**Deprecated/outdated:**
- matplotlib.get_current_filter_manager() - deprecated, use Qt signals instead
- NavigationToolbar - can be hidden for clean diagram view

## Open Questions

1. **Log Scale Pressure Display vs. Input**
   - What we know: CONTEXT.md specifies 0-10000 bar Y-axis, likely log scale
   - What's unclear: Should we use log scale for display or linear?
   - Recommendation: Use log scale for display (matches scientific convention for phase diagrams), matplotlib event handling handles conversion automatically

2. **Melting Curve Boundaries**
   - What we know: Phase regions are defined by melting curves in lookup.py
   - What's unclear: Should we render melting curves as boundaries in the interactive diagram?
   - Recommendation: Yes, include melting curves from phase_diagram.py to show proper phase boundaries visually

3. **Click Debouncing**
   - What we know: User may click rapidly
   - What's unclear: Should we debounce clicks?
   - Recommendation: Not needed for single click selection; event fires once per click

## Sources

### Primary (HIGH confidence)
- Matplotlib documentation - Embed in Qt: https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html
- Matplotlib documentation - Mouse move and click events: https://matplotlib.org/stable/gallery/event_handling/coords_demo.html
- Shapely documentation - Geometric predicates: https://shapely.readthedocs.io/en/stable/manual.html

### Secondary (MEDIUM confidence)
- Matplotlib documentation - Pick event demo: https://matplotlib.org/stable/gallery/event_handling/pick_event_demo.html
- Matplotlib documentation - Colormap reference (for colorblind-friendly colors): https://matplotlib.org/stable/gallery/color/colormap_reference.html
- Paul Tol's color schemes: https://www.sron.nl/~pault/ (colorblind-friendly palettes)

### Tertiary (LOW confidence)
- Existing quickice/output/phase_diagram.py - Static diagram generation
- Existing quickice/phase_mapping/lookup.py - Phase lookup logic

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH - Matplotlib + PySide6 integration is well-documented
- Architecture: HIGH - Event handling pattern is standard matplotlib approach
- Pitfalls: HIGH - Common issues documented in matplotlib docs

**Research date:** 2026-04-01
**Valid until:** 90 days (matplotlib stable, Qt bindings mature)