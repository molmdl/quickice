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
