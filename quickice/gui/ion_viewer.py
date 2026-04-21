"""VTK-based 3D ion structure viewer widget.

This module provides the IonViewerWidget class for rendering Na+ and Cl- ions
as van der Waals (VDW) spheres in the 3D molecular viewer, alongside the
interface structure (ice + water) rendered as bonds.

Uses stacked widget pattern with placeholder before insertion and 3D viewer after.
"""

import os
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget, QLabel,
)
from PySide6.QtCore import Qt

# Check if VTK is available (may fail in remote/indirect rendering environments)
# Same logic as hydrate_viewer.py for consistency
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

from quickice.structure_generation.types import IonStructure

# Import renderer functions for ions
from quickice.gui.ion_renderer import render_ion_structure

# Import interface utilities (loaded lazily when VTK is available)
_interface_utils_loaded = False
_interface_to_vtk_molecules = None
_create_bond_lines_actor = None
_create_unit_cell_actor = None


def _load_interface_utils():
    """Lazily load interface VTK utilities."""
    global _interface_utils_loaded, _interface_to_vtk_molecules, _create_bond_lines_actor, _create_unit_cell_actor
    if not _interface_utils_loaded:
        from quickice.structure_generation.types import InterfaceStructure
        from quickice.gui.vtk_utils import (
            interface_to_vtk_molecules,
            create_bond_lines_actor,
            create_unit_cell_actor,
        )
        _interface_to_vtk_molecules = interface_to_vtk_molecules
        _create_bond_lines_actor = create_bond_lines_actor
        _create_unit_cell_actor = create_unit_cell_actor
        _interface_utils_loaded = True


# Interface visualization constants (same as InterfaceViewerWidget)
ICE_COLOR = (0.0, 0.8, 0.8)         # Cyan
WATER_COLOR = (0.39, 0.58, 0.93)    # Cornflower blue
BOND_LINE_WIDTH = 1.5


class IonViewerWidget(QWidget):
    """VTK-based 3D viewer for ion structures.
    
    Renders Na+ and Cl- ions as van der Waals spheres alongside the interface
    structure (ice + water) rendered as bond lines.
    
    Uses stacked widget pattern to show placeholder before insertion and
    3D viewer after.
    
    Attributes:
        _vtk_available: Whether VTK rendering is available in this environment.
        vtk_widget: The QVTKRenderWindowInteractor instance (if VTK available).
        render_window: VTK render window (if VTK available).
        renderer: VTK renderer for the scene (if VTK available).
        interactor: VTK interactor for user input (if VTK available).
        _current_interface: Currently displayed InterfaceStructure.
        _current_ion_structure: Currently displayed IonStructure.
        _interface_actors: List of VTK actors for interface (ice + water bonds).
        _ion_actors: List of VTK actors for ion visualization.
    
    Signals:
        None (viewer is display-only, no signals needed)
    """

    def __init__(self, parent: QWidget | None = None):
        """Initialize the ion viewer widget.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)

        # State tracking
        self._vtk_available = _VTK_AVAILABLE
        self._current_interface: InterfaceStructure | None = None
        self._current_ion_structure: IonStructure | None = None
        self._interface_actors: list = []
        self._ion_actors: list = []

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
        - Index 0: Placeholder widget with "No ions inserted" message
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
        """Create the placeholder widget shown before ion insertion.
        
        Returns:
            QWidget with centered placeholder message.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        
        label = QLabel("No ions inserted")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: gray; font-size: 14px;")
        layout.addWidget(label)
        
        hint = QLabel("Configure and insert ions to see them in 3D")
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
        
        # Set dark blue background (same as HydrateViewerWidget/InterfaceViewerWidget)
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
    
    def set_interface_structure(self, structure) -> None:
        """Load and display an interface structure (ice + water).

        Converts the InterfaceStructure to VTK bond line actors for ice and water,
        then displays with auto-fit camera.

        Args:
            structure: An InterfaceStructure containing ice and water atoms.
        """
        # Load interface VTK utilities when first needed
        if self._vtk_available:
            _load_interface_utils()

        if not self._vtk_available:
            # VTK not available - just switch to viewer mode
            self._current_interface = structure
            self._stack.setCurrentIndex(1)
            return

        # Clear previous interface actors only (keep ions if already rendered)
        self._clear_interface_actors()

        # Store the structure reference
        self._current_interface = structure

        # Convert to separate ice and water VTK molecules
        ice_mol, water_mol = _interface_to_vtk_molecules(structure)

        # Extract bonds from each molecule with PBC wrapping
        ice_bonds = self._extract_bonds(ice_mol, structure.cell)
        water_bonds = self._extract_bonds(water_mol, structure.cell)

        # Create bond line actors
        ice_actor = _create_bond_lines_actor(ice_bonds, ICE_COLOR, BOND_LINE_WIDTH)
        water_actor = _create_bond_lines_actor(water_bonds, WATER_COLOR, BOND_LINE_WIDTH)
        unit_cell_actor = _create_unit_cell_actor(structure.cell)

        # Store actors
        self._interface_actors.extend([ice_actor, water_actor, unit_cell_actor])

        # Add actors to renderer
        for actor in self._interface_actors:
            self.renderer.AddActor(actor)

        # Auto-fit camera to frame all actors
        self._reset_camera()

        # Render the scene
        self.render_window.Render()

    def _extract_bonds(self, mol, cell: np.ndarray = None) -> list:
        """Extract bond positions from a VTK molecule with PBC wrapping.

        Applies minimum image convention to ensure bonds are drawn as the
        shortest connection, wrapping across periodic boundaries when needed.

        Args:
            mol: vtkMolecule with bonds.
            cell: (3, 3) cell matrix for PBC wrapping. If None, no wrapping.

        Returns:
            List of ((x1, y1, z1), (x2, y2, z2)) tuples for each bond,
            with positions wrapped to show shortest distance.
        """
        from vtkmodules.all import vtkMolecule

        bonds = []
        n_bonds = mol.GetNumberOfBonds()

        # Get cell dimensions for PBC (assuming orthorhombic)
        if cell is not None:
            cell_dims = np.diag(cell)
        else:
            cell_dims = None

        for i in range(n_bonds):
            bond = mol.GetBond(i)

            # Get atom IDs for this bond
            atom1_id = bond.GetBeginAtomId()
            atom2_id = bond.GetEndAtomId()

            # Get atom positions
            atom1 = mol.GetAtom(atom1_id)
            atom2 = mol.GetAtom(atom2_id)

            pos1 = np.array(atom1.GetPosition())
            pos2 = np.array(atom2.GetPosition())

            # Apply minimum image convention if cell is provided
            if cell_dims is not None:
                # Wrap pos2 to be within half box distance of pos1
                delta = pos2 - pos1
                delta = delta - cell_dims * np.round(delta / cell_dims)
                pos2 = pos1 + delta

