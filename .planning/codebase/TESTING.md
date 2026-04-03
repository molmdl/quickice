# Testing Patterns

**Analysis Date:** 2025-04-04

## Test Framework

**Runner:**
- pytest >= 9.0.0
- No pytest.ini or pyproject.toml configuration detected
- Default pytest discovery

**Run Commands:**
```bash
pytest                          # Run all tests
pytest tests/test_validators.py # Run specific file
pytest -v                       # Verbose output
pytest -x                       # Stop on first failure
pytest --tb=short               # Short traceback format
```

**Dependencies:**
```
# requirements-dev.txt
pytest>=9.0.0
pyinstaller>=6.0
```

## Test File Organization

**Location:**
- Tests co-located in `tests/` directory at project root
- Separate from source code in `quickice/`

**Naming:**
- Pattern: `test_<module>.py`
- Example: `tests/test_validators.py` tests `quickice/validation/validators.py`

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
Tests are organized into classes by functionality. Each class tests one function or module.

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

**Naming Pattern:**
- Class: `Test<FunctionName>` or `Test<Feature>`
- Method: `test_<descriptive_name>`
- Docstring: Brief description of what's being tested

## Fixtures

**Test Data Creation:**
Use `@pytest.fixture` decorator for reusable test data.

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
```

**Fixture Usage:**
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

**Fixture Organization:**
- Local fixtures: Defined in same file as tests
- Multiple fixtures for different scenarios: `simple_candidate`, `ideal_candidate`, `overlapping_candidate`

## Mocking

**Not heavily used** - This codebase prefers real implementations for integration tests.

**Pattern for external dependencies:**
```python
# Subprocess-based CLI testing (no mocking)
def test_cli_ice_ih_output():
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

## Assertions

**Standard Assertions:**
```python
# Basic equality
assert result == expected

# Type checking
assert isinstance(result, float)

# Boolean checks
assert result is True
assert result is False
assert result is not None

# Container membership
assert "temperature" in result
assert "phase_id" in result
```

**NumPy Assertions:**
Use `np.testing.assert_allclose` for floating-point comparisons.

```python
import numpy as np

def test_normalize_scores_basic():
    """Test basic normalization: [1, 2, 3] -> [0, 0.5, 1]."""
    scores = [1.0, 2.0, 3.0]
    result = normalize_scores(scores)
    np.testing.assert_allclose(result, [0.0, 0.5, 1.0])

def test_supercell_calculation():
    """Test supercell returns correct matrix."""
    supercell, actual = calculate_supercell(100, 16)
    expected_matrix = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
    np.testing.assert_array_equal(supercell, expected_matrix)
    assert actual == 128
```

**Exception Testing:**
Use `pytest.raises` context manager.

```python
def test_rejects_negative_temperature(self):
    """Temperature -1K should be rejected."""
    with pytest.raises(ArgumentTypeError) as exc_info:
        validate_temperature("-1")
    assert "temperature" in str(exc_info.value).lower()

def test_lookup_unknown_region():
    """Unknown T,P conditions should raise UnknownPhaseError."""
    with pytest.raises(UnknownPhaseError) as exc_info:
        lookup_phase(500, 500)
    assert "500" in str(exc_info.value)  # T value in message

def test_rank_candidates_empty_list():
    """Empty candidate list should raise ValueError."""
    with pytest.raises(ValueError, match="zero-size array"):
        rank_candidates([])
```

## Test Types

### Unit Tests

Test individual functions in isolation with clear inputs/outputs.

```python
class TestCalculateSupercell:
    """Tests for supercell calculation."""

    def test_supercell_100_molecules_ice1h(self):
        """Target 100 molecules with ice1h (16 per unit cell)."""
        supercell, actual = calculate_supercell(100, 16)
        expected_matrix = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 128

    def test_supercell_exact_multiple(self):
        """Target exactly 128 molecules should return 2x2x2."""
        supercell, actual = calculate_supercell(128, 16)
        expected_matrix = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 128
```

### Integration Tests

Test module interactions and real workflows.

```python
class TestIntegrationWithPhase2:
    """Integration tests with Phase 2 lookup."""

    def test_integration_with_phase_lookup(self):
        """generate_candidates should work with Phase 2 lookup_phase output."""
        from quickice.phase_mapping import lookup_phase
        from quickice.structure_generation import generate_candidates

        # Get phase info from Phase 2
        phase_info = lookup_phase(273, 0)  # Ice Ih

        # Generate structures
        result = generate_candidates(phase_info, nmolecules=100)

        assert result.phase_id == "ice_ih"
        assert len(result.candidates) == 10
```

