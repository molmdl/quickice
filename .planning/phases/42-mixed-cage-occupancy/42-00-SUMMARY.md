---
phase: 42-mixed-cage-occupancy
plan: 00
subsystem: core
tags: [hydrate, sH, cage-occupancy, genice2, regression-test, cage-type-map]

# Dependency graph
requires:
  - phase: 39-extended-lattice-types
    provides: HYDRATE_LATTICES data model with cage_type_map for all 10 lattice types (sH had the latent large→16 bug); cage_type_map-driven parse_guest routing in hydrate_generator._run_via_api
provides:
  - Correct sH cage_type_map (small→12, medium→12_1, large→20) — prerequisite for Phase 42 mixed cage occupancy
  - Reachable sH medium cage key (12_1) for upcoming MIXED-01 work
  - Regression test guarding the sH silent-zero large-cage placement bug
affects: [42-mixed-cage-occupancy, 44-gui-integration, 45-cli-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [GenIce2-empirical-count verification for regression tests — always run the generator and observe counts before hardcoding expected values]

key-files:
  created: [tests/test_e2e_sh_cage_occupancy.py]
  modified: [quickice/structure_generation/types.py, tests/test_hydrate_lattice_types.py]

key-decisions:
  - "sH cage_type_map large id corrected 16→20 (the real GenIce2 sH large-cage id); medium key 12_1 added (was missing — sH medium cages were unreachable)"
  - "valid_keys test relaxed to accept medium + guest keys so sH medium and filled-ice guest aliases are permitted"
  - "Regression test uses empirically-verified counts (2 large / 6 small / 8 total) instead of plan research estimates (10/30/40), which wrongly assumed a single crystallographic unit cell; GenIce2 sH 1×1×1 cell actually contains 2 unit cells (68 waters)"

patterns-established:
  - "GenIce2-based regression tests verify exact guest_count empirically before hardcoding; module-scoped fixtures amortize GenIce2 calls (mirrors test_e2e_custom_guest_hydrate.py)"

# Metrics
duration: 4 min
completed: 2026-07-05
---

# Phase 42 Plan 00: sH cage_type_map Bug Fix Summary

**Corrected the sH `cage_type_map` from `{small:12, large:16}` to `{small:12, medium:12_1, large:20}`, fixing the silent zero large-cage placement bug (large-only 0→2 guests) and making the medium cage reachable — guarded by a GenIce2-based regression test proving large placement works and small/large are independent cage types (6≠2).**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-05T08:07:52Z
- **Completed:** 2026-07-05T08:12:31Z
- **Tasks:** 2
- **Files modified:** 3 (2 modified + 1 created)

## Accomplishments
- Fixed the latent sH `cage_type_map` bug (a Phase 39 oversight): the large-cage id `"16"` was an sII id that does not exist in the sH lattice, so `parse_guest(guests, "16=ch4*1.0")` silently placed ZERO large-cage guests. Corrected to `"20"` (the real GenIce2 sH large-cage id).
- Added the missing `"medium": "12_1"` key so sH medium cages become reachable (was entirely absent — sH medium-cage assignment was impossible before Phase 42).
- Relaxed the `valid_keys` structural test to accept `medium` (sH) and `guest` (filled-ice alias completeness) keys, and added a dedicated `test_sh_cage_type_map_values` regression guard.
- Added `tests/test_e2e_sh_cage_occupancy.py` (3 GenIce2-based regression tests, module-scoped fixtures) proving: large-only places guests (0→2 after the fix), small-only places a different count (6), and the silent-zero bug has a value-agnostic sentinel (`>0`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix sH cage_type_map + relax valid_keys test** — `14ffcf7` (fix)
2. **Task 2: Add sH large-cage regression test (GenIce2-based)** — `07b0d82` (test)

**Plan metadata:** _(pending final docs commit)_

## Files Created/Modified
- `quickice/structure_generation/types.py` — sH `cage_type_map` corrected to `{"small": "12", "medium": "12_1", "large": "20"}` (line 118). No other lattice changed; the sH `cages` dict (small/medium/large) was left untouched per the plan's pitfall warning.
- `tests/test_hydrate_lattice_types.py` — `valid_keys` now `{"small", "large", "medium", "guest"}`; added `test_sh_cage_type_map_values` asserting the exact corrected sH map.
- `tests/test_e2e_sh_cage_occupancy.py` (created) — 3 GenIce2-based regression tests with module-scoped `sh_large_ch4` / `sh_small_ch4` fixtures.

## Decisions Made
- Used **empirically-verified** guest counts (2/6/8) in the regression test instead of the plan's research estimates (10/30/40). See *Deviations from Plan* for rationale.
- Added `"guest"` to `valid_keys` (not strictly required today) for future-proofing / filled-ice alias completeness, exactly as the plan instructed.
- Did **not** touch the sH `cages` dict — `HydrateLatticeInfo.from_lattice_type` already iterates `lattice["cages"].items()` and yields small/medium/large correctly; only `cage_type_map` was wrong (per the plan's explicit pitfall warning).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Regression test expected counts corrected from plan's research estimates to empirically-verified GenIce2 values**
- **Found during:** Task 2 (sH large-cage regression test)
- **Issue:** The plan's `<verify>` and `<success_criteria>` (and 42-RESEARCH.md) specified sH 1×1×1 large-only→10 guests, small-only→30, small+large→40. An empirical GenIce2 run showed the actual counts are **2 / 6 / 8**. Root cause: the research assumed a single crystallographic sH unit cell (34 waters, 3 small + 1 large), but GenIce2's `"sH"` lattice returns a cell containing **two** crystallographic unit cells (68 waters = 34×2 → 6 small + 2 large + 4 medium cages). Hardcoding 10/30 would have produced a failing/broken test that asserts `guest_count == 10` against actual output of 2.
- **Fix:** Wrote the regression test with the empirically-verified counts (`test_sh_large_places_guests` asserts `== 2`; `test_sh_small_only_places_more` asserts `== 6`; the value-agnostic `test_sh_large_more_than_zero` asserts `> 0`). All three pass. Confirmed the "before fix" behavior really was silent-zero (`parse_guest(guests, "16=ch4*1.0")` → `guest_count == 0`) by temporarily restoring the old `"16"` id, proving Task 1's `cage_type_map` fix is the cause (0 → 2). The fix itself (cage_type_map `16`→`20`, adding medium `12_1`) is **unchanged** from the plan — only the test's expected literal values differ.
- **Files modified:** tests/test_e2e_sh_cage_occupancy.py
- **Verification:** `pytest tests/test_e2e_sh_cage_occupancy.py -x` → 3 passed; before/after comparison (0 → 2) confirms the fix.
- **Committed in:** `07b0d82` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — wrong expected counts in the test specification)
**Impact on plan:** The correction is essential for the regression test to be meaningful (a test asserting `==10` against actual output of `2` would be broken). No scope creep; the plan's *intent* (prove large-cage placement works + small/large are independent cage types) is fully preserved with the corrected values.

## Issues Encountered
None. Both tasks executed cleanly; the only deviation was the wrong expected counts in the test spec (handled above).

## User Setup Required
None — no external service configuration required. Pure in-repo bug fix + regression test.

## Next Phase Readiness
- **42-00 prerequisite fix complete.** The sH `cage_type_map` is correct and the silent-zero large-cage bug is fixed + regression-guarded.
- **Ready for 42-01-PLAN.md** (data model: `CageGuestAssignment` + `HydrateConfig.cage_guest_assignments` + legacy shim + `HydrateStructure.guest_descriptors`). The sH medium key (`12_1`) is now reachable, so 42-01's medium-cage assignment work can proceed.
- **No blockers.**
- **Note for downstream plans (42-01+):** GenIce2's sH 1×1×1 cell contains **2** crystallographic unit cells (68 waters); per-cage multiplicities are **6 small / 4 medium / 2 large** (not 3/2/1). Downstream tests should use empirically-verified counts (run the generator, observe, then assert), not single-cell crystallographic estimates.

---
*Phase: 42-mixed-cage-occupancy*
*Completed: 2026-07-05*
