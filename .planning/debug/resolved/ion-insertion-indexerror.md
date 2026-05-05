---
status: resolved
trigger: "IndexError when inserting ions after solute insertion - index 46080 out of bounds for size 46080"
created: 2026-05-05T00:00:00Z
updated: 2026-05-05T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - In solute_inserter._remove_overlapping_water(), when creating new InterfaceStructure after removing water molecules, the molecule_index is copied from the original structure without updating the indices. This causes molecule_index to reference atom positions that no longer exist in the reduced positions array.
test: Verify molecule_index structure and implement fix to update indices when water is removed
expecting: After fix, molecule_index.start_idx values should be recalculated to match the new positions array
next_action: Understand molecule_index format and implement fix in _remove_overlapping_water

## Symptoms

expected: Should be able to insert ions after solute insertion without errors
actual: Error when inserting ions after re-adding solute: IndexError: index 46080 is out of bounds for axis 0 with size 46080
errors: IndexError: index 46080 is out of bounds for axis 0 with size 46080
reproduction: 
1. Insert solute
2. Go to ion tab
3. Try to insert ions
4. Get IndexError
started: Just discovered

## Eliminated

## Evidence

- timestamp: 2026-05-05T00:00:00Z
  checked: Error message analysis
  found: Array size is 46080, trying to access index 46080 (off-by-one error where index equals size)
  implication: The index is out of bounds by exactly 1, suggesting indices weren't updated after array was reduced

- timestamp: 2026-05-05T00:00:00Z
  checked: ion_inserter.py line 304 context
  found: Line 304 accesses structure.positions[atom_idx] where atom_idx comes from structure.molecule_index (mol.start_idx and mol.count). The function uses the ORIGINAL structure's molecule_index and positions for overlap checking.
  implication: The input structure passed to ion_inserter has inconsistent molecule_index vs positions array

- timestamp: 2026-05-05T00:00:00Z
  checked: main_window.py _on_insert_ions function
  found: When source is "Solute", the code passes `self._current_solute_result.interface_structure` to insert_ions(). This is the interface_structure from SoluteStructure.
  implication: The SoluteStructure.interface_structure likely has molecule_index that doesn't match its positions array after water removal

- timestamp: 2026-05-05T00:00:00Z
  checked: solute_inserter.py _remove_overlapping_water method
  found: At line 471, when creating new InterfaceStructure after removing water molecules, the code sets `molecule_index=structure.molecule_index` - copying the OLD molecule_index from the original structure. The positions array is reduced (water atoms removed) but molecule_index still has the old indices.
  implication: CONFIRMED ROOT CAUSE - molecule_index contains indices that point beyond the new reduced positions array. When ion_inserter uses these indices to access positions, it gets IndexError.

## Resolution

root_cause: In solute_inserter._remove_overlapping_water(), when creating a new InterfaceStructure after removing water molecules, the molecule_index was copied from the original structure without updating the indices. The positions array was reduced, but molecule_index still contained old start_idx values that pointed beyond the new array bounds, causing IndexError when ion_inserter tried to access those positions.
fix: Rebuild molecule_index in _remove_overlapping_water() to reflect the new positions array. Ice molecule indices stay the same (they're at the start). Water molecule entries are created for kept water molecules with updated indices. Guest molecule entries are added with indices shifted to account for removed water atoms. Added check to handle case where molecule_index is empty.
verification: Created test_solute_ion_molecule_index.py with two tests: (1) test_molecule_index_after_solute_water_removal verifies molecule_index indices are valid after water removal, (2) test_ion_insertion_after_solute verifies the full workflow of inserting solute then ions without IndexError. Both tests pass. Also ran test_solute_insertion.py and test_ion_hydrate_fix.py - all pass.
files_changed: [quickice/structure_generation/solute_inserter.py, tests/test_solute_ion_molecule_index.py]
