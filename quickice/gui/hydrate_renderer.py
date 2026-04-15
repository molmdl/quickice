"""Hydrate rendering module for 3D visualization of gas hydrate structures.

This module provides functions to create VTK actors for rendering hydrate structures
with distinct visual styles:
- Water framework: rendered as lines/bonds only (no atom spheres)
- Guest molecules: rendered as ball-and-stick with CPK colors

All coordinates are in nanometers (nm).
"""

import numpy as np
from vtkmodules.all import (
    vtkMoleculeMapper,
    vtkMolecule,
    vtkActor,
)


# CPK coloring for guest molecules (RGB values in [0, 1])
CPK_COLORS: dict[str, tuple[float, float, float]] = {
    "C": (0.6, 0.6, 0.6),   # Carbon - gray
    "O": (1.0, 0.0, 0.0),   # Oxygen - red
    "H": (1.0, 1.0, 1.0),   # Hydrogen - white
}

# Element to atomic number mapping for VTK
ELEMENT_TO_ATOMIC_NUMBER: dict[str, int] = {
    "H": 1,
    "He": 2,
    "Li": 3,
    "Be": 4,
    "B": 5,
    "C": 6,
    "N": 7,
    "O": 8,
    "F": 9,
    "Ne": 10,
    "Na": 11,
    "Mg": 12,
    "Al": 13,
    "Si": 14,
    "P": 15,
    "S": 16,
    "Cl": 17,
    "Ar": 18,
    "K": 19,
    "Ca": 20,
}

# Bond detection distance threshold (nm)
# Typical O-H bond ~0.1 nm (1 Å), O-O bond ~0.276 nm (2.76 Å)
BOND_DISTANCE_THRESHOLD = 0.20  # nm


def _get_element_from_atom_name(atom_name: str) -> str:
    """Extract element symbol from atom name.
    
    Args:
        atom_name: Atom name (e.g., "OW", "HW1", "C", "NA")
    
    Returns:
        Element symbol (e.g., "O", "H", "C", "N")
    """
    # Handle special cases for water
    if atom_name.startswith("OW"):
        return "O"
    if atom_name.startswith("HW"):
        return "H"
    if atom_name.startswith("MW"):
        return "M"  # Virtual site, treat as mass
    
    # Handle single-letter elements (C, O, N, H, etc.)
    if len(atom_name) == 1:
        return atom_name
    if len(atom_name) == 2:
        return atom_name[0]  # Take first letter
    
    # For multi-char names like "CA", "CB", take first letter(s)
    # Common GROMACS atom naming patterns
    if atom_name[0].isupper():
        return atom_name[0]
    
    return atom_name[:2] if len(atom_name) >= 2 else atom_name


def _build_vtk_molecule(
    positions: np.ndarray,
    atom_names: list[str]
) -> vtkMolecule:
    """Build a vtkMolecule from positions and atom names.
    
    Args:
        positions: (N_atoms, 3) numpy array of positions in nm
        atom_names: List of atom names
    
    Returns:
        Configured vtkMolecule with atoms and bonds
    """
    molecule = vtkMolecule()
    
    # Add atoms
    atom_ids = []
    for i, (pos, name) in enumerate(zip(positions, atom_names)):
        element = _get_element_from_atom_name(name)
        # Get atomic number (default to Carbon=6 for unknown elements)
        atomic_number = ELEMENT_TO_ATOMIC_NUMBER.get(element, 6)
        atom_id = molecule.AppendAtom(atomic_number, float(pos[0]), float(pos[1]), float(pos[2]))
        atom_ids.append(atom_id)
    
    # Detect and add bonds based on distance
    n_atoms = len(positions)
    for i in range(n_atoms):
        for j in range(i + 1, n_atoms):
            # Calculate distance
            dist = np.linalg.norm(positions[i] - positions[j])
            if dist < BOND_DISTANCE_THRESHOLD:
                molecule.AppendBond(atom_ids[i], atom_ids[j], 1)  # Single bond
    
    return molecule


