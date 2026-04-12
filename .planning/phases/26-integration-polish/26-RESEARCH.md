# Phase 26: Integration & Polish - Research

**Researched:** 2026-04-12
**Domain:** Software testing, integration testing, GROMACS file validation
**Confidence:** HIGH

## Summary

This research covers integration testing patterns, GROMACS .gro file validation, and the current state of the codebase for cross-cutting integration. The existing codebase already has:
- Triclinic transformation working (Phase 24 removed orthogonal-only restriction from piece.py)
- CLI interface generation with GROMACS export (Phase 25)
- Density calculation for Ice Ih and water (Phases 22-23)
- Well-established test patterns using pytest with class-based organization

The primary work is creating integration tests that verify end-to-end workflows, not new feature development.

**Primary recommendation:** Create `tests/test_integration_v35.py` following existing patterns, with GROMACS validation functions and CLI subprocess tests.

## Standard Stack

The established testing approach for this project:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | (existing) | Test framework | Already used throughout |
| numpy | (existing) | Array assertions | Already used for structure validation |
| tempfile | stdlib | Temporary files | Used in test_output/test_pdb_writer.py |
| subprocess | stdlib | CLI testing | Used in test_cli_integration.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | Path handling | All file operations |
| pytest fixtures | (existing) | Test data setup | Complex test scenarios |

### Test Structure Pattern
```
tests/
├── test_integration_v35.py     # NEW: End-to-end integration tests
├── test_cli_integration.py     # Existing: CLI subprocess tests
├── test_triclinic_interface.py # Existing: Triclinic phase tests
├── test_transformer.py         # Existing: Transformation tests
└── test_output/
    ├── test_pdb_writer.py      # Existing: PDB output tests
    └── test_validator.py       # Existing: Structure validation tests
```

## Architecture Patterns

### Recommended Test Structure
```
tests/test_integration_v35.py:
├── TestGROFileValidation         # GROMACS .gro format validation
│   ├── test_gro_atom_count_matches_header
│   ├── test_gro_coordinates_within_box
│   ├── test_gro_box_dimensions_valid
│   └── test_gro_triclinic_box_format
├── TestCLIInterfaceGeneration    # CLI end-to-end workflows
│   ├── test_cli_slab_interface_ice_ih
│   ├── test_cli_piece_interface_ice_ii
│   └── test_cli_pocket_interface_ice_v
├── TestTransformedTriclinicCells # Verify triclinic + transformation
│   ├── test_piece_mode_accepts_transformed_ice_ii
│   ├── test_piece_mode_accepts_transformed_ice_v
│   └── test_gromacs_export_transformed_cell
└── TestDensityDisplayValues      # Verify density calculation integration
    ├── test_ice_ih_density_integration
    └── test_water_density_integration
```

### Pattern 1: GROMACS .gro File Validation
**What:** Validate .gro files are correctly formatted and contain valid data
**When to use:** After any GROMACS export operation
**Example:**
```python
def validate_gro_file(filepath: Path) -> dict:
    """Validate a GROMACS .gro file.
    
    Returns dict with validation results:
    - valid: bool
    - atom_count: int
    - box_dimensions: tuple
    - errors: list[str]
    """
    errors = []
    
    with open(filepath) as f:
        lines = f.readlines()
    
    # Line 1: Title (free format)
    title = lines[0].strip()
    
    # Line 2: Number of atoms
    try:
        header_atom_count = int(lines[1].strip())
    except ValueError:
        errors.append("Invalid atom count line")
        return {"valid": False, "errors": errors}
    
    # Atom lines: count and validate format
    atom_lines = lines[2:2+header_atom_count]
    if len(atom_lines) != header_atom_count:
        errors.append(f"Expected {header_atom_count} atoms, found {len(atom_lines)}")
    
    # Box line: last line after atoms
    box_line = lines[2+header_atom_count]
    box_values = [float(x) for x in box_line.split()]
    if len(box_values) < 3:
        errors.append("Box line must have at least 3 values")
    
    return {
        "valid": len(errors) == 0,
        "atom_count": header_atom_count,
        "box_dimensions": tuple(box_values[:3]),
        "errors": errors
    }
```

