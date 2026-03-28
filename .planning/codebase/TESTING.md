# Testing Patterns

**Analysis Date:** 2026-03-28

## Test Framework

**Runner:**
- pytest >= 9.0.0
- Config: No explicit pytest config (no `pytest.ini`, `pyproject.toml` with `[tool.pytest]`)
- Location: `requirements-dev.txt`

**Assertion Library:**
- Built-in `assert` statements
- `pytest.raises()` for exception testing
- `np.testing.assert_allclose()` for numerical comparisons

**Run Commands:**
```bash
pytest                           # Run all tests
pytest tests/test_validators.py  # Run specific test file
pytest -v                        # Verbose output
pytest -x                        # Stop on first failure
```

## Test File Organization

**Location:**
- Separate `tests/` directory at project root
- Mirrors source structure for sub-packages: `tests/test_output/`

**Naming:**
- Test files: `test_{module}.py` (e.g., `test_validators.py`, `test_ranking.py`)
- Test classes: `Test{FeatureName}` (e.g., `TestValidateTemperature`, `TestRankCandidates`)
- Test methods: `test_{behavior}` (e.g., `test_accepts_valid_minimum_boundary`)

**Structure:**
```
tests/
├── __init__.py
├── test_validators.py
├── test_cli_integration.py
├── test_phase_mapping.py
├── test_structure_generation.py
├── test_ranking.py
└── test_output/
    ├── __init__.py
    ├── test_validator.py
    └── test_pdb_writer.py
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
- Class docstring describes the feature being tested
- Method docstring describes the expected behavior
- Method name clearly states what is being tested
- One assertion concept per test (boundary, valid input, invalid input)

## Mocking

**Framework:** 
- No explicit mocking library detected
- Tests use real implementations (not mocked)

**Patterns:**
```python
# Tests use real data structures rather than mocks
@pytest.fixture
def simple_candidate():
    """Create a simple candidate for testing."""
    positions = np.array([...])
    atom_names = ['O', 'H', 'H', ...]
    cell = np.eye(3) * 1.0
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=4,
        phase_id='ice_ih',
        seed=1000,
        metadata={'density': 0.9167}
    )
```

**What to Mock:**
- External API calls (not present in this codebase)
- File system operations (optional - tests can use temp directories)

**What NOT to Mock:**
- Internal module functions
- Data structures
- NumPy operations

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def candidate_set():
    """Create a set of candidates for ranking tests."""
    candidates = []
    for i in range(5):
        positions = np.array([...])
        atom_names = ['O', 'H', 'H'] * 4
        cell = np.eye(3) * 1.0
        candidates.append(Candidate(
            positions=positions,
            atom_names=atom_names,
            cell=cell,
            nmolecules=4,
            phase_id='ice_ih',
            seed=1000 + i,
            metadata={'density': 0.9167}
        ))
    return candidates
```

**Location:**
- Fixtures defined in test files
- Shared fixtures can be in `conftest.py` (not present - each file has its own)

**Fixture Patterns:**
- `simple_candidate`: Basic test data
- `ideal_candidate`: Data with ideal properties
- `candidate_set`: Multiple items for batch testing
- Edge case fixtures: `overlapping_candidate`, `single_candidate`

## Coverage

**Requirements:** Not enforced

**View Coverage:**
```bash
pytest --cov=quickice --cov-report=html
```

**Note:** Coverage plugin not in requirements-dev.txt

## Test Types

**Unit Tests:**
- Focus on single functions/methods
- Test valid inputs, boundary values, invalid inputs
- Located in `tests/test_*.py`

```python
class TestNormalizeScores:
    """Tests for normalize_scores function."""
    
    def test_normalize_scores_basic(self):
        """Test basic normalization: [1, 2, 3] -> [0, 0.5, 1]."""
        scores = [1.0, 2.0, 3.0]
        result = normalize_scores(scores)
        np.testing.assert_allclose(result, [0.0, 0.5, 1.0])
```

**Integration Tests:**
- Test multiple components working together
- Located in dedicated test classes or files
- Examples: `TestCLIIntegration`, `TestIntegrationWithPhase2`

```python
class TestCLIIntegration:
    """Integration tests for CLI phase output."""

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
```

**E2E Tests:**
- CLI integration tests use subprocess to run actual script
- No separate E2E framework

## Common Patterns

**Async Testing:**
- Not used in this codebase (no async code)

**Error Testing:**
```python
def test_rejects_negative_temperature(self):
    """Temperature -1K should be rejected."""
    with pytest.raises(ArgumentTypeError) as exc_info:
        validate_temperature("-1")
    assert "temperature" in str(exc_info.value).lower()

def test_lookup_unknown_region_high_temp_low_pressure(self):
    """Temperature 500K, Pressure 500 MPa should raise UnknownPhaseError."""
    with pytest.raises(UnknownPhaseError) as exc_info:
        lookup_phase(500, 500)
    assert "500" in str(exc_info.value)
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

def test_rejects_temperature_above_maximum(self):
    """Temperature 501K should be rejected."""
    with pytest.raises(ArgumentTypeError):
        validate_temperature("501")
```

**Numerical Comparisons:**
```python
# Use numpy for array comparisons
np.testing.assert_array_equal(supercell, expected_matrix)
np.testing.assert_allclose(result, [0.0, 0.5, 1.0])

# For single values
assert score < 10.0
assert result == 0.0
```

**CLI Testing:**
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
```

## Test Organization by Feature

**Validation Tests (`test_validators.py`):**
- Input validation for temperature, pressure, molecule count
- Boundary value testing
- Type validation

**Phase Mapping Tests (`test_phase_mapping.py`):**
- Phase lookup for various T/P conditions
- Unknown region handling
- Curve-based boundary verification
- Return value structure tests

**Structure Generation Tests (`test_structure_generation.py`):**
- Phase-to-GenIce mapping
- Supercell calculation
- Generator class behavior
- Integration with phase lookup

**Ranking Tests (`test_ranking.py`):**
- Individual score functions (energy, density, diversity)
- Score normalization
- Rank assignment
- Edge cases (empty lists, equal scores)

**Output Tests (`tests/test_output/`):**
- Space group validation
- Atomic overlap detection
- PDB writing

## Best Practices Observed

1. **Descriptive test names** that explain the expected behavior
2. **One concept per test** - don't test multiple things in one test
3. **Boundary testing** - test min, max, and just outside boundaries
4. **Error message verification** - check that error messages contain useful information
5. **Integration tests** - verify components work together
6. **Fixtures** - create reusable test data
7. **Class organization** - group related tests by feature

---

*Testing analysis: 2026-03-28*
