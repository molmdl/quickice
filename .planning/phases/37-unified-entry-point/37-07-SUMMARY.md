---
phase: 37-unified-entry-point
plan: 07
subsystem: testing
tags: [pytest, subprocess, unittest.mock, entry-point, routing]

# Dependency graph
requires:
  - phase: 37-01
    provides: "entry.py with main() routing logic and _is_pyside6_available/_has_display helpers"
  - phase: 37-02
    provides: "parser.py with --cli/--gui flags and create_parser()"
  - phase: 37-06
    provides: "conftest.py run_quickice() subprocess helper"
provides:
  - "tests/test_entry_point.py with 12 routing tests"
affects: [37-08, 37-09, 37-10, 37-11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Subprocess tests for integration, direct function call for mock-based tests"
    - "from tests.conftest import run_quickice avoids root conftest.py shadowing"

key-files:
  created:
    - tests/test_entry_point.py
  modified: []

key-decisions:
  - "from tests.conftest import run_quickice instead of from conftest (root conftest.py shadows tests/conftest.py)"
  - "Use valid ice conditions -T 250 -P 0.1 -N 96 for pipeline tests (plan's -T 300 -P 0.1 is not a valid ice phase, exits 1)"

patterns-established:
  - "Subprocess vs direct-call test split: subprocess for real integration, direct entry.main() call for mock-based tests"

# Metrics
duration: 5min
completed: 2026-06-15
---

# Phase 37 Plan 07: Entry Point Routing Tests Summary

**12 dedicated tests validating unified entry point routing via subprocess and mock-based direct calls**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-14T19:03:54Z
- **Completed:** 2026-06-14T19:08:38Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created tests/test_entry_point.py with 12 tests covering all routing behaviors from CONTEXT.md
- Validated no-args→help, --help, --version, --cli alone error, --cli + pipeline, implicit CLI, --gui missing PySide6, --gui no display, backward compat
- Established subprocess/direct-call test pattern (subprocess for real integration, direct entry.main() for mocks)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tests/test_entry_point.py with 10 routing tests** - `e154181` (feat)

## Files Created/Modified
- `tests/test_entry_point.py` - 12 tests in 5 classes covering all entry point routing behaviors (156 lines)

## Decisions Made
- Used `from tests.conftest import run_quickice` instead of `from conftest import run_quickice` because root conftest.py (project-level pytest config) shadows tests/conftest.py, causing ImportError
- Used valid ice conditions `-T 250 -P 0.1 -N 96 --no-diagram` for pipeline tests instead of plan's `-T 300 -P 0.1 -N 100` which exits 1 (no ice at 300K/0.1MPa)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed invalid ice conditions in pipeline tests**
- **Found during:** Task 1 (creating test_entry_point.py)
- **Issue:** Plan specified `-T 300 -P 0.1 -N 100` which is not a valid ice phase condition — main() catches UnknownPhaseError and returns exit code 1, not 0
- **Fix:** Changed to `-T 250 -P 0.1 -N 96 --no-diagram` (Ice Ih at 250K/0.1MPa, exits 0). Added --no-diagram to reduce runtime.
- **Files modified:** tests/test_entry_point.py
- **Verification:** All 12 tests pass with exit code 0 for pipeline tests
- **Committed in:** e154181 (Task 1 commit)

**2. [Rule 3 - Blocking] Fixed conftest import shadowing**
- **Found during:** Task 1 (first test run failed with ImportError)
- **Issue:** `from conftest import run_quickice` imported root conftest.py (project-level pytest config) instead of tests/conftest.py, causing ImportError
- **Fix:** Changed to `from tests.conftest import run_quickice` which correctly resolves the tests package
- **Files modified:** tests/test_entry_point.py
- **Verification:** Tests collect and pass successfully
- **Committed in:** e154181 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both auto-fixes necessary for correct test execution. No scope creep.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Entry point routing fully tested with 12 dedicated tests
- Remaining plans (37-08 through 37-11, 37-13, 37-15 through 37-18) can rely on these routing tests as regression coverage
- test_entry_point.py can be extended for additional routing edge cases if needed

---
*Phase: 37-unified-entry-point*
*Completed: 2026-06-15*
