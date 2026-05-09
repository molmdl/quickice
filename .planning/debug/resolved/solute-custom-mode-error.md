---
status: resolved
trigger: "Investigate issue: solute-custom-mode-error"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
---

## Current Focus

hypothesis: create_custom_molecule_actor() function does not accept molecule_indices parameter but is being called with it
test: Search for create_custom_molecule_actor() calls and function definition
expecting: Find where it's being called with molecule_indices and where it's defined without that parameter
next_action: Locate create_custom_molecule_actor() function definition and all call sites

## Symptoms

expected: Solute insertion should work with custom molecule source
actual: Error occurs when trying to insert solute with custom molecule source
errors: `Error: create_custom_molecule_actor() got an unexpected keyword argument 'molecule_indices'`
reproduction: 
  1. Load interface structure
  2. Insert custom molecules (random or custom mode)
  3. Switch to solute tab
  4. Select "Custom Molecule" as source
  5. Click generate
  6. Error appears
started: Current issue after recent fixes
previous_fix: Added custom molecule rendering to solute_viewer.py
context:
  - Recent fix added render_custom_molecules() to solute_viewer
  - Error suggests function signature mismatch
  - molecule_indices parameter may not exist in create_custom_molecule_actor()

## Eliminated

## Evidence

- timestamp: 2026-05-09T00:00:00Z
  checked: Function signature of create_custom_molecule_actor()
  found: Function defined in custom_molecule_renderer.py:113 accepts parameters: positions, atom_names, cell, moleculetype_name, mode
  implication: Function does NOT accept molecule_indices parameter

- timestamp: 2026-05-09T00:00:00Z
  checked: Call site in solute_viewer.py:539
  found: Incorrectly calling with molecule_indices=molecule_indices instead of moleculetype_name
  implication: Parameter name mismatch causes the error

- timestamp: 2026-05-09T00:00:00Z
  checked: Correct usage in custom_molecule_viewer.py:488 and 646
  found: Both calls use moleculetype_name as fourth parameter
  implication: This is the correct pattern to follow

- timestamp: 2026-05-09T00:00:00Z
  checked: CustomMoleculeStructure class attributes
  found: Class has moleculetype_name attribute at line 522
  implication: custom_structure.moleculetype_name is available and should be used

## Resolution

root_cause: solute_viewer.py incorrectly calls create_custom_molecule_actor() with non-existent 'molecule_indices' parameter instead of required 'moleculetype_name' parameter. The function signature expects moleculetype_name as the 4th positional argument, but the call was passing molecule_indices which doesn't exist in the function definition.
fix: Removed incorrect molecule_indices calculation code (lines 528-536) and fixed function call to use custom_structure.moleculetype_name as the 4th parameter instead of molecule_indices
verification: 
  - Python syntax check passed (py_compile)
  - Module import successful
  - All solute insertion tests pass (9 passed, 2 skipped)
  - All custom molecule renderer tests pass (18 passed)
  - Code now matches correct usage pattern from custom_molecule_viewer.py
files_changed: [/share/home/nglokwan/quickice/quickice/gui/solute_viewer.py]
