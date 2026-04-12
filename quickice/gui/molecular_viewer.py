"""VTK-based 3D molecular viewer widget.

This module provides the MolecularViewerWidget class for rendering
molecular structures using VTK with PySide6 Qt integration.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QTimer
 
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.all import (
    vtkRenderer,
    vtkInteractorStyleTrackballCamera,
    vtkMoleculeMapper,
    vtkActor,
    vtkColorTransferFunction,
    vtkFloatArray,
)
 
from quickice.structure_generation.types import Candidate
from quickice.ranking.types import RankedCandidate
from quickice.gui.vtk_utils import (
    candidate_to_vtk_molecule,
    detect_hydrogen_bonds,
    create_hbond_actor,
    create_unit_cell_actor,
)

# Unit conversion: VTK periodic table provides radii in Angstroms (Å),
# but QuickIce positions are in nanometers (nm).
# Multiply all radius scale factors by this to convert Å → nm.
ANGSTROM_TO_NM = 0.1


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
        
        # Auto-rotation animation (per ADVVIZ-03)
        self._auto_rotating: bool = False
        self._rotation_timer = QTimer(self)
        self._rotation_timer.timeout.connect(self._rotate_step)
        self._degrees_per_tick = 10.0 * 0.016  # ~10°/sec at 60 FPS per CONTEXT.md
        
        # Color-by-property mapping (per ADVVIZ-05)
        self._color_mode: str = "cpk"  # Default: standard CPK colors
        self._current_ranked_candidate: RankedCandidate | None = None
        
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
        
        # Apply unit conversion: VTK radii are in Å, positions are in nm
        # VTK default 0.30 in Å system → 0.03 in nm system
        self._mapper.SetAtomicRadiusScaleFactor(0.30 * ANGSTROM_TO_NM)
        # VTK default 0.075 in Å system → 0.0075 in nm system
        self._mapper.SetBondRadius(0.075 * ANGSTROM_TO_NM)
        
        # Create actor with the mapper
        self._molecule_actor = vtkActor()
        self._molecule_actor.SetMapper(self._mapper)
        
        # Add to renderer (will be updated when molecule is loaded)
        self.renderer.AddActor(self._molecule_actor)
    
    def set_candidate(self, candidate: Candidate) -> None:
        """Load and display a molecular structure.
        
        Converts the Candidate to a VTK molecule, updates the mapper,
        auto-fits the structure in the viewport, and triggers a render.
        
        For triclinic phases (Ice II, Ice V), displays the ORIGINAL triclinic
        structure rather than the transformed orthogonal version. This ensures
        Tab 1 viewer shows the correct unit cell with intact molecules.
        
        Args:
            candidate: A QuickIce Candidate containing positions, atom_names,
                       cell matrix, and nmolecules.
        """
        # Store the candidate reference
        self._current_candidate = candidate
        
        # For display in Tab 1, use original triclinic structure if available
        # (original_positions/original_cell are set when triclinic transformation was applied)
        # This ensures viewers show correct triclinic unit cells with intact molecules,
        # while Tab 2 interface construction uses the transformed orthogonal structure.
        if candidate.original_positions is not None and candidate.original_cell is not None:
            # Create display candidate with original triclinic data
            display_candidate = Candidate(
                positions=candidate.original_positions,
                atom_names=candidate.atom_names[:len(candidate.original_positions)],  # Match atom count
                cell=candidate.original_cell,
                nmolecules=len(candidate.original_positions) // 3,  # Original molecule count
                phase_id=candidate.phase_id,
                seed=candidate.seed,
                metadata=candidate.metadata,
            )
        else:
            # No transformation was applied, use as-is
            display_candidate = candidate
        
        # Convert to VTK molecule
        mol = candidate_to_vtk_molecule(display_candidate)
        
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
        """Switch between VDW, ball-and-stick, and stick representation modes.
        
        Args:
            mode: One of "vdw", "ball_and_stick", or "stick"
        
        Per VIEWER-03: User can switch between representation modes.
        - VDW: Space-filling van der Waals spheres (full size)
        - Ball-and-stick: Small spheres connected by visible cylinders
        - Stick: Only cylinders (bonds), no atom spheres
        """
        if mode not in ("vdw", "ball_and_stick", "stick"):
            raise ValueError(f"Invalid representation mode: {mode}. "
                             f"Must be 'vdw', 'ball_and_stick', or 'stick'")
        
        self._representation_mode = mode
        
        if mode == "vdw":
            # Space-filling VDW spheres - use VTK defaults for proper sizing
            self._mapper.UseVDWSpheresSettings()
            self._mapper.SetAtomicRadiusTypeToVDWRadius()
            # VTK default scale 1.0 would touch neighbors at 3.1 Å distance,
            # but ice O-O distance ~2.76 Å. Use scale 0.8 for space-filling.
            # Convert Å → nm: 0.8 × 0.1 = 0.08
            self._mapper.SetAtomicRadiusScaleFactor(0.8 * ANGSTROM_TO_NM)
            # Bond radius also needs unit conversion
            self._mapper.SetBondRadius(0.075 * ANGSTROM_TO_NM)
            # Show atoms
            self._mapper.RenderAtomsOn()
        elif mode == "ball_and_stick":
            # Ball-and-stick: use VTK defaults for proper sphere/bond ratio
            self._mapper.UseBallAndStickSettings()
            self._mapper.SetAtomicRadiusTypeToVDWRadius()
            # VTK default 0.30 in Å system, reduce to 0.25 for smaller spheres
            # Convert Å → nm: 0.25 × 0.1 = 0.025
            self._mapper.SetAtomicRadiusScaleFactor(0.25 * ANGSTROM_TO_NM)
            # VTK default 0.075 in Å system, convert to nm: 0.075 × 0.1 = 0.0075
            self._mapper.SetBondRadius(0.075 * ANGSTROM_TO_NM)
            # Show atoms
            self._mapper.RenderAtomsOn()
        else:  # stick
            # Stick mode: equal sphere and bond radii for gap-free joints
            self._mapper.UseLiquoriceStickSettings()
            self._mapper.SetAtomicRadiusTypeToUnitRadius()
            # VTK default 0.15 for LiquoriceStick (equal to bond radius)
            # Convert Å → nm: 0.15 × 0.1 = 0.015
            self._mapper.SetAtomicRadiusScaleFactor(0.15 * ANGSTROM_TO_NM)
            # Match sphere size for seamless joints (also converted)
            self._mapper.SetBondRadius(0.15 * ANGSTROM_TO_NM)
            # Show atoms (with UnitRadius, all atoms same size)
            self._mapper.RenderAtomsOn()
        
        self.render_window.Render()
    
    def get_representation_mode(self) -> str:
        """Return current representation mode.
        
        Returns:
            "vdw", "ball_and_stick", or "stick"
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
            # Use original triclinic structure for H-bond detection if available
            # (same as set_candidate display logic)
            candidate = self._current_candidate
            if candidate.original_positions is not None and candidate.original_cell is not None:
                display_candidate = Candidate(
                    positions=candidate.original_positions,
                    atom_names=candidate.atom_names[:len(candidate.original_positions)],
                    cell=candidate.original_cell,
                    nmolecules=len(candidate.original_positions) // 3,
                    phase_id=candidate.phase_id,
                    seed=candidate.seed,
                    metadata=candidate.metadata,
                )
            else:
                display_candidate = candidate
            
            # Detect H-bonds from current structure
            hbonds = detect_hydrogen_bonds(display_candidate)
            
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
            
            # Use original cell for display if available (triclinic phases)
            # This ensures the unit cell box matches the displayed structure
            cell = self._current_candidate.original_cell
            if cell is None:
                cell = self._current_candidate.cell
            
            # Create and add new actor
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
    
    def zoom_to_fit(self) -> None:
        """Zoom to fit structure in viewport.
        
        Alias for reset_camera() - resets camera to frame all actors.
        Safe to call even when no candidate is loaded.
        
        Per ADVVIZ-02: User can click zoom-to-fit button to automatically 
        frame the structure in viewport.
        """
        self.reset_camera()
    
    def _rotate_step(self) -> None:
        """Perform one rotation step for auto-rotation animation.
        
        Called by QTimer at ~60 FPS. Rotates camera azimuthally by a small
        amount to create smooth presentation-quality rotation.
        """
        camera = self.renderer.GetActiveCamera()
        camera.Azimuth(self._degrees_per_tick)
        self.render_window.Render()
    
    def toggle_auto_rotation(self, enabled: bool) -> None:
        """Toggle animated auto-rotation of the structure.
        
        Args:
            enabled: True to start auto-rotation, False to stop
        
        Per ADVVIZ-03: User can toggle animated auto-rotation of the 
        structure for presentation. Rotation is slow & smooth (~10°/sec).
        """
        if enabled and not self._auto_rotating:
            self._auto_rotating = True
            self._rotation_timer.start(16)  # ~60 FPS
        elif not enabled and self._auto_rotating:
            self._auto_rotating = False
            self._rotation_timer.stop()
    
    def is_auto_rotating(self) -> bool:
        """Return whether auto-rotation is currently active.
        
        Returns:
            True if auto-rotation is running, False otherwise
        """
        return self._auto_rotating
    
    def set_ranked_candidate(self, ranked: RankedCandidate) -> None:
        """Load a ranked candidate for property-based coloring.
        
        Stores the ranked candidate reference and loads its structure.
        If color-by-property is active, re-applies the coloring.
        
        Args:
            ranked: A RankedCandidate with energy/density scores
        """
        self._current_ranked_candidate = ranked
        self.set_candidate(ranked.candidate)
        
        # Re-apply color mode if not CPK
        if self._color_mode != "cpk":
            self.set_color_by_property(self._color_mode)
    
    def set_color_by_property(self, mode: str) -> None:
        """Color atoms by property (energy or density ranking).
        
        Args:
            mode: One of "cpk" (default), "energy", or "density"
        
        Per ADVVIZ-05: User can color atoms by property (energy ranking 
        or density ranking) to highlight favorable structures.
        """
        if mode not in ("cpk", "energy", "density"):
            raise ValueError(f"Invalid color mode: {mode}. "
                           f"Must be 'cpk', 'energy', or 'density'")
        
        self._color_mode = mode
        
        if mode == "cpk":
            # Restore default element-based coloring
            self._mapper.SetColorModeToDefault()
            self._mapper.ScalarVisibilityOff()
        else:
            # Property-based coloring requires ranked candidate
            if self._current_ranked_candidate is None:
                # Can't color without ranking data, fall back to CPK
                self._color_mode = "cpk"
                self._mapper.SetColorModeToDefault()
                self._mapper.ScalarVisibilityOff()
            else:
                self._apply_property_coloring(mode)
        
        self.render_window.Render()
    
    def _apply_property_coloring(self, mode: str) -> None:
        """Apply property-based coloring to molecule atoms.
        
        Creates a scalar array with property values and configures
        the mapper with a viridis-like colormap.
        
        Args:
            mode: "energy" or "density"
        """
        # Get the molecule data
        mol = self._mapper.GetInput()
        if mol is None:
            return
        
        # Create scalar array for coloring
        scalar_array = vtkFloatArray()
        scalar_array.SetName("PropertyRanking")
        
        # Get the property value to use
        if mode == "energy":
            # Lower energy = better rank = lower color value
            # Normalize by using 1/rank (best rank 1 = value 1.0)
            value = 1.0 / max(1, self._current_ranked_candidate.rank)
        else:  # density
            # Lower density deviation = better
            value = 1.0 / max(1, self._current_ranked_candidate.rank)
        
        # All atoms in molecule get the same property value
        # (coloring is per-candidate, not per-atom)
        n_atoms = mol.GetNumberOfAtoms()
        for _ in range(n_atoms):
            scalar_array.InsertNextValue(value)
        
        # Add to molecule's atom data
        mol.GetAtomData().AddArray(scalar_array)
        
        # Configure mapper for scalar coloring
        self._mapper.ScalarVisibilityOn()
        self._mapper.SetColorModeToMapScalars()
        self._mapper.SelectColorArray("PropertyRanking")
        self._mapper.SetScalarModeToUsePointFieldData()
        
        # Create viridis-like colormap (per CONTEXT.md)
        ctf = vtkColorTransferFunction()
        ctf.SetColorSpaceToDiverging()
        # Dark purple (low value = good rank)
        ctf.AddRGBPoint(0.0, 0.267, 0.004, 0.329)
        # Yellow (high value = worse rank)
        ctf.AddRGBPoint(1.0, 0.993, 0.906, 0.144)
        
        self._mapper.SetLookupTable(ctf)
    
    def get_color_mode(self) -> str:
        """Return current color mode.
        
        Returns:
            "cpk", "energy", or "density"
        """
        return self._color_mode
    
    def get_viewer_state(self) -> dict:
        """Return all current viewer state for UI synchronization.
        
        Returns:
            Dictionary with all toggle states and current mode settings.
            Used by MainWindow toolbar to sync button states.
        """
        return {
            "representation_mode": self._representation_mode,
            "show_hydrogen_bonds": self._show_hydrogen_bonds,
            "show_unit_cell": self._show_unit_cell,
            "auto_rotating": self._auto_rotating,
            "color_mode": self._color_mode,
        }
