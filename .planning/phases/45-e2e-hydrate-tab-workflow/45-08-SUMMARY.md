---
phase: 45-e2e-hydrate-tab-workflow
plan: 08
subsystem: testing
tags: [triclinic-blocking, e2e, cli-pipeline, gui-worker, c0te, c1te, interface-builder, pytest, PySide6]

# Dependency graph
requires:
  - phase: 39-hydrate-lattice-expansion
    provides: TRICLINIC_HYDRATE_PHASES blocking in validate_interface_config (interface_builder.py:121)
  - phase: 39-03
    provides: Triclinic filled-ice c0te/c1te lattice definitions + phase_id-based blocking
provides:
  - E2E proof that triclinic filled-ice lattices (c0te, c1te) are blocked at the interface step through the REAL CLI pipeline (_run_interface_step catches InterfaceGenerationError -> returns 1)
  - E2E proof that the GUI InterfaceGenerationWorker catches InterfaceGenerationError -> emits error signal
  - Module-scoped fixture pattern amortizing GenIce2 for c0te/c1te generation across parametrized CLI+GUI blocking tests
affects:
  - 45-09 (triclinic hydrate-only export @ 4x4x4 supercell)
  - 45-e2e-hydrate-tab-workflow (phase completion)

# Tech tracking
tech-stack:
  added: []  # No new libraries — test-only plan
  patterns:
    - "GUI worker synchronous run(): InterfaceGenerationWorker is a QObject (NOT QThread), so worker.run() can be called directly without QThread/start/wait/QTest.qWait"
    - "Module-scoped fixture for parametrized CLI+GUI blocking tests amortizes GenIce2 across c0te+c1te"
    - "CLI pipeline direct-call testing: construct CLIPipeline(args=SimpleNamespace()), set _hydrate_result + _ice_candidate + args fields, call _run_interface_step() directly"

key-files:
  created:
    - tests/test_e2e_triclinic_blocking_e2e.py
  modified: []

key-decisions:
  - "Used the primary GUI worker approach (direct worker.run() call) — no fallback needed; the worker is a QObject so run() executes synchronously and emits error signal on InterfaceGenerationError"
  - "TRICLINIC_HYDRATE_PHASES is a local constant inside validate_interface_config (not module-level), so it is mirrored as a module-level constant in the test file with a comment pointing to the source location (interface_builder.py:121)"
  - "CLI test mirrors the exact InterfaceConfig construction in _run_interface_step (pipeline.py:421-431) including pocket_diameter=None and pocket_shape='sphere' — the triclinic check fires before any mode-specific (slab) or pocket checks"

patterns-established:
  - "Pattern: GUI worker blocking test — construct QObject worker, connect error signal handler, call run() directly (synchronous), assert error signal emitted"
  - "Pattern: CLI pipeline step blocking test — construct CLIPipeline with SimpleNamespace args, set _<step>_result + _ice_candidate, set args fields mirroring the step's InterfaceConfig construction, call _run_<step>_step() directly, assert non-zero return + result is None"

# Metrics
duration: <1 min
completed: 2026-07-11
---

# Phase 45 Plan 08: Triclinic Blocking E2E Summary

**E2e triclinic blocking proven through CLI _run_interface_step (returns 1) + GUI InterfaceGenerationWorker (emits error signal) for c0te/c1te**

## Performance

- **Duration:** <1 min (52s)
- **Started:** 2026-07-11T02:53:17Z
- **Completed:** 2026-07-11T02:54:09Z
- **Tasks:** 2
- **Files modified:** 1 (new test file)

## Accomplishments
- Proved triclinic filled-ice lattices (c0te, c1te) are BLOCKED at the interface step through the REAL CLI pipeline (`_run_interface_step` catches `InterfaceGenerationError` -> returns 1), not just `validate_interface_config` directly
- Proved the GUI `InterfaceGenerationWorker` catches `InterfaceGenerationError` -> emits `error` signal for both c0te and c1te (workers.py:215-218)
- Used the primary GUI worker approach (synchronous `worker.run()` call on the QObject, NOT QThread) — no fallback to direct `generate_interface` was needed
- Module-scoped fixture amortizes GenIce2 generation across 4 parametrized cases (c0te/c1te x CLI/GUI) — entire suite runs in ~1s

## Task Commits

Each task was committed atomically:

1. **Task 1: Write triclinic blocking e2e test** - `324e4c3` (test)
2. **Task 2: Run full test + commit** - `324e4c3` (same commit — test file verified passing then committed)

**Plan metadata:** (pending — SUMMARY + PLAN commit below)

## Files Created/Modified
- `tests/test_e2e_triclinic_blocking_e2e.py` (211 lines) - 4 parametrized tests: c0te/c1te x CLI `_run_interface_step` (returns non-zero) + GUI `InterfaceGenerationWorker` (emits error signal). Module-scoped `triclinic_hydrates` fixture generates both lattices once. GUI worker called synchronously (QObject.run(), not QThread). Asserts error message contains "triclinic".

## Decisions Made
- **Primary GUI worker approach (no fallback):** The plan offered a fallback (direct `generate_interface` + assert raises) if the QThread setup was too heavy. The worker is a `QObject` (NOT `QThread` — workers.py:146), so `run()` is called directly and synchronously. The primary approach worked on the first run — no fallback needed. This is a STRONGER test than the fallback because it proves the worker's `except InterfaceGenerationError` block (workers.py:215-218) actually emits the `error` signal, not just that `generate_interface` raises.
- **TRICLINIC_HYDRATE_PHASES mirrored locally:** The constant `TRICLINIC_HYDRATE_PHASES = {"hydrate_c0te", "hydrate_c1te"}` is a local variable inside `validate_interface_config` (interface_builder.py:121), not a module-level importable name. It is mirrored as a module-level constant in the test file with a comment pointing to the source location. The test references `hydrate_c0te`/`hydrate_c1te` phase_ids through the parametrized lattice types + the candidate's `phase_id` attribute.
- **CLI test mirrors exact InterfaceConfig construction:** The CLI test sets `pipe.args` fields (`mode`, `box_x/y/z`, `ice_thickness`, `water_thickness`, `seed`, `pocket_diameter=None`, `pocket_shape="sphere"`) to mirror the `InterfaceConfig(...)` construction in `_run_interface_step` (pipeline.py:421-431). The triclinic check (interface_builder.py:121-137) fires before any slab-specific or pocket-specific validation, so `pocket_diameter=None` is safe.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- **ImportError on first run:** `TRICLINIC_HYDRATE_PHASES` is a local constant inside `validate_interface_config` (interface_builder.py:121), not a module-level importable name. Fixed by removing the import and mirroring the constant locally in the test file with a comment pointing to the source. This is a test-only fix (Rule 3 - blocking: import failure prevented collection). Re-ran successfully — 4/4 pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Triclinic blocking e2e is now proven through both the CLI pipeline and GUI worker — the gap where only `validate_interface_config` was tested directly is closed
- Ready for 45-09 (triclinic filled-ice hydrate-only export @ 4x4x4 supercell + grompp) — the blocking at the interface step means only hydrate-only export is possible for c0te/c1te
- All 4 tests pass in ~1s (module-scoped fixture amortizes GenIce2)

---
*Phase: 45-e2e-hydrate-tab-workflow*
*Completed: 2026-07-11*
