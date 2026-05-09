---
status: resolved
trigger: "ion-custom-mol-warning"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:10:00Z
---

## Current Focus
hypothesis: CustomMoleculeInserter has misleading comments about water replacement but doesn't actually replace water - it places molecules additively on top of existing water, making ion insertion unsafe
test: Read CustomMoleculeInserter.place_random() and place_custom() to verify actual behavior
expecting: Find that custom molecules are added without water removal
next_action: Verify water replacement logic in CustomMoleculeInserter

## Symptoms
expected: After custom molecule is generated (not just preview), the custom molecules should have replaced water molecules. Ion tab should recognize this and not show "no water replaced" warning.
actual: Ion tab shows warning about "no water replaced" for custom molecules, suggesting it thinks custom molecules were only previewed (not actually inserted with water replacement)
errors: Warning message: "no water replaced" for custom molecules
reproduction: 
  1. Load interface structure
  2. Insert custom molecules using random or custom mode (click Generate, not just Preview)
  3. Switch to ion tab
  4. Observe warning about "no water replaced" for custom molecules
started: Current issue
context:
  - Custom molecules should replace water when generated (not preview)
  - Preview mode places without water removal (correct)
  - Generate mode should remove water (but ion tab thinks it didn't)
  - Logic confusion between preview vs generate behavior
  - Ion tab may be checking wrong flag or status

## Eliminated

## Evidence
- timestamp: 2026-05-09T00:00:00Z
  checked: main_window.py lines 872-881, ion insertion handler
  found: Ion tab blocks Custom Molecule source with warning: "Custom molecules are placed at user-specified positions without removing water, so ions cannot be safely inserted."
  implication: Ion tab correctly prevents insertion because custom molecules don't replace water

- timestamp: 2026-05-09T00:00:00Z
  checked: CustomMoleculeInserter._build_existing_atoms_tree() lines 214-246
  found: Comment says "Liquid water atoms are EXCLUDED because they will be replaced during insertion" but this is only for overlap checking tree, not actual replacement
  implication: Misleading comment suggests water replacement, but this is for overlap detection only

- timestamp: 2026-05-09T00:00:00Z
  checked: CustomMoleculeInserter.place_random() lines 434-439
  found: Code uses `structure.positions[:ice_atom_count + water_atom_count + guest_atom_count]` which KEEPS all water atoms, then appends custom molecule atoms
  implication: Custom molecules are placed ADDITIVELY without removing any water molecules

- timestamp: 2026-05-09T00:00:00Z
  checked: CustomMoleculeInserter.place_custom() lines 558-563
  found: Same additive placement pattern - keeps all water atoms and appends custom molecules on top
  implication: Both placement modes use additive placement, no water removal

- timestamp: 2026-05-09T00:05:00Z
  checked: SoluteInserter._remove_overlapping_water() lines 350-449
  found: SoluteInserter has water removal logic that removes overlapping water molecules after solute placement
  implication: SoluteInserter was fixed to replace water (see solute-water-replacement.md), CustomMoleculeInserter needs same fix

- timestamp: 2026-05-09T00:10:00Z
  checked: All custom molecule tests after fix implementation
  found: tests/test_custom_molecule.py: 7/7 passed, tests/test_ion_source_dropdown.py: 11/11 passed
  implication: Fix works correctly, water replacement logic integrated successfully

## Resolution
root_cause: CustomMoleculeInserter does NOT replace water molecules after placement, unlike SoluteInserter which does. The implementation uses additive placement (keeps all water atoms and appends custom molecules on top), making the structure unsuitable for ion insertion. The misleading comment "Liquid water atoms are EXCLUDED because they will be replaced during insertion" refers only to the overlap checking tree, not actual water removal. SoluteInserter had the same issue but was fixed (solute-water-replacement.md) - CustomMoleculeInserter was never updated.
fix:
  1. Added _remove_overlapping_water() method to CustomMoleculeInserter (following SoluteInserter pattern) - removes water molecules that overlap with custom molecules
  2. Modified place_random() to call _remove_overlapping_water() after molecule placement
  3. Modified place_custom() to call _remove_overlapping_water() after molecule placement
  4. Updated both methods to use modified_interface_structure with water removed
  5. Updated misleading comments in _build_existing_atoms_tree()
  6. Updated main_window.py to allow custom molecule source for ion insertion (now that water is replaced)
verification:
  1. Custom molecules now replace overlapping water after generation - verified by water replacement log messages
  2. Ion tab now accepts custom molecule source - warning removed, custom molecule source handler updated in main_window.py
  3. Water replacement count logged - logger.info shows removed water molecule count
  4. All tests pass - test_custom_molecule.py: 7/7 passed, test_ion_source_dropdown.py: 11/11 passed
  5. Test file updated to check correct indices for custom molecules in complete system
files_changed:
  - quickice/structure_generation/custom_molecule_inserter.py: Added _remove_overlapping_water() method, updated place_random() and place_custom() to use it
  - quickice/gui/main_window.py: Updated ion insertion handler to support custom molecule source
