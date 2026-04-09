"""VTK utility functions for molecular visualization.

This module provides conversion utilities to transform QuickIce data structures
into VTK objects for 3D rendering, along with actor creation functions for
hydrogen bonds and unit cell visualization.
"""

import numpy as np
from vtkmodules.all import (
    vtkMolecule,
    vtkActor,
    vtkPolyData,
    vtkPoints,
    vtkCellArray,
    vtkPolyDataMapper,
    vtkOutlineSource,
    vtkMatrix3x3,
)

from quickice.structure_generation.types import Candidate, InterfaceStructure


def candidate_to_vtk_molecule(candidate: Candidate) -> vtkMolecule:
    """Convert a QuickIce Candidate to a VTK molecule for visualization.
    
    This function creates a vtkMolecule from the Candidate's atomic positions,
    establishing the molecular structure with proper atom types and bonds.
    
    Args:
        candidate: A QuickIce Candidate containing positions, atom_names, 
                   cell matrix, and nmolecules.
    
    Returns:
        A vtkMolecule object with atoms and bonds properly configured.
    
    Note:
        Positions are in nanometers (nm), which is QuickIce's internal unit.
        VTK accepts positions in any consistent unit - nm is maintained.
    """
    mol = vtkMolecule()
    
    # CRITICAL: Initialize before adding atoms (VTK requirement)
    mol.Initialize()
    
    # Map atom names to atomic numbers
    # Support both TIP3P (O, H) and TIP4P (OW, HW1, HW2, MW) naming
    # MW is a massless virtual site (atomic number 0), skip it for visualization
    atomic_numbers = {
        "O": 8, "H": 1,  # TIP3P
        "OW": 8, "HW1": 1, "HW2": 1,  # TIP4P real atoms
        "MW": None,  # TIP4P virtual site - skip
    }
    
    # Add atoms (skip virtual sites like MW)
    atom_indices = []
    for i, (name, pos) in enumerate(zip(candidate.atom_names, candidate.positions)):
        atomic_num = atomic_numbers.get(name)
        if atomic_num is None:
            continue  # Skip virtual sites
        idx = mol.AppendAtom(atomic_num, pos[0], pos[1], pos[2])
        atom_indices.append(idx)
    
    # Add O-H bonds for each water molecule
    # TIP4P has MW (virtual site) which we skip, so atom_indices contains
    # only visible atoms: [OW, HW1, HW2, OW, HW1, HW2, ...] = 3 per water
    # TIP3P is [O, H, H, O, H, H, ...] = 3 per water
    # Either way, we have 3 visible atoms per water molecule
    num_water_molecules = candidate.nmolecules
    for mol_idx in range(num_water_molecules):
        # Each water has 3 visible atoms (O + 2H), regardless of TIP3P/TIP4P
        # atom_indices contains only visible atoms in order
        o_idx = atom_indices[mol_idx * 3]
        h1_idx = atom_indices[mol_idx * 3 + 1]
        h2_idx = atom_indices[mol_idx * 3 + 2]
        # Single bond (bond order 1) for both O-H bonds
        mol.AppendBond(o_idx, h1_idx, 1)
        mol.AppendBond(o_idx, h2_idx, 1)
    
    # Set unit cell lattice from the (3, 3) cell matrix
    # VTK expects a vtkMatrix3x3 with lattice vectors as COLUMNS
    # Our candidate.cell has vectors as ROWS, so we need to transpose
    lattice_matrix = vtkMatrix3x3()
    cell_transposed = candidate.cell.T  # Transpose: rows -> columns
    for i in range(3):
        for j in range(3):
            lattice_matrix.SetElement(i, j, float(cell_transposed[i, j]))
    mol.SetLattice(lattice_matrix)
    
    return mol


