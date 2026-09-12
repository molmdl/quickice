"""Interactive phase diagram widget for QuickIce GUI.

Provides an interactive ice-phase-diagram panel: hover for coordinates,
click to select temperature/pressure conditions, and detect the ice phase at
the selected point.

Classes:
    PhaseDiagramPanel: Complete widget with canvas and info panel

Startup-performance note (slow-gui-startup fix): the matplotlib/shapely-heavy
classes (PhaseDiagramCanvas, PhaseDetector) live in
``quickice.gui.phase_diagram_canvas`` and are imported LAZILY. The panel
builds its canvas after the main window is shown (``QTimer.singleShot(0)``)
or on first access through :attr:`diagram_canvas`, so importing this module
at startup costs nothing heavy. See AGENTS.md lazy-import rule.

The canvas signals are re-emitted at panel level
(``coordinates_selected``/``phase_info_ready``) so callers do NOT need to
touch ``diagram_canvas`` (which would force eager construction).
"""

from typing import Tuple, Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Signal, Qt, QTimer


class PhaseDiagramPanel(QWidget):
    """Complete phase diagram widget with canvas and info panel.

    Combines PhaseDiagramCanvas with a QLabel for displaying coordinates
    and phase information. Handles hover events to show live coordinates
    and click events to display selected phase.

    The matplotlib canvas is built LAZILY (slow-gui-startup fix): either
    right after the main window is shown (via ``QTimer.singleShot(0)``) or
    on first access of :attr:`diagram_canvas`, whichever comes first.
    Until then a light placeholder label occupies the canvas area.

    Signals:
        coordinates_selected: Forwarded from the canvas (temperature, pressure).
        phase_info_ready: Forwarded from the canvas (phase_id, T, P).
    """

    # Forwarded canvas signals — connect to THESE, not to diagram_canvas.*,
    # so the canvas is not forced to exist early.
    coordinates_selected = Signal(float, float)  # (temperature, pressure)
    phase_info_ready = Signal(str, float, float)  # (phase_id, T, P)

    def __init__(self, parent=None):
        """Initialize the panel with a placeholder and info label.

        The heavy matplotlib canvas is deferred (see class docstring).

        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)

        self._diagram_canvas = None

        # Create layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)

        # Placeholder shown until the canvas is built
        self._placeholder = QLabel("Loading phase diagram\u2026")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(self._placeholder, stretch=1)

        # Create info label
        self.info_label = QLabel("Click on diagram to select T, P")
        self.info_label.setStyleSheet(
            "padding: 8px; "
            "background-color: #f5f5f5; "
            "border: 1px solid #ddd; "
            "border-radius: 3px;"
        )
        self.info_label.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(self.info_label)

        # Build the canvas in the next event-loop iteration — i.e. right
        # after the main window becomes visible, so it does not delay show().
        QTimer.singleShot(0, self._ensure_canvas)

    @property
    def diagram_canvas(self):
        """The PhaseDiagramCanvas, building it on first access if needed."""
        self._ensure_canvas()
        return self._diagram_canvas

    def _ensure_canvas(self):
        """Create the matplotlib canvas (idempotent).

        Lazy-imports quickice.gui.phase_diagram_canvas (matplotlib + shapely)
        so the ~0.3 s cost is paid after startup, not before window show.
        """
        if self._diagram_canvas is not None:
            return

        from quickice.gui.phase_diagram_canvas import PhaseDiagramCanvas

        canvas = PhaseDiagramCanvas(self)
        self._diagram_canvas = canvas

        # Replace placeholder with the real canvas
        self._layout.replaceWidget(self._placeholder, canvas)
        self._placeholder.hide()
        self._placeholder.deleteLater()
        canvas.show()

        # Set crosshair cursor on canvas
        canvas.setCursor(Qt.CrossCursor)

        # Internal handler: update info label on selection
        canvas.coordinates_selected.connect(self._on_coordinates_selected)
        # Forwarded panel-level signals (main_window connects to these)
        canvas.coordinates_selected.connect(self.coordinates_selected)
        canvas.phase_info_ready.connect(self.phase_info_ready)

        # Connect hover event for live coordinate display
        canvas.mpl_connect('motion_notify_event', self._on_hover)

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
        # Set marker on canvas (builds the canvas on demand if needed)
        self.diagram_canvas.set_marker(temperature, pressure)

        # Detect phase and update info label
        phase_name, is_boundary = self.diagram_canvas.detect_phase_at(temperature, pressure)

        # Reuse the _on_coordinates_selected logic for label update
        self._on_coordinates_selected(temperature, pressure)


def __getattr__(name: str):
    """Lazy backward-compat re-exports (PEP 562).

    ``PhaseDiagramCanvas`` and ``PhaseDetector`` moved to
    ``quickice.gui.phase_diagram_canvas``; this keeps
    ``from quickice.gui.phase_diagram_widget import PhaseDiagramCanvas``
    working without pulling matplotlib into startup.
    """
    if name in ("PhaseDiagramCanvas", "PhaseDetector"):
        from quickice.gui import phase_diagram_canvas
        value = getattr(phase_diagram_canvas, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Convenience exports
__all__ = ['PhaseDiagramPanel']
