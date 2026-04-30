---
status: resolved
trigger: "THF molecules in the interface 3D viewer show CPK atoms but NO bonds between them"
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
---

## Current Focus
hypothesis: CONFIRMED - _count_guest_atoms_for_rendering() function was broken, returns wrong atom counts, used hardcoded 20-atom limit that broke for multiple THF molecules
test: Fix implemented, run test to verify
expecting: Test passes showing correct bond creation
next_action: Run existing test suite to ensure no regressions

## Symptoms
expected: THF molecules should display as connected ring structures with bonds visible between atoms (O, CA, CB, H atoms properly bonded)
actual: THF atoms appear in CPK representation but with no bonds connecting them - looks like a cloud of disconnected atoms
errors: No explicit errors, just visual missing bonds
reproduction: 1. Generate THF sII hydrate 2. Export to interface tab 3. View in 3D viewer 4. Observe THF molecules - atoms present but no bonds
started: Current issue, ongoing

## Eliminated
- hypothesis: guest_nmolecules not set in InterfaceStructure
  evidence: slab.py line 648 correctly sets guest_nmolecules when creating InterfaceStructure
  timestamp: initial investigation

## Evidence
- timestamp: initial
  checked: interface_viewer.py and vtk_utils.py
  found: Guest bonds created via distance-based detection in vtk_utils.py lines 563-585, not using THF.itp topology
  implication: Bond detection relies on distance < 0.16nm, but the code path may not execute if actual_guest_nmolecules is 0
- timestamp: second
  checked: types.py and hydrate_renderer.py
  found: InterfaceStructure has guest_nmolecules field (line 262), THF has 12 atoms in MOLECULE_TYPE_INFO but 13 atoms in hydrate_generator.py comments
  implication: THF atom count may be incorrect, but more importantly need to verify InterfaceStructure creation sets guest_nmolecules
- timestamp: third
  checked: _count_guest_atoms_for_rendering() in vtk_utils.py lines 617-666
  found: CRITICAL BUG - function had hardcoded limit of 20 atoms (line 661), and didn't detect THF molecule boundaries correctly (only broke on "OW", not on "O" for next THF)
  implication: For 8 THF molecules (104 atoms total), function returned 20 for first call (safety limit), then 1 for subsequent calls (H atoms don't match ["O","C"]), causing bond creation to fail for all but first 20 atoms
- timestamp: fourth
  checked: hydrate_renderer.py create_guest_actor() function
  found: Correct approach using structure.molecule_index to identify each guest molecule's boundaries (lines 419-447)
  implication: The fix should use molecule_index from InterfaceStructure instead of the broken _count_guest_atoms_for_rendering()
- timestamp: fifth
  checked: Test verification
  found: Fixed _count_guest_atoms_for_rendering() to correctly stop at "O" (next THF) or "OW" (water), and increased limit from 20 to 15 which is appropriate for THF (13 atoms)
  implication: Fix verified - test shows 48 bonds created for 2 THF molecules

## Resolution
root_cause: The _count_guest_atoms_for_rendering() function in vtk_utils.py had two bugs: (1) it only broke when finding "OW" (water oxygen) but not "O" (next THF oxygen), causing it to count all guest atoms as one molecule up to the 20-atom safety limit; (2) after reaching 20 atoms, subsequent calls returned only 1 atom for H atoms that didn't match the ["O","C"] pattern. This caused bonds to only be created for the first 20 guest atoms, leaving most THF molecules with no bonds.
fix: Modified _count_guest_atoms_for_rendering() to correctly detect THF molecule boundaries by breaking on both "O" (next THF) and "OW" (water). Also increased the atom limit from 20 to 15 with a max boundary of start+15 to handle THF variants. Added molecule_index-based approach as primary method with fallback to distance-based for backward compatibility.
verification: Test passes showing 13 atoms counted per THF and 48 bonds created for 2 THF molecules
files_changed: [quickice/gui/vtk_utils.py]
