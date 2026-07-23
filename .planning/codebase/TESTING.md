# Testing Patterns

**Analysis Date:** 2026-07-23

## Test Framework

**Runner:**
- pytest `>=9.0.0` (from `requirements-dev.txt`), on Python 3.14 in the `quickice` conda env.
- **No `pytest.ini`, no `pyproject.toml`, no `setup.cfg`, no `.coveragerc`.** Pure default discovery.
- The only pytest configuration is in `conftest.py` files:
  - `conftest.py` (project root): registers the custom `slow` marker via `pytest_configure` (`conftest.py:9-11`).
  - `tests/conftest.py`: defines `gmx_skipif`, module-scoped structure fixtures, and `run_quickice` subprocess helper.
  - `tests/test_output/conftest.py`: defines synthetic structure fixtures + QFileDialog/QMessageBox mock factory fixtures.

**Assertion Library:**
- Plain `assert` with explanatory message strings: `assert cond, f"..."`. No `unittest.TestCase` style.

**Run Commands:**
```bash
pytest                                              # Run all tests (~1007 per AGENTS.md)
pytest tests/test_foo.py                            # Single file
pytest -k "test_pbc"                                # Match by name substring
pytest -x                                           # Stop on first failure
pytest -m "not slow"                                # Deselect slow-marked tests
pytest --timeout=120                                # With timeout (if pytest-timeout installed)
pytest --cov=quickice --cov-report=term-missing     # Coverage
```
- Tests run from the project root with `PYTHONPATH` including the project root (`setup.sh` handles this). The `quickice` conda env MUST be active.

## Test File Organization

**Location:**
- `tests/` (flat root) for unit + e2e tests.
- `tests/test_cli/` for CLI subprocess integration tests (has `__init__.py`).
- `tests/test_output/` for GROMACS export e2e tests (has `__init__.py` + own `conftest.py`).
- `tests/scancode/` for regression tests against scancode-identified bugs (has `__init__.py`).
- Each test subdirectory is a Python package (`__init__.py` present) so `from tests.conftest import gmx_skipif` works.

**Naming:**
- `test_*.py` — unit tests: `tests/test_moleculetype_registry.py`, `tests/test_gro_resname_validation.py`, `tests/test_tip4p_ice_lj_values.py`.
- `test_e2e_*.py` — end-to-end tests that exercise real GenIce2 structures + the full writer/pipeline chain: `tests/test_e2e_ice_interface_export.py`, `tests/test_e2e_gmx_validation.py`, `tests/test_e2e_workflow_chains.py`.
- `test_scancode_bugs_*.py` — regression tests for scancode-flagged bugs (byte-equivalence + source-text guards): `tests/scancode/test_scancode_bugs_constants.py`, `tests/scancode/test_scancode_bugs_pipeline.py`.
- Helper modules MUST NOT start with `test_` (they are not collected): `tests/e2e_export_helpers.py`, `tests/_capture_gro_top_baseline.py`.

**Counts:** ~138 collected `test_*.py` files; 43 `test_e2e_*`; 17 `test_scancode_bugs_*`; 6 non-collected helpers. AGENTS.md documents ~1007 tests (parametrize expands this further).

**Structure:**
```
tests/
├── conftest.py                 # gmx_skipif, module-scoped GenIce2 fixtures, run_quickice
├── e2e_export_helpers.py       # chain builders + GRO/TOP/ITP parsers + run_gmx_grompp
├── em.mdp                      # GROMACS energy-minimization MDP for grompp tests
├── test_*.py                   # unit + e2e tests (flat)
├── test_cli/
│   ├── __init__.py
│   └── test_cli_pipeline.py    # subprocess CLI integration
├── test_output/
│   ├── __init__.py
│   ├── conftest.py             # synthetic structure fixtures + mock dialog factories
│   └── test_gromacs_export_*.py # per-Tab exporter e2e
└── scancode/
    ├── __init__.py
    └── test_scancode_bugs_*.py # regression tests
```

## Test Structure

**Suite Organization:**
Group related tests in a class named `Test<Subject>`. Classes are NOT `pytest.TestCase` subclasses — they are plain classes with `test_*` methods. Both the class and each method carry a docstring stating what is verified and why.

```python
# From tests/test_moleculetype_registry.py
class TestHydrateGuestNaming:
    """Test that hydrate guests use _H suffix (not _HYD)."""

    def test_register_hydrate_guest_ch4(self):
        """CH4 hydrate guest registers as CH4_H."""
        registry = MoleculetypeRegistry()
        result = registry.register_hydrate_guest('CH4')
        assert result == 'CH4_H', f"Expected 'CH4_H', got '{result}'"
```

