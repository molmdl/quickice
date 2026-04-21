---
status: resolved
trigger: "hydrate-to-interface - generate button shows log but no 3D viewer update"
created: "2026-04-21T00:00:00Z"
updated: "2026-04-21T00:00:00Z"
---

## Current Focus
next_action: "Archive the debug session"
hypothesis: "Fixed: _on_interface_hydrate_generate now properly calls start_interface_generation with hydrate as template"
test: "Click Generate with Hydrate Structure source -> interface generated and displayed in 3D viewer"
expecting: "Full interface generation flow works with hydrate as template"

## Symptoms
expected: "Interface generated using hydrate as template, displayed in 3D viewer"
actual: "Clicking Generate shows log but 3D viewer does NOT update"
errors: "No error displayed"
reproduction: "Tab 2 (Generate hydrate) -> Click To Interface -> Tab 3 dropdown select Hydrate Structure -> Click Generate -> Viewer doesn't update"
started: "Unknown"

## Eliminated

## Resolution
root_cause: "_on_interface_hydrate_generate() only pre-populated UI with set_from_hydrate() but never called start_interface_generation() to generate and display the interface structure in the 3D viewer"
fix: |4
  1. Added HydrateStructure.to_candidate() method to convert hydrate to ice Candidate
  2. Modified _on_interface_hydrate_generate() to convert hydrate -> candidate, then call start_interface_generation()
  3. Updated set_from_hydrate() to add extra space (1nm) for water layer in Piece mode (so box > hydrate cell for validation to pass)
verification: "Click Generate with Hydrate Structure source -> interface generated and displayed in 3D viewer"
files_changed:
  - "quickice/structure_generation/types.py: Added to_candidate() method to HydrateStructure"
  - "quickice/gui/main_window.py: Fixed _on_interface_hydrate_generate() to call start_interface_generation()"
  - "quickice/gui/interface_panel.py: Updated set_from_hydrate() to add extra space for water layer"