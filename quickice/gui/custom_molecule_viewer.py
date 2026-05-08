"""VTK-based 3D custom molecule structure viewer widget.

This module provides the CustomMoleculeViewerWidget class for rendering
custom molecules uploaded via .gro/.itp files in the 3D molecular viewer
using ball-and-stick representation with distinct colors.

Uses stacked widget pattern with placeholder before insertion and 3D viewer after.
"""

import os
import numpy as np
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget, QLabel,
)
from PySide6.QtCore import Qt

# Check if VTK is available (may fail in remote/indirect rendering environments)
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
            vtkActor,
        )
except Exception:
    _VTK_AVAILABLE = False

from quickice.structure_generation.types import CustomMoleculeStructure

# Import renderer function for custom molecules
from quickice.gui.custom_molecule_renderer import create_custom_molecule_actor

logger = logging.getLogger(__name__)


class CustomMoleculeViewerWidget(QWidget):
    """VTK-based 3D viewer for custom molecule structures.
    
    Renders custom molecules using ball-and-stick representation with
    distinct colors (purple, cyan, yellow) to differentiate from predefined
    molecules.
    
    Uses stacked widget pattern to show placeholder before insertion and
    3D viewer after.
    
    Attributes:
        _vtk_available: Whether VTK rendering is available in this environment.
        vtk_widget: The QVTKRenderWindowInteractor instance (if VTK available).
        render_window: VTK render window (if VTK available).
        renderer: VTK renderer for the scene (if VTK available).
        interactor: VTK interactor for user input (if VTK available).
        _current_structure: Currently displayed CustomMoleculeStructure.
        _custom_actor: VTK actor for custom molecule visualization.
    
    Signals:
        None (viewer is display-only, no signals needed)
    """

    def __init__(self, parent: QWidget | None = None):
        """Initialize the custom molecule viewer widget.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)

        # State tracking
        self._vtk_available = _VTK_AVAILABLE
        self._current_structure: CustomMoleculeStructure | None = None
        self._custom_actor: vtkActor | None = None
        self._preview_actor: vtkActor | None = None

        # VTK components (initialized only if VTK available)
        self.vtk_widget = None
        self.render_window = None
        self.renderer = None
        self.interactor = None

        # Set up UI
        self._setup_ui()
        
        logger.info("CustomMoleculeViewerWidget initialized")

    def _setup_ui(self) -> None:
        """Set up the user interface.
        
        Creates stacked widget with:
        - Index 0: Placeholder widget with "No custom molecules loaded" message
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
        """Create the placeholder widget shown before custom molecule insertion.
        
        Returns:
            QWidget with centered placeholder message.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        
        label = QLabel("No custom molecules loaded")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: gray; font-size: 14px;")
        layout.addWidget(label)
        
        hint = QLabel("Upload .gro and .itp files to see custom molecules in 3D")
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
        
        # Set dark blue background (same as other viewers)
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

    def update_structure(self, structure: CustomMoleculeStructure) -> None:
        """Render custom molecules in 3D viewer.
        
        Args:
            structure: CustomMoleculeStructure with positions, atom_names, cell
        """
        # Clear any existing preview
        self.clear_preview()
        
        if not self._vtk_available:
            # VTK not available - just switch to viewer mode
            self._current_structure = structure
            self._stack.setCurrentIndex(1)
            logger.info("Custom molecule structure stored (VTK unavailable)")
            return

        # Clear existing custom molecule actor
        self.clear_custom_actor()

        # Store the structure reference
        self._current_structure = structure

        # Create custom molecule actor using the renderer
        actor = create_custom_molecule_actor(
            structure.positions,
            structure.atom_names,
            structure.cell,
            structure.moleculetype_name
        )
        
        if actor:
            self._custom_actor = actor
            self.renderer.AddActor(actor)
            self._reset_camera()
            logger.info(f"Rendered {structure.n_molecules} custom molecules")
        else:
            logger.warning("No custom molecule actor created")

        # Switch to 3D viewer (index 1) if not already showing
        self._stack.setCurrentIndex(1)

        # Render the scene
        if self.render_window:
            self.render_window.Render()

    def _reset_camera(self) -> None:
        """Reset camera for optimal viewing of custom molecule structure.

        Positions camera to frame the entire structure.
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

        # Handle case where diagonal is zero (empty viewer)
        if diagonal < 0.001:
            diagonal = 1.0

        # Position camera at ~2x structure size
        camera.SetPosition(
            center_x + diagonal * 2.0,
            center_y + diagonal * 2.0,
            center_z + diagonal * 2.0
        )
        camera.SetFocalPoint(center_x, center_y, center_z)

        # Set view up to Y vertical
        camera.SetViewUp(0, 1, 0)

        self.renderer.ResetCameraClippingRange()

    def clear_custom_actor(self) -> None:
        """Remove custom molecule actor from viewer."""
        if self._custom_actor is not None and self.renderer is not None:
            self.renderer.RemoveActor(self._custom_actor)
            self._custom_actor = None
            logger.info("Cleared custom molecule actor")

    def clear(self) -> None:
        """Clear the current structure from the viewer.

        Removes all actors and shows placeholder.
        """
        self.clear_custom_actor()
        self._current_structure = None

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
        """Reset camera for optimal custom molecule viewing.
        
        Reorients camera to frame the entire structure.
        """
        self._reset_camera()
        
        if self._vtk_available and self.render_window is not None:
            self.render_window.Render()

    def show_preview(
        self,
        positions: np.ndarray,
        atom_names: list[str],
        cell: np.ndarray
    ) -> None:
        """Show preview molecule with semi-transparent styling.
        
        Renders the molecule at the proposed position with opacity 0.6
        to distinguish from actual insertion. Shows in context of existing
        structure (ice, water, guests).
        
        Args:
            positions: (N_atoms, 3) positions for preview molecule in nm
            atom_names: List of atom names (e.g., ["C", "H", "H", ...])
            cell: (3, 3) unit cell vectors in nm
            
        Note:
            - Removes any existing preview actor before creating new one
            - Switches to 3D viewer if on placeholder
            - Does NOT modify _current_structure (preview is temporary)
        """
        if not self._vtk_available or self.renderer is None:
            logger.warning("VTK not available, cannot show preview")
            return
        
        # Clear existing preview actor
        self.clear_preview()
        
        # Create preview actor using existing renderer
        try:
            from quickice.gui.custom_molecule_renderer import create_custom_molecule_actor
            
            actor = create_custom_molecule_actor(
                positions, atom_names, cell, moleculetype_name="PREVIEW"
            )
            
            # Make preview semi-transparent
            actor.GetProperty().SetOpacity(0.6)
            
            # Add to renderer
            self.renderer.AddActor(actor)
            self._preview_actor = actor
            
            # Render
            if self.render_window:
                self.render_window.Render()
            
            # Switch to 3D viewer if not already showing
            if self._stack.currentIndex() == 0:
                self._stack.setCurrentIndex(1)
            
            logger.info(f"Preview actor added with {len(positions)} atoms")
            
        except Exception as e:
            logger.error(f"Failed to create preview actor: {e}")

    def clear_preview(self) -> None:
        """Clear preview molecule from viewer.
        
        Removes the preview actor from the renderer if it exists.
        Safe to call even if no preview is shown.
        """
        if self._preview_actor is not None and self.renderer is not None:
            self.renderer.RemoveActor(self._preview_actor)
            self._preview_actor = None
            
            # Render to update view
            if self.render_window:
                self.render_window.Render()
            
            logger.info("Preview actor cleared")
