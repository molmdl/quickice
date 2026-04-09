---
status: resolved
trigger: "bonds-pbc-wrapping"
created: 2026-04-09T22:17:00
updated: 2026-04-09T22:45:00
---

## Current Focus
hypothesis: CONFIRMED - Bonds use raw atom positions without PBC wrapping
test: Verified in vtk_utils.py and interface_viewer.py
expecting: Found _pbc_distance() exists but only for H-bond detection
next_action: COMPLETE - Fix verified with tests

## Symptoms
expected: Bonds should be wrapped correctly within periodic boundaries
actual: Bonds are drawn connecting atoms across box boundaries, creating long lines through the box
errors: Visual mess - bonds stretch across entire box when atoms are near boundaries
reproduction: View any structure with molecules near box edges
started: Always showed bonds without PBC wrapping

## Eliminated

## Evidence
- timestamp: 2026-04-09T22:17:30
  checked: vtk_utils.py candidate_to_vtk_molecule()
  found: Atoms added with raw positions (line 60), bonds created with AppendBond (lines 97-98)
  implication: No PBC wrapping applied during molecule creation
- timestamp: 2026-04-09T22:17:45
  checked: vtk_utils.py _pbc_distance()
  found: PBC distance calculation exists (lines 127-148)
  implication: PBC logic exists but only used for H-bond detection, NOT bond rendering
- timestamp: 2026-04-09T22:18:00
  checked: interface_viewer.py _extract_bonds()
  found: Extracts raw positions from vtkMolecule (lines 197-229)
  implication: Bond positions extracted without PBC wrapping
- timestamp: 2026-04-09T22:40:00
  checked: molecular_viewer.py
  found: Uses vtkMoleculeMapper with RenderBondsOn(), VTK controls bond rendering
  implication: Need to disable VTK bonds and use custom line actors with PBC wrapping

## Resolution
root_cause: Bonds were rendered using raw atom positions without applying minimum image convention (PBC wrapping). When atoms are on opposite sides of PBC boundary, the bond was drawn across the entire box instead of being wrapped to show the shortest distance.

fix: 
1. interface_viewer.py: Modified _extract_bonds() to accept cell matrix and apply minimum image convention when extracting bond positions
2. molecular_viewer.py: 
   - Added numpy import and bond constants (BOND_COLOR, BOND_LINE_WIDTH)
   - Added _bond_actor attribute
   - Modified _setup_molecule_actor() to disable VTK bond rendering (RenderBondsOff())
   - Added _extract_bonds() method with PBC wrapping
   - Modified set_candidate() to create custom bond line actors with PBC wrapping
   - Modified clear() to remove bond actor
3. vtk_utils.py: Added create_bond_lines_actor import to molecular_viewer

verification: 
- Created test_pbc_bond_wrapping.py with 4 tests verifying PBC wrapping
- All 4 tests pass
- Existing tests pass (254 passed, 7 pre-existing CLI failures unrelated)

files_changed:
- quickice/gui/interface_viewer.py
- quickice/gui/molecular_viewer.py
