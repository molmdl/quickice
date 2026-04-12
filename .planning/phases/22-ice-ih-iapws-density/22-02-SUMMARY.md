---
phase: 22-ice-ih-iapws-density
plan: 02
subsystem: phase-mapping
tags: [iapws, density, ice-ih, lookup, temperature-dependent]

# Dependency graph
requires:
  - phase: 22-01
    provides: ice_ih_density_gcm3 function with IAPWS R10-06(2009) calculation
provides:
  - IAPWS Ice Ih density integrated into lookup_phase
  - Updated scorer.py comments documenting IAPWS usage
affects: [ranking, structure-generation, gui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Conditional density calculation in _build_result (Ice Ih: IAPWS, others: fixed)

key-files:
  created: []
  modified:
    - quickice/phase_mapping/lookup.py
    - quickice/ranking/scorer.py
    - tests/test_phase_mapping.py

key-decisions:
  - "Ice Ih density now flows: IAPWS → ice_ih_density_gcm3 → lookup_phase → phase_info dict"
  - "Other ice phases continue using fixed density from PHASE_METADATA"
  - "Fallback density 0.9167 g/cm³ kept for IAPWS out-of-range conditions"

patterns-established:
  - "Conditional density calculation: Ice Ih uses IAPWS, other phases use fixed values"

# Metrics
duration: 4min
completed: 2026-04-11
---

# Phase 22 Plan 02: Integrate IAPWS Density into Lookup Summary

**IAPWS Ice Ih density now flows through lookup_phase to phase_info dict, enabling temperature-dependent density for all downstream consumers.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-11T19:51:53Z
- **Completed:** 2026-04-11T19:55:36Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Modified `_build_result()` to call IAPWS for Ice Ih density calculation
- Updated PHASE_METADATA density_note per CONTEXT.md decision
- Updated scorer.py comments to document IAPWS density usage
- Fixed test to use approximate comparison for temperature-dependent density

## Task Commits

Each task was committed atomically:

1. **Task 1: Modify _build_result in lookup.py to use IAPWS for Ice Ih** - `ee19631` (feat)
2. **Task 2: Update scorer.py fallback comment and verify tests** - `77bbac4` (docs)

## Files Created/Modified
- `quickice/phase_mapping/lookup.py` - Added conditional IAPWS density calculation for Ice Ih
- `quickice/ranking/scorer.py` - Updated comments to document IAPWS usage
- `tests/test_phase_mapping.py` - Fixed test for approximate density comparison

## Decisions Made
- Ice Ih density now flows: IAPWS → ice_ih_density_gcm3 → lookup_phase → phase_info dict
- Other ice phases continue using fixed density from PHASE_METADATA
- Fallback density 0.9167 g/cm³ kept for IAPWS out-of-range conditions

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test for temperature-dependent density**
- **Found during:** Task 2 (test verification)
- **Issue:** test_lookup_atmospheric_near_melting used exact equality check for density, but density is now IAPWS-calculated (returns 0.9167328684904943 instead of exactly 0.9167)
- **Fix:** Changed to approximate comparison `abs(result["density"] - 0.9167) < 0.001`
- **Files modified:** tests/test_phase_mapping.py
- **Verification:** All 62 phase mapping tests pass
- **Committed in:** 77bbac4 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Test fix necessary for IAPWS integration. No scope creep.

## Issues Encountered
None - plan executed smoothly with one expected test update.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- IAPWS density now flows through lookup_phase → phase_info dict
- All downstream consumers (scorer, CLI, GUI) receive temperature-dependent density for Ice Ih
- Ready for 22-03 to update remaining consumers to display IAPWS density

---
*Phase: 22-ice-ih-iapws-density*
*Completed: 2026-04-11*
