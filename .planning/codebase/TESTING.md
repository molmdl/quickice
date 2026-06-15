# Testing Patterns

**Analysis Date:** 2026-06-15

## Test Framework

**Runner:**
- pytest 9.0.0+
- Config: `conftest.py` at project root registers custom markers
- Pytest discovers tests automatically via `test_*.py` naming convention
- No `pytest.ini`, `pyproject.toml`, or `setup.cfg` config files

**Assertion Library:**
- Standard pytest assertions: `assert`, `assert ... == ...`
- NumPy-specific: `np.testing.assert_array_equal()`, `np.testing.assert_allclose()`
- No separate assertion library (no `assertpy`, `expects`, etc.)

**Run Commands:**
```bash
pytest                              # Run all tests
pytest tests/test_phase_mapping.py # Run specific file
pytest -k "test_ice_ih"           # Run tests matching name
pytest -m slow                     # Run only slow-marked tests
pytest -m "not slow"              # Skip slow tests (recommended for rapid iteration)
pytest tests/test_output/          # Run output submodule tests
pytest tests/test_cli_integration.py  # Run CLI integration tests
pytest tests/test_cli_pipeline.py     # Run CLI pipeline E2E tests
pytest --tb=short                   # Shorter tracebacks
```

**Pytest Markers:**
- `@pytest.mark.slow` — for expensive GenIce2 generation tests and subprocess pipeline tests (registered in root `conftest.py`)
- `@pytest.mark.parametrize` — for parameterized tests (pocket shapes, concentrations, phases)
- `@pytest.mark.skip(reason="...")` — for tests requiring unavailable dependencies (e.g., `pytest-qt`)
- Marker registration in `conftest.py`:
  ```python
  def pytest_configure(config):
      config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
  ```

## Test File Organization

**Location:**
- All tests in `tests/` directory at project root (NOT co-located with source)
- Sub-directory `tests/test_output/` for GROMACS export tests
- Shared conftest at `tests/conftest.py` and `tests/test_output/conftest.py`

**Naming:**
- Unit/bridge tests: `test_<feature>.py` — e.g., `test_validators.py`, `test_ranking.py`
- E2E tests: `test_e2e_<workflow>.py` — e.g., `test_e2e_ice_generation.py`, `test_e2e_workflow_chains.py`
- CLI integration tests: `test_cli_integration.py` — CLI argument validation via subprocess
- CLI pipeline tests: `test_cli_pipeline.py` — full pipeline E2E via subprocess
- Entry point tests: `test_entry_point.py` — routing behavior via subprocess + direct function call
- Regression tests: `test_scancode_bugs_<area>.py` — e.g., `test_scancode_bugs_gromacs.py`
- Shared helpers (NOT auto-collected): `e2e_export_helpers.py` (no `test_` prefix)

