---
status: resolved
trigger: "Debug: Slab mode PBC overlap for Ic, VII, VIII (orthogonal phases)"
created: 2026-04-10T00:00:00Z
updated: 2026-04-10T01:00:00Z
---

## Current Focus
hypothesis: Fixed - wrapping logic now has second pass to ensure all atoms within [0, target_region)
test: Run slab mode tests for all phases
expecting: All phases should successfully generate slab interfaces
next_action: Archive session

## Symptoms

expected: Slab works for all orthogonal phases
actual: Slab works for Ih, III; fails for Ic, VII, VIII
errors: Top ice atoms have Z >= box_z (outside box). box_z = 9.00 nm. 12 atoms have Z >= box_z for Ic.
reproduction: Load Ic candidate, try slab mode
started: Unknown - discovered during testing

## Eliminated

- hypothesis: Ic/VII/VIII have different z-position origins/ranges than Ih/III
  evidence: All phases have positions outside [0, cell_z), but wrapping logic fails for Ic/VII because H atoms can be negative while O is at boundary
  timestamp: 2026-04-10T00:00:00Z

## Evidence

- timestamp: 2026-04-10T00:00:00Z
  checked: GenIce output positions for different phases
  found: Ih: Z range [0.034, 1.769], all inside [0, cell_z). Ic: Z range [-0.054, 1.172], some atoms < 0. III: Z range [-0.060, 1.442], atoms outside [0, cell_z). VII: Z range [-0.054, 1.212], some atoms < 0.
  implication: GenIce outputs positions that can be outside [0, cell) - this is valid for periodic structures

- timestamp: 2026-04-10T00:00:00Z
  checked: tile_structure behavior for Ic
  found: After tiling to [0, 3] nm: Z range [-0.054, 3.052]. 12 atoms have Z >= 3.0 nm after wrapping.
  implication: Wrapping based on O atom position fails when O is at boundary and H atoms are negative relative to O

- timestamp: 2026-04-10T00:00:00Z
  checked: Traced specific molecule (Molecule 8 for Ic)
  found: Original: O at Z=0.0, H1 at Z=0.054, H2 at Z=-0.054. After tiling and wrapping: O at 0.0, H1 at 0.054, H2 at -0.054 (still negative!). Wrapping uses O position (floor(0/3)=0), so no shift applied.
  implication: Wrapping based only on O position leaves H atoms outside [0, lz) when O is near boundary and H atoms extend in negative direction

- timestamp: 2026-04-10T01:00:00Z
  checked: Implemented second pass in wrapping logic
  found: Added check after initial shift to apply additional +/-target_region shift if atoms still outside [0, target_region)
  implication: Fixes edge cases where first shift pushed atoms out the other side

- timestamp: 2026-04-10T01:00:00Z
  checked: Ran slab mode tests for all phases
  found: All phases (Ih, III, Ic, VII, VIII) now successfully generate slab interfaces. Final Z ranges all within [0, 9.0) nm.
  implication: Fix is working correctly

## Resolution

root_cause: tile_structure wraps molecules based on min/max atom positions using if-elif structure. When min_pos < 0, a shift is applied to bring atoms up, but this can push max_pos >= target_region, creating atoms outside the box. The if-elif structure meant only one correction was applied, not both.

fix: Added second pass in wrapping logic (lines 269-279 in water_filler.py). After applying initial shift based on min_pos or max_pos, the code now checks again for atoms outside [0, target_region) and applies an additional +/-target_region shift if needed. This handles edge cases where the first shift pushed atoms out the other side.

verification: 
- Ran test_slab_modes.py: All 5 phases (Ih, III, Ic, VII, VIII) now successfully generate slab interfaces
- Ran test_high05_slab_pbc.py: All 3 tests pass (atoms within bounds, thin water layer, top ice positions)
- Ran full test suite (247 tests): All pass (excluding pre-existing CLI integration test failures)

files_changed:
- quickice/structure_generation/water_filler.py: Added second pass in wrapping logic to ensure all atoms within [0, target_region) after initial shift
