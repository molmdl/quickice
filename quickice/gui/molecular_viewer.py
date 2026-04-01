"""VTK-based 3D molecular viewer widget.

This module provides the MolecularViewerWidget class for rendering
molecular structures using VTK with PySide6 Qt integration.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.all import (
    vtkRenderer,
    vtkInteractorStyleTrackballCamera,
    vtkMoleculeMapper,
    vtkActor,
)

from quickice.structure_generation.types import Candidate
from quickice.gui.vtk_utils import (
    candidate_to_vtk_molecule,
    detect_hydrogen_bonds,
    create_hbond_actor,
    create_unit_cell_actor,
)


class MolecularViewerWidget(QWidget):
    """VTK-based 3D molecular viewer widget for ice structure visualization.
    
    This widget provides a 3D viewport with ball-and-stick molecular rendering,
    mouse controls for rotation/zoom/pan, and auto-fit on structure load.
    
    The widget integrates QVTKRenderWindowInteractor as a QWidget subclass,
    allowing seamless embedding in PySide6 layouts.
    
    Attributes:
        vtk_widget: The QVTKRenderWindowInteractor instance.
        render_window: VTK render window.
        renderer: VTK renderer for the scene.
        interactor: VTK interactor for user input.
        style: Trackball camera style for 3D mouse controls.
    """
    
    def __init__(self, parent: QWidget | None = None):
        """Initialize the molecular viewer widget.
        
        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        
        # State tracking (initialized by _setup_molecule_actor)
        self._molecule_actor: vtkActor | None = None
        self._current_candidate: Candidate | None = None
        self._representation_mode: str = "ball_and_stick"
        
        # Hydrogen bond visualization (default visible per CONTEXT.md)
        self._hbond_actor: vtkActor | None = None
        self._show_hydrogen_bonds: bool = True
        
        # Unit cell visualization (default hidden per CONTEXT.md "non-intrusive")
        self._unit_cell_actor: vtkActor | None = None
        self._show_unit_cell: bool = False
        
        # Set up VTK rendering pipeline
        self._setup_vtk()
        
        # Set up molecule rendering actor
        self._setup_molecule_actor()
    
    def _setup_vtk(self) -> None:
        """Set up the VTK rendering pipeline.
        
        Creates and configures:
        - QVTKRenderWindowInteractor for Qt integration
        - VTK renderer with dark blue background
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
        
        # Set dark blue background (per CONTEXT.md)
        self.renderer.SetBackground(0.1, 0.2, 0.4)
        
        # Get interactor and set trackball camera style
        # This provides standard 3D controls:
        # - Left drag: rotate
        # - Right drag: zoom
        # - Middle drag: pan
        self.interactor = self.render_window.GetInteractor()
        self.style = vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(self.style)
        
        # Initialize the interactor (required before first render)
        self.vtk_widget.Initialize()
    
    def _setup_molecule_actor(self) -> None:
        """Set up the molecule rendering actor.
        
        Creates a vtkMoleculeMapper for ball-and-stick rendering
        and associates it with a vtkActor for scene management.
        """
        # Create molecule mapper with ball-and-stick settings (per VIEWER-02)
        self._mapper = vtkMoleculeMapper()
        self._mapper.UseBallAndStickSettings()
        
        # Set reasonable ball size for visibility
        self._mapper.SetAtomicRadiusScaleFactor(0.3)
        
        # Create actor with the mapper
        self._molecule_actor = vtkActor()
        self._molecule_actor.SetMapper(self._mapper)
        
        # Add to renderer (will be updated when molecule is loaded)
        self.renderer.AddActor(self._molecule_actor)
    
    def set_candidate(self, candidate: Candidate) -> None:
        """Load and display a molecular structure.
        
        Converts the Candidate to a VTK molecule, updates the mapper,
        auto-fits the structure in the viewport, and triggers a render.
        
        Args:
            candidate: A QuickIce Candidate containing positions, atom_names,
                       cell matrix, and nmolecules.
        """
        # Store the candidate reference
        self._current_candidate = candidate
        
        # Convert to VTK molecule
        mol = candidate_to_vtk_molecule(candidate)
        
        # Set input to mapper
        self._mapper.SetInputData(mol)
        
        # Re-create hydrogen bonds if visible
        if self._show_hydrogen_bonds:
            self.set_hydrogen_bonds_visible(True)
        
        # Re-create unit cell if visible
        if self._show_unit_cell:
            self.set_unit_cell_visible(True)
        
        # Auto-fit structure in viewport
        self.reset_camera()
        
        # Render the updated scene
        self.render_window.Render()
    
    def reset_camera(self) -> None:
        """Reset camera to auto-fit all actors in viewport.
        
        Calls ResetCamera() to frame the entire structure, then
        triggers a render to update the display.
        """
        self.renderer.ResetCamera()
        self.render_window.Render()
    
    def clear(self) -> None:
        """Clear the current structure from the viewer.
        
        Removes the current candidate reference and clears the molecular
        display. The viewer shows an empty viewport after this call.
        """
        self._current_candidate = None
        
        # Remove the molecule actor if it exists
        if self._molecule_actor is not None:
            self.renderer.RemoveActor(self._molecule_actor)
            self._molecule_actor = None
        
        # Remove H-bond actor if it exists
        if self._hbond_actor is not None:
            self.renderer.RemoveActor(self._hbond_actor)
            self._hbond_actor = None
        
        # Remove unit cell actor if it exists
        if self._unit_cell_actor is not None:
            self.renderer.RemoveActor(self._unit_cell_actor)
            self._unit_cell_actor = None
        
        # Render the cleared scene
        self.render_window.Render()
    
    def render(self) -> None:
        """Explicitly render the current scene.
        
        Useful for triggering renders after external state changes
        or when the widget needs to be refreshed.
        """
        self.render_window.Render()
    
    def set_representation_mode(self, mode: str) -> None:
        """Switch between ball-and-stick and stick representation modes.
        
        Args:
            mode: Either "ball_and_stick" or "stick"
        
        Per VIEWER-03: User can switch between ball-and-stick and stick-only 
        representations. Stick mode ("liquorice") shows uniform thickness tubes 
        for bonds without distinct atom balls.
        """
        if mode not in ("ball_and_stick", "stick"):
            raise ValueError(f"Invalid representation mode: {mode}. "
                             f"Must be 'ball_and_stick' or 'stick'")
        
        self._representation_mode = mode
        
        if mode == "ball_and_stick":
            self._mapper.UseBallAndStickSettings()
        else:  # stick
            self._mapper.UseLiquoriceStickSettings()
        
        self.render_window.Render()
    
    def get_representation_mode(self) -> str:
        """Return current representation mode.
        
        Returns:
            "ball_and_stick" or "stick"
        """
        return self._representation_mode
    
    def set_hydrogen_bonds_visible(self, visible: bool) -> None:
        """Toggle hydrogen bond visualization as dashed lines.
        
        Args:
            visible: True to show H-bonds, False to hide
        
        Per VIEWER-05: User can view hydrogen bonds displayed as dashed 
        lines between neighboring molecules.
        """
        self._show_hydrogen_bonds = visible
        
        if visible and self._current_candidate is not None:
            # Detect H-bonds from current structure
            hbonds = detect_hydrogen_bonds(self._current_candidate)
            
            # Remove old actor if exists
            if self._hbond_actor is not None:
                self.renderer.RemoveActor(self._hbond_actor)
            
            # Create and add new actor if H-bonds detected
            if hbonds:
                self._hbond_actor = create_hbond_actor(hbonds)
                self.renderer.AddActor(self._hbond_actor)
            else:
                self._hbond_actor = None
        
        elif not visible and self._hbond_actor is not None:
            # Remove H-bond actor
            self.renderer.RemoveActor(self._hbond_actor)
            self._hbond_actor = None
        
        self.render_window.Render()
    
    def get_hydrogen_bonds_visible(self) -> bool:
        """Return whether hydrogen bonds are visible.
        
        Returns:
            True if H-bonds are shown, False otherwise
        """
        return self._show_hydrogen_bonds
    
    def set_unit_cell_visible(self, visible: bool) -> None:
        """Toggle unit cell boundary box visualization.
        
        Args:
            visible: True to show unit cell, False to hide
        
        Per ADVVIZ-01: User can toggle unit cell boundary box to 
        visualize the simulation cell.
        """
        self._show_unit_cell = visible
        
        if visible and self._current_candidate is not None:
            # Remove old actor if exists
            if self._unit_cell_actor is not None:
                self.renderer.RemoveActor(self._unit_cell_actor)
            
            # Create and add new actor
            self._unit_cell_actor = create_unit_cell_actor(self._current_candidate.cell)
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
    
    def zoom_to_fit(self) -> None:
        """Zoom to fit structure in viewport.
        
        Alias for reset_camera() - resets camera to frame all actors.
        Safe to call even when no candidate is loaded.
        
        Per ADVVIZ-02: User can click zoom-to-fit button to automatically 
        frame the structure in viewport.
        """
        self.reset_camera()