**Structure:**
```
tests/
├── conftest.py                          # Root shared fixtures + run_quickice() helper
├── e2e_export_helpers.py               # GRO/TOP parsing + chain-building helpers
├── em.mdp                              # GROMACS energy-minimization MDP file
├── __init__.py                         # Package marker
├── test_validators.py                  # CLI validator unit tests
├── test_phase_mapping.py               # Phase lookup unit/integration tests
├── test_structure_generation.py        # Generator unit/integration tests
├── test_ranking.py                     # Scoring and ranking unit tests
├── test_cli_integration.py            # CLI argument validation (subprocess)
├── test_cli_pipeline.py               # CLI pipeline E2E (subprocess, @pytest.mark.slow)
├── test_entry_point.py                # Entry routing: --cli, --gui, --help, no-args
├── test_integration_v35.py            # Integration tests for v3.5 features
├── test_e2e_ice_generation.py          # E2E: ice generation pipeline
├── test_e2e_hydrate_generation.py      # E2E: hydrate generation
├── test_e2e_interface_generation.py    # E2E: interface construction
├── test_e2e_ion_insertion.py          # E2E: ion insertion
├── test_e2e_solute_insertion.py        # E2E: solute insertion
├── test_e2e_workflow_chains.py         # E2E: full chain F1–F7
├── test_e2e_gmx_validation.py          # E2E: gmx grompp validation
├── test_e2e_chain_export_1.py          # E2E: chain export part 1
├── test_e2e_chain_export_2.py          # E2E: chain export part 2
├── test_e2e_cross_chain_invariants.py   # E2E: cross-chain invariant checks
├── test_e2e_custom_molecule.py          # E2E: custom molecule insertion
├── test_e2e_custom_export.py            # E2E: custom molecule export
├── test_e2e_ice_interface_export.py     # E2E: ice interface export
├── test_e2e_ion_export.py               # E2E: ion export
├── test_e2e_solute_export.py            # E2E: solute export
├── test_e2e_itp_baseline.py             # E2E: ITP file baseline validation
├── test_scancode_bugs_gromacs.py       # Regression: GROMACS writer bugs
├── test_scancode_bugs_ion.py           # Regression: ion insertion bugs
├── test_scancode_bugs_inserters.py     # Regression: inserter bugs
├── test_pocket_edge_cases.py           # Edge cases: pocket mode
├── test_pocket_invariants.py           # Invariants: pocket structure
├── test_overlap_removal_invariants.py  # Invariants: overlap removal
├── test_pbc_hbonds.py                  # PBC hydrogen bond detection
├── test_triclinic_interface.py         # Triclinic cell interface tests
├── test_custom_molecule.py             # Custom molecule unit tests
├── test_custom_molecule_concentration.py # Concentration calculation tests
├── test_custom_molecule_renderer.py    # Custom molecule renderer tests
├── test_custom_molecule_panel_34_6.py  # Panel regression test
├── test_atom_names_filtering.py        # Atom name filtering tests
├── test_atom_ordering_validation.py    # Atom ordering validation tests
├── test_interface_ordering_validation.py # Interface ordering validation
├── test_interface_modes_audit.py       # Interface modes audit tests
├── test_ion_hydrate_fix.py             # Ion hydrate fix regression
├── test_ion_source_dropdown.py         # Ion source dropdown tests
├── test_itp_parser_edge_cases.py       # ITP parser edge cases
├── test_med03_minimum_box_size.py      # Minimum box size regression
├── test_moleculetype_registry.py       # Moleculetype registry tests
├── test_guest_atom_counting.py         # Guest atom counting tests
├── test_gromacs_molecule_ordering.py    # GROMACS molecule ordering
├── test_gromacs_moleculetype_names.py  # GROMACS moleculetype name tests
├── test_hydrate_guest_tiling.py        # Hydrate guest tiling tests
├── test_ice_ih_density.py              # Ice Ih density validation
├── test_water_density.py               # Water density validation
├── test_piece_mode_validation.py       # Piece mode validation tests
├── test_pocket_cubic_guests.py         # Pocket cubic guest tests
├── test_scorer_diversity.py            # Scorer diversity tests
├── test_scorer_performance.py          # Scorer performance tests
├── test_solute_insertion.py            # Solute insertion tests
├── test_solute_ion_molecule_index.py   # Solute-ion molecule index tests
├── test_validators.py                  # Additional validator tests
├── ... (67+ total test files)
└── test_output/                        # GROMACS export tests
    ├── conftest.py                     # Export-specific fixtures (mock dialogs, synthetic structures)
    ├── __init__.py                     # Package marker
    ├── test_gromacs_export_ice.py
    ├── test_gromacs_export_interface.py
    ├── test_gromacs_export_hydrate.py
    ├── test_gromacs_export_ion.py
    ├── test_gromacs_export_solute.py
    ├── test_gromacs_export_custom.py
    ├── test_gromacs_export_chain.py
    ├── test_molecule_wrapping.py
    ├── test_pdb_writer.py
    └── test_validator.py
```

