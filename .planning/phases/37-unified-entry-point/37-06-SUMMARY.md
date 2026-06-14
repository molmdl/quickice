---
phase: 37-unified-entry-point
plan: 06
subsystem: testing
tags: [subprocess, conftest, cli-testing, pytest]

# Dependency graph
requires: []
provides:
  - "run_quickice(*args, timeout=60) subprocess helper in tests/conftest.py"
affects: [37-07, 37-08, 37-09, 37-10, 37-11, 37-12, 37-13, 37-14, 37-15, 37-16, 37-17, 37-18]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Subprocess-based CLI testing via run_quickice() in conftest.py"
    - "python -m quickice as canonical invocation (not quickice.py)"
    - "Local imports inside helper function (no namespace pollution)"

key-files:
  created: []
  modified:
    - "tests/conftest.py"

key-decisions:
  - "import subprocess/sys inside function body to avoid polluting conftest module namespace"
  - "Default timeout 60s matching test_integration_v35.py's convention"
  - "python -m quickice invocation (canonical) instead of quickice.py path"

patterns-established:
  - "Shared subprocess helper: single run_quickice() replaces per-file run_cli() helpers"
  - "Timeout overridable per-call: run_quickice(..., timeout=120) for slow pipelines"

# Metrics
duration: 1min
completed: 2026-06-14
---

# Phase 37 Plan 06: Add run_quickice() Helper Summary

**Shared run_quickice(*args, timeout=60) subprocess helper in conftest.py using python -m quickice invocation**

## Performance

- **Duration:** 1 min
- **Started:** 2026-06-14T18:56:41Z
- **Completed:** 2026-06-14T18:57:56Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added run_quickice() helper to tests/conftest.py as shared subprocess-based CLI testing function
- Uses canonical `python -m quickice` invocation (not quickice.py)
- Returns (returncode, stdout, stderr) tuple for flexible assertions
- Default timeout 60s with per-call override capability

## Task Commits

Each task was committed atomically:

1. **Task 1: Add run_quickice() helper to tests/conftest.py** - `688f3b6` (feat)

## Files Created/Modified
- `tests/conftest.py` - Added run_quickice() function at end of file (30 lines appended)

## Decisions Made
- **Local imports inside function body** — `import subprocess` and `import sys` placed inside `run_quickice()` to avoid polluting the conftest module namespace. Other fixtures already import their own dependencies at module level.
- **Default timeout 60s** — Matches test_integration_v35.py's convention. Individual test files can override: `run_quickice(..., timeout=120)`.
- **python -m quickice invocation** — Canonical entry point that will work once Plans 01+02 create entry.py and __main__.py.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- run_quickice() helper ready for use in CLI integration tests
- Will work once Plans 01+02 create quickice/entry.py and quickice/__main__.py
- Test files can now `from conftest import run_quickice` instead of defining local run_cli() helpers

---
*Phase: 37-unified-entry-point*
*Completed: 2026-06-14*
