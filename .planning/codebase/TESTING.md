# Testing Patterns

**Analysis Date:** 2026-04-10

## Test Framework

**Runner:**
- pytest (>=9.0.0 per `requirements-dev.txt`)
- No `conftest.py` detected at project root or test directories
- No `pytest.ini` or `pyproject.toml` pytest config detected

**Assertion Library:**
- `pytest` assertions (native `assert` statements)
- `numpy.testing.assert_array_equal` for NumPy array comparisons
- `numpy.testing.assert_allclose` for floating-point comparisons
- No `unittest.TestCase` usage — all tests are pytest-style

**Run Commands:**
```bash
pytest                          # Run all tests
pytest tests/test_validators.py # Run specific test file
pytest tests/test_ranking.py -k "test_energy_score"  # Run specific test
pytest tests/test_phase_mapping.py::TestLookupPhaseIceIh  # Run specific class
pytest -x                       # Stop on first failure
pytest -v                       # Verbose output
```

## Test File Organization

**Location:**
- Tests are in a separate `tests/` directory at project root (not co-located with source)
- Test output files in `tests/test_output/` subdirectory for PDB writer tests

**Naming:**
- Test files: `test_<module_name>.py` — e.g., `test_validators.py`, `test_ranking.py`, `test_phase_mapping.py`
- Test classes: `Test<FeatureName>` — e.g., `TestValidateTemperature`, `TestEnergyScore`, `TestLookupPhaseIceIh`
- Test methods: `test_<behavior_description>` — e.g., `test_accepts_valid_minimum_boundary`, `test_rejects_negative_temperature`

**Structure:**
```
tests/
├── __init__.py                           # Package marker
├── test_validators.py                    # CLI input validators
├── test_cli_integration.py               # Full CLI subprocess tests
├── test_phase_mapping.py                # Phase mapping + CLI integration
├── test_structure_generation.py          # Core generation + mapper + types
├── test_ranking.py                       # Scoring + ranking + normalization
├── test_pbc_hbonds.py                   # PBC-aware hydrogen bond detection
├── test_atom_ordering_validation.py       # VTK atom ordering validation
├── test_interface_ordering_validation.py  # Interface atom ordering validation
├── test_piece_mode_validation.py          # Piece mode water layer validation
├── test_med03_minimum_box_size.py        # Minimum box size validation
└── test_output/
    ├── __init__.py                       # Empty
    ├── test_pdb_writer.py                # PDB format output tests
    └── test_validator.py                 # Structure validation (spglib, overlap)
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
- Each test class groups related tests (by function or feature)
- Class names use `Test` prefix with `PascalCase`
- Test method names use `test_` prefix with `snake_case`
- Docstrings describe expected behavior in sentence form: `"Temperature 0K should be accepted."`
- Arrange-Act-Assert pattern used consistently
- Boundary value testing: tests for minimum, maximum, and just-outside-boundary values

**Setup/Teardown:**
- `pytest.fixture` for shared test data creation
- No `setup_module`, `setup_class`, or `setUp` methods
- Fixtures defined at module level (not in conftest.py)

## Mocking

**Framework:** No mocking framework detected. Tests use real objects and actual function calls.

**Patterns:**
- No `unittest.mock`, `pytest-mock`, or similar mocking libraries used
- CLI integration tests use `subprocess.run()` to test the actual CLI
- Structure generation tests call real GenIce generation (no mocking)
- Ranking tests create `Candidate` objects with known positions for deterministic scoring

**What to Mock:**
- NOT MOCKED: `lookup_phase()`, `generate_candidates()`, `rank_candidates()` — tested with real calls
- NOT MOCKED: GenIce lattice generation — integration tests generate real structures
- NO MOCKING PATTERN ESTABLISHED — the project has no mocking convention

**What NOT to Mock:**
- Pure computation functions (scoring, normalization) — tested with crafted inputs
- Validation functions — tested directly with string inputs
- CLI parsers — tested via subprocess for full integration

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
- Fixtures defined inline in each test file (no `conftest.py`)
- Common fixture pattern: create `Candidate` or `InterfaceConfig` with known, simple values
- Multiple fixture variants for different scenarios: `simple_candidate`, `ideal_candidate`, `candidate_set`, `candidate_with_duplicate_seeds`
- Fixture names are descriptive: `simple_candidate`, `overlapping_candidate`, `pbc_overlap_candidate`, `well_spaced_candidate`

**Factory Patterns:**
- Direct `Candidate()` construction with known `numpy` arrays
- `phase_info_ice_ih` fixture creates dict matching `lookup_phase()` output format
- `ranking_result` fixture in `test_pdb_writer.py` creates a `RankingResult` with 12 candidates for output testing

**Key Fixture Naming Convention:**
- `simple_candidate` — minimal valid test data
- `ideal_candidate` — data matching ideal values (e.g., O-O distance of 0.276 nm)
- `candidate_set` — collection of 5 candidates for ranking tests
- `overlapping_candidate` — data designed to trigger a specific condition
- `pbc_overlap_candidate` — data for periodic boundary condition tests
- `ice_ih_candidate` — data specific to Ice Ih phase
- `triclinic_candidate` — data with non-orthogonal cell

## Coverage

**Requirements:** No coverage target enforced. No `.coveragerc` or `pytest --cov` configuration detected.

**View Coverage:**
```bash
pytest --cov=quickice --cov-report=term-missing  # Would need pytest-cov installed
```

**Coverage Gaps Observed:**
- GUI code (`quickice/gui/`) has NO direct tests — GUI testing requires Qt environment
- `quickice/output/phase_diagram.py` — no direct unit tests
- `quickice/structure_generation/modes/` (slab, pocket, piece) — no direct unit tests
- `quickice/structure_generation/overlap_resolver.py` — no direct unit tests
- `quickice/structure_generation/water_filler.py` — no direct unit tests
- `quickice/output/gromacs_writer.py` — no direct unit tests
- `quickice/gui/export.py`, `quickice/gui/vtk_utils.py` — tested indirectly via `test_atom_ordering_validation.py` and `test_pbc_hbonds.py`

## Test Types

**Unit Tests:**
- `test_validators.py` — Pure function testing with string inputs and assertion checks
- `test_ranking.py` — Mathematical scoring functions with known-position Candidates
- `test_structure_generation.py` (types, mapper, supercell calculation) — Pure data/computation
- `test_output/test_validator.py` — Space group and overlap detection

**Integration Tests:**
- `test_structure_generation.py` (IceStructureGenerator, generate_candidates) — Tests real GenIce generation
- `test_phase_mapping.py::TestCLIIntegration` — Tests full CLI subprocess execution
- `test_phase_mapping.py::TestIntegrationWithPhase2` — Tests lookup + generation pipeline
- `test_cli_integration.py` — Full CLI subprocess tests with `subprocess.run()`
- `test_pdb_writer.py::TestWriteRankedCandidates` — Tests file I/O with temp directories

**E2E Tests:**
- Not formally structured as E2E tests, but `TestCLIIntegration` in `test_phase_mapping.py` and `test_cli_integration.py` serve this purpose by running the full CLI pipeline

## Common Patterns

**Async Testing:**
- Not used — no async code in the project

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

def test_rejects_temperature_above_maximum(self):
    """Temperature 501K should be rejected."""
    with pytest.raises(ArgumentTypeError) as exc_info:
        validate_temperature("501")
```