## Test Structure

**Suite Organization:**
```python
class TestLookupPhaseIceIh:
    """Tests for Ice Ih (normal atmospheric ice) lookups."""

    def test_lookup_atmospheric_near_melting(self):
        """Temperature 273K, Pressure 0 MPa should return ice_ih."""
        result = lookup_phase(273, 0)
        assert result["phase_id"] == "ice_ih"
        assert result["phase_name"] == "Ice Ih"
```

**Patterns:**
- Each test class groups related tests by feature/bug/behavior
- Class names use `Test` prefix + descriptive name: `TestBUG05`, `TestIceCandidateGmxValidation`, `TestPipelineFlagValidation`, `TestPipelineExitCodes`
- Test method names use descriptive `snake_case`: `test_lookup_atmospheric_near_melting`, `test_gmx_grompp_succeeds`
- Test docstrings describe expected behavior and context (especially for regression tests)
- Descriptive assertion messages on non-obvious checks:
  ```python
  assert result["phase_id"] == "ice_v", (
      f"Expected ice_v at T=260K, P=400MPa but got {result['phase_id']}. "
      "This indicates polygon overlap error not fixed."
  )
  ```

**Setup Pattern:**
- Use `@pytest.fixture` for expensive GenIce2 generation (module-scoped for amortization):
  ```python
  @pytest.fixture(scope="module")
  def ice_ih_candidate():
      """Generate Ice Ih candidate at 250 K, 0.1 MPa with 96 target molecules."""
      phase_info = lookup_phase(250, 0.1)
      gen = IceStructureGenerator(phase_info, 96)
      candidates = gen.generate_all(1)
      return candidates[0]
  ```
- Use `@pytest.fixture(autouse=True)` for per-class setup in chain tests:
  ```python
  @pytest.fixture(autouse=True)
  def _build_chain(self, interface_slab):
      self.ion = _insert_ions(interface_slab, concentration=0.15)
  ```
- Use `tmp_path` fixture for file output tests (pytest built-in)
- Use custom workspace fixture for GROMACS grompp tests:
  ```python
  @pytest.fixture
  def gmx_workspace(request):
      """Persistent workspace under tmp/e2e-gmx-validation/ for GROMACS grompp."""
      base = Path(__file__).parent.parent / "tmp" / "e2e-gmx-validation"
      workspace = base / request.node.name.replace("::", "_")
      workspace.mkdir(parents=True, exist_ok=True)
      yield workspace
  ```
- Temp directory for CLI pipeline tests:
  ```python
  def make_temp_output_dir() -> str:
      return tempfile.mkdtemp(prefix="test_cli_pipeline_")
  # Always cleanup: shutil.rmtree(outdir, ignore_errors=True) in finally block
  ```

**Teardown Pattern:**
- No explicit teardown — fixtures handle cleanup via `yield` or `tmp_path`
- CLI pipeline tests use `try/finally` with `shutil.rmtree(outdir, ignore_errors=True)`
- Workspace fixture yields directory (persists for debugging, no cleanup)

**Assertion Pattern:**
- Standard Python `assert` with descriptive messages
- NumPy array comparisons: `np.testing.assert_array_equal()`, `np.testing.assert_allclose()`
- Approximate float comparisons: `assert abs(result["density"] - 0.9167) < 0.001`
- Exception testing: `with pytest.raises(UnknownPhaseError) as exc_info:`
- CLI subprocess assertions: `assert rc == 0`, `assert "[PROGRESS]" in stderr`, `assert "required" in stderr.lower()`

## Mocking

**Framework:** `unittest.mock` (standard library)

