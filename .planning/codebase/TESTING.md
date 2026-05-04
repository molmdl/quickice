# Testing Patterns

**Analysis Date:** 2026-05-05

## Test Framework

**Runner:**
- pytest (version >= 9.0.0)
- Config: No pytest.ini or pyproject.toml with pytest config detected (uses pytest defaults)
- Test discovery: Automatic (test_*.py files in tests/ directory)

**Assertion Library:**
- pytest assertions (built-in `assert` statement)
- NumPy test utilities: `np.testing.assert_allclose()` for numerical comparisons

**Run Commands:**
```bash
pytest                           # Run all tests
pytest tests/test_validators.py  # Run specific test file
pytest -v                        # Verbose output
pytest -x                        # Stop on first failure
pytest -k "temperature"          # Run tests matching pattern
```

## Test File Organization

**Location:**
- Tests are in separate `tests/` directory (not co-located with source)
- Mirror source structure: `tests/test_<module>.py` corresponds to `quickice/<module>/`

**Naming:**
- Test files: `test_<module_name>.py` (e.g., `test_validators.py`, `test_ranking.py`)
- Test classes: `Test<Feature>` (e.g., `TestValidateTemperature`, `TestRankCandidates`)
- Test methods: `test_<descriptive_name>()` (e.g., `test_accepts_valid_minimum_boundary()`)

**Structure:**
```
tests/
├── __init__.py
├── test_validators.py           # Tests for quickice/validation/
├── test_phase_mapping.py        # Tests for quickice/phase_mapping/
├── test_structure_generation.py # Tests for quickice/structure_generation/
├── test_ranking.py              # Tests for quickice/ranking/
├── test_cli_integration.py      # Integration tests for CLI
├── test_integration_v35.py      # Integration tests for v3.5 features
├── test_output/
│   └── test_output/             # Test output files
└── ...
```

**Test Statistics:**
- Total test files: 21 Python test files in `tests/`
- Total test functions: 335 test methods across all test files

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


class TestValidatePressure:
    """Tests for pressure validation."""
    
    def test_accepts_valid_minimum_boundary(self):
        """Pressure 0 MPa should be accepted."""
        result = validate_pressure("0")
        assert result == 0.0
        assert isinstance(result, float)
```

**Patterns:**
- Group related tests in a class named `Test<Feature>`
- Use descriptive test names that explain expected behavior
- Include docstrings for test methods
- Test both valid inputs (acceptance tests) and invalid inputs (rejection tests)

## Test Method Patterns

**Acceptance Tests:**
```python
def test_accepts_valid_minimum_boundary(self):
    """Temperature 0K should be accepted."""
    result = validate_temperature("0")
    assert result == 0.0
    assert isinstance(result, float)

def test_accepts_valid_middle_value(self):
    """Temperature 300K should be accepted."""
    result = validate_temperature("300")
    assert result == 300.0
    assert isinstance(result, float)
```

**Rejection Tests:**
```python
def test_rejects_negative_temperature(self):
    """Temperature -1K should be rejected."""
    with pytest.raises(ArgumentTypeError) as exc_info:
        validate_temperature("-1")
    assert "temperature" in str(exc_info.value).lower()

def test_rejects_non_numeric_input(self):
    """Non-numeric input should be rejected."""
    with pytest.raises(ArgumentTypeError) as exc_info:
        validate_temperature("abc")
    assert "temperature" in str(exc_info.value).lower()
```

**Equality Tests:**
```python
def test_ice_ih_maps_to_ice1h(self):
    """Phase ID 'ice_ih' should map to GenIce lattice 'ice1h'."""
    assert get_genice_lattice_name("ice_ih") == "ice1h"
```

**Numerical Comparison Tests:**
```python
def test_normalize_scores_basic(self):
    """Test basic normalization: [1, 2, 3] -> [0, 0.5, 1]."""
    scores = [1.0, 2.0, 3.0]
    result = normalize_scores(scores)
    np.testing.assert_allclose(result, [0.0, 0.5, 1.0])
```

## Fixtures

**Framework:** pytest `@pytest.fixture` decorator

**Patterns:**
```python
@pytest.fixture
def simple_candidate():
    """Create a simple candidate for testing.
    
    Creates a 1nm cubic cell with 4 water molecules.
    """
    positions = np.array([
        [0.0, 0.0, 0.0],    # O
        [0.1, 0.0, 0.0],    # H
        [-0.1, 0.0, 0.0],   # H
        # ... more atoms
    ])
    atom_names = ['O', 'H', 'H', 'O', 'H', 'H', ...]
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
        # Create candidate with varied parameters
        candidates.append(Candidate(...))
    return candidates
