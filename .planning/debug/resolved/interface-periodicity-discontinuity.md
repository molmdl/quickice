---
status: resolved
trigger: "The interface builder failed to account for periodicity of ice units, resulting discontinued boundary between periodic images. while the tab 1 unit cell from genice can give continuous image. This should be here since the interface builder introduced in v3 gui. suggest to allow buffer in final box size and/or layer thickness with report on the adjustment in info dialog to ensure continuous image."
created: 2026-04-12T00:00:00Z
updated: 2026-04-12T00:00:00Z
---

## Current Focus
hypothesis: CONFIRMED - tile_structure filters molecules extending past box boundary, creating gaps when box dimensions don't align with ice unit cell dimensions
test: All interface tests pass with fix
expecting: Continuous periodic images after fix
next_action: Run full test suite to verify no regressions

## Symptoms
expected: Continuous boundary between periodic images (like genice produces with tab 1 unit cell - images should tile seamlessly without gaps)
actual: Broken continuity - discontinued boundary between periodic images, broken hexagons visible in hexagonal Ih ice phase
errors: No error messages - purely visual discontinuity issue
reproduction: Build interface using the v3 GUI interface builder with hexagonal Ih ice. Broken hexagons are very obvious at the boundaries. Likely affects other ice phases as well.
started: Since v3 GUI interface builder was introduced - never worked correctly since then

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
- timestamp: 2026-04-12T00:00:00Z
  checked: interface_builder.py, interface_panel.py, slab.py, water_filler.py
  found: tile_structure calculates nx=ceil(target_x/cell_x) tiles, then filters molecules extending past boundary
  implication: When box dimensions don't align with ice unit cell, last partial unit cell molecules are removed, creating gaps

- timestamp: 2026-04-12T00:00:00Z
  checked: water_filler.py lines 251-263
  found: Molecule filtering logic: keep only if ALL atoms are inside [0, target_region)
  implication: Molecules in last partial tile extending past boundary are removed, not wrapped

- timestamp: 2026-04-12T00:00:00Z
  checked: Concrete calculation with box_x=5.0nm, ice_cell=0.893nm
  found: nx=6 tiles cover 5.358nm, gap=0.358nm (7.2% of box, 40% of last tile filtered)
  implication: Significant discontinuity at periodic boundary

- timestamp: 2026-04-12T00:00:00Z
  checked: After fix applied - verification test
  found: Box dimensions adjusted to multiples of ice unit cell (e.g., 5.0nm → 6.266nm = 4 x 1.566nm ice cell)
  implication: Periodicity check passes - continuous images guaranteed

## Resolution
root_cause: tile_structure() filters out molecules that extend past the target box boundary instead of wrapping them. When box dimensions don't align with ice unit cell dimensions, this creates gaps at periodic boundaries.
fix: Added round_to_periodicity() function to adjust box dimensions and layer thickness to be multiples of ice unit cell dimensions. Adjustments reported in InterfaceStructure.report. Applied to slab and pocket modes.
verification: All interface tests pass. Periodicity verification confirms box dimensions are exact multiples of ice unit cell dimensions.
files_changed:
- quickice/structure_generation/water_filler.py: Added round_to_periodicity() function
- quickice/structure_generation/modes/slab.py: Apply periodicity adjustment to box_x, box_y, ice_thickness
- quickice/structure_generation/modes/pocket.py: Apply periodicity adjustment to box_x, box_y, box_z