**Patterns:**
- Mock `QFileDialog` and `QMessageBox` for export tests:
  ```python
  @pytest.fixture
  def mock_save_dialog(tmp_path):
      """Factory fixture for export.py QFileDialog mocking."""
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

- Mock cancel dialog for testing user cancellation:
  ```python
  @pytest.fixture
  def mock_cancel_dialog():
      """Factory fixture for cancelled QFileDialog simulation."""
      def _create(module_path='quickice.gui.export'):
          dialog_patch = patch(
              f'{module_path}.QFileDialog.getSaveFileName',
              return_value=("", "")
          )
          mb_patch = patch(f'{module_path}.QMessageBox')
          return dialog_patch, mb_patch
      return _create
  ```

- Mock for entry point routing tests (direct function call, NOT subprocess):
  ```python
  def test_gui_missing_pyside6_error(self, capsys):
      """--gui + PySide6 missing → error message, exit 1."""
      from quickice.entry import main
      with unittest.mock.patch(
          'quickice.entry._is_pyside6_available', return_value=False
      ):
          rc = main(['quickice', '--gui'])
      assert rc == 1
      captured = capsys.readouterr()
      assert "PySide6 is not installed" in captured.err
  ```

- Context manager pattern for mock application:
  ```python
  def test_export_creates_gro_top_itp(self, ranked_candidate, mock_save_dialog):
      save_path, dialog_p, mb_p = mock_save_dialog("ice_test.gro")
      exporter = GROMACSExporter(parent_widget=None)
      with dialog_p, mb_p:
          result = exporter.export_gromacs(ranked_candidate, T=195, P=1.36)
      assert result is True
  ```

**What to Mock:**
- Qt dialog classes (`QFileDialog`, `QMessageBox`) — always mock in export tests
- External processes (`gmx grompp`) — subprocess calls wrapped in helper functions
- GUI rendering (VTK, OpenGL) — not tested in API-level tests
- Entry routing helpers (`_is_pyside6_available`, `_has_display`) — mock for GUI mode tests

**What NOT to Mock:**
- Internal computation pipeline: test with REAL GenIce2-generated structures
- Data structures: use actual `Candidate`, `InterfaceStructure`, `IonStructure` objects
- GRO/TOP file writers: write to real `tmp_path` and verify file contents
- Phase lookup: use real curve-based computation, not mocked lookups
- CLI subprocess tests: use REAL subprocess invocation (not mocked argparse)

## Fixtures and Factories

**Test Data:**
- Synthetic minimal structures for unit tests (1-2 molecules):
  ```python
  @pytest.fixture
  def simple_candidate():
      """1-molecule ice Candidate with 3 atoms (O, H, H)."""
      positions = np.array([[0.1, 0.1, 0.1], [0.15, 0.12, 0.1], [0.08, 0.12, 0.1]])
      atom_names = ["O", "H", "H"]
      cell = np.array([[0.9, 0.0, 0.0], [0.0, 0.78, 0.0], [0.0, 0.0, 0.72]])
      return Candidate(positions=positions, atom_names=atom_names, cell=cell,
                        nmolecules=1, phase_id="ice_ih", seed=42, metadata={})
  ```

- Real GenIce2-generated structures for E2E tests (module-scoped):
  ```python
  @pytest.fixture(scope="module")
  def ice_ih_candidate():
      phase_info = lookup_phase(250, 0.1)
      gen = IceStructureGenerator(phase_info, 96)
      candidates = gen.generate_all(1)
      return candidates[0]
  ```

- Chain fixture building (incremental composition):
  ```python
  @pytest.fixture
  def custom_structure(simple_interface):
      """CustomMoleculeStructure: interface + 1 ethanol molecule."""
      ...

  @pytest.fixture
  def solute_structure(interface_with_ch4_guests):
      """SoluteStructure with 1 CH4 solute molecule."""
      ...

  @pytest.fixture
  def ion_structure(simple_interface):
      """Minimal IonStructure: 2 water + 1 Na + 1 Cl."""
      ...
  ```

**Subprocess Test Helper:**
- `run_quickice(*args, timeout=60)` in `tests/conftest.py` — the canonical subprocess CLI test helper
- Import pattern: `from tests.conftest import run_quickice`
- Returns `tuple[int, str, str]` — `(return_code, stdout, stderr)`
- Default timeout: 60 seconds
- Uses canonical invocation: `python -m quickice` (not `quickice.py`)
  ```python
  def run_quickice(*args: str, timeout: int = 60) -> tuple[int, str, str]:
      import subprocess, sys
      cmd = [sys.executable, "-m", "quickice"] + list(args)
      result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
      return result.returncode, result.stdout, result.stderr
  ```

**Location:**
- Root conftest: `tests/conftest.py` — expensive GenIce2 fixtures (module-scoped) + `run_quickice()` subprocess helper
- Export conftest: `tests/test_output/conftest.py` — synthetic structures + mock dialog factories
- Project conftest: `conftest.py` — custom marker registration
- Inline fixtures: per-class or per-file `@pytest.fixture` for test-specific data
- Shared helpers: `tests/e2e_export_helpers.py` — chain-building + GRO/TOP parsing

## Coverage

**Requirements:** Not enforced (no coverage target, no `pytest-cov` installed)

**Coverage file:** `.coverage` exists at project root (from previous runs)

**View Coverage:**
```bash
# pytest-cov is NOT currently installed; add with: pip install pytest-cov
pytest --cov=quickice --cov-report=html
# Then open htmlcov/index.html
```

## Test Types

**Unit Tests:**
- Pure logic with no external dependencies
- Test data validation, mapping functions, scoring, configuration
- Files: `test_validators.py`, `test_ranking.py`, `test_structure_generation.py` (mapping/class tests)
- Pattern: Create minimal synthetic objects, test single behavior per method
- No Qt dependencies, no GenIce2 calls

**Integration/Bridge Tests:**
- Test pipeline stages with real GenIce2 computation
- Verify data flows correctly between modules
- Files: `test_structure_generation.py` (generation tests), `test_e2e_ice_generation.py`, `test_e2e_workflow_chains.py`
- Pattern: Use conftest fixtures for shared expensive structures, build chains inline

**CLI Integration Tests (Subprocess):**
- Test CLI argument validation and routing via subprocess
- Verify exit codes: 0=success, 1=runtime error, 2=argument error
- Verify stderr/stdout separation: `[PROGRESS]` on stderr, clean output on stdout
- Files: `test_cli_integration.py`, `test_entry_point.py`
- Pattern: `run_quickice(args...) → (rc, stdout, stderr)`, assert on return code and output
- No `@pytest.mark.slow` needed for fast flag-validation tests

**CLI Pipeline E2E Tests (Subprocess):**
- Test full pipeline workflows with real GenIce2 computation via subprocess
- Verify file output: GRO, TOP, ITP files exist and contain correct data
- Files: `test_cli_pipeline.py` (marked `@pytest.mark.slow`)
- Pattern: create temp output dir, run pipeline, assert file existence, cleanup in finally
- Test classes: `TestPipelineFlagValidation`, `TestPipelineExitCodes`, `TestPipelineProgressReporting`, `TestPipelineBasicWorkflows`, `TestPipelineAdvancedWorkflows`, `TestPipelineExportCorrectness`

**E2E Tests:**
- Full pipeline from phase lookup through GROMACS export validation
- Includes `gmx grompp` validation against actual GROMACS binary
- Files: `test_e2e_gmx_validation.py`, `test_e2e_chain_export_1.py`, `test_e2e_chain_export_2.py`
- Pattern: Generate structure → export GRO/TOP/ITP → stage ITP files → run grompp → assert exit code 0

**Regression Tests:**
- Named by bug ID: `TestBUG05`, `TestMW01`, `TestDEFLT01`, `TestTREE01`, `TestATOM01`, `TestRNG01`
- Each class verifies a specific bug is fixed and cannot regress
- Files: `test_scancode_bugs_gromacs.py`, `test_scancode_bugs_ion.py`, `test_scancode_bugs_inserters.py`

**GUI Export Tests:**
- Test GROMACS/PDB export with mocked Qt dialogs
- Verify file contents (atom counts, residue names, topology sections)
- Located in `tests/test_output/`

## Common Patterns

**Subprocess CLI Testing:**
```python
from tests.conftest import run_quickice

