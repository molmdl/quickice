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
        
        For hydrate-derived interfaces (with guest molecules), also renders
        guest molecules as ball-and-stick (Issue 2 fix).
        
        Args:
            structure: An InterfaceStructure containing ice and water atoms,
                       and optionally guest molecules.
        """
        # Clear previous actors
        self._clear_actors()
        
        # Store the structure reference
        self._current_structure = structure
        
        # Extract atoms into ice/water/guest categories
        ice_atom_names = structure.atom_names[:structure.ice_atom_count]
        water_atom_names = structure.atom_names[structure.ice_atom_count:]
        
        # Define standard ice/water atom types
        # For hydrate structures, we identify guests by atom type
        # Water atoms: OW (oxygen), HW1/HW2 (hydrogens), MW (virtual site)
        # Ice atoms (from hydrate lattice): OW, HW1, HW2, MW (same as water in TIP4P)
        # Guest atoms: C, O (THF), H (from guests)
        
        # Simplest approach: Guest molecules are identified by C atoms (always from CH4/THF)
        # Also include any H atoms that are adjacent to C atoms
        guest_atom_indices = []
        
        # First pass: identify C atoms (definitely guest for hydrate)
        for i, name in enumerate(structure.atom_names):
            if name == "C":  # Carbon - always guest in hydrate
                guest_atom_indices.append(i)
        
        # Second pass: identify H atoms that are likely from guests
        # (adjacent to C atoms, not water-bound)
        # For now, include all H atoms in ice region after water atoms if C present
        if guest_atom_indices:
            # If we have guest C atoms, check for H atoms in ice region
            # that might be from guests
            ice_atom_count_for_h = structure.ice_atom_count
            for i in range(ice_atom_count_for_h):
                name = structure.atom_names[i]
                if name == "H":
                    # This H could be from guest - include it
                    # (Over-inclusive is fine, will only add bonds that are close enough)
                    if i not in guest_atom_indices:
                        guest_atom_indices.append(i)
        
        # Alternative simpler check: presence of C atoms indicates guest
        has_carbon = "C" in structure.atom_names[:structure.ice_atom_count]
        
        # Check if this is a hydrate-derived interface (has guest molecules)
        has_guest_molecules = len(guest_atom_indices) > 0
        
        if has_guest_molecules:
            # Separate ice from guest atoms in the ice region
            ice_atom_types = {"O", "H", "OW", "HW1", "HW2", "MW"}  # Water framework atom types
            ice_only_indices = []
            guest_in_ice_region = []
            for i, name in enumerate(ice_atom_names):
                if name in ice_atom_types:
                    ice_only_indices.append(i)
                else:
                    guest_in_ice_region.append(i)
            
            # Extract ice-only positions for bond line rendering
            ice_positions = structure.positions[:structure.ice_atom_count]
            ice_only_positions = ice_positions[ice_only_indices]
            
            # Extract guest positions (from ice region that are guest atoms)
            guest_positions = structure.positions[guest_atom_indices]
            guest_names = [structure.atom_names[i] for i in guest_atom_indices]
            
            # Create ice VTK molecule (only ice atoms)
            ice_mol = self._create_vtk_molecule_from_indices(
                ice_only_positions,
                [ice_atom_names[i] for i in ice_only_indices]
            )
        else:
            # Standard interface (no guests) - use existing logic
            ice_mol = None
        
        # Get water molecule for water bonds
        water_start = structure.ice_atom_count
        water_positions = structure.positions[water_start:]
        water_mol = self._create_vtk_molecule_from_indices(
            water_positions,
            water_atom_names
        )
        
        # Extract bonds from each molecule with PBC wrapping
        if ice_mol is not None:
            ice_bonds = self._extract_bonds(ice_mol, structure.cell)
        else:
            # Fallback: convert full structure using existing method
            ice_mol, water_mol_fallback = interface_to_vtk_molecules(structure)
            ice_bonds = self._extract_bonds(ice_mol, structure.cell)
            water_mol = water_mol_fallback
        
        water_bonds = self._extract_bonds(water_mol, structure.cell)
        
        # Create bond line actors
        self._ice_bond_actor = create_bond_lines_actor(
            ice_bonds, ICE_COLOR, BOND_LINE_WIDTH
        )
        self._water_bond_actor = create_bond_lines_actor(
            water_bonds, WATER_COLOR, BOND_LINE_WIDTH
        )
        
        # Create guest actor if present (ball-and-stick style)
        if has_guest_molecules:
            # Create a mock HydrateStructure for guest rendering
            # This uses the same rendering as HydrateViewer
            guest_actor = self._create_guest_actor_from_indices(
                guest_positions,
                guest_names,
                structure.cell
            )
            self._guest_actor = guest_actor
        
        # Create unit cell actor
        self._unit_cell_actor = create_unit_cell_actor(structure.cell)
        
        # Add actors to renderer
        self.renderer.AddActor(self._ice_bond_actor)
        self.renderer.AddActor(self._water_bond_actor)
        if has_guest_molecules and self._guest_actor is not None:
            self.renderer.AddActor(self._guest_actor)
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
    
    def _create_vtk_molecule_from_indices(
        self,
        positions: np.ndarray,
        atom_names: list[str]
    ) -> vtkMolecule:
        """Create a vtkMolecule from positions and atom names.
        
        Args:
            positions: (N_atoms, 3) positions in nm
            atom_names: List of atom names
        
        Returns:
            vtkMolecule with atoms and bonds
        """
        from vtkmodules.all import vtkMolecule
        
        # Build a simple molecule using distance-based bonding
        # Similar to hydrate_renderer's approach
        molecule = vtkMolecule()
        
        # Add atoms
        atom_ids = []
        element_map = {
            "O": 8, "OW": 8,
            "H": 1, "HW1": 1, "HW2": 1,
            "C": 6,
        }
        
        for pos, name in zip(positions, atom_names):
            atomic_num = element_map.get(name, 6)  # Default to carbon
            atom_id = molecule.AppendAtom(atomic_num, float(pos[0]), float(pos[1]), float(pos[2]))
            atom_ids.append(atom_id)
        
        # Add bonds based on distance (same threshold as hydrate_renderer)
        BOND_THRESHOLD = 0.16  # nm
        n_atoms = len(atom_ids)
        for i in range(n_atoms):
            for j in range(i + 1, n_atoms):
                dist = np.linalg.norm(positions[i] - positions[j])
                if dist < BOND_THRESHOLD:
                    # Skip H-H bonds
                    if atom_names[i] == "H" and atom_names[j] == "H":
                        continue
                    molecule.AppendBond(atom_ids[i], atom_ids[j], 1)
        
        return molecule
    
    def _create_guest_actor_from_indices(
        self,
        positions: np.ndarray,
        atom_names: list[str],
        cell: np.ndarray
    ) -> vtkActor:
        """Create a ball-and-stick actor for guest molecules.
        
        Args:
            positions: (N_atoms, 3) guest positions in nm
            atom_names: List of atom names for guests
            cell: (3, 3) cell matrix for PBC
        
        Returns:
            vtkActor with ball-and-stick rendering
        """
        from vtkmodules.all import vtkMoleculeMapper, vtkMolecule, vtkActor, vtkMatrix3x3
        
        molecule = vtkMolecule()
        
        # Add atoms
        element_map = {
            "C": 6, "H": 1, "O": 8,
        }
        
        for pos, name in zip(positions, atom_names):
            atomic_num = element_map.get(name, 6)
            molecule.AppendAtom(atomic_num, float(pos[0]), float(pos[1]), float(pos[2]))
        
        # Add bonds based on distance within molecules
        # Group atoms by molecule type (simplified: assume sorted by molecule)
        # For now, use simple distance-based bonding
        BOND_THRESHOLD = 0.16  # nm
        n_atoms = molecule.GetNumberOfAtoms()
        
        # Get atom positions from molecule
        for i in range(n_atoms):
            for j in range(i + 1, n_atoms):
                atom_i = molecule.GetAtom(i)
                atom_j = molecule.GetAtom(j)
                pos_i = np.array(atom_i.GetPosition())
                pos_j = np.array(atom_j.GetPosition())
                dist = np.linalg.norm(pos_i - pos_j)
                if dist < BOND_THRESHOLD:
                    # Skip H-H bonds
                    name_i = atom_names[i]
                    name_j = atom_names[j]
                    if name_i == "H" and name_j == "H":
                        continue
                    molecule.AppendBond(i, j, 1)
        
        # Set lattice for PBC
        lattice = vtkMatrix3x3()
        cell_t = cell.T
        for i in range(3):
            for j in range(3):
                lattice.SetElement(i, j, float(cell_t[i, j]))
        molecule.SetLattice(lattice)
        
        # Create mapper with ball-and-stick settings
        mapper = vtkMoleculeMapper()
        mapper.SetInputData(molecule)
        mapper.UseBallAndStickSettings()
        mapper.SetAtomicRadiusTypeToVDWRadius()
        mapper.SetAtomicRadiusScaleFactor(0.25 * ANGSTROM_TO_NM)
        mapper.SetBondRadius(0.075 * ANGSTROM_TO_NM)
        mapper.SetRenderAtoms(True)
        mapper.SetRenderBonds(True)
        
        # Set bond color for guests (matching hydrate_renderer)
        mapper.SetBondColor(180, 180, 180)  # Gray
        
        # Create actor
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