### Pattern 2: CLI Integration Test
**What:** Test CLI commands via subprocess like existing test_cli_integration.py
**When to use:** End-to-end CLI workflow testing
**Example:**
```python
def run_cli(*args: str) -> tuple[int, str, str]:
    """Run quickice.py with given arguments."""
    cmd = [sys.executable, str(QUICKICE_SCRIPT)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return result.returncode, result.stdout, result.stderr

def test_cli_piece_interface_ice_ii():
    """Ice II piece interface should work via CLI."""
    with tempfile.TemporaryDirectory() as tmpdir:
        returncode, stdout, stderr = run_cli(
            "--interface",
            "--mode", "piece",
            "--temperature", "238",
            "--pressure", "300",
            "--box-x", "4.0",
            "--box-y", "4.0", 
            "--box-z", "4.0",
            "--output", tmpdir
        )
        
        assert returncode == 0, f"CLI failed: {stderr}"
        assert "Interface generation complete" in stdout
        
        # Verify .gro file was created
        gro_files = list(Path(tmpdir).glob("*.gro"))
        assert len(gro_files) == 1
        
        # Validate .gro file
        result = validate_gro_file(gro_files[0])
        assert result["valid"], f"Invalid GRO: {result['errors']}"
```

### Pattern 3: Parametrized Phase Testing
**What:** Test multiple ice phases with same test logic
**When to use:** Testing triclinic phases (Ice II, V, VI) with similar assertions
**Example:**
```python
@pytest.mark.parametrize("phase_id,temperature,pressure", [
    ("ice_ii", 238, 300),
    ("ice_v", 253, 500),
    ("ice_vi", 180, 1000),
])
def test_triclinic_phase_interface(phase_id, temperature, pressure):
    """All triclinic phases should work in piece mode."""
    phase_info = {
        "phase_id": phase_id,
        "phase_name": phase_id.replace("_", " ").title(),
        "temperature": temperature,
        "pressure": pressure,
        "density": 1.18,  # Approximate, will be overridden
    }
    result = generate_candidates(phase_info, nmolecules=50, n_candidates=1)
    candidate = result.candidates[0]
    
    # Generate interface - should NOT raise
    config = InterfaceConfig(mode="piece", box_x=4.0, box_y=4.0, box_z=4.0, seed=42)
    interface = generate_interface(candidate, config)
    
    assert interface.ice_nmolecules > 0
    assert interface.water_nmolecules > 0
```

### Anti-Patterns to Avoid
- **Don't test density calculation logic:** Already tested in test_ice_ih_density.py and test_water_density.py
- **Don't test transformation logic in isolation:** Already tested in test_transformer.py
- **Don't mock GenIce2:** Use real structure generation for integration tests
- **Don't skip CLI tests:** CLI integration is critical for this phase

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GRO parsing | Custom parser | GROMACS format spec (see below) | Format is fixed and documented |
| CLI testing | Function calls | subprocess like test_cli_integration.py | Tests actual CLI entry point |
| Temp files | Manual cleanup | tempfile.TemporaryDirectory() | Automatic cleanup, safer |
| Parametrized tests | Loop over phases | pytest.mark.parametrize | Better test isolation and reporting |

**Key insight:** Follow existing patterns in test_cli_integration.py and test_output/test_pdb_writer.py

## Common Pitfalls

### Pitfall 1: Testing Density Display Without GUI
**What goes wrong:** Trying to automate GUI testing for density display
**Why it happens:** Wanting full automation
**How to avoid:** CONTEXT.md explicitly says "No automated GUI tests" — manual verification is sufficient
**Warning signs:** Attempting to use PyQt test frameworks

### Pitfall 2: Forgetting Triclinic Box Format
**What goes wrong:** Assuming GROMACS box line is always 3 values (x, y, z)
**Why it happens:** Most test structures are orthogonal
**How to avoid:** Triclinic boxes have 9 values: v1(x) v2(y) v3(z) v1(y) v1(z) v2(x) v2(z) v3(x) v3(y)
**Warning signs:** Parsing only first 3 values of box line

