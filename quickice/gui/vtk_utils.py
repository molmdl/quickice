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
    
    # VERIFY: Build list of visible atom names (excluding MW virtual sites)
    # This matches what atom_indices contains
    visible_atom_names = [name for name in candidate.atom_names if name != "MW"]
    
    for mol_idx in range(num_water_molecules):
        # Each water has 3 visible atoms (O + 2H), regardless of TIP3P/TIP4P
        # atom_indices contains only visible atoms in order
        
        # VERIFY atom ordering before creating bonds
        # This catches upstream issues where atoms might not follow expected O, H, H pattern
        visible_names_per_mol = visible_atom_names[mol_idx * 3: mol_idx * 3 + 3]
        # For TIP3P: ["O", "H", "H"]
        # For TIP4P: ["OW", "HW1", "HW2"]
        expected_tip3p = ["O", "H", "H"]
        expected_tip4p = ["OW", "HW1", "HW2"]
        
        if visible_names_per_mol != expected_tip3p and visible_names_per_mol != expected_tip4p:
            raise ValueError(
                f"Invalid atom ordering for molecule {mol_idx}: expected {expected_tip3p} or {expected_tip4p}, "
                f"got {visible_names_per_mol}. "
                f"Bond creation requires atoms to be ordered as oxygen followed by two hydrogens."
            )
        
        o_idx = atom_indices[mol_idx * 3]
        h1_idx = atom_indices[mol_idx * 3 + 1]
        h2_idx = atom_indices[mol_idx * 3 + 2]
        # Single bond (bond order 1) for both O-H bonds
        mol.AppendBond(o_idx, h1_idx, 1)
        mol.AppendBond(o_idx, h2_idx, 1)
    
    # Set unit cell lattice from the (3, 3) cell matrix
    # 
    # CELL MATRIX ORIENTATION CONVENTIONS:
    # =====================================
    # - VTK uses COLUMN vectors: new_position = lattice_matrix @ position
    #   where lattice columns are the a, b, c vectors
    # - QuickIce uses ROW vectors: new_position = position @ cell_matrix
    #   where cell rows are the a, b, c vectors
    # 
    # The transpose converts between these conventions:
    #   (row_vectors)^T = column_vectors
    # 
    # For orthogonal cells (ice Ih), transpose has no effect since the
    # matrix is diagonal. For non-orthogonal cells (ice II, V), the
    # transpose is critical for correct lattice visualization.
    # 
    # See resolved debug session: unit-cell-mismatch.md
    lattice_matrix = vtkMatrix3x3()
    cell_transposed = candidate.cell.T  # Transpose: rows -> columns
    for i in range(3):
        for j in range(3):
            lattice_matrix.SetElement(i, j, float(cell_transposed[i, j]))
    mol.SetLattice(lattice_matrix)
    
    return mol


def _pbc_distance(pos1: np.ndarray, pos2: np.ndarray, cell: np.ndarray) -> float:
    """Calculate distance between two positions with periodic boundary conditions.
    
    Applies the minimum image convention to compute the shortest distance
    between two atoms across periodic box boundaries. Works for both
    orthorhombic (diagonal) and triclinic (non-orthogonal) cells.
    
    Args:
        pos1: (3,) array of first atom position in nm
        pos2: (3,) array of second atom position in nm
        cell: (3, 3) cell matrix where each row is a lattice vector in nm.
              For orthorhombic cells, this is diagonal. For triclinic cells,
              off-diagonal elements are non-zero.
    
    Returns:
        Distance in nanometers, accounting for periodic boundaries.
    
    Note:
        Uses the minimum image convention in fractional coordinate space.
        For triclinic cells, this correctly handles non-orthogonal periodic
        images by transforming to fractional coordinates before applying
        the minimum image convention.
    """
    # Compute displacement in Cartesian coordinates
    delta_cart = pos1 - pos2
    
    # Convert to fractional coordinates using inverse of cell matrix
    # This works for both orthorhombic and triclinic cells
    cell_inv = np.linalg.inv(cell)
    delta_frac = delta_cart @ cell_inv
    
    # Apply minimum image convention in fractional space
    # Wrap each component to [-0.5, 0.5]
    delta_frac = delta_frac - np.round(delta_frac)
    
    # Convert back to Cartesian coordinates
    delta_cart = delta_frac @ cell
    
    return np.linalg.norm(delta_cart)


