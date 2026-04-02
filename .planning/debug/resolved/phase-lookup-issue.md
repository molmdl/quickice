---
status: investigating
trigger: "phase with no issue and correct citation: XI, Ih, IX, II; all other phases marked as boundary even when clicking in the middle since they are wrongly marked as boundary no citation"
created: 2026-04-02T00:00:00Z
updated: 2026-04-02T00:00:00Z
---

## Current Focus
hypothesis: `_check_near_boundary` function checks ALL phases with relative tolerance that's too large at high pressures
test: Verify that tolerance at high P (e.g., 62000 MPa) causes false boundary detection
expecting: At P=62000 MPa, tolerance=3100 MPa which incorrectly includes adjacent phases
next_action: Fix _check_near_boundary to only check the inside_phase boundary

## Symptoms
expected: All phases should be correctly identified with proper citations
actual: Only XI, Ih, IX, II phases work correctly; other phases marked as "boundary"
errors: No citation shown for incorrectly identified phases
reproduction: Click in the middle of a phase region that's not XI, Ih, IX, or II

## Eliminated
(empty)

## Evidence
- timestamp: 2026-04-02T00:00:00Z
  checked: `_check_near_boundary` function in phase_diagram_widget.py
  found: Function iterates over ALL phases, not just the inside_phase
  implication: When point is in Phase VI, it checks distance to ALL phase boundaries
  
- timestamp: 2026-04-02T00:00:00Z
  checked: Tolerance calculation `max(0.01, pressure * 0.05)`
  found: At P=62000 MPa (Ice VII/VIII region), tolerance = 3100 MPa
  implication: Huge tolerance causes false boundary detection for adjacent phases
  
- timestamp: 2026-04-02T00:00:00Z
  checked: Phases that work vs don't work
  found: XI, Ih, IX, II work (low P, tolerance < 50 MPa); V, VI, VII, VIII fail (high P, tolerance > 50 MPa)
  implication: Relative tolerance is the root cause

## Resolution
root_cause: `_check_near_boundary` function iterated over ALL phases with relative tolerance (pressure * 0.05), causing false boundary detection at high pressures. At P=62000 MPa, tolerance was 3100 MPa, which incorrectly marked any point near adjacent phase polygons as boundary.
fix: Rewrote `_check_near_boundary` to only check the inside_phase boundary with fixed 5 MPa tolerance. Added helper methods `_is_near_boundary`, `_find_adjacent_phase`, `_find_nearest_phase` for proper boundary detection.
verification: Tested all phases (XI, Ih, IX, II, V, VI, VII, VIII) - all now correctly identified without boundary flag. Boundary detection still works for actual boundary cases like Ih-II.
files_changed: [quickice/gui/phase_diagram_widget.py]
