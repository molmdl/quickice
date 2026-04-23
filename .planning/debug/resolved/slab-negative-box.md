---
status: resolved
trigger: "Negative input data are outside of the periodic box"
created: 2026-04-23T00:00:00Z
updated: 2026-04-23T01:30:00Z
---

## Current Focus
FIXED - Root cause found and fixed

## Root Cause
Two issues were found and fixed:

1. **Primary Issue**: `scipy.spatial.cKDTree` requires non-negative coordinates when using the `boxsize` parameter. When hydrate candidates have positions outside [0, box) due to tiling/shifting operations, the cKDTree throws `ValueError: "Negative input data are outside of the periodic box."`

2. **Secondary Issue**: When pressure=0 is passed to `IAPWS95()`, it returns `rho=None`, which causes a `TypeError` when comparing `if 100 < rho < 2000`.

## Fix Applied

1. **overlap_resolver.py** - Added coordinate wrapping before cKDTree:
   ```python
   # CRITICAL: Wrap coordinates to [0, box) before passing to cKDTree
   box = np.asarray(box_dims_nm)
   ice_wrapped = np.mod(ice_o_positions_nm, box)  # Handle negative values
   water_wrapped = np.mod(water_o_positions_nm, box)
   ```

2. **water_density.py** - Added None check for IAPWS95 with P=0:
   ```python
   if rho is None:
       return FALLBACK_DENSITY_GCM3 * 1000
   ```
   Also added `TypeError` to exception handling.

## Verification
- All 310 tests pass
- Manual test with negative coordinate candidate succeeds

## Symptoms
expected: Slab mode generates structure with valid coordinates within box bounds
actual: Error "Negative input data are outside of the periodic box"
errors:
  - "Failed to generate interface structure: [slab] Unexpected error during slab mode generation: Negative input data are outside of the periodic box."
reproduction: Hydrate → Interface → Select "Hydrate Structure" → Slab mode → Click Generate
started: after previous hang fix that changed hydrate processing in slab/piece modes
files_involved:
  - quickice/structure_generation/modes/slab.py
  - quickice/structure_generation/modes/piece.py

## Eliminated

## Evidence
<!-- APPEND only - facts discovered -->
- timestamp: 2026-04-23T00:30:00Z
  checked: water_filler.py get_cell_extent function
  found: function calculates bounding box extent using all 8 corners of the cell parallelepiped
  implication: should work correctly for both orthogonal and triclinic cells

- timestamp: 2026-04-23T00:35:00Z
  checked: tile_structure function in water_filler.py
  found: Has comprehensive PBC wrapping logic for both triclinic and orthogonal cells
  implication: wrapping is handled, but might not cover all edge cases

- timestamp: 2026-04-23T00:40:00Z
  checked: slab.py and piece.py with hydrate detection
  found: Code correctly extracts water framework positions for tiling, adds guests separately
  implication: Logic looks correct for hydrate handling

- timestamp: 2026-04-23T00:45:00Z
  checked: Simple test case with hydrate candidate → slab mode
  found: Test passes with simple orthogonal cell and 3x3x3 water grid + CH4
  implication: Basic logic works for simple cases

- timestamp: 2026-04-23T00:50:00Z
  checked: Error source search - grep for "Negative", "outside of the periodic box"
  found: Error message not found in codebase - appears to be from external tool or library
  implication: Error likely occurs during GROMACS export or after generation completes

- timestamp: 2026-04-23T00:55:00Z
  checked: write_interface_gro_file function in gromacs_writer.py
  found: Function handles coordinate writing to .gro format with proper formatting
  implication: GROMACS export might be the source of the error if coordinates are out of bounds

- timestamp: 2026-04-23T01:05:00Z
  checked: Full interface generation with negative coordinate hydrate candidate
  found: **ROOT CAUSE FOUND** - ValueError: "Negative input data are outside of the periodic box" comes from scipy.spatial.cKDTree in overlap_resolver.py detect_overlaps() function when ice/water positions have negative coordinates
  implication: The fix from commit 40bb120 doesn't wrap hydrate positions before passing to detect_overlaps()

- timestamp: 2026-04-23T01:10:00Z
  checked: water_density.py with pressure=0
  found: IAPWS95 returns rho=None for P=0, causing TypeError in comparison
  implication: Need to handle None case for rho

- timestamp: 2026-04-23T01:25:00Z
  checked: After fix verification
  found: All 310 tests pass with both fixes applied
  implication: Fixes are complete and correct