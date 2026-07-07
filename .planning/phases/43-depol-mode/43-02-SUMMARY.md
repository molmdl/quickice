---
phase: 43-depol-mode
plan: 02
subsystem: gui
tags: [pyside6, qcombobox, depol, hydrate-panel, headless-tests, configuration-changed]

# Dependency graph
requires:
  - phase: 43-01
    provides: HydrateConfig.depol_mode field (default "strict", __post_init__ validation against {"strict","optimal"}, from_dict passthrough) — the config surface this GUI selector wires to
  - phase: 42-06
    provides: HydratePanel per-cage-row architecture (lattice combo + cage combo + supercell pattern that the depol combo mirrors)
provides:
  - HydratePanel._create_depol_group() QGroupBox with a strict/optimal QComboBox (index 0 = "strict" default)
  - Depol group rendered between the supercell group and the lattice info group in _setup_ui
  - depol_combo.currentIndexChanged -> configuration_changed.emit() wiring in _setup_connections
  - get_configuration passes depol_mode=self.depol_combo.currentData() into HydrateConfig(...)
  - 4 headless GUI tests (TestDepolCombo) covering default, item count, get_configuration round-trip, signal emission
  - DEPOL-01 (user can select depol mode in Hydrate tab) SATISFIED — combined with 43-01 (config + generator passthrough), DEPOL-01/02/03 are all closed