```python
# From tests/test_e2e_ice_interface_export.py — scenario-class grouping
class TestIceCandidateExport:
    """Validate Ice Candidate export via write_gro_file / write_top_file.
    Ice candidate has only SOL residues (TIP4P-ICE water model). ..."""

    def test_gro_only_sol_residues(self, ice_ih_candidate, tmp_path):
        gro_path = str(tmp_path / "ice.gro")
        write_gro_file(ice_ih_candidate, gro_path)
        residue_names = parse_gro_residue_names(gro_path)
        assert set(residue_names) == {"SOL"}, (
            f"Ice candidate GRO should have only SOL residues, got {set(residue_names)}"
        )
```

**Section dividers in test files:**
- `# ═══...` (heavy box-drawing) for major scenarios (`tests/test_e2e_ice_interface_export.py:50`).
- `# ── Title ──...` for subsections (`tests/conftest.py`, `tests/e2e_export_helpers.py`).
- `# ---------------------------------------------------------------------------` (72 dashes) for grouping blocks.

**Assertion pattern:**
- Always include an explanatory message: `assert cond, f"expected X, got {actual}"`. Messages state what was expected and what was observed so failures are self-diagnosing.

**Patterns:**
- Setup: prefer fixtures over `setup_method`. Expensive structures come from module-scoped conftest fixtures (see Fixtures). Cheap per-test setup is inline in the test body.
- Teardown: rely on `tmp_path` (auto-cleaned). Persistent workspaces (`gmx_workspace`) use `yield` and intentionally leave files for debugging.
- Assertion: plain `assert cond, msg`. Error-case assertions use `with pytest.raises(ValueError, match="...substring..."):`.

## Fixtures

**Framework:** pytest built-in fixtures + project-defined fixtures in `conftest.py` files.

**Module-scoped fixtures (amortize expensive GenIce2 calls, ~3-5s each)** — defined in `tests/conftest.py:50-217`:
```python
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
    config = InterfaceConfig(mode="slab", box_x=3.0, box_y=3.0, box_z=8.0,
                              seed=42, ice_thickness=2.0, water_thickness=4.0)
    return generate_interface(ice_ih_candidate, config)
```
Available module-scoped fixtures: `ice_ih_candidate`, `ice_ic_candidate`, `hydrate_sI_ch4_candidate`, `hydrate_sI_thf_candidate`, `hydrate_sII_ch4_candidate`, `hydrate_sI_ch4_structure`, `hydrate_sI_thf_structure`, `hydrate_sII_ch4_structure`, `hydrate_sII_thf_structure`, `interface_slab`, `interface_pocket`, `interface_hydrate_slab`. Use these whenever a test needs a real generated structure; do NOT regenerate inline.

**Function-scoped synthetic fixtures** — defined in `tests/test_output/conftest.py:45-419`:
```python
@pytest.fixture
def simple_candidate():
    """1-molecule ice Candidate with 3 atoms (O, H, H)."""
    positions = np.array([[0.1, 0.1, 0.1], [0.15, 0.12, 0.1], [0.08, 0.12, 0.1]])
    return Candidate(positions=positions, atom_names=["O","H","H"],
                     cell=np.array([[0.9,0,0],[0,0.78,0],[0,0,0.72]]),
                     nmolecules=1, phase_id="ice_ih", seed=42, metadata={})
```
Use synthetic fixtures (no GenIce2) for unit tests of writers/validators — fast and deterministic. Available: `simple_candidate`, `ranked_candidate`, `simple_hydrate_config`, `simple_hydrate_structure`, `simple_interface`, `interface_with_ch4_guests`, `interface_with_thf_guests`, `custom_structure`, `solute_structure`, `ion_structure`.

**`tmp_path` (built-in):** use for all temp file outputs; auto-cleaned after the test.
```python
def test_gro_only_sol_residues(self, ice_ih_candidate, tmp_path):
    gro_path = str(tmp_path / "ice.gro")
    write_gro_file(ice_ih_candidate, gro_path)
```

**`gmx_workspace` (persistent, NOT auto-cleaned):** for GROMACS `gmx grompp` debugging. Files persist under `tmp/e2e-gmx-validation/<test_name>/` after the run (`tests/test_e2e_gmx_validation.py:64-74`):
```python
@pytest.fixture
def gmx_workspace(request):
    base = Path(__file__).parent.parent / "tmp" / "e2e-gmx-validation"
    workspace = base / request.node.name.replace("::", "_")
    workspace.mkdir(parents=True, exist_ok=True)
    yield workspace
```

