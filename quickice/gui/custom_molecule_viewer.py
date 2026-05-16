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


# Interface visualization constants (same as SoluteViewerWidget and IonViewerWidget)
ICE_COLOR = (0.0, 0.8, 0.8)         # Cyan
WATER_COLOR = (0.39, 0.58, 0.93)    # Cornflower blue
GUEST_COLOR = (0.8, 0.8, 0.8)        # Gray for guest molecules
BOND_LINE_WIDTH = 1.5
ANGSTROM_TO_NM = 0.1

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
        _preview_actor: VTK actor for preview molecule visualization.
        _interface_structure: Currently displayed interface structure (ice + water).
        _interface_actors: List of VTK actors for interface (ice + water bonds).
        _guest_actor: VTK actor for guest molecules (if present).
    
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
        self._interface_structure = None  # InterfaceStructure (ice + water) for context
        self._interface_actors: list = []  # List of VTK actors for interface
        self._guest_actor = None  # For guest molecules (vtkActor when VTK available)

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

    def _extract_bonds(self, mol, cell: np.ndarray | None = None) -> list:
        """Extract bond positions from VTK molecule with PBC wrapping.
        
        Args:
            mol: vtkMolecule with bonds
            cell: (3, 3) unit cell vectors in nm (optional, for PBC)
        
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

    def _create_guest_ball_and_stick_actor(self, structure, guest_mol) -> vtkActor:
        """Create a ball-and-stick actor for guest molecules.
        
        Uses vtkMoleculeMapper with ball-and-stick settings for CPK coloring
        and proper bond rendering. Same as interface_viewer.py.
        
        Args:
            structure: InterfaceStructure containing guest data
            guest_mol: vtkMolecule with guest atoms
        
        Returns:
            vtkActor configured for ball-and-stick visualization
        """
        from vtkmodules.all import vtkMoleculeMapper, vtkActor
        
        # Create mapper with ball-and-stick settings
        mapper = vtkMoleculeMapper()
        mapper.SetInputData(guest_mol)
        mapper.UseBallAndStickSettings()
        mapper.SetAtomicRadiusTypeToVDWRadius()
        mapper.SetRenderAtoms(True)
        mapper.SetRenderBonds(True)
        mapper.SetAtomicRadiusScaleFactor(0.25 * ANGSTROM_TO_NM)  # 0.025 nm
        mapper.SetBondRadius(0.075 * ANGSTROM_TO_NM)  # 0.0075 nm
        mapper.SetBondColor(180, 180, 180)  # Gray bonds
        
        actor = vtkActor()
        actor.SetMapper(mapper)
        
        return actor

    def _clear_interface_actors(self) -> None:
        """Remove interface actors from renderer."""
        if self.renderer is None:
            return
            
        for actor in self._interface_actors:
            if actor is not None:
                self.renderer.RemoveActor(actor)

        # Clear actor list
        self._interface_actors = []

        # Also remove guest actor if it exists
        if self._guest_actor is not None:
            self.renderer.RemoveActor(self._guest_actor)
            self._guest_actor = None

    def load_interface_structure(self, interface_structure) -> None:
        """Load interface structure for preview context.
        
        Called by MainWindow when preview is requested, to show the
        interface structure (ice + water) as context for the preview molecule.
        
        Args:
            interface_structure: InterfaceStructure to render
        """
        if not self._vtk_available:
            self._interface_structure = interface_structure
            return
        
        # Load interface VTK utilities when first needed
        _load_interface_utils()
        
        # Clear existing interface actors
        self._clear_interface_actors()
        
        # Store interface structure
        self._interface_structure = interface_structure
        
        # Render interface structure
        if interface_structure is not None:
            # Convert to separate ice, water, and guest VTK molecules
            ice_mol, water_mol, guest_mol = _interface_to_vtk_molecules(interface_structure)
            
            # Extract bonds from each molecule with PBC wrapping
            ice_bonds = self._extract_bonds(ice_mol, interface_structure.cell)
            water_bonds = self._extract_bonds(water_mol, interface_structure.cell)
            
            # Create bond line actors
            ice_actor = _create_bond_lines_actor(ice_bonds, ICE_COLOR, BOND_LINE_WIDTH)
            water_actor = _create_bond_lines_actor(water_bonds, WATER_COLOR, BOND_LINE_WIDTH)
            unit_cell_actor = _create_unit_cell_actor(interface_structure.cell)
            
            # Create guest actor if guests exist
            if guest_mol is not None and interface_structure.guest_atom_count > 0:
                guest_actor = self._create_guest_ball_and_stick_actor(interface_structure, guest_mol)
                self._guest_actor = guest_actor
            else:
                self._guest_actor = None
            
            # Store interface actors
            self._interface_actors.extend([ice_actor, water_actor, unit_cell_actor])
            
            # Add actors to renderer
            for actor in self._interface_actors:
                self.renderer.AddActor(actor)
            
            # Add guest actor if it exists
            if self._guest_actor is not None:
                self.renderer.AddActor(self._guest_actor)
            
            logger.info(f"Loaded interface structure: {getattr(interface_structure, 'ice_nmolecules', 0)} ice + {getattr(interface_structure, 'water_nmolecules', 0)} water molecules")
            
            # Render to show interface
            if self.render_window:
                self.render_window.Render()

    def update_structure(self, structure: CustomMoleculeStructure) -> None:
        """Render custom molecules in 3D viewer.
        
        Renders the interface structure (ice + water) first, then adds custom
        molecules on top. This ensures both are visible in the viewer.
        
        Args:
            structure: CustomMoleculeStructure with positions, atom_names, cell,
                      and interface_structure
        """
        # Load interface VTK utilities when first needed
        if self._vtk_available:
            _load_interface_utils()
        
        # Clear any existing preview
        self.clear_preview()
        
        if not self._vtk_available:
            # VTK not available - just switch to viewer mode
            self._current_structure = structure
            self._stack.setCurrentIndex(1)
            logger.info("Custom molecule structure stored (VTK unavailable)")
            return

        # Clear existing custom molecule actor and interface actors
        self.clear_custom_actor()
        self._clear_interface_actors()

        # Store the structure reference
        self._current_structure = structure

        # Render interface structure (ice + water) if available
        if structure.interface_structure is not None:
            interface = structure.interface_structure
            
            # Convert to separate ice, water, and guest VTK molecules
            ice_mol, water_mol, guest_mol = _interface_to_vtk_molecules(interface)
            
            # Extract bonds from each molecule with PBC wrapping
            ice_bonds = self._extract_bonds(ice_mol, interface.cell)
            water_bonds = self._extract_bonds(water_mol, interface.cell)
            
            # Create bond line actors
            ice_actor = _create_bond_lines_actor(ice_bonds, ICE_COLOR, BOND_LINE_WIDTH)
            water_actor = _create_bond_lines_actor(water_bonds, WATER_COLOR, BOND_LINE_WIDTH)
            unit_cell_actor = _create_unit_cell_actor(interface.cell)
            
            # Create guest actor if guests exist
            if guest_mol is not None and interface.guest_atom_count > 0:
                guest_actor = self._create_guest_ball_and_stick_actor(interface, guest_mol)
                self._guest_actor = guest_actor
            else:
                self._guest_actor = None
            
            # Store interface actors
            self._interface_actors.extend([ice_actor, water_actor, unit_cell_actor])
            
            # Add actors to renderer
            for actor in self._interface_actors:
                self.renderer.AddActor(actor)
            
            # Add guest actor if it exists
            if self._guest_actor is not None:
                self.renderer.AddActor(self._guest_actor)
            
            logger.info(f"Rendered interface: {getattr(interface, 'ice_nmolecules', 0)} ice + {getattr(interface, 'water_nmolecules', 0)} water molecules")

        # Extract only custom molecule atoms (not ice + water)
        if structure.custom_molecule_atom_count > 0:
            # Get start index for custom molecules
            ice_count = structure.ice_atom_count
            water_count = structure.water_atom_count
            guest_count = structure.guest_atom_count
            custom_start = ice_count + water_count + guest_count
            custom_end = custom_start + structure.custom_molecule_atom_count
            
            # Extract custom molecule positions and atom names
            custom_positions = structure.positions[custom_start:custom_end]
            custom_atom_names = structure.atom_names[custom_start:custom_end]
            
            # Create custom molecule actor using the renderer
            actor = create_custom_molecule_actor(
                custom_positions,
                custom_atom_names,
                structure.cell,
                structure.moleculetype_name
            )

            if actor:
                self._custom_actor = actor
                self.renderer.AddActor(actor)
                logger.info(f"Rendered {structure.custom_molecule_count} custom molecules")
            else:
                logger.warning("No custom molecule actor created")
        else:
            logger.info("No custom molecules to render")

        # Reset camera to view the complete structure
        self._reset_camera()

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

        Removes all actors (interface, custom molecules, preview) and shows placeholder.
        """
        self.clear_custom_actor()
        self.clear_preview()
        self._clear_interface_actors()
        self._current_structure = None
        self._interface_structure = None

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
            
            # Reset camera to view the preview molecule
            self._reset_camera()
            
            # Render
            if self.render_window:
                self.render_window.Render()
            
            # Switch to 3D viewer if not already showing
            if self._stack.currentIndex() == 0:
                self._stack.setCurrentIndex(1)
            
            logger.info(f"Preview actor added with {len(positions)} atoms")
            
        except Exception as e:
            logger.error(f"Failed to create preview actor: {e}")
            # Provide user feedback if parent has log_message method
            if hasattr(self, 'parent') and hasattr(self.parent, 'log_message'):
                self.parent.log_message(f"Warning: Could not create preview: {e}")

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
    
    def show_multiple_previews(
        self,
        molecule_positions_list: list[tuple[np.ndarray, list[str], np.ndarray]]
    ) -> None:
        """Show multiple preview molecules with semi-transparent styling.
        
        Renders multiple molecules at the proposed positions with opacity 0.6
        to distinguish from actual insertion. Shows in context of existing
        structure (ice, water, guests).
        
        Args:
            molecule_positions_list: List of (positions, atom_names, cell) tuples,
                                    where each positions is (N_atoms, 3) array in nm
            
        Note:
            - Removes any existing preview actor before creating new ones
            - Creates one actor per molecule (combined for efficiency)
            - Switches to 3D viewer if on placeholder
            - Does NOT modify _current_structure (preview is temporary)
        """
        if not self._vtk_available or self.renderer is None:
            logger.warning("VTK not available, cannot show preview")
            return
        
        # Clear existing preview actor
        self.clear_preview()
        
        # Combine all molecule positions into single arrays
        all_positions = []
        all_atom_names = []
        
        for positions, atom_names, cell in molecule_positions_list:
            all_positions.append(positions)
            all_atom_names.extend(atom_names)
        
        if not all_positions:
            logger.warning("No positions to preview")
            return
        
        # Combine positions
        combined_positions = np.vstack(all_positions)
        
        # Use the cell from the first molecule (should be same for all)
        _, _, cell = molecule_positions_list[0]
        
        # Create single preview actor for all molecules
        try:
            from quickice.gui.custom_molecule_renderer import create_custom_molecule_actor
            
            actor = create_custom_molecule_actor(
                combined_positions, all_atom_names, cell, moleculetype_name="PREVIEW"
            )
            
            # Make preview semi-transparent
            actor.GetProperty().SetOpacity(0.6)
            
            # Add to renderer
            self.renderer.AddActor(actor)
            self._preview_actor = actor
            
            # Reset camera to view all preview molecules
            self._reset_camera()
            
            # Render
            if self.render_window:
                self.render_window.Render()
            
            # Switch to 3D viewer if not already showing
            if self._stack.currentIndex() == 0:
                self._stack.setCurrentIndex(1)
            
            logger.info(f"Preview actor added with {len(combined_positions)} atoms from {len(molecule_positions_list)} molecules")
            
        except Exception as e:
            logger.error(f"Failed to create preview actor: {e}")
            # Provide user feedback if parent has log_message method
            if hasattr(self, 'parent') and hasattr(self.parent, 'log_message'):
                self.parent.log_message(f"Warning: Could not create preview: {e}")
