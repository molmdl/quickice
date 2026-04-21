---
status: resolved
trigger: "Fix NameError in ion_viewer.py - function name typo"
created: 2026-04-21T00:00:00Z
updated: 2026-04-21T00:00:00Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: "Line 262 calls `interface_to_vtk_molecules()` but function is `_interface_to_vtk_molecules()` with underscore"
test: "Read ion_viewer.py and verify the typo, then fix"
expecting: "Function call matches defined function name"
next_action: "Fix the typo on line 262"

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: "Function `interface_to_vtk_molecules()` should be called"
actual: "NameError: name 'interface_to_vtk_molecules' is not defined. Did you mean: '_interface_to_vtk_molecules'?"
errors: "NameError: name 'interface_to_vtk_molecules' is not defined"
reproduction: "Run code that calls the function"
started: "Unknown - typo in code"

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-21T00:00:00Z
  checked: "ion_viewer.py line 262"
  found: "Function call is `interface_to_vtk_molecules(structure)` without underscore"
  implication: "Call does not match the lazy-loaded wrapper variable which is `_interface_to_vtk_molecules`"

- timestamp: 2026-04-21T00:00:00Z
  checked: "ion_viewer.py lines 47, 54, 62"
  found: "Lazy-loading pattern stores import as `_interface_to_vtk_molecules` (with underscore prefix)"
  implication: "Must use underscore version at call site"

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: "Line 262 called `interface_to_vtk_molecules()` but the lazy-loaded wrapper variable is `_interface_to_vtk_molecules` (with underscore prefix). The underscore version is set at line 62: `_interface_to_vtk_molecules = interface_to_vtk_molecules`"

fix: "Changed line 262 from `interface_to_vtk_molecules(structure)` to `_interface_to_vtk_molecules(structure)`"

verification: "Import test passed, interface ordering tests (5 tests) passed, syntax validated"

files_changed:
  - quickice/gui/ion_viewer.py