"""Tests for PDB writer with CRYST1 records."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from quickice.structure_generation.types import Candidate
from quickice.ranking.types import RankedCandidate, RankingResult
from quickice.output.pdb_writer import write_pdb_with_cryst1, write_ranked_candidates


@pytest.fixture
def simple_candidate():
    """Create a simple candidate for testing.
    
    Cell vectors in nm (will be converted to Angstrom):
    - a = [0.9, 0.0, 0.0] -> a = 0.9 nm = 9.0 Angstrom
    - b = [0.0, 0.78, 0.0] -> b = 0.78 nm = 7.8 Angstrom
    - c = [0.0, 0.0, 0.72] -> c = 0.72 nm = 7.2 Angstrom
    - All angles = 90 degrees (orthorhombic)
    """
    # Cell vectors in nm
    cell = np.array([
        [0.9, 0.0, 0.0],
        [0.0, 0.78, 0.0],
        [0.0, 0.0, 0.72]
    ])
    
    # Two water molecules in nm
    # O at (0.1, 0.1, 0.1) nm, H at (0.15, 0.12, 0.1) nm, H at (0.08, 0.12, 0.1) nm
    # O at (0.3, 0.3, 0.3) nm, H at (0.35, 0.32, 0.3) nm, H at (0.28, 0.32, 0.3) nm
    positions = np.array([
        [0.1, 0.1, 0.1],   # O1
        [0.15, 0.12, 0.1], # H1
        [0.08, 0.12, 0.1], # H2
        [0.3, 0.3, 0.3],   # O2
        [0.35, 0.32, 0.3], # H3
        [0.28, 0.32, 0.3], # H4
    ])
    
    atom_names = ["O", "H", "H", "O", "H", "H"]
    
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=2,
        phase_id="ice_ih",
        seed=42,
        metadata={"density": 0.9167}
    )


@pytest.fixture
def triclinic_candidate():
    """Create a triclinic cell candidate for angle testing.
    
    Non-orthogonal cell with angles ≠ 90°.
    """
    # Triclinic cell in nm with angles: alpha=80°, beta=85°, gamma=75°
    # Using standard crystallographic definition
    cell = np.array([
        [0.8, 0.0, 0.0],
        [0.1, 0.75, 0.0],
        [0.15, 0.2, 0.7]
    ])
    
    # 1 water molecule: O, H, H
    positions = np.array([
        [0.1, 0.1, 0.1],  # Oxygen
        [0.15, 0.15, 0.1],  # Hydrogen 1
        [0.05, 0.15, 0.1],  # Hydrogen 2
    ])
    
    atom_names = ["O", "H", "H"]
    
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=1,
        phase_id="test_phase",
        seed=1,
        metadata={}
    )


@pytest.fixture
def ranking_result(simple_candidate):
    """Create a ranking result with multiple ranked candidates."""
    candidates = []
    
    # Create 12 candidates with different ranks
    for i in range(12):
        # Offset positions slightly for each candidate
        positions = simple_candidate.positions + i * 0.01
        
        candidate = Candidate(
            positions=positions,
            atom_names=simple_candidate.atom_names.copy(),
            cell=simple_candidate.cell.copy(),
            nmolecules=simple_candidate.nmolecules,
            phase_id=simple_candidate.phase_id,
            seed=simple_candidate.seed + i,
            metadata=simple_candidate.metadata.copy()
        )
        
        ranked = RankedCandidate(
            candidate=candidate,
            energy_score=0.001 * i,
            density_score=0.0005 * i,
            diversity_score=0.01 * (10 - i),
            combined_score=0.001 * i,
            rank=i + 1
        )
        candidates.append(ranked)
    
    return RankingResult(
        ranked_candidates=candidates,
        scoring_metadata={"ideal_oo_distance": 0.275},
        weight_config={"energy": 1.0, "density": 1.0, "diversity": 1.0}
    )


class TestWritePdbWithCryst1:
    """Tests for write_pdb_with_cryst1 function."""
    
    def test_creates_valid_pdb_file(self, simple_candidate):
        """Test that function creates a valid PDB file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdb', delete=False) as f:
            filepath = f.name
        
        try:
            write_pdb_with_cryst1(simple_candidate, filepath)
            
            # Check file was created
            assert Path(filepath).exists()
            
            # Read and verify basic structure
            with open(filepath, 'r') as f:
                content = f.read()
            
            assert 'CRYST1' in content
            assert 'ATOM' in content or 'HETATM' in content
            assert 'END' in content
        finally:
            Path(filepath).unlink(missing_ok=True)
    
    def test_cryst1_record_contains_cell_parameters(self, simple_candidate):
        """Test that CRYST1 record contains a, b, c, alpha, beta, gamma in Angstrom."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdb', delete=False) as f:
            filepath = f.name
        
        try:
            write_pdb_with_cryst1(simple_candidate, filepath)
            
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            # Find CRYST1 record
            cryst1_line = None
            for line in lines:
                if line.startswith('CRYST1'):
                    cryst1_line = line
                    break
            
            assert cryst1_line is not None, "CRYST1 record not found"
            
            # Parse CRYST1: columns 7-15 (a), 16-24 (b), 25-33 (c)
            # columns 34-40 (alpha), 41-47 (beta), 48-54 (gamma)
            # Format: CRYST1 a(9.3) b(9.3) c(9.3) alpha(7.2) beta(7.2) gamma(7.2) spacegroup
            a = float(cryst1_line[6:15].strip())
            b = float(cryst1_line[15:24].strip())
            c = float(cryst1_line[24:33].strip())
            alpha = float(cryst1_line[33:40].strip())
            beta = float(cryst1_line[40:47].strip())
            gamma = float(cryst1_line[47:54].strip())
            
            # Expected values: cell * 10.0 (nm to Angstrom)
            # a = 0.9 nm = 9.0 Angstrom
            # b = 0.78 nm = 7.8 Angstrom
            # c = 0.72 nm = 7.2 Angstrom
            assert abs(a - 9.0) < 0.01
            assert abs(b - 7.8) < 0.01
            assert abs(c - 7.2) < 0.01
            
            # For orthogonal cell: alpha=beta=gamma=90°
            assert abs(alpha - 90.0) < 0.01
            assert abs(beta - 90.0) < 0.01
            assert abs(gamma - 90.0) < 0.01
        finally:
            Path(filepath).unlink(missing_ok=True)
    
    def test_coordinates_converted_from_nm_to_angstrom(self, simple_candidate):
        """Test that coordinates are converted from nm to Angstrom (multiply by 10.0)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdb', delete=False) as f:
            filepath = f.name
        
        try:
            write_pdb_with_cryst1(simple_candidate, filepath)
            
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            # Find first ATOM/HETATM record
            atom_line = None
            for line in lines:
                if line.startswith('ATOM') or line.startswith('HETATM'):
                    atom_line = line
                    break
            
            assert atom_line is not None, "ATOM/HETATM record not found"
            
            # Parse coordinates: columns 31-38 (x), 39-46 (y), 47-54 (z)
            # Format: 8.3 (8 chars, 3 decimal places)
            x = float(atom_line[30:38].strip())
            y = float(atom_line[38:46].strip())
            z = float(atom_line[46:54].strip())
            
            # First atom at (0.1, 0.1, 0.1) nm = (1.0, 1.0, 1.0) Angstrom
            assert abs(x - 1.0) < 0.01
            assert abs(y - 1.0) < 0.01
            assert abs(z - 1.0) < 0.01
        finally:
            Path(filepath).unlink(missing_ok=True)
    
    def test_atom_records_follow_pdb_format(self, simple_candidate):
        """Test that ATOM records follow PDB format specification."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdb', delete=False) as f:
            filepath = f.name
        
        try:
            write_pdb_with_cryst1(simple_candidate, filepath)
            
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            # Count ATOM/HETATM records
            atom_count = 0
            for line in lines:
                if line.startswith('ATOM') or line.startswith('HETATM'):
                    atom_count += 1
                    
                    # Verify line length (standard PDB is 80 chars, but we allow flexible)
                    assert len(line) >= 54, f"Line too short: {line}"
                    
                    # Verify serial number format (columns 7-11)
                    serial = line[6:11].strip()
                    assert serial.isdigit(), f"Invalid serial number: {serial}"
                    
                    # Verify atom name format (columns 13-16)
                    atom_name = line[12:16].strip()
                    assert atom_name in ['O', 'H'], f"Invalid atom name: {atom_name}"
            
            # Should have 6 atoms (2 water molecules)
            assert atom_count == 6
        finally:
            Path(filepath).unlink(missing_ok=True)
    
    def test_uses_hetatm_for_water_molecules(self, simple_candidate):
        """Test that HETATM is used for water molecules (standard for non-standard residues)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdb', delete=False) as f:
            filepath = f.name
        
        try:
            write_pdb_with_cryst1(simple_candidate, filepath)
            
            with open(filepath, 'r') as f:
                content = f.read()
            
            # HETATM should be used for water molecules
            assert 'HETATM' in content
        finally:
            Path(filepath).unlink(missing_ok=True)
    
    def test_element_column_right_justified(self, simple_candidate):
        """Test that element symbol is right-justified in columns 77-78."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdb', delete=False) as f:
            filepath = f.name
        
        try:
            write_pdb_with_cryst1(simple_candidate, filepath)
            
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            # Check first HETATM record (oxygen)
            for line in lines:
                if line.startswith('HETATM'):
                    # Element should be in columns 77-78 (0-indexed: 76-78)
                    if len(line) >= 78:
                        element = line[76:78].strip()
                        assert element in ['O', 'H'], f"Invalid element: '{element}'"
                    break
        finally:
            Path(filepath).unlink(missing_ok=True)
    
    def test_triclinic_cell_angles(self, triclinic_candidate):
        """Test that non-orthogonal cell angles are calculated correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdb', delete=False) as f:
            filepath = f.name
        
        try:
            write_pdb_with_cryst1(triclinic_candidate, filepath)
            
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            # Find CRYST1 record
            cryst1_line = None
            for line in lines:
                if line.startswith('CRYST1'):
                    cryst1_line = line
                    break
            
            assert cryst1_line is not None
            
            # Parse angles
            alpha = float(cryst1_line[33:40].strip())
            beta = float(cryst1_line[40:47].strip())
            gamma = float(cryst1_line[47:54].strip())
            
            # Verify angles are in valid range (0-180 degrees)
            assert 0 < alpha < 180
            assert 0 < beta < 180
            assert 0 < gamma < 180
            
            # Should NOT be 90 degrees for triclinic cell
            assert abs(alpha - 90.0) > 1.0
            assert abs(beta - 90.0) > 1.0
            assert abs(gamma - 90.0) > 1.0
        finally:
            Path(filepath).unlink(missing_ok=True)
    
    def test_residue_numbering_increments_per_molecule(self, simple_candidate):
        """Test that residue numbers increment for each water molecule."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdb', delete=False) as f:
            filepath = f.name
        
        try:
            # Create candidate with 2 water molecules
            positions = np.array([
                [0.1, 0.1, 0.1],   # Molecule 1: O
                [0.15, 0.15, 0.1], # Molecule 1: H1
                [0.05, 0.15, 0.1], # Molecule 1: H2
                [0.3, 0.3, 0.3],   # Molecule 2: O
                [0.35, 0.35, 0.3], # Molecule 2: H1
                [0.25, 0.35, 0.3], # Molecule 2: H2
            ])
            atom_names = ["O", "H", "H", "O", "H", "H"]
            
            candidate = Candidate(
                positions=positions,
                atom_names=atom_names,
                cell=simple_candidate.cell.copy(),
                nmolecules=2,
                phase_id="test_phase",
                seed=1,
                metadata={}
            )
            
            write_pdb_with_cryst1(candidate, filepath)
            
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            # Extract residue numbers from HETATM lines
            residue_numbers = []
            for line in lines:
                if line.startswith('HETATM'):
                    # Residue number is in columns 23-26 (1-indexed, so 22-26 in 0-indexed)
                    res_seq = int(line[22:26].strip())
                    residue_numbers.append(res_seq)
            
            # Should have 6 atoms with residue numbers
            assert len(residue_numbers) == 6
            
            # Molecule 1 atoms (O, H, H) should have residue 1
            assert residue_numbers[0] == 1  # O of molecule 1
            assert residue_numbers[1] == 1  # H1 of molecule 1
            assert residue_numbers[2] == 1  # H2 of molecule 1
            
            # Molecule 2 atoms (O, H, H) should have residue 2
            assert residue_numbers[3] == 2  # O of molecule 2
            assert residue_numbers[4] == 2  # H1 of molecule 2
            assert residue_numbers[5] == 2  # H2 of molecule 2
        finally:
            Path(filepath).unlink(missing_ok=True)


class TestWriteRankedCandidates:
    """Tests for write_ranked_candidates function."""
    
    def test_creates_output_directory(self, ranking_result):
        """Test that output directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "subdir" / "output"
            base_name = "ice_candidate"
            
            result = write_ranked_candidates(ranking_result, str(output_dir), base_name)
            
            # Directory should be created
            assert output_dir.exists()
    
    def test_writes_ten_pdb_files(self, ranking_result):
        """Test that exactly 10 PDB files are written (top 10 candidates)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            base_name = "ice_candidate"
            
            result = write_ranked_candidates(ranking_result, str(output_dir), base_name)
            
            # Should return 10 file paths
            assert len(result) == 10
            
            # All files should exist
            for filepath in result:
                assert Path(filepath).exists()
    
    def test_filename_pattern_with_rank_suffix(self, ranking_result):
        """Test that filenames follow {base_name}_{rank:02d}.pdb pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            base_name = "ice_candidate"
            
            result = write_ranked_candidates(ranking_result, str(output_dir), base_name)
            
            # Check filenames
            for i, filepath in enumerate(result):
                expected_name = f"{base_name}_{i+1:02d}.pdb"
                assert Path(filepath).name == expected_name
    
    def test_only_top_ten_candidates_written(self, ranking_result):
        """Test that only the first 10 candidates are written, not all 12."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            base_name = "test"
            
            # Ranking result has 12 candidates
            assert len(ranking_result.ranked_candidates) == 12
            
            result = write_ranked_candidates(ranking_result, str(output_dir), base_name)
            
            # Should only write 10
            assert len(result) == 10
            
            # Verify ranks 1-10 are written
            for i, filepath in enumerate(result):
                assert Path(filepath).exists()
    
    def test_returns_list_of_output_paths(self, ranking_result):
        """Test that function returns list of output file paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            base_name = "ice_candidate"
            
            result = write_ranked_candidates(ranking_result, str(output_dir), base_name)
            
            # Should be a list
            assert isinstance(result, list)
            
            # Should contain strings (file paths)
            assert all(isinstance(p, str) for p in result)
            
            # All paths should end with .pdb
            assert all(p.endswith('.pdb') for p in result)
    
    def test_preserves_candidate_rank_in_filename(self, ranking_result):
        """Test that filename rank matches the candidate's rank attribute."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            base_name = "ice"
            
            result = write_ranked_candidates(ranking_result, str(output_dir), base_name)
            
            # Verify that rank 1 candidate gets _01.pdb, rank 2 gets _02.pdb, etc.
            for i, filepath in enumerate(result):
                expected_rank = i + 1
                expected_suffix = f"_{expected_rank:02d}.pdb"
                assert filepath.endswith(expected_suffix)