def test_valid_inputs():
    returncode, stdout, stderr = run_quickice(
        "--temperature", "273", "--pressure", "0.1", "--nmolecules", "100",
        timeout=10,
    )
    assert returncode == 0
    assert "Temperature: 273.0K" in stdout

def test_invalid_args_exit_code_2():
    rc, _, stderr = run_quickice(
        "-T", "270", "-P", "0.1", "--interface", "--mode", "slab",
        "--box-x", "3", "--box-y", "3", "--box-z", "5",
        "--ice-thickness", "1.5",
        # Missing --water-thickness for slab mode
        timeout=120,
    )
    assert rc == 2
```

**CLI Pipeline File Output Testing:**
```python
@pytest.mark.slow
def test_interface_slab(self):
    outdir = make_temp_output_dir()
    try:
        rc, _, stderr = run_quickice(
            "-T", "270", "-P", "0.1",
            "--interface", "--mode", "slab",
            "--box-x", "3", "--box-y", "3", "--box-z", "5",
            "--ice-thickness", "1.5", "--water-thickness", "2.0",
            "-o", outdir,
            timeout=120,
        )
        assert rc == 0
        outpath = Path(outdir)
        assert (outpath / "interface.gro").exists()
        assert (outpath / "interface.top").exists()
        assert (outpath / "tip4p-ice.itp").exists()
    finally:
        shutil.rmtree(outdir, ignore_errors=True)
