---
status: investigating
trigger: "Two critical issues: Missing guests at PBC boundary (filtering still in code - but was also in working version!) and Crazy overlap in liquid water (NEW issue - older versions had NO liquid water issue)"
created: 2026-05-03T00:00:00Z
updated: 2026-05-03T12:00:00Z
---

## Current Focus
hypothesis: COM wrapping logic + water thickness adjustment cause overlaps. Working version used MIN/MAX wrapping and had no issues despite same filtering.
test: Compare working version (892908e) wrapping logic with current version - identify exact differences
expecting: Find that COM wrapping loses molecules or causes overlaps that min/max wrapping prevented
next_action: Read working version tile_structure() code (git show 892908e:quickice/structure_generation/water_filler.py lines 480-560)

## Symptoms
expected: |
  1. All guest molecules present at PBC boundaries (none missing)
  2. Liquid water with NO overlaps (correct O-O spacing ~0.28nm)
  3. Continuous periodic images
  4. Older versions had NO liquid water issues

actual: |
  1. Guests missing at PBC boundary in hydrate
  2. Liquid water has 6,074 overlapping pairs (1,266 severe < 0.15nm)
  3. Minimum O-O distances in liquid: 0.03-0.05 nm (crazy!)
  4. Liquid region (Z 3.5-7.5 nm) has 6,475 OW but 6,074 overlapping pairs

errors: |
  - Liquid water molecules almost on top of each other (0.03nm apart)
  - Missing guests at periodic boundaries
  - Water template has atoms outside box (min: -0.064nm, max: 1.896nm > box 1.868nm)

reproduction: |
  Files in tmp/ch4, tmp/thf, tmp/ice:
  - tmp/ch4/slab/interface_slab.gro: 12,790 OW, 6,074 overlapping pairs in liquid
  - tmp/thf/slab/interface_slab.gro: Similar issues
  - tmp/ice/slab/interface_slab.gro: Also has overlaps

  Key evidence:
  - Liquid region OW count: 6,475
  - Overlapping pairs < 0.25nm: 6,074 (almost 1 pair per atom!)
  - Severe overlaps < 0.15nm: 1,266
  - Sample distances: 0.034, 0.052, 0.068 nm (should be ~0.28nm)

timeline: |
  - Older versions: Liquid water had NO issues
  - After recent fixes: Liquid water now has crazy overlaps
  - Recent commits:
    - b641498: Simplified calc_tile_count to use math.ceil()
    - f09c930: Added filtering of molecules with atoms outside box

## Eliminated

## Evidence

- timestamp: 2026-05-03T00:00:00Z
  checked: Initial symptoms from user report
  found: Two critical issues - filtering removes valid molecules, liquid water has overlaps
  implication: Need to investigate both filtering logic and tiling calculation

- timestamp: 2026-05-03T00:00:01Z
  checked: Git history of water_filler.py
  found: Commit b641498 changed calc_tile_count from complex tolerance logic to simple math.ceil()
  implication: This may cause over-tiling when target dimension is nearly exact multiple of cell dimension

- timestamp: 2026-05-03T00:00:02Z
  checked: Water template file (tip4p.gro)
  found: Template has atoms with negative coordinates and atoms >= box_dim (1.86824nm)
         X: [-0.064, 1.896], Y: [-0.028, 1.894], Z: [-0.051, 1.937]
         14 atoms outside X, 9 atoms outside Y, 15 atoms outside Z
  implication: Template is improperly wrapped or broken - this causes molecules to span PBC boundaries

- timestamp: 2026-05-03T00:00:03Z
  checked: Filtering logic in water_filler.py lines 567-590
  found: Code filters molecules with atoms outside [0, target_region)
         This removes molecules that span PBC boundaries (including valid guest molecules)
  implication: This filtering CAUSES missing guests at PBC boundaries

- timestamp: 2026-05-03T00:00:04Z
  checked: Simulated current tile_structure logic with water template
  found: Current code produces 18,964 overlapping pairs (4,155 severe < 0.15nm)
         Minimum distance: 0.042nm (should be ~0.28nm)
         After tiling 10,368 molecules, filtering removes 613 molecules
         Remaining molecules have MASSIVE overlaps
  implication: Current tiling logic is BROKEN for water template with atoms outside box

- timestamp: 2026-05-03T00:00:05Z
  checked: Tested wrapped water template (modulo on individual atoms)
  found: Wrapped template has ALL atoms within [0, template_box)
         NO overlaps in template itself
         Maximum molecule span: [0.150, 0.148, 0.151] nm
  implication: Wrapping template atoms fixes the root cause

 - timestamp: 2026-05-03T00:00:06Z
  checked: Tested tiling with wrapped water template
  found: Wrapped template produces NO overlaps when tiled
         All 10,368 molecules preserved (no filtering needed)
         Correct O-O spacing maintained
  implication: Fixing the template SOLVES the liquid water overlap issue

- timestamp: 2026-05-03T12:00:00Z
  checked: User provided critical new information about working version
  found: Working version (commit 892908e) ALSO had filtering but worked correctly
         Key differences: MIN/MAX wrapping vs COM wrapping
         Water thickness adjustment is NEW in current version
         User says template worked before - do NOT change template
  implication: Previous investigation was WRONG - template is fine, wrapping logic changed and broke it
               
               ROOT CAUSE HYPOTHESIS REVISED:
               1. COM wrapping is different from min/max wrapping
               2. Combined with water thickness adjustment, this may cause overlaps
               3. Need to compare exact wrapping logic between versions

## Resolution
root_cause: |
  TWO CRITICAL ISSUES:
  
  1. WATER TEMPLATE IS BROKEN:
     - Template has 32 molecules (15%) with atoms outside [0, template_box)
     - Template position ranges: X [-0.064, 1.896], Y [-0.028, 1.894], Z [-0.051, 1.937]
     - Template box: 1.86824 nm
     - This causes molecules to span PBC boundaries incorrectly
  
  2. TILING LOGIC DOESN'T HANDLE SPANNING MOLECULES:
     - Current code: tile -> COM wrap -> filter
     - COM wrapping doesn't fix molecules spanning boundaries
     - Filtering removes 613 molecules (6%), changing density
     - Remaining molecules have massive overlaps (18,964 pairs, min distance 0.042nm)
  
  3. FILTERING CAUSES MISSING GUESTS:
     - Lines 567-590 filter molecules with atoms outside [0, target_region)
     - This removes valid guest molecules at PBC boundaries
     - Guest molecules at origin (spanning PBC) are incorrectly removed

fix: |
  1. FIX WATER TEMPLATE: Wrap atoms with modulo to bring all atoms into [0, template_box)
     - Use: positions_wrapped = positions % template_box
     - Result: All atoms in [0, 1.86824), no overlaps in template
  
  2. REMOVE/SIMPLIFY FILTERING LOGIC:
     - After fixing template, filtering is no longer needed for water
     - Keep simple boundary check for safety, but don't filter molecules
     - For guests: handle wrapping correctly (don't filter at PBC boundaries)
  
  3. UPDATE load_water_template() to return wrapped template

verification: |
  1. Wrapped template test: 0 atoms outside box, 0 overlaps ✓
  2. Tiling with wrapped template: 0 overlaps, correct density ✓
  3. All 10,368 water molecules preserved (no filtering) ✓
  4. Guest molecules at PBC boundaries preserved (no filtering) - NEEDS TESTING

files_changed: []

