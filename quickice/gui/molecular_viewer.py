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
from quickice.gui.vtk_utils import candidate_to_vtk_molecule


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
        
        # Render the cleared scene
        self.render_window.Render()
    
    def render(self) -> None:
        """Explicitly render the current scene.
        
        Useful for triggering renders after external state changes
        or when the widget needs to be refreshed.
        """
        self.render_window.Render()
