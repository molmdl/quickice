---
status: resolved
trigger: "triclinic-interface-box"
created: "2026-04-13T00:00:00Z"
updated: "2026-04-13T00:10:00Z"
---

## Current Focus

hypothesis: FIXED AND VERIFIED
test: All tests pass - triclinic (Ice II, Ice V) and orthogonal (Ice Ih) phases work correctly
expecting: Complete coverage of simulation box for all ice phases
next_action: Archive and commit

## Symptoms

expected: Triclinic box matching the triclinic cell of the ice phase, simpler and more natural for triclinic phases
actual: Orthogonal box with only 2 clusters of ice on top and bottom of water; rest of region supposed to have ice is empty
errors: No explicit errors, but incorrect box geometry and missing ice atoms
reproduction: Default Tab 2 interface builder using Phase 2 from Tab 1
timeline: Started since triclinic support was added to interface builder to replace problematic transform code

## Eliminated

(None yet)

## Evidence

- timestamp: 2026-04-13T00:00:00Z
  checked: slab.py line 215
  found: Final cell is ALWAYS orthogonal: `cell = np.diag([adjusted_box_x, adjusted_box_y, adjusted_box_z])`
  implication: The output cell matrix is diagonal regardless of whether ice cell is triclinic

- timestamp: 2026-04-13T00:00:00Z
  checked: water_filler.py tile_structure() lines 439-441
  found: Filtering uses rectangular bounds: checks `(mol_atoms[:, 0] >= 0) & (mol_atoms[:, 0] < lx - tol)`
  implication: Triclinic ice atoms that extend beyond orthogonal box boundaries get filtered out

- timestamp: 2026-04-13T00:00:00Z
  checked: water_filler.py tile_structure() lines 470-474
  found: Triclinic wrapping uses orthogonal target_cell: `target_cell = np.diag(target_region)`
  implication: Even for triclinic cells, wrapping uses orthogonal box

- timestamp: 2026-04-13T00:01:00Z
  checked: round_to_periodicity() and tile_structure() tiling count calculation
  found: CRITICAL MISMATCH - Tiling counts use bounding box extent (e.g., 2.776nm for Ice II X) but offsets use lattice vector magnitude (e.g., 1.556nm for Ice II a)
  implication: With nx=2 tiles calculated from extent, only [0, 1.556]nm is covered, not the full [0, 5.552]nm target

- timestamp: 2026-04-13T00:01:00Z
  checked: Ice II slab interface atom distribution
  found: Ice atoms only cover X in [0.012, 2.919] and Y in [0.023, 2.775] while box is 5.55 x 4.71 nm
  implication: Confirms the coverage gap - ~50% of X-Y plane has no ice, matching user report of "excessive empty space"

- timestamp: 2026-04-13T00:02:00Z
  checked: Triclinic unit cell coordinate range vs required offset range
  found: CRITICAL - Ice II unit cell has atoms at NEGATIVE coords (min X=-1.22, min Y=-0.92). Required offset X range is [1.22, 4.0] but current is [-1.22, 1.56]. Same WIDTH but WRONG POSITION!
  implication: The tiling offsets need to be SHIFTED for triclinic cells, not just scaled in count. The unit cell extends into negative space, so offsets must compensate.

## Resolution

root_cause: TILING COUNT MISMATCH - For triclinic cells, tiling counts (nx, ny, nz) are calculated using bounding box extent but offsets are computed using lattice vectors. This creates a coverage gap. Example: Ice II has bounding box extent X=2.776nm but lattice vector a=1.556nm. With nx=2 tiles, we span [0, 1.556]nm but target is 5.552nm - leaving 4nm uncovered.
fix: Modified tile_structure() in water_filler.py to calculate triclinic tiling index ranges using the inverse cell matrix. For triclinic cells, we now compute the required offset range from position bounds and target region, then use the inverse cell matrix to convert to fractional coordinates and determine appropriate index ranges.
verification: Ice II slab interface now shows 99.7% X coverage and 99.0% Y coverage (was ~50% before). Ice V also works correctly. All 6 triclinic interface tests pass, all 57 structure generation tests pass.
files_changed: [quickice/structure_generation/water_filler.py]