def detect_hydrogen_bonds(
    candidate: Candidate, max_distance: float = 0.25
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    """Detect hydrogen bonds from molecular geometry.
    
    Identifies H-bonds by finding hydrogen atoms that are close to oxygen atoms
    from other water molecules. A hydrogen bond is assumed when the H...O 
    distance is less than the threshold.
    
    Args:
        candidate: A QuickIce Candidate containing atomic positions and metadata.
        max_distance: Maximum H...O distance threshold in nanometers.
                      Default 0.25 nm (2.5 Å) is typical for H-bonds.
    
    Returns:
        List of (H_position, O_position) tuples for each detected H-bond.
        Each position is a (x, y, z) tuple in nanometers.
    
    Note:
        Water molecules follow the pattern [O, H, H, O, H, H, ...] where:
        - Oxygen atoms are at indices 0, 3, 6, 9, ... (every 3rd starting at 0)
        - Hydrogen atoms are at indices 1, 2, 4, 5, 7, 8, ...
        - Each O has two bonded H atoms: O[i] bonded to H[i+1] and H[i+2]
    """
    positions = candidate.positions
    nmolecules = candidate.nmolecules
    
    # Collect O and H atom positions with their indices
    # O atoms: indices 0, 3, 6, ... (every 3rd atom starting at 0)
    # H atoms: indices 1, 2, 4, 5, 7, 8, ... (remaining atoms)
    o_positions = []  # [(index, position), ...]
    h_positions = []  # [(index, position, parent_O_index), ...]
    
    for mol_idx in range(nmolecules):
        # O atom index for this molecule
        o_idx = mol_idx * 3
        o_positions.append((o_idx, positions[o_idx]))
        
        # H atoms for this molecule
        h1_idx = mol_idx * 3 + 1
        h2_idx = mol_idx * 3 + 2
        h_positions.append((h1_idx, positions[h1_idx], o_idx))
        h_positions.append((h2_idx, positions[h2_idx], o_idx))
    
    # Detect H-bonds
    hbonds = []
    
    for h_idx, h_pos, parent_o_idx in h_positions:
        # Find O atoms that could form H-bonds with this H
        for o_idx, o_pos in o_positions:
            # Skip the parent O (same molecule, covalently bonded)
            if o_idx == parent_o_idx:
                continue
            
            # Calculate H...O distance
            distance = np.linalg.norm(h_pos - o_pos)
            
            if distance < max_distance:
                # H-bond detected: H...O
                hbonds.append((
                    tuple(float(h_pos[i]) for i in range(3)),
                    tuple(float(o_pos[i]) for i in range(3))
                ))
    
    return hbonds


def create_hbond_actor(
    hbond_pairs: list[tuple[tuple[float, float, float], tuple[float, float, float]]]
) -> vtkActor:
    """Create a VTK actor for hydrogen bond visualization as dashed lines.
    
    Builds a vtkPolyData object with line segments for each H-bond and
    creates manual dashed lines by splitting each H-bond into short segments.
    This workaround is needed because VTK's OpenGL2 backend does not support
    SetLineStipplePattern (only legacy OpenGL).
    
    Args:
        hbond_pairs: List of (point1, point2) tuples where each point is 
                     (x, y, z) coordinates in nanometers.
    
    Returns:
        A vtkActor configured with cyan color and dashed line styling.
    
    Note:
        Uses manual dash creation by splitting each line into segments.
        Dash pattern: 8 segments with alternating on/off (dash length ~0.01 nm).
    """
    # Create points and line cells
    points = vtkPoints()
    lines = vtkCellArray()
    
    # Dash parameters
    num_dashes = 8  # Number of dash segments per line
    dash_ratio = 0.5  # Fraction of each segment that is visible (dash length)
    
    for p1, p2 in hbond_pairs:
        # Create dashed line by splitting into segments
        p1_arr = np.array(p1)
        p2_arr = np.array(p2)
        direction = p2_arr - p1_arr
        
        for i in range(num_dashes):
            # Calculate start and end of this dash segment
            t_start = i / num_dashes
            t_end = (i + dash_ratio) / num_dashes
            
            # Only draw if this is a "dash" (not a gap)
            if i % 2 == 0:
                dash_start = p1_arr + direction * t_start
                dash_end = p1_arr + direction * t_end
                
                # Insert the two endpoints
                id1 = points.InsertNextPoint(dash_start[0], dash_start[1], dash_start[2])
                id2 = points.InsertNextPoint(dash_end[0], dash_end[1], dash_end[2])
                
                # Create a line cell connecting the two points
                lines.InsertNextCell(2)
                lines.InsertCellPoint(id1)
                lines.InsertCellPoint(id2)
    
    # Build the polydata
    polydata = vtkPolyData()
    polydata.SetPoints(points)
    polydata.SetLines(lines)
    
    # Create mapper
    mapper = vtkPolyDataMapper()
    mapper.SetInputData(polydata)
    
    # Create actor
    actor = vtkActor()
    actor.SetMapper(mapper)
    
    # Set visual properties: cyan color for distinction from regular bonds
    actor.GetProperty().SetColor(0.0, 0.8, 0.8)  # Cyan color
    actor.GetProperty().SetLineWidth(1.5)
    
    return actor


def create_unit_cell_actor(cell: np.ndarray) -> vtkActor:
    """Create a wireframe box actor for the simulation unit cell.
    
    Creates a vtkOutlineSource-based actor that renders the unit cell
    boundaries as a non-intrusive wireframe box.
    
    Args:
        cell: (3, 3) numpy array of cell vectors [a, b, c] in nanometers.
              Each row is a lattice vector.
    
    Returns:
        A vtkActor configured with subtle gray color and thin lines.
    
    Note:
        For orthogonal cells (typical of ice structures), the bounds are
        calculated directly from the diagonal components. Non-orthogonal
        cells would require a transform, but ice structures are typically
        close to orthogonal.
    """
    # Calculate cell dimensions (length of each lattice vector)
    # For orthogonal cells, these are simply the box dimensions
    a_len = np.linalg.norm(cell[0])
    b_len = np.linalg.norm(cell[1])
    c_len = np.linalg.norm(cell[2])
    
    # Create outline source (wireframe box from origin)
    outline = vtkOutlineSource()
    outline.SetBounds(0.0, a_len, 0.0, b_len, 0.0, c_len)
    
    # Create mapper
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(outline.GetOutputPort())
    
    # Create actor
    actor = vtkActor()
    actor.SetMapper(mapper)
    
    # Set visual properties per CONTEXT.md ("subtle gray")
    actor.GetProperty().SetColor(0.5, 0.5, 0.5)  # Subtle gray
    actor.GetProperty().SetLineWidth(1.0)
    
    return actor


def interface_to_vtk_molecules(iface: InterfaceStructure) -> tuple[vtkMolecule, vtkMolecule]:
    """Convert an InterfaceStructure into separate ice and water VTK molecules.
    
    Splits the combined interface structure into two vtkMolecule objects for
    phase-distinct visualization: one for ice atoms (cyan) and one for water
    atoms (cornflower blue).
    
    Args:
        iface: An InterfaceStructure containing combined ice + water atoms.
               Ice atoms come first, followed by water atoms.
               ice_atom_count marks the boundary between phases.
    
    Returns:
        A tuple of (ice_mol, water_mol) where:
        - ice_mol: vtkMolecule with ice atoms (O, H, H pattern, 3 per molecule)
        - water_mol: vtkMolecule with water atoms (OW, HW1, HW2, MW pattern, 
                     but MW virtual sites are skipped, so 3 visible per molecule)
    
    Note:
        MW (massless virtual site) atoms are skipped during conversion as they
        are not visualized. Ice has 3 atoms per molecule (O, H, H) with no MW.
        Water has 4 atoms per molecule (OW, HW1, HW2, MW). The atom_names array
        contains ice atoms first (indices 0 to ice_atom_count-1) followed by
        water atoms (indices ice_atom_count onward). MW atoms only appear in the
        water region, so skipping them before the boundary check is safe.
    """
    ice_mol = vtkMolecule()
    water_mol = vtkMolecule()
    
    # CRITICAL: Initialize before adding atoms (VTK requirement)
    ice_mol.Initialize()
    water_mol.Initialize()
    
    # Map atom names to atomic numbers (same pattern as candidate_to_vtk_molecule)
    atomic_numbers = {
        "O": 8, "H": 1,  # Ice atoms (TIP3P-style)
        "OW": 8, "HW1": 1, "HW2": 1,  # Water atoms (TIP4P real atoms)
        "MW": None,  # TIP4P virtual site - skip
    }
    
    # Track indices in each molecule for bond creation
    ice_indices = []
    water_indices = []
    
    # Add atoms to appropriate molecule, skipping MW virtual sites
    for i, (name, pos) in enumerate(zip(iface.atom_names, iface.positions)):
        atomic_num = atomic_numbers.get(name)
        
        # Skip MW virtual sites (atomic_num is None)
        if atomic_num is None:
            continue
        
        # Check ice/water boundary using raw index i
        # Ice atoms: indices 0 to ice_atom_count-1 (no MW in ice)
        # Water atoms: indices ice_atom_count onward (MW skipped above)
        if i < iface.ice_atom_count:
            # Ice atom
            idx = ice_mol.AppendAtom(atomic_num, pos[0], pos[1], pos[2])
            ice_indices.append(idx)
        else:
            # Water atom
            idx = water_mol.AppendAtom(atomic_num, pos[0], pos[1], pos[2])
            water_indices.append(idx)
    
    # Add bonds for ice molecules
    # Ice uses 3 visible atoms per molecule (O, H, H) - no MW to skip
    for mol_idx in range(iface.ice_nmolecules):
        o_idx = ice_indices[mol_idx * 3]
        h1_idx = ice_indices[mol_idx * 3 + 1]
        h2_idx = ice_indices[mol_idx * 3 + 2]
        # Single bond (bond order 1) for both O-H bonds
        ice_mol.AppendBond(o_idx, h1_idx, 1)
        ice_mol.AppendBond(o_idx, h2_idx, 1)
    
    # Add bonds for water molecules
    # Water uses 4 atoms per molecule (OW, HW1, HW2, MW) but MW is skipped
    # So we have 3 visible atoms per molecule in water_indices
    for mol_idx in range(iface.water_nmolecules):
        o_idx = water_indices[mol_idx * 3]
        h1_idx = water_indices[mol_idx * 3 + 1]
        h2_idx = water_indices[mol_idx * 3 + 2]
        # Single bond (bond order 1) for both O-H bonds
        water_mol.AppendBond(o_idx, h1_idx, 1)
        water_mol.AppendBond(o_idx, h2_idx, 1)
    
    # Do NOT set lattice on either molecule (interface structures use create_unit_cell_actor instead)
    
    return ice_mol, water_mol


def create_bond_lines_actor(
    bond_pairs: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    color_rgb: tuple[float, float, float],
    line_width: float = 1.5
) -> vtkActor:
    """Create a VTK actor for rendering bonds as 2D lines (not 3D cylinders).
    
    Creates a vtkPolyData with line cells connecting bond pairs. This provides
    lightweight bond visualization compared to the vtkMoleculeMapper's 3D cylinders.
    
    Args:
        bond_pairs: List of ((x1, y1, z1), (x2, y2, z2)) tuples in nanometers.
        color_rgb: RGB color tuple (r, g, b) with values in [0, 1].
        line_width: Width of the lines in pixels. Default 1.5.
    
    Returns:
        A vtkActor configured with the specified color and line width.
    
    Note:
        Similar to create_hbond_actor but WITHOUT the dash splitting.
        Used for regular O-H bonds in the interface visualization.
    """
    # Create points and line cells
    points = vtkPoints()
    lines = vtkCellArray()
    
    for p1, p2 in bond_pairs:
        # Insert the two endpoints
        id1 = points.InsertNextPoint(p1[0], p1[1], p1[2])
        id2 = points.InsertNextPoint(p2[0], p2[1], p2[2])
        
        # Create a line cell connecting the two points
        lines.InsertNextCell(2)
        lines.InsertCellPoint(id1)
        lines.InsertCellPoint(id2)
    
    # Build the polydata
    polydata = vtkPolyData()
    polydata.SetPoints(points)
    polydata.SetLines(lines)
    
    # Create mapper
    mapper = vtkPolyDataMapper()
    mapper.SetInputData(polydata)
    
    # Create actor
    actor = vtkActor()
    actor.SetMapper(mapper)
    
    # Set visual properties
    actor.GetProperty().SetColor(*color_rgb)
    actor.GetProperty().SetLineWidth(line_width)
    
    return actor
