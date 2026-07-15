# Testing Patterns

**Analysis Date:** 2026-07-14

## Test Framework

**Runner:**
- pytest 9.0.2
- Config: NO `pytest.ini`, NO `pyproject.toml`, NO `setup.cfg` — uses pytest default discovery
- Root `conftest.py` (`/share/home/nglokwan/quickice/conftest.py`) registers custom markers:
  ```python
  def pytest_configure(config):
      config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
  ```

**Assertion Library:**
- Plain `assert` statements only (no `self.assertEqual` / unittest asserts)
- numpy testing: `np.all()`, `np.allclose()` for array comparisons; `np.array_equal()`
- `pytest.raises(Exception, match="regex")` for exception testing

**Run Commands:**
```bash
pytest                                      # Run all tests (~1007)
pytest tests/test_foo.py                    # Single file
pytest tests/test_output/test_validator.py # Single file (subdirectory)
pytest -k "test_pbc"                        # Match by name
pytest -x                                   # Stop on first failure
pytest --timeout=120                        # With timeout (if pytest-timeout installed)
pytest --cov=quickice --cov-report=term-missing   # Coverage
pytest -m "not slow"                        # Deselect slow tests
```

## Test File Organization

**Location:**
- All tests live under `tests/` (separate from source `quickice/`)
- Subdirectory for output-module tests: `tests/test_output/`
- Subdirectory for CLI-specific tests: `tests/test_cli/`
- Each test subdirectory MAY have its own `conftest.py` (e.g., `tests/test_output/conftest.py`)
- `tests/test_cli/` currently has NO conftest — imports `gmx_skipif` from `tests.conftest`

**Naming (CRITICAL — controls collection):**
- Unit tests: `test_<feature>.py` — e.g., `test_validator.py`, `test_tip4p_ice_lj_values.py`
- End-to-end tests: `test_e2e_<feature>.py` — e.g., `test_e2e_hydrate_generation.py`, `test_e2e_gmx_validation.py`
- Regression tests: `test_scancode_bugs_<module>.py` — e.g., `test_scancode_bugs_solute.py`, `test_scancode_bugs_ion.py`
- Test helpers: NO `test_` prefix (otherwise pytest auto-collects and breaks on module-level code): `tests/e2e_export_helpers.py`
- Conftest files: always `conftest.py`
- Non-collected data files: `tests/em.mdp` (GROMACS MDP), `tests/__init__.py`

**Structure:**
```
tests/
├── conftest.py                         # Shared fixtures: ice/hydrate/interface, gmx_skipif, run_quickice
├── e2e_export_helpers.py               # Non-collected helpers: GRO/TOP/ITP parsing, chain builders
├── em.mdp                              # GROMACS energy-minimization MDP (data file)
├── __init__.py
├── test_<feature>.py                   # Unit tests (single module/function)
├── test_e2e_<feature>.py               # End-to-end pipeline tests (real GenIce2 structures)
├── test_scancode_bugs_<module>.py      # Regression tests for verified bugs
├── test_cli/
│   ├── test_mixed_cage_cli.py
│   ├── test_depol_flag.py
│   └── ...
└── test_output/
    ├── conftest.py                     # Output-specific fixtures + mock dialog factories
    ├── __init__.py
    ├── test_gromacs_export_<type>.py   # Per-type GROMACS export tests
    ├── test_validator.py
    └── test_pdb_writer.py
```

## Test Structure

