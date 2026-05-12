# Testing Patterns

**Analysis Date:** 2026-05-12

## Test Framework

**Runner:**
- pytest >= 9.0.0 (from `requirements-dev.txt`)
- No pytest.ini or pyproject.toml configuration detected
- Configuration via command-line arguments or pytest conventions

**Assertion Library:**
- Built-in `assert` statements
- NumPy's `np.testing.assert_array_equal` and `np.testing.assert_allclose` for array comparisons

**Run Commands:**
```bash
pytest                          # Run all tests
pytest tests/test_validators.py # Run specific file
pytest -v                       # Verbose output
pytest -k "phase"               # Run tests matching pattern
```

## Test File Organization

**Location:**
- Tests in separate `tests/` directory at project root
- Test output tests in subdirectory: `tests/test_output/`

**Naming:**
- Pattern: `test_<module_or_feature>.py`
- Examples: `test_validators.py`, `test_phase_mapping.py`, `test_structure_generation.py`

**Structure:**
```
tests/
├── __init__.py                      # Package marker
├── test_validators.py               # Input validation tests
├── test_phase_mapping.py            # Phase lookup tests
├── test_structure_generation.py     # Generator tests
├── test_ranking.py                  # Candidate ranking tests
├── test_integration_v35.py          # Integration tests
├── test_solute_insertion.py         # Solute workflow tests
├── test_custom_molecule.py          # Custom molecule tests
├── test_cli_integration.py          # CLI integration tests
├── test_triclinic_interface.py      # Triclinic cell tests
├── test_piece_mode_validation.py    # Piece mode tests
├── test_output/
│   ├── __init__.py
│   ├── test_validator.py            # Output validation tests
│   ├── test_pdb_writer.py           # PDB writer tests
│   └── test_molecule_wrapping.py    # Molecule wrapping tests
```

## Test Structure

**Suite Organization:**
```python
"""Tests for input validators."""

import pytest
from argparse import ArgumentTypeError
from quickice.validation.validators import (
    validate_temperature,
    validate_pressure,
)


class TestValidateTemperature:
    """Tests for temperature validation."""

    def test_accepts_valid_minimum_boundary(self):
        """Temperature 0K should be accepted."""
        result = validate_temperature("0")
        assert result == 0.0
        assert isinstance(result, float)

    def test_rejects_negative_temperature(self):
        """Temperature -1K should be rejected."""
        with pytest.raises(ArgumentTypeError) as exc_info:
            validate_temperature("-1")
        assert "temperature" in str(exc_info.value).lower()
```

**Patterns:**
- Group related tests in classes (`TestValidateTemperature`, `TestLookupPhaseIceIh`)
- Descriptive test names following `test_<action>_<condition>` pattern
- Docstrings explain what's being tested and expected outcome
- Each test method tests one specific behavior

## Mocking

**Framework:** No explicit mocking framework detected (no unittest.mock imports found)

**Patterns:**
- Tests use real objects where possible
- Fixtures create mock/test data structures
- Example fixture from `tests/test_solute_insertion.py`:
  ```python
  @pytest.fixture
  def interface_structure(self):
      """Create mock interface structure for testing."""
      # Create ice atoms (simple cubic crystal)
      n_ice_molecules = 100
      ice_positions = []
      for i in range(n_ice_molecules):
          # Each water molecule has 3 atoms (O, H, H)
          ice_positions.append([i * 0.3, 0, 0])  # O
          ice_positions.append([i * 0.3 + 0.1, 0.1, 0])  # H
          ice_positions.append([i * 0.3 + 0.1, -0.1, 0])  # H
      
      # ... create water atoms ...
      
      return InterfaceStructure(
          positions=all_positions,
          atom_names=atom_names,
          cell=cell,
          ice_atom_count=n_ice_molecules * 3,
          water_atom_count=n_water_molecules * 3,
          mode="slab",
          report="Mock interface for testing",
      )
  ```

**What to Mock:**
- Complex data structures that are test prerequisites
- External dependencies (files, network resources)

**What NOT to Mock:**
- Core business logic (test real implementation)
- Data transformations

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def simple_candidate():
    """Create a simple candidate for testing.
    
    Creates a 1nm cubic cell with 4 water molecules.
    """
    positions = np.array([
        # Molecule 1: O at origin, H's nearby
        [0.0, 0.0, 0.0],    # O
        [0.1, 0.0, 0.0],    # H
        [-0.1, 0.0, 0.0],   # H
        # ... more molecules ...
    ])
    atom_names = ['O', 'H', 'H', 'O', 'H', 'H', 'O', 'H', 'H', 'O', 'H', 'H']
    cell = np.eye(3) * 1.0  # 1nm cubic cell
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=4,
        phase_id="ice_ih",
        seed=42,
    )
