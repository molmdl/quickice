"""Test atom ordering validation in VTK bond creation."""

import numpy as np
import pytest
from quickice.structure_generation.types import Candidate
from quickice.gui.vtk_utils import candidate_to_vtk_molecule, detect_hydrogen_bonds


def test_tip3p_atom_ordering_validation():
    """Test that TIP3P atom ordering is validated before creating bonds."""
    # Valid TIP3P ordering
    positions = np.array([
        [0.0, 0.0, 0.0],   # O
        [0.1, 0.0, 0.0],   # H
        [-0.1, 0.0, 0.0],  # H
    ])
    atom_names = ["O", "H", "H"]
    cell = np.eye(3) * 2.0
    
    candidate = Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=1,
        phase_id="test",
        seed=42
    )
    
    # Should succeed
    mol = candidate_to_vtk_molecule(candidate)
    assert mol.GetNumberOfAtoms() == 3
    assert mol.GetNumberOfBonds() == 2


def test_tip4p_atom_ordering_validation():
    """Test that TIP4P atom ordering is validated before creating bonds."""
    # Valid TIP4P ordering (with MW virtual site)
    positions = np.array([
        [0.0, 0.0, 0.0],   # OW
        [0.1, 0.0, 0.0],   # HW1
        [-0.1, 0.0, 0.0],  # HW2
        [0.0, 0.0, 0.0],   # MW (virtual site, will be skipped)
    ])
    atom_names = ["OW", "HW1", "HW2", "MW"]
    cell = np.eye(3) * 2.0
    
    candidate = Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=1,
        phase_id="test",
        seed=42
    )
    
    # Should succeed - MW is skipped, only 3 visible atoms
    mol = candidate_to_vtk_molecule(candidate)
    assert mol.GetNumberOfAtoms() == 3  # MW skipped
    assert mol.GetNumberOfBonds() == 2


def test_invalid_atom_ordering_detected():
    """Test that invalid atom ordering raises ValueError."""
    # Invalid ordering: H, O, H (wrong order)
    positions = np.array([
        [0.0, 0.0, 0.0],   # H (wrong!)
        [0.1, 0.0, 0.0],   # O (wrong!)
        [-0.1, 0.0, 0.0],  # H (correct)
    ])
    atom_names = ["H", "O", "H"]  # Invalid ordering
    cell = np.eye(3) * 2.0
    
    candidate = Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=1,
        phase_id="test",
        seed=42
    )
    
    # Should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        candidate_to_vtk_molecule(candidate)
    
    assert "Invalid atom ordering" in str(exc_info.value)
    assert "molecule 0" in str(exc_info.value)


def test_hbond_detection_validates_atom_ordering():
    """Test that H-bond detection validates atom ordering."""
    # Invalid ordering: H, H, O (wrong order)
    positions = np.array([
        [0.0, 0.0, 0.0],   # H (wrong!)
        [0.1, 0.0, 0.0],   # H (wrong!)
        [-0.1, 0.0, 0.0],  # O (wrong!)
    ])
    atom_names = ["H", "H", "O"]  # Invalid ordering
    cell = np.eye(3) * 2.0
    
    candidate = Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=1,
        phase_id="test",
        seed=42
    )
    
    # Should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        detect_hydrogen_bonds(candidate)
    
    assert "Invalid atom ordering" in str(exc_info.value)


def test_mixed_atom_names_detected():
    """Test that mixed atom names (TIP3P + TIP4P) are detected."""
    # Mixed: OW, H, H (invalid - should be either O, H, H or OW, HW1, HW2)
    positions = np.array([
        [0.0, 0.0, 0.0],   # OW
        [0.1, 0.0, 0.0],   # H (should be HW1)
        [-0.1, 0.0, 0.0],  # H (should be HW2)
    ])
    atom_names = ["OW", "H", "H"]  # Invalid mix
    cell = np.eye(3) * 2.0
    
    candidate = Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=1,
        phase_id="test",
        seed=42
    )
    
    # Should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        candidate_to_vtk_molecule(candidate)
    
    assert "Invalid atom ordering" in str(exc_info.value)


def test_multiple_molecules_validation():
    """Test that validation works for multiple molecules."""
    # Valid TIP3P ordering for 2 molecules
    positions = np.array([
        [0.0, 0.0, 0.0],   # O1
        [0.1, 0.0, 0.0],   # H1 of mol 1
        [-0.1, 0.0, 0.0],  # H2 of mol 1
        [1.0, 0.0, 0.0],   # O2
        [1.1, 0.0, 0.0],   # H1 of mol 2
        [0.9, 0.0, 0.0],   # H2 of mol 2
    ])
    atom_names = ["O", "H", "H", "O", "H", "H"]
    cell = np.eye(3) * 2.0
    
    candidate = Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=2,
        phase_id="test",
        seed=42
    )
    
    # Should succeed
    mol = candidate_to_vtk_molecule(candidate)
    assert mol.GetNumberOfAtoms() == 6
    assert mol.GetNumberOfBonds() == 4  # 2 bonds per molecule


def test_multiple_molecules_invalid_ordering():
    """Test that invalid ordering in second molecule is detected."""
    # Invalid ordering in second molecule: O, H, H, H, O, H
    positions = np.array([
        [0.0, 0.0, 0.0],   # O1
        [0.1, 0.0, 0.0],   # H1 of mol 1
        [-0.1, 0.0, 0.0],  # H2 of mol 1
        [1.0, 0.0, 0.0],   # H (should be O!) - invalid
        [1.1, 0.0, 0.0],   # O (should be H!) - invalid
        [0.9, 0.0, 0.0],   # H
    ])
    atom_names = ["O", "H", "H", "H", "O", "H"]  # Second molecule invalid
    cell = np.eye(3) * 2.0
    
    candidate = Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=2,
        phase_id="test",
        seed=42
    )
    
    # Should raise ValueError for second molecule
    with pytest.raises(ValueError) as exc_info:
        candidate_to_vtk_molecule(candidate)
    
    assert "Invalid atom ordering" in str(exc_info.value)
    assert "molecule 1" in str(exc_info.value)  # Second molecule (0-indexed)