**Factory fixtures (return a callable):** for QFileDialog/QMessageBox mocking (`tests/test_output/conftest.py:426-498`):
```python
@pytest.fixture
def mock_save_dialog(tmp_path):
    """Factory: mock_save_dialog('out.gro') -> (save_path, dialog_patch, mb_patch)."""
    def _create(filename="test.gro"):
        save_path = str(tmp_path / filename)
        dialog_patch = patch('quickice.gui.export.QFileDialog.getSaveFileName',
                             return_value=(save_path, "GRO Files (*.gro)"))
        mb_patch = patch('quickice.gui.export.QMessageBox')
        return save_path, dialog_patch, mb_patch
    return _create

# Usage:
def test_export_creates_files(self, ranked_candidate, mock_save_dialog):
    save_path, dialog_p, mb_p = mock_save_dialog("ice_test.gro")
    exporter = GROMACSExporter(parent_widget=None)
    with dialog_p, mb_p:
        result = exporter.export_gromacs(ranked_candidate, T=195, P=1.36)
    assert result is True
```

## Mocking

**Framework:** `unittest.mock.patch` + pytest's `monkeypatch`.

**Patterns:**

1. **QFileDialog / QMessageBox (GUI export tests)** — `patch` the class method on the specific module under test:
```python
# From tests/test_output/test_gromacs_export_ice.py
dialog_patch = patch('quickice.gui.export.QFileDialog.getSaveFileName',
                     return_value=(save_path, "GRO Files (*.gro)"))
mb_patch = patch('quickice.gui.export.QMessageBox')
with dialog_patch, mb_patch:
    result = exporter.export_gromacs(ranked_candidate, T=195, P=1.36)
```

2. **Headless Qt (GUI panel tests)** — `monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")` + singleton `QApplication` guard:
```python
# From tests/test_hydrate_panel.py
@pytest.fixture
def panel(self, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    if not QApplication.instance():
        QApplication(sys.argv)
    return HydratePanel()
```

3. **Replace a function to assert it is NOT called** (regression guards):
```python
# From tests/test_output/test_interface_gro_custom_guest.py:136
def test_custom_branch_skips_detect(tmp_path, monkeypatch):
    def boom(_atom_names):
        raise AssertionError("detect_guest_type_from_atoms should not be called")
    monkeypatch.setattr(
        "quickice.output.gromacs_writer.detect_guest_type_from_atoms", boom)
    write_interface_gro_file(iface, str(out_path), custom_guest_info=custom_guest_info)
    # No raise => the custom branch correctly bypassed the heuristic.
```

4. **cwd-controlled tests (path containment)** — `monkeypatch.chdir(work_dir)`:
```python
# From tests/scancode/test_scancode_bugs_pipeline.py:246
def test_output_outside_cwd_raises_value_error(self, tmp_path, monkeypatch):
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)
    outside_output = (tmp_path / "escape").as_posix()
    pipeline = self._make_pipeline(outside_output)
    with pytest.raises(ValueError, match="--output path resolves outside"):
        pipeline.execute()
```

5. **Suppress modal dialogs** — `monkeypatch.setattr(QMessageBox, "warning", lambda *a, **kw: QMessageBox.Ok)` (`tests/test_hydrate_panel.py:298`).

**What to Mock:**
- QFileDialog / QMessageBox in GUI exporter tests.
- Environment variables (`QT_QPA_PLATFORM`) for headless Qt.
- `cwd` for path-containment tests.
- Specific functions whose call/no-call is the invariant under test.

**What NOT to Mock:**
- The structure generators (`IceStructureGenerator`, `HydrateStructureGenerator`) — use the real ones via module-scoped conftest fixtures (slow but genuine e2e coverage).
- `genice2` itself — exercise the real GenIce2 pipeline; only skip when `gmx` is absent (via `@gmx_skipif`).
- The writer functions under test — call them directly on real/synthetic structures.

## Fixtures and Factories

**Test Data:**
- Synthetic structures built inline in fixtures with explicit `np.array` positions and `MoleculeIndex` lists (see `simple_interface`, `interface_with_ch4_guests` in `tests/test_output/conftest.py`).
- Bundled ITP/GRO data lives in `quickice/data/` and `quickice/data/custom/` (e.g., `etoh.gro`, `etoh.itp`, `tip4p-ice.itp`, `ch4.itp`, `ch4_hydrate.itp`). Locate via `Path(quickice.__file__).parent / "data"` (see `tests/test_e2e_ice_interface_export.py:44-47`, `tests/e2e_export_helpers.py:44-46`).

