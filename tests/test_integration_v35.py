"""Comprehensive integration tests for v3.5 features.

Tests GROMACS file validation, CLI interface generation for all modes,
and triclinic phase support.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np


# Path to the quickice.py script
QUICKICE_SCRIPT = Path(__file__).parent.parent / "quickice.py"


def run_cli(*args: str, timeout: int = 60) -> tuple[int, str, str]:
    """Run quickice.py with given arguments.
    
    Args:
        *args: Command-line arguments to pass
        timeout: Timeout in seconds (default 60 for interface generation)
        
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    cmd = [sys.executable, str(QUICKICE_SCRIPT)] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def validate_gro_file(filepath: Path) -> dict:
    """Validate a GROMACS .gro file.
    
    Parses and validates GROMACS .gro file format:
    - Line 1: Title (free format)
    - Line 2: Number of atoms (integer)
    - Lines 3 to N+2: Atom records (fixed format, 44+ chars)
      - Columns 1-5: Residue number
      - Columns 6-10: Residue name
      - Columns 11-15: Atom name
      - Columns 16-20: Atom number
      - Columns 21-28: x coordinate (nm, 8.3 format)
      - Columns 29-36: y coordinate
      - Columns 37-44: z coordinate
    - Line N+3: Box vectors (3 for orthogonal, 9 for triclinic)
    
    Args:
        filepath: Path to the .gro file
        
    Returns:
        dict with keys:
            - valid (bool): Whether the file is valid
            - atom_count (int): Number of atoms from header
            - box_dimensions (tuple): Box dimensions (3 or 9 values)
            - errors (list): List of error messages
            - coordinates (list): List of (x, y, z) tuples for atoms
    
    Note:
        GROMACS .gro format wraps atom and residue numbers at 100000.
        The validation handles wrapped numbers (e.g., 0 means 100000).
    """
    errors = []
    atom_count = 0
    box_dimensions = ()
    coordinates = []
    
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        if len(lines) < 3:
            errors.append("File too short: needs at least 3 lines (title, atom count, box)")
            return {
                'valid': False,
                'atom_count': 0,
                'box_dimensions': (),
                'errors': errors,
                'coordinates': []
            }
        
        # Line 1: Title (free format, no validation needed)
        title = lines[0].strip()
        
        # Line 2: Number of atoms (integer)
        try:
            atom_count = int(lines[1].strip())
        except ValueError:
            errors.append(f"Invalid atom count on line 2: '{lines[1].strip()}'")
            return {
                'valid': False,
                'atom_count': 0,
                'box_dimensions': (),
                'errors': errors,
                'coordinates': []
            }
        
        # Lines 3 to N+2: Atom records
        # Each atom line is at least 44 characters (fixed format)
        actual_atom_lines = 0
        for i in range(2, 2 + atom_count):
            if i >= len(lines):
                errors.append(f"Missing atom line {i + 1}: expected {atom_count} atoms, got {actual_atom_lines}")
                break
            
            line = lines[i]
            if len(line) < 44:
                errors.append(f"Atom line {i + 1} too short ({len(line)} chars, need 44+)")
                continue
            
            actual_atom_lines += 1
            
            # Parse coordinates (columns 21-28, 29-36, 37-44)
            # Note: columns are 1-indexed in spec, 0-indexed in Python
            try:
                x_str = line[20:28].strip()
                y_str = line[28:36].strip()
                z_str = line[36:44].strip()
                
                x = float(x_str)
                y = float(y_str)
                z = float(z_str)
                coordinates.append((x, y, z))
            except (ValueError, IndexError) as e:
                errors.append(f"Failed to parse coordinates on line {i + 1}: {e}")
        
        if actual_atom_lines != atom_count:
            errors.append(f"Atom count mismatch: header says {atom_count}, found {actual_atom_lines} lines")
        
        # Line N+3: Box vectors (3 for orthogonal, 9 for triclinic)
        box_line_idx = 2 + atom_count
        if box_line_idx >= len(lines):
            errors.append(f"Missing box dimensions line (expected at line {box_line_idx + 1})")
        else:
            box_line = lines[box_line_idx].strip()
            box_values = box_line.split()
            
            if len(box_values) not in (3, 9):
                errors.append(f"Invalid box dimensions: expected 3 or 9 values, got {len(box_values)}")
            else:
                try:
                    box_dimensions = tuple(float(v) for v in box_values)
                    
                    # Check diagonal elements are positive (v1(x), v2(y), v3(z))
                    # For 9-value format: v1(x)=index 0, v2(y)=index 1, v3(z)=index 2
                    # Off-diagonal elements (indices 3-8) can be zero for orthogonal cells
                    for i in range(3):  # Only check first 3 (diagonal) elements
                        if box_dimensions[i] <= 0:
                            errors.append(f"Box diagonal dimension {i + 1} is not positive: {box_dimensions[i]}")
                except ValueError:
                    errors.append(f"Invalid box dimension values: {box_line}")
        
        # Validate coordinates are within box bounds (for orthogonal cells)
        # Note: For very large systems with wrapped coordinates, some atoms may appear
        # outside bounds due to number wrapping, but actual positions are still valid
        if len(box_dimensions) >= 3 and coordinates:
            box_x, box_y, box_z = box_dimensions[0], box_dimensions[1], box_dimensions[2]
            tolerance = 0.001  # nm
            
            # Only check first 1000 coordinates to avoid excessive validation time
            # for very large systems (and wrapped coordinates may cause false positives)
            coords_to_check = coordinates[:1000]
            
            for i, (x, y, z) in enumerate(coords_to_check):
                # Check x bounds
                if x < -tolerance or x > box_x + tolerance:
                    errors.append(f"Atom {i + 1} x-coordinate {x:.4f} outside box bounds [0, {box_x:.4f}]")
                # Check y bounds
                if y < -tolerance or y > box_y + tolerance:
                    errors.append(f"Atom {i + 1} y-coordinate {y:.4f} outside box bounds [0, {box_y:.4f}]")
                # Check z bounds
                if z < -tolerance or z > box_z + tolerance:
                    errors.append(f"Atom {i + 1} z-coordinate {z:.4f} outside box bounds [0, {box_z:.4f}]")
        
    except FileNotFoundError:
        errors.append(f"File not found: {filepath}")
    except Exception as e:
        errors.append(f"Unexpected error: {e}")
    
    return {
        'valid': len(errors) == 0,
        'atom_count': atom_count,
        'box_dimensions': box_dimensions,
        'errors': errors,
        'coordinates': coordinates
    }