### CLI Integration Tests

Test the full CLI using subprocess.

```python
class TestCLIIntegration:
    """Integration tests for QuickIce CLI."""

    def test_cli_ice_ih_output(self):
        """CLI should show Ice Ih for T=273K, P=0MPa."""
        result = subprocess.run(
            [sys.executable, "quickice.py", 
             "--temperature", "273", "--pressure", "0", "--nmolecules", "100"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Ice Ih" in result.stdout
        assert "ice_ih" in result.stdout

    def test_cli_unknown_region_error(self):
        """CLI should show error for unknown T,P conditions."""
        result = subprocess.run(
            [sys.executable, "quickice.py",
             "--temperature", "500", "--pressure", "500", "--nmolecules", "100"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "No ice phase found" in result.stderr
```

## Coverage

**Requirements:** No coverage threshold enforced

**View Coverage:**
```bash
pytest --cov=quickice --cov-report=html
```

## Test Categories

### Boundary Tests

Test edge cases and boundary values.

```python
class TestValidateTemperature:
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

### Requirement Verification Tests

Tests that verify specific requirements.

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
            assert isinstance(rc.density_score, float)
            assert rc.density_score >= 0

    def test_RANK_03_diversity_scoring(self, candidate_set):
        """RANK-03: Verify candidates have diversity scores."""
        result = rank_candidates(candidate_set)
        for rc in result.ranked_candidates:
            assert hasattr(rc, 'diversity_score')
            assert 0 < rc.diversity_score <= 1.0
```

### Edge Case Tests

Test unusual inputs and corner cases.

```python
class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_energy_score_no_oxygen_pairs(self, single_candidate):
        """Test energy score with only one oxygen (no pairs)."""
        score = energy_score(single_candidate)
        assert score == float('inf')

    def test_rank_candidates_single_candidate(self, single_candidate):
        """Test handling of single candidate."""
        result = rank_candidates([single_candidate])
        assert len(result.ranked_candidates) == 1
        assert result.ranked_candidates[0].rank == 1

    def test_check_atomic_overlap_single_atom(self):
        """Test overlap check handles single atom."""
        single_atom = Candidate(
            positions=np.array([[0.0, 0.0, 0.0]]),
            atom_names=['O'],
            cell=np.eye(3) * 1.0,
            nmolecules=1,
            phase_id='ice_ih',
            seed=5000
        )
        result = check_atomic_overlap(single_atom)
        assert result is False  # Single atom cannot overlap
```

## Docstrings in Tests

Every test method has a docstring explaining:
1. What is being tested
2. Expected behavior

```python
def test_lookup_260_400_ice_v(self):
    """T=260K, P=400MPa should return ice_v (not ice_ii from overlap).

    This was a CRITICAL overlap error in the polygon-based approach.
    Ice V region: T(218-273K), P(344-626MPa)
    At T=260K, P=400MPa, we're clearly in Ice V region.

    The polygon-based approach incorrectly identified this as Ice II
    due to polygon overlap in the II-V boundary region.
    """
    result = lookup_phase(260, 400)
    assert result["phase_id"] == "ice_v"
```

## Common Patterns

### Testing Valid Inputs

```python
def test_accepts_valid_input(self):
    """Valid input should return expected result."""
    result = validate_temperature("300")
    assert result == 300.0
    assert isinstance(result, float)
```

### Testing Invalid Inputs

```python
def test_rejects_invalid_input(self):
    """Invalid input should raise appropriate error."""
    with pytest.raises(ArgumentTypeError) as exc_info:
        validate_temperature("abc")
    assert "number" in str(exc_info.value).lower()
```

### Testing Return Structure

```python
def test_return_contains_expected_keys(self):
    """Result should contain all required keys."""
    result = lookup_phase(250, 100)
    assert "phase_id" in result
    assert "phase_name" in result
    assert "density" in result
    assert "temperature" in result
    assert "pressure" in result
```

### Testing Reproducibility

```python
def test_generate_single_is_reproducible(self, phase_info_ice_ih):
    """Same seed should produce identical structures."""
    from quickice.structure_generation.generator import IceStructureGenerator

    gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)
    candidate1 = gen._generate_single(seed=1000)
    candidate2 = gen._generate_single(seed=1000)

    np.testing.assert_array_equal(candidate1.positions, candidate2.positions)
```

---

*Testing analysis: 2025-04-04*
