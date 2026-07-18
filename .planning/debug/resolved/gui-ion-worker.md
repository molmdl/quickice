---
status: resolved
trigger: "SAFE-01 + SAFE-07: GUI ion insertion threading + NaN/Inf concentration crash"
created: 2026-07-19T00:00:00Z
updated: 2026-07-19T00:01:00Z
---

## Current Focus

hypothesis: Both root causes CONFIRMED and FIXED. Two atomic commits landed.
test: (done) tests/test_scancode_bugs_gui_ion.py — 21 tests (9 SAFE-01 + 12 SAFE-07) all pass.
expecting: (met) UI no longer freezes during ion insertion; NaN/Inf shows a clear QMessageBox warning instead of an unhelpful ValueError/OverflowError.
next_action: archive this debug file to .planning/debug/resolved/ with a docs commit.

## Symptoms

### SAFE-01 (UI freeze during ion insertion)
expected: Ion insertion runs on a background thread; UI stays responsive; ion button disabled during work, re-enabled on completion/error.
actual: `insert_ions(...)` called synchronously on the main GUI thread at `main_window.py:935`, freezing the UI.
errors: No exception — UI freeze.
reproduction: Load a realistic interface in the GUI, trigger ion insertion, observe unresponsive UI.
timeline: Present since the ion-insertion GUI handler was written.

### SAFE-07 (NaN/Inf concentration crash)
expected: NaN or Inf concentration shows a clear user-facing error message before any crash.
actual: `if concentration <= 0` does not reject NaN (NaN comparisons return False) or Inf. `int(round(NaN))` raises `ValueError` from inside `round`.
errors: `ValueError: cannot convert float NaN to integer` (unhelpful, no guided message).
reproduction: Feed NaN/Inf concentration via any input path that bypasses the spinbox; trigger ion insertion.
timeline: Present since the concentration validation was written.

## Eliminated

(none yet — both root causes confirmed, not eliminated)

## Evidence

- 2026-07-19 CONFIRMED SAFE-01: `quickice/gui/main_window.py:935` reads:
  `ion_structure = insert_ions(interface, concentration, volume_arg)` — synchronous, no worker.
  Contrast: `HydrateWorker` at `hydrate_worker.py:15` (`class HydrateWorker(QThread)`) is used at `main_window.py:759` (`self._hydrate_worker = HydrateWorker(config)`), started at `:767`, with complete handler `:802` and error handler `:821` — button disabled at `:756`, re-enabled in both handlers.
- 2026-07-19 CONFIRMED SAFE-07: `quickice/gui/main_window.py:924` reads:
  `if concentration <= 0:` — NaN<=0 is False, Inf<=0 is False, so NaN/Inf pass.
  Crash site: `quickice/structure_generation/ion_inserter.py:222` `return int(round(n_formula_units))` where `n_formula_units = concentration_molar * volume_liters * AVOGADRO` (line 219). NaN propagates → `int(round(NaN))` → ValueError.
- 2026-07-19 HydrateWorker pattern (authoritative): `quickice/gui/hydrate_worker.py` — separate module, `class HydrateWorker(QThread)` with signals `progress_updated=Signal(str)`, `generation_complete=Signal(object)`, `generation_error=Signal(str)`. `run()` imports `HydrateStructureGenerator` INSIDE `run()` (lazy), try/except with specific handlers (ImportError, RuntimeError, ValueError, Exception). Imported in `main_window.py:34` as `from quickice.gui.hydrate_worker import HydrateWorker`.
- 2026-07-19 IonPanel.insert_button: `quickice/gui/ion_panel.py:126` `self.insert_button = QPushButton("Insert Ions")`. This is the button to disable/enable (mirrors `hydrate_panel.generate_button`).
- 2026-07-19 `insert_ions` signature: `quickice/structure_generation/ion_inserter.py:660` `def insert_ions(structure, concentration_molar, liquid_volume_nm3=None, seed=None) -> IonStructure`. Returns an `IonStructure` with `.na_count` and `.cl_count`.
- 2026-07-19 IonConfig: `quickice/structure_generation/types.py:812` — `concentration_molar: float = 0.0`; `__post_init__` at `:821` does `if self.concentration_molar < 0: raise ValueError(...)`. This ALSO misses NaN (NaN<0 is False). SAFE-07 fix is in `main_window.py:924` (the GUI handler), NOT in `types.py` (out of scope).
- 2026-07-19 main_window.py imports: `QThread` imported at `:23` (`from PySide6.QtCore import Qt, Slot, QThread`); `Signal` NOT imported (need to add). `insert_ions` imported at `:40`. `math` NOT imported (need to add for SAFE-07). PySide6 is at top level (main_window is the GUI module — this is the established pattern, not a lazy-import violation).
- 2026-07-19 Test pattern: `tests/test_hydrate_panel.py:363-408` uses `inspect.getsource(MainWindow.<method>)` to assert code patterns WITHOUT constructing MainWindow (which is heavy: viewmodel, exporters, VTK panels). `tests/test_ion_source_dropdown.py` constructs `IonPanel()` with QApplication (headless-safe). `tests/conftest.py` provides `interface_slab` fixture and `gmx_skipif` marker; no QApplication fixture.

