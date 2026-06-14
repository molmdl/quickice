---
phase: 37-unified-entry-point
plan: 16
subsystem: docs
tags: [readme, binary, cli, gui, platform-invocation]

# Dependency graph
requires:
  - phase: 37-unified-entry-point
    provides: Unified binary with CLI+GUI mode support (Plans 37-01 to 37-05)
provides:
  - Platform invocation table in README_bin.md
  - CLI mode documentation for binary users
  - GUI mode section restructuring
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - README_bin.md

key-decisions:
  - "Platform invocation table covers source install, binary Linux/macOS, binary Windows"
  - "CLI Mode section with quickice-gui flag examples"
  - "Existing Linux/Windows instructions become sub-sections of GUI Mode"

patterns-established: []

# Metrics
duration: 1min
completed: 2026-06-15
---

# Phase 37 Plan 16: README_bin.md Platform Invocation Summary

**Platform invocation table and CLI mode documentation added to binary distribution guide**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-06-14T19:03:50Z
- **Completed:** 2026-06-14T19:04:16Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Platform Invocation table showing source install, binary Linux/macOS, and binary Windows commands
- CLI Mode section with `quickice-gui` flag examples and link to CLI reference docs
- GUI Mode section restructuring with existing Linux/Windows instructions as sub-sections
- Added note that CLI flags also work with the binary

## Task Commits

Each task was committed atomically:

1. **Task 1: Add platform invocation table and CLI mode docs to README_bin.md** - `6287a8f` (docs)

## Files Created/Modified
- `README_bin.md` - Binary distribution guide with platform invocation table, CLI mode, and GUI mode sections

## Decisions Made
- Platform invocation table uses `[options]` placeholder for all platforms (concise, avoids duplication)
- Windows `.exe` note is a one-liner ("Windows users: append `.exe`") instead of per-row explanation
- CLI examples show both implicit CLI (pipeline flags) and explicit `--cli` mode
- Existing Linux/Windows instructions kept intact, restructured as sub-sections under GUI Mode
- Added note about CLI flags working with binary (e.g., `./quickice-gui/quickice-gui -T 300 -P 0.1 -N 100`)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- README_bin.md fully documents dual-mode binary behavior
- No blockers or concerns for subsequent plans

---
*Phase: 37-unified-entry-point*
*Completed: 2026-06-15*
