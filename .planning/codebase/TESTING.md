# Testing Patterns

**Analysis Date:** 2026-03-30

## Test Framework

**Runner:**
- pytest (version >= 9.0.0)
- No explicit configuration file (uses pytest defaults)
- Test discovery: files matching `tests/test_*.py`

**Assertion Library:**
- pytest assertions (no unittest.TestCase)
- `assert` statements for simple checks
- `pytest.raises()` for exception testing
- `np.testing.assert_allclose()` for numerical comparisons

**Run Commands:**
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_phase_mapping.py

# Run specific test class
pytest tests/test_phase_mapping.py::TestLookupPhaseIceIh

# Run specific test
pytest tests/test_phase_mapping.py::TestLookupPhaseIceIh::test_lookup_atmospheric_near_melting

# Verbose output
pytest -v

# With coverage (if configured)
pytest --cov=quickice
```

## Test File Organization

**Location:**
- Tests in `tests/` directory (separate from source)
- Mirror module structure: `tests/test_output/test_validator.py`

**Naming:**
- Test files: `test_<module>.py`
- Test classes: `Test<FeatureName>`
- Test methods: `test_<scenario>`

**Structure:**
```
tests/
├── __init__.py
├── test_phase_mapping.py
├── test_validators.py
├── test_structure_generation.py
├── test_ranking.py
├── test_cli_integration.py
└── test_output/
    ├── __init__.py
    ├── test_validator.py
    └── test_pdb_writer.py
```

## Test Structure

**Suite Organization:**
```python
"""Tests for phase mapping lookup functionality."""

import subprocess
import sys

import pytest
from quickice.phase_mapping.lookup import lookup_phase, IcePhaseLookup
from quickice.phase_mapping.errors import UnknownPhaseError


class TestLookupPhaseIceIh:
    """Tests for Ice Ih (normal atmospheric ice) lookups."""

    def test_lookup_atmospheric_near_melting(self):
        """Temperature 273K, Pressure 0 MPa should return ice_ih."""
        result = lookup_phase(273, 0)
        assert result["phase_id"] == "ice_ih"
        assert result["phase_name"] == "Ice Ih"
        assert result["density"] == 0.9167
        assert result["temperature"] == 273
        assert result["pressure"] == 0

    def test_lookup_normal_conditions(self):
        """Temperature 250K, Pressure 100 MPa should return ice_ih."""
        result = lookup_phase(250, 100)
        assert result["phase_id"] == "ice_ih"
        assert result["phase_name"] == "Ice Ih"
```

**Patterns:**
- One test class per feature/function group
- Docstrings describe what is being tested
- Clear test names: `test_<function>_<scenario>`
- Each test verifies one specific behavior

## Mocking

**Framework:**
- No mocking framework detected
- Real objects used (fixtures create test data)
- Subprocess used for CLI integration tests

**What to Mock:**
- External dependencies (none detected in current tests)
- File I/O uses temp files instead of mocking

**What NOT to Mock:**
- Domain objects (use fixtures)
- Pure functions (test with real implementation)
- Database/network calls (not present in this codebase)

**CLI Integration Test Pattern:**
```python
def run_cli(*args: str) -> tuple[int, str, str]:
    """Run quickice.py with given arguments."""
    cmd = [sys.executable, str(QUICKICE_SCRIPT)] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10
    )
    return result.returncode, result.stdout, result.stderr


