---
status: resolved
trigger: "interface-viewer-molecule-ordering-broken"
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:02:00Z
---

## Current Focus
hypothesis: CONFIRMED - The interface_to_vtk_molecules() function uses OLD molecule ordering (ice → guest → water) but the actual structure now uses NEW ordering (ice → water → guest)
test: Fix boundary calculations in vtk_utils.py lines 480-488
expecting: After fix, water atoms will be correctly identified and viewer will display without errors
next_action: Update boundary calculations to use NEW ordering (ice → water → guest)

## Symptoms
expected: Interface 3D viewer should display the structure without errors

actual: 
- Error: "ValueError: Invalid water atom ordering for molecule 118: expected ['OW', 'HW1', 'HW2', 'MW'], got ['O', 'CA', 'CA', 'CB']"
- Interface generation completes but nothing displayed in viewer
- The atoms ['O', 'CA', 'CA', 'CB'] are THF guest atoms, not water atoms

errors: ValueError in vtk_utils.py line 637

reproduction:
- Generate THF sII hydrate
- Export to interface tab
- Viewer crashes with molecule ordering error

timeline: Immediate regression after commit 90afe86 (molecule ordering fix)

## Eliminated

## Evidence
- timestamp: initial
  checked: Error traceback and commit message
  found: Commit 90afe86 changed ordering from ice→guest→water to ice→water→guest for GROMACS compliance
  implication: vtk_utils.py likely still uses old ordering assumptions

- timestamp: initial
  checked: Error message location (line 637)
  found: water_start_in_full calculation at line 634 is checking atoms that are actually guest atoms
  implication: water_start boundary is incorrectly calculated, pointing to guest atoms instead of actual water atoms

- timestamp: investigation
  checked: vtk_utils.py lines 480-488 (boundary calculations)
  found: 
    OLD code: guest_start = ice_end, guest_end = ice_end + guest_atom_count, water_start = guest_end
    This assumes ice → guest → water ordering
  implication: Water atoms are being identified as guest atoms, and guest atoms are being checked for water atom ordering

- timestamp: investigation
  checked: slab.py commit diff (90afe86)
  found: Position concatenation changed from ice→guest→water to ice→water→guest
  implication: Confirms NEW ordering is ice → water → guest

- timestamp: investigation
  checked: InterfaceStructure class and fields
  found: Has water_atom_count field (line 255), ice_atom_count, guest_atom_count all available
  implication: Can use these fields to calculate correct boundaries

## Resolution
root_cause: vtk_utils.py interface_to_vtk_molecules() function (lines 480-488) uses OLD molecule ordering (ice → guest → water), but slab.py now produces NEW ordering (ice → water → guest) since commit 90afe86. This causes the function to treat guest atoms as water atoms when validating water molecule atom ordering.

Additionally, piece.py and pocket.py also used the old ordering, causing inconsistency across all interface modes.

fix: Updated boundary calculations in vtk_utils.py to use NEW ordering:
- OLD: ice [0:ice_atom_count], guest [ice_atom_count:ice_atom_count+guest_atom_count], water [rest]
- NEW: ice [0:ice_atom_count], water [ice_atom_count:ice_atom_count+water_atom_count], guest [rest]

Also updated piece.py and pocket.py to use the same NEW ordering for consistency.

Updated InterfaceStructure docstring and all comments to reflect new ordering.

verification: Created mock InterfaceStructure with ice → water → guest ordering and verified:
- Boundary calculations produce correct indices: ice_end=12, water_end=20, guest_end=24
- VTK conversion succeeds without "Invalid water atom ordering" error
- Correct atom counts: Ice=12, Water=6 (MW skipped), Guest=4

files_changed:
- quickice/gui/vtk_utils.py: Fixed boundary calculations (lines 480-489) and updated comments
- quickice/structure_generation/types.py: Updated InterfaceStructure docstring
- quickice/structure_generation/modes/piece.py: Updated position concatenation order
- quickice/structure_generation/modes/pocket.py: Updated position concatenation order
