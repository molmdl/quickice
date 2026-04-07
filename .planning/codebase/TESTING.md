# Testing Patterns

**Analysis Date:** 2026-04-07

## Test Framework

**Runner:**
- pytest 9.0.2
- No explicit config file (no pytest.ini, pyproject.toml pytest section)
- Python 3.14.3

**Assertion Library:**
- Standard pytest assertions: `assert result == expected`
- NumPy-specific assertions: `np.testing.assert_array_equal()`, `np.testing.assert_allclose()`

**Run Commands:**
```bash
pytest                           # Run all tests
pytest tests/test_validators.py  # Run specific file
pytest -v                        # Verbose output
pytest -k "test_name"            # Run tests matching pattern
```

## Test File Organization

**Location:**
- Tests in separate `tests/` directory at project root
- Test subdirectories mirror source structure: `tests/test_output/`
- No co-located tests (all tests in `tests/`)

**Naming:**
- Test files: `test_*.py` (e.g., `test_validators.py`, `test_ranking.py`)
- Test classes: `Test*` (e.g., `TestValidateTemperature`, `TestRankCandidates`)
- Test functions: `test_*` (e.g., `test_accepts_valid_minimum_boundary`)

**Structure:**
```
tests/
├── __init__.py
├── test_cli_integration.py      # CLI integration tests
├── test_validators.py           # CLI validator unit tests
├── test_phase_mapping.py        # Phase mapping tests
├── test_structure_generation.py # Structure generation tests
├── test_ranking.py              # Ranking/scoring tests
└── test_output/
    ├── __init__.py
    ├── test_validator.py        # Output validation tests
    └── test_pdb_writer.py       # PDB writer tests
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
- Class-based organization by functionality
- Descriptive test names that explain expected behavior
- Docstrings in tests describing what's being tested
- One assertion concept per test (boundary tests separate)

## Mocking

**Framework:** No explicit mocking detected

**Patterns:**
Tests use real objects rather than mocks:
- Real `Candidate` dataclass instances created in fixtures
- Real GenIce integration in structure generation tests
- Real file I/O in output tests (with cleanup)

**What to Test Without Mocks:**
- Data transformations and calculations
- Validation logic
- File writing operations (with temp directories)

**When Mocks Would Be Needed:**
- External API calls (not present in current tests)
- Slow operations (tests use small molecule counts)
- GUI components (PySide6 tests not present)

## Fixtures and Factories

**Test Data:**
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
    atom_names = ['O', 'H', 'H', 'O', 'H', 'H', 'O', 'H', 'H', 'O', 'H', 'H']
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

**Location:**
- Fixtures defined at class level (method scope) or module level
- No shared `conftest.py` file
- Fixtures named descriptively: `simple_candidate`, `ideal_candidate`, `overlapping_candidate`

**Fixture Patterns:**
- Create realistic test data inline
- Multiple fixtures for different scenarios: `simple_candidate`, `ideal_candidate`, `candidate_set`
- Docstrings explain what the fixture provides

## Coverage

**Requirements:** None enforced in configuration

**View Coverage:**
```bash
pytest --cov=quickice           # Coverage with pytest-cov plugin
pytest --cov=quickice --cov-report=html  # HTML report
```

**Current State:**
- 220 tests collected
- Tests cover validators, phase mapping, structure generation, ranking, output
- Integration tests for CLI

## Test Types

**Unit Tests:**
- Pure function testing (validators, scorers)
- Dataclass creation and validation
- Calculation correctness
- Boundary value testing

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
- CLI subprocess testing:
```python
def run_cli(*args: str) -> tuple[int, str, str]:
    """Run quickice.py with given arguments."""
    cmd = [sys.executable, str(QUICKICE_SCRIPT)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return result.returncode, result.stdout, result.stderr
```

- End-to-end flows:
```python
class TestIntegrationWithPhase2:
    """Integration tests with Phase 2 lookup."""
    
    def test_integration_with_phase_lookup(self):
        """generate_candidates should work with Phase 2 lookup_phase output."""
        from quickice.phase_mapping import lookup_phase
        from quickice.structure_generation import generate_candidates
        
        phase_info = lookup_phase(273, 0)  # Ice Ih
        result = generate_candidates(phase_info, nmolecules=100)
        
        assert result.phase_id == "ice_ih"
        assert len(result.candidates) == 10
```

**E2E Tests:**
- CLI integration tests using subprocess
- Full workflow from CLI args to output files
- Tests verify both success and error cases

## Common Patterns

**Async Testing:**
- Not used (no async code in codebase)

**Error Testing:**
```python
def test_rejects_negative_temperature(self):
    """Temperature -1K should be rejected."""
    with pytest.raises(ArgumentTypeError) as exc_info:
        validate_temperature("-1")
    assert "temperature" in str(exc_info.value).lower()

def test_lookup_unknown_region(self):
    """Unknown conditions should raise UnknownPhaseError."""
    with pytest.raises(UnknownPhaseError) as exc_info:
        lookup_phase(500, 500)
    assert "500" in str(exc_info.value)
```

**Boundary Testing:**
```python
class TestValidateNmolecules:
    """Tests for molecule count validation."""
    
    def test_accepts_valid_minimum_boundary(self):
        """Molecule count 4 should be accepted."""
        result = validate_nmolecules("4")
        assert result == 4
    
    def test_accepts_valid_maximum_boundary(self):
        """Molecule count 100000 should be accepted."""
        result = validate_nmolecules("100000")
        assert result == 100000
    
    def test_rejects_count_below_minimum(self):
        """Molecule count 3 should be rejected."""
        with pytest.raises(ArgumentTypeError):
            validate_nmolecules("3")
```

**NumPy Array Testing:**
```python
def test_positions_within_cell(self, phase_info_ice_ih):
    """All atom positions should be within cell bounds."""
    gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)
    candidate = gen._generate_single(seed=1000)
    
    cell_x = candidate.cell[0, 0]
    assert np.all(candidate.positions[:, 0] <= cell_x * 1.01)

