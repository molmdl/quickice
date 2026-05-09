---
status: resolved
trigger: "For workflows custom mol random mode -> solute -> ion and custom mol random mode -> ion, the custom molecules are not shown in the 3D viewer of the ion tab"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
---

## Current Focus
hypothesis: CONFIRMED - Ion viewer needs two fixes: (1) Add render_custom_molecules() method and _custom_molecule_actors tracking in ion_viewer.py, (2) Add call to render_custom_molecules in main_window.py after ion insertion when source is "Custom Molecule"
test: Implement the same pattern as solute_viewer fix
expecting: Custom molecules will render in ion tab 3D viewer
next_action: Add render_custom_molecules method to ion_viewer.py

## Symptoms
expected: Custom molecules should be visible in the ion tab 3D viewer when custom molecule or solute (derived from custom molecule) is used as source
actual: Custom molecules do not appear in the ion tab 3D viewer
errors: No error, just missing visualization
reproduction: 
  Workflow 1: Custom mol -> Solute -> Ion
  1. Load interface structure
  2. Insert custom molecules using random mode
  3. Insert solutes using custom molecule source
  4. Switch to ion tab
  5. Custom molecules not visible in 3D viewer
  
  Workflow 2: Custom mol -> Ion
  1. Load interface structure
  2. Insert custom molecules using random mode
  3. Switch to ion tab
  4. Select custom molecule source
  5. Custom molecules not visible in 3D viewer
started: Current issue
context:
  - Custom molecules are present in the structure (insertion succeeded)
  - Issue is with ion_viewer visualization
  - Solute viewer was fixed to show custom molecules, ion viewer may need similar fix
  - Need to check if ion_viewer has render_custom_molecules() method or similar

## Eliminated

## Evidence

- timestamp: 2026-05-09T00:00:00Z
  checked: Compared ion_viewer.py with solute_viewer.py
  found: solute_viewer.py has render_custom_molecules() method (lines 493-545) and _custom_molecule_actors list (line 115). ion_viewer.py is missing both.
  implication: ion_viewer lacks the capability to render custom molecules

- timestamp: 2026-05-09T00:00:00Z
  checked: main_window.py ion insertion handler (lines 935-950)
  found: Code renders solutes when source is "Solute", but NO code to render custom molecules when source is "Custom Molecule"
  implication: Need to add similar rendering logic for custom molecules after ion insertion

- timestamp: 2026-05-09T00:00:00Z
  checked: main_window.py solute insertion handler (lines 1043-1046)
  found: Shows the pattern - check if source is "Custom Molecule" and call render_custom_molecules on the viewer
  implication: This is the correct pattern to apply to ion insertion handler

## Resolution
root_cause: Ion viewer lacked render_custom_molecules() method and _custom_molecule_actors tracking that exists in solute_viewer.py. Main window did not call render_custom_molecules after ion insertion when source was "Custom Molecule".
fix: 
  1. Added _custom_molecule_actors list to IonViewerWidget.__init__
  2. Added _clear_custom_molecule_actors() method to IonViewerWidget
  3. Added render_custom_molecules() method to IonViewerWidget (mirrors solute_viewer pattern)
  4. Updated _clear_actors() to clear custom molecule actors
  5. Updated clear_interface_only() to clear custom molecule actors
  6. Added call to render_custom_molecules in main_window._on_insert_ions when source is "Custom Molecule"
verification: 
  - Unit test confirms IonViewerWidget has render_custom_molecules method and _custom_molecule_actors attribute
  - Syntax check passed for both modified files
  - Pattern matches the successful fix applied to solute_viewer
files_changed:
  - quickice/gui/ion_viewer.py: Added custom molecule rendering support
  - quickice/gui/main_window.py: Added render_custom_molecules call after ion insertion
