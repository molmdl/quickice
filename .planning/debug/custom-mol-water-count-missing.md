---
status: diagnosed
trigger: "custom-mol-water-count-missing"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
---

## Current Focus

hypothesis: Code is correct and tests pass, so the issue must be in the specific user scenario or data. Need to add defensive logging to understand what values are actually being calculated.
test: All unit tests pass (test_custom_molecule.py: 7/7), comprehensive scenario tests show logic works
expecting: Find that the issue is either: (1) no water actually replaced in user's specific case, or (2) exception being caught silently, or (3) logging issue
next_action: Add detailed debug logging to _on_custom_finished to track the exact values of original_water_count, modified_water_count, and water_replaced

## Symptoms

expected: After custom molecule insertion completes, should display a message like "Replaced X water molecules" in the status log
actual: Insertion completes successfully, system displays in viewer, but no water replacement count is shown in the log
errors: No error message, just missing the water count display
reproduction: 
  1. Load interface structure
  2. Insert custom molecules using random mode
  3. Wait for completion
  4. System displays in viewer
  5. Check status log - no water replacement count shown
started: Current issue
timeline: Commit c66a109 added water replacement count display logic, but it's not appearing

## Eliminated

None yet

## Evidence

- timestamp: 2026-05-09T00:00:00Z
  checked: Symptoms documentation
  found: Water replacement IS happening (viewer shows result), count code exists in main_window.py (commit c66a109), but count not displayed
  implication: The insertion logic works, the display code exists, so either the display condition isn't met or the value isn't being tracked/passed correctly

- timestamp: 2026-05-09T00:00:00Z
  checked: main_window.py lines 1114-1181 (_on_custom_finished method)
  found: Water replacement count logic at lines 1146-1164. Calculates water_replaced by comparing original_water_count from _current_interface_result with modified_water_count from result.interface_structure
  implication: Logic is present and looks correct

- timestamp: 2026-05-09T00:00:00Z
  checked: test_water_count_verification.py and test_debug_water_count.py
  found: Tests pass and show water replacement count is calculated correctly (2-4 water molecules replaced in tests)
  implication: Logic works in isolation, issue is specific to user scenario

- timestamp: 2026-05-09T00:00:00Z
  checked: Git history after commit c66a109
  found: No changes to main_window.py after c66a109. Commits cb04af9 and c89b81b fixed MoleculeIndex issues in custom_molecule_inserter.py but did not affect water count logic
  implication: Code hasn't been modified since fix was applied

- timestamp: 2026-05-09T00:00:00Z
  checked: custom_molecule_inserter._remove_overlapping_water method
  found: Method correctly creates new InterfaceStructure with updated water_nmolecules count (line 454). Returns modified structure that is stored in result.interface_structure
  implication: Water count tracking is correct in the inserter

- timestamp: 2026-05-09T00:00:00Z
  checked: test_comprehensive_water_count.py - tested 3 scenarios
  found: 
    - Scenario 1 (normal): Water count shown correctly (3 waters replaced)
    - Scenario 2 (no interface): water_replaced=0, no message shown
    - Scenario 3 (no overlaps): water_replaced=0, no message shown
  implication: The logic works, but user could be hitting scenario 2 or 3. However, scenario 2 is blocked by validation (line 1071 checks for None and returns early). Scenario 3 would mean no water is actually replaced, but user says water replacement IS happening.

## Resolution

root_cause: Unable to reproduce issue - code is correct and all tests pass. The logic works correctly in all tested scenarios. The issue may be:
  1. Specific to user's molecule configuration or placement (no actual overlaps detected, water_replaced=0)
  2. An exception being caught silently before the water count calculation
  3. The user interface showing success but the calculation failing silently

fix: Added comprehensive debug logging to _on_custom_finished method to track:
  - Whether _current_interface_result exists
  - Values of original_water_count and modified_water_count
  - Calculation of water_replaced
  - Whether the water replacement message is logged
This will help diagnose the actual values in production when the issue occurs.

verification: Added test_comprehensive_water_count.py which passes all 3 scenarios. Debug logging added to main_window.py will provide visibility into what's happening in production.
files_changed: [quickice/gui/main_window.py]
