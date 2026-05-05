"""Solute rendering module for 3D visualization of solute molecules.

This module provides functions to create VTK actors for rendering solute molecules
with ball-and-stick style:
- THF (tetrahydrofuran): C4H8O molecule
- CH4 (methane): Simple hydrocarbon

All coordinates are in nanometers (nm).

The renderer follows the same pattern as hydrate_renderer.py:
- CPK colors for C (gray), O (red), H (white)
- Automatic bond detection at 0.16 nm threshold
- Ball-and-stick representation by default
- MW virtual sites are skipped during rendering
"""

import logging
import numpy as np
from vtkmodules.all import (
    vtkMoleculeMapper,
    vtkMolecule,
    vtkActor,
    vtkMatrix3x3,
)

logger = logging.getLogger(__name__)

# Unit conversion: VTK periodic table provides radii in Angstroms (Å),
# but QuickIce positions are in nanometers (nm).
# Multiply all radius scale factors by this to convert Å → nm.
ANGSTROM_TO_NM = 0.1


# CPK coloring for common elements (RGB values in [0, 1])
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
BOND_DISTANCE_THRESHOLD = 0.16  # nm


def get_element_from_atom_name(atom_name: str) -> str | None:
    """Extract element symbol from atom name.
    
    Args:
        atom_name: Atom name like 'C1', 'O2', 'H3', 'MW'
        
    Returns:
        Element symbol like 'C', 'O', 'H', or None for MW/unknown
    """
    # Strip numbers and whitespace
    element = atom_name.strip('0123456789').strip()
    
    # Map common variations
    if element in ('C', 'CA', 'CB', 'CG', 'CD', 'CE', 'CZ'):
        return 'C'
    elif element in ('O', 'OA', 'OB', 'OG', 'OD', 'OE', 'OH'):
        return 'O'
    elif element in ('H', 'HA', 'HB', 'HG', 'HD', 'HE', 'HZ'):
        return 'H'
    elif element == 'MW':
        return None  # Virtual site, skip
    
    return element if len(element) <= 2 else None


def create_solute_actor(
    positions: np.ndarray,
    atom_names: list[str],
    cell: np.ndarray,
    mode: str = "ball_and_stick"
) -> vtkActor | None:
    """Create VTK actor for solute molecules with ball-and-stick rendering.
    
    Args:
        positions: (N_atoms, 3) positions in nm
        atom_names: List of atom names (C, O, H, etc.)
        cell: (3, 3) unit cell vectors in nm
        mode: Rendering mode ("vdw", "ball_and_stick", "stick")
        
    Returns:
        vtkActor with solute molecules rendered, or None if no valid atoms
    """
    molecule = vtkMolecule()
    
    # Add atoms (skip MW virtual sites)
    atom_ids = []
    for pos, name in zip(positions, atom_names):
        element = get_element_from_atom_name(name)
        if element is None:
            continue
        
        # Get atomic number (simplified mapping)
        atomic_number = ELEMENT_TO_ATOMIC_NUMBER.get(element, 6)
        atom_id = molecule.AppendAtom(
            atomic_number,
            float(pos[0]), float(pos[1]), float(pos[2])
        )
        atom_ids.append(atom_id)
    
    if not atom_ids:
        logger.warning("No valid atoms for solute rendering")
        return None
    
    # Detect bonds automatically
    visible_positions = positions[:len(atom_ids)]
    for i in range(len(atom_ids)):
        for j in range(i + 1, len(atom_ids)):
            dist = np.linalg.norm(visible_positions[i] - visible_positions[j])
            if dist < BOND_DISTANCE_THRESHOLD:
                molecule.AppendBond(atom_ids[i], atom_ids[j], 1)
    
    # Set lattice for PBC
    lattice_matrix = vtkMatrix3x3()
    cell_transposed = cell.T
    for i in range(3):
        for j in range(3):
            lattice_matrix.SetElement(i, j, float(cell_transposed[i, j]))
    molecule.SetLattice(lattice_matrix)
    
    # Create mapper
    mapper = vtkMoleculeMapper()
    mapper.SetInputData(molecule)
    
    if mode == "ball_and_stick":
        mapper.UseBallAndStickSettings()
        mapper.SetAtomicRadiusTypeToVDWRadius()
        mapper.SetAtomicRadiusScaleFactor(0.25 * ANGSTROM_TO_NM)  # 0.025 nm
        mapper.SetBondRadius(0.075 * ANGSTROM_TO_NM)  # 0.0075 nm
    elif mode == "vdw":
        mapper.UseVDWSpheresSettings()
        mapper.SetAtomicRadiusTypeToVDWRadius()
        mapper.SetAtomicRadiusScaleFactor(0.8 * ANGSTROM_TO_NM)  # 0.08 nm
        mapper.SetBondRadius(0.075 * ANGSTROM_TO_NM)  # 0.0075 nm
    else:  # stick
        mapper.UseLiquoriceStickSettings()
        mapper.SetAtomicRadiusTypeToUnitRadius()
        mapper.SetAtomicRadiusScaleFactor(0.15 * ANGSTROM_TO_NM)  # 0.015 nm
        mapper.SetBondRadius(0.15 * ANGSTROM_TO_NM)  # 0.015 nm
    
    mapper.SetRenderAtoms(True)
    mapper.SetRenderBonds(True)
    mapper.SetBondColor(180, 180, 180)  # Gray bonds
    
    actor = vtkActor()
    actor.SetMapper(mapper)
    
    return actor