```

**Usage in Tests:**
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

**Fixture Naming:**
- Descriptive names: `simple_candidate`, `ideal_candidate`, `candidate_set`
- Document purpose in docstring
- Create reusable test data for common test scenarios

## Mocking

**Framework:** No external mocking library detected; uses helper functions to create test objects

**Patterns:**
- Create mock/test objects using helper functions instead of mocking
- Use real objects with controlled test data when possible

```python
def create_mock_ice_candidate(ice_atoms: int = 12) -> Candidate:
    """Create a simple mock ice candidate (GenIce style: 3 atoms per molecule O, H, H)."""
    positions = np.zeros((ice_atoms, 3))
    atom_names = ['O', 'H', 'H'] * (ice_atoms // 3)
    cell = np.eye(3) * 2.0
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=ice_atoms // 3,
        phase_id='ice_ih',
        seed=12345,
        metadata={'density': 0.9167}
    )

def create_mock_hydrate_candidate(n_water: int = 8, n_guest: int = 1) -> Candidate:
    """Create a mock hydrate candidate with water framework + guest molecules."""
    # Create water atoms (TIP4P: OW, HW1, HW2, MW)
    water_atoms = n_water * 4
    # Create guest atoms (CH4: C + 4H)
    guest_atoms = n_guest * 5
    
    positions = np.zeros((water_atoms + guest_atoms, 3))
    atom_names = (['OW', 'HW1', 'HW2', 'MW'] * n_water + 
                  ['C', 'H', 'H', 'H', 'H'] * n_guest)
    
    return Candidate(...)
```

**What to Mock:**
- External dependencies (GenIce, IAPWS) - use real calls when feasible, or create test fixtures
- File I/O - use temporary directories (see integration tests)
- User input - not typically mocked in this codebase

**What NOT to Mock:**
- Internal data structures (Candidate, InterfaceConfig)
- Business logic functions
- NumPy operations

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def simple_candidate():
    """Create a simple candidate for testing."""
    positions = np.array([
        [0.0, 0.0, 0.0],
        [0.1, 0.0, 0.0],
        [-0.1, 0.0, 0.0],
    ])
    atom_names = ['O', 'H', 'H']
    cell = np.eye(3) * 0.5
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=1,
        phase_id='ice_ih',
        seed=9999,
        metadata={'density': 0.9167}
    )
```

**Location:**
- Fixtures defined at module level in test files
- Reusable fixtures can be moved to `conftest.py` (not currently used)

## Coverage

**Requirements:** No coverage requirement enforced

**View Coverage:**
```bash
pytest --cov=quickice --cov-report=html
# Opens htmlcov/index.html
```

**Note:** Coverage tool not configured in requirements-dev.txt, would need to add `pytest-cov` package

## Test Types

**Unit Tests:**
- Test individual functions in isolation
- Examples: `test_validators.py`, `test_ranking.py`
- Focus on: input validation, boundary conditions, edge cases
- Fast execution (< 1 second per test)

**Integration Tests:**
- Test complete workflows
- Examples: `test_cli_integration.py`, `test_integration_v35.py`
- Use subprocess to run CLI
- Test file I/O with temporary directories
- Slower execution (may take several seconds)

**Example Integration Test:**
```python
def run_cli(*args: str) -> tuple[int, str, str]:
    """Run quickice.py with given arguments."""
    cmd = [sys.executable, str(QUICKICE_SCRIPT)] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60
    )
    return result.returncode, result.stdout, result.stderr

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
- Not explicitly separated from integration tests
- CLI integration tests cover end-to-end flows

## Common Patterns

**Async Testing:**
- Not applicable (no async code detected)

**Error Testing:**
```python
def test_unsupported_phase_raises_error(self):
    """Unsupported phase ID should raise UnsupportedPhaseError."""
    with pytest.raises(UnsupportedPhaseError) as exc_info:
        get_genice_lattice_name("ice_xxx")
    assert exc_info.value.phase_id == "ice_xxx"

def test_empty_candidate_list(self):
    """Test handling of empty candidate list."""
    with pytest.raises(ValueError, match="zero-size array"):
        rank_candidates([])
