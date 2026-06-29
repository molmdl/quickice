---
phase: 39-extended-lattice-types
plan: 04
subsystem: ui
tags: [PySide6, hydrate-panel, water-only, filled-ice, lattice-combo, guest-occupancy]

# Dependency graph
requires:
  - phase: 39-01
    provides: HYDRATE_LATTICES with 10 entries including is_water_only and cage_type_map
provides:
  - Dynamic guest/occupancy UI toggling for water-only lattices in HydratePanel
  - Updated info display for filled ice single-cage and water-only empty-cage structures
  - Expanded HelpIcon documentation for all 10 lattice types
affects: [hydrate-gui, lattice-selection, export-gui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "is_water_only flag check: HYDRATE_LATTICES[lattice_id]['is_water_only'] → UI enable/disable"
    - "_on_lattice_changed → _update_guest_ui_for_lattice signal chain for dynamic control toggling"

key-files:
  created: []
  modified:
    - quickice/gui/hydrate_panel.py

key-decisions:
  - "Water-only lattices disable ALL guest controls (combo + both occupancy spinners)"
  - "Filled ices (single cage_type_map key) disable large occupancy spinner only"
  - "get_configuration unchanged — returns valid HydrateConfig with default ch4 even when disabled"

patterns-established:
  - "Lattice-driven UI toggling: _update_guest_ui_for_lattice() called at init and on lattice change"
  - "Info display conditional: water-only shows 'No cages' message, others show cage type list"

# Metrics
duration: 28min
completed: 2026-06-29
---

# Phase 39 Plan 04: GUI Hydrate Panel Water-Only Toggling Summary

**Dynamic guest/occupancy UI toggling for water-only lattices with expanded HelpIcon docs and conditional info display**

## Performance

- **Duration:** 28 min
- **Started:** 2026-06-29T13:47:30Z
- **Completed:** 2026-06-29T14:16:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added `_update_guest_ui_for_lattice()` method that disables guest combo and occupancy spinners for water-only lattices (sTprime, Ice XVII) and disables large occupancy for single-cage-type filled ices
- Updated lattice info display to show "No cages — water-only structure" for water-only lattices instead of empty cage list
- Expanded HelpIcon text to document all 10 lattice types including filled ices and water-only lattices

## Task Commits

Each task was committed atomically:

1. **Task 1: Auto-populate lattice combo + disable guest/occupancy for water-only lattices** - `7e33d29` (feat)
2. **Task 2: Update lattice info display for filled ice and water-only lattice structures** - `c81919b` (feat)

## Files Created/Modified
- `quickice/gui/hydrate_panel.py` - Water-only guest/occupancy toggling, expanded HelpIcon docs, conditional info display

## Decisions Made
- Water-only lattices disable ALL guest controls (combo + both occupancy spinners) since no cages exist for guest placement
- Filled ices with single cage_type_map key only disable the large occupancy spinner; small occupancy remains enabled as it maps to the single cage type
- `get_configuration()` is unchanged — it still returns a valid `HydrateConfig` with default ch4 guest_type that gets ignored by the generator for water-only lattices

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- GUI hydrate panel fully supports all 10 lattice types with correct UI toggling
- Ready for 39-05-PLAN.md (next plan in phase)
- No blockers or concerns

---
*Phase: 39-extended-lattice-types*
*Completed: 2026-06-29*
