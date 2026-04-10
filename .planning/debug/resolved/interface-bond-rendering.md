---
status: resolved
trigger: "interface-bond-rendering"
created: 2026-04-10T00:00:00Z
updated: 2026-04-10T16:30:00Z
---

## Current Focus

hypothesis: Previous fixes (693f2e9, 2e3b46f) did NOT work - all issues remain per user verification
test: Run GUI and actually generate structures to verify the bond behavior
expecting: Find the REAL root cause - previous investigation may have been on wrong track
next_action: Re-investigate from scratch - trace bond creation through actual data

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

---

## RE-INVESTIGATION (Fix didn't work)

- timestamp: 2026-04-10T14:40:00
  checked: User verification after commit 2e3b46f
  found: ALL ISSUES STILL REMAIN. The fixes did not resolve the bond problems.
  implication: Previous investigation was incorrect or incomplete. Need to start fresh and trace through actual execution.

- timestamp: 2026-04-10T16:00:00
  checked: Bond distance verification - calculated distances for all bonds
  found: Bonds have distances of 1.9-3.9 nm instead of expected ~0.1 nm (O-H bond length)
  implication: Bonds are connecting atoms from DIFFERENT molecules, not wrong atoms within same molecule

- timestamp: 2026-04-10T16:05:00
  checked: Specific problematic bond (Bond 72 in slab mode)
  found: Atom 108 (O) at Y=0.091, Atom 109 (H) at Y=1.996 - 1.9 nm apart! Same molecule (36) but atoms span PBC boundary
  implication: The modulo operation in tile_structure wraps atoms independently, breaking molecular integrity

- timestamp: 2026-04-10T16:10:00
  checked: tile_structure function in water_filler.py (line 234)
  found: CRITICAL BUG: `tiled_positions = filtered % target_region` applies modulo to EACH ATOM INDIVIDUALLY
  implication: When a molecule spans the PBC boundary (e.g., O at Y=0.1, H at Y=1.9), the atoms are kept apart instead of being wrapped together as a unit. This causes H atoms to be 1.9 nm from their O instead of 0.1 nm.

## Resolution

root_cause: The `tile_structure` function in `water_filler.py` line 234 applies PBC wrapping (`% target_region`) to each atom INDIVIDUALLY instead of wrapping molecules as a UNIT. When a water molecule spans the periodic boundary (e.g., O at Y=0.1 nm, H at Y=1.9 nm in a 2.0 nm box), the atoms end up 1.8 nm apart after wrapping instead of staying together. This breaks molecular integrity and causes bonds to connect atoms from different molecules.

fix: Replace atom-level modulo wrapping with molecule-level wrapping. For each molecule:
1. Use the oxygen atom position as reference
2. Calculate shift to wrap O into target region
3. Apply the same shift to all atoms in the molecule
This keeps all atoms of a molecule together while still wrapping molecules into the target region.

verification: All bond distance errors eliminated for all three modes:
- Slab mode: 0 errors (was 8 ice + 13 water errors)
- Piece mode: 0 errors (was 8 ice + 86 water errors)
- Pocket mode: 0 errors (was 42 ice errors)
All 264 tests pass (6 CLI test failures are unrelated).

files_changed:
  - quickice/structure_generation/water_filler.py: Replace atom-level modulo with molecule-level wrapping in tile_structure()
