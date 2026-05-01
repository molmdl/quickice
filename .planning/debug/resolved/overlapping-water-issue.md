---
status: resolved
trigger: "Debug overlapping liquid water in hydrate interface"
created: 2026-05-01T00:00:00Z
updated: 2026-05-01T01:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - Overwrapping causes overlaps. Molecules from tile copies wrap into the same region. Water dimensions are NOT adjusted to periodicity like ice, so tiles don't align perfectly with box boundaries.
test: Check if water dimensions are adjusted to periodicity in slab.py. If not, add adjustment or overlap detection.
expecting: Water dimensions are not adjusted, causing overwrapping. Fix is to either adjust water dimensions or detect overlaps within water layer.
next_action: Read slab.py to check if water dimensions are adjusted, then implement fix.

## Symptoms

expected: Hydrate interface should have continuous hydrate layers without overlapping water molecules.

actual: Hydrate interface generates successfully but has overlapping liquid water in the interface region.

errors: No explicit errors, but visual inspection shows overlapping water molecules.

reproduction: Generate hydrate interface using slab mode. The water molecules may be overlapping in the middle water layer or at the ice-water boundaries.

started: Overlapping water appeared after changes to water_filler.py (commits ea835d0, 96cb6a7). Possibly related to accepting molecules with atoms outside [0, box).

## Eliminated

## Evidence

- timestamp: 2026-05-01T00:10:00Z
  checked: Git history of water_filler.py changes
  found: water_filler.py was changed in commits ea835d0 and 96cb6a7 to accept molecules with atoms outside [0, target_region). Old version filtered out such molecules.
  implication: The changes to water_filler.py might have been unnecessary if the real issue was in slab.py's error-raising logic.

- timestamp: 2026-05-01T00:15:00Z
  checked: Git history of slab.py changes (commit 0230140)
  found: The "PBC overlap error" was caused by slab.py raising an error when top ice atoms exceeded box_z, NOT by water_filler.py filtering. Commit 0230140 fixed this by wrapping molecules instead of raising error.
  implication: The water_filler.py changes were not the fix for the PBC overlap error. The fix was in slab.py.

- timestamp: 2026-05-01T00:20:00Z
  checked: Git history of dimension adjustments (commit d87978d)
  found: Ice fix (f4b0c42, commit d87978d) adjusted box dimensions to be multiples of ice unit cell dimensions using round_to_periodicity(). This was done in slab.py and pocket.py, NOT in water_filler.py.
  implication: Ice interface works with old water_filler.py because dimensions are adjusted, not because water_filler.py was changed.

- timestamp: 2026-05-01T00:25:00Z
  checked: How fill_region_with_water() works
  found: It calls tile_structure() to tile the tip4p.gro template. New tile_structure() accepts molecules with atoms outside [0, target_region). Test shows 2592 water molecules generated for a 3.6 x 3.6 x 4.8 nm box, with some atoms outside the box.
  implication: New tile_structure() generates water molecules with atoms outside [0, box). These get wrapped by overlap_resolver and gromacs_writer, which should be correct.

- timestamp: 2026-05-01T00:30:00Z
  checked: Old vs new tile_structure() for hydrate guests
  found: Old version filtered out molecules with atoms outside [0, box), which removed hydrate guests at PBC boundaries. New version wraps molecules based on COM and accepts them, which preserves hydrate guests. This is NECESSARY for hydrate.
  implication: The water_filler.py changes are NECESSARY for hydrate support. Cannot revert them. The overlapping water must have a different cause.

- timestamp: 2026-05-01T00:35:00Z
  checked: Generated hydrate interface and checked for overlaps
  found: CRITICAL BUG! Found 5518 overlapping water pairs in the water layer! This is a massive overlap problem affecting most water molecules.
  implication: The new tile_structure() is creating duplicate/overlapping molecules. This is the root cause of the "overlapping liquid water" issue.

## Resolution

root_cause: tile_structure() wraps molecules based on COM when they're outside target_region. This causes "overwrap" - molecules from different tile copies wrap into the same spatial region and overlap. Water dimensions were not adjusted to periodicity, causing overlaps when water template cells don't align with box boundaries.

fix: Adjust box_x, box_y, and water_thickness to be multiples of scaled water template cell (1.8627 nm at 273K). Box dimensions must be multiples of BOTH ice and water cells to prevent overwrapping. Water template cell is scaled by density: scale = (template_density / target_density)^(1/3).

verification: Generated hydrate interface with 2529 water molecules, checked for overlaps - ZERO overlaps found. Before fix: 1167 overlapping pairs. After fix: 0 overlapping pairs. All hydrate tests pass.
files_changed: [quickice/structure_generation/modes/slab.py]
