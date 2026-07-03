---
phase: 41-gromacs-export-for-custom-guests
plan: 09
subsystem: testing
tags: [gromacs, itp, test-fixture, custom-guest, hydrate-export, transform_guest_itp]

# Dependency graph
requires:
  - phase: 40-custom-guest-bridge-core
    provides: transform_guest_itp (comment atomtypes + _H moleculetype rename + [atoms] resname rewrite) and the etoh.itp custom guest fixture
provides:
  - "_stage_custom_guest_itp(workspace, itp_path, residue_name) -> str test helper (full _H transform staging)"
  - "Unit tests proving the staged custom guest ITP has moleculetype '{name}_H', [atomtypes] commented, [atoms] resname '{name}_H'"
affects: [41-10, 41-11, custom-guest-grompp, e2e-gmx-validation]

# Tech tracking
tech-stack:
  added: []
  patterns: ["transformed-ITP staging: call _stage_custom_guest_itp AFTER _stage_itp_files to overwrite the under-transformed (comment-only) copy with the fully-renamed one"]

key-files:
  created:
    - tests/test_e2e_stage_custom_guest_itp.py
  modified:
    - tests/e2e_export_helpers.py

key-decisions:
  - "Used the existing ETOH_ITP absolute path constant (e2e_export_helpers.py) in tests instead of the plan's cwd-relative Path('quickice/data/custom/etoh.itp') for cwd-independence; identical fixture, no behavioral change"
  - "Kept _stage_itp_files unchanged (built-in staging stays comment-only); the new helper is purely additive so existing grompp tests are unaffected"

patterns-established:
  - "Full-transform staging helper: _stage_custom_guest_itp applies transform_guest_itp (not just comment_out_atomtypes_in_itp) so staged custom guest ITPs are internally consistent with .top [molecules] '{name}_H'"
  - "Overwrite-after ordering: _stage_itp_files (stages tip4p-ice.itp + built-ins, comments custom etoh.itp atomtypes but keeps moleculetype 'etoh') then _stage_custom_guest_itp (overwrites etoh.itp with moleculetype 'MOL_H')"

# Metrics
duration: 5min
completed: 2026-07-03
---

# Phase 41 Plan 09: Custom Guest ITP Staging Helper Summary

**Test-only `_stage_custom_guest_itp` helper that stages a custom guest ITP with the full `_H` transform (moleculetype `MOL_H`, `[atomtypes]` commented, `[atoms]` resname `MOL_H`), closing the gap left by `_stage_itp_files` (comment-only) so custom-guest grompp e2e tests (plans 41-10/41-11) get a topology consistent with `.top [molecules] MOL_H`.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-07-03T13:33:01Z
- **Completed:** 2026-07-03T13:38:03Z
- **Tasks:** 2
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments
- Added `_stage_custom_guest_itp(workspace, itp_path, residue_name) -> str` to `tests/e2e_export_helpers.py` — applies the FULL `transform_guest_itp(content, residue_name, "_H")` pipeline (not just `comment_out_atomtypes_in_itp`) and writes the result to `workspace/<basename>`, returning the basename.
- Wrote 3 unit tests in `tests/test_e2e_stage_custom_guest_itp.py` proving: (1) staged etoh.itp has moleculetype `MOL_H` + `[atomtypes]` commented + `[atoms]` resname `MOL_H`; (2) the overwrite-after-`_stage_itp_files` pattern upgrades moleculetype `etoh` → `MOL_H`; (3) a >5-char base name (`ETHAN` → `ETHAN_H`, 7 chars) raises `ValueError`.
- Verified no regression: all 18 existing `test_e2e_gmx_validation.py` grompp tests still pass (the helper is purely additive).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _stage_custom_guest_itp helper** - `a3fbbad` (feat)
2. **Task 2: Unit tests for _stage_custom_guest_itp** - `db37ede` (test)

## Files Created/Modified
- `tests/e2e_export_helpers.py` - Added `_stage_custom_guest_itp(workspace, itp_path, residue_name) -> str` helper near `_stage_itp_files` (lines ~455-486). Reads `itp_path`, applies `transform_guest_itp(content, residue_name, suffix="_H")`, writes to `workspace/itp_path.name`, returns the basename. `_stage_itp_files` is unchanged.
- `tests/test_e2e_stage_custom_guest_itp.py` - New test file with 3 unit tests (`test_stages_transformed_mol_h`, `test_overwrites_under_transformed_copy`, `test_name_too_long_raises`) plus a `_moleculetype_name(text)` local helper that extracts the `[ moleculetype ]` name for assertions.

## Decisions Made
- **Used `ETOH_ITP` absolute path constant** (already exported from `e2e_export_helpers.py`) instead of the plan's cwd-relative `Path("quickice/data/custom/etoh.itp")` in the test assertions. Rationale: identical fixture, but cwd-independent — robust regardless of pytest's invocation directory. The helper signature accepts any path; only the test's fixture choice changed. No behavioral change to the success criteria.
- **Kept `_stage_itp_files` unchanged** (built-in staging stays comment-only). The new helper is purely additive — existing grompp tests that depend on `_stage_itp_files`'s comment-only behavior are unaffected, confirmed by the 18/18 regression pass.

## Deviations from Plan

None — plan executed as written. The only adjustment (using `ETOH_ITP` instead of the relative path in the test) is a fixture-robustness choice that does not alter any success criterion; the helper implementation matches the plan's code block verbatim.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `_stage_custom_guest_itp` is importable from `e2e_export_helpers` and ready for plans 41-10 (GUI custom-guest grompp) and 41-11 (CLI custom-guest grompp). The expected call pattern: `_stage_itp_files(top_path, workspace)` first (stages tip4p-ice.itp + comments custom etoh.itp atomtypes), then `_stage_custom_guest_itp(workspace, ETOH_ITP, "MOL")` to overwrite etoh.itp with the `MOL_H`-renamed copy, so `gmx grompp` sees a topology consistent with `.top [molecules] MOL_H`.
- The contract is enforced by `transform_guest_itp`'s `validate_gro_residue_name` call: base names ≤3 chars (`MOL` → `MOL_H`, 5 chars) pass; longer bases raise `ValueError` (covered by `test_name_too_long_raises`).

---
*Phase: 41-gromacs-export-for-custom-guests*
*Completed: 2026-07-03*