### Pitfall 3: Not Testing CLI Parameter Validation
**What goes wrong:** Only testing successful CLI calls, not error cases
**Why it happens:** Focus on "happy path"
**How to avoid:** Test missing parameters, invalid modes, out-of-range values
**Warning signs:** All CLI tests have returncode == 0

### Pitfall 4: Using Wrong Molecule Count for Interface
**What goes wrong:** Using --nmolecules with --interface mode (not supported)
**Why it happens:** Not understanding CLI parameter constraints
**How to avoid:** Interface mode uses default 256 molecules (hardcoded in main.py)
**Warning signs:** Tests that pass --nmolecules to interface generation

## Code Examples

### GROMACS .gro File Validation Function

```python
# Source: GROMACS 2026 documentation
# https://manual.gromacs.org/current/reference-manual/file-formats.html#gro

def validate_gro_file(filepath: Path) -> dict:
    """Validate a GROMACS .gro coordinate file.
    
    GROMACS .gro format:
    - Line 1: Title string (free format, optional time after 't=')
    - Line 2: Number of atoms (free format integer)
    - Lines 3 to N+2: Atom records (fixed format, 44+ chars each)
      - Columns 1-5: Residue number (integer)
      - Columns 6-10: Residue name (5 chars)
      - Columns 11-15: Atom name (5 chars)
      - Columns 16-20: Atom number (integer)
      - Columns 21-28: x coordinate (nm, 8.3 format)
      - Columns 29-36: y coordinate (nm, 8.3 format)
      - Columns 37-44: z coordinate (nm, 8.3 format)
    - Line N+3: Box vectors (free format, 3 or 9 values)
      - Orthogonal: v1(x) v2(y) v3(z)
      - Triclinic: v1(x) v2(y) v3(z) v1(y) v1(z) v2(x) v2(z) v3(x) v3(y)
    
    Returns:
        dict with keys: valid, atom_count, box_dimensions, errors
    """
    errors = []
    
    with open(filepath) as f:
        lines = f.readlines()
    
    if len(lines) < 3:
        errors.append("File too short: need title, atom count, and at least one atom")
        return {"valid": False, "errors": errors}
    
    # Parse header
    title = lines[0].strip()
    
    try:
        header_atom_count = int(lines[1].strip())
    except ValueError as e:
        errors.append(f"Invalid atom count line: {lines[1].strip()}")
        return {"valid": False, "errors": errors}
    
    # Validate atom count matches actual lines
    expected_atom_lines = header_atom_count
    actual_atom_lines = len(lines) - 3  # Exclude title, count, box
    
    if actual_atom_lines != expected_atom_lines:
        errors.append(
            f"Atom count mismatch: header says {header_atom_count}, "
            f"found {actual_atom_lines} atom lines"
        )
    
    # Parse box dimensions
    box_line = lines[-1].strip()
    try:
        box_values = [float(x) for x in box_line.split()]
    except ValueError as e:
        errors.append(f"Invalid box line: {box_line}")
        box_values = []
    
    if len(box_values) not in (3, 9):
        errors.append(f"Box line must have 3 or 9 values, found {len(box_values)}")
    
    # Validate coordinates are within box (for orthogonal)
    if len(box_values) >= 3:
        box_x, box_y, box_z = box_values[0], box_values[1], box_values[2]
        
        for i, line in enumerate(lines[2:2+header_atom_count], start=1):
            if len(line) < 44:
                errors.append(f"Atom line {i} too short: {len(line)} chars")
                continue
            
            try:
                x = float(line[20:28])
                y = float(line[28:36])
                z = float(line[36:44])
                
                # Check coordinates are positive and within box
                if x < 0 or x > box_x:
                    errors.append(f"Atom {i} x={x:.3f} outside box [0, {box_x:.3f}]")
                if y < 0 or y > box_y:
                    errors.append(f"Atom {i} y={y:.3f} outside box [0, {box_y:.3f}]")
                if z < 0 or z > box_z:
                    errors.append(f"Atom {i} z={z:.3f} outside box [0, {box_z:.3f}]")
            except ValueError:
                errors.append(f"Atom line {i} has invalid coordinates")
    
    return {
        "valid": len(errors) == 0,
        "atom_count": header_atom_count,
        "box_dimensions": tuple(box_values) if box_values else (),
        "errors": errors
    }
```

