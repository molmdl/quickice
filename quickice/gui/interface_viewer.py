"""VTK-based 3D interface structure viewer widget.

This module provides the InterfaceViewerWidget class for rendering
ice-water interface structures with phase-distinct coloring.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.all import (
    vtkRenderer,
    vtkInteractorStyleTrackballCamera,
    vtkMoleculeMapper,
    vtkActor,
)

import numpy as np
from quickice.structure_generation.types import InterfaceStructure
from quickice.gui.vtk_utils import (
    interface_to_vtk_molecules,
    create_bond_lines_actor,
    create_unit_cell_actor,
)

# Color constants for phase-distinct visualization
ICE_COLOR = (0.0, 0.8, 0.8)         # Cyan
WATER_COLOR = (0.39, 0.58, 0.93)    # Cornflower blue
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
        _ice_actor: VTK actor for ice atoms.
        _water_actor: VTK actor for water atoms.
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
        self._ice_actor: vtkActor | None = None
        self._water_actor: vtkActor | None = None
        self._ice_bond_actor: vtkActor | None = None
        self._water_bond_actor: vtkActor | None = None
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
        
        # Create atom actors for each phase
        self._ice_actor = self._create_phase_actor(ice_mol, ICE_COLOR)
        self._water_actor = self._create_phase_actor(water_mol, WATER_COLOR)
        
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
        
        # Add all actors to renderer
        self.renderer.AddActor(self._ice_actor)
        self.renderer.AddActor(self._water_actor)
        self.renderer.AddActor(self._ice_bond_actor)
        self.renderer.AddActor(self._water_bond_actor)
        self.renderer.AddActor(self._unit_cell_actor)
        
        # Auto-fit camera to frame all actors
        self._reset_camera()
        
        # Render the scene
        self.render_window.Render()
    
    def _create_phase_actor(self, mol, color_rgb: tuple) -> vtkActor:
        """Create a VTK actor for a phase (ice or water).
        
        Configures vtkMoleculeMapper with single-color atoms and
        disabled 3D bonds (bonds rendered separately as 2D lines).
        
        Args:
            mol: vtkMolecule containing atoms and bonds.
            color_rgb: RGB color tuple with values in [0, 1].
        
        Returns:
            A vtkActor configured for ball-and-stick rendering.
        """
        # Create molecule mapper
        mapper = vtkMoleculeMapper()
        mapper.SetInputData(mol)

        # Set single color mode for all atoms in this phase
        # VTK 9.5+ uses SetAtomColorMode(int) instead of SetAtomColorModeToSingleColor()
        mapper.SetAtomColorMode(mapper.SingleColor)
        
        # Convert float RGB to uint8 (multiply by 255)
        r, g, b = color_rgb
        mapper.SetAtomColor(int(r * 255), int(g * 255), int(b * 255))
        
        # Disable 3D bond rendering (bonds shown as 2D lines instead)
        mapper.RenderBondsOff()
        
        # Use unit radius with small scale for performance
        mapper.SetAtomicRadiusTypeToUnitRadius()
        mapper.SetAtomicRadiusScaleFactor(0.2 * ANGSTROM_TO_NM)
        
        # Create and return actor
        actor = vtkActor()
        actor.SetMapper(mapper)
        return actor
    
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
        """Reset camera to auto-fit all actors in viewport.
        
        Uses VTK's default camera behavior which provides an isometric-style
        view optimized for the structure's aspect ratio. This is better for
        horizontal slab structures (ice-water interfaces) than a fixed side view.
        """
        self.renderer.ResetCamera()
        self.renderer.ResetCameraClippingRange()
    
    def _clear_actors(self) -> None:
        """Remove all actors from renderer and reset state."""
        # Remove ice actor
        if self._ice_actor is not None:
            self.renderer.RemoveActor(self._ice_actor)
            self._ice_actor = None
        
        # Remove water actor
        if self._water_actor is not None:
            self.renderer.RemoveActor(self._water_actor)
            self._water_actor = None
        
        # Remove ice bond actor
        if self._ice_bond_actor is not None:
            self.renderer.RemoveActor(self._ice_bond_actor)
            self._ice_bond_actor = None
        
        # Remove water bond actor
        if self._water_bond_actor is not None:
            self.renderer.RemoveActor(self._water_bond_actor)
            self._water_bond_actor = None
        
        # Remove unit cell actor
        if self._unit_cell_actor is not None:
            self.renderer.RemoveActor(self._unit_cell_actor)
            self._unit_cell_actor = None
        
        # Clear current structure
        self._current_structure = None
    
    def clear(self) -> None:
        """Clear the current structure from the viewer.
        
        Removes all actors and renders an empty viewport.
        """
        self._clear_actors()
        self.render_window.Render()
    
    def reset_camera(self) -> None:
        """Reset camera to auto-fit all actors in viewport.
        
        Recalculates bounds and resets camera for optimal viewing.
        """
        self._reset_camera()
        self.render_window.Render()
