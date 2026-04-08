---
phase: 15-phase-diagram-data-update
plan: 08
subsystem: phase-mapping
tags: [ih-ii-boundary, ice-ic, metastable, iapws]

requires:
  - phase: 15-phase-diagram-data-update
    provides: Ice Ic polygon with corrected lower boundary (72K)

provides:
  - Ice Ic polygon with scientifically correct upper boundary
  - Ih-II boundary function integration

affects:
  - Phase diagram visualization accuracy
  - lookup_phase() correctness for Ice Ic region

tech-stack:
  added: []
  patterns: [boundary-function-integration]

key-files:
  created: []
  modified:
    - quickice/output/phase_diagram.py
    - quickice/phase_mapping/lookup.py

key-decisions:
  - "Ice Ic upper boundary follows Ih-II curve (~196-204 MPa) not arbitrary 100 MPa"

patterns-established:
  - "Use scientific boundary functions instead of hardcoded values for polygon definitions"

duration: 6 min
completed: 2026-04-08
---

# Phase 15 Plan 08: Ice Ic Upper Boundary Fix Summary

**Ice Ic polygon upper pressure boundary now follows Ih-II thermodynamic curve (~196-204 MPa) instead of arbitrary 100 MPa truncation**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-08T07:26:08Z
- **Completed:** 2026-04-08T07:33:04Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Updated `_build_ice_ic_polygon()` to use `ih_ii_boundary()` for upper pressure
- Fixed lookup_phase() Ice Ic boundary check to use Ih-II boundary function
- Corrected temperature boundary from `< 150` to `<= 150` (inclusive)
- Phase diagram now renders Ice Ic with scientifically accurate extent

## Task Commits

Each task was committed atomically:

1. **Task 1: Update Ice Ic polygon upper boundary to use Ih-II boundary** - `12dd1cf` (feat)

**Additional fix:** - `10b6606` (fix) - Updated lookup_phase() boundary check

## Files Created/Modified

- `quickice/output/phase_diagram.py` - Updated _build_ice_ic_polygon() function
- `quickice/phase_mapping/lookup.py` - Fixed Ice Ic boundary conditions in lookup_phase()

## Decisions Made

- Use Ih-II boundary function (ih_ii_boundary) for Ice Ic upper pressure limit
- Ice Ic is metastable wherever Ice Ih is stable, so boundaries should match

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed lookup_phase() Ice Ic boundary conditions**

- **Found during:** Test execution after updating phase_diagram.py
- **Issue:** Test `test_integration_different_phases` expected Ice Ic at (150K, 0 MPa) but got Ice Ih because lookup.py had hardcoded 100 MPa boundary and `T < 150` instead of `T <= 150`
- **Fix:** Updated lookup_phase() to use ih_ii_boundary(T) for upper pressure and changed temperature check to `<= 150`
- **Files modified:** quickice/phase_mapping/lookup.py
- **Verification:** All 79 phase-related tests pass
- **Committed in:** 10b6606

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Fix necessary for correctness. lookup_phase() must match polygon definition.

## Issues Encountered

- Pre-existing test failure in test_cli_integration.py (T=300K, P=100 MPa is liquid water region) - unrelated to this plan

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ice Ic polygon now has scientifically accurate boundaries
- Upper boundary correctly follows Ih-II curve
- Ready for milestone archival or additional gap closure plans
