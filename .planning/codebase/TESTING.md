# Testing Patterns

**Analysis Date:** 2026-06-18

## Test Framework

**Runner:**
- pytest 9.0.2
- Config: No `pytest.ini` or `pyproject.toml` config — uses default discovery

**Assertion Library:**
- Plain `assert` statements (no unittest asserts)
- numpy testing: `np.all()`, `np.allclose()` for array comparisons

**Run Commands:**
```bash
pytest                        # Run all tests
pytest tests/test_tip4p_ice_lj_values.py  # Single file
pytest -x                     # Stop on first failure
pytest -k "test_pbc"          # Run matching tests
pytest --timeout=120          # With timeout (if pytest-timeout installed)
```

## Test File Organization

**Location:**
- Co-located in `tests/` directory (separate from source)
- Sub-directory for output module tests: `tests/test_output/`
- Each sub-directory has its own `conftest.py`

**Naming:**
- Test files: `test_<feature>.py` for unit tests, `test_e2e_<feature>.py` for end-to-end
- Regression test files: `test_scancode_bugs_<module>.py`
- Test helper files: NOT `test_`-prefixed (e.g., `e2e_export_helpers.py`)
- Conftest files: `conftest.py`

**Structure:**
```
tests/
├── conftest.py                    # Shared fixtures (ice, hydrate, interface)
├── e2e_export_helpers.py          # Non-collected helpers (GRO/TOP parsing, chain builders)
├── test_<feature>.py              # Unit tests
├── test_e2e_<feature>.py          # End-to-end pipeline tests
├── test_scancode_bugs_<module>.py # Regression tests for verified bugs
└── test_output/
    ├── conftest.py                # Output-specific fixtures
    ├── test_gromacs_export_<type>.py  # Per-type GROMACS export tests
    └── test_validator.py          # Validator tests
```

## Test Structure

**Suite Organization:**
```python
class TestTIP4PIceConstants:
    """Verify module-level LJ constants are physically correct."""

    def test_sigma_magnitude(self):
        """OW sigma must be ~0.317 nm (not 0.000317 nm or 316 nm)."""
        assert 0.01 < TIP4P_ICE_OW_SIGMA < 1.0

    def test_sigma_close_to_abascal2005(self):
        """OW sigma must be close to Abascal 2005 value: 0.31668 nm."""
        assert abs(TIP4P_ICE_OW_SIGMA - 0.31668) < 0.001
```

**Patterns:**
- Classes group related tests: `TestPBCWrapping`, `TestTREE03`, `TestWriteTopFileLJValues`
- Descriptive docstrings on every test method explaining what's being verified
- One assertion concept per test (but multiple assert lines acceptable for related checks)
- Bug fix references in docstrings: `(V-17 fix)`, `(TREE-01 / Plan 08)`

**Setup pattern:**
- `@pytest.fixture` for expensive objects (module-scoped for GenIce generation):
  ```python
  @pytest.fixture(scope="module")
  def ice_ih_candidate():
      phase_info = lookup_phase(250, 0.1)
      gen = IceStructureGenerator(phase_info, 96)
      candidates = gen.generate_all(1)
      return candidates[0]
  ```
- `@pytest.fixture` for lightweight objects (function-scoped, tmp_path):
  ```python
  @pytest.fixture
  def tmp_top(tmp_path):
      return str(tmp_path / "test.top")
  ```

**Teardown pattern:**
- No explicit teardown — pytest handles fixture cleanup
- `tmp_path` fixture provides auto-cleaned temporary directories
- Persistent workspace fixture for GROMACS debugging:
  ```python
  @pytest.fixture
  def gmx_workspace(request):
      base = Path(__file__).parent.parent / "tmp" / "e2e-gmx-validation"
      workspace = base / request.node.name.replace("::", "_")
      workspace.mkdir(parents=True, exist_ok=True)
      yield workspace
  ```

## Mocking

**Framework:** `unittest.mock.patch`

