---
status: verifying
trigger: "Fix hydrate→interface - showing original hydrate, not new interface"
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: FIX APPLIED - When interface generation completes with hydrate source, viewer now renders the InterfaceStructure result instead of original hydrate
test: Run application and test hydrate→interface workflow
expecting: Should see hydrate framework + water layer in viewer
next_action: Mark as resolved

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: Interface should show hydrate framework at bottom with water layer on top or around it - a NEW combined structure combining hydrate + water
actual: Viewer shows the original hydrate unchanged - no water layer visible
errors: None specific (visual bug)
reproduction: Use hydrate→interface workflow in 3D viewer
started: Unknown

## Eliminated
<!-- APPEND only - prevents re-investigating -->


## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-22T00:05:00Z
  checked: main_window.py _on_export_to_interface_requested (lines 740-758)
  found: Calls set_hydrate_structure() directly on viewer - just renders hydrate, does NOT generate interface
  implication: Bug confirmed - the hydrate is displayed without any water layer because it's calling the wrong viewer method

- timestamp: 2026-04-22T00:05:00Z
  checked: interface_viewer.py set_hydrate_structure() method
  found: This method only renders hydrate framework + guests, does NOT create water layer
  implication: This method is for displaying hydrate only, not for creating hydrate→interface

- timestamp: 2026-04-22T00:05:00Z
  checked: main_window.py _on_interface_hydrate_generate() method
  found: This is the CORRECT flow - converts hydrate to candidate, calls viewmodel.start_interface_generation()
  implication: The generate button flow works correctly; only the completion handler was wrong

- timestamp: 2026-04-22T00:10:00Z
  checked: main_window.py _on_interface_generation_complete() method
  found: Was checking for hydrate source and calling set_hydrate_structure() instead of set_interface_structure()
  implication: Bug was here - the interface generation produces correct result but viewer shows original hydrate instead

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: In main_window.py _on_interface_generation_complete(), when interface is generated from hydrate source, the code was checking for hydrate and calling viewer.set_hydrate_structure() which renders the ORIGINAL hydrate structure instead of the generated InterfaceStructure. This caused the viewer to show just the hydrate (with water framework + guests), not the interface (hydrate framework + water layer).

fix: Simplified _on_interface_generation_complete() to always call viewer.set_interface_structure(result) when displaying the generated interface. The interface was correctly generated from hydrate (hydrate.to_candidate() -> assemble_piece), it just wasn't being displayed.

verification: Run application and test the hydrate→interface workflow. Expected: viewer shows hydrate framework with water layer around/above it (the generated InterfaceStructure).
files_changed:
  - quickice/gui/main_window.py (lines 557-563)