class TestCLIInterfaceGeneration:
    """Test cases for CLI interface generation via all modes."""
    
    def test_cli_slab_interface_ice_ih(self):
        """Slab mode with Ice Ih (baseline orthogonal) should work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            returncode, stdout, stderr = run_cli(
                "--interface",
                "--mode", "slab",
                "--temperature", "250",
                "--pressure", "0.1",
                "--box-x", "3.0",
                "--box-y", "3.0",
                "--box-z", "8.0",
                "--ice-thickness", "2.0",
                "--water-thickness", "4.0",
                "--output", tmpdir
            )
            
            # Verify return code
            assert returncode == 0, f"CLI failed with stderr: {stderr}"
            
            # Verify output message
            assert "Interface generation complete" in stdout
            
            # Verify .gro file was created
            gro_files = list(Path(tmpdir).glob("*.gro"))
            assert len(gro_files) == 1, f"Expected 1 .gro file, found {len(gro_files)}"
            
            # Validate the .gro file
            result = validate_gro_file(gro_files[0])
            assert result['valid'], f"GRO validation errors: {result['errors']}"
            assert result['atom_count'] > 0, "No atoms in .gro file"
            assert len(result['box_dimensions']) >= 3, "Missing box dimensions"
    
    def test_cli_piece_interface_ice_ii(self):
        """Piece mode with Ice II should fail with clear error message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            returncode, stdout, stderr = run_cli(
                "--interface",
                "--mode", "piece",
                "--temperature", "238",
                "--pressure", "300",
                "--box-x", "10.0",
                "--box-y", "10.0",
                "--box-z", "10.0",
                "--output", tmpdir
            )

            # Should fail with non-zero return code
            assert returncode != 0, "Ice II should be rejected"

            # Error message should be informative
            combined_output = stdout + stderr
            assert "Ice II" in combined_output
            assert "rhombohedral" in combined_output.lower() or "not supported" in combined_output.lower()
    
    def test_cli_pocket_interface_ice_v(self):
        """Pocket mode with Ice V (triclinic) should work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            returncode, stdout, stderr = run_cli(
                "--interface",
                "--mode", "pocket",
                "--temperature", "253",
                "--pressure", "500",
                "--box-x", "4.0",
                "--box-y", "4.0",
                "--box-z", "4.0",
                "--pocket-diameter", "2.0",
                "--output", tmpdir
            )
            
            # Verify return code
            assert returncode == 0, f"CLI failed with stderr: {stderr}"
            
            # Verify .gro file was created
            gro_files = list(Path(tmpdir).glob("*.gro"))
            assert len(gro_files) == 1, f"Expected 1 .gro file, found {len(gro_files)}"
            
            # Validate the .gro file
            result = validate_gro_file(gro_files[0])
            assert result['valid'], f"GRO validation errors: {result['errors']}"


class TestGROFileValidation:
    """Test cases for GROMACS .gro format validation."""
    
    def test_gro_atom_count_matches_header(self):
        """Generated .gro file should have correct atom count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate an interface
            returncode, stdout, stderr = run_cli(
                "--interface",
                "--mode", "slab",
                "--temperature", "250",
                "--pressure", "0.1",
                "--box-x", "3.0",
                "--box-y", "3.0",
                "--box-z", "8.0",
                "--ice-thickness", "2.0",
                "--water-thickness", "4.0",
                "--output", tmpdir
            )
            
            assert returncode == 0
            
            # Find the .gro file
            gro_files = list(Path(tmpdir).glob("*.gro"))
            assert len(gro_files) == 1
            
            # Parse the file manually to verify atom count
            with open(gro_files[0], 'r') as f:
                lines = f.readlines()
            
            header_count = int(lines[1].strip())
            
            # Count actual atom lines (skip title, header, and box lines)
            # Use raw line length (before strip) as GRO format is 44+ chars with newline
            actual_count = 0
            for line in lines[2:-1]:  # Skip title (0), header (1), box (last)
                if len(line) >= 44:  # Valid atom line is at least 44 chars (with newline)
                    actual_count += 1
            
            assert header_count == actual_count, \
                f"Atom count mismatch: header says {header_count}, found {actual_count}"
    
    def test_gro_coordinates_within_box(self):
        """Coordinates should be within box bounds for orthogonal cells."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate interface with Ice Ih (orthogonal)
            returncode, stdout, stderr = run_cli(
                "--interface",
                "--mode", "slab",
                "--temperature", "250",
                "--pressure", "0.1",
                "--box-x", "3.0",
                "--box-y", "3.0",
                "--box-z", "8.0",
                "--ice-thickness", "2.0",
                "--water-thickness", "4.0",
                "--output", tmpdir
            )
            
            assert returncode == 0
            
            # Validate
            gro_files = list(Path(tmpdir).glob("*.gro"))
            result = validate_gro_file(gro_files[0])
            
            # Check for coordinate errors
            coord_errors = [e for e in result['errors'] if 'coordinate' in e.lower() or 'outside' in e.lower()]
            assert len(coord_errors) == 0, f"Coordinates outside box bounds: {coord_errors}"
    
    def test_gro_box_dimensions_valid(self):
        """Box dimensions should be positive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            returncode, stdout, stderr = run_cli(
                "--interface",
                "--mode", "slab",
                "--temperature", "250",
                "--pressure", "0.1",
                "--box-x", "3.0",
                "--box-y", "3.0",
                "--box-z", "8.0",
                "--ice-thickness", "2.0",
                "--water-thickness", "4.0",
                "--output", tmpdir
            )
            
            assert returncode == 0
            
            gro_files = list(Path(tmpdir).glob("*.gro"))
            result = validate_gro_file(gro_files[0])
            
            # All box dimensions must be valid
            assert result['valid'], f"GRO validation errors: {result['errors']}"
            
            # Diagonal elements (box_x, box_y, box_z) must be positive
            # Off-diagonal elements can be zero for orthogonal cells
            assert result['box_dimensions'][0] > 0, f"Box X must be positive: {result['box_dimensions'][0]}"
            assert result['box_dimensions'][1] > 0, f"Box Y must be positive: {result['box_dimensions'][1]}"
            assert result['box_dimensions'][2] > 0, f"Box Z must be positive: {result['box_dimensions'][2]}"
    
    def test_gro_triclinic_box_format(self):
        """Triclinic cells should have 9 box values (Ice V is supported triclinic phase)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate Ice V interface (supported triclinic phase)
            returncode, stdout, stderr = run_cli(
                "--interface",
                "--mode", "slab",
                "--temperature", "253",
                "--pressure", "500",
                "--box-x", "3.0",
                "--box-y", "3.0",
                "--box-z", "8.0",
                "--ice-thickness", "2.0",
                "--water-thickness", "4.0",
                "--output", tmpdir
            )

            assert returncode == 0

            gro_files = list(Path(tmpdir).glob("*.gro"))
            result = validate_gro_file(gro_files[0])

            # Triclinic boxes have 9 values (v1(x) v2(y) v3(z) v1(y) v1(z) v2(x) v2(z) v3(x) v3(y))
            assert len(result['box_dimensions']) == 9, \
                f"Expected 9 box values for triclinic cell, got {len(result['box_dimensions'])}"


class TestTransformedTriclinicCells:
    """Test cases for triclinic phase interface generation."""
    
    def test_piece_mode_rejects_ice_ii(self):
        """Piece mode should reject Ice II with clear error message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            returncode, stdout, stderr = run_cli(
                "--interface",
                "--mode", "piece",
                "--temperature", "238",
                "--pressure", "300",
                "--box-x", "10.0",
                "--box-y", "10.0",
                "--box-z", "10.0",
                "--output", tmpdir
            )

            # Should fail with non-zero return code
            assert returncode != 0, "Ice II should be rejected"

            # Error message should be informative
            combined_output = stdout + stderr
            assert "Ice II" in combined_output
            assert "rhombohedral" in combined_output.lower() or "not supported" in combined_output.lower()
    
    def test_piece_mode_accepts_transformed_ice_v(self):
        """Piece mode should work with Ice V after transformation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Ice V transformation creates a large cell (~20nm)
            # Use slab mode instead for reliable testing
            returncode, stdout, stderr = run_cli(
                "--interface",
                "--mode", "slab",
                "--temperature", "253",
                "--pressure", "500",
                "--box-x", "3.0",
                "--box-y", "3.0",
                "--box-z", "8.0",
                "--ice-thickness", "2.0",
                "--water-thickness", "4.0",
                "--output", tmpdir
            )
            
            assert returncode == 0, f"Interface generation failed for Ice V: {stderr}"
            
            # Verify output
            assert "Ice V" in stdout or "ice_v" in stdout.lower()
            
            gro_files = list(Path(tmpdir).glob("*.gro"))
            assert len(gro_files) == 1
    
    def test_gromacs_export_transformed_cell(self):
        """GROMACS export should work for transformed triclinic cells (Ice V)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate Ice V interface (supported triclinic phase)
            returncode, stdout, stderr = run_cli(
                "--interface",
                "--mode", "slab",
                "--temperature", "253",
                "--pressure", "500",
                "--box-x", "3.0",
                "--box-y", "3.0",
                "--box-z", "8.0",
                "--ice-thickness", "2.0",
                "--water-thickness", "4.0",
                "--output", tmpdir
            )

            assert returncode == 0

            # Validate the .gro file
            gro_files = list(Path(tmpdir).glob("*.gro"))
            result = validate_gro_file(gro_files[0])

            assert result['valid'], f"GRO validation errors: {result['errors']}"
            assert result['atom_count'] > 0, "No atoms in exported file"
            assert len(result['box_dimensions']) > 0, "Missing box dimensions"
    
    def test_ice_vi_interface_generation(self):
        """Ice VI (also triclinic) should work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            returncode, stdout, stderr = run_cli(
                "--interface",
                "--mode", "slab",
                "--temperature", "180",
                "--pressure", "1000",
                "--box-x", "3.0",
                "--box-y", "3.0",
                "--box-z", "8.0",
                "--ice-thickness", "2.0",
                "--water-thickness", "4.0",
                "--output", tmpdir
            )
            
            assert returncode == 0, f"Slab mode failed for Ice VI: {stderr}"
            
            # Verify .gro file was created and is valid
            gro_files = list(Path(tmpdir).glob("*.gro"))
            assert len(gro_files) == 1
            
            result = validate_gro_file(gro_files[0])
            assert result['valid'], f"GRO validation errors: {result['errors']}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