**Patterns:**
- Patch cKDTree constructor to track rebuild sizes (performance regression test):
  ```python
  original_cKDTree = cKDTree
  call_sizes = []

  def tracking_cKDTree(data, *args, **kwargs):
      size = data.shape[0] if hasattr(data, 'shape') else len(data)
      call_sizes.append(size)
      return original_cKDTree(data, *args, **kwargs)

  with patch('quickice.structure_generation.solute_inserter.cKDTree', tracking_cKDTree):
      result = inserter.insert_solutes(interface_slab)
  ```
- The patched constructor delegates to the real cKDTree (preserving behavior)
- Only tracks metadata (call sizes) for regression assertions

**What to Mock:**
- Third-party constructors for call-count/size tracking (cKDTree)
- GROMACS subprocess availability (`shutil.which('gmx')`)

**What NOT to Mock:**
- Core computation pipeline (GenIce, interface generation, inserters) — use real structures
- Dataclass construction and validation — use real objects
- File I/O — use `tmp_path` fixture for real writes

## Fixtures and Factories

**Test Data:**
- Shared fixtures in `tests/conftest.py` generate REAL structures via GenIce2:
  ```python
  @pytest.fixture(scope="module")
  def interface_slab(ice_ih_candidate):
      config = InterfaceConfig(mode="slab", box_x=3.0, box_y=3.0, box_z=8.0, seed=42,
                               ice_thickness=2.0, water_thickness=4.0)
      return generate_interface(ice_ih_candidate, config)
  ```
- Module-scoped fixtures amortize ~3-5s GenIce2 calls across all tests in a module

**Chain-building helpers in `tests/e2e_export_helpers.py`:**
```python
def _make_slab_interface(candidate, box_x=3.0, box_y=3.0, box_z=8.0, ...):
    config = InterfaceConfig(mode="slab", ...)
    return generate_interface(candidate, config)

def _insert_solutes(source_structure, solute_type='CH4', concentration=0.3, seed=42):
    config = SoluteConfig(concentration_molar=concentration, solute_type=solute_type)
    inserter = SoluteInserter(config=config, seed=seed)
    return inserter.insert_solutes(source_structure, config)

def _insert_ions(source_structure, concentration=0.15, seed=42):
    config = IonConfig(concentration_molar=concentration)
    inserter = IonInserter(config=config, seed=seed)
    volume = _liquid_volume_nm3(source_structure)
    ion_pairs = inserter.calculate_ion_pairs(concentration, volume)
    return inserter.replace_water_with_ions(source_structure, ion_pairs)
```

**Location:**
- Main fixtures: `tests/conftest.py`
- Output fixtures: `tests/test_output/conftest.py`
- Chain helpers: `tests/e2e_export_helpers.py` (NOT collected by pytest)

## Coverage

**Requirements:** None enforced (no coverage threshold, no coverage config)

**View Coverage:**
```bash
pytest --cov=quickice --cov-report=term-missing
```

## TIP4P-ICE LJ Parameter Regression Test Pattern

**File:** `tests/test_tip4p_ice_lj_values.py` (288 lines, 15+ tests)

**Purpose:** Prevents recurrence of Bug P16 (sigma 1000x too small, epsilon 10^6x too small)

**Structure:**
- Helper functions for parsing `.top` file sections:
  ```python
  def _parse_atomtypes(top_text: str) -> dict[str, dict[str, float]]:
      """Parse [atomtypes] section from .top text into {name: {sigma, epsilon}}."""

  def _parse_defaults(top_text: str) -> dict:
      """Parse [defaults] section from .top text."""
  ```
- Fixture for minimal Candidate:
  ```python
  @pytest.fixture
  def simple_candidate():
      positions = np.array([[0.0, 0.0, 0.0], [0.06, 0.09, 0.0], [-0.06, 0.09, 0.0]])
      return Candidate(positions=positions, atom_names=["O", "H", "H"], cell=np.eye(3)*2.0,
                       nmolecules=1, phase_id="ice_ih", seed=42)
  ```