def _pbc_min_image_position(ref_pos: np.ndarray, target_pos: np.ndarray, cell: np.ndarray) -> np.ndarray:
    """Get the minimum image position of target relative to reference position.
    
    Given a reference position (e.g., H atom), returns the periodic image of target_pos
    that is closest to ref_pos. This is needed for correct visualization of H-bonds
    that cross periodic boundaries.
    
    Args:
        ref_pos: (3,) array of reference position (e.g., H atom) in nm
        target_pos: (3,) array of target position (e.g., O atom) in nm
        cell: (3, 3) cell matrix in nm
    
    Returns:
        (3,) array of target_pos in the periodic image closest to ref_pos
    """
    # Compute displacement from ref to target
    delta_cart = target_pos - ref_pos
    
    # Convert to fractional coordinates
    cell_inv = np.linalg.inv(cell)
    delta_frac = delta_cart @ cell_inv
    
    # Apply minimum image convention in fractional space
    delta_frac = delta_frac - np.round(delta_frac)
    
    # Convert back to Cartesian coordinates
    delta_cart = delta_frac @ cell
    
    # Return the minimum image position of target
    return ref_pos + delta_cart


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
        
        Uses periodic boundary conditions (PBC) to correctly detect H-bonds
        that cross box boundaries.
    """
    positions = candidate.positions
    nmolecules = candidate.nmolecules
    atom_names = candidate.atom_names
    
    # VERIFY atom ordering before detecting H-bonds
    # This function expects atoms to be ordered as O, H, H for each molecule
    for mol_idx in range(nmolecules):
        mol_names = atom_names[mol_idx * 3: mol_idx * 3 + 3]
        # Accept both TIP3P (O, H, H) and TIP4P (OW, HW1, HW2) patterns
        # Note: TIP4P with MW virtual site should have MW already filtered out
        # before calling this function, as MW atoms are not stored in Candidate
        expected_tip3p = ["O", "H", "H"]
        expected_tip4p = ["OW", "HW1", "HW2"]
        
        if mol_names != expected_tip3p and mol_names != expected_tip4p:
            raise ValueError(
                f"Invalid atom ordering for molecule {mol_idx} in H-bond detection: "
                f"expected {expected_tip3p} or {expected_tip4p}, got {mol_names}. "
                f"H-bond detection requires atoms to be ordered as oxygen followed by two hydrogens."
            )
    
    # Get cell matrix for PBC distance calculation
    # This works for both orthorhombic (ice Ih) and triclinic (ice II, V) cells
    cell = candidate.cell
    
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
            
            # Calculate H...O distance with PBC (handles both orthorhombic and triclinic)
            distance = _pbc_distance(h_pos, o_pos, cell)
            
            if distance < max_distance:
                # H-bond detected: H...O
                # Use minimum image position of O for correct visualization
                # This ensures the line is drawn to the nearest periodic image of O
                o_min_image = _pbc_min_image_position(h_pos, o_pos, cell)
                hbonds.append((
                    tuple(float(h_pos[i]) for i in range(3)),
                    tuple(float(o_min_image[i]) for i in range(3))
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


def interface_to_vtk_molecules(iface: InterfaceStructure) -> tuple[vtkMolecule, vtkMolecule, vtkMolecule | None]:
    """Convert an InterfaceStructure into separate ice, water, and optionally guest VTK molecules.
    
    Splits the combined interface structure into vtkMolecule objects for
    phase-distinct visualization: one for ice atoms (cyan), one for water
    atoms (cornflower blue), and optionally one for guest molecules (gray).
    
    Args:
        iface: An InterfaceStructure containing combined ice + guests + water atoms.
               Ice atoms: indices 0 to ice_atom_count-1
               Guest atoms: indices ice_atom_count to ice_atom_count + guest_atom_count-1 (if guest_atom_count > 0)
               Water atoms: indices ice_atom_count + guest_atom_count onward
               ice_atom_count marks the boundary between ice and guests/water.
               guest_atom_count marks the boundary between guests and water.
    
    Returns:
        A tuple of (ice_mol, water_mol, guest_mol) where:
        - ice_mol: vtkMolecule with ice/water-framework atoms (O, H, H pattern OR OW, HW1, HW2 pattern)
        - water_mol: vtkMolecule with water atoms (OW, HW1, HW2, MW pattern, but MW virtual sites skipped)
        - guest_mol: vtkMolecule with guest atoms (Me, C, H, etc.), or None if no guests
    
    Note:
        MW (massless virtual site) atoms are skipped during conversion as they
        are not visualized.
        
        Atom arrangement in InterfaceStructure:
        - For classic ice interface: [ice] + [water]
        - For hydrate interface: [ice/hydrate water framework] + [guests] + [water box]
        
        The function detects hydrate ice by checking for "OW" in the ice atom names.
        For hydrate ice (4 atoms/mol: OW, HW1, HW2, MW), MW is skipped, so we have
        3 visible atoms per molecule for bonding.
    """
    ice_mol = vtkMolecule()
    water_mol = vtkMolecule()
    guest_mol = vtkMolecule() if iface.guest_atom_count > 0 else None
    
    # CRITICAL: Initialize before adding atoms (VTK requirement)
    ice_mol.Initialize()
    water_mol.Initialize()
    if guest_mol is not None:
        guest_mol.Initialize()
    
    # Map atom names to atomic numbers
    # Supports:
    # - Classic ice: O, H, H (3 atoms/mol)
    # - TIP4P/hydrate water: OW, HW1, HW2, MW (4 atoms/mol, MW skipped)
    # - Guests: various (Me, C, H, O, etc.)
    atomic_numbers = {
        "O": 8, "H": 1,  # Classic ice atoms
        "OW": 8, "HW1": 1, "HW2": 1,  # TIP4P water atoms (real)
        "MW": None,  # TIP4P virtual site - skip
    }
    
    # Additional atom types for guests
    guest_atomic_numbers = {
        "C": 6, "H": 1, "O": 8, "N": 7, "S": 16, "P": 15,
        "F": 9, "Cl": 17, "Br": 35, "I": 53,
        # United-atom methane
        "Me": 6,
    }
    
    # Track indices in each molecule for bond creation
    ice_indices = []
    water_indices = []
    guest_indices = []
    
    # Define boundaries:
    # ice_end = ice_atom_count (start of guests or water)
    # guest_end = ice_atom_count + guest_atom_count (start of water, only if guests exist)
    # If guest_atom_count > 0, guests are at indices [ice_atom_count, ice_atom_count + guest_atom_count)
    # If guest_atom_count == 0, water starts at ice_atom_count
    ice_end = iface.ice_atom_count
    guest_start = ice_end
    guest_end = ice_end + iface.guest_atom_count
    water_start = guest_end
    
    # Add atoms to appropriate molecule, skipping MW virtual sites
    for i, (name, pos) in enumerate(zip(iface.atom_names, iface.positions)):
        # Check which region this atom belongs to
        if i < ice_end:
            # Ice/water-framework atom
            atomic_num = atomic_numbers.get(name)
            if atomic_num is not None:  # Skip MW
                idx = ice_mol.AppendAtom(atomic_num, pos[0], pos[1], pos[2])
                ice_indices.append(idx)
        elif iface.guest_atom_count > 0 and guest_start <= i < guest_end:
            # Guest atom
            atomic_num = guest_atomic_numbers.get(name, 6)  # Default to carbon
            idx = guest_mol.AppendAtom(atomic_num, pos[0], pos[1], pos[2])
            guest_indices.append(idx)
        else:
            # Water atom (if not in guest range)
            atomic_num = atomic_numbers.get(name)
            if atomic_num is not None:  # Skip MW
                idx = water_mol.AppendAtom(atomic_num, pos[0], pos[1], pos[2])
                water_indices.append(idx)
    
    # Detect atoms per molecule in ice region
    # Classic ice: 3 atoms (O, H, H) - uses "O" (not "OW")
    # TIP4P/hydrate ice: 4 atoms (OW, HW1, HW2, MW) - uses "OW"
    ice_region_atom_names = iface.atom_names[:ice_end]
    has_ow_in_ice = "OW" in ice_region_atom_names
    has_mw_in_ice = "MW" in ice_region_atom_names
    atoms_per_ice_mol = 4 if (has_ow_in_ice or has_mw_in_ice) else 3
    
    # Number of ice molecules (may differ from original if guests were in ice count)
    # If ice_nmolecules + guest_nmolecules were combined, we need to separate them
    # Original ice molecules = ice positions / atoms_per_ice_mol
    actual_ice_nmolecules = ice_end // atoms_per_ice_mol
    # Guest molecules are in their own section (calculated separately)
    actual_guest_nmolecules = iface.guest_nmolecules if hasattr(iface, 'guest_nmolecules') else 0
    
    # Add bonds for ice molecules
    # Ice uses 3 visible atoms per molecule (O, H, H) after MW is skipped
    # For classic ice (uses "O"): validate exact ordering (O, H, H)
    # For TIP4P/hydrate ice (uses "OW"): atoms may be in any order after tiling/wrapping
    for mol_idx in range(actual_ice_nmolecules):
        # Get raw atom names for this molecule (for validation of classic ice)
        raw_start = mol_idx * atoms_per_ice_mol
        raw_end = raw_start + atoms_per_ice_mol
        
        if not has_ow_in_ice and not has_mw_in_ice:
            # Classic ice (uses "O"): validate exact ordering (O first, then H, H)
            if raw_end <= len(iface.atom_names):
                ice_names_per_mol = iface.atom_names[raw_start:raw_end]
                classic_ice = ["O", "H", "H"]
                if ice_names_per_mol != classic_ice:
                    raise ValueError(
                        f"Invalid ice atom ordering for molecule {mol_idx}: expected {classic_ice}, "
                        f"got {ice_names_per_mol}. "
                        f"Ice bond creation requires atoms to be ordered as oxygen followed by two hydrogens."
                    )
        
        # Verify we have 3 visible atoms (MW filtered out)
        mol_start = mol_idx * 3
        if mol_start + 3 > len(ice_indices):
            raise ValueError(
                f"Not enough visible atoms for ice molecule {mol_idx}: "
                f"need 3, have {len(ice_indices) - mol_start}"
            )
        
        o_idx = ice_indices[mol_start]
        h1_idx = ice_indices[mol_start + 1]
        h2_idx = ice_indices[mol_start + 2]
        # Single bond (bond order 1) for both O-H bonds
        ice_mol.AppendBond(o_idx, h1_idx, 1)
        ice_mol.AppendBond(o_idx, h2_idx, 1)
    
    # Add guest bonds (distance-based, within same molecule only)
    # Use molecule_index to correctly identify each guest molecule's boundaries
    # This is the same approach used in hydrate_renderer.py for guest molecules
    if guest_indices and iface.molecule_index:
        # Build mapping from global position index to guest_mol atom index
        # guest_mol contains atoms in order: guest_start, guest_start+1, ..., guest_end-1
        # (excluding any skipped atoms like MW, but guests don't have MW)
        # guest_indices[i] = i for simple cases
        
        # Iterate through molecule_index to find guest molecules
        for mol in iface.molecule_index:
            if mol.mol_type == "water":
                continue  # Skip water molecules
            
            # Get the global atom indices for this guest molecule
            mol_start_global = mol.start_idx
            mol_end_global = mol_start_global + mol.count
            
            # Convert global indices to guest_mol indices
            # guest_mol contains atoms from guest_start to guest_end
            # mol_start_global should be >= guest_start and < guest_end
            if mol_start_global < guest_start or mol_end_global > guest_end:
                continue  # This molecule is not in the guest range
            
            # Calculate guest_mol indices (relative to guest_start)
            mol_start = mol_start_global - guest_start
            mol_end = mol_end_global - guest_start
            
            # Add bonds within this molecule using distance detection
            for i in range(mol_start, mol_end):
                for j in range(i + 1, mol_end):
                    # Distance-based bond detection (threshold: 0.16 nm)
                    dist = np.linalg.norm(
                        np.array(iface.positions[guest_start + i]) - 
                        np.array(iface.positions[guest_start + j])
                    )
                    if dist < 0.16:  # Covalent bond threshold
                        guest_mol.AppendBond(guest_indices[i], guest_indices[j], 1)
    
    # Fallback for backward compatibility: if molecule_index is empty, use old method
    elif guest_indices and actual_guest_nmolecules > 0:
        guest_atom_names = iface.atom_names[guest_start:guest_end]
        
        # Group atoms by molecule (legacy method - may not work for complex guests)
        mol_start = 0
        for mol_idx in range(actual_guest_nmolecules):
            # Count atoms in this guest molecule
            guest_atoms = _count_guest_atoms_for_rendering(guest_atom_names, mol_start)
            mol_end = mol_start + guest_atoms
            
            # Add bonds within this molecule
            for i in range(mol_start, mol_end):
                for j in range(i + 1, mol_end):
                    # Distance-based bond detection (threshold: 0.16 nm)
                    dist = np.linalg.norm(
                        np.array(iface.positions[guest_start + i]) - 
                        np.array(iface.positions[guest_start + j])
                    )
                    if dist < 0.16:  # Covalent bond threshold
                        guest_mol.AppendBond(guest_indices[i], guest_indices[j], 1)
            
            mol_start = mol_end
    
    # Add bonds for water molecules
    # Water uses 4 atoms per molecule (OW, HW1, HW2, MW) but MW is skipped
    # So we have 3 visible atoms per molecule in water_indices
    for mol_idx in range(iface.water_nmolecules):
        # VERIFY atom ordering before creating bonds
        # water_indices has MW already filtered out, so we check the raw iface.atom_names
        # to verify the pattern before MW was skipped
        # Each water molecule has 4 atoms in iface: [OW, HW1, HW2, MW, OW, HW1, HW2, MW, ...]
        # Water starts at water_start (which is guest_end or ice_end)
        water_start_in_full = water_start + mol_idx * 4
        water_names_check = iface.atom_names[water_start_in_full: water_start_in_full + 4]
        if water_names_check != ["OW", "HW1", "HW2", "MW"]:
            raise ValueError(
                f"Invalid water atom ordering for molecule {mol_idx}: "
                f"expected ['OW', 'HW1', 'HW2', 'MW'], got {water_names_check}. "
                f"Water bond creation requires atoms to be ordered as OW, HW1, HW2, MW."
            )
        
        o_idx = water_indices[mol_idx * 3]
        h1_idx = water_indices[mol_idx * 3 + 1]
        h2_idx = water_indices[mol_idx * 3 + 2]
        # Single bond (bond order 1) for both O-H bonds
        water_mol.AppendBond(o_idx, h1_idx, 1)
        water_mol.AppendBond(o_idx, h2_idx, 1)
    
    # Do NOT set lattice on either molecule (interface structures use create_unit_cell_actor instead)
    
    return ice_mol, water_mol, guest_mol


def _count_guest_atoms_for_rendering(atom_names: list[str], start: int) -> int:
    """Count atoms in a guest molecule starting at index.
    
    Guest types:
    - Me: 1 atom (united-atom methane)
    - C: 5 atoms (all-atom methane: C + 4H)
    - For THF: starts with O (13 atoms, stops at next O or OW)
    
    Args:
        atom_names: List of atom names
        start: Starting index
    
    Returns:
        Number of atoms in this guest molecule
    """
    if start >= len(atom_names):
        return 0
    
    first_atom = atom_names[start]
    
    # United-atom methane (Me) - single carbon
    if first_atom == "Me":
        return 1
    
    # All-atom methane (C + 4H)
    if first_atom == "C":
        count = 0
        i = start
        while i < len(atom_names) and i < start + 5:
            count += 1
            i += 1
        return count
    
    # THF starts with O (oxygen)
    # THF has 13 atoms: O, CA, CA, CB, CB, + 8H
    # Next THF molecule starts with O, water starts with OW
    if first_atom == "O":
        count = 0
        i = start
        while i < len(atom_names) and i < start + 15:  # Max 15 atoms (generous for THF variants)
            count += 1
            i += 1
            # Stop if we hit another O (next THF) or OW (water)
            if i < len(atom_names) and atom_names[i] in ["O", "OW"]:
                break
        return count
    
    # H-first methane (H, H, H, H, C) from GenIce2 or H2 molecule
    if first_atom == "H":
        # Check next atoms to distinguish CH4 from H2
        sample_size = min(start + 6, len(atom_names))
        sample = atom_names[start:sample_size]
        c_count = sum(1 for a in sample if a == 'C')
        h_count = sum(1 for a in sample if a == 'H')
        
        # CH4 pattern: 4 H + 1 C = 5 atoms
        if h_count >= 4 and c_count >= 1:
            return 5
        
        # H2 pattern: 2 H atoms, no C
        if h_count >= 2 and c_count == 0:
            return 2
        
        # Single H atom (fallback)
        return 1
    
    # Default: treat as 1 atom guest
    return 1


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