```

**Fixture Location:**
- Inline in test files (most common)
- No shared fixture files detected

**Fixture Scope:**
- Default function scope (each test gets fresh fixture)
- Use `@pytest.fixture(autouse=True)` for setup that runs for all tests in class

## Coverage

**Requirements:** No coverage threshold enforced

**View Coverage:**
```bash
pytest --cov=quickice --cov-report=html
```

**Coverage Notes:**
- GUI tests may be skipped due to missing pytest-qt
- Integration tests require full environment setup

## Test Types

**Unit Tests:**
- Test individual functions and methods in isolation
- Use fixtures to set up test data
- Example from `tests/test_validators.py`:
  ```python
  def test_accepts_valid_minimum_boundary(self):
      """Temperature 0K should be accepted."""
      result = validate_temperature("0")
      assert result == 0.0
      assert isinstance(result, float)
  ```

**Integration Tests:**
- Test complete workflows
- Located in `test_integration_v35.py`, `test_cli_integration.py`
- Test full pipeline from input to output
- Example from `tests/test_integration_v35.py`:
  ```python
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
          
          assert returncode == 0, f"CLI failed with stderr: {stderr}"
          assert "Interface generation complete" in stdout
          
          gro_files = list(Path(tmpdir).glob("*.gro"))
          assert len(gro_files) == 1
  ```

**E2E Tests:**
- CLI integration tests cover end-to-end workflows
- Test actual script execution via subprocess
- Validate generated files (GRO format validation)

## Common Patterns

**Async Testing:**
- Not detected in current test suite
- Project is primarily synchronous

**Error Testing:**
```python
def test_rejects_negative_temperature(self):
    """Temperature -1K should be rejected."""
    with pytest.raises(ArgumentTypeError) as exc_info:
        validate_temperature("-1")
    assert "temperature" in str(exc_info.value).lower()

def test_unsupported_phase_raises_error(self):
    """Unsupported phase ID should raise UnsupportedPhaseError."""
    with pytest.raises(UnsupportedPhaseError) as exc_info:
        get_genice_lattice_name("ice_xxx")
    assert exc_info.value.phase_id == "ice_xxx"
```

**Boundary Testing:**
- Tests include boundary conditions explicitly
- Example from `tests/test_validators.py`:
  ```python
  def test_accepts_valid_minimum_boundary(self):
      """Temperature 0K should be accepted."""
      result = validate_temperature("0")
      assert result == 0.0

  def test_accepts_valid_maximum_boundary(self):
      """Temperature 500K should be accepted."""
      result = validate_temperature("500")
      assert result == 500.0
  ```

**Reproducibility Testing:**
```python
def test_generate_all_reproducible_with_seed(self, phase_info_ice_ih):
    """Same base_seed should produce identical candidates across batches."""
    gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)

    candidates1 = gen.generate_all(base_seed=42)
    candidates2 = gen.generate_all(base_seed=42)

    seeds1 = [c.seed for c in candidates1]
    seeds2 = [c.seed for c in candidates2]
    assert seeds1 == seeds2

    for c1, c2 in zip(candidates1, candidates2):
        np.testing.assert_array_equal(c1.positions, c2.positions)
```

**Skipping Tests:**
```python
@pytest.mark.skip(reason="pytest-qt not installed in test environment")
def test_panel_initialization(self, qtbot):
    """Test SolutePanel initializes correctly."""
    from quickice.gui.solute_panel import SolutePanel
    panel = SolutePanel()
    qtbot.addWidget(panel)
```

## NumPy Testing Patterns

**Array Assertions:**
```python
# Check arrays are exactly equal
np.testing.assert_array_equal(candidate.positions, expected_positions)

# Check arrays are close (with tolerance)
assert np.allclose(center, 0, atol=0.2)

# Check array shapes
assert candidate.positions.shape == (384, 3)
assert candidate.cell.shape == (3, 3)
```

**Array Validation:**
```python
# Check all values are finite
assert np.all(np.isfinite(candidate.positions))

# Check determinant
det = np.linalg.det(rotation_matrix)
assert np.isclose(det, 1.0, atol=1e-6)
```

## CLI Testing Pattern

**Helper Function:**
```python
def run_cli(*args: str, timeout: int = 60) -> tuple[int, str, str]:
    """Run quickice.py with given arguments."""
    cmd = [sys.executable, str(QUICKICE_SCRIPT)] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr
```

**Usage:**
```python
def test_cli_ice_ih_output(self):
    """CLI should show Ice Ih for T=273K, P=0MPa."""
    result = subprocess.run(
        [sys.executable, "quickice.py", "--temperature", "273", 
         "--pressure", "0", "--nmolecules", "100"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Ice Ih" in result.stdout
    assert "ice_ih" in result.stdout
```

## File Validation Pattern

**GRO File Validation:**
```python
def validate_gro_file(filepath: Path) -> dict:
    """Validate a GROMACS .gro file.
    
    Returns:
        dict with keys:
            - valid (bool): Whether the file is valid
            - atom_count (int): Number of atoms from header
            - box_dimensions (tuple): Box dimensions
            - errors (list): List of error messages
            - coordinates (list): List of (x, y, z) tuples
    """
    errors = []
    # Parse and validate file format...
    return {
        'valid': len(errors) == 0,
        'atom_count': atom_count,
        'box_dimensions': box_dimensions,
        'errors': errors,
        'coordinates': coordinates
    }
```

---

*Testing analysis: 2026-05-12*
