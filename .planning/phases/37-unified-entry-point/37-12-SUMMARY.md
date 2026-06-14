---
phase: 37-unified-entry-point
plan: 12
subsystem: docs
tags: [cli, documentation, invocation, python-m]

# Dependency graph
requires:
  - phase: 37-04
    provides: Unified entry point routing (python -m quickice canonical invocation)
provides:
  - Updated CLI reference with python -m quickice invocation throughout
affects: [37-13, 37-unified-entry-point]

# Tech tracking
tech-stack:
  added: []
  patterns: [python -m quickice as canonical CLI invocation]

key-files:
  created: []
  modified: [docs/cli-reference.md]

key-decisions:
  - "Global replaceAll safe: every python quickice.py occurrence is old invocation that must change"

patterns-established:
  - "python -m quickice: canonical CLI invocation replacing python quickice.py"

# Metrics
duration: <1min
completed: 2026-06-15
---

# Phase 37 Plan 12: CLI Reference python -m quickice Replacement Summary

**Replace all 27 python quickice.py references with python -m quickice in docs/cli-reference.md**

## Performance

- **Duration:** <1 min
- **Started:** 2026-06-14T19:01:40Z
- **Completed:** 2026-06-14T19:02:07Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- All 27 occurrences of `python quickice.py` replaced with `python -m quickice` in docs/cli-reference.md
- Zero remaining references to old invocation pattern
- Version output line updated (line 150: `python -m quickice 4.5.0`)

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace all python quickice.py refs in cli-reference.md** - `a759318` (docs)

**Plan metadata:** pending

## Files Created/Modified
- `docs/cli-reference.md` - Replaced 27 python quickice.py → python -m quickice occurrences

## Decisions Made
None - followed plan as specified. Global replaceAll was safe as every occurrence needed updating.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- docs/cli-reference.md ready for Plan 37-13 (new sections addition)
- All old invocation patterns eliminated, clean base for new content

---
*Phase: 37-unified-entry-point*
*Completed: 2026-06-15*
