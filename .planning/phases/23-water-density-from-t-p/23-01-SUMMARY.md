---
phase: 23-water-density-from-t-p
plan: 01
subsystem: phase-mapping
tags: [iapws, water-density, caching, supercooled-water, fallback]

# Dependency graph
requires:
  - phase: 22-ice-ih-iapws-density
    provides: IAPWS caching pattern, fallback density approach
provides:
  - IAPWS95 water density calculation with caching
  - Support for supercooled water (T < 273.15K)
  - Fallback density for out-of-range/invalid conditions
affects: [23-02, tab1-display, tab2-interface-generation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "@lru_cache(maxsize=256) for IAPWS density lookups"
    - "Fallback density 0.9998 g/cm³ (water at 0°C, 1 atm)"

key-files:
  created:
    - quickice/phase_mapping/water_density.py
    - tests/test_water_density.py
  modified: []

key-decisions:
  - "Use IAPWS95 (not IAPWS97) for supercooled water support"
  - "Fallback density 0.9998 g/cm³ = water at melting point"
  - "Sanity check requires rho > 100 kg/m³ to catch numerical issues"

patterns-established:
  - "Same caching/fallback pattern as ice_ih_density.py from Phase 22"

# Metrics
duration: 3min
completed: 2026-04-12
---

# Phase 23 Plan 01: IAPWS95 Water Density Module Summary

**IAPWS95 water density module with caching and supercooled water support (T < 273.15K via extrapolation)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-12T03:06:58Z
- **Completed:** 2026-04-12T03:10:52Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created water_density.py module following ice_ih_density.py pattern from Phase 22
- Implemented IAPWS95 water density calculation with @lru_cache(maxsize=256)
- Added support for supercooled water via IAPWS95 extrapolation (critical for ice-water interfaces)
- Created comprehensive test suite with 10 passing tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Create water_density.py module** - `da2e370` (feat)
2. **Task 2: Create tests for water density module** - `63ce87d` (test)

**Plan metadata:** (pending final commit)

_Note: Task 2 also included a fix to water_density.py sanity check_

## Files Created/Modified
- `quickice/phase_mapping/water_density.py` - IAPWS95 water density calculation with caching
- `tests/test_water_density.py` - Comprehensive test suite (10 tests)

## Decisions Made
- **IAPWS95 vs IAPWS97:** Use IAPWS95 because it supports supercooled water (T < 273.15K) via extrapolation, while IAPWS97 only works at T ≥ 273.15K
- **Fallback density:** 0.9998 g/cm³ = water density at melting point (0°C, 1 atm) - scientifically meaningful for ice-water interfaces
- **Sanity check threshold:** rho > 100 kg/m³ to catch numerical issues from invalid inputs (e.g., negative pressure returns ~1e-23 kg/m³)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed sanity check for invalid pressure**
- **Found during:** Task 2 (test_fallback_for_invalid_input)
- **Issue:** IAPWS95 returns ~1e-23 kg/m³ for negative pressure (not an exception), which passed the original sanity check `rho > 0 and rho < 2000`
- **Fix:** Changed sanity check to require `rho > 100 kg/m³` to catch numerical issues
- **Files modified:** quickice/phase_mapping/water_density.py
- **Verification:** All 10 tests pass, fallback correctly triggers for negative pressure
- **Committed in:** 63ce87d (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Fix ensures robust fallback behavior for edge cases

## Issues Encountered
None - IAPWS95 proved more robust than expected, handling extreme pressures via extrapolation

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Water density module ready for integration into Tab 1 display and Tab 2 interface generation
- Plan 23-02 will integrate water density into GUI and interface spacing

---
*Phase: 23-water-density-from-t-p*
*Completed: 2026-04-12*