**Location:**
- Shared structure fixtures: `tests/conftest.py` (real GenIce2) and `tests/test_output/conftest.py` (synthetic).
- Test-local helpers (chain builders, parsers): `tests/e2e_export_helpers.py` (NOT collected; imported via `sys.path.insert`).
- Test-local constants: `PHASE_CONDITIONS` dict in `tests/conftest.py:38-45`; `ETOH_GRO`/`ETOH_ITP` paths in `tests/e2e_export_helpers.py:45-46`; MD5 baselines `TOP_MD5_BASELINE`/`ITP_MD5_BASELINE` in `tests/scancode/test_scancode_bugs_constants.py:67-68`.

**Chain-building helpers (`tests/e2e_export_helpers.py`):** use these to build multi-step structures instead of re-deriving the chain in each test:
```python
from e2e_export_helpers import (
    _make_slab_interface, _insert_custom_molecules, _insert_solutes,
    _insert_ions, _insert_ions_from_solute,
    parse_gro_residue_names, parse_gro_atom_count, parse_top_molecules,
    parse_top_includes, assert_gro_residue_ordering, assert_gro_top_consistent,
    assert_itp_completeness, _stage_itp_files, run_gmx_grompp, MDP_PATH,
)
```
Import pattern (add `tests/` to `sys.path` because conftest import is unreliable):
```python
sys.path.insert(0, str(Path(__file__).parent))
from e2e_export_helpers import parse_gro_residue_names, ...
```

## GROMACS-Dependent Tests

**Marker:** `gmx_skipif` defined in `tests/conftest.py:24-27`:
```python
def _gmx_available():
    return shutil.which("gmx") is not None

gmx_skipif = pytest.mark.skipif(
    not _gmx_available(), reason="GROMACS (gmx) not found on PATH"
)
```

**Usage:** import and apply as a decorator on the class OR individual function:
```python
from tests.conftest import gmx_skipif

@gmx_skipif
class TestIceCandidateGmxValidation:
    def test_gmx_grompp_succeeds(self, gmx_workspace): ...

@gmx_skipif
def test_gmx_grompp_constants_refactor(ice_ih_candidate, tmp_path): ...
```

**grompp helper:** `run_gmx_grompp(workspace, gro_file="struct.gro", top_file="struct.top", mdp_file="em.mdp", tpr_file="em.tpr", maxwarn=5) -> tuple[int, str]` in `tests/e2e_export_helpers.py:591-634`. It cleans stale `.tpr` backups, runs `gmx grompp` via subprocess, returns `(exit_code, stderr_text)`. Assert `exit_code == 0`.

## Coverage

**Requirements:** None enforced. No coverage gate in CI.

**View Coverage:**
```bash
pytest --cov=quickice --cov-report=term-missing
```
(`pytest-cov` must be installed; it is implied by the `--cov` usage in AGENTS.md but not pinned in `requirements-dev.txt`.)

## Test Types

**Unit Tests:**
- Scope: a single function/class with synthetic inputs. Fast (no GenIce2).
- Examples: `tests/test_moleculetype_registry.py` (registry naming), `tests/test_gro_resname_validation.py` (5-char GRO limit), `tests/test_tip4p_ice_lj_values.py` (LJ magnitudes), `tests/test_output/test_gro_format_helpers.py`.
- Fixtures: synthetic structures from `tests/test_output/conftest.py`.

**Integration / E2E Tests:**
- Scope: real GenIce2 structures → writer functions → parsed GRO/TOP/ITP → invariants. Some run `gmx grompp`.
- Examples: `tests/test_e2e_ice_interface_export.py`, `tests/test_e2e_gmx_validation.py`, `tests/test_e2e_workflow_chains.py`, `tests/test_pbc_wrapping.py`.
- Fixtures: module-scoped real-structure fixtures from `tests/conftest.py` + `tmp_path` / `gmx_workspace`.

**Regression Tests (`tests/scancode/test_scancode_bugs_*.py`):**
- Scope: a specific bug identified by scancode, with byte-equivalence and/or source-text guards so it cannot recur.
- Pattern A — **byte-equivalence**: MD5 snapshot of writer output must match a pre-refactor baseline:
  ```python
  TOP_MD5_BASELINE = "bb3df33e131a5d18c5f5439eaa0c29b2"
  def test_top_byte_equivalence(self, ice_ih_candidate, tmp_path):
      write_top_file(ice_ih_candidate, str(tmp_path / "ice_ih.top"))
      md5 = hashlib.md5(Path(tmp_path/"ice_ih.top").read_text().encode()).hexdigest()
      assert md5 == TOP_MD5_BASELINE, f"... refactor must be byte-equivalent ..."
  ```