**Suite Organization — class-based grouping:**
```python
# tests/test_tip4p_ice_lj_values.py
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
- Classes group related tests: `TestPBCWrapping`, `TestTREE03`, `TestWriteTopFileLJValues`, `TestHydrateS1Ch4Generation`
- Descriptive docstrings on EVERY test method explaining what's being verified (one line is fine)
- One assertion CONCEPT per test, but multiple `assert` lines acceptable for related checks
- Bug fix references in docstrings and class names: `(V-17 fix)`, `(TREE-01 / Plan 08)`, `TestTREE03`, `TestP16`
- Descriptive assertion messages explaining regression implications:
  ```python
  assert rebuild_count == placed_molecules, (
      f"Rebuild count ({rebuild_count}) should equal placed molecules "
      f"({placed_molecules}). Extra rebuilds indicate unconditional "
      f"per-iteration rebuild pattern (V-03 fix may have been reverted)."
  )
  ```

**Setup pattern — module-scoped fixtures for expensive GenIce2 calls:**
```python
# tests/conftest.py
@pytest.fixture(scope="module")
def ice_ih_candidate():
    """Generate Ice Ih candidate at 250 K, 0.1 MPa with 96 target molecules."""
    phase_info = lookup_phase(250, 0.1)
    gen = IceStructureGenerator(phase_info, 96)
    candidates = gen.generate_all(1)
    return candidates[0]

@pytest.fixture(scope="module")
def interface_slab(ice_ih_candidate):
    """Generate slab interface from Ice Ih candidate."""
    config = InterfaceConfig(
        mode="slab", box_x=3.0, box_y=3.0, box_z=8.0, seed=42,
        ice_thickness=2.0, water_thickness=4.0,
    )
    return generate_interface(ice_ih_candidate, config)
```
- Module scope amortizes ~3-5s GenIce2 calls across ALL tests in a module
- Fixtures depend on other fixtures (e.g., `interface_slab` depends on `ice_ih_candidate`)

**Setup pattern — function-scoped lightweight fixtures using `tmp_path`:**
```python
# tests/test_output/conftest.py
@pytest.fixture
def simple_candidate():
    """1-molecule ice Candidate with 3 atoms (O, H, H)."""
    positions = np.array([[0.1, 0.1, 0.1], [0.15, 0.12, 0.1], [0.08, 0.12, 0.1]])
    return Candidate(positions=positions, atom_names=["O", "H", "H"],
                     cell=np.eye(3)*2.0, nmolecules=1, phase_id="ice_ih", seed=42)

@pytest.fixture
def tmp_top(tmp_path):
    """Provide a temporary .top file path."""
    return str(tmp_path / "test.top")
```

**Teardown pattern:**
- No explicit teardown — pytest handles fixture cleanup
- `tmp_path` fixture provides auto-cleaned temporary directories (function-scoped)
- Persistent workspace fixture for GROMACS debugging (NOT auto-cleaned):
  ```python
  # tests/e2e_export_helpers.py
  @pytest.fixture
  def gmx_workspace(request):
      base = Path(__file__).parent.parent / "tmp" / "e2e-gmx-validation"
      workspace = base / request.node.name.replace("::", "_")
      workspace.mkdir(parents=True, exist_ok=True)
      yield workspace
  ```

## Mocking

**Framework:** `unittest.mock.patch` (from stdlib, no external mock lib)

**Pattern 1 — Tracking constructor calls without changing behavior (cKDTree rebuild regression):**
```python
# tests/test_scancode_bugs_solute.py
original_cKDTree = cKDTree
call_sizes = []

def tracking_cKDTree(data, *args, **kwargs):
    size = data.shape[0] if hasattr(data, 'shape') else len(data)
    call_sizes.append(size)
    return original_cKDTree(data, *args, **kwargs)  # delegate to real

with patch('quickice.structure_generation.solute_inserter.cKDTree', tracking_cKDTree):
    result = inserter.insert_solutes(interface_slab)
