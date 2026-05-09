---
status: investigating
trigger: "water-replacement-not-happening"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:03Z
---

## Current Focus

hypothesis: Tests prove the logic works correctly (14 water molecules replaced in realistic test), so the issue must be in how the user is running the code - either the debug logs aren't being seen, or there's a specific data issue
test: Create test_water_replacement_debug.py with realistic interface (ice + liquid water) to verify overlap detection and water removal
expecting: Test confirms 14 water molecules replaced, proving the logic works end-to-end
next_action: The code is correct. Need to ask user for the debug logs to see what's actually happening in their specific case

## Symptoms

expected: When custom molecules are placed in random mode into a liquid water region (which is filled with water), water molecules should be replaced and the count should be displayed
actual: Insertion completes successfully, viewer shows results, but no water replacement count is displayed. User confirms this is impossible - the liquid region is filled with water, so overlaps MUST occur
errors: No error message, but water replacement may not be happening at all, or the count is not being tracked correctly
reproduction: 
  1. Load interface structure with liquid water region
  2. Insert custom molecules using random mode into the liquid region
  3. Completion shows no water replacement count
started: Current issue

## Eliminated

- hypothesis: _remove_overlapping_water() not being called
  evidence: Code shows it's called in both place_random() and place_custom() at lines 582 and 739
  timestamp: 2026-05-09T00:00:01Z

- hypothesis: interface_structure not being returned correctly
  evidence: Both place_random() and place_custom() return CustomMoleculeStructure with interface_structure=modified_structure
  timestamp: 2026-05-09T00:00:01Z

- hypothesis: water_nmolecules not being updated correctly
  evidence: _remove_overlapping_water() creates new InterfaceStructure with water_nmolecules=new_water_nmolecules at line 454
  timestamp: 2026-05-09T00:00:01Z

- hypothesis: main_window.py logic is broken
  evidence: test_comprehensive_water_count.py shows the exact logic works perfectly - Scenario 1 shows 4 water molecules replaced and message displayed
  timestamp: 2026-05-09T00:00:01Z

- hypothesis: Overlap detection is broken
  evidence: test_water_replacement_debug.py shows 14 water molecules replaced from 100 original, proving overlap detection works correctly
  timestamp: 2026-05-09T00:00:02Z

## Evidence

- timestamp: 2026-05-09T00:00:00Z
  checked: User provided critical context
  found: Liquid water region IS filled with water, overlaps MUST occur
  implication: Either water removal is not happening, OR water_nmolecules is not being updated, OR count comparison is wrong

- timestamp: 2026-05-09T00:00:01Z
  checked: custom_molecule_inserter.py lines 285-459 (_remove_overlapping_water method)
  found: Method correctly removes overlapping water molecules and creates new InterfaceStructure with updated water_nmolecules
  implication: Water replacement logic is implemented correctly

- timestamp: 2026-05-09T00:00:01Z
  checked: custom_molecule_inserter.py lines 582, 739 (calls to _remove_overlapping_water)
  found: Both place_random() and place_custom() call _remove_overlapping_water and return CustomMoleculeStructure with interface_structure=modified_structure
  implication: Modified structure with updated water count is being returned

- timestamp: 2026-05-09T00:00:01Z
  checked: main_window.py lines 1180-1229 (_on_custom_finished method)
  found: Method has correct logic to calculate water_replaced = original_water_count - modified_water_count and log if > 0
  implication: Display logic is implemented correctly

- timestamp: 2026-05-09T00:00:01Z
  checked: test_comprehensive_water_count.py (Scenario 1)
  found: Test shows 4 water molecules replaced, and message WOULD be displayed
  implication: THE LOGIC WORKS! Issue is specific to user's workflow or data

- timestamp: 2026-05-09T00:00:02Z
  checked: test_water_replacement_debug.py (realistic interface with ice + liquid water)
  found: Test shows 14 water molecules replaced from 100 original water molecules
  implication: CONFIRMED - The entire water replacement pipeline works correctly end-to-end. The issue must be in the user's specific scenario or they're not seeing the debug logs.

## Resolution

root_cause: 
fix: 
verification: 
files_changed: []
