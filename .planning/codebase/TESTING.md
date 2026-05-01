# Testing Patterns

**Analysis Date:** 2026-05-02

## Test Framework

**Runner:**
- pytest 9.0.0+
- Config: No `pytest.ini` or `conftest.py` at root level
- Test discovery: Standard pytest discovery (`test_*.py` files, `Test*` classes, `test_*` functions)

**Assertion Library:**
- pytest assertions (built-in `assert` statement)
- NumPy test utilities: `np.testing.assert_array_equal()` for array comparisons

**Run Commands:**
```bash
pytest                          # Run all tests
pytest tests/                   # Run tests in specific directory
pytest tests/test_validators.py # Run specific test file
pytest -v                       # Verbose output
pytest -x                       # Stop on first failure
```

## Test File Organization

**Location:**
- Tests in separate `tests/` directory (not co-located with source)
- Integration tests: `tests/test_integration_v35.py`, `tests/test_cli_integration.py`
- Unit tests: `tests/test_validators.py`, `tests/test_structure_generation.py`
- Subdirectory tests: `tests/test_output/` for output-related tests

**Naming:**
- Test files: `test_<module_or_feature>.py` (e.g., `test_validators.py`, `test_ranking.py`)
- Test classes: `Test<Feature>` (e.g., `TestValidateTemperature`, `TestPhaseToGenIceMapping`)
- Test methods: `test_<description>` (e.g., `test_accepts_valid_minimum_boundary`)

**Structure:**
```
tests/
├── __init__.py
├── test_validators.py
├── test_cli_integration.py
├── test_integration_v35.py
├── test_structure_generation.py
├── test_phase_mapping.py
├── test_ranking.py
├── test_pbc_hbonds.py
├── test_triclinic_interface.py
├── test_interface_modes_audit.py
├── test_hydrate_guest_tiling.py
├── test_output/
│   ├── test_pdb_writer.py
│   ├── test_validator.py
│   └── test_molecule_wrapping.py
└── test_output/           # Test output directory
```

## Test Structure

**Suite Organization:**
```python
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
- Class-based organization: Group related tests in classes
- Docstrings: Every test method has a docstring describing expected behavior
- Boundary testing: Explicit tests for boundary values (min, max, edge cases)
- Descriptive test names: Names describe what is being tested

**Test Organization by Type:**
- Validation tests: Test input validation with boundary values
- Unit tests: Test individual functions in isolation
- Integration tests: Test full workflows using subprocess
- Structure tests: Test data structures and type conversions

## Mocking

**Framework:** Minimal use of mocking; tests prefer real objects and integration testing

**Patterns:**
- Mock objects created manually when needed (no `unittest.mock` detected)
- Fixtures create test data structures instead of mocking
- CLI integration tests use subprocess to test real execution

**Example from `tests/test_interface_modes_audit.py`:**
```python
def create_mock_ice_candidate(ice_atoms: int = 12) -> Candidate:
    """Create a simple mock ice candidate (GenIce style: 3 atoms per molecule O, H, H)."""
    positions = np.array([...])
    atom_names = ["O", "H", "H"] * (ice_atoms // 3)
    cell = np.array([...])
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=ice_atoms // 3,
        phase_id="ice_ih",
        seed=42,
        metadata={"density": 0.9167}
    )
```

**What to Mock:**
- External dependencies (file I/O for integration tests)
- Complex data structures for unit tests
- Ice/water structures when testing interface assembly

**What NOT to Mock:**
- Core calculation functions
- Data transformations
- Type conversions

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def simple_candidate():
    """Create a simple candidate for testing.
    
    Cell vectors in nm (will be converted to Angstrom):
    - a = [0.9, 0.0, 0.0] -> a = 0.9 nm = 9.0 Angstrom
    - b = [0.0, 0.78, 0.0] -> b = 0.78 nm = 7.8 Angstrom
    - c = [0.0, 0.0, 0.72] -> c = 0.72 nm = 7.2 Angstrom
    """
    cell = np.array([
        [0.9, 0.0, 0.0],
        [0.0, 0.78, 0.0],
        [0.0, 0.0, 0.72]
    ])
    
    positions = np.array([
        [0.1, 0.1, 0.1],   # O1
        [0.15, 0.12, 0.1], # H1
        [0.08, 0.12, 0.1], # H2
    ])
    
    atom_names = ["O", "H", "H"]
    
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=1,
        phase_id="ice_ih",
        seed=42,
        metadata={"density": 0.9167}
    )
```

**Location:**
- Fixtures defined in test files (no shared `conftest.py`)
- Each test file defines its own fixtures as needed
- Fixture names describe what they provide (e.g., `simple_candidate`, `triclinic_candidate`)

