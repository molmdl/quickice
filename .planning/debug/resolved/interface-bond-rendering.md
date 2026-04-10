---
status: verifying
trigger: "interface-bond-rendering"
created: 2026-04-10T00:00:00Z
updated: 2026-04-10T00:10:00Z
---

## Current Focus

hypothesis: CONFIRMED - Atom names array is incorrectly trimmed when water molecules are removed
test: All tests pass including new test_atom_names_filtering.py
expecting: Fix verified - bonds now correctly connect atoms within same molecule
next_action: Final verification by updating debug file

## Symptoms

expected: Normal cylindrical bonds connecting only atoms within the same molecule
actual: Long bonds connecting different atoms (not within same molecule), especially around liquid-solid interface. Not all molecules affected.
errors: No explicit errors, just visual artifact in 3D viewer
reproduction: Open Interface tab, generate any interface structure, observe bonds in 3D viewer
started: Not sure when it started, may have always been like this

## Eliminated

## Evidence

- timestamp: 2026-04-10T00:01:00
  checked: quickice/gui/interface_viewer.py, quickice/gui/molecular_viewer.py
  found: Bond extraction uses VTK molecule bonds, created by interface_to_vtk_molecules()
  implication: Bug is in bond creation, not rendering

- timestamp: 2026-04-10T00:02:00
  checked: quickice/gui/vtk_utils.py - interface_to_vtk_molecules()
  found: Bond creation uses indices from ice_indices/water_indices lists, which track atom positions after MW filtering
  implication: Indices should be correct IF atom_names matches positions

- timestamp: 2026-04-10T00:03:00
  checked: quickice/structure_generation/modes/piece.py, pocket.py, slab.py
  found: When water molecules are removed, positions are filtered by remove_overlapping_molecules() but atom_names is trimmed with slicing [:water_nmolecules * 4]
  implication: CRITICAL BUG - slicing takes first N molecules, but removal can be at ANY position

- timestamp: 2026-04-10T00:04:00
  checked: quickice/structure_generation/overlap_resolver.py
  found: remove_overlapping_molecules uses boolean mask: keep_mask[mol_idx] = False for removed molecules, then applies mask to positions
  implication: Positions are correctly filtered, but atom_names must use same mask

- timestamp: 2026-04-10T00:05:00
  checked: All three mode files (slab.py:145, pocket.py:144,167, piece.py:128)
  found: All have the same bug: water_atom_names = water_atom_names[:water_nmolecules * 4] instead of proper filtering
  implication: Bug affects all interface modes that remove overlapping water molecules

- timestamp: 2026-04-10T00:10:00
  checked: tests/test_atom_names_filtering.py
  found: All 9 tests pass, including test demonstrating the bug vs correct behavior
  implication: Fix verified - filter_atom_names correctly removes atom names matching positions

## Resolution

root_cause: When water molecules overlapping with ice are removed, the positions array is correctly filtered using a molecule-level mask, but the atom_names list was incorrectly sliced to take the first N molecules instead of applying the same mask. This caused bond indices to point to wrong atoms, creating bonds between atoms from different molecules.
fix: Added filter_atom_names() function in overlap_resolver.py to properly filter atom_names with the same mask used for positions. Updated slab.py, pocket.py, and piece.py to use this function instead of slicing.
verification: All 9 new tests pass. All 261 existing tests pass (6 pre-existing CLI failures unrelated to this fix).
files_changed:
  - quickice/structure_generation/overlap_resolver.py: Added filter_atom_names() function
  - quickice/structure_generation/modes/slab.py: Use filter_atom_names instead of slicing
  - quickice/structure_generation/modes/pocket.py: Use filter_atom_names instead of slicing (2 locations)
  - quickice/structure_generation/modes/piece.py: Use filter_atom_names instead of slicing
  - tests/test_atom_names_filtering.py: New test file for verification
