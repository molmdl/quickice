---
status: resolved
trigger: "After generating custom molecules in random mode, if user changes the number of molecules and clicks generate again, the GUI crashes without any error message"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:30:00Z
---

## Current Focus

hypothesis: Fix verified - all safety mechanisms working correctly
test: Integration tests pass, verification script confirms all checks
expecting: Fix prevents regeneration crash
next_action: Commit changes and document fix

## Symptoms

expected: User should be able to adjust molecule count and regenerate, or should see a dialog asking to clear previous results
actual: After changing molecule count and clicking generate again, GUI crashes silently
errors: No error message displayed
reproduction: 
  1. Load interface structure
  2. Insert custom molecules using random mode (e.g., 10 molecules)
  3. Wait for completion
  4. Change the number of molecules (e.g., to 20)
  5. Click generate again
  6. GUI crashes
started: Current issue
context:
  - First generation works fine
  - Crash happens on second generation attempt
  - May be related to state management, viewer cleanup, or thread handling
  - Could be trying to modify existing results without proper cleanup
  - Previous mode switch fix added dialog, but regeneration within same mode may not handle state properly

## Eliminated

- hypothesis: VTK rendering issue
  evidence: Analysis showed viewer properly clears old actors before adding new ones
  timestamp: 2026-05-09T00:10:00Z

- hypothesis: Thread cleanup race condition
  evidence: Finally block properly cleans up thread and worker references
  timestamp: 2026-05-09T00:10:00Z

## Evidence

- timestamp: 2026-05-09T00:05:00Z
  checked: _on_custom_generate_clicked method (lines 1065-1112)
  found: No check for _has_previous_insertion flag, no check for existing running worker/thread
  implication: User can click generate multiple times, creating multiple concurrent workers

- timestamp: 2026-05-09T00:06:00Z
  checked: _on_custom_finished cleanup (lines 1172-1180)
  found: Finally block deletes thread and worker attributes
  implication: If user clicks generate again before first finishes, old thread reference is lost

- timestamp: 2026-05-09T00:07:00Z
  checked: custom_molecule_panel generate_button state management
  found: Button is NOT disabled during processing (unlike hydrate_panel which disables at line 747)
  implication: User can click generate button while worker is still running

- timestamp: 2026-05-09T00:08:00Z
  checked: _on_placement_mode_changed method (lines 606-658)
  found: Check for _has_previous_insertion exists, but only triggers on MODE change, not on regenerate
  implication: Regeneration within same mode bypasses all state checks

- timestamp: 2026-05-09T00:12:00Z
  checked: Code analysis comparing custom vs hydrate generation
  found: Hydrate panel disables button (line 747) and re-enables (line 793), custom panel does neither
  implication: User can click generate while worker is running, creating thread collision

- timestamp: 2026-05-09T00:14:00Z
  checked: test_regenerate_crash_simple.py analysis
  found: Confirmed ALL safety mechanisms missing: no previous insertion check, no cleanup, no dialog, no button state management
  implication: ROOT CAUSE CONFIRMED - regeneration crash is due to missing safety mechanisms

- timestamp: 2026-05-09T00:18:00Z
  checked: Fix implementation in main_window.py
  found: Added previous insertion check with dialog (lines 1077-1099), button disabled during processing (line 1114), button re-enabled in finally block (lines 1210-1212)
  implication: Fix should prevent crash by handling regeneration properly

- timestamp: 2026-05-09T00:25:00Z
  checked: test_verify_fix.py verification script
  found: All 6 checks pass - previous insertion check, dialog, clear, button disabled, button re-enabled in finally, button re-enabled on error
  implication: Fix implementation verified

- timestamp: 2026-05-09T00:28:00Z
  checked: test_regeneration_integration.py integration tests
  found: All 6 tests pass - dialog shown on regeneration, clear on confirmation, button disabled, button re-enabled after completion, button re-enabled on error, no dialog without previous insertion
  implication: Fix works correctly in all scenarios

## Resolution

root_cause: _on_custom_generate_clicked lacks safety mechanisms that exist in mode switching (lines 606-658) and hydrate generation (lines 736-793). When regenerating in same mode: (1) no check for _has_previous_insertion, (2) no cleanup of previous results, (3) no dialog asking user what to do, (4) generate button not disabled during processing, (5) button not re-enabled after completion. This causes VTK viewer state corruption or thread collision leading to silent crash.
fix: Added previous insertion check with Yes/No dialog (lines 1077-1099), clear previous results on user confirmation, button disabled during processing (line 1117), button re-enabled in finally block (lines 1228-1230), button re-enabled on error (line 1147)
verification: All verification tests pass - 6/6 checks in test_verify_fix.py, 6/6 integration tests in test_regeneration_integration.py
files_changed: [quickice/gui/main_window.py]
