# Testing Patterns

**Analysis Date:** 2026-04-13

## Test Framework

**Runner:**
- pytest >=9.0.0 (per `requirements-dev.txt`)
- No `conftest.py` detected at project root or test directories
- No `pytest.ini`, `pyproject.toml`, or `setup.cfg` pytest config detected
- All pytest configuration uses defaults
- 307 tests collected across 16 test files

**Assertion Library:**
- `pytest` native `assert` statements for all general assertions
- `numpy.testing.assert_array_equal` for exact NumPy array comparisons
- `numpy.testing.assert_allclose` for floating-point tolerance comparisons
- `pytest.approx()` for approximate floating-point comparisons in density tests
- No `unittest.TestCase` usage anywhere — all tests are pytest-style

**Run Commands:**
```bash
pytest                                    # Run all tests
pytest tests/test_validators.py           # Run specific test file
pytest tests/test_ranking.py -k "energy" # Run tests matching pattern
pytest tests/test_phase_mapping.py::TestLookupPhaseIceIh  # Run specific class
pytest -x                                 # Stop on first failure
pytest -v                                 # Verbose output
pytest tests/test_output/                  # Run output tests only
pytest --co -q                             # List all tests without running
```

## Test File Organization

**Location:**
- Tests are in a separate `tests/` directory at project root (not co-located with source)
- Test output files in `tests/test_output/` subdirectory for PDB writer tests
- No `conftest.py` — all fixtures defined per test module

**Naming:**
- Test files: `test_<module_name>.py` — e.g., `test_validators.py`, `test_ranking.py`, `test_phase_mapping.py`
- Test classes: `Test<FeatureName>` — e.g., `TestValidateTemperature`, `TestEnergyScore`, `TestLookupPhaseIceIh`
- Test methods: `test_<behavior_description>` — e.g., `test_accepts_valid_minimum_boundary`, `test_rejects_negative_temperature`
- Issue-tracking tests include issue IDs: `test_med03_minimum_box_size.py`

**Structure:**
```
tests/
├── __init__.py                           # Package marker
├── test_validators.py                    # CLI input validators (153 lines)
├── test_cli_integration.py               # Full CLI subprocess tests (292 lines)
├── test_phase_mapping.py                 # Phase mapping + CLI integration (618 lines)
├── test_structure_generation.py          # Core generation + mapper + types (625 lines)
├── test_ranking.py                        # Scoring + ranking + normalization (691 lines)
├── test_water_density.py                 # IAPWS-95 water density (176 lines)
├── test_ice_ih_density.py                # IAPWS Ice Ih density (174 lines)
├── test_pbc_hbonds.py                    # PBC-aware hydrogen bond detection (200 lines)
├── test_atom_ordering_validation.py      # VTK atom ordering validation (201 lines)
├── test_atom_names_filtering.py          # Overlap resolver atom name filtering (199 lines)
├── test_interface_ordering_validation.py # Interface atom ordering validation
├── test_piece_mode_validation.py         # Piece mode water layer validation
├── test_med03_minimum_box_size.py        # Minimum box size validation
├── test_triclinic_interface.py           # Triclinic cell interface tests
├── test_integration_v35.py               # v3.5 comprehensive integration tests (513 lines)
└── test_output/
    ├── __init__.py                        # Empty
    ├── test_pdb_writer.py                # PDB format output tests (482 lines)
    └── test_validator.py                 # Structure validation (spglib, overlap) (323 lines)
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
- Test method names use `test_` prefix with descriptive `snake_case`
- Docstrings describe expected behavior in sentence form: `"Temperature 0K should be accepted."`
- Arrange-Act-Assert pattern used consistently
- Boundary value testing: tests for minimum, maximum, and just-outside-boundary values
- Error message content verification: `assert "temperature" in str(exc_info.value).lower()`
- Section separators with `# ============` comment blocks in larger test files (e.g., `test_ranking.py`)

**Setup/Teardown:**
- `pytest.fixture` for shared test data creation
- No `setup_module`, `setup_class`, or `setUp` methods
- No `conftest.py` — fixtures defined at module level in each test file
- `tempfile.NamedTemporaryFile` for file I/O tests with `try/finally` cleanup
- `tempfile.TemporaryDirectory` for directory output tests

## Mocking

**Framework:** No mocking framework detected. Tests use real objects and actual function calls.

**Patterns:**
- No `unittest.mock`, `pytest-mock`, or similar mocking libraries used anywhere
- CLI integration tests use `subprocess.run()` to test the actual CLI binary
- Structure generation tests call real GenIce generation (no mocking of GenIce)
- Ranking tests create `Candidate` objects with known positions for deterministic scoring
- Phase mapping tests call real `lookup_phase()` with no stubs
- Caching tests verify `lru_cache` behavior by checking `cache_info()`

