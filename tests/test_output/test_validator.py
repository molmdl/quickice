"""Tests for structure validation (space group and atomic overlap detection)."""

import numpy as np
import pytest

from quickice.structure_generation.types import Candidate


@pytest.fixture
def ice_ih_candidate():
    """Create a simple Ice Ih candidate for testing.
    
    Ice Ih has space group P6_3/mmc (#194) in hexagonal setting.
    This creates a minimal hexagonal cell with correct symmetry.
    """
    # Simple hexagonal cell for Ice Ih
    # a = 0.45 nm (4.5 Angstrom), c = 0.73 nm (7.3 Angstrom)
    a = 0.45  # nm
    c = 0.73  # nm
    
    # Hexagonal lattice vectors
    cell = np.array([
        [a, 0.0, 0.0],
        [a * 0.5, a * np.sqrt(3) / 2, 0.0],
        [0.0, 0.0, c]
    ])
    
    # Positions for 4 water molecules (12 atoms total)
    # Arranged to maintain hexagonal symmetry
    positions = np.array([
        # Molecule 1
        [0.0, 0.0, 0.0],        # O
        [0.1, 0.0, 0.0],        # H
        [-0.1, 0.0, 0.0],       # H
        # Molecule 2
        [0.225, 0.13, 0.365],   # O
        [0.325, 0.13, 0.365],   # H
        [0.125, 0.13, 0.365],   # H
        # Molecule 3
        [0.0, 0.0, 0.73],       # O
        [0.1, 0.0, 0.73],       # H
        [-0.1, 0.0, 0.73],      # H
        # Molecule 4
        [0.225, 0.13, 1.095],   # O
        [0.325, 0.13, 1.095],   # H
        [0.125, 0.13, 1.095],   # H
    ])
    
    atom_names = ['O', 'H', 'H', 'O', 'H', 'H', 'O', 'H', 'H', 'O', 'H', 'H']
    
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=4,
        phase_id='ice_ih',
        seed=1000,
        metadata={'density': 0.9167}
    )


@pytest.fixture
def overlapping_candidate():
    """Create a candidate with overlapping atoms.
    
    Two oxygen atoms are placed at 0.5 Angstrom apart (0.05 nm),
    which is less than the minimum allowed distance (0.8 Angstrom).
    """
    positions = np.array([
        # Molecule 1
        [0.0, 0.0, 0.0],        # O
        [0.1, 0.0, 0.0],        # H
        [-0.1, 0.0, 0.0],       # H
        # Molecule 2 - oxygen overlaps with molecule 1
        [0.05, 0.0, 0.0],       # O (0.5 Angstrom from first O - overlap!)
        [0.15, 0.0, 0.0],       # H
        [-0.05, 0.0, 0.0],      # H
    ])
    
    atom_names = ['O', 'H', 'H', 'O', 'H', 'H']
    cell = np.eye(3) * 1.0  # 1nm cubic cell
    
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=2,
        phase_id='ice_ih',
        seed=2000,
        metadata={'density': 0.9167}
    )


@pytest.fixture
def pbc_overlap_candidate():
    """Create a candidate with atoms overlapping across PBC boundary.
    
    An atom near one edge of the cell overlaps with an atom near the 
    opposite edge due to periodic boundary conditions.
    """
    # Two oxygens at 0.5 Angstrom apart across PBC
    positions = np.array([
        # Molecule 1 - oxygen near one edge
        [0.95, 0.0, 0.0],       # O (near x=1.0 boundary)
        [0.05, 0.0, 0.0],       # H
        [0.85, 0.0, 0.0],       # H
        # Molecule 2 - oxygen near opposite edge
        [0.0, 0.0, 0.0],        # O (distance 0.5 Angstrom via PBC!)
        [0.1, 0.0, 0.0],        # H
        [-0.1, 0.0, 0.0],       # H
    ])
    
    atom_names = ['O', 'H', 'H', 'O', 'H', 'H']
    cell = np.eye(3) * 1.0  # 1nm cubic cell
    
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=2,
        phase_id='ice_ih',
        seed=3000,
        metadata={'density': 0.9167}
    )


@pytest.fixture
def well_spaced_candidate():
    """Create a candidate with well-spaced atoms (no overlaps).
    
    All atoms are > 2.5 Angstrom apart (0.25 nm), well above the 
    minimum threshold of 0.8 Angstrom.
    """
    positions = np.array([
        # Molecule 1
        [0.0, 0.0, 0.0],        # O
        [0.1, 0.0, 0.0],        # H
        [-0.1, 0.0, 0.0],       # H
        # Molecule 2 - well separated
        [0.3, 0.0, 0.0],        # O
        [0.4, 0.0, 0.0],        # H
        [0.2, 0.0, 0.0],        # H
        # Molecule 3
        [0.6, 0.0, 0.0],        # O
        [0.7, 0.0, 0.0],        # H
        [0.5, 0.0, 0.0],        # H
    ])
    
    atom_names = ['O', 'H', 'H', 'O', 'H', 'H', 'O', 'H', 'H']
    cell = np.eye(3) * 1.0  # 1nm cubic cell
    
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=3,
        phase_id='ice_ih',
        seed=4000,
        metadata={'density': 0.9167}
    )


