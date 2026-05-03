---
status: resolved
trigger: "Fix issue: water-filler-wrapping - Revert the wrapping logic in water_filler.py from COM-based back to min/max-based"
created: 2026-05-03T00:00:00Z
updated: 2026-05-03T00:00:00Z
---

## Current Focus

hypothesis: (resolved)
test: (resolved)
expecting: (resolved)
next_action: Archive session

## Symptoms

expected: |
  1. Liquid water with NO overlaps (correct O-O spacing ~0.28nm)
  2. Working version: commit 892908e

actual: |
  1. Liquid water has 6,074 overlapping pairs (1,266 severe)
  2. Minimum O-O distances: 0.03-0.05 nm (crazy!)

errors: None

reproduction: |
  The issue is in quickice/structure_generation/water_filler.py
  
  Working version (892908e) uses min/max-based wrapping.
  Current version uses COM-based wrapping.

started: After commit 892908e

## Eliminated

(none - fix was straightforward revert)

## Evidence

- timestamp: 2026-05-03T00:00:00Z
  checked: Current water_filler.py lines 528-664
  found: COM-based wrapping logic that wraps molecules based on center of mass first, then filters
  implication: This approach doesn't preserve molecular integrity for molecules spanning PBC boundaries

- timestamp: 2026-05-03T00:00:00Z
  checked: Working version from commit 892908e
  found: Min/max-based wrapping that filters molecules first, then wraps based on min/max position
  implication: This approach properly preserves molecular integrity

- timestamp: 2026-05-03T00:00:00Z
  checked: After applying fix
  found: All tests pass (59 structure generation, 10 water density, 5 molecule wrapping, 6 PBC hbonds, 8 triclinic/hydrate)
  implication: Fix is verified and doesn't break existing functionality

## Resolution

root_cause: COM-based wrapping doesn't properly handle molecules that span PBC boundaries. The working version filters molecules first (keeping only those fully inside the box), then wraps them as units based on min/max position, which correctly preserves molecular geometry.

fix: Replaced lines 528-664 in water_filler.py with the working version from commit 892908e. The key differences are:
1. Filter molecules FIRST based on whether ALL atoms are inside the box
2. Then wrap molecules based on min/max position (not COM)
3. For triclinic cells, use wrap_positions_triclinic with the target orthogonal box

verification: All tests pass:
- 59 structure generation tests
- 10 water density tests
- 5 molecule wrapping tests
- 6 PBC hydrogen bonds tests
- 8 triclinic/hydrate tiling tests

files_changed:
- quickice/structure_generation/water_filler.py: Reverted wrapping logic from COM-based to min/max-based
