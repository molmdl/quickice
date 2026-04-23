"""VTK-based 3D interface structure viewer widget.

This module provides the InterfaceViewerWidget class for rendering
ice-water interface structures with phase-distinct coloring.

Issue 2: Also supports rendering hydrate guest molecules alongside interface.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.all import (
    vtkRenderer,
    vtkInteractorStyleTrackballCamera,
    vtkActor,
)

import numpy as np
from quickice.structure_generation.types import InterfaceStructure, HydrateStructure
from quickice.gui.vtk_utils import (
    interface_to_vtk_molecules,
    create_bond_lines_actor,
    create_unit_cell_actor,
)
from quickice.gui.hydrate_renderer import render_hydrate_structure

# Color constants for phase-distinct visualization
ICE_COLOR = (0.0, 0.8, 0.8)         # Cyan
WATER_COLOR = (0.39, 0.58, 0.93)    # Cornflower blue
GUEST_COLOR = (0.8, 0.8, 0.8)        # Gray for guest molecules
BOND_LINE_WIDTH = 1.5
ANGSTROM_TO_NM = 0.1


class InterfaceViewerWidget(QWidget):
    """VTK-based 3D viewer for ice-water interface structures.
    
    Renders ice and water phases with distinct colors in a single viewport,
    with line-based bonds and auto-fit camera orientation.
    
    Attributes:
        vtk_widget: The QVTKRenderWindowInteractor instance.
        render_window: VTK render window.
        renderer: VTK renderer for the scene.
        interactor: VTK interactor for user input.
        _current_structure: Currently displayed InterfaceStructure.
        _ice_bond_actor: VTK actor for ice bonds (lines).
        _water_bond_actor: VTK actor for water bonds (lines).
        _unit_cell_actor: VTK actor for unit cell boundary box.
    """
    
    def __init__(self, parent: QWidget | None = None):
        """Initialize the interface viewer widget.
        
        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        
        # State tracking
        self._current_structure: InterfaceStructure | None = None
        self._current_hydrate: HydrateStructure | None = None
        self._ice_bond_actor: vtkActor | None = None
        self._water_bond_actor: vtkActor | None = None
        self._guest_actor: vtkActor | None = None  # For guest molecules (Issue 2)
        self._unit_cell_actor: vtkActor | None = None
        
        # Set up VTK rendering pipeline
        self._setup_vtk()
    
    def _setup_vtk(self) -> None:
        """Set up the VTK rendering pipeline.
        
        Creates and configures:
        - QVTKRenderWindowInteractor for Qt integration
        - VTK renderer with dark blue background (same as Tab 1)
        - Trackball camera interactor style for mouse controls
        """
        # Create VTK widget (QWidget subclass for Qt integration)
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        
        # Layout with zero margins for full widget area
        layout = QVBoxLayout(self)
        layout.addWidget(self.vtk_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Get render window
        self.render_window = self.vtk_widget.GetRenderWindow()
        
        # Create and add renderer
        self.renderer = vtkRenderer()
        self.render_window.AddRenderer(self.renderer)
        
        # Set dark blue background (same as Tab 1 per CONTEXT.md)
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
    
    def set_interface_structure(self, structure: InterfaceStructure) -> None:
        """Load and display an interface structure.
        
        Converts the InterfaceStructure to separate ice and water VTK molecules,
        creates actors for atoms, bonds, and unit cell, then displays with
        Z-axis side-view camera.
        
        Args:
            structure: An InterfaceStructure containing ice and water atoms.
        """
        # Clear previous actors
        self._clear_actors()
        
        # Store the structure reference
        self._current_structure = structure
        
        # Convert to separate ice and water VTK molecules
        ice_mol, water_mol = interface_to_vtk_molecules(structure)
        
        # Extract bonds from each molecule with PBC wrapping
        ice_bonds = self._extract_bonds(ice_mol, structure.cell)
        water_bonds = self._extract_bonds(water_mol, structure.cell)
        
        # Create bond line actors
        self._ice_bond_actor = create_bond_lines_actor(
            ice_bonds, ICE_COLOR, BOND_LINE_WIDTH
        )
        self._water_bond_actor = create_bond_lines_actor(
            water_bonds, WATER_COLOR, BOND_LINE_WIDTH
        )
        
        # Create unit cell actor
        self._unit_cell_actor = create_unit_cell_actor(structure.cell)
        
        # Add all actors to renderer (bond lines and unit cell only)
        self.renderer.AddActor(self._ice_bond_actor)
        self.renderer.AddActor(self._water_bond_actor)
        self.renderer.AddActor(self._unit_cell_actor)
        
        # Auto-fit camera to frame all actors
        self._reset_camera()
        
        # Render the scene
        self.render_window.Render()
    
    def set_hydrate_structure(self, structure: HydrateStructure) -> None:
        """Load and display a hydrate structure as interface (Issue 2).
        
        Renders:
        - Water framework: lines (same as interface)
        - Guest molecules: ball-and-stick (same as HydrateViewer)
        
        Args:
            structure: A HydrateStructure containing water and guest molecules.
        """
        # Clear previous actors
        self._clear_actors()
        
        # Store the structure reference
        self._current_hydrate = structure
        self._current_structure = None  # Not an interface
        
        # Render water framework as lines (like interface)
        # Use hydrate renderer to create water framework actor
        hydrate_actors = render_hydrate_structure(structure, "ball_and_stick")
        
        # hydrate_actors[0] = water_actor, [1] = guest_actor
        self._water_bond_actor = hydrate_actors[0]
        self._guest_actor = hydrate_actors[1]
        
        # Create unit cell actor
        self._unit_cell_actor = create_unit_cell_actor(structure.cell)
        
        # Add actors to renderer
        self.renderer.AddActor(self._water_bond_actor)
        self.renderer.AddActor(self._guest_actor)
        self.renderer.AddActor(self._unit_cell_actor)
        
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
    
    def _reset_camera(self) -> None:
        """Reset camera for optimal viewing of ice-water interface in wide viewer.
        
        The interface viewer is a wide horizontal rectangle. Interface structures
        have ice-water-ice layers stacked along Z-axis. This camera orientation
        makes Z horizontal (left-right) to utilize the wide viewer space.
        """
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
        
        # Position camera at an angle to see the slab layers
        # Looking from above and to the side
        camera.SetPosition(
            center_x + diagonal * 0.5,
            center_y + diagonal * 0.5,
            center_z + diagonal * 0.5
        )
        camera.SetFocalPoint(center_x, center_y, center_z)
        
        # Make Z horizontal (along X direction) for wide viewer
        # ViewUp = (0, 0, 1) would make Z vertical
        # ViewUp = (0, 1, 0) makes Y vertical, Z horizontal
        camera.SetViewUp(0, 1, 0)
        
        self.renderer.ResetCameraClippingRange()
    
    def _clear_actors(self) -> None:
        """Remove all actors from renderer and reset state."""
        # Remove ice bond actor
        if self._ice_bond_actor is not None:
            self.renderer.RemoveActor(self._ice_bond_actor)
            self._ice_bond_actor = None
        
        # Remove water bond actor
        if self._water_bond_actor is not None:
            self.renderer.RemoveActor(self._water_bond_actor)
            self._water_bond_actor = None
        
        # Remove guest actor (Issue 2)
        if self._guest_actor is not None:
            self.renderer.RemoveActor(self._guest_actor)
            self._guest_actor = None
        
        # Remove unit cell actor
        if self._unit_cell_actor is not None:
            self.renderer.RemoveActor(self._unit_cell_actor)
            self._unit_cell_actor = None
        
        # Clear current structures
        self._current_structure = None
        self._current_hydrate = None
    
    def clear(self) -> None:
        """Clear the current structure from the viewer.
        
        Removes all actors and renders an empty viewport.
        """
        self._clear_actors()
        self.render_window.Render()
    
    def reset_camera(self) -> None:
        """Reset camera for optimal interface viewing.
        
        Reorients camera to show slab layers horizontally in the wide viewer.
        """
        self._reset_camera()
        self.render_window.Render()
