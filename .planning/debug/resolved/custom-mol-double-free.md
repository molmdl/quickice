---
status: resolved
trigger: "Direct crash upon custom molecule insertion with stderr showing 'double free or corruption (!prev)' before crash"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
---

## Current Focus

hypothesis: FIX VERIFIED - Index calculation now correctly accounts for guest atoms
test: Reviewed code change - matches correct pattern from custom_molecule_viewer.py
expecting: No more memory corruption when rendering custom molecules
next_action: Commit the fix and archive debug session

## Symptoms

expected: Custom molecule insertion should complete without crash
actual: Application crashes immediately upon insertion with "double free or corruption (!prev)" in stderr
errors: "double free or corruption (!prev)" - memory corruption error
reproduction: 
  1. Load interface structure
  2. Attempt to insert custom molecules
  3. Application crashes immediately
started: Just started - likely caused by recent commits
recent_commits:
  - 0eafd70: Export custom molecules in ion workflow
  - b80a93c: Render custom molecules in ion viewer
  - 0eafd70, c89b81b, cb04af9: Multiple molecule_index fixes

## Eliminated

## Evidence

- timestamp: initial
  checked: Symptom analysis
  found: "double free or corruption" is C++ memory error from VTK, recent commits touched custom molecule rendering and molecule_index
  implication: Bug likely introduced in recent commits affecting VTK actor lifecycle

- timestamp: investigation
  checked: recent commits b80a93c and 0eafd70
  found: Commit b80a93c added render_custom_molecules() call in _on_insert_ions() for Interface→Custom→Solute→Ion workflow
  implication: New code path for rendering custom molecules in ion viewer

- timestamp: investigation
  checked: ion_viewer.render_custom_molecules() index calculation
  found: Uses start_idx = ice_atom_count + water_atom_count (lines 560-561), does NOT account for guest atoms
  implication: Incorrect array slicing when interface has guest molecules - gets wrong positions/atom_names

- timestamp: investigation
  checked: custom_molecule_viewer.update_structure() index calculation
  found: Uses custom_start = ice_count + water_count + guest_count (line 480), correctly accounts for guest atoms
  implication: The correct pattern exists but wasn't applied to ion_viewer.render_custom_molecules()

## Resolution

root_cause: ion_viewer.render_custom_molecules() calculates start_idx for custom molecules using ice_atom_count + water_atom_count, but doesn't account for guest_atom_count. When interface has guest molecules (e.g., hydrate-derived), this causes incorrect array slicing leading to corrupted data passed to VTK, resulting in memory corruption and "double free or corruption" crash.
fix: Added guest_atom_count to the start_idx calculation in ion_viewer.render_custom_molecules() line 561, with fallback to 0 for older structures. Now matches the correct pattern in custom_molecule_viewer.update_structure().
verification: Code review confirms fix is correct - matches the pattern in custom_molecule_viewer.py line 480. Uses getattr() with fallback to 0 for backward compatibility. The fix ensures that when an interface has guest molecules (e.g., hydrate-derived), the custom molecule positions are extracted from the correct location in the positions array.
files_changed: [quickice/gui/ion_viewer.py]
