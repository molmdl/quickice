---
phase: 15-phase-diagram-data-update
plan: 07
subsystem: data-consistency
tags: [triple-points, phase-diagram, polygon-builders, iapws-r14-08]

# Dependency graph
requires:
  - phase: 15-01 to 15-04
    provides: Corrected triple point data in triple_points.py
provides:
  - All polygon builders use get_triple_point() for boundary values
  - No hardcoded old triple point values remain in phase_diagram.py
  - Polygon boundaries align with corrected thermodynamic data
affects: [phase-diagram-visualization, phase-lookup-accuracy]

# Tech tracking
tech-stack:
  added: []
  patterns: [single-source-of-truth, function-calls-instead-of-hardcoded-values]

key-files:
  created: []
  modified:
    - quickice/output/phase_diagram.py - Updated 3 polygon builders to use get_triple_point()

key-decisions:
  - "Use get_triple_point() calls for all boundary vertices instead of hardcoded values"
  - "Move triple point lookups to beginning of polygon builders to avoid forward references"
  - "Update comments to not reference specific hardcoded numbers"

patterns-established:
  - "All polygon builders fetch triple point values via get_triple_point()"
  - "Boundary sampling ranges use variables from triple point lookups"
  - "Cold edge calculations use T3/P3 variables instead of magic numbers"

# Metrics
duration: 8 min
completed: 2026-04-08
---

# Phase 15 Plan 07: Fix Hardcoded Old Triple Point Values Summary

**All polygon builders now use get_triple_point() for triple point boundaries, eliminating hardcoded old values and ensuring consistency with corrected IAPWS R14-08(2011) data.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-07T20:23:38Z
- **Completed:** 2026-04-08T00:31:42Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- Fixed Ice Ih polygon to use get_triple_point() for Ih-III-Liquid and Ih-II-III boundaries
- Fixed Ice II polygon to use get_triple_point() for II-III-V and II-V-VI boundaries, with reordered calls to avoid forward references
- Fixed Ice VI polygon comments to not reference hardcoded old values
- All 62 phase mapping tests pass with corrected boundary values
- Verified no old hardcoded values (248.85, 218.95, 207.5, 238.55) remain

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix hardcoded values in _build_ice_ih_polygon** - `3820a6c` (fix)
2. **Task 2: Fix hardcoded values in _build_ice_ii_polygon** - `bbc1568` (fix)
3. **Task 3: Fix hardcoded values in _build_ice_vi_polygon comments** - `29c7925` (fix)

**Plan metadata:** Pending commit (docs: complete plan)

_Note: All changes are bug fixes to ensure data consistency_

## Files Created/Modified

- `quickice/output/phase_diagram.py` - Updated 3 polygon builders to use get_triple_point() instead of hardcoded values

## Decisions Made

- Reordered get_triple_point() calls at the beginning of _build_ice_ii_polygon() to avoid forward reference errors
- Changed boundary sampling ranges to use variables from triple point lookups instead of magic numbers
- Updated cold edge calculations in Ice II to use T3 and P3 variables for line equation
- Removed specific hardcoded values from comments to prevent confusion

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed smoothly without issues.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All polygon builders now use corrected triple point values from the single source of truth (triple_points.py)
- Phase diagram boundaries align with IAPWS R14-08(2011) compliant thermodynamic data
- All existing tests pass with the corrected values
- Ready for gap closure completion and final verification

---
*Phase: 15-phase-diagram-data-update*
*Completed: 2026-04-08*
