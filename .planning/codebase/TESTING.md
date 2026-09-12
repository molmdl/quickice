# Testing Patterns

**Analysis Date:** 2026-09-12

## Test Framework

**Runner:**
- pytest `>=9.0.0` (from `requirements-dev.txt`), on Python 3.14.3 in the `quickice` conda env.
- **No `pytest.ini`, no `pyproject.toml`, no `setup.cfg`.** Pure default discovery.
- pytest configuration lives ONLY in `conftest.py` files:
  - `conftest.py` (project root): registers the `slow` marker via `pytest_configure` (`conftest.py:9-11`).
  - `tests/conftest.py`: registers `slow`/`e2e`/`gui`/`cli` markers, enforces `QT_QPA_PLATFORM=offscreen` at session start (`tests/conftest.py:18`, BEFORE any Qt import), defines `gmx_skipif`, module-scoped GenIce2 fixtures, `PHASE_CONDITIONS`, and the `run_quickice` subprocess helper.
  - `tests/test_output/conftest.py`: synthetic structure fixtures + QFileDialog/QMessageBox mock factory fixtures.
  - **`tests/e2e/` contains NO conftest.py by design** (INFRA collision rule, stated in `tests/e2e/__init__.py`): an e2e conftest must not shadow `test_output` fixture names (`custom_structure`, `solute_structure`, `ion_structure`) — simplest rule: none at all. Shared e2e fixtures live in the plain module `tests/e2e_chain_fixtures.py` instead.

**Assertion Library:**
- Plain `assert` with explanatory message strings: `assert cond, f"..."`. No `unittest.TestCase` style.

**Run Commands:**
```bash
pytest                                              # Run all tests (~1846 collected)
pytest tests/test_foo.py                            # Single file
pytest -k "test_pbc"                                # Match by name substring
pytest -x                                           # Stop on first failure
pytest -m "not slow"                                # Deselect slow-marked tests
pytest --cov=quickice --cov-report=term-missing     # Coverage
```

**Full suite (canonical, headless — GATE-FULL in `.planning/phases/48.3-revise-tests-true-e2e/GATES.md`):**
```bash
QT_QPA_PLATFORM=offscreen timeout 900 python -m pytest -q     # ~4-5 min
```
- The external `timeout 900` guard is MANDATORY. pytest-timeout's SIGALRM **cannot interrupt C-level hangs** (Qt XCB, VTK) — prevention via env guards is the only cure. Never run a bare full suite without it.
- Gate commands for phase verification are defined once in `.planning/phases/48.3-revise-tests-true-e2e/GATES.md` (GATE-COUNT / GATE-IDS / GATE-SUBSET / GATE-FULL); downstream plans reference gate names, never redefine commands.
- GATE-SUBSET (e2e subset) post-48.3-21 form: `QT_QPA_PLATFORM=offscreen python -m pytest tests/e2e/ tests/test_gro_top_byte_equivalence.py -q`.
- Tests run from the project root with `PYTHONPATH` including the project root (`setup.sh` handles this). The `quickice` conda env MUST be active.

## True E2E Definition (authoritative, from AGENTS.md)

An e2e test:
1. **Builds structures via REAL generators/inserters** (`IceStructureGenerator`, `HydrateStructureGenerator`, `assemble_slab`, `IonInserter`, `SoluteInserter`, `CustomMoleculeInserter`) — never synthetic substitutes,
2. **Exports through a REAL pipeline surface** — one of: the GUI exporter (`GROMACSExporter` / per-tab exporters), `CLIPipeline._run_export_step`, a subprocess (`run_quickice`), or real MainWindow menu handlers,
3. **Asserts `gmx grompp` rc==0 when gmx is present** (via `@gmx_skipif`).

Files live in `tests/e2e/<feature>/`. File-parsing-only tests and curated-fixture-only tests are NOT true e2e.

## Test File Organization

**Location:** feature-organized e2e tree + flat root for unit/regression tests.