**Fixture Types:**
- Simple data structures: `simple_candidate()`, `triclinic_candidate()`
- Complex structures: `ranking_result()` with multiple candidates
- Validation helpers: File validation functions

## Coverage

**Requirements:** No coverage requirements enforced

**View Coverage:**
```bash
# Install coverage plugin
pip install pytest-cov

# Run with coverage
pytest --cov=quickice --cov-report=html
```

**Coverage Status:**
- No coverage reports configured
- No coverage badges in README
- No CI coverage enforcement

**Test Count:**
- 19 test files
- ~5,486 total lines of test code
- Tests cover validation, structure generation, CLI integration, GROMACS output, phase mapping

## Test Types

**Unit Tests:**
- Scope: Individual functions and classes
- Approach: Test functions in isolation with controlled inputs
- Examples: `test_validators.py`, `test_structure_generation.py`

**Example from `tests/test_structure_generation.py`:**
```python
class TestCalculateSupercell:
    """Tests for supercell calculation."""
    
    def test_supercell_100_molecules_ice1h(self):
        """Target 100 molecules with ice1h (16 per unit cell) should return 2x2x2 with 128 molecules."""
        supercell, actual = calculate_supercell(100, 16)
        expected_matrix = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 128
```

**Integration Tests:**
- Scope: Full application workflows
- Approach: Use subprocess to execute CLI commands
- Examples: `test_cli_integration.py`, `test_integration_v35.py`

**Example from `tests/test_cli_integration.py`:**
```python
class TestValidInputs:
    """Test cases for valid CLI inputs."""
    
    def test_valid_inputs_print_values(self):
        """Valid inputs should print temperature, pressure, and molecules."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "273",
            "--pressure", "0.1",
            "--nmolecules", "100"
        )
        
        assert returncode == 0
        assert "Temperature: 273.0K" in stdout
        assert "Pressure: 0.1 MPa" in stdout
        assert "Molecules: 100" in stdout
```

**E2E Tests:**
- Framework: Subprocess execution of CLI commands
- Approach: Test complete user workflows from CLI invocation to output validation
- Examples: `test_integration_v35.py` validates GROMACS file format

**Example from `tests/test_integration_v35.py`:**
```python
def validate_gro_file(filepath: Path) -> dict:
    """Validate a GROMACS .gro file.
    
    Parses and validates GROMACS .gro file format:
    - Line 1: Title (free format)
    - Line 2: Number of atoms (integer)
    - Lines 3 to N+2: Atom records (fixed format, 44+ chars)
    - Line N+3: Box vectors (3 for orthogonal, 9 for triclinic)
    """
    # ... validation logic ...
    return {
        'valid': bool,
        'atom_count': int,
        'box_dimensions': tuple,
        'errors': list,
        'coordinates': list
    }
```

## Common Patterns

**Async Testing:**
- Not applicable (synchronous codebase)

**Error Testing:**
```python
def test_rejects_negative_temperature(self):
    """Temperature -1K should be rejected."""
    with pytest.raises(ArgumentTypeError) as exc_info:
        validate_temperature("-1")
    assert "temperature" in str(exc_info.value).lower()
```

**Boundary Testing:**
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

**Array Comparison:**
```python
def test_supercell_exact_multiple(self):
    """Target exactly 128 molecules should return 2x2x2."""
    supercell, actual = calculate_supercell(128, 16)
    expected_matrix = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
    np.testing.assert_array_equal(supercell, expected_matrix)
    assert actual == 128
```

**File Output Validation:**
```python
def test_gro_file_format_validation(self):
    """Validate generated GROMACS .gro files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir)
        # Generate file
        write_gro_file(candidate, str(output_path / "test.gro"))
        # Validate format
        result = validate_gro_file(output_path / "test.gro")
        assert result['valid']
        assert result['atom_count'] == expected_count
```

**CLI Integration Testing:**
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

## Test Data Files

**Location:**
- Test data in `tests/test_output/` directory
- Sample output files for validation
- Temporary directories created with `tempfile.TemporaryDirectory()`

**Pattern:**
- Use `tempfile.TemporaryDirectory()` for test output
- Clean up automatic on context exit
- No persistent test artifacts

## Continuous Integration

**CI Status:**
- No automated test runs in CI
- GitHub Actions workflow only builds Windows executable
- Tests must be run manually: `pytest tests/`

**Recommendation:** Add CI workflow to run tests on pull requests:
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: conda-incubator/setup-miniconda@v3
        with:
          environment-file: environment.yml
      - shell: bash -el {0}
        run: pytest tests/
```

---

*Testing analysis: 2026-05-02*
