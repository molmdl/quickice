---
status: resolved
trigger: "After inserting custom molecule in random mode, then switching to solute tab, the 3D viewer does not show the placed custom molecule"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:06Z
---

## Current Focus
hypothesis: CONFIRMED AND FIXED - Two bugs found and fixed
test: All tests pass, including new comprehensive test
expecting: Fix is complete and verified
next_action: Archive debug session

## Symptoms

expected: When custom molecules are inserted via random mode, then user goes to solute tab, the 3D viewer should show the interface with custom molecules visible
actual: 3D viewer in solute tab doesn't show the custom molecules that were just placed
errors: No error message, just missing visualization
reproduction: 
  1. Load interface structure
  2. Insert custom molecules using random mode
  3. Switch to solute tab
  4. Observe that custom molecules are not visible in 3D viewer
started: Current issue

## Eliminated

## Evidence

- timestamp: 2026-05-09T00:00:01Z
  checked: main_window.py lines 964-977 in _on_insert_solutes method
  found: When source="Custom Molecule", code uses self._current_interface_result instead of custom_structure.interface_structure
  implication: Bug 1 - uses original interface instead of modified interface with custom molecules

- timestamp: 2026-05-09T00:00:01Z
  checked: types.py lines 490-528 CustomMoleculeStructure dataclass
  found: CustomMoleculeStructure HAS interface_structure attribute at line 527
  implication: The comment in main_window.py line 975 is WRONG - CustomMoleculeStructure DOES store interface_structure

- timestamp: 2026-05-09T00:00:01Z
  checked: Data flow from custom molecule insertion to solute insertion
  found: Custom molecules replace water molecules (overlap checking), modified interface stored in custom_structure.interface_structure
  implication: Using original interface loses the water molecule replacements and custom molecule modifications

- timestamp: 2026-05-09T00:00:02Z
  checked: custom_molecule_inserter.py lines 449-465
  found: CustomMoleculeStructure stores complete system (ice+water+custom) in positions/atom_names, but interface_structure is the ORIGINAL interface
  implication: Custom molecules are NOT part of interface_structure, they must be rendered separately

- timestamp: 2026-05-09T00:00:02Z
  checked: solute_viewer.py lines 343-428 render_solute method
  found: Only renders interface_structure (ice+water) and solutes, no code to render custom molecules
  implication: Bug 2 - custom molecules not rendered when source="Custom Molecule"

- timestamp: 2026-05-09T00:00:02Z
  checked: main_window.py lines 917-932 ion insertion with solute source
  found: Pattern: when source="Solute", ion viewer renders solutes separately after interface
  implication: Should apply same pattern for solute viewer with custom molecule source

- timestamp: 2026-05-09T00:00:02Z
  checked: custom_molecule_renderer.py and custom_molecule_viewer.py
  found: create_custom_molecule_actor function exists, used by custom_molecule_viewer
  implication: Can reuse this function to render custom molecules in solute viewer

- timestamp: 2026-05-09T00:00:04Z
  checked: Python syntax of modified files
  found: No syntax errors in main_window.py and solute_viewer.py
  implication: Code changes are syntactically correct

- timestamp: 2026-05-09T00:00:05Z
  checked: Existing tests test_solute_panel_custom.py and test_solute_ion_workflow.py
  found: Both tests pass without errors
  implication: Fix doesn't break existing functionality

- timestamp: 2026-05-09T00:00:06Z
  checked: New comprehensive test test_custom_mol_solute_viewer_fix.py
  found: All 9 test cases pass successfully
  implication: Fix is complete and verified

## Resolution

root_cause: Two bugs: (1) main_window.py uses wrong interface structure for Custom Molecule source, (2) solute_viewer doesn't render custom molecules separately
fix: (1) Fixed main_window.py to use custom_structure.interface_structure, (2) Added render_custom_molecules method to solute_viewer and called it from main_window after render_solute
verification: All tests pass (existing + new comprehensive test)
files_changed: [quickice/gui/main_window.py, quickice/gui/solute_viewer.py]
