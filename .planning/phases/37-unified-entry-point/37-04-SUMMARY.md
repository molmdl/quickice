---
phase: 37-unified-entry-point
plan: 04
subsystem: cli
tags: [argparse, prog-name, discoverability, entry-point]

# Dependency graph
requires:
  - phase: 36-cli-feature-parity
    provides: CLI parser infrastructure with v4.5 pipeline flags
provides:
  - Updated prog name "python -m quickice" in argparse
  - --cli and --gui mode selection flags for discoverability
  - Consistent epilog examples using "python -m quickice"
affects: [37-05, 37-06, entry-router, unified-entry-point]

# Tech tracking
tech-stack:
  added: []
  patterns: [discoverability-flags-in-parser, mode-selection-before-argparse]

key-files:
  created: []
  modified: [quickice/cli/parser.py]

key-decisions:
  - "--cli/--gui flags with default=False for backward compatibility"
  - "Mode flags consumed by entry router before argparse runs; added to parser for --help discoverability only"

patterns-established:
  - "Discoverability flags: add flags to argparse for --help visibility even when consumed earlier by entry router"

# Metrics
duration: 2min
completed: 2026-06-14
---

# Phase 37 Plan 04: Parser Prog Name & Mode Flags Summary

**Updated argparse prog to 'python -m quickice', replaced all 6 epilog examples, added --cli/--gui mode flags for discoverability**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-14T18:56:29Z
- **Completed:** 2026-06-14T18:58:01Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Changed prog from "python quickice.py" to "python -m quickice" in ArgumentParser
- Replaced all 6 epilog example references with "python -m quickice"
- Added --cli flag (store_true, default=False) with help text for headless/CI discoverability
- Added --gui flag (store_true, default=False) with help text for GUI mode discoverability
- Both flags appear in --help output with visible descriptions

## Task Commits

Each task was committed atomically:

1. **Task 1: Update parser.py — prog name, epilog examples, add --cli/--gui flags** - `5d63eaf` (feat)

## Files Created/Modified
- `quickice/cli/parser.py` - Updated prog name, epilog examples, added --cli/--gui mode flags

## Decisions Made
- `--cli` and `--gui` flags use `default=False` to avoid interfering with existing behavior
- Mode flags are consumed by entry router before argparse runs; they are added to the parser solely for `--help` discoverability and to prevent argparse from rejecting them as unrecognized arguments
- Epilog example count is 6 (not 7 as plan stated); plan had a minor count discrepancy but all occurrences were correctly replaced

## Deviations from Plan

None - plan executed exactly as written (minor count discrepancy in plan: epilog has 6 examples, not 7; all were replaced correctly).

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Parser updated with new prog name and mode flags
- Ready for entry router (Plan 05+) that will consume --cli/--gui before argparse
- No "python quickice.py" references remain in parser.py

---
*Phase: 37-unified-entry-point*
*Completed: 2026-06-14*
