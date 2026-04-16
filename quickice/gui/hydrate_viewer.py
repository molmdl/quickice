"""VTK-based 3D hydrate structure viewer widget.

This module provides the HydrateViewerWidget class for rendering gas hydrate
structures with dual-style visualization:
- Water framework: rendered as bonds/lines only
- Guest molecules: rendered as ball-and-stick with CPK coloring

Uses stacked widget pattern with placeholder before generation and 3D viewer after.
"""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget, QLabel,
)
from PySide6.QtCore import Qt

# Check if VTK is available (may fail in remote/indirect rendering environments)
# Same logic as interface_panel.py for consistency
_VTK_AVAILABLE = False
try:
    # Test if we can create a basic VTK render window
    # This will fail in environments with indirect rendering (SSH X11 forwarding)
    if os.environ.get('DISPLAY') and 'localhost' in os.environ.get('DISPLAY', ''):
        # Likely SSH X11 forwarding - check for direct rendering
        _VTK_AVAILABLE = os.environ.get('QUICKICE_FORCE_VTK', '').lower() == 'true'
    else:
        # Local display or forced - assume VTK works
        _VTK_AVAILABLE = True
    
    if _VTK_AVAILABLE:
        from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
        from vtkmodules.all import (
            vtkRenderer,
            vtkInteractorStyleTrackballCamera,
        )
except Exception:
    _VTK_AVAILABLE = False

from quickice.structure_generation.types import HydrateStructure

# Import renderer function
from quickice.gui.hydrate_renderer import render_hydrate_structure


# Unit cell actor import - loaded only when needed
def _get_unit_cell_creator():
    """Lazy import for create_unit_cell_actor."""
    from quickice.gui.vtk_utils import create_unit_cell_actor
    return create_unit_cell_actor


