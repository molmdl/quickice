---
status: checkpoint
trigger: "guest-missing-after-ion-insertion: After ion insertion, only half of each hydrate layer has guest molecules, while interface before insertion had correct guest distribution."
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T01:30:00Z
---

## Current Focus

hypothesis: After extensive code tracing (static analysis), the code flow appears correct. Both interface_viewer.py and ion_viewer.py use identical rendering pipelines for guests (_create_guest_ball_and_stick_actor method, interface_to_vtk_molecules function). The same InterfaceStructure object is used for both tabs. Unable to identify root cause via static analysis - need runtime debugging.
test: Unable to reproduce without runtime access - need user to verify or provide more details
expecting: Either find the bug or need user input to proceed
next_action: Return CHECKPOINT to user for verification or additional debugging help

## Symptoms
<!-- IMMUTABLE: Symptoms prefilled from UAT/context -->

expected: All hydrate cages should have guest molecules (as in interface before ion insertion)
actual: After ion insertion, only ~50% of hydrate layer has guest molecules
errors: None
reproduction:
  1. Generate hydrate (full guest in all cages)
  2. Generate interface from hydrate - check guest distribution (correct)
  3. Insert ions
  4. Check ion tab 3D viewer - guest molecules missing from ~50% of hydrate layer
started: Started when transitioning from interface to ion workflow

## Eliminated
<!-- APPEND only - prevents re-investigating -->

- hypothesis: _build_molecule_index_from_structure makes incorrect assumptions about positions array layout
  evidence: Verified piece.py assembles positions as [ice, guest, water] which matches assumption
  timestamp: 2026-04-28T00:10:00Z

- hypothesis: interface_to_vtk_molecules incorrectly splits the interface structure
  evidence: Verified function correctly uses ice_atom_count and guest_atom_count to split positions
  timestamp: 2026-04-28T00:15:00Z

- hypothesis: interface_viewer.py and ion_viewer.py use different guest rendering
  evidence: Both use identical _create_guest_ball_and_stick_actor method with same parameters
  timestamp: 2026-04-28T00:30:00Z

- hypothesis: Different camera angles cause guests to be out of view
  evidence: Both viewers use same SetViewUp(0,1,0) and _reset_camera pattern (differs only in distance)
  timestamp: 2026-04-28T00:50:00Z

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-28T00:00:00Z
  checked: Debug context and symptoms
  found: Issue is specific to ion insertion step - interface before insertion is correct
  implication: Bug is in ion insertion code, not in hydrate generation or interface creation

- timestamp: 2026-04-28T00:05:00Z
  checked: ion_inserter.py - _build_molecule_index_from_structure method
  found: Method assumes positions array layout is [ice atoms, guest atoms, water atoms] and builds molecule_index accordingly
  implication: If actual InterfaceStructure positions layout differs, guest molecules will be read from wrong indices

- timestamp: 2026-04-28T00:10:00Z
  checked: piece.py - assemble_piece method
  found: Confirms positions layout is [ice, guest, water] - ice_atom_count = len(centered_ice_positions), guest_atom_count = len(guest_positions)
  implication: Layout assumption in _build_molecule_index_from_structure is correct

- timestamp: 2026-04-28T00:15:00Z
  checked: vtk_utils.py - interface_to_vtk_molecules function
  found: Correctly splits interface into ice (0:ice_atom_count), guest (ice_atom_count:ice_atom_count+guest_atom_count), water (ice_atom_count+guest_atom_count:)
  implication: Rendering function correctly interprets InterfaceStructure layout

- timestamp: 2026-04-28T00:20:00Z
  checked: ion_viewer.py - set_interface_structure and set_ion_structure methods
  found: set_interface_structure uses _interface_to_vtk_molecules to render ice+guest+water; set_ion_structure only adds ions on top
  implication: Guest rendering should work if interface is passed correctly

- timestamp: 2026-04-28T00:25:00Z
  checked: main_window.py - _on_insert_ions method
  found: Calls set_interface_structure(interface) with self._current_interface_result, then set_ion_structure(ion_structure)
  implication: Same interface result is used for both interface tab and ion tab

- timestamp: 2026-04-28T00:40:00Z
  checked: ion_inserter.py - replace_water_with_ions flow
  found: Modifies structure.molecule_index in place, but this doesn't affect positions array or guest rendering
  implication: molecule_index modification is not the cause

- timestamp: 2026-04-28T00:45:00Z
  checked: Traced full flow from hydrate generation → interface generation → ion insertion → rendering
  found: Code flow appears correct; InterfaceStructure has correct guest_atom_count and positions; both viewers use same rendering pipeline
  implication: Issue may be intermittent, related to timing, or the "50% missing" observation may be misleading

- timestamp: 2026-04-28T01:00:00Z
  checked: Searched for differences between interface_viewer.py and ion_viewer.py guest rendering
  found: Both use identical code for rendering guests (_create_guest_ball_and_stick_actor), both use same interface_to_vtk_molecules function
  implication: If interface tab shows guests correctly, ion tab should also show them correctly with same data

- timestamp: 2026-04-28T01:15:00Z
  checked: Verified _current_interface_result is only set once (line 538 in main_window.py)
  found: Same object reference is used for both interface_viewer and ion_viewer
  implication: Data should be identical; any modification to the object would affect both viewers

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: NOT YET DETERMINED - Static analysis shows correct code flow. The interface_viewer.py and ion_viewer.py use identical rendering pipelines. Same InterfaceStructure object is passed to both. Need runtime debugging to identify actual cause.
fix:
verification:
files_changed: []
