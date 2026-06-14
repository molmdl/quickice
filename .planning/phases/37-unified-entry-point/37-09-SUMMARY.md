---
phase: 37-unified-entry-point
plan: 09
subsystem: testing
tags: [subprocess, conftest, cli-testing, pytest, pipeline]

# Dependency graph
requires:
  - phase: 37-06
    provides: "run_quickice(*args, timeout=60) subprocess helper in tests/conftest.py"
  - phase: 37-01
    provides: "quickice/entry.py unified entry point router"
  - phase: 37-02
    provides: "quickice/__main__.py for python -m quickice invocation"
provides:
  - "test_cli_pipeline.py migrated from quickice.py to python -m quickice via run_quickice()"
  - "28 subprocess calls using shared helper with timeout=120s"
affects: [37-10, 37-18]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "from tests.conftest import run_quickice (NOT from conftest — root conftest.py shadows)"
    - "timeout=120 explicit on all pipeline test calls (conftest default is 60s)"

key-files:
  created: []
  modified:
    - "tests/test_cli_pipeline.py"

key-decisions:
  - "from tests.conftest import run_quickice — root conftest.py shadows tests/conftest.py"
  - "timeout=120 explicit on every call — preserves original 120s default from run_cli()"
  - "Removed import sys — no longer needed after run_cli() removal"

patterns-established:
  - "Pipeline test files: timeout=120 explicit on every run_quickice() call (GenIce2 generation)"
  - "Flag validation tests also use timeout=120 for consistency within the same file"

# Metrics
duration: 12min
completed: 2026-06-14
---

# Phase 37 Plan 09: Migrate test_cli_pipeline.py Summary

**All 28 CLI pipeline subprocess calls migrated from run_cli(QUICKICE_SCRIPT) to run_quickice() with 120s timeout**

## Performance

- **Duration:** 12 min
- **Started:** 2026-06-14T19:10:27Z
- **Completed:** 2026-06-14T19:22:56Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Replaced QUICKICE_SCRIPT-based run_cli() with shared run_quickice() from conftest
- Added explicit timeout=120 to all 28 calls (preserving original 120s pipeline timeout)
- Removed unused imports (subprocess, sys)
- All 13 fast tests pass; 15 slow tests deselected with @pytest.mark.slow

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate test_cli_pipeline.py to use run_quickice()** - `9712a6d` (feat)

## Files Created/Modified
- `tests/test_cli_pipeline.py` - Replaced QUICKICE_SCRIPT/run_cli() with run_quickice(), added timeout=120 to all 28 calls

## Decisions Made
- **from tests.conftest import run_quickice** — Root conftest.py shadows tests/conftest.py; discovered in Plans 37-07 and 37-08. Package import (tests has __init__.py) resolves correctly.
- **timeout=120 explicit on every call** — Original run_cli() default was 120s for pipeline tests (GenIce2 generation). Conftest default is 60s. Every call gets explicit timeout=120 to preserve original behavior.
- **Removed import sys** — sys.executable was only used in run_cli(); now handled inside run_quickice().

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- test_cli_pipeline.py fully migrated to unified entry point invocation
- Plan 37-10 can proceed with test_integration_v35.py migration (same pattern)
- All pipeline test files in Wave 4 can now use shared run_quickice() helper

---
*Phase: 37-unified-entry-point*
*Completed: 2026-06-14*
