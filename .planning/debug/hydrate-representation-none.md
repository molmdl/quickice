---
status: investigating
trigger: "Hydrate viewer ball-and-stick - NoneType molecule_index error"
created: 2026-04-16T00:00:00
updated: 2026-04-16T00:05:00
---

## Current Focus
next_action: "Verify bug in set_representation_mode - save structure reference before clearing actors"

hypothesis: "set_representation_mode saves _current_structure reference AFTER calling _clear_actors, which sets it to None"
test: "Trace line-by-line execution in set_representation_mode"
expecting: "Confirm that _current_structure becomes None before render_hydrate_structure is called"

## Symptoms
expected: Clicking "ball and stick" button should change representation
actual: Atom index error, viewer becomes empty
errors: "AttributeError: 'NoneType' object has no attribute 'molecule_index'" at hydrate_renderer.py:228 in create_water_framework_actor
reproduction: Generate hydrate → Click "ball and stick" button OR toggle representation mode
started: Atoms/bonds display correctly now after prior fix, but representation toggle fails

## Eliminated
- hypothesis: "Structure not set when representation changed"
  evidence: "User says atoms/bonds display correctly, so structure was set via set_hydrate_structure"
  timestamp: "2026-04-16T00:03:00"

## Evidence
- timestamp: "2026-04-16T00:03:00"
  checked: "hydrate_viewer.py set_representation_mode lines 348-373"
  found: "Line 364: condition checks _current_structure is not None"
  found: "Line 367: _clear_actors() is called"
  found: "Line 368-369: render_hydrate_structure(self._current_structure, mode) - but _current_structure was just set to None by _clear_actors!"
  implication: "BUG: _clear_actors() sets _current_structure = None, then render_hydrate_structure is called with None"

- timestamp: "2026-04-16T00:04:00"
  checked: "hydrate_viewer.py _clear_actors lines 289-300"
  found: "Line 300: self._current_structure = None"
  implication: "Confirmed: _clear_actors sets _current_structure to None"

- timestamp: "2026-04-16T00:05:00"
  checked: "hydrate_viewer.py set_hydrate_structure lines 214-249"
  found: "Line 233: self._current_structure = structure is set BEFORE render_hydrate_structure is called"
  found: "In set_hydrate_structure, structure is set first, then render_hydrate_structure is called with that structure"
  implication: "set_hydrate_structure is correct, but set_representation_mode calls _clear_actors BEFORE using _current_structure"

## Resolution
root_cause: "In set_representation_mode, _current_structure reference is lost because _clear_actors() is called before render_hydrate_structure"
fix: [not yet applied]
verification: [not yet applied]
files_changed: []