- Three test classes:
  - `TestTIP4PIceConstants` — verifies module-level constant magnitudes
  - `TestWriteTopFileLJValues` — verifies LJ values in write_top_file() output
  - `TestWriteInterfaceTopFileLJValues` — verifies LJ values in interface TOP output
  - `TestNoBuggyHardcodedValues` — verifies no traces of buggy exponent errors in source

**Key assertion pattern — magnitude bounds, not exact values:**
```python
def test_ow_sigma_in_output(self, simple_candidate, tmp_top):
    write_top_file(simple_candidate, tmp_top)
    top_text = Path(tmp_top).read_text()
    atomtypes = _parse_atomtypes(top_text)
    sigma = atomtypes["OW_ice"]["sigma"]
    # Must be > 0.01 nm (catches 1000x error: 0.000317 nm)
    # Must be < 1.0 nm (catches unit errors)
    assert 0.01 < sigma < 1.0
```

**Comb-rule regression test:**
```python
def test_defaults_comb_rule_2(self, simple_candidate, tmp_top):
    write_top_file(simple_candidate, tmp_top)
    top_text = Path(tmp_top).read_text()
    defaults = _parse_defaults(top_text)
    assert defaults.get("comb_rule") == 2
```

**Source scanning regression test:**
```python
def test_no_31668e_minus3(self):
    """0.31668e-3 (1000x too small sigma) must not appear in gromacs_writer.py."""
    source = Path("quickice/output/gromacs_writer.py").read_text()
    assert "0.31668e-3" not in source
```

## PBC Wrapping Integration Test Pattern

**File:** `tests/test_pbc_wrapping.py` (224 lines)

**Purpose:** Verifies all atom coordinates in exported GRO files fall within [0, box_size)

**Structure:**
- GRO coordinate parser:
  ```python
  def _parse_gro_coordinates(gro_path: str) -> tuple[np.ndarray, np.ndarray]:
      """Parse atom positions and box dimensions from .gro file."""
      positions = np.zeros((n_atoms, 3))
      for i in range(n_atoms):
          line = lines[2 + i]
          x = float(line[20:28])
          y = float(line[28:36])
          z = float(line[36:44])
          positions[i] = [x, y, z]
      box_values = [float(v) for v in box_line.split()]
      box_dims = np.array([box_values[0], box_values[1], box_values[2]])
      return positions, box_dims
  ```
- Tolerance-aware assertion:
  ```python
  TOL = 0.01  # nm — accounts for molecule-aware wrapping near PBC boundaries

  def _assert_all_coords_in_box(self, positions, box_dims):
      assert np.all(positions >= -self.TOL)
      assert np.all(positions < box_dims[np.newaxis, :] + self.TOL)
  ```
- Tests cover 4 chain combinations:
  - `test_full_chain_gro_coordinates_in_box` — interface → custom → solute → ion
  - `test_solute_only_coordinates_in_box` — interface → solute → ion
  - `test_custom_only_coordinates_in_box` — interface → custom → ion
  - `test_interface_only_coordinates_in_box` — interface → ion

**No GROMACS required** — only verifies coordinate bounds in GRO output

## Scancode Bug Regression Test Pattern

**File:** `tests/test_scancode_bugs_solute.py` (174 lines)

**Purpose:** Regression tests for V-03 (cKDTree rebuild), V-07 (dedup), V-17 (mutation-free)

**Structure:**
- Class per bug ID:
  ```python
  class TestTREE03:
      """Regression tests for V-03: solute inserter cKDTree rebuild optimization."""
  ```
- Monkeypatch pattern for counting cKDTree invocations:
  ```python
  with patch('quickice.structure_generation.solute_inserter.cKDTree', tracking_cKDTree):
      result = inserter.insert_solutes(interface_slab)
  ```
