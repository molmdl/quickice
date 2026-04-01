"""VTK utility functions for molecular visualization.

This module provides conversion utilities to transform QuickIce data structures
into VTK objects for 3D rendering, along with actor creation functions for
hydrogen bonds and unit cell visualization.
"""

import numpy as np
from vtkmodules.all import vtkMolecule

from quickice.structure_generation.types import Candidate


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
    atomic_numbers = {"O": 8, "H": 1}
    
    # Add atoms
    atom_indices = []
    for i, (name, pos) in enumerate(zip(candidate.atom_names, candidate.positions)):
        atomic_num = atomic_numbers[name]
        idx = mol.AppendAtom(atomic_num, pos[0], pos[1], pos[2])
        atom_indices.append(idx)
    
    # Add O-H bonds: Water molecules have pattern [O, H, H, O, H, H, ...]
    # For each water molecule (indices i, i+1, i+2), add bonds from O to both H
    num_water_molecules = candidate.nmolecules
    for mol_idx in range(num_water_molecules):
        o_idx = atom_indices[mol_idx * 3]
        h1_idx = atom_indices[mol_idx * 3 + 1]
        h2_idx = atom_indices[mol_idx * 3 + 2]
        # Single bond (bond order 1) for both O-H bonds
        mol.AppendBond(o_idx, h1_idx, 1)
        mol.AppendBond(o_idx, h2_idx, 1)
    
    # Set unit cell lattice from the (3, 3) cell matrix
    # Flatten the matrix for VTK: [a0, a1, a2, b0, b1, b2, c0, c1, c2]
    mol.SetLattice(candidate.cell.flatten().tolist())
    
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
