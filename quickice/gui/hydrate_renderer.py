"""Hydrate rendering module for 3D visualization of gas hydrate structures.

This module provides functions to create VTK actors for rendering hydrate structures
with distinct visual styles:
- Water framework: rendered as lines/bonds only (no atom spheres)
- Guest molecules: rendered as ball-and-stick with CPK colors

All coordinates are in nanometers (nm).

Radius Control:
- The renderer uses hardcoded radii that can be adjusted. Default values are
  chosen for optimal visibility of the hydrate structure (water framework
  as lines, guest molecules as ball-and-stick).
- For better visibility, the atomic radius scale factor can be increased.
"""

import numpy as np
from vtkmodules.all import (
    vtkMoleculeMapper,
    vtkMolecule,
    vtkActor,
)

# Unit conversion: VTK periodic table provides radii in Angstroms (Å),
# but QuickIce positions are in nanometers (nm).
# Multiply all radius scale factors by this to convert Å → nm.
ANGSTROM_TO_NM = 0.1

# Representation modes matching Tab 1's molecular_viewer.py
# These are the EXACT values from molecular_viewer.py for consistent rendering
def get_representation_settings(mode: str) -> dict:
    """Get radius settings for representation mode (matching molecular_viewer.py).
    
    Args:
        mode: One of "vdw", "ball_and_stick", or "stick"
    
    Returns:
        Dict with 'atomic_radius_scale' and 'bond_radius' keys (already in nm)
    """
    if mode == "vdw":
        return {
            'atomic_radius_scale': 0.8 * ANGSTROM_TO_NM,  # 0.08 nm
            'bond_radius': 0.075 * ANGSTROM_TO_NM,  # 0.0075 nm
        }
    elif mode == "ball_and_stick":
        return {
            'atomic_radius_scale': 0.25 * ANGSTROM_TO_NM,  # 0.025 nm
            'bond_radius': 0.075 * ANGSTROM_TO_NM,  # 0.0075 nm
        }
    else:  # stick
        return {
            'atomic_radius_scale': 0.15 * ANGSTROM_TO_NM,  # 0.015 nm
            'bond_radius': 0.15 * ANGSTROM_TO_NM,  # 0.015 nm
        }


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
# Covalent bonds: O-H ~0.10nm, C-H ~0.11nm, C-O (THF) ~0.143nm
# C-C (THF ring): ~0.151-0.153nm
# H-H within molecules: ~0.16-0.18nm (should NOT be bonded)
# Non-covalent: O-O in ice ~0.28nm, O-O in hydrate cages ~0.30nm
# Use 0.16nm threshold to capture all covalent bonds including C-C but NOT H-H
BOND_DISTANCE_THRESHOLD = 0.16  # nm (captures O-H, C-H, C-O, C-C bonds, excludes H-H)


def _get_element_from_atom_name(atom_name: str) -> str | None:
    """Extract element symbol from atom name.
    
    Args:
        atom_name: Atom name (e.g., "OW", "HW1", "C", "NA", "MW")
    
    Returns:
        Element symbol (e.g., "O", "H", "C", "N"), or None to skip the atom
    """
    # Handle special cases for water
    if atom_name.startswith("OW"):
        return "O"
    if atom_name.startswith("HW"):
        return "H"
    if atom_name.startswith("MW"):
        return None  # Virtual site - skip this atom
    
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
    
    # Add atoms (skipping virtual sites like MW)
    atom_ids = []
    for pos, name in zip(positions, atom_names):
        element = _get_element_from_atom_name(name)
        if element is None:
            continue  # Skip virtual sites like MW
        # Get atomic number (default to Carbon=6 for unknown elements)
        atomic_number = ELEMENT_TO_ATOMIC_NUMBER.get(element, 6)
        atom_id = molecule.AppendAtom(atomic_number, float(pos[0]), float(pos[1]), float(pos[2]))
        atom_ids.append(atom_id)
    
    # Track which original positions have atoms for bond detection
    # (positions may have been filtered by skipping MW)
    visible_positions = [pos for pos, name in zip(positions, atom_names) 
                        if _get_element_from_atom_name(name) is not None]
    
    # Detect and add bonds based on distance
    n_atoms = len(visible_positions)
    for i in range(n_atoms):
        for j in range(i + 1, n_atoms):
            # Calculate distance
            dist = np.linalg.norm(visible_positions[i] - visible_positions[j])
            if dist < BOND_DISTANCE_THRESHOLD:
                molecule.AppendBond(atom_ids[i], atom_ids[j], 1)  # Single bond
    
    return molecule


