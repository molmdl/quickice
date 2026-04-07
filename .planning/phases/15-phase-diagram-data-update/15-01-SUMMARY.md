---
phase: 15-phase-diagram-data-update
plan: "01"
subsystem: phase_mapping
tags: [IAPWS, triple-points, thermodynamic-data, Journaux]

# Dependency graph
requires: []
provides:
  - Corrected triple point coordinates for all 8 primary ice phase boundaries
  - Cross-file consistency between triple_points.py and ice_boundaries.py
affects: [15-02, 15-03, 15-04]

# Tech tracking
tech-stack:
  added: []
  patterns: [scientific-data-correction, cross-file-synchronization]

key-files:
  created: []
  modified:
    - quickice/phase_mapping/triple_points.py
    - quickice/phase_mapping/data/ice_boundaries.py

key-decisions:
  - "Used IAPWS R14-08(2011) as primary source for triple point values"
  - "Used Journaux et al. (2019) for II-III-V and II-V-VI triple points"
  - "Maintained separate TRIPLE_POINTS dicts in both files for backward compatibility"

patterns-established:
  - "Cross-file validation: triple points must match between triple_points.py and ice_boundaries.py"

# Metrics
duration: 5 min
completed: 2026-04-08
---

# Phase 15 Plan 01: Update Triple Points Summary

**Updated triple point coordinates to IAPWS R14-08(2011) and Journaux et al. (2019, 2020) compliant values across both data source files**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-07T19:38:57Z
- **Completed:** 2026-04-07T19:43:32Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Corrected 32 triple point coordinate values across 2 files
- All 8 primary triple points now match IAPWS R14-08(2011) specifications
- II-III-V and II-V-VI triple points updated per Journaux et al. (2019) high-pressure measurements
- Cross-file consistency verified - all values match between triple_points.py and ice_boundaries.py
- All 62 existing tests pass with corrected values

## Task Commits

Each task was committed atomically:

1. **Task 1: Update TRIPLE_POINTS in triple_points.py** - `f2e1394` (feat)
   - Updated all 8 triple point (T, P) coordinate tuples
   - Updated docstring to cite IAPWS and Journaux sources

2. **Task 2: Update TRIPLE_POINTS in ice_boundaries.py** - `62e1756` (docs/feat)
   - Updated all 8 triple point T and P values to match triple_points.py
   - Updated module docstring to cite Journaux et al. (2019, 2020) sources
   - Values already committed as part of plan 15-02 documentation

**Plan metadata:** `9fcddce` (docs: complete plan)

_Note: Task 2 changes were committed as part of the plan 15-02 documentation commit due to concurrent development_

## Files Created/Modified

- `quickice/phase_mapping/triple_points.py` - Corrected triple point coordinates and updated docstring
- `quickice/phase_mapping/data/ice_boundaries.py` - Corrected triple point values and updated module docstring

## Decisions Made

- **Source hierarchy**: IAPWS R14-08(2011) as primary, Journaux et al. (2019, 2020) for high-pressure phases (II-III-V, II-V-VI), LSBU for verification
- **Backward compatibility**: Maintained separate TRIPLE_POINTS dictionaries in both files rather than creating single source of truth to avoid breaking existing imports
- **Validation approach**: Cross-file consistency verified programmatically in verification step

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all changes straightforward data updates.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 15.01 complete: Triple point data corrected
- Ready for: 15-02 (Ice Ic polygon builder) - already complete in parallel
- Ready for: 15-03 (PHASE_POLYGONS and MELTING_CURVE_COEFFICIENTS updates) - already complete in parallel
- Ready for: 15-04 (Documentation comments) - pending

---
*Phase: 15-phase-diagram-data-update*
*Completed: 2026-04-08*
