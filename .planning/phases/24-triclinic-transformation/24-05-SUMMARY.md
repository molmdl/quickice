---
phase: 24-triclinic-transformation
plan: 05
subsystem: types
tags: [candidate, dataclass, triclinic, cleanup]

# Dependency graph
requires:
  - phase: 24-triclinic-transformation
    provides: Removed transformation approach, Candidate stores native structure
provides:
  - Clean Candidate dataclass without original_* fields
  - Simplified molecular viewer displaying native triclinic structures
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - quickice/structure_generation/types.py
    - quickice/gui/molecular_viewer.py

key-decisions:
  - "Removed original_positions/original_cell fields - no longer needed after transformation removal"
  - "Candidate now stores native triclinic structure directly"

patterns-established:
  - "Native triclinic cell display in Tab 1 viewer"

# Metrics
duration: 18 min
completed: 2026-04-13
---

# Phase 24 Plan 05: Remove Candidate Fields Summary

**Simplified Candidate dataclass and molecular viewer by removing transformation-related fields**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-13T06:34:37Z
- **Completed:** 2026-04-13T06:52:47Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Removed original_positions and original_cell fields from Candidate dataclass
- Updated Candidate docstrings to reflect native triclinic handling
- Simplified molecular viewer to display candidate structures directly
- Removed conditional display logic for transformed vs native structures
- Verified no remaining references to original_* fields in codebase

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove original_positions and original_cell from Candidate** - `3c2f4d8` (feat)
2. **Task 2: Simplify molecular_viewer to use candidate directly** - `e8bc8c8` (feat)
3. **Task 3: Search and clean any other original_* references** - `51f37ba` (refactor)

**Plan metadata:** (will be added after commit)

_Note: TDD tasks may have multiple commits (test → feat → refactor)_

## Files Created/Modified
- `quickice/structure_generation/types.py` - Removed original_positions and original_cell fields, updated docstrings
- `quickice/gui/molecular_viewer.py` - Simplified set_candidate(), set_hydrogen_bonds_visible(), and set_unit_cell_visible() to use candidate directly

## Decisions Made
None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - all tests passed on first run after changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Candidate dataclass is now clean and simple
- Molecular viewer displays native structures for all phases
- Ready for next phase (if any remaining in v3.5)

---
*Phase: 24-triclinic-transformation*
*Completed: 2026-04-13*