- Strict monotonicity assertion on rebuild sizes:
  ```python
  for i in range(1, len(rebuild_sizes)):
      assert rebuild_sizes[i] > rebuild_sizes[i-1], (
          f"Rebuild sizes not strictly increasing at index {i}: "
          f"{rebuild_sizes[i-1]} -> {rebuild_sizes[i]}. "
          f"Duplicate sizes indicate redundant rebuilds on "
          f"overlap-rejected iterations (V-03 fix may have been reverted)."
      )
  ```
- Rebuild count must equal placed molecule count:
  ```python
  assert rebuild_count == placed_molecules
  ```

**Other scancode bug test files:**
- `tests/test_scancode_bugs_gromacs.py` — GROMACS writer bugs
- `tests/test_scancode_bugs_ion.py` — ion inserter bugs
- `tests/test_scancode_bugs_inserters.py` — general inserter bugs

## Parameterized Grompp Validation Pattern

**File:** `tests/test_e2e_gmx_param_validation.py` (311 lines)

**Purpose:** 27 parameterized test cases for untested hydrate→interface chain combinations

**NamedTuple chain parameters:**
```python
class ChainParams(NamedTuple):
    """Parameters defining a hydrate→interface chain combination."""
    id: str
    hydrate_type: str
    has_custom: bool
    solute_type: Optional[str]
    has_ion: bool

CHAIN_COMBINATIONS = [
    ChainParams("sI-CH4_custom_ion",      "sI-CH4",  True,  None,  True),
    ChainParams("sI-CH4_custom_thf",      "sI-CH4",  True,  "THF", False),
    # ... 25 more combinations
]
```

**Parameterized test:**
```python
@gmx_skipif
class TestParametricGmxValidation:
    @pytest.mark.parametrize("params", CHAIN_COMBINATIONS, ids=lambda p: p.id)
    def test_gmx_grompp_succeeds(self, params, gmx_workspace):
        final, writer_type = _build_param_chain(params)
        gro_writer, top_writer = _WRITERS[writer_type]
        gro_writer(final, gro_path)
        top_writer(final, top_path)
        # Stage ITPs and assert completeness
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        # Run gmx grompp
        exit_code, stderr = run_gmx_grompp(gmx_workspace, ...)
        assert exit_code == 0
```

**Key patterns:**
- `@pytest.mark.parametrize` with NamedTuple for systematic coverage
- Chain builder function returns `(final_structure, writer_type)`
- `ids=lambda p: p.id` for readable test names

## StagingResult NamedTuple Pattern

**Defined in:** `tests/e2e_export_helpers.py`

```python
StagingResult = namedtuple("StagingResult", ["staged", "missing"])
"""Result from _stage_itp_files: lists of staged and missing ITP filenames."""
```

**Usage:**
```python
def _stage_itp_files(top_path: str, workspace: Path) -> StagingResult:
    staged = []
    missing = []
    for itp_name in includes:
        if not src.exists():
            missing.append(itp_name)
            continue
        (workspace / itp_name).write_text(content)
        staged.append(itp_name)
    return StagingResult(staged=staged, missing=missing)
```

**Advantage over `list[str]`:** Distinguishes successfully staged files from missing ones,
preventing silent failures when ITP files are not found

## ITP Completeness Assertion Pattern

**Defined in:** `tests/e2e_export_helpers.py`

```python
def assert_itp_completeness(top_path: str, workspace: Path) -> None:
    """Assert every #include'd ITP file (except ion.itp) exists in workspace."""
    includes = parse_top_includes(top_path)
    missing = []
    for itp_name in includes:
        if itp_name == "ion.itp":
            continue  # Generated by write_ion_itp(), not staged
        if not (workspace / itp_name).exists():
            missing.append(itp_name)
    assert not missing, (
        f"Missing ITP files in workspace (referenced by #include in .top): {missing}. "
        f"This indicates the export pipeline or ITP staging failed to provide "
        f"a required topology file that GROMACS needs."
    )
```

