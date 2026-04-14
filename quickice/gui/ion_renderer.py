"""Ion rendering module for 3D visualization of Na+ and Cl- ions.

This module provides functions to create VTK actors for rendering Na+ and Cl- ions
as van der Waals (VDW) spheres in the 3D molecular viewer.

All coordinates are in nanometers (nm).
"""

import numpy as np
from vtkmodules.all import (
    vtkSphereSource,
    vtkPolyDataMapper,
    vtkActor,
)


# Ion van der Waals radii (in nm)
NA_VDW_RADIUS = 0.190  # 190 pm (1.90 Å)
CL_VDW_RADIUS = 0.181  # 181 pm (1.81 Å)

# Ion colors for visualization (RGB)
NA_COLOR = (1.0, 0.84, 0.0)  # Gold
CL_COLOR = (0.56, 0.99, 0.56)  # Lime green

# Ion opacity
ION_OPACITY = 0.9

# Store actor references for visibility toggling
_ion_actors: list[vtkActor] = []


def _create_vdw_sphere(
    center: tuple[float, float, float],
    radius: float,
    color_rgb: tuple[float, float, float],
    opacity: float = 1.0
) -> vtkActor:
    """Create a VDW sphere actor at the specified position.
    
    Args:
        center: (x, y, z) position in nanometers
        radius: VDW radius in nanometers
        color_rgb: RGB color tuple (r, g, b) with values in [0, 1]
        opacity: Opacity value in [0, 1]
    
    Returns:
        A vtkActor representing the VDW sphere
    """
    # Create sphere source
    sphere = vtkSphereSource()
    sphere.SetCenter(center[0], center[1], center[2])
    sphere.SetRadius(radius)
    sphere.SetThetaResolution(20)
    sphere.SetPhiResolution(20)
    
    # Create mapper
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(sphere.GetOutputPort())
    
    # Create actor
    actor = vtkActor()
    actor.SetMapper(mapper)
    
    # Set color and opacity
    actor.GetProperty().SetColor(*color_rgb)
    actor.GetProperty().SetOpacity(opacity)
    
    return actor


def create_na_actor(positions: np.ndarray) -> vtkActor:
    """Create a VDW sphere actor for Na+ ions.
    
    Creates a single actor containing all Na+ positions as VDW spheres.
    
    Args:
        positions: (N_na, 3) numpy array of Na+ positions in nm
    
    Returns:
        A vtkActor with all Na+ ions rendered as gold VDW spheres
    """
    if len(positions) == 0:
        # Return an empty actor (hidden)
        sphere = vtkSphereSource()
        sphere.SetRadius(0)
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.VisibilityOff()
        return actor
    
    # Create actor that holds all spheres - use first position as placeholder
    # We'll add multiple spheres by using a glyph approach
    # For simplicity, create multiple actors and group them in a list
    actors = []
    for pos in positions:
        actor = _create_vdw_sphere(
            center=(float(pos[0]), float(pos[1]), float(pos[2])),
            radius=NA_VDW_RADIUS,
            color_rgb=NA_COLOR,
            opacity=ION_OPACITY
        )
        actors.append(actor)
    
    # Store for reference (but we'll return the combined view)
    global _ion_actors
    _ion_actors.extend(actors)
    
    # Return a collection-like by returning a parent actor
    # For VTK, we'll return a single actor that aggregates all
    # Actually, simpler: return the first actor and add others via render
    # Let's return a list through a different approach - create a parent
    
    # Simpler approach: just return the actors as a list via the render function
    # This actor can be None since we'll use multi-actor approach
    sphere = vtkSphereSource()
    sphere.SetRadius(0)
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(sphere.GetOutputPort())
    placeholder = vtkActor()
    placeholder.SetMapper(mapper)
    placeholder.VisibilityOff()
    
    return placeholder