class HydrateViewerWidget(QWidget):
    """VTK-based 3D viewer for hydrate structures.
    
    Renders water framework as lines and guest molecules as ball-and-stick,
    with auto-fit camera orientation. Uses stacked widget pattern to show
    placeholder before generation and 3D viewer after.
    
    Attributes:
        _vtk_available: Whether VTK rendering is available in this environment.
        vtk_widget: The QVTKRenderWindowInteractor instance (if VTK available).
        render_window: VTK render window (if VTK available).
        renderer: VTK renderer for the scene (if VTK available).
        interactor: VTK interactor for user input (if VTK available).
        _current_structure: Currently displayed HydrateStructure.
        _hydrate_actors: List of VTK actors for hydrate visualization.
    
    Signals:
        None (viewer is display-only, no signals needed)
    """
    
    def __init__(self, parent: QWidget | None = None):
        """Initialize the hydrate viewer widget.
        
        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        
        # State tracking
        self._vtk_available = _VTK_AVAILABLE
        self._current_structure: HydrateStructure | None = None
        self._hydrate_actors: list = []
        self._representation_mode: str = "ball_and_stick"
        
        # Unit cell state (matching molecular_viewer.py pattern)
        self._unit_cell_actor = None
        self._show_unit_cell = False
        
        # VTK components (initialized only if VTK available)
        self.vtk_widget = None
        self.render_window = None
        self.renderer = None
        self.interactor = None
        
        # Set up UI
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the user interface.
        
        Creates stacked widget with:
        - Index 0: Placeholder widget with "No hydrate generated" message
        - Index 1: VTK widget for 3D rendering (or fallback if VTK unavailable)
        """
        # Main layout with zero margins
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create stacked widget for placeholder/3D toggle
        self._stack = QStackedWidget()
        main_layout.addWidget(self._stack)
        
        # Create placeholder widget
        placeholder_widget = self._create_placeholder_widget()
        self._stack.addWidget(placeholder_widget)
        
        # Create 3D viewer widget (or fallback)
        if self._vtk_available:
            viewer_widget = self._create_vtk_viewer_widget()
        else:
            viewer_widget = self._create_vtk_fallback_widget()
        self._stack.addWidget(viewer_widget)
        
        # Show placeholder initially (index 0)
        self._stack.setCurrentIndex(0)
    
    def _create_placeholder_widget(self) -> QWidget:
        """Create the placeholder widget shown before generation.
        
        Returns:
            QWidget with centered placeholder message.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        
        label = QLabel("No hydrate generated")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: gray; font-size: 14px;")
        layout.addWidget(label)
        
        hint = QLabel("Configure and generate a hydrate structure")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: lightgray; font-size: 12px;")
        layout.addWidget(hint)
        
        return widget
    
    def _create_vtk_viewer_widget(self) -> QWidget:
        """Create the VTK-based 3D viewer widget.
        
        Returns:
            QWidget containing QVTKRenderWindowInteractor.
        """
        widget = QWidget()
        
        # Create VTK widget (QWidget subclass for Qt integration)
        self.vtk_widget = QVTKRenderWindowInteractor(widget)
        
        # Layout with zero margins for full widget area
        layout = QVBoxLayout(widget)
        layout.addWidget(self.vtk_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Get render window
        self.render_window = self.vtk_widget.GetRenderWindow()
        
        # Create and add renderer
        self.renderer = vtkRenderer()
        self.render_window.AddRenderer(self.renderer)
        
        # Set dark blue background (same as InterfaceViewerWidget)
        self.renderer.SetBackground(0.1, 0.2, 0.4)
        
        # Get interactor and set trackball camera style
        # This provides standard 3D controls:
        # - Left drag: rotate
        # - Right drag: zoom
        # - Middle drag: pan
        self.interactor = self.render_window.GetInteractor()
        style = vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(style)
        
        # Initialize the interactor (required before first render)
        self.vtk_widget.Initialize()
        
        return widget
    
    def _create_vtk_fallback_widget(self) -> QWidget:
        """Create fallback widget when VTK is unavailable.
        
        Returns:
            QWidget with message indicating VTK is not available.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        
        label = QLabel("3D viewer unavailable")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: gray; font-size: 14px;")
        layout.addWidget(label)
        
        hint = QLabel("VTK rendering not available in this environment.\n"
                      "Set QUICKICE_FORCE_VTK=true to attempt VTK rendering.")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: lightgray; font-size: 12px;")
        layout.addWidget(hint)
        
        return widget
    
    def set_hydrate_structure(self, structure: HydrateStructure) -> None:
        """Load and display a hydrate structure.
        
        Converts the HydrateStructure to VTK actors (water framework as lines,
        guest molecules as ball-and-stick), then displays with auto-fit camera.
        
        Args:
            structure: A HydrateStructure containing water and guest molecules.
        """
        if not self._vtk_available:
            # VTK not available - just switch to viewer mode
            self._current_structure = structure
            self._stack.setCurrentIndex(1)
            return
        
        # Clear previous actors
        self._clear_actors()
        
        # Store the structure reference
        self._current_structure = structure
        
        # Render hydrate structure to get actors
        self._hydrate_actors = render_hydrate_structure(structure)
        
        # Add actors to renderer
        for actor in self._hydrate_actors:
            self.renderer.AddActor(actor)
        
        # Auto-fit camera to frame all actors
        self._reset_camera()
        
        # Switch to 3D viewer (index 1)
        self._stack.setCurrentIndex(1)
        
        # Render the scene
        self.render_window.Render()
    
    def _reset_camera(self) -> None:
        """Reset camera for optimal viewing of hydrate structure.
        
        Positions camera to frame the entire structure with ball-and-stick scale.
        """
        if self.renderer is None:
            return
        
        self.renderer.ResetCamera()
        
        # Get the camera
        camera = self.renderer.GetActiveCamera()
        
        # Get bounds to find center
        bounds = self.renderer.ComputeVisiblePropBounds()
        center_x = (bounds[0] + bounds[1]) / 2
        center_y = (bounds[2] + bounds[3]) / 2
        center_z = (bounds[4] + bounds[5]) / 2
        
        # Calculate diagonal for distance
        dx = bounds[1] - bounds[0]
        dy = bounds[3] - bounds[2]
        dz = bounds[5] - bounds[4]
        diagonal = (dx**2 + dy**2 + dz**2) ** 0.5
        
        # Position camera at ~2x structure size (ball-and-stick scale)
        camera.SetPosition(
            center_x + diagonal * 2.0,
            center_y + diagonal * 2.0,
            center_z + diagonal * 2.0
        )
        camera.SetFocalPoint(center_x, center_y, center_z)
        
        # Set view up to Y vertical
        camera.SetViewUp(0, 1, 0)
        
        self.renderer.ResetCameraClippingRange()
    
    def _clear_actors(self) -> None:
        """Remove all hydrate actors from renderer and reset state."""
        # Remove actors from renderer
        for actor in self._hydrate_actors:
            if actor is not None:
                self.renderer.RemoveActor(actor)
        
        # Clear actor list
        self._hydrate_actors = []
        
        # Clear current structure
        self._current_structure = None
    
    def clear(self) -> None:
        """Clear the current structure from the viewer.
        
        Removes all actors and shows placeholder.
        """
        self._clear_actors()
        
        if self._vtk_available and self.render_window is not None:
            self.render_window.Render()
        
        # Show placeholder
        self._stack.setCurrentIndex(0)
    
    def show_placeholder(self) -> None:
        """Show the placeholder widget.
        
        Switches to placeholder view (index 0).
        """
        self._stack.setCurrentIndex(0)
    
    def hide_placeholder(self) -> None:
        """Hide the placeholder, show the 3D viewer.
        
        Switches to 3D viewer (index 1). Does nothing if no structure is loaded.
        """
        if self._current_structure is not None:
            self._stack.setCurrentIndex(1)
    
    def is_vtk_available(self) -> bool:
        """Check if VTK 3D viewer is available.
        
        Returns:
            True if VTK rendering is available, False otherwise.
        """
        return self._vtk_available
    
    def reset_camera(self) -> None:
        """Reset camera for optimal hydrate viewing.
        
        Reorients camera to frame the entire structure.
        """
        self._reset_camera()
        
        if self._vtk_available and self.render_window is not None:
            self.render_window.Render()
    
    def set_representation_mode(self, mode: str) -> None:
        """Switch between VDW, ball-and-stick, and stick representation modes.
        
        Args:
            mode: One of "vdw", "ball_and_stick", or "stick"
        
        This method re-renders the current structure with the specified mode,
        matching Tab 1's representation settings.
        """
        if mode not in ("vdw", "ball_and_stick", "stick"):
            raise ValueError(f"Invalid representation mode: {mode}. "
                           "Must be 'vdw', 'ball_and_stick', or 'stick'")
        
        self._representation_mode = mode
        
        # Re-render if structure is loaded
        if self._current_structure is not None and self._vtk_available:
            self._clear_actors()
            self._hydrate_actors = render_hydrate_structure(
                self._current_structure, mode
            )
            for actor in self._hydrate_actors:
                self.renderer.AddActor(actor)
            self.render_window.Render()
    
    def get_representation_mode(self) -> str:
        """Return current representation mode.
        
        Returns:
            "vdw", "ball_and_stick", or "stick"
        """
        return self._representation_mode
    
    def set_unit_cell_visible(self, visible: bool) -> None:
        """Toggle unit cell boundary box visualization.
        
        Args:
            visible: True to show unit cell, False to hide
        
        Per ADVVIZ-01: User can toggle unit cell boundary box to 
        visualize the simulation cell.
        """
        self._show_unit_cell = visible
        
        if not self._vtk_available or self._current_structure is None:
            return
        
        if visible:
            # Remove old actor if exists
            if self._unit_cell_actor is not None:
                self.renderer.RemoveActor(self._unit_cell_actor)
            
            # Create and add new actor
            cell = self._current_structure.cell
            create_unit_cell_actor = _get_unit_cell_creator()
            self._unit_cell_actor = create_unit_cell_actor(cell)
            self.renderer.AddActor(self._unit_cell_actor)
        
        elif not visible and self._unit_cell_actor is not None:
            # Remove unit cell actor
            self.renderer.RemoveActor(self._unit_cell_actor)
            self._unit_cell_actor = None
        
        self.render_window.Render()
    
    def get_unit_cell_visible(self) -> bool:
        """Return whether unit cell box is visible.
        
        Returns:
            True if unit cell is shown, False otherwise
        """
        return self._show_unit_cell
