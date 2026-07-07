---
phase: 43-depol-mode
plan: 01
subsystem: hydrate
tags: [genice2, depol, hydrate-config, depolarization, dataclass-validation]

# Dependency graph
requires:
  - phase: 38-internal-pipeline-refactor
    provides: HydrateConfig dataclass with __post_init__ validation + from_dict pattern (the extension surface)
  - phase: 42-mixed-cage-occupancy
    provides: cage_guest_assignments field (last HydrateConfig field before depol_mode insertion point)
provides:
  - HydrateConfig.depol_mode field (default "strict", validated against {"strict","optimal"})
  - HydrateConfig.from_dict depol_mode passthrough (explicit → passthrough; absent → "strict")
  - hydrate_generator._run_via_api passes config.depol_mode to GenIce2 generate_ice(depol=...)
  - 8 new tests (6 unit + 2 e2e) covering default, passthrough, validation, from_dict, and e2e generation
affects: [43-02-gui-depol-selector, 45-cli-integration, 44-gui-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HydrateConfig is the SOLE gatekeeper for depol_mode validity (GenIce2 accepts any string silently)"
    - "Default 'strict' preserves byte-identical behavior for every pre-existing call site (backward compat by default)"
    - "strict ≡ optimal in GenIce2 2.2.13.1 — tests assert equality, not difference (Pitfall 1)"

key-files:
  created: []
  modified:
    - quickice/structure_generation/types.py
    - quickice/structure_generation/hydrate_generator.py
    - tests/test_hydrate_config_metadata.py
    - tests/test_hydrate_lattice_types.py

key-decisions:
  - "depol_mode added as the LAST HydrateConfig field (after cage_guest_assignments) to minimize diff and avoid disturbing __post_init__ legacy-shim logic"
  - "Validation set is {strict, optimal} only — 'none' is rejected even though GenIce2 accepts it (iter=0 → nonzero net dipole → physically unrealistic)"
  - "Validation placed in __post_init__ immediately after the supercell check, before the guest_type custom-guest branch"
  - "e2e test asserts strict and optimal produce EQUAL atom counts (not a difference) — Pitfall 1: strict≡optimal in GenIce2 2.2.13.1"
  - "generator.py:126 ice-path hardcode (depol='strict') left UNTOUCHED — out of scope for Phase 43 (hydrate-only)"
  - "No CLI --depol flag added (Phase 45 / CLI-03 scope); CLI pipeline.py:372 inherits 'strict' default automatically"

patterns-established:
  - "Phase 43 depol validation: QuickIce is the sole gatekeeper for GenIce2 string kwargs that accept anything silently"
  - "Forward-compatibility knob: depol_mode string field maps to GenIce3 pol_loop_1/pol_loop_2 integers in a future migration"

# Metrics
duration: 2 min
completed: 2026-07-07
---

# Phase 43 Plan 01: HydrateConfig depol_mode + Generator Passthrough Summary

**Wire GenIce2's depolarization parameter through QuickIce's HydrateConfig with {"strict","optimal"} validation and a "strict" default that preserves byte-identical behavior for every existing call site**

## Performance

- **Duration:** 2 min
- **Started:** 2026-07-07T07:48:38Z
- **Completed:** 2026-07-07T07:51:09Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- HydrateConfig carries a `depol_mode: str = "strict"` field as the last dataclass field, with `__post_init__` validation against `{"strict","optimal"}` (rejects `"none"` and typos like `"banana"` that GenIce2 would silently accept)
- `HydrateConfig.from_dict` threads `depol_mode` through (explicit → passthrough; absent → `"strict"` default), preserving backward compatibility for old UI dicts
- `hydrate_generator._run_via_api` passes `config.depol_mode` to `GenIce2.generate_ice(depol=...)` in place of the hardcoded `'strict'` — the single in-scope call site
- 8 new tests (6 unit + 2 e2e) covering: default value, optimal passthrough, invalid `"none"` raises, invalid `"banana"` raises, from_dict explicit passthrough, from_dict default, e2e optimal generation succeeds, e2e optimal≡strict equal atom counts
- 234 hydrate regression tests pass — every pre-existing `HydrateConfig(...)` call site (CLI, GUI, fixtures, tests) omits `depol_mode` and inherits `"strict"`, preserving current behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Add depol_mode to HydrateConfig + swap generator hardcode** - `a22a1b4` (feat)
2. **Task 2: Unit + e2e tests for depol_mode** - `4d757b2` (test)

## Files Created/Modified
- `quickice/structure_generation/types.py` - Added `depol_mode: str = "strict"` field (last dataclass field), `__post_init__` validation after supercell check, `from_dict` passthrough as last kwarg
- `quickice/structure_generation/hydrate_generator.py` - Swapped hardcoded `depol='strict'` → `depol=config.depol_mode` at the single in-scope `generate_ice` call (line 317)
- `tests/test_hydrate_config_metadata.py` - Appended `TestDepolMode` class (6 unit tests) covering default, optimal passthrough, invalid raises, from_dict round-trip
- `tests/test_hydrate_lattice_types.py` - Added `HydrateStructureGenerator` import + appended `TestDepolModePassthrough` class (2 e2e tests with module-scoped fixtures)

## Decisions Made
- **depol_mode placement:** Added as the LAST HydrateConfig field (after `cage_guest_assignments`) per 43-RESEARCH.md guidance — minimizes diff, avoids disturbing the `__post_init__` legacy-shim logic, and follows the dataclass field-ordering note (every existing field has a default, so a new defaulted field can be placed anywhere; last is safest).
- **Validation set:** `{"strict", "optimal"}` only. `"none"` is rejected even though GenIce2 accepts it silently (`iter=0` → nonzero net dipole → physically unrealistic structures). QuickIce's `__post_init__` is the sole gatekeeper — GenIce2 does no validation (even `"banana"` runs `iter=1000`).
- **Validation placement:** Immediately after the supercell check in `__post_init__`, before the `guest_type` custom-guest branch — matches the existing validation style (lattice_type, occupancies, supercell) and runs early enough to reject invalid configs before any metadata auto-population side effects.
- **e2e test assertion:** `test_optimal_and_strict_have_equal_atom_counts` asserts EQUALITY, not difference. In GenIce2 2.2.13.1, both `strict` and `optimal` set `dipoleOptimizationCycles=1000` (Stage34E branches only on `"none"` vs anything-else). A test asserting strict≠optimal would be a false-future-proofing bug (Pitfall 1).
- **Out-of-scope boundaries honored:** `generator.py:126` ice-path hardcode (`depol='strict'`) left untouched (non-hydrate TIP3P path, different class, no HydrateConfig). No CLI `--depol` flag (Phase 45 / CLI-03). No `hydrate_worker.py` or `gromacs_writer.py` edits (depol rides along `config`; export path is unaffected).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DEPOL-02 (depol mode passed through to GenIce2 `generate_ice()`) is satisfied at the config+generator layer — `hydrate_generator._run_via_api` now passes `config.depol_mode`.
- DEPOL-03 (default depol mode is `'strict'`) is satisfied — `HydrateConfig.depol_mode` defaults to `"strict"`, preserving current behavior for every existing call site.
- DEPOL-01 (user can select depol mode strict/optimal in the Hydrate tab) requires the GUI selector (Phase 43-02) — the config+generator plumbing is ready for 43-02 to wire a `QComboBox` to `depol_mode`.
- Phase 45 (CLI Integration) can add a `--depol` flag that sets `depol_mode` on the `HydrateConfig` constructed at `pipeline.py:372` — the config field is already in place.
- No blockers. No new dependencies. No export/worker changes needed (depol only affects H-bond orientation during generation, not GRO/topology output).

---
*Phase: 43-depol-mode*
*Completed: 2026-07-07*
