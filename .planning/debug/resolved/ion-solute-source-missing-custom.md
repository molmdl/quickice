---
status: resolved
trigger: "ion-solute-source-missing-custom"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
symptoms_prefilled: true
---

## Current Focus

hypothesis: Fix verified - custom molecules now render correctly when ion source="Solute"
test: Ran test_ion_solute_custom_workflow.py and verified the fix is present
expecting: All tests pass ✓
next_action: Update debug file to resolved status

## Symptoms

expected: In ion tab with "Solute" source (where solute was derived from custom molecules), the 3D viewer should show interface + custom molecules + solutes + ions
actual: 3D viewer shows interface + solutes + ions, but custom molecules are missing
errors: No error, just missing visualization
reproduction: 
  Workflow: Interface → Custom → Solute → Ion
  1. Load interface structure
  2. Insert custom molecules (random or custom mode)
  3. Insert solutes using "Custom Molecule" source
  4. Switch to ion tab
  5. Choose "Solute" as source
  6. Click generate
  7. 3D viewer missing custom molecules
  
  Comparison:
  - Ion source = "Custom": Shows interface + custom mol + ions ✓
  - Ion source = "Solute": Shows interface + solute + ions, NO custom mol ✗
started: Current issue
timeline: Current issue
context:
  - Custom molecules are correctly shown when ion uses custom molecule source directly
  - Custom molecules are missing when ion uses solute source (where solute was derived from custom)
  - The solute structure should contain/represent the custom molecules
  - Ion viewer may need to render custom molecules when source is "Solute" but the structure has custom molecules

## Eliminated

<!-- No hypotheses eliminated yet -->

## Evidence

- timestamp: 2026-05-09T00:00:00Z
  checked: main_window.py _on_insert_solutes() lines 1048-1052
  found: When solute source is "Custom Molecule", the code renders custom molecules in solute viewer
  implication: The pattern exists for rendering custom molecules after solute insertion

- timestamp: 2026-05-09T00:00:00Z
  checked: main_window.py _on_insert_ions() lines 935-956
  found: When ion source is "Solute", the code renders solutes (lines 935-950) and custom molecules when source is "Custom Molecule" (lines 952-956), but does NOT render custom molecules when source is "Solute"
  implication: This is the bug - missing logic to render custom molecules when ion source is "Solute" and the solute was derived from custom molecules

- timestamp: 2026-05-09T00:00:00Z
  checked: Workflow trace: Interface → Custom → Solute → Ion
  found: Custom molecules stored in self._current_custom_molecule_result, solutes stored in self._current_solute_result
  implication: Both variables exist when the workflow is complete, but ion insertion doesn't check for custom molecules when source is "Solute"

- timestamp: 2026-05-09T00:00:00Z
  checked: Fix implementation in main_window.py lines 951-956
  found: Added custom molecule rendering logic after solute rendering when source="Solute"
  implication: Fix mirrors the pattern used in solute viewer for rendering custom molecules

- timestamp: 2026-05-09T00:00:00Z
  checked: Test verification with test_ion_solute_custom_workflow.py
  found: All tests pass, fix is correctly implemented
  implication: The fix works correctly and doesn't break existing functionality

## Resolution

root_cause: In main_window.py _on_insert_ions(), when the ion source is "Solute" (where the solute was derived from custom molecules), the code renders the interface, ions, and solutes, but does NOT render custom molecules. The fix requires adding logic similar to what's in _on_insert_solutes() to render custom molecules when source="Solute" and _current_custom_molecule_result exists.
fix: Added custom molecule rendering logic in main_window.py _on_insert_ions() after solute rendering (lines 951-956). When source="Solute" and _current_custom_molecule_result exists, render custom molecules in ion viewer.
verification: Ran test_ion_solute_custom_workflow.py - all tests pass. Verified that the fix is present and working correctly. Also ran existing tests (test_solute_ion_workflow.py, test_ion_viewer_custom_mol.py, test_custom_mol_solute_viewer_fix.py) - all pass without issues.
files_changed: [quickice/gui/main_window.py]