## Resolution

root_cause:
  - SAFE-01: `quickice/gui/main_window.py:935` called `insert_ions(interface, concentration, volume_arg)` synchronously on the main GUI thread, freezing the UI during ion insertion (no worker thread, unlike HydrateWorker).
  - SAFE-07: `quickice/gui/main_window.py:924` guarded concentration with `if concentration <= 0`, which does NOT reject NaN (NaN <= 0 is False) or Inf. NaN/Inf then reached `int(round(concentration))` inside `ion_inserter.py:222` (calculate_ion_pairs) and crashed with an unhelpful `ValueError` ("cannot convert float NaN to integer") / `OverflowError` ("cannot convert float infinity to integer") — no guided user message.

fix:
  - SAFE-01 (commit e6855cc6): Added `IonInsertionWorker(QThread)` class to `quickice/gui/main_window.py` mirroring the existing `HydrateWorker` pattern (direct QThread subclass per AGENTS.md — NOT QObject+moveToThread). Three signals (progress_updated/insertion_complete/insertion_error); `run()` lazy-imports `insert_ions` inside `run()` and emits results via signals (does NOT mutate GUI widgets). Added `Signal` to the `PySide6.QtCore` import. Refactored `_on_insert_ions` to: stash `interface`+`current_source`, disable `ion_panel.insert_button`, construct/connect/start the worker. Moved the post-insertion rendering (store result, render in viewer, log) into the new `_on_ion_insertion_complete` handler; added `_on_ion_progress` and `_on_ion_insertion_error` handlers — both re-enable the button (same lifecycle as HydrateWorker).
  - SAFE-07 (commit 16d2942c): Added `import math` at the top of `quickice/gui/main_window.py`. Hardened the concentration guard to `if concentration is None or math.isnan(concentration) or math.isinf(concentration) or concentration <= 0:` — reusing the existing `QMessageBox.warning("Invalid Concentration", ...)` error-display pattern (same dialog, just a wider condition). The `is None` check short-circuits before `math.isnan(None)` (which would raise TypeError). IonConfig.__post_init__ also misses NaN (its `< 0` check returns False for NaN), so the GUI boundary is the authoritative guard (defense in depth).

verification:
  - New tests: `QT_QPA_PLATFORM=offscreen pytest tests/test_scancode_bugs_gui_ion.py -v` → 21 passed (9 SAFE-01 + 12 SAFE-07). Includes a runtime thread-identity test (insert_ions captured on the worker thread, NOT the main thread), runtime button-lifecycle tests (disabled before start(), re-enabled in complete/error handlers), and runtime NaN/Inf/-Inf/None/0 rejection tests (QMessageBox.warning shown, no worker constructed).
  - GUI ion-related subset: `QT_QPA_PLATFORM=offscreen pytest tests/test_scancode_bugs_gui_ion.py tests/test_ion_source_dropdown.py tests/test_scancode_bugs_ion_charge_warning.py tests/test_ion_path1_guest_attrs.py tests/test_ion_hydrate_fix.py tests/test_e2e_ion_insertion.py tests/test_e2e_ion_export.py` → 87 passed, 0 failed (21 + 11 + 14 + 6 + 1 + 14 + 20).
  - Full non-GUI suite (excluding ~20 slow GUI/Qt/VTK files): 1438 passed, 2 failed, 2 skipped in 172s. The 2 failures (`test_cli_integration.py::test_version_shows_version`, `test_entry_point.py::test_version_shows_version`) are PRE-EXISTING: at the parent commit d4542ba5 (before my changes), both tests already asserted `"4.5.0" in stdout` while `quickice/__init__.py` already had `__version__ = "4.7.0"`. My commits only touch `quickice/gui/main_window.py` and `tests/test_scancode_bugs_gui_ion.py` — neither the version constant nor the CLI version tests. Zero new failures from my change.
  - gmx IS on PATH (`/data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx`); optional grompp dry-run not run (e2e ion export tests already validate the topology).

files_changed:
  - quickice/gui/main_window.py (SAFE-01: IonInsertionWorker + handler refactor; SAFE-07: import math + hardened guard)
  - tests/test_scancode_bugs_gui_ion.py (new — 21 regression tests)
