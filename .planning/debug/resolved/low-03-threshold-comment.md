---
status: resolved
trigger: "LOW-03 threshold-comment-mismatch - Docstring says overlap threshold is 'informational' but it's actually used"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:04:00Z
---

## Current Focus
hypothesis: The overlap_threshold_nm parameter is unused dead code that should be removed
test: Verified parameter is never used in function body or passed to tile_structure
expecting: Confirm parameter serves no purpose
next_action: Verify fix by running tests and checking functionality

## Symptoms
expected: Docstring accurately describes parameter usage
actual: Docstring says "informational purposes" but parameter is used for overlap detection
errors: Confusing documentation for developers
reproduction: Read docstring, then read code - mismatch
started: Always had misleading comment

## Eliminated
- hypothesis: Parameter is passed to tile_structure and used
  evidence: tile_structure does not accept overlap_threshold parameter; fill_region_with_water never passes it
  timestamp: 2026-04-09T00:01:00Z

## Evidence
- timestamp: 2026-04-09T00:00:00Z
  checked: water_filler.py lines 239-284
  found: fill_region_with_water accepts overlap_threshold_nm parameter but does NOT use it in function body
  implication: Parameter is defined but not used internally - need to check call sites

- timestamp: 2026-04-09T00:00:30Z
  checked: All call sites (piece.py:92-95, pocket.py:111-114, slab.py:112-115)
  found: All three callers pass config.overlap_threshold to fill_region_with_water, but function ignores it
  implication: Parameter is passed but unused - dead code

- timestamp: 2026-04-09T00:00:45Z
  checked: piece.py:104-109, pocket.py:152-153, slab.py:129-134
  found: Callers use config.overlap_threshold separately with detect_overlaps after calling fill_region_with_water
  implication: Overlap detection happens at call site, not inside fill_region_with_water

- timestamp: 2026-04-09T00:00:50Z
  checked: git history (commit 3990afd)
  found: Parameter has existed since original commit and has NEVER been used in the function
  implication: This is legacy dead code, not a recent regression

- timestamp: 2026-04-09T00:02:30Z
  checked: All Python files compile successfully
  found: No syntax errors after removing parameter
  implication: Fix is syntactically correct

- timestamp: 2026-04-09T00:02:45Z
  checked: tests/test_structure_generation.py (57 tests), tests/test_piece_mode_validation.py (7 tests), tests/test_med03_minimum_box_size.py (12 tests)
  found: All 76 tests pass
  implication: Fix does not break existing functionality

- timestamp: 2026-04-09T00:03:00Z
  checked: Manual test of fill_region_with_water
  found: Function works correctly without overlap_threshold_nm parameter, generates 251 molecules for 2nm³ region
  implication: Fix is functionally correct

## Resolution
root_cause: The overlap_threshold_nm parameter in fill_region_with_water is dead code that has never been used. The function accepts the parameter but ignores it completely. Callers pass it but it serves no purpose. The docstring saying "informational purposes" is misleading - the parameter is actually unused. All overlap detection is handled separately by callers using detect_overlaps from overlap_resolver module.
fix: Removed the unused overlap_threshold_nm parameter from fill_region_with_water function signature and updated all three callers (piece.py, pocket.py, slab.py) to not pass this parameter. This eliminates dead code and removes confusing documentation.
verification: All 76 related tests pass. Manual testing confirms function works correctly without the parameter. Python files compile without errors.
files_changed: [quickice/structure_generation/water_filler.py, quickice/structure_generation/modes/piece.py, quickice/structure_generation/modes/pocket.py, quickice/structure_generation/modes/slab.py]