# Convert to tuples
            p1 = (float(pos1[0]), float(pos1[1]), float(pos1[2]))
            p2 = (float(pos2[0]), float(pos2[1]), float(pos2[2]))

            bonds.append((p1, p2))

        return bonds

    def set_ion_structure(self, structure: IonStructure) -> None:
        """Load and display an ion structure.

        Converts the IonStructure to VTK actors (Na+ as gold spheres,
        Cl- as green spheres), then displays with auto-fit camera.

        NOTE: This adds ions to ANY existing interface structure already displayed.
        Call set_interface_structure() first to show ice + water, then call this
        to add ions as spheres on top.

        Args:
            structure: An IonStructure containing Na+ and Cl- ions.
        """
        if not self._vtk_available:
            # VTK not available - just switch to viewer mode
            self._current_ion_structure = structure
            self._stack.setCurrentIndex(1)
            return

        # Clear previous ion actors only (keep interface if already rendered)
        self._clear_ion_actors()

        # Store the structure reference
        self._current_ion_structure = structure

        # Render ion structure to get actors
        self._ion_actors = render_ion_structure(structure)

        # Add actors to renderer
        for actor in self._ion_actors:
            self.renderer.AddActor(actor)

        # Auto-fit camera to frame all actors
        self._reset_camera()

        # Switch to 3D viewer (index 1) if not already showing
        self._stack.setCurrentIndex(1)

        # Render the scene
        self.render_window.Render()
    
    def _reset_camera(self) -> None:
        """Reset camera for optimal viewing of ion + interface structure.

        Positions camera to frame the entire structure with both interface
        and ions visible.
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

    def _clear_interface_actors(self) -> None:
        """Remove interface actors from renderer."""
        for actor in self._interface_actors:
            if actor is not None:
                self.renderer.RemoveActor(actor)

        # Clear actor list
        self._interface_actors = []

    def _clear_ion_actors(self) -> None:
        """Remove ion actors from renderer."""
        # Remove actors from renderer
        for actor in self._ion_actors:
            if actor is not None:
                self.renderer.RemoveActor(actor)

        # Clear actor list
        self._ion_actors = []

        # Clear current ion structure
        self._current_ion_structure = None

    def _clear_actors(self) -> None:
        """Remove all actors from renderer and reset state."""
        self._clear_interface_actors()
        self._clear_ion_actors()

        # Clear current interface structure
        self._current_interface = None

    def clear(self) -> None:
        """Clear the current structure from the viewer.

        Removes all actors and shows placeholder.
        """
        self._clear_actors()

        if self._vtk_available and self.render_window is not None:
            self.render_window.Render()

        # Show placeholder
        self._stack.setCurrentIndex(0)

    def clear_ions_only(self) -> None:
        """Clear only the ion actors, keep interface structure."""
        self._clear_ion_actors()

        if self._vtk_available and self.render_window is not None:
            self.render_window.Render()

    def clear_interface_only(self) -> None:
        """Clear only the interface structure, keep ion actors."""
        self._clear_interface_actors()

        if self._vtk_available and self.render_window is not None:
            self.render_window.Render()

    def show_placeholder(self) -> None:
        """Show the placeholder widget.

        Switches to placeholder view (index 0).
        """
        self._stack.setCurrentIndex(0)

    def hide_placeholder(self) -> None:
        """Hide the placeholder, show the 3D viewer.

        Switches to 3D viewer (index 1). Does nothing if no structure is loaded.
        """
        if self._current_interface is not None or self._current_ion_structure is not None:
            self._stack.setCurrentIndex(1)
    
    def is_vtk_available(self) -> bool:
        """Check if VTK 3D viewer is available.
        
        Returns:
            True if VTK rendering is available, False otherwise.
        """
        return self._vtk_available
    
    def reset_camera(self) -> None:
        """Reset camera for optimal ion viewing.
        
        Reorients camera to frame the entire structure.
        """
        self._reset_camera()
        
        if self._vtk_available and self.render_window is not None:
            self.render_window.Render()