**What to Mock:**
- NOT MOCKED: `lookup_phase()`, `generate_candidates()`, `rank_candidates()` — tested with real calls
- NOT MOCKED: GenIce lattice generation — integration tests generate real structures
- NO MOCKING PATTERN ESTABLISHED — the project has no mocking convention

**What NOT to Mock:**
- Pure computation functions (scoring, normalization) — tested with crafted inputs
- Validation functions — tested directly with string inputs
- CLI parsers — tested via subprocess for full integration
- NumPy operations — tested with constructed arrays

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
        # Molecule 2: O at 0.28nm (near ideal O-O distance)
        [0.28, 0.0, 0.0],   # O
        [0.38, 0.0, 0.0],   # H
        [0.18, 0.0, 0.0],   # H
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
- Multiple fixture variants for different scenarios within same test file

**Key Fixture Naming Convention:**
- `simple_candidate` — minimal valid test data
- `ideal_candidate` — data matching ideal values (e.g., O-O distance of 0.276 nm)
- `candidate_set` — collection of 5 candidates for ranking tests
- `candidate_with_duplicate_seeds` — data designed to trigger diversity edge case
- `single_candidate` — edge case: only one molecule
- `triclinic_candidate` — data with non-orthogonal cell for angle testing
- `ranking_result` — full `RankingResult` with 12 candidates for output testing
- `phase_info_ice_ih` — dict matching `lookup_phase()` output format
- `ice_ih_candidate` — candidate with hexagonal cell for space group testing
- `overlapping_candidate` — candidate with atom overlaps for overlap detection
- `pbc_overlap_candidate` — candidate with overlaps across PBC boundary
- `well_spaced_candidate` — candidate with no overlaps (negative control)

**Factory Patterns:**
- Direct `Candidate()` construction with known `numpy` arrays
- Loop-based candidate generation for sets: `for i in range(5): candidates.append(Candidate(...))`
- Dict-based phase info construction: `{"phase_id": "ice_ih", "phase_name": "Ice Ih", "density": 0.9167}`

## Coverage

**Requirements:** No coverage target enforced. No `.coveragerc` or `pytest --cov` configuration detected.

**View Coverage:**
```bash
pytest --cov=quickice --cov-report=term-missing  # Would need pytest-cov installed
```

**Coverage Gaps:**
- GUI code (`quickice/gui/`) has NO direct tests — GUI testing requires Qt display environment
- `quickice/output/phase_diagram.py` — no direct unit tests
- `quickice/structure_generation/modes/` (`slab.py`, `pocket.py`, `piece.py`) — no direct unit tests
- `quickice/structure_generation/water_filler.py` — no direct unit tests
- `quickice/output/gromacs_writer.py` — no direct unit tests
- `quickice/gui/export.py`, `quickice/gui/vtk_utils.py` — tested indirectly via `test_atom_ordering_validation.py` and `test_pbc_hbonds.py`
- `quickice/structure_generation/overlap_resolver.py` — tested via `test_atom_names_filtering.py`
- `quickice/phase_mapping/melting_curves.py`, `quickice/phase_mapping/solid_boundaries.py`, `quickice/phase_mapping/triple_points.py` — tested indirectly through `test_phase_mapping.py`

## Test Types

**Unit Tests:**
- `test_validators.py` — Pure function testing with string inputs and assertion checks
- `test_ranking.py` (TestNormalizeScores, TestEnergyScore, TestDensityScore, TestDiversityScore) — Mathematical scoring functions with known-position Candidates
- `test_structure_generation.py` (TestPhaseToGenIceMapping, TestUnitCellMolecules, TestCalculateSupercell, TestCandidateDataclass) — Pure data/computation
- `test_output/test_validator.py` — Space group and overlap detection
- `test_atom_names_filtering.py` — Overlap resolver atom name filtering logic
- `test_water_density.py` — IAPWS-95 water density calculations
- `test_ice_ih_density.py` — IAPWS Ice Ih density calculations

**Integration Tests:**
- `test_structure_generation.py` (TestIceStructureGenerator, TestGenerateCandidates) — Tests real GenIce generation
- `test_phase_mapping.py::TestCLIIntegration` — Tests full CLI subprocess execution
- `test_structure_generation.py::TestIntegrationWithPhase2` — Tests lookup + generation pipeline
- `test_cli_integration.py` — Full CLI subprocess tests with `subprocess.run()`
- `test_output/test_pdb_writer.py::TestWriteRankedCandidates` — Tests file I/O with temp directories
- `test_integration_v35.py` — Comprehensive CLI interface generation for all modes + GRO validation