affects: [44-gui-integration, 45-cli-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Depol combo reuses the established lattice-combo pattern (QComboBox + HelpIcon + addStretch + QFormLayout row) — zero new widget patterns"
    - "GUI selector + config field + generator passthrough = 3-layer depol wiring (43-01 config+gen, 43-02 GUI) — Phase 44 #4 references it as already-integrated, do NOT double-build"

key-files:
  created: []
  modified:
    - quickice/gui/hydrate_panel.py
    - tests/test_hydrate_panel.py

key-decisions:
  - "depol group placed between supercell group and lattice info group (per 43-RESEARCH.md Open Question 1 recommendation — separate QGroupBox is more discoverable than a row inside the Hydrate Lattice group)"
  - "Tooltip text describes the INTENDED strict/optimal distinction (per GenIce2 CLI help / GenIce3 design), not a guaranteed runtime delta in GenIce2 2.2.13.1 where strict≡optimal — text is factual as written (intent + 'does not change atom count' which IS true)"
  - "No third 'none' item offered — Pitfall 2 (none yields unrealistic nonzero-dipole structures; HydrateConfig.__post_init__ from 43-01 rejects it, and the GUI must not offer it either)"
  - "depol_mode kwarg added LAST in the HydrateConfig(...) call (after supercell_z) to minimize diff"
  - "No edits to hydrate_worker.py, gromacs_writer.py, or cli/pipeline.py — depol rides along config; export path unaffected (depol only sets H-bond orientation during generation)"
  - "Per-class panel fixture (copy of the TestHydratePanelCageRows 4-line fixture) added to TestDepolCombo — pytest fixtures are per-class, so the new class needs its own fixture instance"

patterns-established:
  - "Phase 43 GUI depol selector: QComboBox with 2 items (strict default, optimal), wired exactly like the lattice combo — the template for any future GenIce2 enum-kwarg GUI selector"

# Metrics
duration: 16 min
completed: 2026-07-07
---

# Phase 43 Plan 02: GUI Depol Mode Selector Summary

**Add a Depolarization QComboBox (strict/optimal) to the Hydrate GUI tab, wired exactly like the lattice combo, flowing into HydrateConfig via get_configuration() and emitting configuration_changed on change — closes DEPOL-01 (user-selectable depol mode) when combined with 43-01's config+generator passthrough**

## Performance

- **Duration:** 16 min
- **Started:** 2026-07-07T07:56:55Z
- **Completed:** 2026-07-07T08:13:53Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- HydratePanel renders a new `Depolarization` QGroupBox containing a `QComboBox` with exactly 2 items: `("Strict (ice rules, zero net dipole)", "strict")` at index 0 (default) and `("Optimal (relaxed)", "optimal")` at index 1
- The depol group renders between the supercell group and the lattice info group in `_setup_ui` (group order preserved: lattice → cage → supercell → **depol** → info → generate button)
- `get_configuration()` passes `depol_mode=self.depol_combo.currentData()` into `HydrateConfig(...)` as the last kwarg — `currentData()` returns `"strict"` by default (index 0) or `"optimal"` (index 1), both valid per 43-01's `__post_init__` validation, so `get_configuration()` can never produce an invalid config
- Changing the depol combo emits `configuration_changed` (wired in `_setup_connections` mirroring the existing `lattice_combo.currentIndexChanged` + `supercell_*.valueChanged` pattern)
- 4 headless GUI tests (`TestDepolCombo`) pass: default is strict (index 0, data "strict"), combo has exactly 2 items with data {"strict","optimal"}, get_configuration round-trips strict→strict and optimal→optimal, changing the combo emits `configuration_changed` at least once per change
- DEPOL-01 (user can select depol mode strict/optimal in the Hydrate tab) is SATISFIED by this plan combined with 43-01 — completing Phase 43 (Depol Mode) end-to-end

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _create_depol_group + wire into UI, connections, get_configuration** - `64865ef` (feat)
2. **Task 2: Headless GUI tests for depol combo** - `9e9c651` (test)

## Files Created/Modified
- `quickice/gui/hydrate_panel.py` - Added `_create_depol_group()` method (QGroupBox + QComboBox with strict/optimal items + HelpIcon), inserted depol group in `_setup_ui` between supercell and info groups, wired `depol_combo.currentIndexChanged` → `configuration_changed.emit()` in `_setup_connections`, added `depol_mode=self.depol_combo.currentData()` kwarg to `get_configuration()`'s `HydrateConfig(...)` call
- `tests/test_hydrate_panel.py` - Appended `TestDepolCombo` class with a per-class `panel` fixture (copy of the `TestHydratePanelCageRows` fixture) + 4 headless tests covering default, item count, get_configuration round-trip, and signal emission

## Decisions Made
- **Group placement:** The `Depolarization` group renders between the supercell group and the lattice info group, per 43-RESEARCH.md Open Question 1's recommendation that a separate `QGroupBox` is more discoverable than a row inside the Hydrate Lattice group. This matches the per-section `QGroupBox` convention used throughout the panel.
- **Tooltip wording:** The HelpIcon text describes the INTENDED strict/optimal distinction (per GenIce2 CLI help and GenIce3's `pol_loop_1`/`pol_loop_2` design) rather than a guaranteed runtime delta. In GenIce2 2.2.13.1 both `strict` and `optimal` set `dipoleOptimizationCycles=1000` (functionally identical — Pitfall 1). The text is factual as written: it describes intent and the true statement "Affects H-bond orientation only; does not change atom count" (which IS true — depol only orients hydrogens, never adds/removes atoms).
- **No `none` item:** The combo offers exactly 2 items. `"none"` is excluded because it yields physically unrealistic nonzero-dipole structures (Pitfall 2). 43-01's `HydrateConfig.__post_init__` rejects `"none"` with `ValueError`, and the GUI must not offer it either — consistency between the validation layer and the UI layer.
- **Kwarg ordering:** `depol_mode=self.depol_combo.currentData()` added as the LAST kwarg in the `HydrateConfig(...)` call (after `supercell_z`) to minimize the diff and follow the 43-01 field-placement decision (depol_mode is the last dataclass field).
- **Out-of-scope boundaries honored:** No edits to `hydrate_worker.py` (passes `config` opaquely to `generator.generate(config)`; depol rides along), `gromacs_writer.py` / `HydrateGROMACSExporter` (depol only affects H-bond orientation during generation, not GRO/topology output), or `cli/pipeline.py` (CLI `--depol` is Phase 45 / CLI-03 scope; the CLI call site inherits `"strict"` default automatically). No CLI surface added in Phase 43.
- **Per-class fixture:** `TestDepolCombo` has its own copy of the 4-line `panel` fixture (pytest fixtures are per-class; the existing fixture lives in `TestHydratePanelCageRows` and is not inherited). Verbatim copy ensures the same headless `QT_QPA_PLATFORM=offscreen` + singleton `QApplication` pattern.
- **Signal test approach:** Used a plain Python list as the `configuration_changed` slot callback (`emitted.append(True)`) rather than `QtSignalSpy` — matches the existing panel test approach for `configuration_changed` and avoids importing `PySide6.QtTest`. Simpler and sufficient for asserting "at least one emission per change".

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- **Pre-existing headless VTK hang in `tests/test_custom_molecule_panel_34_6.py` (NOT a regression from this plan):** The plan's `<verification>` section suggested a broader GUI smoke (`pytest tests/test_hydrate_panel.py tests/test_custom_molecule_panel_34_6.py`). Collection of `test_custom_molecule_panel_34_6.py` succeeds in 0.08s (no import regression), but a specific test (`test_button_state_persistence`) hangs indefinitely during execution — the `pytest-timeout` `--timeout=30` signal method does not fire because the test is blocked in a VTK C-extension call. This matches AGENTS.md's documented limitation: "VTK rendering may still crash in some headless environments — mock or skip VTK-dependent tests if needed. See ROADMAP.md TEST-06 (deferred)." This plan's changes only touch `hydrate_panel.py` and `test_hydrate_panel.py`; `test_custom_molecule_panel_34_6.py` does not import from `hydrate_panel.py` (it tests the separate Custom Molecule panel), so the hang is pre-existing and unrelated. The critical Task 2 verifications (targeted depol tests: 4 passed; full `test_hydrate_panel.py` regression: 10 passed) both succeeded.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- **DEPOL-01 (user can select depol mode strict/optimal in the Hydrate tab) is SATISFIED** by this plan (GUI QComboBox) combined with 43-01 (HydrateConfig.depol_mode + generator passthrough). All three Phase 43 requirements (DEPOL-01/02/03) are now closed:
  - DEPOL-01: GUI dropdown (this plan) ✓
  - DEPOL-02: depol mode passed through to GenIce2 `generate_ice()` (43-01) ✓
  - DEPOL-03: default is `'strict'` (43-01 config default + this plan's combo index 0) ✓
- **Phase 43 (Depol Mode) is COMPLETE** (2/2 plans). Ready to mark the phase complete in ROADMAP.md and STATE.md.
- **Phase 44 (GUI Integration) #4 (depol mode dropdown)** references this selector as an already-integrated feature — do NOT double-build. The 43-02 dropdown IS the GUI-04 implementation. Phase 44 should focus on its other items (new lattice types in dropdown, custom guest upload panel, mixed occupancy controls).
- **Phase 45 (CLI Integration) #2** can add a `--depol` flag that sets `depol_mode` on the `HydrateConfig` constructed at `pipeline.py:372` — the config field (43-01) and GUI precedent (43-02) are both in place.
- No blockers. No new dependencies. No export/worker changes needed (depol only affects H-bond orientation during generation, not GRO/topology output).

---
*Phase: 43-depol-mode*
*Completed: 2026-07-07*