```

**Async/Worker Testing:**
- Not directly tested — GUI worker threads are tested indirectly via export results
- `pytest-qt` is NOT installed; GUI-dependent tests use `@pytest.mark.skip`

**Error Testing:**
```python
# Custom exceptions with attributes
with pytest.raises(UnsupportedPhaseError) as exc_info:
    get_genice_lattice_name("ice_xxx")
assert exc_info.value.phase_id == "ice_xxx"

# Error message content verification
with pytest.raises(UnknownPhaseError) as exc_info:
    lookup_phase(500, 500)
assert "500" in str(exc_info.value)

# CLI validator error type
with pytest.raises(ArgumentTypeError) as exc_info:
    validate_temperature("-1")
assert "temperature" in str(exc_info.value).lower()

# CLI subprocess error — exit code + stderr message
rc, _, stderr = run_quickice("--temperature", "-1", "--pressure", "100", "--nmolecules", "100")
assert rc != 0
assert "Temperature must be between 0 and 500K" in stderr
```

**Parameterized Testing:**
```python
@pytest.mark.parametrize(
    "phase_id",
    ["ice_ih", "ice_ic", "ice_iii", "ice_vi", "ice_vii", "ice_viii"],
)
def test_all_orthogonal_phases_generate_successfully(self, phase_id):
    T, P = PHASE_CONDITIONS[phase_id]
    phase_info = lookup_phase(T, P)
    gen = IceStructureGenerator(phase_info, 96)
    candidates = gen.generate_all(1, base_seed=42)
    assert len(candidates) >= 1
```

**Invariant Testing:**
```python
# Structural invariants across all molecules
def test_ice_candidate_has_correct_atom_count(self, ice_ih_candidate):
    candidate = ice_ih_candidate
    atoms_per_molecule = 3  # TIP3P: O, H, H
    expected_atoms = candidate.nmolecules * atoms_per_molecule
    assert len(candidate.positions) == expected_atoms
```

**GROMACS File Validation:**
```python
# Parse and verify GRO file content
gro_path = Path(save_path)
lines = gro_path.read_text().splitlines()
atom_count = int(lines[1].strip())
assert atom_count == 4  # 1 molecule * 4 atoms (TIP4P-ICE)

