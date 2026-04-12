---
phase: 23-water-density-from-t-p
plan: 02
subsystem: density
tags: [iapws, water-density, interface-generation, gui, scaling]

# Dependency graph
requires:
  - phase: 23-01
    provides: IAPWS95 water density module (water_density_gcm3)
provides:
  - Water density scaling for interface generation
  - Water density display in Tab 1 info panel
  - target_density parameter in fill_region_with_water
affects:
  - All interface generation modes (slab, pocket, piece)
  - GUI info panel display

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Density scaling via cube root formula: scale = (template_density / target_density)^(1/3)"
    - "Lazy import pattern for water density in GUI"

key-files:
  created: []
  modified:
    - quickice/structure_generation/water_filler.py
    - quickice/structure_generation/modes/slab.py
    - quickice/structure_generation/modes/pocket.py
    - quickice/structure_generation/modes/piece.py
    - quickice/gui/main_window.py

key-decisions:
  - "Scale positions BEFORE tiling (positions in nm, scaling preserves molecular geometry)"
  - "Scale box_dims by same factor so tiling works correctly"
  - "Lazy import of water_density_gcm3 only when Liquid phase is displayed"
  - "4 decimal place formatting for consistency with Ice Ih density display"

patterns-established:
  - "Pattern: Density scaling for water molecule spacing in interfaces"
  - "Pattern: IAPWS-95 water density calculation for supercooled water"

# Metrics
duration: ~5 min
completed: 2026-04-12
---

# Phase 23 Plan 02: Water Density Integration Summary

**Water density scaling for interface generation and GUI display using IAPWS-95**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-12T03:21:23Z
- **Completed:** 2026-04-12T03:26:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Added `TEMPLATE_DENSITY_GCM3 = 0.991` constant to water_filler.py
- Created `scale_positions_for_density()` function with cube root formula
- Modified `fill_region_with_water()` to accept optional `target_density` parameter
- Updated all three interface modes (slab, pocket, piece) to use IAPWS-95 water density
- Added water density display for Liquid phase in Tab 1 info panel

## Task Commits

Each task was committed atomically:

1. **Task 1: Add target_density parameter to water_filler.py** - `52c1206` (feat)
2. **Task 2: Update interface modes to use water density** - `223d46f` (feat)
3. **Task 3: Display water density in Tab 1 info panel** - `daaaab6` (feat)

**Plan metadata:** Pending commit

## Files Created/Modified

- `quickice/structure_generation/water_filler.py` - Added TEMPLATE_DENSITY_GCM3 constant, scale_positions_for_density function, target_density parameter
- `quickice/structure_generation/modes/slab.py` - Added water density calculation and target_density parameter
- `quickice/structure_generation/modes/pocket.py` - Added water density calculation and target_density parameter
- `quickice/structure_generation/modes/piece.py` - Added water density calculation and target_density parameter
- `quickice/gui/main_window.py` - Added Liquid phase water density display

## Decisions Made

- **Scale positions BEFORE tiling**: Positions are in nm, and scaling preserves molecular geometry by uniformly expanding/contracting the unit cell
- **Scale box_dims by same factor**: This ensures tiling works correctly with the scaled positions
- **Cube root formula**: `scale = (template_density / target_density)^(1/3)` is the correct 3D scaling relationship
- **Lazy import pattern**: water_density_gcm3 is only imported when Liquid phase is displayed, matching the Ice Ih pattern
- **4 decimal formatting**: Consistent with Ice Ih density display for UI consistency

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tests pass and verification checks succeed.

## User Setup Required

None - no external service configuration required. The iapws library is already in environment.yml.

## Next Phase Readiness

- Phase 23 complete (2/2 plans)
- Water density now calculated and displayed for Liquid phase
- Interface generation uses correct water molecule spacing based on IAPWS-95
- Ready for Phase 24: Triclinic Transformation Service

---
*Phase: 23-water-density-from-t-p*
*Completed: 2026-04-12*