**Counts:** 141 collected `test_*.py` files; ~1846 collected tests. Breakdown: 39 e2e files (38 under `tests/e2e/<feature>/` + 1 at `tests/e2e/` root), 17 in `tests/scancode/`, 9 in `tests/test_cli/`, 19 in `tests/test_output/`, 57 at `tests/` root. **Root-level `tests/test_e2e_*.py` count is 0** — all were moved into the feature tree (48.3-21..24).

**Naming:**
- `test_*.py` — unit tests: `tests/test_moleculetype_registry.py`, `tests/test_gro_resname_validation.py`, `tests/test_tip4p_ice_lj_values.py`.
- `tests/e2e/<feature>/test_e2e_*.py` — true e2e tests. Features: `chains/` (cross-tab regression chains), `custom_guest/`, `export_validation/` (grompp + gmx param validation), `hydrate/`, `interface/`, `lattice/`, `solute_ion/`, plus the flagship `tests/e2e/test_e2e_gui_fullchain.py` (MainWindow-driven full chain).
- `tests/scancode/test_scancode_bugs_*.py` — regression tests for scancode-identified bugs. Newer scancode-class regressions may live at `tests/` root with the same prefix: `tests/test_scancode_bugs_custom_guest_bridge_assert.py`, `tests/test_scancode_bugs_piece_logger.py`.
- Root-level regression tests named by their issue/origin: `tests/test_uat_f_custom_guest_fixes.py` (UAT Workflow F bugs), `tests/test_thf_bonds_viewer_issue2.py` (THF viewer bonds issue), `tests/test_gro_top_byte_equivalence.py` (7-path byte contract).
- Non-collected helpers MUST NOT start with `test_`: `tests/e2e_export_helpers.py` (parsers/chain builders/grompp runner), `tests/e2e_chain_fixtures.py` (shared module-scoped chain fixtures), `tests/gui_e2e_helpers.py` (headless GUI safety infra), `tests/_capture_gro_top_baseline.py` (baseline capture script), `tests/repro_*.py` (manual repro scripts).

**Structure:**
```
tests/
├── conftest.py                 # markers, offscreen guard, gmx_skipif, GenIce2 fixtures, run_quickice
├── e2e_export_helpers.py       # GRO/TOP/ITP parsers, chain builders, _stage_itp_files, run_gmx_grompp
├── e2e_chain_fixtures.py       # shared module-scoped chain fixtures + canonical lattice constants
├── gui_e2e_helpers.py          # headless GUI safety infra (patch_gui_modals, teardown_threads, ...)
├── em.mdp                      # shared GROMACS EM MDP (rcoulomb=rvdw=1.0 → needs box > 2.0 nm)
├── _capture_gro_top_baseline.py # baseline capture script (run via python -m tests._capture_gro_top_baseline)
├── repro_*.py                  # manual GUI regression repro scripts (non-collected)
├── _baselines/                 # baseline_shas.json + snapshots/baseline/<path_name>/ (committed)
├── e2e/                        # feature-organized e2e tree — NO conftest.py (INFRA collision rule)
│   ├── chains/                 #   cross-tab regression chains (builtin sI)
│   ├── custom_guest/           #   custom guest cross-tab CLI/GUI + lattice grompp
│   ├── export_validation/      #   gmx grompp validation, param validation, ITP staging
│   ├── hydrate/                #   hydrate generation + grompp chains
│   ├── interface/              #   ice/interface generation + lattice interface CLI/GUI
│   ├── lattice/                #   mixed/builtin lattice cross-tab CLI/GUI
│   ├── solute_ion/             #   solute/ion insertion + mixed ion export
│   └── test_e2e_gui_fullchain.py  # MainWindow-driven headless full-chain (flagship)
├── test_*.py                   # 57 root unit + regression tests
├── test_cli/                   # subprocess CLI integration (has __init__.py)
├── test_output/                # per-Tab exporter e2e with synthetic fixtures (conftest.py + __init__.py)
└── scancode/                   # scancode regression tests (has __init__.py)
```

## Test Structure

**Suite Organization:**
Group related tests in a class named `Test<Subject>`. Classes are NOT `unittest.TestCase` subclasses — plain classes with `test_*` methods. Both the class and each method carry a docstring stating what is verified and why. E2E modules open with a LONG module docstring citing the plan ID, the pipeline surface under test, fixture amortization, and pitfalls avoided (see `tests/e2e/interface/test_e2e_lattice_interface_cli.py:1-63`).

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

