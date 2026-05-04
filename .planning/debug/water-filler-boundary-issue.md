---
status: verifying
trigger: "Water filler places 22 water OW atoms in TOP ice region causing overlaps"
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:10:00Z
---

## Current Focus
hypothesis: Fix implemented and tested - added guest-water overlap detection to remove water molecules that overlap with CH4 guests in top ice region
test: Regenerate test structure tmp/ch4/slab/interface_slab.gro with the fix and verify no overlaps between water filler OW and CH4 C atoms
expecting: After fix, all water filler OW should be within [ice_thickness, ice_thickness + water_thickness) and no overlaps with CH4
next_action: Need to regenerate the test file or verify with user that fix resolves the issue

## Symptoms

expected: Water filler should place water ONLY in middle liquid region between ice/hydrate layers: Z = [ice_thickness, ice_thickness + water_thickness]
actual: Water filler places 22 water OW atoms in the TOP ice region (Z >= 7.263 nm), causing 57 overlaps with CH4 guest molecules
errors: 57 overlaps with CH4 guest molecules in top ice region
reproduction: Generate slab structure with water filling
started: Always present in slab mode with water filling

Evidence from UAT:
1. CH4 gap analysis shows water region should be Z = [3.364, 7.263) nm
2. Water filler OW are at Z = [3.636, 7.301] nm
3. 22 water filler OW atoms are at Z >= 7.263 nm (top ice region)
4. These cause 57 overlaps with CH4 in the top ice region
5. 2733 out of 6000 CH4 molecules have overlaps with water OW within 0.3 nm

## Eliminated

## Evidence

- timestamp: 2026-05-04T00:01:00Z
  checked: OW Z distribution in test file tmp/ch4/slab/interface_slab.gro
  found: |
    - Box Z = 10.92752 nm
    - Total OW atoms: 10489
    - OW Z range: 0.0 to 10.792 nm
    - Distribution: 2970 in bottom ice (Z < 3.364), 4337 in water region (3.364 <= Z < 7.263), 3182 in top ice (Z >= 7.263)
    - Top ice has 212 more OW atoms than bottom ice (3182 vs 2970)
  implication: Water filler atoms are appearing in the top ice region

- timestamp: 2026-05-04T00:02:00Z
  checked: CH4 Z distribution to identify ice layer boundaries
  found: |
    - CH4 molecules: 1200 total
    - Largest gap in CH4: Z = 3.301 to 7.326 nm (water region)
    - Bottom ice CH4: Z = [0, 3.301) nm (600 molecules)
    - Top ice CH4: Z = [7.326, box_z) nm (525 molecules)
    - 75 CH4 molecules found in water region [3.301, 7.326) nm
  implication: CH4 molecules are also appearing in the water region, which is incorrect

- timestamp: 2026-05-04T00:03:00Z
  checked: OW Z distribution gaps to identify actual layer boundaries
  found: |
    - Largest OW gap: Z = 3.466 to 3.636 (gap = 0.170 nm) - boundary between bottom ice and water
    - Second largest gap: Z = 7.326 to 7.469 (gap = 0.143 nm) - boundary between water and top ice
    - Water filler OW range: Z = [3.636, 7.301] nm
  implication: Water filler starts at 3.636 nm, ends at 7.301 nm, which is 0.038 nm above intended upper boundary

- timestamp: 2026-05-04T00:04:00Z
  checked: Calculated adjusted ice and water thickness values
  found: |
    - Water template cell: 1.868 nm, scaled: 1.863 nm (at 273.15 K, 0.101325 MPa)
    - Likely ice cell Z: 1.2 nm (structure I hydrate)
    - Adjusted ice_thickness: 3.600 nm (3 cells)
    - Adjusted water_thickness: 3.725 nm (2 cells)
    - Calculated box_z: 10.925 nm (actual: 10.92752 nm, close match)
    - Expected water region: Z = [3.600, 7.325) nm
    - Actual water filler region: Z = [3.636, 7.301] nm
  implication: Water filler starts 0.036 nm above expected and ends 0.024 nm below expected, but max Z (7.301) exceeds intended boundary (7.263)

- timestamp: 2026-05-04T00:05:00Z
  checked: Simulated water tiling with actual adjusted values
  found: |
    - Water template scaled box: 1.863 nm
    - Tiled into region [3.0, 3.0, 3.725] nm
    - Result: 4164 atoms, 1041 molecules
    - Tiled Z range: [0.006, 3.710] nm (within target [0, 3.725))
    - OW Z range: [0.035, 3.700] nm
    - After shift by ice_thickness=3.6 nm: OW Z range becomes [3.635, 7.3] nm
  implication: Water tiling produces molecules near the upper boundary (Z ~ 3.7 nm), which after shifting end up at Z ~ 7.3 nm

- timestamp: 2026-05-04T00:06:00Z
  checked: Overlaps between water filler OW at Z >= 7.263 and CH4 C in top ice
  found: |
    - Water filler OW at Z >= 7.263: 22 atoms (Z values: 7.294-7.301 nm)
    - CH4 C atoms at Z >= 7.263: 600 atoms (all at Z = 7.326 nm or higher)
    - Overlaps (distance < 0.3 nm): 13 pairs
    - Overlap distances: 0.053 to 0.294 nm
    - Example: OW at Z=7.301 nm, CH4 at Z=7.326 nm, distance=0.053 nm
  implication: Water filler molecules near the upper boundary are overlapping with CH4 in top ice because the gap (7.301 to 7.326 = 0.025 nm) is too small

- timestamp: 2026-05-04T00:07:00Z
  checked: Code review of overlap detection in slab.py (lines 341-369)
  found: |
    - Overlap detection only checks ice OW vs water OW (lines 348-353)
    - Does NOT check water OW vs guest (CH4) atoms
    - Guest tiling happens AFTER water overlap detection (lines 373-519)
    - Water molecules near upper boundary pass through ice-water overlap check
    - But they overlap with CH4 guests in top ice region
  implication: Missing overlap check between water filler and guest molecules causes water to be placed in regions occupied by CH4

## Resolution

root_cause: Overlap detection in assemble_slab() only checks ice OW vs water OW, but does NOT check water OW vs guest (CH4) atoms. Since guest tiling happens after water placement and overlap detection, water molecules near the upper boundary of the water region overlap with CH4 guest molecules in the top ice region. The gap between water filler (ends at 7.301 nm) and top ice CH4 (starts at 7.326 nm) is only 0.025 nm, causing 13 overlaps.
fix: Added guest-water overlap detection after guest tiling (lines 521-544 in slab.py). The fix detects overlaps between all guest atoms and water OW atoms, then removes overlapping water molecules. This ensures water filler respects both ice framework AND guest molecule positions.
verification: All existing interface mode tests pass. Manual verification with test file tmp/ch4/slab/interface_slab.gro needed to confirm 22 water OW atoms at Z >= 7.263 nm are removed and no overlaps with CH4 remain.
files_changed: [quickice/structure_generation/modes/slab.py]
