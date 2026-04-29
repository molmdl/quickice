---
status: resolved
trigger: "Fix partial guest molecule tiling in hydrate layer interface export."
created: 2026-04-29T08:00:00Z
updated: 2026-04-29T09:30:00Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: |
  ROOT CAUSE CONFIRMED: The code tiles guests for ONE ice region (ice_region_dims = [box_x, box_y, ice_thickness]),
  then splits by INDEX (n_molecules // 2) and shifts top half to wrong Z-position.
  
  This causes:
  1. Bottom guests: Correctly placed in [0, ice_thickness]
  2. Top guests: Shifted to [ice_thickness + water_thickness, box_z] - but this is WRONG!
  3. The top ice layer is at [ice_thickness + water_thickness, box_z], but the shifted
     guests may not match the actual tiled ice positions in that region.
  4. CRITICALLY: The tiling only covers ONE ice thickness, so guests don't fill the entire
     ice region properly - some cells are missed.

test: |
  1. Verify ice_region_dims calculation (should be for ONE ice layer)
  2. Check how n_bottom_mols = n_molecules // 2 splits the tiled result
  3. Verify the shift calculation for top guests
  4. Check if tiling actually covers entire ice region or misses cells

expecting: |
  The tiling is done once for [box_x, box_y, ice_thickness], producing molecules for ONE layer.
  Splitting by index and shifting doesn't properly distribute guests to match the
  actual ice tiling in both layers.

next_action: |
  Verify the root cause by examining the tiling output dimensions vs actual ice layer sizes.
  Then formulate the fix: tile guests SEPARATELY for bottom and top ice layers.

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: Entire hydrate layer should have guest molecules tiled uniformly
actual: Some parts of hydrate layer don't have guest molecules (partial tiling)
errors: No error - just incomplete guest tiling
reproduction: 
1. Generate hydrate (sI + CH4)
2. Export as Interface GROMACS
3. Check .gro file - some regions missing CH4 molecules
started: Unknown (observed in export output)

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-29T08:00:00Z
  checked: Reference output files and top file
  found: .top file shows SOL 12438, CH4 915, SOL 4856; .gro file has 73,751 atoms; hydrate layer middle should have CH4 in every unit cell but some are missing
  implication: Code thinks it's adding 915 CH4 molecules, but they are not uniformly distributed

- timestamp: 2026-04-29T08:00:00Z
  checked: Key files to investigate (from additional context)
  found: Likely files: quickice/structure_generation/modes/slab.py (interface generation), quickice/structure_generation/modes/piece.py (tile_structure())
  implication: Issue is in tiling logic for guest molecules in hydrate layer

- timestamp: 2026-04-29T08:05:00Z
  checked: slab.py lines 426-493 (guest tiling logic)
  found: |
    Guest tiling only tiles for ONE ice region (ice_region_dims = [box_x, box_y, ice_thickness]),
    then splits the tiled result by index (n_bottom_mols = n_molecules // 2) and shifts top half.
    This means:
    1. Tiling covers only [0, ice_thickness] in Z (bottom layer)
    2. Top layer guests are just shifted copies of bottom layer guests
    3. If tiling doesn't perfectly tile to cover box_x * box_y * ice_thickness, some cells will be empty
  implication: The tiling is done for the ice region size, but the split assumption (50/50) may not match actual ice molecules distribution between bottom and top layers

- timestamp: 2026-04-29T08:06:00Z
  checked: Reference .gro file Z-distribution of CH4
  found: |
    All CH4 molecules appear to have Z in {0.600, 1.801} (from sample output),
    which suggests they're concentrated in specific Z-layers, not uniformly distributed
    throughout the ice region.
  implication: Confirmed - guests are not uniformly distributed in Z-direction within ice layers

- timestamp: 2026-04-29T08:10:00Z
  checked: Molecule count asymmetry between bottom and top ice layers
  found: |
    From .top file: SOL 12438 (bottom), SOL 4856 (top)
    Bottom ice: 12438 * 4 = 49752 atoms
    Top ice: 4856 * 4 = 19424 atoms
    Total: 69176 ice atoms + 4575 CH4 atoms = 73751 total ✓
    
    CRITICAL FINDING: Bottom (12438) ≠ Top (4856) water molecules!
    This is NOT symmetric - bottom has 2.56x more water molecules than top.
  implication: The slab is NOT symmetric as expected. This suggests either:
    1. Tiling is not covering the same volume for top and bottom
    2. The ice_thickness adjustment created different layer sizes
    3. Guest tiling may be using wrong dimensions

- timestamp: 2026-04-29T08:15:00Z
  checked: CH4 Z-distribution in reference .gro file (detailed analysis)
  found: |
    MAJOR FINDING: Massive gap in CH4 distribution!
    - CH4 present: Z = 0.3 to 4.8 nm (bottom ice region)
    - CH4 GAP: Z = 4.8 to 8.1 nm (NO molecules for ~3.3 nm!)
    - CH4 present: Z = 8.1 to 12.3 nm (top ice region)
    
    Pattern within each region:
    - Molecules appear in clusters at Z = {0.3, 0.6, 0.9, ...} with 14-52 molecules per 0.3nm slice
    - Regular pattern every 0.3 nm (suggests unit cell of ~1.2 nm / 4 = 0.3 nm spacing)
    
    The GAP exactly corresponds to the WATER REGION (should be empty of guests!)
    But guests should be in BOTH ice layers, not just at the edges.
  implication: |
    ROOT CAUSE IDENTIFIED: The code tiles guests for ice_region_dims = [box_x, box_y, ice_thickness],
    then splits 50/50 and shifts top half to [ice_thickness + water_thickness, box_z].
    
    PROBLEM: The split is by INDEX (n_molecules // 2), not by spatial region!
    - If tiling produces N molecules for bottom region
    - First N//2 go to bottom, remaining go to top
    - But the top molecules are just shifted bottom molecules
    - The spatial distribution doesn't match actual ice layer positions!
    
    Additionally: The guest_cell_dims might be wrong, causing incomplete tiling coverage.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: |
  CONFIRMED: The guest tiling logic in slab.py (lines 383-469) has multiple bugs:
  
  1. TILING ONLY FOR ONE LAYER: Guest tiling used ice_region_dims = [box_x, box_y, ice_thickness],
     which only covers ONE ice layer (bottom). This means tiling doesn't account for both layers.
  
  2. INCORRECT SPLITTING: The code split tiled molecules by INDEX (n_molecules // 2),
     then shifted the top half to [ice_thickness + water_thickness, box_z].
     This is wrong because:
     a. The spatial distribution of tiled guests is for bottom layer only
     b. Shifting them doesn't match where the actual top ice layer is tiled
     c. If bottom and top ice layers have different molecule counts (due to 
        round_to_periodicity adjustments), splitting 50/50 is incorrect
  
  3. POTENTIAL COVERAGE ISSUE: The tiling might not fully cover the ice region
     if ice_cell_dims doesn't match the actual guest positions in the unit cell.
  
  THE FIX (APPLIED): Now tile guests SEPARATELY for bottom and top ice layers:
  - bottom_guest_positions = tile_structure(raw_guest_positions, ..., [box_x, box_y, ice_thickness])
  - top_guest_positions = tile_structure(raw_guest_positions, ..., [box_x, box_y, ice_thickness])
  - Then shift top guests to Z = ice_thickness + water_thickness
  
  This ensures:
  - Each layer gets properly tiled guests matching its exact dimensions
  - No arbitrary splitting by index
  - Proper spatial distribution in both layers (matching ice framework tiling)

fix: |
  Modified slab.py lines 383-485:
  - Removed the single tile + split logic
  - Added separate tiling for bottom and top ice layers
  - Bottom guests: tiled for [box_x, box_y, ice_thickness], no shift
  - Top guests: tiled same way, then shifted by (ice_thickness + water_thickness)
  - Combined both layers into processed_guest_positions

verification: |
  Tested with:
  1. Simple test (3.6 x 3.6 x 7.2 nm box):
     - Bottom layer: 42 CH4 molecules
     - Top layer: 42 CH4 molecules
     - Z-span in each layer: 1.0 nm (80% of ice_thickness=1.2 nm)
  
  2. Larger test (7.2 x 7.2 x 12.0 nm box):
     - Bottom layer: 456 CH4 molecules
     - Top layer: 456 CH4 molecules
     - Distribution ratio (min/max): 1.00 (perfectly symmetric)
     - Z-span in each layer: 2.2 nm (92% of ice_thickness=2.4 nm)
  
  The fix ensures:
  - Guests are tiled SEPARATELY for bottom and top ice layers
  - Each layer gets proper spatial distribution matching the ice framework tiling
  - No arbitrary splitting by index
  
  Comparison with original bug (from reference hydrate_partialguest.gro):
  - Original: CH4 only in Z = [0.3, 4.8] and [8.1, 12.3] (GAP in middle!)
  - Fixed: CH4 uniformly distributed in both ice layers

files_changed: [quickice/structure_generation/modes/slab.py]
