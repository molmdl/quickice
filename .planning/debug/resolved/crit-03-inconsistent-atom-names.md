---
status: resolved
trigger: "CRIT-03 inconsistent-atom-names - Inconsistent Atom Name Handling Between Ice and Water (vtk_utils.py:277-360)"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:04:00Z
---

## Current Focus

hypothesis: N/A
test: N/A
expecting: N/A
next_action: Archive resolved session

## Symptoms

expected: Atoms should be correctly identified as ice or water based on atom names and indices
actual: Check i < iface.ice_atom_count to determine ice vs water, but this may not account for MW virtual sites correctly
errors: Atoms could be assigned to wrong phase, causing incorrect visualization
reproduction: Visualize interface structure in VTK viewer, check if ice/water atoms are colored/represented correctly
started: Always been potentially wrong since VTK interface visualization was implemented

## Eliminated

## Evidence

- timestamp: 2026-04-09T00:01:00Z
  checked: vtk_utils.py lines 277-360 (interface_to_vtk_molecules function)
  found: Code order: (1) get atomic_num, (2) if MW (None) continue, (3) check boundary
  implication: MW atoms are skipped BEFORE boundary check, contradicting comments

- timestamp: 2026-04-09T00:01:00Z
  checked: vtk_utils.py line 297-298 docstring and line 326-327 inline comment
  found: Comments claim "ice_atom_count includes ALL atoms including MW" and "boundary check must happen BEFORE skipping MW"
  implication: Both comments are FACTUALLY WRONG - ice_atom_count does NOT include MW (ice has no MW)

- timestamp: 2026-04-09T00:01:00Z
  checked: slab.py line 77 - ice atom names generation
  found: ice_atom_names = ["O", "H", "H"] * total_ice_nmolecules
  implication: Ice has NO MW atoms - only O, H, H pattern

- timestamp: 2026-04-09T00:01:00Z
  checked: slab.py line 132, pocket.py line 163, piece.py line 129
  found: ice_atom_count = len(ice_positions) where ice_positions have 3 atoms per molecule
  implication: ice_atom_count = ice_nmolecules * 3 (no MW in ice)

- timestamp: 2026-04-09T00:01:00Z
  checked: Atom ordering in InterfaceStructure
  found: Ice atoms first (indices 0 to ice_atom_count-1), water atoms second (indices ice_atom_count to total-1)
  implication: Boundary check i < ice_atom_count correctly identifies ice vs water

- timestamp: 2026-04-09T00:01:00Z
  checked: MW atom locations in iteration
  found: MW atoms only exist in water, at indices >= ice_atom_count
  implication: When MW is skipped with continue, it's always in the water region - no misclassification possible

## Resolution

root_cause: MISLEADING COMMENTS, NOT A LOGIC BUG. The comments in interface_to_vtk_molecules claim that (1) ice_atom_count includes MW atoms, and (2) the boundary check happens before skipping MW. Both claims are factually wrong. ice_atom_count = ice_nmolecules * 3 (ice has NO MW), and MW atoms are skipped with 'continue' BEFORE reaching the boundary check. However, the LOGIC is actually correct because: (1) ice atoms occupy indices 0 to ice_atom_count-1, (2) MW atoms only exist in water at indices >= ice_atom_count, (3) skipping MW before the boundary check is safe because MW atoms are never in the ice region.
fix: Corrected misleading docstring (lines 295-302) and inline comment (lines 326-329) to accurately describe the atom ordering and boundary check logic
verification: Ran quick sanity check verifying atom classification logic works correctly. Ice atoms (O, H, H) at indices 0-2 correctly identified as ice. Water atoms (OW, HW1, HW2) at indices 3-5 correctly identified as water. MW at index 6 correctly skipped. Pre-existing test failures (CLI integration, structure generation) are unrelated to this comment fix.
files_changed: [quickice/gui/vtk_utils.py]