**Section dividers in test files:**
- `# ── Title ──...` for subsections (`tests/conftest.py`, `tests/e2e_chain_fixtures.py`, `tests/test_thf_bonds_viewer_issue2.py`).
- `# ═══...` (heavy box-drawing) for major scenario/fixture boundaries (`tests/e2e_chain_fixtures.py:94,287,342`).
- `# ---------------------------------------------------------------------------` (72 dashes) for grouping blocks.

**Assertion pattern:**
- Always include an explanatory message: `assert cond, f"expected X, got {actual}"`. State what was expected and what was observed so failures are self-diagnosing.
- E2E chain tests share a per-file assertion helper instead of repeating asserts per case (e.g. `_assert_lattice_cli_export` in `tests/e2e/interface/test_e2e_lattice_interface_cli.py:132`, `_assert_residue_ordering` / `_assert_atom_conservation` in `tests/e2e/export_validation/test_e2e_gmx_validation.py:112,128`).

**Patterns:**
- Setup: prefer fixtures over `setup_method`. Expensive structures come from module-scoped fixtures (`tests/conftest.py`, `tests/e2e_chain_fixtures.py`); cheap per-test setup is inline.
- Teardown: rely on `tmp_path` (auto-cleaned). GUI e2e MUST call `teardown_threads(mw)` in fixture teardown (try/finally or finalizer) — see Mocking/Safety below. `gmx_workspace` uses `yield` and intentionally leaves files for debugging.
- Error-case assertions use `with pytest.raises(ValueError, match="...substring..."):`.

## Test Types

**Unit Tests:**
- Scope: a single function/class with synthetic inputs. Fast (no GenIce2).
- Examples: `tests/test_moleculetype_registry.py`, `tests/test_gro_resname_validation.py`, `tests/test_tip4p_ice_lj_values.py`, `tests/test_output/test_gro_format_helpers.py`.
- Fixtures: synthetic structures from `tests/test_output/conftest.py`.

**True E2E Tests (`tests/e2e/`):**
- Real generators/inserters → real pipeline surface → file asserts + `gmx grompp` rc==0. See the definition above.

**Pipeline surfaces used by e2e (pick the one matching the tab/path under test):**
- **CLI `_run_export_step` (Pattern 4):** construct `CLIPipeline(args=SimpleNamespace())`, set `_output_dir` + `_hydrate_result` (carrying `.config`) + the downstream `_<tab>_result` attribute, call `_run_export_step()` directly. Helper `_make_cli_pipeline` in `tests/e2e/interface/test_e2e_lattice_interface_cli.py:97-126`; sibling GUI half in `tests/e2e/interface/test_e2e_lattice_interface_gui.py`.
- **GUI exporter:** real per-tab exporter classes with `QFileDialog.getSaveFileName` patched in the `quickice.gui.export` namespace (`tests/e2e/custom_guest/test_e2e_custom_guest_cross_tab_gui.py:344-347`).
- **MainWindow-driven full chain:** `tests/e2e/test_e2e_gui_fullchain.py` — drives real handlers (`_on_hydrate_generate_clicked` → `_on_interface_hydrate_generate` → `_on_insert_solutes` → custom → `_on_insert_ions`) through real QThread workers, then the four real `_on_export_*_gromacs` menu handlers; validates files + `assert_itp_completeness` + `assert_gro_top_consistent` + grompp rc==0; includes a negative-path test (missing `_current_*` → warning dialog, no files) and a Tab 0 leg via `GenerationWorker.run()` synchronously.
- **Subprocess CLI:** `run_quickice(*args, timeout=60)` from `tests/conftest.py:203-228` (runs `python -m quickice`); used by `tests/test_cli/test_cli_pipeline.py`, `tests/test_cli/test_cli_integration.py`, and `tests/test_cli/test_pipeline_step_chain_e2e.py`. Exit-code convention: 0 success, 1 runtime error, 2 argparse error. Output dirs go under `<cwd>/tmp/` because `CLIPipeline` rejects `--output` outside cwd (SEC-05) — see `make_temp_output_dir()` in `tests/e2e_export_helpers.py:640-662`.