```

**Boundary Testing:**
```python
class TestValidateTemperature:
    """Tests for temperature validation."""
    
    def test_accepts_valid_minimum_boundary(self):
        """Temperature 0K should be accepted."""
        result = validate_temperature("0")
        assert result == 0.0
    
    def test_accepts_valid_maximum_boundary(self):
        """Temperature 500K should be accepted."""
        result = validate_temperature("500")
        assert result == 500.0
    
    def test_rejects_temperature_below_minimum(self):
        """Temperature -1K should be rejected."""
        with pytest.raises(ArgumentTypeError):
            validate_temperature("-1")
    
    def test_rejects_temperature_above_maximum(self):
        """Temperature 501K should be rejected."""
        with pytest.raises(ArgumentTypeError):
            validate_temperature("501")
```

**Comparison Testing:**
```python
def test_energy_score_lower_better(self, simple_candidate, ideal_candidate):
    """Test that better H-bond geometry gives lower score."""
    score_simple = energy_score(simple_candidate)
    score_ideal = energy_score(ideal_candidate)
    
    # Ideal candidate should have lower (better) energy score
    assert score_ideal < score_simple
```

**Result Validation:**
```python
def test_rank_candidates_returns_result(self, candidate_set):
    """Test that rank_candidates returns RankingResult."""
    result = rank_candidates(candidate_set)
    
    assert isinstance(result, RankingResult)
    assert len(result.ranked_candidates) == 5
    assert result.ranked_candidates[0].rank == 1
```

**Metadata Testing:**
```python
def test_rank_candidates_metadata(self, candidate_set):
    """Test that result includes scoring_metadata and weight_config."""
    result = rank_candidates(candidate_set)
    
    assert 'n_candidates' in result.scoring_metadata
    assert 'ideal_oo_distance' in result.scoring_metadata
    assert 'energy_range' in result.scoring_metadata
    assert 'density_range' in result.scoring_metadata
    assert 'diversity_range' in result.scoring_metadata
    
    assert result.weight_config is not None
```

## Test Organization Best Practices

**Class Naming:**
- Group related tests in a class: `TestValidateTemperature`, `TestRankCandidates`
- Use descriptive class names that indicate the feature being tested

**Test Method Naming:**
- Pattern: `test_<action>_<expected_outcome>`
- Examples:
  - `test_accepts_valid_minimum_boundary()` - acceptance test
  - `test_rejects_negative_temperature()` - rejection test
  - `test_lookup_atmospheric_near_melting()` - behavior test
  - `test_RANK_01_energy_ranking()` - requirement verification test

**Docstrings:**
- Include docstrings for all test methods
- Document expected behavior, not implementation details
- Example: `"""Temperature 0K should be accepted."""`

**Test Independence:**
- Each test should be independent and self-contained
- Use fixtures for shared setup
- No test should depend on another test's execution

**Setup/Teardown:**
- Not commonly used; fixtures preferred
- Use temporary directories for file I/O tests
```python
import tempfile
from pathlib import Path

def test_file_output():
    """Test file output functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.gro"
        # Test file creation
        assert output_path.exists()
```

## Testing Requirements

**Requirements Verification:**
Tests explicitly verify numbered requirements:
```python
class TestRequirements:
    """Tests verifying all 4 ranking requirements."""
    
    def test_RANK_01_energy_ranking(self, candidate_set):
        """RANK-01: Verify candidates have energy scores."""
        result = rank_candidates(candidate_set)
        for rc in result.ranked_candidates:
            assert hasattr(rc, 'energy_score')
            assert isinstance(rc.energy_score, float)
    
    def test_RANK_02_density_scoring(self, candidate_set):
        """RANK-02: Verify candidates have density scores."""
        result = rank_candidates(candidate_set)
        for rc in result.ranked_candidates:
            assert hasattr(rc, 'density_score')
            assert rc.density_score >= 0
```

**Edge Case Testing:**
```python
class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_rank_candidates_handles_infinite_energy(self):
        """Test that infinite energy scores are handled gracefully."""
        # Test with candidate that has no O-O pairs
        result = rank_candidates([normal, single_oxygen])
        assert len(result.ranked_candidates) == 2
        assert float('inf') in [rc.energy_score for rc in result.ranked_candidates]
    
    def test_all_scores_equal(self):
        """Test normalization when all scores are equal."""
        scores = [5.0, 5.0, 5.0, 5.0]
        result = normalize_scores(scores)
        np.testing.assert_allclose(result, [0.0, 0.0, 0.0, 0.0])
```

---

*Testing analysis: 2026-05-05*
