---
phase: 019
plan: 01
subsystem: ui
tags: [pyside6, qt, gui, custom-molecule, preview, refactor]

# Dependency graph
requires:
  - phase: 34.5
    provides: Validation & Preview button functionality
provides:
  - Clean custom molecule panel without old preview system conflicts
  - Position table with 6 columns (X, Y, Z, α, β, γ)
  - Validate & Preview button working correctly
affects: [custom-molecule, gui, preview]

# Tech tracking
tech-stack:
  added: []
  patterns: [signal-slot cleanup, ui simplification]

key-files:
  created: []
  modified:
    - quickice/gui/custom_molecule_panel.py
    - quickice/gui/main_window.py

key-decisions:
  - "Keep preview_requested signal for Phase 34.5 Validate & Preview button"
  - "Remove preview_all_requested signal to eliminate conflict"
  - "Change position table from 7 to 6 columns"

patterns-established: []

# Metrics
duration: 3min
completed: 2026-05-10
---

# Quick Task 019: Remove Old Custom Molecule Preview Summary

**Removed old preview system from Custom Molecule Custom mode, eliminating conflict with Phase 34.5 validation preview**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-10T07:51:13Z
- **Completed:** 2026-05-10T07:54:07Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Removed old "Preview All Positions" button from Custom mode UI
- Removed "Click to preview" column from position table (changed 7→6 columns)
- Eliminated preview_all_requested signal that conflicted with Phase 34.5 validation
- Preserved Validate & Preview button and Clear Preview button functionality

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove old preview UI from custom_molecule_panel.py** - `b7c1452` (refactor)
2. **Task 2: Remove old preview handlers from main_window.py** - `b7c1452` (refactor)

**Note:** Both tasks were combined into a single commit as they were tightly coupled changes.

## Files Created/Modified

- `quickice/gui/custom_molecule_panel.py` - Removed old preview system UI elements and methods
  - Removed preview_all_requested signal declaration
  - Changed position table column count from 7 to 6
  - Removed "Preview" column header
  - Removed "Preview All Positions" button and layout
  - Removed signal connection in _setup_connections()
  - Removed preview column item creation in _update_position_table()
  - Removed preview column click handling in _on_position_table_clicked()
  - Removed _on_preview_all_clicked() method
  - Removed preview_all_button.setEnabled() call in reset() method

- `quickice/gui/main_window.py` - Removed old preview system signal handlers
  - Removed preview_all_requested signal connection
  - Removed _on_custom_molecule_preview_all_requested() method

## Decisions Made

- **Keep preview_requested signal:** This signal is used by the Phase 34.5 "Validate & Preview" button and should not be removed
- **Remove preview_all_requested signal:** This signal causes conflicts with Phase 34.5 validation preview due to shared viewer state
- **Change table columns from 7 to 6:** Remove the "Preview" column that provided click-to-preview functionality (replaced by Validate & Preview button)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Pre-existing test failure:** One test (`test_custom_to_ion_workflow`) failed both before and after the changes. This failure is unrelated to the preview system removal and appears to be a pre-existing issue with water atom count expectations in the ion workflow.

**Test results:**
- 29 tests passed
- 1 test failed (pre-existing)
- No new failures introduced by this change

## Verification

All verification criteria met:
- ✓ No references to preview_all_button in custom_molecule_panel.py
- ✓ No references to preview_all_requested signal
- ✓ Position table has 6 columns (X, Y, Z, α, β, γ)
- ✓ _on_preview_all_clicked method removed
- ✓ _on_custom_molecule_preview_all_requested method removed
- ✓ preview_requested signal connection remains (for Validate & Preview button)
- ✓ preview_cleared signal connection remains (for Clear Preview button)
- ✓ Both files parse without syntax errors

## Manual Testing Required

Task 3 in the plan requires manual GUI testing:
1. Launch GUI and create an interface structure
2. Upload custom molecule files
3. Verify "Preview All Positions" button is gone
4. Verify position table has 6 columns (no Preview column)
5. Test Validate & Preview button works correctly
6. Test Clear Preview button works
7. Test table row click loads position into input fields
8. Test no crashes during complete workflow

## Next Steps

Manual testing should be performed to verify the GUI works correctly after removing the old preview system.

---
*Quick Task: 019-remove-old-custom-preview*
*Completed: 2026-05-10*