def _build_vtk_molecule_from_molecule(
    mol_positions: np.ndarray,
    mol_atom_names: list[str]
) -> vtkMolecule:
    """Build a vtkMolecule for a SINGLE molecule with proper bond detection.
    
    This function applies distance threshold ONLY within a single molecule,
    preventing cross-molecule bonds.
    
    Args:
        mol_positions: (N_atoms, 3) positions for atoms in ONE molecule
        mol_atom_names: List of atom names for this molecule
    
    Returns:
        vtkMolecule with atoms and bonds
    """
    molecule = vtkMolecule()
    
    # Add atoms (skipping virtual sites like MW)
    atom_ids = []
    visible_positions = []
    for pos, name in zip(mol_positions, mol_atom_names):
        element = _get_element_from_atom_name(name)
        if element is None:
            continue  # Skip virtual sites like MW
        # Get atomic number (default to Carbon=6 for unknown elements)
        atomic_number = ELEMENT_TO_ATOMIC_NUMBER.get(element, 6)
        atom_id = molecule.AppendAtom(atomic_number, float(pos[0]), float(pos[1]), float(pos[2]))
        atom_ids.append(atom_id)
        visible_positions.append(pos)
    
    # Detect and add bonds based on distance WITHIN this molecule only
    n_atoms = len(atom_ids)
    for i in range(n_atoms):
        for j in range(i + 1, n_atoms):
            dist = np.linalg.norm(visible_positions[i] - visible_positions[j])
            if dist < BOND_DISTANCE_THRESHOLD:
                molecule.AppendBond(atom_ids[i], atom_ids[j], 1)  # Single bond
    
    return molecule


def create_water_framework_actor(structure, mode: str = "ball_and_stick") -> vtkActor:
    """Create an actor for the water framework with specified representation.
    
    The water framework can be rendered as bonds only (wireframe) or with
    ball-and-stick style matching Tab 1's representation modes.
    
    Args:
        structure: HydrateStructure with molecule_index containing water molecules
        mode: Representation mode - "vdw", "ball_and_stick", or "stick"
    
    Returns:
        vtkActor with water framework rendered in specified mode
    """
    # Extract water molecule positions from molecule_index
    water_molecules = []
    
    for mol in structure.molecule_index:
        if mol.mol_type == "water":
            # Get positions for this molecule
            start = mol.start_idx
            end = start + mol.count
            water_molecules.append({
                'positions': structure.positions[start:end],
                'atom_names': structure.atom_names[start:end]
            })
    
    if not water_molecules:
        # No water molecules - return empty hidden actor
        mapper = vtkMoleculeMapper()
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.VisibilityOff()
        return actor
    
    # Build ONE vtkMolecule from all water atoms, but only bond atoms within SAME molecule
    molecule = _build_vtk_molecule_from_molecule_index(
        water_molecules, structure.atom_names, structure.positions, structure.molecule_index
    )
    
    # Get representation settings (matching molecular_viewer.py)
    settings = get_representation_settings(mode)
    
    # Create mapper with specified rendering mode
    mapper = vtkMoleculeMapper()
    mapper.SetInputData(molecule)
    
    if mode == "vdw":
        mapper.UseVDWSpheresSettings()
        mapper.SetAtomicRadiusTypeToVDWRadius()
        mapper.SetRenderBonds(True)
    elif mode == "ball_and_stick":
        mapper.UseBallAndStickSettings()
        mapper.SetAtomicRadiusTypeToVDWRadius()
        mapper.SetRenderAtoms(True)
        mapper.SetRenderBonds(True)
    else:  # stick
        mapper.UseLiquoriceStickSettings()
        mapper.SetAtomicRadiusTypeToUnitRadius()
        mapper.SetRenderAtoms(True)
        mapper.SetRenderBonds(True)
    
    # Apply radius settings (matching Tab 1's molecular_viewer.py)
    mapper.SetAtomicRadiusScaleFactor(settings['atomic_radius_scale'])
    mapper.SetBondRadius(settings['bond_radius'])
    
    # Set a neutral color for water bonds (blue-tinted, RGB 0-255)
    mapper.SetBondColor(127, 178, 255)  # Light blue
    
    # Create actor
    actor = vtkActor()
    actor.SetMapper(mapper)
    
    return actor


