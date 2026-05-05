---
status: resolved
trigger: "thf-ion-solute-issues"
created: 2026-05-05T00:00:00Z
updated: 2026-05-05T00:00:00Z
---

## Current Focus
hypothesis: Three root causes identified for three issues
test: Fix all three issues with minimal changes
expecting: All three symptoms resolved
next_action: Implement fixes

## Root Causes Found

### Issue 1 - THF solute bonds wrong:
**Location:** solute_renderer.py lines 152-153
**Problem:** When MW atoms are skipped (lines 128-129), visible_positions becomes shorter than original positions array, but molecule_indices still uses original indices
**Impact:** Incorrect slicing causes bonds to be detected between wrong atoms

### Issue 2 - Water replacement message:
**Location:** main_window.py line 959
**Problem:** Message says "Water replacement: Removed N water molecules to make room"
**Impact:** Not clear and concise enough
**Fix:** Change to "Replaced N overlapping liquid water molecules"

### Issue 3 - Ion panel not showing solutes:
**Location:** main_window.py lines 902-903
**Problem:** When "Solute" source is selected, only interface is rendered, but solutes themselves are not rendered
**Impact:** Solute molecules not visible in ion viewer
**Fix:** Add solute rendering when source is "Solute"

## Symptoms
expected: 
1. THF solute molecules in liquid phase should have correct bonds (same as hydrate THF)
2. Log message should say "replaced N overlapping liquid water" (clear and concise)
3. Ion panel with "Solute" source should show solute molecules in the viewer

actual: 
1. THF solute bonds are STILL wrong despite previous fix (hydrate THF is correct, solute THF is wrong)
2. Need to revise water replacement message wording
3. Ion panel selecting "Solute" source still doesn't show solutes in viewer

errors: No errors
reproduction: 
1. Insert THF solute, check bonds in viewer - still wrong
2. Check water replacement log message
3. Insert solute, go to ion tab, select "Solute" source, check viewer

started: Previous fixes didn't resolve the issues

## Eliminated

## Evidence
- timestamp: initial
  checked: SoluteStructure class definition
  found: molecule_indices is defined as list[tuple[int, int]] and is properly populated
  implication: molecule_indices itself is not the issue

- timestamp: initial
  checked: solute_viewer.py render_solute() method
  found: Lines 408-413 correctly pass molecule_indices to create_solute_actor()
  implication: molecule_indices is being passed correctly

- timestamp: initial
  checked: solute_inserter.py molecule creation
  found: Line 637 creates molecule_indices correctly based on current_idx, lines 684-693 pass it to SoluteStructure
  implication: molecule_indices is populated and passed correctly through the whole chain

- timestamp: initial
  checked: solute_renderer.py create_solute_actor() implementation
  found: BUG at lines 152-153! When MW atoms are skipped (lines 128-129), visible_positions becomes shorter than original positions array. But molecule_indices still uses original indices, causing wrong slicing
  implication: This is the root cause of Issue 1 - incorrect bond detection due to index mismatch

## Resolution
root_cause: Three separate issues identified and fixed:
1. THF solute bonds: solute_renderer.py used incorrect index mapping when MW atoms were skipped
2. Water replacement message: Unclear wording
3. Ion panel solutes: Solute molecules not rendered when "Solute" source selected
fix: 
1. Fixed index mapping in solute_renderer.py by tracking original_to_visible_idx mapping
2. Updated message to "Replaced N overlapping liquid water molecules"
3. Added solute rendering to main_window.py when source is "Solute" and proper cleanup in ion_viewer.py
verification: 
- All automated tests pass (test_thf_ion_solute_fixes.py)
- Cross-molecule bond prevention verified (test_cross_molecule_bonds.py)
- Index mapping correctly handles MW virtual sites
- No syntax errors in modified files
files_changed:
- quickice/gui/solute_renderer.py: Fixed index mapping for bond detection with MW atoms
- quickice/gui/main_window.py: Updated water message, added solute rendering for ion panel
- quickice/gui/ion_viewer.py: Added solute actor support and cleanup