**Regression Tests (`tests/scancode/test_scancode_bugs_*.py` + root-level issue tests):**
- Scope: one specific bug, with guards so it cannot recur.
- Pattern A — **byte-equivalence**: SHA256 (or MD5) of writer output must match a committed baseline. The canonical 7-path contract is `tests/test_gro_top_byte_equivalence.py`, which loads `tests/_baselines/baseline_shas.json` (26 file SHAs across ice/interface/hydrate/ion/custom/solute/custom_guest) and reference files in `tests/_baselines/snapshots/baseline/<path_name>/`. Baselines are captured with `python -m tests._capture_gro_top_baseline` (`tests/_capture_gro_top_baseline.py`); paths are `__file__`-relative so loading is CWD-independent. Older MD5 baselines live inline in `tests/scancode/test_scancode_bugs_constants.py`.
- Pattern B — **source-text grep**: read `quickice/**/*.py` and assert a forbidden literal is absent (e.g. buggy sigma `0.31668e-3`, `comb-rule=1` in `tests/scancode/test_scancode_bugs_constants.py:448-457`).
- Pattern C — **count definitions**: assert a constant is defined exactly once across the package (`_count_tip4p_ice_alpha_defs()` in `tests/scancode/test_scancode_bugs_constants.py`).
- Pattern D — **behavior pinning**: deliberately pin a KNOWN-broken heuristic so any change to it is visible (`test_heuristic_miscounts_thf_followed_by_ch4` in `tests/test_thf_bonds_viewer_issue2.py:39-63`).

**GUI Tests:**
- Headless via `QT_QPA_PLATFORM=offscreen` (enforced at session start by `tests/conftest.py:18`; GUI e2e helpers force it harder at module import). See the GUI safety mechanics section below.
- Panel-level: `tests/test_hydrate_panel.py`, `tests/test_custom_molecule_panel_34_6.py` (singleton `QApplication` guard).
- Exporter-level: `tests/test_output/test_gromacs_export_*.py` (QFileDialog/QMessageBox mock factories).
- Full-chain: `tests/e2e/test_e2e_gui_fullchain.py` (the only test driving real MainWindow handlers end-to-end).

**CLI Tests:**
- Subprocess-based via `run_quickice()`; `tests/test_cli/test_pipeline_grompp_matrix.py` runs the full grompp matrix (module-level `pytestmark = [gmx_skipif, pytest.mark.slow]`, `tests/test_cli/test_pipeline_grompp_matrix.py:77`).

## Markers

**`gmx_skipif`** — defined in `tests/conftest.py:38-47`, imported as `from tests.conftest import gmx_skipif` (33 files import it; 31 apply it). Apply to a class OR function; or module-wide via `pytestmark`:
```python
from tests.conftest import gmx_skipif  # noqa: E402

@gmx_skipif
class TestIceCandidateGmxValidation:
    def test_gmx_grompp_succeeds(self, gmx_workspace): ...

# tests/test_cli/test_pipeline_grompp_matrix.py:77
pytestmark = [gmx_skipif, pytest.mark.slow]
```
`gmx 2023.5` is on PATH in the dev env, but every grompp test still gates on `@gmx_skipif` so the suite stays green (skips, not failures) on machines without gmx (GATES.md GROMACS note).

**Registered markers** (`conftest.py:9-11` and `tests/conftest.py:28-33`): `slow`, `e2e`, `gui`, `cli`. Only `slow` is applied to tests today (`tests/test_cli/test_cli_pipeline.py`, `tests/e2e/interface/test_ice_generation.py:88`); `e2e`/`gui`/`cli` are registered for future use — do not emit unknown-mark warnings.

## Fixtures