**NumPy Array Testing:**
```python
# Exact comparison for deterministic arrays
np.testing.assert_array_equal(candidate.positions, positions)

# Floating-point comparison for computed values
np.testing.assert_allclose(result, [0.0, 0.5, 1.0])
```

**File I/O Testing:**
```python
def test_creates_valid_pdb_file(self, simple_candidate):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pdb', delete=False) as f:
        filepath = f.name
    
    try:
        write_pdb_with_cryst1(simple_candidate, filepath)
        assert Path(filepath).exists()
        # ... verify content ...
    finally:
        Path(filepath).unlink(missing_ok=True)
```

**CLI Subprocess Testing:**
```python
def run_cli(*args: str) -> tuple[int, str, str]:
    cmd = [sys.executable, str(QUICKICE_SCRIPT)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return result.returncode, result.stdout, result.stderr

def test_valid_inputs_print_values(self):
    returncode, stdout, stderr = run_cli(
        "--temperature", "300",
        "--pressure", "100",
        "--nmolecules", "100"
    )
    assert returncode == 0
    assert "Temperature: 300.0K" in stdout
```

**Phase Mapping Table-Driven Tests:**
- The phase mapping tests are organized by ice phase region (`TestLookupPhaseIceIh`, `TestLookupPhaseIceVii`, etc.)
- Each test specifies (T, P) coordinates and expected `phase_id`
- Tests include physics explanations in docstrings referencing IAPWS triple point data
- Regression tests for polygon overlap fixes are in `TestPolygonOverlapFixes` and `TestCurveBasedPhaseLookup`

**Requirement-Traceable Tests:**
- Test class `TestRequirements` maps directly to requirement IDs: `test_RANK_01_energy_ranking`, `test_RANK_02_density_scoring`, etc.
- MED (Medium priority) issue tests use the MED ID in filenames: `test_med03_minimum_box_size.py`

**Dataclass Validation Testing:**
- `InterfaceConfig` validation tested via `pytest.raises(InterfaceGenerationError)` in `test_piece_mode_validation.py` and `test_med03_minimum_box_size.py`
- Error message content verified: `assert "Water layer too thin" in error_msg`

---

*Testing analysis: 2026-04-10*