**Usage:** Called after every `_stage_itp_files` invocation in grompp validation tests:
```python
_stage_itp_files(top_path, gmx_workspace)
assert_itp_completeness(top_path, gmx_workspace)
```

**Purpose:** Catches the "top references ITP but file is missing from export" class of bugs

## pytest.mark.skipif for GROMACS Availability

**Defined in:** `tests/conftest.py`

```python
def _gmx_available():
    """Check if GROMACS gmx command is available on PATH."""
    return shutil.which("gmx") is not None

gmx_skipif = pytest.mark.skipif(
    not _gmx_available(),
    reason="GROMACS (gmx) not found on PATH"
)
```

**Usage:** Decorate test classes that require `gmx grompp`:
```python
@gmx_skipif
class TestParametricGmxValidation:
    ...
```

**Convention:** All grompp-dependent tests use `gmx_skipif` marker — never fail due to missing GROMACS

## Test Types

**Unit Tests:**
- Test individual functions/classes in isolation
- Examples: `test_validators.py`, `test_ranking.py`, `test_tip4p_ice_lj_values.py`
- Use minimal fixtures (small numpy arrays, simple dataclass instances)

**Integration Tests:**
- Test multi-module pipeline flows
- Examples: `test_e2e_workflow_chains.py`, `test_e2e_solute_insertion.py`
- Use module-scoped GenIce fixtures for amortization
- Use chain-building helpers from `e2e_export_helpers.py`

**E2E Tests (grompp validation):**
- Test complete pipeline: generation → export → GROMACS grompp
- Examples: `test_e2e_gmx_validation.py`, `test_e2e_gmx_param_validation.py`
- Require GROMACS (`gmx_skipif` marker)
- Verify: grompp exit code 0, correct molecule types in .top, correct residues in .gro

**Regression Tests:**
- Prevent reversion of specific verified bug fixes
- Examples: `test_scancode_bugs_solute.py`, `test_pbc_wrapping.py`
- Reference bug IDs in class names and docstrings: `TestTREE03`, `TestP16`

## Common Patterns

**Async Testing:**
- Not used — all tests are synchronous
- GUI worker tests use `QThreadPool` + signals but are tested via mock/wait patterns

**Error Testing:**
```python
def test_concentration_out_of_range(self):
    with pytest.raises(ArgumentTypeError):
        validate_concentration_range("10.0")

def test_negative_concentration(self):
    with pytest.raises(ArgumentTypeError):
        validate_concentration_range("-1.0")
```

**Dataclass Validation Testing:**
```python
def test_invalid_solute_type(self):
    with pytest.raises(ValueError, match="solute_type must be"):
        SoluteConfig(concentration_molar=0.1, solute_type="INVALID")
```

**GRO/TOP File Parsing in Tests:**
- Reusable parsers in `e2e_export_helpers.py`:
  - `parse_gro_residue_names()` — extracts residue names from GRO
  - `parse_gro_atom_count()` — reads atom count header
  - `parse_top_molecules()` — parses `[molecules]` section
  - `parse_top_includes()` — extracts `#include` filenames
  - `check_itp_has_moleculetype()` — verifies ITP completeness
  - `assert_gro_residue_ordering()` — verifies no residue interleaving

**Molecule Count Verification:**
```python
molecules = parse_top_molecules(top_path)
expected_top = _expected_top_keys(params)
for key in expected_top:
    assert key in molecules
```

**Residue Ordering Verification:**
```python
residue_names = parse_gro_residue_names(gro_path)
assert_gro_residue_ordering(residue_names, ["SOL", "CH4_H", "NA", "CL"])
```

## Test File Count

**76+ test files** across:
- 72 files in `tests/` (including `conftest.py`, `e2e_export_helpers.py`)
- 8 files in `tests/test_output/` (including `conftest.py`)
- Total test code: ~24,773 lines

---

*Testing analysis: 2026-06-18*