def create_water_framework_actor(structure) -> vtkActor:
    """Create a line-only actor for the water framework.
    
    The water framework is rendered as bonds only (no atom spheres),
    creating a clean wireframe appearance of the hydrogen-bonded network.
    
    Args:
        structure: HydrateStructure with molecule_index containing water molecules
    
    Returns:
        vtkActor with water framework rendered as lines
    """
    # Extract water molecule positions from molecule_index
    water_positions = []
    water_atom_names = []
    
    for mol in structure.molecule_index:
        if mol.mol_type == "water":
            # Get positions for this molecule
            start = mol.start_idx
            end = start + mol.count
            water_positions.append(structure.positions[start:end])
            water_atom_names.extend(structure.atom_names[start:end])
    
    if not water_positions:
        # No water molecules - return empty hidden actor
        mapper = vtkMoleculeMapper()
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.VisibilityOff()
        return actor
    
    # Concatenate all water positions
    all_water_positions = np.vstack(water_positions)
    
    # Build vtkMolecule for water
    molecule = _build_vtk_molecule(all_water_positions, water_atom_names)
    
    # Create mapper with line-only rendering
    mapper = vtkMoleculeMapper()
    mapper.SetInputData(molecule)
    mapper.SetRenderAtoms(False)  # Don't render atom spheres
    mapper.SetRenderBonds(True)    # Render bonds as lines
    
    # Set a neutral color for water bonds (blue-tinted, RGB 0-255)
    mapper.SetBondColor(127, 178, 255)  # Light blue
    
    # Create actor
    actor = vtkActor()
    actor.SetMapper(mapper)
    
    return actor


def create_guest_actor(structure) -> vtkActor:
    """Create a ball-and-stick actor for guest molecules.
    
    Guest molecules (CH4, THF, CO2, H2) are rendered with full ball-and-stick
    style using CPK coloring.
    
    Args:
        structure: HydrateStructure with molecule_index containing guest molecules
    
    Returns:
        vtkActor with guest molecules rendered as ball-and-stick
    """
    # Extract guest molecule positions (mol_type != "water")
    guest_positions = []
    guest_atom_names = []
    
    for mol in structure.molecule_index:
        if mol.mol_type != "water":
            # Get positions for this guest molecule
            start = mol.start_idx
            end = start + mol.count
            guest_positions.append(structure.positions[start:end])
            guest_atom_names.extend(structure.atom_names[start:end])
    
    if not guest_positions:
        # No guest molecules - return empty hidden actor
        mapper = vtkMoleculeMapper()
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.VisibilityOff()
        return actor
    
    # Concatenate all guest positions
    all_guest_positions = np.vstack(guest_positions)
    
    # Build vtkMolecule for guests
    molecule = _build_vtk_molecule(all_guest_positions, guest_atom_names)
    
    # Create mapper with ball-and-stick rendering
    mapper = vtkMoleculeMapper()
    mapper.SetInputData(molecule)
    mapper.SetRenderAtoms(True)   # Render atom spheres
    mapper.SetRenderBonds(True)   # Render bonds as cylinders
    mapper.UseBallAndStickSettings()
    
    # Set custom bond color for visibility (RGB 0-255)
    mapper.SetBondColor(180, 180, 180)  # Gray bonds
    
    # Create actor
    actor = vtkActor()
    actor.SetMapper(mapper)
    
    return actor


def render_hydrate_structure(structure) -> list[vtkActor]:
    """Render a hydrate structure with dual-style visualization.
    
    Creates VTK actors for:
    - Water framework: rendered as lines/bonds only
    - Guest molecules: rendered as ball-and-stick with CPK colors
    
    Args:
        structure: HydrateStructure with water framework and guest molecules
    
    Returns:
        List of vtkActor objects [water_actor, guest_actor]
    """
    # Create water framework actor (lines)
    water_actor = create_water_framework_actor(structure)
    
    # Create guest molecules actor (ball-and-stick)
    guest_actor = create_guest_actor(structure)
    
    return [water_actor, guest_actor]


def add_hydrate_actors_to_viewer(viewer, structure) -> list[vtkActor]:
    """Add hydrate actors to a viewer panel.
    
    Args:
        viewer: A ViewerPanel or similar viewer object with addActor method
        structure: HydrateStructure to render
    
    Returns:
        List of created vtkActor objects [water_actor, guest_actor]
    """
    actors = render_hydrate_structure(structure)
    
    # Add each actor to the viewer
    for actor in actors:
        viewer.addActor(actor)
    
    return actors


def remove_hydrate_actors_from_viewer(viewer, actors: list[vtkActor]) -> None:
    """Remove hydrate actors from a viewer.
    
    Args:
        viewer: A ViewerPanel or similar viewer object with removeActor method
        actors: List of vtkActor objects to remove
    """
    for actor in actors:
        viewer.removeActor(actor)


def toggle_hydrate_visibility(
    water_actor: vtkActor,
    guest_actor: vtkActor,
    water_visible: bool = True,
    guest_visible: bool = True
) -> None:
    """Toggle visibility of hydrate components.
    
    Args:
        water_actor: Actor for water framework
        guest_actor: Actor for guest molecules
        water_visible: True to show water framework
        guest_visible: True to show guest molecules
    """
    water_actor.SetVisibility(water_visible)
    guest_actor.SetVisibility(guest_visible)
