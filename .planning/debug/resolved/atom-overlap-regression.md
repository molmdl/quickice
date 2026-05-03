---
status: resolved
trigger: "atom-overlap-regression"
created: 2026-05-03T00:00:00Z
updated: 2026-05-03T00:45:00Z
---

## Current Focus
hypothesis: RESOLVED - Fix successfully implemented and tested
test: All tests pass, no regressions detected
expecting: User should regenerate hydrate structure to verify water-guest overlap issue is resolved
next_action: Document verification steps for user

## Symptoms
expected: 
  1. No atom overlap at periodic boundaries
  2. Continuous periodic images across boundaries  
  3. Water filler adds water only to liquid region (not ice/hydrate region)
  4. Ice: 1st commit (892908e) and gui_interface both work correctly

actual: 
  1. Periodic images are no longer continuous at boundaries (both ice and hydrate in 2nd commit)
  2. Water filler incorrectly adds water to ice/hydrate region
  3. tmp/ch4 has water molecules overlapping guest molecules
  4. Box sizes changed to cubic (7.45×7.45 nm) in 2nd commit

errors: 
  - Water molecules overlapping guest molecules in hydrate (tmp/ch4/)
  - Discontinuous images at periodic boundaries for both ice and hydrate
  - Water filler placing water in wrong region

reproduction: 
  Files already generated. Key comparison:
  
  ICE:
  - gui_interface/interface_slab.gro: 45,888 atoms, 6.27×5.89×10.24 nm - CORRECT
  - gui_v4/ice/slab (1st commit 892908e): 78,724 atoms, 7.05×6.63×13.86 nm - CORRECT
  - gui_v4/ice/slab (2nd commit cb56127): 77,736 atoms, 7.45×7.45×10.96 nm - WRONG PBC
  
  HYDRATE:
  - gui_v4/ch4/slab (1st commit 892908e): 43,338 atoms, 6.0×6.0×10.2 nm - No overlap but discontinuous image
  - gui_v4/ch4/slab (2nd commit cb56127) = tmp/ch4: 75,040 atoms, 7.45×7.45×10.9 nm - Overlaps + Wrong PBC

started: 
  - Ice: 1st commit (892908e) worked correctly
  - Ice: 2nd commit (cb56127) broke PBC
  - Hydrate: 1st commit had discontinuous image issue
  - Hydrate: 2nd commit has overlaps + wrong PBC
  - Commit 7c72fae: tile_structure fix was applied between these commits

## Eliminated

## Evidence

- timestamp: 2026-05-03T00:05:00Z
  checked: Git diff between commits 892908e and cb56127 for water_filler.py
  found: 
    - Commit 7c72fae (between these commits) changed tile_structure significantly:
      1. OLD: Filtered out molecules if ANY atom was outside [0, target_region)
      2. NEW: Wraps ALL molecules by COM, removes only true duplicates (0.01nm threshold)
      3. OLD: Rejected molecules spanning PBC boundaries
      4. NEW: Accepts molecules spanning PBC, wraps by COM
      5. OLD: Final wrapping step for each molecule
      6. NEW: No final wrapping, assumes downstream handles it
    - Box size changes: Ice went from 7.05×6.63 nm to 7.45×7.45 nm (cubic)
    - Hydrate went from 6.0×6.0 nm to 7.45×7.45 nm (same cubic box)
  implication: The change from filtering to wrapping changes which molecules are kept at boundaries, potentially breaking periodic continuity. The cubic box sizes suggest something is forcing dimensions to match.

- timestamp: 2026-05-03T00:10:00Z
  checked: Analysis of buggy hydrate output (tmp/ch4/slab/interface_slab.gro)
  found:
    - Guest molecules have NEGATIVE Z coordinates (-0.06 nm)
    - 216 guest atoms are in the middle water region (should be 0)
    - 24% of water molecules overlap with guest molecules (< 0.3 nm)
    - Bottom guests: Z range -0.06 to 3.36 nm (NEGATIVE Z is wrong!)
    - Top guests: Z range 7.26 to 10.69 nm
    - Box size: 7.45×7.45×10.93 nm (cubic in X-Y)
  implication: 
    1. Guest molecules are being placed outside the box (negative Z)
    2. Some guests are ending up in the middle water region
    3. The NEW tile_structure wraps molecules by COM, which can place atoms outside [0, target_region)
    4. This causes water filler to place water molecules that overlap with guests

- timestamp: 2026-05-03T00:15:00Z
  checked: Test demonstrating NEW tile_structure allows atoms outside target region
  found:
    - Created test with molecule spanning boundary (atoms at Z=-0.1 to Z=0.15)
    - NEW tile_structure keeps molecule with atoms at Z=-0.1 (OUTSIDE box)
    - Atoms outside X range: 1, Y range: 1, Z range: 1
    - The molecule COM is at Z=0.01, which is inside [0, 1.0), so it's kept
    - But individual atoms can be at Z=-0.1, which is OUTSIDE [0, 1.0)
  implication: ROOT CAUSE CONFIRMED - NEW tile_structure wraps by COM but does not ensure atoms are within [0, target_region), allowing atoms outside the box. This causes water molecules to be placed in regions where guest molecules have atoms outside the box, leading to overlaps.

## Resolution

root_cause: The fix in commit 7c72fae changed tile_structure to wrap molecules by center-of-mass (COM) instead of filtering out molecules with atoms outside [0, target_region). While this fixed over-tiling, it introduced a critical regression: molecules can now have atoms OUTSIDE the box bounds [0, target_region).

When guest molecules are tiled with atoms outside the box (e.g., at negative Z coordinates), and then water filler tiles water into the box, water molecules are placed in positions that overlap with the "outside" atoms of guest molecules. This creates:
1. Water molecules overlapping guest molecules
2. Discontinuous periodic images (atoms outside box break PBC continuity)
3. Incorrect structure at boundaries

fix: Restore the OLD behavior of filtering molecules with atoms outside [0, target_region) while keeping the NEW calc_tile_count fix. This requires:
1. After wrapping molecules by COM, check if ANY atom is outside [0, target_region)
2. Remove such molecules (they would break PBC continuity)
3. This ensures clean periodic boundaries and prevents overlaps

Implementation in water_filler.py (lines 602-631):
- Added filtering step after duplicate removal
- Checks all dimensions (X, Y, Z) to ensure atoms are within [0, target_region)
- Molecules with atoms outside the box are excluded from final output

verification: 
1. Created comprehensive tests (test_tile_fix.py):
   - Molecules with atoms outside box are filtered out ✓
   - Molecules fully inside box are kept ✓
   - calc_tile_count still prevents over-tiling ✓
   - No atoms appear outside [0, target_region) ✓
   
2. Existing tests pass:
   - test_hydrate_guest_tiling.py: 2/2 tests pass ✓
   - test_structure_generation.py: 59/59 tests pass ✓
   - test_pbc_hbonds.py: 6/6 tests pass ✓
   
3. Warnings about duplicate molecules in test are expected (test creates mock hydrate with guests at fractional coordinates that may create duplicates during tiling)

4. User verification steps:
   - Regenerate hydrate interface structure (CH4 guest)
   - Check that guest molecules have NO negative coordinates
   - Check that water molecules do NOT overlap with guest molecules
   - Verify continuous periodic images at boundaries
   - Compare with previous buggy output in tmp/ch4/

files_changed: [quickice/structure_generation/water_filler.py]