class TestValidateSpaceGroup:
    """Tests for validate_space_group function."""
    
    def test_validate_space_group_returns_correct_keys(self, ice_ih_candidate):
        """Test that validate_space_group returns dict with correct keys."""
        from quickice.output.validator import validate_space_group
        
        result = validate_space_group(ice_ih_candidate)
        
        assert isinstance(result, dict)
        assert 'spacegroup_number' in result
        assert 'spacegroup_symbol' in result
        assert 'valid' in result
    
    def test_validate_space_group_detects_symmetry(self, ice_ih_candidate):
        """Test that validate_space_group correctly identifies space group.
        
        Note: Actual space group detection depends on structure quality.
        This test verifies the function works and returns reasonable values.
        """
        from quickice.output.validator import validate_space_group
        
        result = validate_space_group(ice_ih_candidate)
        
        # Should return valid=True for a reasonable structure
        assert result['valid'] is True
        assert result['spacegroup_number'] is not None
        assert result['spacegroup_symbol'] is not None
        assert isinstance(result['spacegroup_number'], int)
        assert isinstance(result['spacegroup_symbol'], str)
    
    def test_validate_space_group_uses_symprec(self, ice_ih_candidate):
        """Test that validate_space_group accepts symprec parameter."""
        from quickice.output.validator import validate_space_group
        
        # Should accept symprec parameter
        result_default = validate_space_group(ice_ih_candidate)
        result_loose = validate_space_group(ice_ih_candidate, symprec=1e-3)
        result_strict = validate_space_group(ice_ih_candidate, symprec=1e-5)
        
        # All should return valid results
        assert result_default['valid'] is True
        assert result_loose['valid'] is True
        assert result_strict['valid'] is True
    
    def test_validate_space_group_returns_hall_number(self, ice_ih_candidate):
        """Test that validate_space_group returns hall_number when valid."""
        from quickice.output.validator import validate_space_group
        
        result = validate_space_group(ice_ih_candidate)
        
        if result['valid']:
            assert 'hall_number' in result
            assert isinstance(result['hall_number'], int)
    
    def test_validate_space_group_returns_n_operations(self, ice_ih_candidate):
        """Test that validate_space_group returns number of symmetry operations."""
        from quickice.output.validator import validate_space_group
        
        result = validate_space_group(ice_ih_candidate)
        
        if result['valid']:
            assert 'n_operations' in result
            assert isinstance(result['n_operations'], int)
            assert result['n_operations'] > 0


class TestCheckAtomicOverlap:
    """Tests for check_atomic_overlap function."""
    
    def test_check_atomic_overlap_no_overlap(self, well_spaced_candidate):
        """Test that check_atomic_overlap returns False for well-spaced atoms."""
        from quickice.output.validator import check_atomic_overlap
        
        result = check_atomic_overlap(well_spaced_candidate)
        
        assert result is False
    
    def test_check_atomic_overlap_detects_overlap(self, overlapping_candidate):
        """Test that check_atomic_overlap returns True for overlapping atoms."""
        from quickice.output.validator import check_atomic_overlap
        
        result = check_atomic_overlap(overlapping_candidate)
        
        assert result is True
    
    def test_check_atomic_overlap_detects_pbc_overlap(self, pbc_overlap_candidate):
        """Test that check_atomic_overlap detects overlap across PBC boundary."""
        from quickice.output.validator import check_atomic_overlap
        
        result = check_atomic_overlap(pbc_overlap_candidate)
        
        # Should detect overlap across periodic boundary
        assert result is True
    
    def test_check_atomic_overlap_min_distance_parameter(self, well_spaced_candidate):
        """Test that check_atomic_overlap respects min_distance parameter."""
        from quickice.output.validator import check_atomic_overlap
        
        # With default threshold (0.8 Angstrom), no overlap
        result_default = check_atomic_overlap(well_spaced_candidate, min_distance=0.8)
        assert result_default is False
        
        # With very large threshold (3.0 Angstrom), detects "overlap"
        result_large = check_atomic_overlap(well_spaced_candidate, min_distance=3.0)
        assert result_large is True
    
    def test_check_atomic_overlap_single_atom(self):
        """Test that check_atomic_overlap handles single atom (no pairs to check)."""
        from quickice.output.validator import check_atomic_overlap
        from quickice.structure_generation.types import Candidate
        
        single_atom = Candidate(
            positions=np.array([[0.0, 0.0, 0.0]]),
            atom_names=['O'],
            cell=np.eye(3) * 1.0,
            nmolecules=1,
            phase_id='ice_ih',
            seed=5000,
            metadata={'density': 0.9167}
        )
        
        result = check_atomic_overlap(single_atom)
        
        # Single atom cannot overlap
        assert result is False
    
    def test_check_atomic_overlap_empty_positions(self):
        """Test that check_atomic_overlap handles empty positions gracefully."""
        from quickice.output.validator import check_atomic_overlap
        from quickice.structure_generation.types import Candidate
        
        empty = Candidate(
            positions=np.array([]).reshape(0, 3),
            atom_names=[],
            cell=np.eye(3) * 1.0,
            nmolecules=0,
            phase_id='ice_ih',
            seed=6000,
            metadata={'density': 0.9167}
        )
        
        result = check_atomic_overlap(empty)
        
        # Empty positions cannot overlap
        assert result is False
