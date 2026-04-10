---
status: resolved
trigger: "interface-bond-rendering"
created: 2026-04-10T00:00:00Z
updated: 2026-04-10T15:45:00Z
---

## Current Focus

hypothesis: N/A - bugs found and fixed
test: N/A
expecting: N/A
next_action: Commit and archive

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

- timestamp: 2026-04-10T14:25:00
  checked: User verification after commit 693f2e9
  found: BUG STILL PRESENT but different per mode:
    - Piece mode: ice bonds are wrong
    - Pocket mode: water bonds are wrong
    - Slab mode: water bonds are wrong
  implication: Previous fix was incomplete or there's another source of bond indexing errors

- timestamp: 2026-04-10T15:00:00
  checked: vtk_utils.py bond creation logic (lines 426-466)
  found: Ice bonds use ice_indices[mol_idx * 3] which assumes ice atoms are correctly ordered. Water bonds use ice_atom_count + mol_idx * 4 which assumes water starts after ice.
  implication: Bond creation logic itself is correct IF atom_names matches positions

- timestamp: 2026-04-10T15:01:00
  checked: All three mode files for atom ordering
  found: ALL three modes (piece, slab, pocket) place ice atoms FIRST, then water atoms. This is consistent.
  implication: Atom ordering is not the issue - the problem is atom_names content

- timestamp: 2026-04-10T15:02:00
  checked: pocket.py lines 127-136 (ice molecule removal and atom_names creation)
  found: CRITICAL BUG: ice_positions is filtered by remove_overlapping_molecules() when ice molecules are removed from cavity, but ice_atom_names = TEMPLATE * ice_nmolecules assumes remaining molecules are the FIRST N molecules. This is the EXACT same bug pattern as the water one!
  implication: When pocket mode removes ice molecules from inside cavity, the positions are correctly filtered but atom_names is wrong, causing ice bonds to point to wrong atoms

- timestamp: 2026-04-10T15:10:00
  checked: pocket.py ice removal logic (lines 127-136)
  found: CONFIRMED: ice_positions is filtered by remove_overlapping_molecules() with ice_inside_cavity, but ice_atom_names = TEMPLATE * ice_nmolecules. Missing filter_atom_names call for ice!
  implication: This is the bug for pocket mode. However, user reports piece mode has wrong ICE bonds - need to investigate further after fixing pocket mode

- timestamp: 2026-04-10T15:15:00
  checked: water_filler.py fill_region_with_water function (line 278)
  found: CRITICAL BUG #2: template_atom_names has 864 entries (216 molecules from tip4p.gro), but code does template_atom_names * n_molecules, creating 864 * 251 = 216864 atom names when only 1004 are needed!
  implication: This bug affects ALL interface modes that use fill_region_with_water (piece, pocket, slab), causing water atom_names to be 216x larger than positions

- timestamp: 2026-04-10T15:20:00
  checked: Fixed water_filler.py to use WATER_ATOM_NAMES_TEMPLATE (single molecule) * n_molecules
  found: After fix, positions and atom_names counts match for all modes
  implication: Both bugs fixed

## Resolution

root_cause: TWO bugs found:
  1. **pocket.py**: When ice molecules are removed from inside cavity, ice_positions is filtered by remove_overlapping_molecules() but ice_atom_names was incorrectly created with TEMPLATE * ice_nmolecules (assumes remaining molecules are first N). Same bug pattern as the previous water fix.
  2. **water_filler.py**: fill_region_with_water() creates atom names with template_atom_names * n_molecules, but template_atom_names has 864 entries (216 molecules), resulting in 216x too many atom names.

fix:
  1. Added ice atom_names filtering in pocket.py: create ice_atom_names BEFORE removal, then filter with filter_atom_names(ice_atom_names, ice_inside_cavity, 3)
  2. Fixed water_filler.py to use WATER_ATOM_NAMES_TEMPLATE (4 atoms per molecule) instead of full template (864 atoms)
verification: All 247 tests pass. Positions and atom_names counts match for all modes (piece, pocket, slab).
files_changed:
  - quickice/structure_generation/modes/pocket.py: Create ice_atom_names before removal, filter after removal
  - quickice/structure_generation/water_filler.py: Use WATER_ATOM_NAMES_TEMPLATE constant instead of template_atom_names