class TestValidInputs:
    """Test cases for valid CLI inputs."""

    def test_valid_inputs_print_values(self):
        """Valid inputs should print temperature, pressure, and molecules."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "300",
            "--pressure", "100",
            "--nmolecules", "100"
        )
        
        assert returncode == 0
        assert "Temperature: 300.0K" in stdout
        assert "Pressure: 100.0 MPa" in stdout
        assert "Molecules: 100" in stdout
```

## Fixtures and Factories

**Test Data:**
- Use `@pytest.fixture` decorator for reusable test data
- Fixtures defined at module level
- Descriptive fixture names: `simple_candidate`, `ideal_candidate`, `candidate_set`

**Pattern:**
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
        # Molecule 2: O at 0.28nm
        [0.28, 0.0, 0.0],   # O
        [0.38, 0.0, 0.0],   # H
        [0.18, 0.0, 0.0],   # H
        # ... more molecules
    ])
    atom_names = ['O', 'H', 'H', 'O', 'H', 'H', 'O', 'H', 'H', 'O', 'H', 'H']
    cell = np.eye(3) * 1.0  # 1nm cubic cell
    
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
def candidate_set():
    """Create a set of candidates for ranking tests."""
    candidates = []
    for i in range(5):
        # Create candidates with varied positions
        positions = create_positions(i)
        candidates.append(Candidate(
            positions=positions,
            atom_names=['O', 'H', 'H'] * 4,
            cell=np.eye(3) * 1.0,
            nmolecules=4,
            phase_id='ice_ih',
            seed=1000 + i,
            metadata={'density': 0.9167}
        ))
    return candidates
```

**Location:**
- Fixtures defined at top of test file
- Shared fixtures could go in `conftest.py` (not currently used)

## Coverage

**Requirements:**
- No coverage target enforced
- Comprehensive test coverage observed

**View Coverage:**
```bash
pytest --cov=quickice --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Types

**Unit Tests:**
- Test individual functions in isolation
- Use fixtures for test data
- No external dependencies
- Fast execution

**Example from `test_validators.py`:**
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

**Integration Tests:**
- Test module interactions
- Located in `test_cli_integration.py`
- Use subprocess for CLI testing

**Example from `test_cli_integration.py`:**
```python
class TestValidInputs:
    """Test cases for valid CLI inputs."""

    def test_valid_inputs_print_values(self):
        """Valid inputs should print temperature, pressure, and molecules."""
        returncode, stdout, stderr = run_cli(
            "--temperature", "300",
            "--pressure", "100",
            "--nmolecules", "100"
        )
        
        assert returncode == 0
        assert "Temperature: 300.0K" in stdout
```

**E2E Tests:**
- Not explicitly separated from integration tests
- Full pipeline tests in `test_cli_integration.py`

## Common Patterns

**Exception Testing:**
```python
def test_lookup_unknown_region_high_temp_low_pressure(self):
    """Temperature 500K, Pressure 500 MPa should raise UnknownPhaseError."""
    with pytest.raises(UnknownPhaseError) as exc_info:
        lookup_phase(500, 500)
    assert "500" in str(exc_info.value)  # T value in message
    assert "500" in str(exc_info.value)  # P value in message
```

**Numerical Assertions:**
```python
def test_supercell_100_molecules_ice1h(self):
    """Target 100 molecules with ice1h (16 per unit cell) should return 2x2x2."""
    supercell, actual = calculate_supercell(100, 16)
    expected_matrix = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
    np.testing.assert_array_equal(supercell, expected_matrix)
    assert actual == 128
```

**Array/Structure Assertions:**
```python
def test_candidate_creation(self):
    """Candidate should be creatable with all required fields."""
    candidate = Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=1,
        phase_id="ice_ih",
        seed=42
    )

    assert candidate.nmolecules == 1
    assert candidate.phase_id == "ice_ih"
    np.testing.assert_array_equal(candidate.positions, positions)
```

**Fixture Usage in Tests:**
```python
class TestEnergyScore:
    """Tests for energy_score function."""

    def test_energy_score_returns_float(self, simple_candidate):
        """Test that energy_score returns a float."""
        result = energy_score(simple_candidate)
        assert isinstance(result, float)

    def test_energy_score_lower_better(self, simple_candidate, ideal_candidate):
        """Test that better H-bond geometry gives lower score."""
        score_simple = energy_score(simple_candidate)
        score_ideal = energy_score(ideal_candidate)
        assert score_ideal < score_simple
```

**File I/O Testing:**
```python
def test_creates_valid_pdb_file(self, simple_candidate):
    """Test that function creates a valid PDB file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pdb', delete=False) as f:
        filepath = f.name
    
    try:
        write_pdb_with_cryst1(simple_candidate, filepath)
        
        assert Path(filepath).exists()
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        assert 'CRYST1' in content
        assert 'ATOM' in content or 'HETATM' in content
        assert 'END' in content
    finally:
        Path(filepath).unlink(missing_ok=True)
```

**Parametrized Tests:**
- Not currently used, but pytest.mark.parametrize is available

## Test Organization Guidelines

**Naming Convention:**
- Test class per feature: `Test<FeatureName>`
- Test method describes scenario: `test_<function>_<scenario>`
- Docstring describes what is being tested

**Test Grouping:**
- Group related tests in classes
- Use descriptive class names: `TestLookupPhaseIceIh`, `TestPolygonOverlapFixes`
- Use sections in test files for different test groups

**Example Organization:**
```python
class TestLookupPhaseIceIh:
    """Tests for Ice Ih (normal atmospheric ice) lookups."""
    # Tests for Ice Ih...


class TestLookupPhaseIceVii:
    """Tests for Ice VII (high pressure, high temperature) lookups."""
    # Tests for Ice VII...


class TestCurveBasedPhaseLookup:
    """Comprehensive tests for curve-based phase lookup."""
    # Tests for algorithm...


class TestLookupPhaseUnknown:
    """Tests for conditions outside known phase regions."""
    # Tests for error cases...
```

---

*Testing analysis: 2026-03-30*