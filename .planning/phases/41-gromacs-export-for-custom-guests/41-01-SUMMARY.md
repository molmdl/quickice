---
phase: 41-gromacs-export-for-custom-guests
plan: 01
subsystem: testing
tags: [gromacs, atomtypes, tdd, dedup, itp]

# Dependency graph
requires:
  - phase: 40-custom-guest-itp-transform
    provides: GAFF2_ATOMTYPES dict, parse_itp_atomtypes, _check_custom_atomtype_conflict, _format_custom_atomtype_line primitives reused by the helper
provides:
  - "_merge_custom_atomtypes(f, itp_path, written, label) shared merge+dedup primitive for custom molecule [ atomtypes ] blocks"
affects: [EXPORT-03, write_multi_molecule_top_file, write_interface_top_file, hydrate-gui-export, cli-interface-export]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Additive TDD extraction: write failing tests for a shared helper, implement verbatim equivalent of the canonical inline reference, leave existing call sites untouched (zero regression risk)"

key-files:
  created:
    - tests/test_output/test_merge_custom_atomtypes.py
  modified:
    - quickice/output/gromacs_writer.py

key-decisions:
  - "Add helper ONLY — no refactor of existing inline merge call sites in write_custom_molecule_top_file / write_ion_top_file (refactor deferred to consumer phases; zero regression risk this plan)"
  - "Use GAFF2_ATOMTYPES as the pre-seed source of truth in the real-fixture test (importable, exact LJ-param match with etoh.itp hc/c3/h1) instead of hardcoding fallback values"
  - "No-op returns BEFORE writing the '; label' comment header — the header is written only when parse_itp_atomtypes returns a non-empty list"

patterns-established:
  - "TDD extract-and-test: RED failing tests → GREEN verbatim-canonical implementation → leave existing triplicated inline code untouched"
  - "cwd-independent fixture paths from tests/test_output/ subdir require three Path.parent levels (tests/test_output/ → tests/ → project root)"

# Metrics
duration: 6min
completed: 2026-07-03
---

# Phase 41 Plan 01: _merge_custom_atomtypes Helper Summary

**Shared tested `_merge_custom_atomtypes(f, itp_path, written, label)` primitive that parses a custom ITP's [ atomtypes ], conflict-checks against already-written atomtypes, and writes+records only the new ones (dedup) — extracted additively from the triplicated inline merge pattern with zero call-site refactor.**

## Performance

- **Duration:** 6 min (355 s)
- **Started:** 2026-07-03T13:41:34Z
- **Completed:** 2026-07-03T13:47:29Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `_merge_custom_atomtypes(f, itp_path, written, label)` to `quickice/output/gromacs_writer.py` (placed after `_lj_params_match`, before `MOLECULE_TO_GROMACS`), reusing the existing `parse_itp_atomtypes` / `_check_custom_atomtype_conflict` / `_format_custom_atomtype_line` primitives.
- 5 unit tests proving all four contract behaviors (new-write, dedup-on-match, ValueError-on-LJ-mismatch, no-section no-op) plus a real `etoh.itp` integration test that dedups GAFF2-shared types (hc, c3, h1) and writes ethanol-only types (oh, ho).
- Confirmed zero regression: all 46 existing gromacs tests in `tests/test_output/` still pass; helper is purely additive (existing inline merge code untouched).

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Write failing tests** - `e5aff7a` (test)
2. **Task 2 (GREEN): Implement _merge_custom_atomtypes** - `b388b16` (feat)

_Note: TDD task; the test path fix needed to reach GREEN was folded into the GREEN commit (see Deviations)._

## Files Created/Modified
- `tests/test_output/test_merge_custom_atomtypes.py` - 5 unit tests (new-write, dedup, LJ-conflict, no-section no-op, real etoh.itp integration)
- `quickice/output/gromacs_writer.py` - Added `_merge_custom_atomtypes` helper (39 insertions, placed after `_lj_params_match`)

## Decisions Made
- **Add helper only, no call-site refactor:** The plan objective explicitly scopes this plan to adding the helper; the existing inline merge code in `write_custom_molecule_top_file` (~lines 2648-2670) and `write_ion_top_file` (~lines 2238-2262) is intentionally left untouched. This keeps regression risk at exactly zero — the two future call sites (hydrate GUI `write_multi_molecule_top_file`, CLI `write_interface_top_file`) and the EXPORT-03 refactor will consume the helper in later plans.
- **GAFF2_ATOMTYPES as test source of truth:** Test 5 pre-seeds `written` from `GAFF2_ATOMTYPES` (importable at `gromacs_writer.py:67`) rather than hardcoding LJ values, guaranteeing the pre-seed exactly matches `etoh.itp`'s hc/c3/h1 entries so dedup is exercised deterministically.
- **No-op semantics:** The helper returns before writing the `; {label}` comment header when `parse_itp_atomtypes` returns `[]`, so a no-section ITP produces a truly empty file (verified by `test_no_atomtypes_section_is_noop` asserting `f.getvalue() == ""`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test 5 fixture path (two `.parent` levels instead of three)**
- **Found during:** Task 2 (GREEN — first run after implementing the helper)
- **Issue:** Test 5 used `Path(__file__).parent.parent / "quickice" / ...` to locate `etoh.itp`. This file lives in `tests/test_output/`, so `.parent.parent` resolves to `tests/` (not the project root), yielding the nonexistent path `tests/quickice/data/custom/etoh.itp`. The bug was latent during RED because collection errored on the missing `_merge_custom_atomtypes` import before test 5 could run.
- **Fix:** Changed to `Path(__file__).parent.parent.parent / "quickice" / "data" / "custom" / "etoh.itp"` (three `.parent` levels: `tests/test_output/` → `tests/` → project root). Matches the cwd-independence convention used by `tests/test_transform_guest_itp_atoms.py` (which lives directly in `tests/` and uses two levels).
- **Files modified:** tests/test_output/test_merge_custom_atomtypes.py
- **Verification:** All 5 tests pass; test 5 now resolves the real fixture and asserts oh/ho are written while hc/c3/h1 are deduped.
- **Committed in:** b388b16 (folded into the GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The path fix was necessary for test 5 to run at all; it is a test-only change with no impact on the shipped helper. No scope creep — the helper implementation is verbatim the plan's specified code.

## Issues Encountered
- `git add quickice/output/gromacs_writer.py` printed a spurious "paths are ignored by your .gitignore" warning, but the file is already tracked (`git ls-files` confirms) and was staged correctly; the warning did not block the commit. No action needed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `_merge_custom_atomtypes` is importable and tested; ready to be consumed by EXPORT-03 and the two planned call-site refactors (hydrate GUI `write_multi_molecule_top_file`, CLI `write_interface_top_file`).
- The existing inline merge code in `write_custom_molecule_top_file` / `write_ion_top_file` remains the source of truth for behavior until those consumer plans refactor them to call the helper — this plan intentionally did not touch them.
- No blockers; the 41-01 helper is a verified primitive for the remaining Phase 41 plans.

---
*Phase: 41-gromacs-export-for-custom-guests*
*Completed: 2026-07-03*