### CLI Interface Generation Test

```python
# Source: tests/test_cli_integration.py pattern
import subprocess
import sys
import tempfile
from pathlib import Path

QUICKICE_SCRIPT = Path(__file__).parent.parent / "quickice.py"

def run_cli(*args: str, timeout: int = 60) -> tuple[int, str, str]:
    """Run quickice.py with given arguments."""
    cmd = [sys.executable, str(QUICKICE_SCRIPT)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout, result.stderr


class TestCLIInterfaceGeneration:
    """Integration tests for CLI interface generation."""
    
    def test_slab_interface_ice_ih(self):
        """Slab interface with Ice Ih should succeed."""
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
            
            assert returncode == 0, f"CLI failed: {stderr}"
            assert "Interface generation complete" in stdout
            
            # Verify GROMACS files created
            gro_files = list(Path(tmpdir).glob("*.gro"))
            assert len(gro_files) == 1, "Should create one .gro file"
            
            # Validate .gro file
            result = validate_gro_file(gro_files[0])
            assert result["valid"], f"Invalid GRO file: {result['errors']}"
            assert result["atom_count"] > 0
    
    def test_piece_interface_ice_ii(self):
        """Piece interface with Ice II (triclinic) should succeed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            returncode, stdout, stderr = run_cli(
                "--interface",
                "--mode", "piece",
                "--temperature", "238",
                "--pressure", "300",
                "--box-x", "4.0",
                "--box-y", "4.0",
                "--box-z", "4.0",
                "--output", tmpdir
            )
            
            assert returncode == 0, f"CLI failed for Ice II piece: {stderr}"
            assert "Interface generation complete" in stdout
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Orthogonal-only piece mode | Transformed triclinic accepted | Phase 24 | Ice II, V, VI now work in piece mode |
| Mock data for tests | Real GenIce2 structures | v3.0 | Tests reflect real usage |
| Separate test functions | pytest.mark.parametrize | Existing pattern | Cleaner multi-case testing |

**Deprecated/outdated:**
- Orthogonal-only validation in piece.py: Removed in Phase 24, no longer needed

## Open Questions

Things that couldn't be fully resolved:

1. **Exact tolerance values for coordinate validation**
   - What we know: Coordinates should be within box, but floating-point precision may cause edge cases
   - What's unclear: Exact tolerance for "within box" check (e.g., 1e-6 nm?)
   - Recommendation: Use 0.001 nm tolerance (1e-3 nm) for coordinate validation

2. **Timeout values for CLI tests**
   - What we know: Interface generation can take several seconds
   - What's unclear: Upper bound for slowest test case
   - Recommendation: Use 60s timeout for interface tests, 10s for simple CLI tests

## Sources

### Primary (HIGH confidence)
- `tests/test_cli_integration.py` - Existing CLI test patterns
- `tests/test_triclinic_interface.py` - Triclinic phase interface tests
- `tests/test_output/test_pdb_writer.py` - File output test patterns
- `quickice/output/gromacs_writer.py` - GROMACS .gro format implementation
- GROMACS 2026 manual - https://manual.gromacs.org/current/reference-manual/file-formats.html#gro

### Secondary (MEDIUM confidence)
- `quickice/main.py` - CLI interface generation workflow
- `quickice/cli/parser.py` - CLI argument validation
- `quickice/structure_generation/modes/piece.py` - Piece mode implementation (orthogonal-only removed)

### Tertiary (LOW confidence)
- None needed - primary sources sufficient

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pytest, tempfile patterns well-established in codebase
- Architecture: HIGH - test structure follows existing patterns
- GROMACS validation: HIGH - format documented in official GROMACS manual
- Pitfalls: HIGH - based on actual codebase analysis

**Research date:** 2026-04-12
**Valid until:** 30 days - test patterns are stable
