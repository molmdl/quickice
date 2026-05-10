---
status: verifying
trigger: "When using 'hydrate -> custom -> solute' workflow with custom source, the liquid region in 3D viewer shows ONLY the inserted solute, NOT the custom molecule. However, 'ice -> custom -> solute' works correctly and shows both custom molecule and solute."
created: 2026-05-10T00:00:00Z
updated: 2026-05-10T00:11:00Z
---

## Current Focus

hypothesis: Fix implemented - pass modified interface structure to render_custom_molecules
test: Verify fix by running verification test and existing tests
expecting: Custom molecules should now be visible in solute viewer for hydrate workflow
next_action: Clean up test files and verify with user

## Symptoms

expected: Liquid region should display liquid water, custom molecule, AND solute (same as ice -> custom -> solute workflow). Hydrate layer should remain correct (and it does).
actual: Liquid region shows only solute, custom molecule is NOT visible. Hydrate layer is correct.
errors: No error messages during generation. User tried to export and got "name np not defined" error (separate issue).
reproduction: 
  1. Create hydrate structure (default settings)
  2. Create slab interface (default settings)
  3. Add custom molecule: @quickice/data/custom/etoh* files
  4. Add solute: 10 CH4 molecules (default)
  5. Generate
  6. Observe 3D viewer: only solute visible in liquid region, no custom molecule
started: Unknown - not sure if this ever worked correctly
comparison: ice -> custom -> solute workflow works correctly (both custom mol and solute visible)

## Eliminated

<!-- APPEND only - prevents re-investigating -->

## Evidence

- timestamp: 2026-05-10T00:01:00Z
  checked: CustomMoleculeInserter code (custom_molecule_inserter.py)
  found: Creates CustomMoleculeStructure with complete system (ice + water + custom molecules), stores interface_structure reference
  implication: Custom molecules are tracked in the structure

- timestamp: 2026-05-10T00:02:00Z
  checked: SoluteInserter._remove_overlapping_water method (solute_inserter.py lines 342-608)
  found: Method creates new InterfaceStructure with custom molecules appended after guests. Stores custom molecule data in attributes: custom_molecule_positions, custom_molecule_atom_names, custom_molecule_atom_count
  implication: Modified interface structure has custom molecule data in dynamic attributes

- timestamp: 2026-05-10T00:03:00Z
  checked: SoluteViewerWidget.render_custom_molecules method (solute_viewer.py lines 493-545)
  found: Method expects custom_structure parameter and extracts custom molecules from positions[ice_atom_count + water_atom_count:...]
  implication: Rendering code expects to find custom molecules in the positions array

- timestamp: 2026-05-10T00:04:00Z
  checked: MainWindow._on_insert_solutes handler (main_window.py lines 1064-1067)
  found: Calls render_custom_molecules(self._current_custom_molecule_result) with the ORIGINAL CustomMoleculeStructure, not the modified interface structure from solute_structure.interface_structure
  implication: **ROOT CAUSE IDENTIFIED** - Wrong structure passed to render_custom_molecules

- timestamp: 2026-05-10T00:06:00Z
  checked: Implemented fix in solute_viewer.py render_custom_molecules method
  found: Added logic to detect and use separate custom molecule attributes (custom_molecule_positions, custom_molecule_atom_names) if present, otherwise fall back to extracting from positions array
  implication: Fix makes rendering work with both original CustomMoleculeStructure and modified InterfaceStructure

- timestamp: 2026-05-10T00:07:00Z
  checked: Updated main_window.py to pass solute_structure.interface_structure instead of original CustomMoleculeStructure
  found: Changed line 1067 to pass solute_structure.interface_structure to render_custom_molecules
  implication: Correct structure now being passed with up-to-date custom molecule positions

- timestamp: 2026-05-10T00:08:00Z
  checked: Ran verification test test_hydrate_custom_solute_fix.py
  found: All tests pass - SoluteInserter preserves custom molecule data, and render_custom_molecules handles separate attributes correctly
  implication: Fix verified to work correctly

- timestamp: 2026-05-10T00:09:00Z
  checked: Ran existing tests (test_solute_insertion.py, test_custom_to_solute_workflow)
  found: All relevant tests pass (9 passed, 2 skipped in test_solute_insertion.py; test_custom_to_solute_workflow passes)
  implication: Fix does not break existing functionality

## Resolution

root_cause: In main_window.py line 1067, render_custom_molecules was called with the original CustomMoleculeStructure (self._current_custom_molecule_result) instead of the modified interface structure that contains the correct custom molecule positions after water removal. When solutes are inserted, SoluteInserter._remove_overlapping_water creates a new InterfaceStructure with custom molecule data stored in dynamic attributes (custom_molecule_positions, custom_molecule_atom_names, custom_molecule_atom_count), but these were not being used for rendering.

fix: 
1. Updated solute_viewer.py render_custom_molecules() to handle both CustomMoleculeStructure and modified InterfaceStructure by checking for separate custom molecule attributes and using them if present
2. Updated main_window.py line 1067 to pass solute_structure.interface_structure (which has correct custom molecule positions after water removal) instead of the original CustomMoleculeStructure

verification: 
- Created test_hydrate_custom_solute_fix.py which verifies SoluteInserter preserves custom molecule data and render_custom_molecules handles separate attributes correctly - all tests pass
- Ran existing tests: test_solute_insertion.py (9 passed, 2 skipped), test_custom_to_solute_workflow (passed)
- No regressions in existing functionality

files_changed:
- quickice/gui/solute_viewer.py: Modified render_custom_molecules() to handle separate custom molecule attributes
- quickice/gui/main_window.py: Changed to pass solute_structure.interface_structure to render_custom_molecules