- Pattern B — **source-text grep**: read `quickice/output/*.py` and assert a forbidden literal/pattern is absent:
  ```python
  def test_no_comb_rule_1(self):
      source = "\n".join(p.read_text() for p in sorted(Path("quickice/output").glob("*.py")))
      assert "0.31668e-3" not in source, "Buggy sigma value found in source"
  ```
- Pattern C — **count definitions**: assert a constant is defined exactly once across the package (`_count_tip4p_ice_alpha_defs()` in `tests/scancode/test_scancode_bugs_constants.py:93-102`).

**GUI Tests:**
- Headless via `QT_QPA_PLATFORM=offscreen` (monkeypatched). Singleton `QApplication` guard. QFileDialog/QMessageBox patched.
- Examples: `tests/test_hydrate_panel.py` (panel rendering + `get_configuration` round-trip), `tests/test_output/test_gromacs_export_*.py` (per-Tab exporter e2e), `tests/test_custom_molecule_renderer.py`.

**CLI Tests:**
- Subprocess-based via `run_quickice(*args, timeout=60)` from `tests/conftest.py:222-247` (runs `python -m quickice`). Assert on `(returncode, stdout, stderr)`.
- Exit-code convention: `0` success, `1` runtime error, `2` argparse error.
- Examples: `tests/test_cli/test_cli_pipeline.py`, `tests/test_cli/test_cli_integration.py`. Output dirs go under `<cwd>/tmp/` (not system `/tmp`) because `CLIPipeline` rejects `--output` outside cwd (SEC-05).

## Common Patterns

**Parametrize (matrix testing):**
```python
# From tests/test_hydrate_lattice_types.py — iterate all HYDRATE_LATTICES keys
@pytest.mark.parametrize("lattice_type", list(HYDRATE_LATTICES.keys()))
def test_all_required_keys_present(self, lattice_type):
    entry = HYDRATE_LATTICES[lattice_type]
    assert {"genice_name","description","cages","unit_cell_molecules",
            "cage_type_map","is_triclinic","is_water_only"} <= set(entry.keys())

# From tests/scancode/test_scancode_bugs_inserter_perf.py — seed stability
@pytest.mark.parametrize("seed", [0, 1, 2, 42, 123, 999])
def test_insertion_reproducible(self, seed): ...
```

**Error Testing:**
```python
# Exact exception + message substring
with pytest.raises(ValueError, match="5-character GRO format limit"):
    validate_gro_residue_name("ETHANOL")

# Containment check
with pytest.raises(ValueError, match="--output path resolves outside"):
    pipeline.execute()

# Assert an operation does NOT raise (prove a guard passed)
try:
    rc = pipeline.execute()
except ValueError as e:
    pytest.fail(f"in-cwd --output raised ValueError (containment check is wrong): {e}")
assert isinstance(rc, int)
```

**Async Testing:** Not applicable — the codebase has no `async`/`await`. `QThread` workers (`HydrateWorker`, `IonInsertionWorker`, `CustomMoleculeWorker`) are tested by calling the underlying computation functions (`insert_ions`, `generate`) directly, NOT by driving the thread event loop.

**Byte-equivalence regression (refactor guards):** When refactoring constants/formatting, capture a pre-refactor MD5 baseline and assert post-refactor output matches. Example: `tests/scancode/test_scancode_bugs_constants.py:67-68, 417-431`.

**GRO/TOP/ITP parsing in tests:** Use the shared parsers in `tests/e2e_export_helpers.py` (`parse_gro_residue_names`, `parse_gro_atom_count`, `parse_top_molecules`, `parse_top_includes`, `check_itp_has_moleculetype`) rather than re-implementing GROMACS format parsing per test. For cross-file consistency use `assert_gro_top_consistent(gro_path, top_path)` and `assert_itp_completeness(top_path, workspace)`.

**`sys.path` for helper imports:** Because conftest import can be unreliable across subdirectories, tests that need `e2e_export_helpers` insert the `tests/` dir explicitly:
```python
sys.path.insert(0, str(Path(__file__).parent))          # tests/ at root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # from tests/scancode/
```

---

*Testing analysis: 2026-07-23*