def _build_vtk_molecule_from_molecule_index(
    molecules: list[dict],
    all_atom_names: list[str],
    all_positions: np.ndarray,
    molecule_index: list
) -> vtkMolecule:
    """Build ONE vtkMolecule from multiple molecules, bonding only within each molecule.
    
    This prevents cross-molecule bonds while still showing all atoms in one actor.
    
    Args:
        molecules: List of dicts with 'positions' and 'atom_names' for each molecule
        all_atom_names: All atom names from structure
        all_positions: All positions from structure
        molecule_index: List of MoleculeIndex entries
    
    Returns:
        Single vtkMolecule with correct intra-molecule bonds only
    """
    molecule = vtkMolecule()
    
    # Track which atoms belong to which molecule
    mol_atom_ids = []  # List of (molecule_idx, local_atom_ids, visible_positions)
    
    for mol_idx, mol in enumerate(molecule_index):
        if mol.mol_type != "water":
            continue
        
        # Get positions for this molecule
        start = mol.start_idx
        end = start + mol.count
        mol_positions = all_positions[start:end]
        mol_names = all_atom_names[start:end]
        
        # Add atoms for this molecule (skipping virtual sites like MW)
        atom_ids = []
        visible_positions = []
        for pos, name in zip(mol_positions, mol_names):
            element = _get_element_from_atom_name(name)
            if element is None:
                continue  # Skip virtual sites like MW
            atomic_number = ELEMENT_TO_ATOMIC_NUMBER.get(element, 6)
            atom_id = molecule.AppendAtom(atomic_number, float(pos[0]), float(pos[1]), float(pos[2]))
            atom_ids.append(atom_id)
            visible_positions.append(pos)
        
        if atom_ids:  # Only add if there are visible atoms
            mol_atom_ids.append((mol_idx, atom_ids, visible_positions))
    
    # Add bonds only within each molecule (not across molecules)
    for mol_idx, atom_ids, mol_positions in mol_atom_ids:
        n_atoms = len(atom_ids)
        for i in range(n_atoms):
            for j in range(i + 1, n_atoms):
                dist = np.linalg.norm(mol_positions[i] - mol_positions[j])
                if dist < BOND_DISTANCE_THRESHOLD:
                    molecule.AppendBond(atom_ids[i], atom_ids[j], 1)
    
    return molecule


def create_guest_actor(structure, mode: str = "ball_and_stick") -> vtkActor:
    """Create an actor for guest molecules with specified representation.
    
    Guest molecules (CH4, THF, CO2, H2) are rendered with the specified
    representation mode using CPK coloring (matching Tab 1).
    
    Args:
        structure: HydrateStructure with molecule_index containing guest molecules
        mode: Representation mode - "vdw", "ball_and_stick", or "stick"
    
    Returns:
        vtkActor with guest molecules rendered in specified mode
    """
    # Check if there are any guest molecules
    has_guest = any(mol.mol_type != "water" for mol in structure.molecule_index)
    
    if not has_guest:
        # No guest molecules - return empty hidden actor
        mapper = vtkMoleculeMapper()
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.VisibilityOff()
        return actor
    
    # Build ONE vtkMolecule from all guest atoms, but only bond atoms within SAME molecule
    # Use a similar approach to water - iterate through molecule_index for guests
    molecule = vtkMolecule()
    
    for mol in structure.molecule_index:
        if mol.mol_type == "water":
            continue  # Skip water, only process guests
        
        # Get positions for this guest molecule
        start = mol.start_idx
        end = start + mol.count
        mol_positions = structure.positions[start:end]
        mol_names = structure.atom_names[start:end]
        
        # Add atoms for this molecule (skipping virtual sites like MW)
        atom_ids = []
        visible_positions = []
        for pos, name in zip(mol_positions, mol_names):
            element = _get_element_from_atom_name(name)
            if element is None:
                continue  # Skip virtual sites like MW
            atomic_number = ELEMENT_TO_ATOMIC_NUMBER.get(element, 6)
            atom_id = molecule.AppendAtom(atomic_number, float(pos[0]), float(pos[1]), float(pos[2]))
            atom_ids.append(atom_id)
            visible_positions.append(pos)
        
        # Add bonds only within this guest molecule
        n_atoms = len(atom_ids)
        for i in range(n_atoms):
            for j in range(i + 1, n_atoms):
                dist = np.linalg.norm(visible_positions[i] - visible_positions[j])
                if dist < BOND_DISTANCE_THRESHOLD:
                    molecule.AppendBond(atom_ids[i], atom_ids[j], 1)
    
    # Get representation settings (matching molecular_viewer.py)
    settings = get_representation_settings(mode)
    
    # Create mapper with specified rendering mode
    mapper = vtkMoleculeMapper()
    mapper.SetInputData(molecule)
    mapper.SetRenderAtoms(True)   # Render atom spheres
    mapper.SetRenderBonds(True)   # Render bonds as cylinders
    
    if mode == "vdw":
        mapper.UseVDWSpheresSettings()
        mapper.SetAtomicRadiusTypeToVDWRadius()
    elif mode == "ball_and_stick":
        mapper.UseBallAndStickSettings()
        mapper.SetAtomicRadiusTypeToVDWRadius()
    else:  # stick
        mapper.UseLiquoriceStickSettings()
        mapper.SetAtomicRadiusTypeToUnitRadius()
    
    # Apply radius settings (matching Tab 1's molecular_viewer.py)
    mapper.SetAtomicRadiusScaleFactor(settings['atomic_radius_scale'])
    mapper.SetBondRadius(settings['bond_radius'])
    
    # Set custom bond color for visibility (RGB 0-255)
    mapper.SetBondColor(180, 180, 180)  # Gray bonds
    
    # Create actor
    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.SetScale(1.0, 1.0, 1.0)
    
    return actor


