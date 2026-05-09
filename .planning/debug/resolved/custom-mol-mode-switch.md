---
status: resolved
trigger: "custom-mol-mode-switch"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:05Z
---

## Current Focus

hypothesis: When switching from Random to Custom mode, previous insertion results are not cleared, and there's no user prompt to choose whether to start fresh or add to existing molecules
test: All unit tests pass (8/8)
expecting: Fix verified through automated tests
next_action: Archive and commit

## Symptoms

expected: User should have option to either:
  - Start fresh from clean interface (no previous custom molecules)
  - Add onto existing custom molecules from previous placement
actual: When switching from random to custom mode, the preview shows molecule overlay on the random placement box without giving user choice
errors: No error, but workflow is confusing
reproduction: 
  1. Load interface structure
  2. Insert custom molecules using random mode
  3. Switch to custom placement mode
  4. Preview shows molecule overlay on the random placement box
  5. No option to clear and start fresh
started: Current issue
timeline: Current issue
context:
  - This is a UX/workflow issue
  - User wants control over whether to add to existing or start fresh
  - May need UI control (checkbox, button, or mode reset)

## Eliminated

## Evidence

- timestamp: 2026-05-09T00:00:00Z
  checked: custom_molecule_panel.py lines 602-626
  found: _on_placement_mode_changed only shows/hides controls and updates displays, does NOT clear previous insertion results or positions_added list
  implication: Mode switching has no state cleanup

- timestamp: 2026-05-09T00:00:01Z
  checked: custom_molecule_panel.py lines 905-929
  found: reset() method exists that clears positions_added and resets state, but it's not called during mode switching
  implication: There's a reset mechanism available but not utilized

- timestamp: 2026-05-09T00:00:01Z
  checked: custom_molecule_panel.py line 69
  found: self.positions_added list stores positions for Custom mode
  implication: This list persists across mode switches unless explicitly cleared

- timestamp: 2026-05-09T00:00:02Z
  checked: custom_molecule_viewer.py lines 563-579
  found: Viewer has clear() method that clears all actors (custom, preview, interface)
  implication: Can use viewer.clear() to reset the display

- timestamp: 2026-05-09T00:00:02Z
  checked: main_window.py lines 106, 1097
  found: _current_custom_molecule_result is set when insertion completes, but never cleared during mode switching
  implication: Previous results persist in memory and viewer

- timestamp: 2026-05-09T00:00:04Z
  checked: test_custom_mol_mode_switch.py
  found: All 8 unit tests pass
  implication: Fix correctly implements the desired behavior

## Resolution

root_cause: When switching placement modes, the application does not clear previous insertion results or ask user preference, leading to confusion about whether molecules will be added to existing or start fresh
fix: 
  - Added _has_previous_insertion flag to CustomMoleculePanel to track insertion state
  - Added clear_previous_results signal to panel
  - Modified _on_placement_mode_changed to show dialog when previous insertion exists
  - Dialog offers three choices: Start Fresh (Yes), Add to Existing (No), or Cancel
  - Added mark_insertion_complete() method to set flag after successful insertion
  - Added _on_clear_custom_molecule_results handler in MainWindow to clear results and viewer
  - Connected signal and handler in MainWindow setup
  - Handler reloads interface structure (ice + water) after clearing custom molecules
verification: All unit tests pass (8/8), providing complete coverage of the new functionality
files_changed: 
  - quickice/gui/custom_molecule_panel.py
  - quickice/gui/main_window.py
  - test_custom_mol_mode_switch.py (new test file)