**Module-scoped GenIce2 fixtures** — `tests/conftest.py:70-198` (amortize expensive generation across consuming test modules; measured GenIce2 costs: ~17ms ice_ih 96-mol, ~60ms sH 2³, ~360ms sII 3³ — amortization is conventional, no longer load-bearing):
`ice_ih_candidate`, `hydrate_sI_ch4_candidate`, `hydrate_sI_ch4_structure`, `hydrate_sI_thf_structure`, `hydrate_sII_ch4_structure`, `hydrate_sII_thf_structure`, `interface_slab`, `interface_pocket`, `interface_hydrate_slab`. Use these whenever a test needs a real generated structure; do NOT regenerate inline. `PHASE_CONDITIONS` (`tests/conftest.py:58-65`) maps phase → verified (T, P) pairs.

**Shared chain fixtures** — `tests/e2e_chain_fixtures.py` (NOT a conftest; imported into test modules' namespaces, which preserves module scope). Extracted from 3 near-copy sibling fixture clusters (48.3-20, line-diff-verified identical bodies):
- `custom_guest_chains` — ethanol-guest hydrate + per-inserter slab interfaces + solute/custom/ion downstream structures per lattice (`tests/e2e/custom_guest/test_e2e_custom_guest_lattices_cli.py` + `_gui.py`).
- `lattice_chains` — hydrate → slab interface for the 6 non-blocked lattices (`tests/e2e/interface/test_e2e_lattice_interface_cli.py` + `_gui.py`).
- `filled_ice_hydrates` — c2te/ice1hte filled-ice hydrates with per-lattice minimum supercells (`tests/e2e/hydrate/test_e2e_filled_ice_cli_hydrate_grompp.py` + `tests/e2e/lattice/test_e2e_mixed_filled_ice_gui.py`).
- Also the single source of truth for canonical lattice constants imported by fixtures AND `parametrize` decorators: `CUSTOM_GUEST_LATTICES`, `INTERFACE_LATTICES(_WITH_GUESTS/_WATER_ONLY)`, `FILLED_ICE_SUPERCELLS` (`tests/e2e_chain_fixtures.py:71-91`).
- Rule (48.2 warning, restated in the module docstring): near-copy fixtures get merged; DIVERGENT same-name sibling fixtures get RENAMED apart in their own files, never merged.

**Synthetic function-scoped fixtures** — `tests/test_output/conftest.py:47-419`: `simple_candidate`, `ranked_candidate`, `simple_hydrate_config`, `simple_hydrate_structure`, `simple_interface`, `interface_with_ch4_guests`, `interface_with_thf_guests`, `custom_structure`, `solute_structure`, `ion_structure`. Use for unit tests of writers/validators — fast, deterministic, no GenIce2. NOTE: GenIce2 output is NOT deterministic even with `seed=42` (dipole optimization) — byte-equivalence tests MUST use synthetic fixtures (rationale in `tests/_capture_gro_top_baseline.py:31-40`).

**`tmp_path` (built-in):** all temp file outputs; auto-cleaned.
```python
def test_gro_only_sol_residues(self, ice_ih_candidate, tmp_path):
    gro_path = str(tmp_path / "ice.gro")
    write_gro_file(ice_ih_candidate, gro_path)
```

**`gmx_workspace` (persistent, NOT auto-cleaned):** for grompp debugging. Defined in `tests/e2e/export_validation/test_e2e_gmx_validation.py:84-96`; workspace root anchored via `quickice.__file__` so it stays at `<repo>/tmp/e2e-gmx-validation/<test_name>/` regardless of the test file's location:
```python
@pytest.fixture
def gmx_workspace(request):
    base = Path(quickice.__file__).resolve().parent.parent / "tmp" / "e2e-gmx-validation"
    workspace = base / request.node.name.replace("::", "_")
    workspace.mkdir(parents=True, exist_ok=True)
    yield workspace
```

**Factory fixtures (return a callable):** for dialog mocking — `mock_save_dialog`, `mock_hydrate_save_dialog`, `mock_cancel_dialog` in `tests/test_output/conftest.py:428-480`.

**`qapp_session`** — module-scoped QApplication with headless env guards applied at module import; reuses the singleton (`tests/gui_e2e_helpers.py:263-279`).

## Mocking

**Framework:** `unittest.mock.patch`/`patch.object` + pytest `monkeypatch` + `MagicMock`.

**Headless GUI safety mechanics (`tests/gui_e2e_helpers.py`) — use for ANY MainWindow-driven test.** Five probe-verified blockers, each with an institutionalized countermeasure:
1. **Qt XCB C-level hang:** `QT_QPA_PLATFORM=offscreen` forced at module import, before any Qt import (`tests/gui_e2e_helpers.py:48`).
2. **Modal dialog hang:** patch the COMPLETE modal catalog via `patch_gui_modals()` (`tests/gui_e2e_helpers.py:81-144`) — patches `QMessageBox` in the `main_window`, `export`, and `custom_molecule_panel` namespaces + `QFileDialog` in `export`, question → Yes, yields `ModalMocks` for call assertions. The `main_window.QMessageBox.information` "Export Complete" modal fires on EVERY successful export and hangs if missed.
3. **VTK headless crash:** protective `DISPLAY=localhost:11.0` (`tests/gui_e2e_helpers.py:53-54`) so `is_vtk_available()` returns False (SSH-X11 heuristic in `quickice/gui/vtk_utils.py`) and MainWindow takes its no-VTK branches. An empty DISPLAY would route real-structure rendering → `std::bad_array_new_length` core dump.
4. **Thread teardown SIGABRT:** `teardown_threads(mw)` (`tests/gui_e2e_helpers.py:196-251`) quits+waits viewmodel threads, `_custom_worker_thread`, and `_hydrate_worker`/`_ion_worker` (direct QThread subclasses — do NOT migrate them per AGENTS.md). MUST run in fixture teardown via try/finally/finalizer — a live QThread at exit poisons the whole pytest session (exit 134).
5. **Handler-created workers:** signals cannot be pre-connected; poll state instead — `wait_for_mainwindow_state(mw, "_current_hydrate_result")` (`tests/gui_e2e_helpers.py:147-193`) runs a QEventLoop + 80 ms poll + hard QTimer backstop.

**Other mocking patterns:**
1. **Patch the USING module's namespace**, never `PySide6.QtWidgets` directly (Pattern B): `patch("quickice.gui.export.QFileDialog.getSaveFileName", return_value=(path, filter))` + `patch("quickice.gui.export.QMessageBox")` (`tests/e2e/custom_guest/test_e2e_custom_guest_cross_tab_gui.py:344-347`).
2. **Headless Qt panel tests:** `monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")` + singleton `QApplication` guard (`tests/test_hydrate_panel.py`).
3. **Assert a function is NOT called** (regression guards): `monkeypatch.setattr("quickice.output.gromacs_writer.detect_guest_type_from_atoms", boom)` (`tests/test_output/test_interface_gro_custom_guest.py`).
4. **cwd-controlled tests (path containment):** `monkeypatch.chdir(work_dir)` + assert `--output` escape raises `ValueError` (`tests/scancode/test_scancode_bugs_pipeline.py`).
5. **CLI e2e needs NO dialog patching** — `CLIPipeline._run_export_step` writes files directly.

**What to Mock:** dialogs (QFileDialog/QMessageBox) per Blocker 2; env (`QT_QPA_PLATFORM`, `DISPLAY`); `cwd`; specific functions whose call/no-call is the invariant.

**What NOT to Mock:** structure generators/inserters (real via fixtures); `genice2` (real; only skip via `@gmx_skipif`); the writer functions under test; MainWindow handlers/workers in fullchain tests (mock only the modals they raise).

## GROMACS-Dependent Tests

**grompp helper:** `run_gmx_grompp(workspace, gro_file="struct.gro", top_file="struct.top", mdp_file="em.mdp", tpr_file="em.tpr", maxwarn=5) -> tuple[int, str]` in `tests/e2e_export_helpers.py:593-637`. Cleans stale `.tpr` backups, runs `gmx grompp` via subprocess, returns `(exit_code, stderr_text)`. Assert `exit_code == 0`.

**MDP files:** shared `tests/em.mdp` (`MDP_PATH` in `tests/e2e_export_helpers.py:397`) has `rcoulomb=rvdw=1.0` → requires shortest box vector > 2.0 nm. For smaller boxes (e.g. 96-molecule ice ≈ 1.47 nm) define a local `SMALL_CUTOFF_MDP` with 0.5 nm cutoffs — precedent: `tests/e2e/test_e2e_gui_fullchain.py:91-104`, `tests/test_cli/test_pipeline_grompp_matrix.py`.

**File-consistency asserts always run; grompp only when gmx present.** The `@gmx_skipif` decorator gates the whole test, and helpers guard the grompp call with `shutil.which("gmx")` so parse/assert coverage still executes without GROMACS (`tests/e2e/interface/test_e2e_lattice_interface_cli.py:44-47`).

## Shared Assertion / Parsing Helpers

Use the shared helpers in `tests/e2e_export_helpers.py` rather than re-implementing GROMACS format parsing:
- Parsers: `parse_gro_residue_names` (:52), `parse_gro_atom_count` (:99), `parse_top_molecules` (:115), `parse_top_includes` (:158), `check_itp_has_moleculetype` (:185).
- Chain builders: `_make_slab_interface` (:380), `_make_pocket_interface` (:380ff), `_insert_solutes` (:262), `_insert_ions` (:294), `_insert_ions_from_solute` (:303), `_insert_custom_molecules` (:250), `_solute_to_ion_source` (:269).
- Staging: `_stage_itp_files` (:401), `_stage_custom_guest_itp` (:458), `StagingResult` namedtuple (:39).
- Cross-file asserts: `assert_itp_completeness(top_path, workspace)` (:490 — every #include'd ITP except ion.itp exists), `assert_gro_top_consistent(gro_path, top_path)` (:519 — header count == atom lines AND every .top [molecules] name appears as a .gro residue).
- Data paths: `ETOH_GRO` / `ETOH_ITP` (:45-47, absolute, CWD-independent), `MDP_PATH` (:397).

**Import pattern:** `from tests.conftest import gmx_skipif` and `from tests.e2e_export_helpers import ...` work everywhere (tests/ is a package; root on sys.path). Add `# noqa: E402` when imports follow module-level env setup (34 test files do this). Legacy `sys.path.insert` survives only in the standalone scripts `tests/_capture_gro_top_baseline.py` and `tests/repro_sii_mixed_gui_regression.py` — do not extend that pattern.

## Coverage

**Requirements:** None enforced. No coverage gate.

**View Coverage:**
```bash
pytest --cov=quickice --cov-report=term-missing
```
(`pytest-cov` implied by AGENTS.md usage; not pinned in `requirements-dev.txt`.)

## Common Patterns

**Parametrize + shared canonical constants:**
```python
# tests/e2e/interface/test_e2e_lattice_interface_cli.py — constants and fixture
# come from tests/e2e_chain_fixtures.py (ONE definition shared by fixture + decorator)
from tests.e2e_chain_fixtures import INTERFACE_LATTICES, lattice_chains

@pytest.mark.parametrize("lattice_type", INTERFACE_LATTICES)
def test_export(self, lattice_type, lattice_chains): ...
```
```python
# tests/scancode/test_scancode_bugs_inserter_perf.py — seed matrix
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
```

**Guest-count asserts are inequalities, never exact** (Pitfall 5 — counts vary by lattice/GenIce2 version): assert `> 0` for guest lattices, `== 0` for water-only (`tests/e2e/interface/test_e2e_lattice_interface_cli.py:56-58`).

**Fresh interface per inserter** (fixture hygiene): the ion inserter mutates `iface.molecule_index` when empty (`quickice/structure_generation/ion_inserter.py:259`), so chains build a fresh `assemble_slab` interface PER inserter from one shared candidate (generate-once-derive-many, `seed=42` → deterministic identical slabs) — see `tests/e2e_chain_fixtures.py:193-210`.

**Async Testing:** Not applicable — no `async`/`await`. QThread workers (`HydrateWorker`, `IonInsertionWorker`, `CustomMoleculeWorker`) are tested by driving real MainWindow handlers with state-polling (`wait_for_mainwindow_state`) in fullchain e2e, or by calling the underlying computation functions directly in panel/unit tests — never by manually driving the event loop.

---

*Testing analysis: 2026-09-12*
