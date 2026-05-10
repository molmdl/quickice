---
status: resolved
trigger: "For the workflow hydrate -> slab -> custom -> solute -> ion, no custom mol ITP is exported when user exports via ctrl-S. Output files show ch4.itp and ch4_liquid.itp are exported, but the custom molecule from the "custom" step may not be properly handled."
created: 2026-05-10T00:00:00Z
updated: 2026-05-10T00:10:00Z
---

## Current Focus

hypothesis: SoluteStructure lacks custom molecule fields. solute_inserter.py preserves custom molecule info in modified_interface but doesn't propagate it to SoluteStructure, causing ion_inserter.py to default to 0 custom molecules
test: Add custom molecule fields to SoluteStructure and propagate from interface_structure in solute_inserter.py
expecting: After fix, ion export will properly copy custom molecule ITP files
next_action: Commit the fix

## Symptoms

expected: Custom molecule ITP file should be exported and included in the .top file when exporting the final ion structure
actual: Custom molecule ITP may not be properly exported or included in topology
errors: No explicit error reported
reproduction: Workflow: hydrate -> slab -> custom -> solute -> ion, then export via ctrl-S
started: Current issue

## Eliminated

<!-- Empty - no hypotheses eliminated yet -->

## Evidence

- timestamp: 2026-05-10T00:00:00Z
  checked: types.py SoluteStructure definition (lines 423-445)
  found: SoluteStructure does NOT have custom molecule fields (no custom_molecule_count, custom_itp_path, etc.)
  implication: Custom molecule info is lost when SoluteStructure is created

- timestamp: 2026-05-10T00:00:00Z
  checked: ion_inserter.py lines 479-487
  found: Uses getattr(structure, 'custom_molecule_count', 0) to get custom molecule info, defaults to 0 if not present
  implication: When SoluteStructure is passed to ion_inserter, custom_molecule_count defaults to 0

- timestamp: 2026-05-10T00:00:00Z
  checked: export.py IonGROMACSExporter lines 355-367
  found: Checks ion_structure.custom_molecule_count > 0 before copying custom ITP file
  implication: If custom_molecule_count is 0, custom ITP file is not copied

- timestamp: 2026-05-10T00:00:00Z
  checked: solute_inserter.py lines 800-809
  found: SoluteStructure creation does not include custom molecule fields
  implication: Custom molecule info is not propagated from input structure to SoluteStructure

- timestamp: 2026-05-10T00:00:00Z
  checked: solute_inserter.py lines 587-607
  found: _remove_overlapping_water() preserves custom molecule attributes in modified_interface (sets custom_molecule_count, custom_molecule_positions, etc.)
  implication: The modified_interface has the custom molecule info, but it's not transferred to SoluteStructure

## Resolution

root_cause: SoluteStructure dataclass lacks custom molecule fields (custom_molecule_count, custom_itp_path, etc.). When workflow is hydrate → slab → custom → solute → ion, the custom molecule info is preserved in interface_structure by solute_inserter._remove_overlapping_water(), but not propagated to SoluteStructure. ion_inserter.py then uses getattr(structure, 'custom_molecule_count', 0) which returns 0, causing IonGROMACSExporter to skip copying the custom ITP file.
fix: Added custom molecule fields to SoluteStructure in types.py and propagated them from interface_structure in solute_inserter.py (all three SoluteStructure creation points updated)
verification: 
  - Created test_custom_mol_propagation.py to verify custom molecule info is correctly propagated
  - Test confirms getattr(solute_structure, 'custom_molecule_count', 0) returns correct value (6)
  - Test confirms getattr(solute_structure, 'custom_itp_path', None) returns correct path
  - All existing solute-related tests pass (14 passed, 2 skipped)
files_changed: 
  - quickice/structure_generation/types.py (added custom molecule fields to SoluteStructure)
  - quickice/structure_generation/solute_inserter.py (propagate custom molecule info in all 3 SoluteStructure creation points)