**E2E Tests:**
- `TestCLIIntegration` in `test_phase_mapping.py` — runs full CLI pipeline via subprocess
- `test_cli_integration.py` — end-to-end CLI with argument parsing, validation, generation, output
- `test_integration_v35.py` — end-to-end interface generation with GRO file validation

## Common Patterns

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

# pytest.approx for reference value comparison
result = ice_ih_density_gcm3(273.15, 0.101325)
assert result == pytest.approx(0.91672, abs=0.0001)

# Cell volume range testing
volume = abs(np.linalg.det(candidate.cell))
assert 2.0 < volume < 25.0  # Reasonable volume in nm³

# Position range testing
assert np.all(np.abs(candidate.positions) < 10)
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
        assert 'HETATM' in content
        assert 'END' in content
    finally:
        Path(filepath).unlink(missing_ok=True)
```

**CLI Subprocess Testing:**
```python
def run_cli(*args: str) -> tuple[int, str, str]:
    """Run quickice.py with given arguments."""
    cmd = [sys.executable, str(QUICKICE_SCRIPT)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return result.returncode, result.stdout, result.stderr

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

**GRO File Validation (custom helper):**
```python
# From test_integration_v35.py
def validate_gro_file(filepath: Path) -> dict:
    """Validate a GROMACS .gro file."""
    # Parses title, atom count, coordinates, box vectors
    # Validates format, coordinate bounds, and structure
    return {
        'valid': len(errors) == 0,
        'atom_count': atom_count,
        'box_dimensions': box_dimensions,
        'errors': errors,
        'coordinates': coordinates
    }
```

**Caching Verification:**
```python
def test_caching_works(self):
    """Verify that lru_cache is working for density calculations."""
    water_density_kgm3.cache_clear()
    
    result1 = water_density_kgm3(298.15, 0.101325)
    info1 = water_density_kgm3.cache_info()
    assert info1.misses == 1
    assert info1.hits == 0
    
    result2 = water_density_kgm3(298.15, 0.101325)
    info2 = water_density_kgm3.cache_info()
    assert info2.hits == 1
    
    assert result1 is result2  # Cached result is exact same object
```

**Phase Mapping Table-Driven Tests:**
- Tests organized by ice phase region: `TestLookupPhaseIceIh`, `TestLookupPhaseIceVii`, `TestLookupPhaseIceVi`, `TestLookupPhaseIceIii`, `TestLookupPhaseIceV`, `TestLookupPhaseIceViii`, `TestLookupPhaseIceIi`, `TestLookupPhaseIceXi`, `TestLookupPhaseIceIx`, `TestLookupPhaseIceX`, `TestLookupPhaseIceXv`
- Each test specifies (T, P) coordinates and expected `phase_id`
- Tests include physics explanations in docstrings referencing IAPWS triple point data
- Regression tests for polygon overlap fixes in `TestPolygonOverlapFixes` and `TestCurveBasedPhaseLookup`
- Curved boundary verification in `TestCurvedBoundaryVerification`

**Requirement-Traceable Tests:**
- Test class `TestRequirements` maps directly to requirement IDs: `test_RANK_01_energy_ranking`, `test_RANK_02_density_scoring`, `test_RANK_03_diversity_scoring`, `test_RANK_04_combined_score`
- MED (Medium priority) issue tests use the MED ID in filenames: `test_med03_minimum_box_size.py`

**Dataclass Validation Testing:**
- `InterfaceConfig` validation tested via `pytest.raises(InterfaceGenerationError)` in `test_piece_mode_validation.py` and `test_med03_minimum_box_size.py`
- Error message content verified: `assert "Water layer too thin" in error_msg`
- Custom `overlap_threshold` validation tested: `InterfaceConfig.__post_init__()` range check

**Regression/Bug Fix Tests:**
- `TestSlicingBugComparison` in `test_atom_names_filtering.py` — explicitly documents a past bug and verifies the fix using labeled atom names to make the comparison clear
- `TestPolygonOverlapFixes` in `test_phase_mapping.py` — documents specific cases where polygon-based approach had overlapping regions

**Edge Case Testing:**
- Empty inputs: `rank_candidates([])` raises `ValueError`
- Single candidate: `rank_candidates([single_candidate])`
- Duplicate seeds: `candidate_with_duplicate_seeds` fixture
- Infinite energy score: single oxygen molecule (no O-O pairs)
- All scores equal: normalization returns zeros
- Triclinic cells: angle calculations for non-orthogonal boxes
- PBC boundary atoms: overlapping across periodic boundary
- Invalid molecule indices: out-of-range indices silently ignored
- Mixed atom name formats: TIP3P + TIP4P mixing detected and rejected

**Async Testing:**
- Not used — no async code in the project

---

*Testing analysis: 2026-04-13*