def create_cl_actor(positions: np.ndarray) -> vtkActor:
    """Create a VDW sphere actor for Cl- ions.
    
    Creates a single actor containing all Cl- positions as VDW spheres.
    
    Args:
        positions: (N_cl, 3) numpy array of Cl- positions in nm
    
    Returns:
        A vtkActor with all Cl- ions rendered as green VDW spheres
    """
    if len(positions) == 0:
        # Return an empty actor (hidden)
        sphere = vtkSphereSource()
        sphere.SetRadius(0)
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.VisibilityOff()
        return actor
    
    # Create sphere for each Cl- position
    actors = []
    for pos in positions:
        actor = _create_vdw_sphere(
            center=(float(pos[0]), float(pos[1]), float(pos[2])),
            radius=CL_VDW_RADIUS,
            color_rgb=CL_COLOR,
            opacity=ION_OPACITY
        )
        actors.append(actor)
    
    # Store for reference
    global _ion_actors
    _ion_actors.extend(actors)
    
    # Return placeholder
    sphere = vtkSphereSource()
    sphere.SetRadius(0)
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(sphere.GetOutputPort())
    placeholder = vtkActor()
    placeholder.SetMapper(mapper)
    placeholder.VisibilityOff()
    
    return placeholder


def render_ion_structure(ion_structure) -> list[vtkActor]:
    """Render Na+ and Cl- ions as VDW spheres from an IonStructure.
    
    Extracts Na+ and Cl- positions from the ion_structure and creates
    VTK actors for visualization.
    
    Args:
        ion_structure: An IonStructure object with positions, atom_names,
                       and molecule_index
    
    Returns:
        A list of vtkActor objects, one per ion
    """
    actors = []
    
    # Extract Na+ positions from the structure
    na_positions = []
    cl_positions = []
    
    for i, name in enumerate(ion_structure.atom_names):
        if name == "NA":
            na_positions.append(ion_structure.positions[i])
        elif name == "CL":
            cl_positions.append(ion_structure.positions[i])
    
    na_positions = np.array(na_positions) if na_positions else np.zeros((0, 3))
    cl_positions = np.array(cl_positions) if cl_positions else np.zeros((0, 3))
    
    # Create Na+ actors
    for pos in na_positions:
        actor = _create_vdw_sphere(
            center=(float(pos[0]), float(pos[1]), float(pos[2])),
            radius=NA_VDW_RADIUS,
            color_rgb=NA_COLOR,
            opacity=ION_OPACITY
        )
        actors.append(actor)
    
    # Create Cl- actors
    for pos in cl_positions:
        actor = _create_vdw_sphere(
            center=(float(pos[0]), float(pos[1]), float(pos[2])),
            radius=CL_VDW_RADIUS,
            color_rgb=CL_COLOR,
            opacity=ION_OPACITY
        )
        actors.append(actor)
    
    return actors


def add_ion_actors_to_viewer(viewer, ion_structure) -> list[vtkActor]:
    """Add ion actors to a viewer panel.
    
    Args:
        viewer: A ViewerPanel or similar viewer object with addActor method
        ion_structure: An IonStructure with ion positions
    
    Returns:
        List of created vtkActor objects
    """
    actors = render_ion_structure(ion_structure)
    
    # Add each actor to the viewer
    for actor in actors:
        viewer.addActor(actor)
    
    return actors


def remove_ion_actors_from_viewer(viewer, actors: list[vtkActor]) -> None:
    """Remove ion actors from a viewer.
    
    Args:
        viewer: A ViewerPanel or similar viewer object with removeActor method
        actors: List of vtkActor objects to remove
    """
    for actor in actors:
        viewer.removeActor(actor)


def toggle_ion_visibility(actors: list[vtkActor], visible: bool) -> None:
    """Toggle ion actors visibility.
    
    Args:
        actors: List of vtkActor objects
        visible: True to show, False to hide
    """
    for actor in actors:
        actor.SetVisibility(visible)