def test_supercell_calculation(self):
    """Verify supercell matrix calculation."""
    np.testing.assert_array_equal(supercell, expected_matrix)
```

**Test Organization by Feature:**
```python
class TestLookupPhaseIceIh:
    """Tests for Ice Ih lookups."""
    
class TestLookupPhaseIceVii:
    """Tests for Ice VII lookups."""
    
class TestPolygonOverlapFixes:
    """Tests that verify curve-based lookup fixes."""
```

## Test Data Patterns

**Creating Test Objects:**
```python
# Direct dataclass instantiation
candidate = Candidate(
    positions=np.array([[0.0, 0.0, 0.0]]),
    atom_names=["O"],
    cell=np.eye(3),
    nmolecules=1,
    phase_id="ice_ih",
    seed=0,
    metadata={"density": 0.9167}
)

# Using fixtures for common patterns
@pytest.fixture
def phase_info_ice_ih():
    return {
        "phase_id": "ice_ih",
        "phase_name": "Ice Ih",
        "density": 0.9167,
        "temperature": 273,
        "pressure": 0,
    }
```

**Assertion Patterns:**
```python
# Type checking
assert isinstance(result, float)
assert isinstance(candidate.positions, np.ndarray)

# Value checking
assert result["phase_id"] == "ice_ih"
assert candidate.nmolecules == 128

# Collection checking
assert len(result.candidates) == 10
assert "phase_id" in result

# Error message content
assert "temperature" in str(exc_info.value).lower()

# NumPy array comparison
np.testing.assert_array_equal(supercell, expected_matrix)
np.testing.assert_allclose(result, [0.0, 0.5, 1.0])
```

---

*Testing analysis: 2026-04-07*
