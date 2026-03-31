# Testing Patterns

**Analysis Date:** 2026-03-31

## Test Framework

**Runner:**
- pytest (version >= 9.0.0)
- No explicit pytest configuration file detected
- Uses pytest's automatic test discovery

**Assertion Library:**
- Standard pytest assertions
- `numpy.testing.assert_allclose` for numerical comparisons
- `pytest.raises` for exception testing

**Run Commands:**
```bash
pytest                              # Run all tests
pytest tests/                       # Run tests in directory
pytest tests/test_validators.py     # Run specific test file
pytest -v                           # Verbose output
pytest -k "test_name"                # Run tests matching pattern
```

## Test File Organization

**Location:**
- Tests co-located in dedicated `tests/` directory at project root
- Test modules mirror source structure: `tests/test_output/test_pdb_writer.py`
- Integration tests in `tests/test_cli_integration.py`

**Naming:**
- Test files: `test_<module_name>.py`
- Test classes: `Test<Feature>` (e.g., `TestValidateTemperature`, `TestRankCandidates`)
- Test methods: `test_<scenario>_<expected_result>` (e.g., `test_accepts_valid_minimum_boundary`)

**Structure:**
```
tests/
├── __init__.py
├── test_validators.py
├── test_ranking.py
├── test_phase_mapping.py
├── test_structure_generation.py
├── test_cli_integration.py
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
- Class-based test organization with descriptive class names
- Each test class tests one component/feature
- Test methods named descriptively with docstrings
- Group related tests in same class (e.g., `TestNormalizeScores`, `TestEnergyScore`, `TestRankCandidates`)

**Setup/Teardown:**
- Use pytest fixtures for test data setup
- No global setup/teardown detected
- Fixtures defined at module level or within test classes

## Mocking

**Framework:** No mocking framework explicitly used in current tests

**Patterns:**
- Tests use real implementations (integration-style testing)
- No `unittest.mock` or `pytest-mock` usage detected
- Test fixtures create minimal test data objects

**What to Mock:**
- External services (not applicable to this codebase)
- File I/O operations (use `tempfile` module for file tests)

**What NOT to Mock:**
- Internal module functions (test real implementation)
- Data classes and simple functions

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
```

**Location:**
- Fixtures defined at module level in test files
- Shared fixtures within test classes for related tests
- Phase-specific fixtures for different test scenarios (e.g., `phase_info_ice_ih`)

## Coverage

**Requirements:** No coverage target enforced

**View Coverage:**
```bash
pytest --cov=quickice          # With pytest-cov plugin (not installed)
pytest -v                      # Verbose output shows test counts
```

## Test Types

**Unit Tests:**
- Test individual functions in isolation
- Located in `tests/test_<module>.py` files
- Example: `tests/test_validators.py` tests input validation functions
- Example: `tests/test_ranking.py` tests scoring functions

**Integration Tests:**
- Test module interactions
- Located in `tests/test_structure_generation.py` (tests integration with GenIce)
- Located in `tests/test_cli_integration.py` (tests full CLI flow)

**E2E Tests:**
- CLI integration tests using subprocess
- Example from `tests/test_cli_integration.py`:
  ```python
  def test_cli_ice_ih_output(self):
      """CLI should show Ice Ih for T=273K, P=0MPa."""
      result = subprocess.run(
          [sys.executable, "quickice.py", "--temperature", "273", "--pressure", "0", "--nmolecules", "100"],
          capture_output=True,
          text=True,
      )
      assert result.returncode == 0
      assert "Ice Ih" in result.stdout
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

def test_lookup_unknown_region_high_temp_low_pressure(self):
    """Temperature 500K, Pressure 500 MPa should raise UnknownPhaseError."""
    with pytest.raises(UnknownPhaseError) as exc_info:
        lookup_phase(500, 500)
    assert "500" in str(exc_info.value)  # T value in message
    assert "500" in str(exc_info.value)  # P value in message
```

**Boundary Testing:**
- Tests explicitly cover boundary conditions
- Example: `test_accepts_valid_minimum_boundary`, `test_accepts_valid_maximum_boundary`
- Example: `test_rejects_count_below_minimum`, `test_rejects_count_above_maximum`

**Numerical Assertions:**
```python
def test_normalize_scores_basic(self):
    """Test basic normalization: [1, 2, 3] -> [0, 0.5, 1]."""
    scores = [1.0, 2.0, 3.0]
    result = normalize_scores(scores)
    
    np.testing.assert_allclose(result, [0.0, 0.5, 1.0])

def test_energy_score_ideal_distance(self, ideal_candidate):
    """Test that structure near ideal 0.276nm gives low score."""
    score = energy_score(ideal_candidate)
    assert score < 10.0  # Should be relatively low
```

**File Testing:**
```python
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
    finally:
        Path(filepath).unlink(missing_ok=True)
```

## Test Organization Principles

**Requirement-Based Tests:**
- Tests organized by requirements (e.g., `RANK-01`, `RANK-02`)
- Example from `tests/test_ranking.py`:
  ```python
  class TestRequirements:
      """Tests verifying all 4 ranking requirements."""

      def test_RANK_01_energy_ranking(self, candidate_set):
          """RANK-01: Verify candidates have energy scores."""
          result = rank_candidates(candidate_set)
          for rc in result.ranked_candidates:
              assert hasattr(rc, 'energy_score')

      def test_RANK_02_density_scoring(self, candidate_set):
          """RANK-02: Verify candidates have density scores."""
          # ...
  ```

**Edge Case Testing:**
- Dedicated test classes for edge cases
- Example: `TestEdgeCases` class in `tests/test_ranking.py`
- Tests for empty inputs, single values, infinity handling

**Descriptive Test Names:**
- Test names describe scenario and expected outcome
- Pattern: `test_<function>_<scenario>_<expected>`
- Example: `test_lookup_260_400_ice_v` (documents fixed bug)

**Bug Regression Tests:**
- Tests document specific bug fixes
- Example from `tests/test_phase_mapping.py`:
  ```python
  class TestPolygonOverlapFixes:
      """Tests that verify curve-based lookup fixes polygon overlap errors.

      These tests document specific cases where the old polygon-based approach
      had overlapping regions causing incorrect phase identification.

      CRITICAL: These tests MUST pass to verify the curve-based approach works.
      """

      def test_lookup_260_400_ice_v(self):
          """T=260K, P=400MPa should return ice_v (not ice_ii from overlap)."""
          result = lookup_phase(260, 400)
          assert result["phase_id"] == "ice_v"
  ```

---

*Testing analysis: 2026-03-31*