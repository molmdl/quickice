---
status: resolved
trigger: "ion-custom-mol-freeze"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
---

## Current Focus
hypothesis: CONFIRMED - _remove_overlapping_water has bug in molecule_index calculation: uses ice_atom_count // 3 to count ice molecules, but should use ice_nmolecules from structure. This causes molecule_index to have wrong number of ice entries, shifting all water molecule indices and causing ion_inserter to fail when accessing water positions
test: Check if InterfaceStructure has ice_nmolecules attribute and use it to calculate correct molecule count
expecting: InterfaceStructure has ice_nmolecules (confirmed from types.py line 263). Fix: replace ice_atom_count // 3 with structure.ice_nmolecules
next_action: Fix the bug in custom_molecule_inserter.py lines 409 and 588 (same bug appears twice)

## Symptoms

expected: Ion insertion should complete after custom molecule insertion
actual: Application freezes when clicking generate in ion tab after custom molecule random mode insertion
errors: No error message, just freeze/hang
reproduction: 
  1. Load interface structure
  2. Insert custom molecules using random mode
  3. Switch to ion tab
  4. Select "Custom Molecule" as source
  5. Click generate
  6. Application freezes
started: Current issue after recent water replacement fix
previous_fix: Added water removal to CustomMoleculeInserter, enabled custom molecule source for ion insertion

## Eliminated

## Evidence

- timestamp: 2026-05-09T00:00:00Z
  checked: custom_molecule_inserter.py lines 404-433 (_remove_overlapping_water molecule_index building)
  found: BUG - Line 409: ice_mol_count = ice_atom_count // 3 (assumes 3 atoms per ice molecule) BUT Line 412: molecule_index.append(MoleculeIndex(current_idx, current_idx + 4, "ice")) (uses 4 atoms per ice molecule). This is INCONSISTENT.
  implication: Molecule index misalignment causes water molecule boundaries to be wrong. When ion_inserter tries to extract water molecules, it gets incorrect positions, potentially causing freeze or infinite loop in overlap checking

- timestamp: 2026-05-09T00:00:00Z
  checked: IonInserter._build_molecule_index_from_structure (ion_inserter.py lines 60-134)
  found: Method builds molecule_index from ice_nmolecules, water_nmolecules, guest_nmolecules. Uses ice_atom_count and water_atom_count to determine atoms per molecule
  implication: If molecule_index is already present (from _remove_overlapping_water), it uses that directly. If the molecule_index is wrong, water molecule extraction fails

- timestamp: 2026-05-09T00:00:00Z
  checked: InterfaceStructure docstring (types.py lines 244-250)
  found: Ice candidates from GenIce use 3 atoms per molecule (O, H, H). Hydrate ice uses 4 atoms per molecule (OW, HW1, HW2, MW). Water uses 4 atoms per molecule (TIP4P).
  implication: Ice can have either 3 or 4 atoms per molecule depending on source. Cannot assume ice_atom_count // 3

- timestamp: 2026-05-09T00:00:00Z
  checked: _remove_overlapping_water molecule_index calculation (custom_molecule_inserter.py lines 408-414)
  found: Line 409: ice_mol_count = ice_atom_count // 3 (WRONG - assumes 3 atoms per molecule). Line 412: MoleculeIndex(current_idx, current_idx + 4, "ice") (WRONG - count parameter gets current_idx + 4 instead of just 4). This creates ice_mol_count indices with wrong count, causing molecule_index to have incorrect boundaries.
  implication: CRITICAL BUG - Multiple issues: (1) Using ice_atom_count // 3 assumes all ice has 3 atoms/molecule, but hydrate ice has 4. (2) MoleculeIndex count parameter is set to current_idx + 4 instead of 4. Both cause molecule_index misalignment, shifting water molecule boundaries and causing ion_inserter to fail when accessing water positions (freeze/hang)

- timestamp: 2026-05-09T00:00:00Z
  checked: MoleculeIndex usage in ion_inserter.py lines 99-106
  found: Correct pattern: ice_atoms_per_mol = ice_atom_count // ice_mols, then MoleculeIndex(start_idx=current_idx, count=ice_atoms_per_mol, mol_type="ice")
  implication: Should use keyword arguments with proper count value, and calculate atoms_per_molecule from ice_atom_count and ice_nmolecules

## Resolution

root_cause: CONFIRMED - Double bug in CustomMoleculeInserter._remove_overlapping_water, place_random, and place_custom methods: (1) Lines 409/588/730 used ice_atom_count // 3 to calculate ice molecule count, assuming all ice has 3 atoms/molecule, but hydrate ice has 4 atoms/molecule. (2) Lines 412/591/733 used MoleculeIndex(current_idx, current_idx + 4, "ice") which passed current_idx + 4 as count parameter instead of 4. This caused molecule_index to have incorrect ice molecule boundaries, shifting all water molecule indices. When ion_inserter tried to extract water molecules using this molecule_index, it accessed wrong atoms or went out of bounds, causing freeze/hang.
fix: Fixed in custom_molecule_inserter.py at three locations: (1) _remove_overlapping_water lines 408-420, (2) place_random lines 586-600, (3) place_custom lines 728-742. Changed ice_mol_count calculation to use structure.ice_nmolecules instead of ice_atom_count // 3. Changed MoleculeIndex construction to use keyword arguments with proper count value: MoleculeIndex(start_idx=current_idx, count=ice_atoms_per_mol, mol_type="ice"). Follows pattern from ion_inserter.py lines 99-106.
verification: Created test_ion_custom_freeze_fix.py that reproduces the exact bug scenario. Test creates interface with 10 ice molecules (40 atoms, 4 atoms per molecule - hydrate ice), inserts 5 custom molecules in random mode, then inserts ions. Test verifies: (1) molecule_index is correctly built with proper ice molecule count, (2) water molecule indices start at correct position after ice, (3) ion insertion completes without freeze/hang. Test PASSED.
files_changed: [/share/home/nglokwan/quickice/quickice/structure_generation/custom_molecule_inserter.py]
