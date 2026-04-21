---
status: resolved
trigger: "Fix NameError - same pattern as interface_to_vtk_molecules"
created: 2026-04-21T00:00:00Z
updated: 2026-04-21T00:00:00Z
---

## Current Focus
hypothesis: "lazy loading functions use underscore prefix, but calls don't include underscore"
test: "grep for underscore-prefixed functions that are called without underscore"
expecting: "find all mismatches and fix them"
next_action: "Fix lines 269-271 to use underscore prefix"

## Evidence
- timestamp: 2026-04-21
  checked: "_create_bond_lines_actor and _create_unit_cell_actor pattern"
  found: "Lines 48-49: `_create_bond_lines_actor = None` (underscore prefix); Lines 63-64: imports real function into underscore-prefixed global"
  implication: "Calls at lines 269-271 are missing underscore prefix"

## Symptoms
expected: "create_bond_lines_actor should be callable"
actual: "NameError: name 'create_bond_lines_actor' is not defined. Did you mean: '_create_bond_lines_actor'?"
errors: ["NameError: name 'create_bond_lines_actor' is not defined"]
reproduction: "N/A - known pattern issue"
started: "now"

## Eliminated

## Evidence

## Resolution
root_cause: "Lazy loading pattern uses underscore-prefixed globals (_create_bond_lines_actor, _create_unit_cell_actor) but calls at lines 269-271 used non-prefixed names"
fix: "Changed 3 calls to use underscore prefix: _create_bond_lines_actor and _create_unit_cell_actor"
verification: "Syntax verified, pattern matches _interface_to_vtk_molecules pattern" 
files_changed: ["quickice/gui/ion_viewer.py"]