```
- The patched constructor delegates to the REAL cKDTree (preserving behavior), only tracks metadata for regression assertions.

**Pattern 2 — Mocking GUI dialogs (factory fixtures):**
```python
# tests/test_output/conftest.py
@pytest.fixture
def mock_save_dialog(tmp_path):
    """Factory fixture for export.py QFileDialog mocking.

    Usage in tests::
        def test_example(mock_save_dialog):
            save_path, dialog_patch, mb_patch = mock_save_dialog("output.gro")
            with dialog_patch, mb_patch:
                # code under test that calls QFileDialog.getSaveFileName
                ...
            assert Path(save_path).exists()
    """
    def _create(filename="test.gro"):
        save_path = str(tmp_path / filename)
        dialog_patch = patch(
            'quickice.gui.export.QFileDialog.getSaveFileName',
            return_value=(save_path, "GRO Files (*.gro)")
        )
        mb_patch = patch('quickice.gui.export.QMessageBox')
        return save_path, dialog_patch, mb_patch
    return _create
```

**What to Mock:**
- Third-party constructors for call-count/size tracking (cKDTree)
- GROMACS subprocess availability: `shutil.which('gmx')` via `gmx_skipif` (skip, don't mock)
- GUI dialogs: `QFileDialog.getSaveFileName`, `QMessageBox` (factory fixtures)
- Module-level functions when testing isolated units

**What NOT to Mock:**
- Core computation pipeline (GenIce, interface generation, inserters) — use REAL structures via fixtures
- Dataclass construction and validation — use real objects
- File I/O — use `tmp_path` fixture for real writes (catches format bugs)

## Fixtures and Factories

**Real-structure fixtures in `tests/conftest.py`** generate structures via GenIce2 (NOT synthetic):
- `ice_ih_candidate`, `ice_ic_candidate` — Ice phases at verified T/P conditions
- `hydrate_sI_ch4_candidate`, `hydrate_sI_thf_candidate`, `hydrate_sII_ch4_candidate` — hydrates
- `hydrate_sI_ch4_structure`, `hydrate_sII_thf_structure` — raw `HydrateStructure` (not converted to `Candidate`)
- `interface_slab`, `interface_pocket`, `interface_hydrate_slab` — interfaces built from candidates

**Chain-building helpers in `tests/e2e_export_helpers.py`** (NOT collected — no `test_` prefix):
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
- Import pattern: `sys.path.insert(0, str(Path(__file__).parent))` then `from e2e_export_helpers import ...`
- These helpers exist because the full chain (interface → custom → solute → ion) requires careful attribute propagation; reusing them avoids re-implementing the workaround for BUG I5 (`_solute_to_ion_source`)

**Subprocess helper for CLI invocation:**
```python
# tests/conftest.py
def run_quickice(*args: str, timeout: int = 60) -> tuple[int, str, str]:
    """Run python -m quickice with given arguments.
    Uses the canonical ``python -m quickice`` invocation (not quickice.py).
    """
    import subprocess, sys
    cmd = [sys.executable, "-m", "quickice"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout, result.stderr
```

**Location summary:**
- Main fixtures: `tests/conftest.py`
- Output-module fixtures + mock dialog factories: `tests/test_output/conftest.py`
- Chain helpers + parsers: `tests/e2e_export_helpers.py`
- Root marker registration: `/share/home/nglokwan/quickice/conftest.py`

## Coverage

**Requirements:** None enforced (no coverage threshold, no coverage config)

**View Coverage:**
```bash
pytest --cov=quickice --cov-report=term-missing
```

## GROMACS Availability Marker

**Defined in `tests/conftest.py`:**
```python
def _gmx_available():
    """Check if GROMACS gmx command is available on PATH."""
    return shutil.which("gmx") is not None

gmx_skipif = pytest.mark.skipif(
    not _gmx_available(),
    reason="GROMACS (gmx) not found on PATH"
)
```

**Usage:** Decorate test CLASSES (or methods) that require `gmx grompp`:
```python
# tests/test_e2e_gmx_param_validation.py
from tests.conftest import gmx_skipif

@gmx_skipif
class TestParametricGmxValidation:
    @pytest.mark.parametrize("params", CHAIN_COMBINATIONS, ids=lambda p: p.id)
    def test_gmx_grompp_succeeds(self, params, gmx_workspace):
        ...
```
- Convention: ALL grompp-dependent tests use `gmx_skipif` — tests SKIP (never fail) when GROMACS is missing
- Headless/remote VTK tests require `QT_QPA_PLATFORM=offscreen` (see AGENTS.md); VTK may still crash — mock or skip VTK-dependent tests when needed

## Test Types

**Unit Tests:**
- Test individual functions/classes in isolation
- Examples: `tests/test_output/test_validator.py`, `tests/test_tip4p_ice_lj_values.py`, `tests/test_gro_resname_validation.py`
- Use minimal fixtures (small numpy arrays, simple dataclass instances, `tmp_path`)

**Integration / E2E Tests:**
- Test multi-module pipeline flows with REAL GenIce2 structures
- Examples: `tests/test_e2e_workflow_chains.py`, `tests/test_e2e_solute_insertion.py`, `tests/test_e2e_hydrate_generation.py`
- Use module-scoped GenIce fixtures for amortization
- Use chain-building helpers from `e2e_export_helpers.py`
- Class per scenario: `TestHydrateS1Ch4Generation`, `TestHydrateS2ThfGeneration`

**E2E Grompp Validation Tests:**
- Test complete pipeline: generation → export → `gmx grompp`
- Examples: `tests/test_e2e_gmx_validation.py`, `tests/test_e2e_gmx_param_validation.py`
- REQUIRE GROMACS (`gmx_skipif` marker)
- Verify: grompp exit code 0, correct molecule types in `.top`, correct residues in `.gro`

**Regression Tests (scancode bugs):**
- Prevent reversion of SPECIFIC verified bug fixes
- Files: `tests/test_scancode_bugs_solute.py`, `tests/test_scancode_bugs_ion.py`, `tests/test_scancode_bugs_gromacs.py`, `tests/test_scancode_bugs_inserters.py`, `tests/test_scancode_bugs_ion_charge_warning.py`
- Reference bug IDs in class names and docstrings: `TestTREE03` (V-03), `TestP16` (P16)
- Include explanatory docstrings describing what reversion looks like:
  ```python
  class TestTREE03:
      """Regression tests for V-03: solute inserter cKDTree rebuild optimization.

      If these tests fail, someone may have moved the tree rebuild back
      outside the success branch, causing O(iterations) tree rebuilds
      instead of O(placed_molecules) rebuilds.
      """
  ```

## Common Patterns

**Async Testing:** Not used — all tests are synchronous. GUI worker tests (`HydrateWorker` subclasses `QThread` directly) are tested via mock/wait patterns, NOT asyncio.

**Error Testing — CLI validators raise:**
```python
def test_concentration_out_of_range(self):
    with pytest.raises(ArgumentTypeError):
        validate_concentration_range("10.0")

def test_negative_concentration(self):
    with pytest.raises(ArgumentTypeError):
        validate_concentration_range("-1.0")
```

**Error Testing — Dataclass validation with match:**
```python
def test_invalid_solute_type(self):
    with pytest.raises(ValueError, match="solute_type must be"):
        SoluteConfig(concentration_molar=0.1, solute_type="INVALID")
```

**Parameterized Tests — NamedTuple for systematic coverage:**
```python
# tests/test_e2e_gmx_param_validation.py
class ChainParams(NamedTuple):
    """Parameters defining a hydrate→interface chain combination."""
    id: str
    hydrate_type: str
    has_custom: bool
    solute_type: Optional[str]
    has_ion: bool

CHAIN_COMBINATIONS = [
    ChainParams("sI-CH4_custom_ion",  "sI-CH4",  True,  None,  True),
    ChainParams("sI-CH4_custom_thf",   "sI-CH4",  True,  "THF", False),
    # ... 25 more combinations
]

@gmx_skipif
class TestParametricGmxValidation:
    @pytest.mark.parametrize("params", CHAIN_COMBINATIONS, ids=lambda p: p.id)
    def test_gmx_grompp_succeeds(self, params, gmx_workspace):
        final, writer_type = _build_param_chain(params)
        ...
        assert exit_code == 0, (
            f"gmx grompp failed for {params.id} "
            f"(hydrate={params.hydrate_type}, custom={params.has_custom}, "
            f"solute={params.solute_type}, ion={params.has_ion}):\n{stderr[-500:]}"
        )
```
- `ids=lambda p: p.id` produces readable test IDs in output
- NamedTuple beats `list[str]` for distinguishing multi-field results (see `StagingResult` below)

**Simple parametrize (single arg):**
```python
@pytest.mark.parametrize("concentration", [0.05, 0.15, 0.5])
def test_ion_count_scales_with_concentration(self, concentration, interface_slab):
    ...

@pytest.mark.parametrize("shape", ["sphere", "cubic"])
def test_pocket_shape(self, shape, ...):
    ...
```

**StagingResult NamedTuple pattern (in `tests/e2e_export_helpers.py`):**
```python
StagingResult = namedtuple("StagingResult", ["staged", "missing"])
"""Result from _stage_itp_files: lists of staged and missing ITP filenames."""

def _stage_itp_files(top_path: str, workspace: Path) -> StagingResult:
    staged, missing = [], []
    for itp_name in includes:
        if not src.exists():
            missing.append(itp_name); continue
        (workspace / itp_name).write_text(content)
        staged.append(itp_name)
    return StagingResult(staged=staged, missing=missing)
```
- Distinguishes successfully staged files from missing ones — prevents silent failures

**ITP completeness assertion (in `tests/e2e_export_helpers.py`):**
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
- Call after EVERY `_stage_itp_files` in grompp validation tests — catches "top references ITP but file missing" bugs

**Reusable GRO/TOP/ITP parsers (in `tests/e2e_export_helpers.py`):**
- `parse_gro_residue_names(gro_path)` — extracts residue names (columns 6-10)
- `parse_gro_atom_count(gro_path)` — reads atom count from line 2
- `parse_top_molecules(top_path)` — parses `[ molecules ]` section → `dict[str, int]`
- `parse_top_includes(top_path)` — extracts `#include` filenames
- `check_itp_has_moleculetype(itp_path)` — verifies `[ moleculetype ]` section exists
- `assert_gro_residue_ordering(residue_names, expected_order)` — verifies no residue interleaving

**Molecule count verification:**
```python
molecules = parse_top_molecules(top_path)
expected_top = _expected_top_keys(params)
for key in expected_top:
    assert key in molecules
```

**Residue ordering verification:**
```python
residue_names = parse_gro_residue_names(gro_path)
assert_gro_residue_ordering(residue_names, ["SOL", "CH4_H", "NA", "CL"])
```

## Source-scanning Regression Test Pattern

**File:** `tests/test_tip4p_ice_lj_values.py`

Prevents recurrence of Bug P16 (sigma 1000x too small, epsilon 10^6x too small) by scanning SOURCE for known-bad literals:
```python
def test_no_31668e_minus3(self):
    """0.31668e-3 (1000x too small sigma) must not appear in gromacs_writer.py."""
    source = Path("quickice/output/gromacs_writer.py").read_text()
    assert "0.31668e-3" not in source
```
- Magnitude bounds (NOT exact values) catch unit/order-of-magnitude errors:
  ```python
  # Must be > 0.01 nm (catches 1000x error: 0.000317 nm)
  # Must be < 1.0 nm (catches unit errors)
  assert 0.01 < sigma < 1.0
  ```
- Helper parsers reuse across test classes: `_parse_atomtypes(top_text)`, `_parse_defaults(top_text)`

## Test File Count

- ~107 entries in `tests/` (including `conftest.py`, `e2e_export_helpers.py`, `em.mdp`, `__init__.py`, `__pycache__/`)
- ~20 entries in `tests/test_output/` (including `conftest.py`, `__init__.py`)
- ~5 entries in `tests/test_cli/`
- Total active test files: ~100 collected, ~1007 tests

---

*Testing analysis: 2026-07-14*
