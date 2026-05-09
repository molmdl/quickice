---
status: resolved
trigger: "custom-mol-water-count"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
---

## Current Focus
hypothesis: _on_custom_finished in main_window.py doesn't calculate and display water replacement count
test: Compare _on_custom_finished with _on_insert_solutes to identify missing water count display logic
expecting: Find that _on_custom_finished lacks water replacement count calculation and display
next_action: Add water replacement count calculation and display to _on_custom_finished

## Symptoms
expected: After custom molecule insertion in random mode, should display a message showing how many water atoms were replaced (similar to solute insertion)
actual: No message about water replacement count is shown, user cannot verify if water replacement is working
errors: No error, missing functionality
reproduction: 
  1. Load interface structure
  2. Insert custom molecules using random mode
  3. Observe status messages - no water replacement count shown
started: Current issue after recent fix for water replacement
timeline: Current issue after recent fix for water replacement
previous_fix: Added _remove_overlapping_water() to CustomMoleculeInserter, but no count is displayed
context:
  - Solute insertion shows water replacement count
  - Custom molecule insertion should show similar count
  - Need to verify water removal is actually happening

## Eliminated

## Evidence
- timestamp: 2026-05-09T00:00:00Z
  checked: CustomMoleculeInserter._remove_overlapping_water() method
  found: Method tracks removed_count and logs it (line 357-360), but only returns modified InterfaceStructure, not the count
  implication: The count is calculated but not passed back to caller for display

- timestamp: 2026-05-09T00:00:00Z
  checked: SoluteInserter._remove_overlapping_water() method
  found: Same pattern - logs count but only returns modified structure
  implication: Both inserters use same approach, count must be calculated elsewhere

- timestamp: 2026-05-09T00:00:00Z
  checked: main_window._on_insert_solutes() method (lines 1034-1058)
  found: Calculates water replacement count by comparing original vs modified water counts, then logs it to UI
  implication: This is where solute insertion displays water count - the correct pattern to follow

- timestamp: 2026-05-09T00:00:00Z
  checked: main_window._on_custom_finished() method (lines 1115-1166)
  found: Does NOT calculate or display water replacement count. Only logs total atoms (lines 1147-1150)
  implication: ROOT CAUSE - Missing water replacement count calculation and display logic

## Resolution
root_cause: _on_custom_finished method in main_window.py does not calculate or display water replacement count, unlike _on_insert_solutes which does display this information
fix: Added water replacement count calculation and display logic to _on_custom_finished method (lines 1144-1157). Logic compares original water count from source interface with modified water count from result.interface_structure, then logs the count if > 0
verification: Created test_water_count_verification.py which confirms water replacement count is calculated correctly (1 water molecule replaced in test). The fix works as expected.
files_changed: [quickice/gui/main_window.py, test_water_count_verification.py]
