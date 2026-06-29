---
phase: 39-extended-lattice-types
plan: 02
subsystem: structure-generation
tags: [genice2, hydrate, cage-type-map, filled-ice, water-only, parse-guest]

# Dependency graph
requires:
  - phase: 39-01
    provides: HYDRATE_LATTICES with cage_type_map/is_water_only for all 10 lattice types
provides:
  - HydrateStructureGenerator supports all 10 lattice types
  - cage_type_map-driven parse_guest routing (no hardcoded 12/14/16)
  - Water-only lattice handling (no guest placement)
  - Filled ice handling (single Ne1 cage type, no double-placement)
affects: [39-05, gui-hydrate-panel, cli-hydrate-generation]

# Tech tracking
tech-stack:
  added: []
  patterns: [cage_type_map-driven guest routing, water-only lattice skip]

key-files:
  created: []
  modified:
    - quickice/structure_generation/hydrate_generator.py

key-decisions:
  - "Numeric lattice module names (16, 17) loaded via safe_import at runtime, not pre-imported"
  - "Filled ices use only cage_type_map['small'] ('Ne1') — no 'large' key prevents double-placement"
  - "parse_guest used for ALL guest placement (spot_guests crashes with IndexError for filled ices)"

patterns-established:
  - "cage_type_map lookup: HYDRATE_LATTICES[lt]['cage_type_map'] drives guest routing, replacing hardcoded 12/14/16"
  - "is_water_only flag: HYDRATE_LATTICES[lt]['is_water_only'] controls guest skipping in generator and report"

# Metrics
duration: 4min
completed: 2026-06-29
---

# Phase 39 Plan 02: Hydrate Generator Rewrite Summary

**cage_type_map-driven parse_guest routing for all 10 lattice types, replacing hardcoded 12/14/16 cage type logic**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-29T14:36:25Z
- **Completed:** 2026-06-29T14:41:16Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Extended _LATTICE_MODULES to 10 entries and _ensure_genice_import to pre-load 8 named modules (5 new + 3 existing)
- Rewrote _run_via_api guest placement to use cage_type_map from HYDRATE_LATTICES instead of hardcoded 12/14/16 cage type logic
- Water-only lattices (sTprime, 17) correctly skip guest placement and report "Water-only lattice"
- Filled ices (c0te, c1te, c2te, ice1hte) use parse_guest('Ne1=ch4') — no double-placement because cage_type_map has only "small" key
- Ice XVI (16) uses 12/16 cage types (same as sII), correctly handled by cage_type_map
- All 1121 existing tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend _LATTICE_MODULES and _ensure_genice_import for 7 new lattice modules** - `78d0931` (feat)
2. **Task 2: Rewrite _run_via_api cage routing with cage_type_map + water-only handling** - `aca3b99` (feat)

## Files Created/Modified
- `quickice/structure_generation/hydrate_generator.py` - Extended lattice module loading and cage_type_map-driven guest routing

## Decisions Made
- Numeric lattice module names (16, 17) loaded via safe_import at runtime since Python forbids `from X import 16` — consistent with existing safe_import pattern in _run_via_api
- Filled ices have only "small" key in cage_type_map (value "Ne1"), so large_occ is naturally ignored — prevents double-placement to same cage type
- parse_guest used for ALL guest placement (not spot_guests) because spot_guests crashes with IndexError for filled ices that use Ne1 cage type

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Hydrate generator now supports all 10 lattice types with dynamic cage routing
- Ready for 39-05-PLAN.md (any remaining phase 39 plans)
- Downstream consumers (GUI hydrate panel, CLI) already updated in 39-03/39-04

---
*Phase: 39-extended-lattice-types*
*Completed: 2026-06-29*