# Parse and verify TOP [molecules] section
from e2e_export_helpers import parse_top_molecules
molecules = parse_top_molecules(top_path)
assert molecules["SOL"] == expected_water_count

# Run actual gmx grompp
exit_code, stderr = run_gmx_grompp(workspace, gro_file="f1.gro", top_file="f1.top")
assert exit_code == 0, f"gmx grompp failed for F1:\n{stderr[-500:]}"
```

**Entry Routing Testing:**
```python
# Subprocess-based routing tests
def test_no_args_shows_usage(self):
    rc, stdout, stderr = run_quickice()
    assert rc == 0
    assert "python -m quickice" in stdout

def test_cli_with_pipeline_flags(self):
    rc, stdout, stderr = run_quickice(
        "--cli", "-T", "250", "-P", "0.1", "-N", "96", "--no-diagram",
        timeout=60,
    )
    assert rc == 0
    assert "Temperature: 250.0K" in stdout

# Mock-based routing tests (direct function call)
def test_gui_missing_pyside6_error(self, capsys):
    from quickice.entry import main
    with unittest.mock.patch('quickice.entry._is_pyside6_available', return_value=False):
        rc = main(['quickice', '--gui'])
    assert rc == 1
```

**Test Data Paths:**
```python
# Standard pattern for referencing test data files
DATA_DIR = Path(__file__).resolve().parent.parent / "quickice" / "data" / "custom"
ETOH_GRO = DATA_DIR / "etoh.gro"
ETOH_ITP = DATA_DIR / "etoh.itp"

# GROMACS MDP file for grompp validation
MDP_PATH = Path(__file__).resolve().parent / "em.mdp"
```

## Fixture Scoping Strategy

| Scope | Use Case | Example |
|-------|----------|---------|
| `function` (default) | Synthetic test data, mock dialogs | `simple_candidate`, `mock_save_dialog` |
| `class` | Per-class chain building | `@pytest.fixture(autouse=True) _build_chain` |
| `module` | Expensive GenIce2 structures | `ice_ih_candidate`, `hydrate_sI_ch4_candidate` |
| `session` | Not used | — |

**Key principle:** Module-scoped fixtures amortize GenIce2 generation cost (~3-5s each) across all tests in a file. The conftest.py comment explicitly states this design intent.

## Writing New Tests — Guidelines

1. **Place unit tests** in `tests/test_<feature>.py`
2. **Place E2E tests** in `tests/test_e2e_<workflow>.py`
3. **Place export tests** in `tests/test_output/test_gromacs_export_<tab>.py`
4. **Place regression tests** in `tests/test_scancode_bugs_<area>.py` with bug ID class names
5. **Place CLI integration tests** in `tests/test_cli_integration.py` or `tests/test_cli_pipeline.py`
6. **Use `run_quickice(*args, timeout=N)`** from `tests.conftest` for all subprocess CLI tests
7. **Use module-scoped fixtures** for any GenIce2-dependent structure generation
8. **Never import Qt modules** in API-level tests; mock `QFileDialog`/`QMessageBox` for export tests
9. **Use `e2e_export_helpers.py`** for chain-building helpers; do NOT import from other test files
10. **Add `@pytest.mark.slow`** for tests taking >5 seconds (GenIce2 generation, subprocess pipeline)
11. **Assert with descriptive messages** on non-obvious checks, especially for regression tests
12. **Test GROMACS compatibility** by verifying `gmx grompp` exit code 0 for new export features
13. **Test CLI exit codes**: 0=success, 1=runtime error, 2=argument error
14. **Verify stderr/stdout separation** for CLI pipeline tests: `[PROGRESS]` on stderr only
15. **Always cleanup temp directories** in CLI pipeline tests: `try/finally` with `shutil.rmtree(outdir, ignore_errors=True)`

---

*Testing analysis: 2026-06-15*