def render_hydrate_structure(structure, mode: str = "ball_and_stick") -> list[vtkActor]:
    """Render a hydrate structure with specified representation.
    
    Creates VTK actors for:
    - Water framework: rendered with specified mode
    - Guest molecules: rendered with specified mode (matching Tab 1)
    
    Args:
        structure: HydrateStructure with water framework and guest molecules
        mode: Representation mode - "vdw", "ball_and_stick", or "stick"
    
    Returns:
        List of vtkActor objects [water_actor, guest_actor]
    """
    # Create water framework actor (with specified mode)
    water_actor = create_water_framework_actor(structure, mode)
    
    # Create guest molecules actor (with specified mode)
    guest_actor = create_guest_actor(structure, mode)
    
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


def detect_hbonds_in_hydrate_structure(
    structure,
    max_distance: float = 0.25
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    """Detect hydrogen bonds in a HydrateStructure.
    
    Identifies H-bonds between water molecules by finding H atoms that are 
    close to O atoms from other water molecules.
    
    Args:
        structure: HydrateStructure with water molecules in molecule_index
        max_distance: Maximum H...O distance threshold in nanometers.
                      Default 0.25 nm (2.5 Å) is typical for H-bonds.
    
    Returns:
        List of (H_position, O_position) tuples for each detected H-bond.
        Each position is a (x, y, z) tuple in nanometers.
    """
    from quickice.gui.vtk_utils import _pbc_distance, _pbc_min_image_position
    
    hbonds = []
    
    # Collect O and H atom positions from water molecules
    o_positions = []  # [(index, position), ...]
    h_positions = []  # [(h_idx, h_position, parent_o_idx), ...]
    
    for mol in structure.molecule_index:
        if mol.mol_type != "water":
            continue
        
        start = mol.start_idx
        end = start + mol.count
        mol_positions = structure.positions[start:end]
        mol_names = structure.atom_names[start:end]
        
        # Find O and H atoms in this molecule
        for i, (pos, name) in enumerate(zip(mol_positions, mol_names)):
            if name.startswith("OW") or name == "O":
                o_positions.append((start + i, pos))
            elif name.startswith("HW") or name == "H":
                # Find the parent O (first O before this H in the molecule)
                parent_o_idx = None
                for j in range(i):
                    prev_name = mol_names[j]
                    if prev_name.startswith("OW") or prev_name == "O":
                        parent_o_idx = start + j
                        break
                if parent_o_idx is not None:
                    h_positions.append((start + i, pos, parent_o_idx))
    
    # Detect H-bonds
    cell = structure.cell
    for h_idx, h_pos, parent_o_idx in h_positions:
        for o_idx, o_pos in o_positions:
            # Skip the parent O (same molecule, covalently bonded)
            if o_idx == parent_o_idx:
                continue
            
            # Calculate H...O distance with PBC
            distance = _pbc_distance(h_pos, o_pos, cell)
            
            if distance < max_distance:
                # H-bond detected: H...O
                # Use minimum image position of O for correct visualization
                o_min_image = _pbc_min_image_position(h_pos, o_pos, cell)
                hbonds.append((
                    tuple(float(h_pos[i]) for i in range(3)),
                    tuple(float(o_min_image[i]) for i in range(3))
                ))
    
    return hbonds
