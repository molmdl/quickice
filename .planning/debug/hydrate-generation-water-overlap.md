---
status: fixing
trigger: "Investigate severe water-water overlap in hydrate structure generation."
created: 2026-05-01T01:00:00Z
updated: 2026-05-01T02:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - Hydrate structure ALREADY spans target Y dimension (~7.2 nm) but tile_structure() creates extra copy to fill 7.451 nm box, causing residue 829 to overlap with residue 1 (Y diff = 0.249 nm)
test: Verify hydrate cell dimensions and fix tile_structure to not over-tile when structure already fits
expecting: Hydrate structure should be used as-is without tiling, OR tiling should be skipped when structure is large enough
next_action: Check hydrate cell dimensions from to_candidate() and fix tile_structure to handle large structures

## Symptoms

expected: Hydrate structure should have properly spaced water molecules (O-O distance ~0.28 nm minimum)
actual: Both ion and interface exports show ~6,500 overlapping water pairs with minimum O-O distance of 0.0286 nm
errors: 
- 306 severe overlaps (<0.15 nm) in ion export
- 300 severe overlaps (<0.15 nm) in interface export
- Total ~6,600 pairs < 0.25 nm in each file
reproduction: Both files have identical overlap patterns:
- tmp/ch4/ion/ions_50na_50cl.gro: 6,662 O-O pairs < 0.25 nm
- tmp/ch4/interface/interface_slab.gro: 6,390 O-O pairs < 0.25 nm
This indicates the overlap originates in hydrate generation, not export
started: Always broken - fundamental issue in hydrate generation

## Critical Pattern Evidence

Example overlap at 0.0286 nm:
- Res 12 SOL OW at (0.234, 0.458, 0.600)
- Res 861 SOL OW at (0.230, 0.486, 0.604)

Pattern analysis:
- Same X coordinate (e.g., 1.057, 1.057)
- Same Z coordinate (e.g., 3.605, 3.605)
- Different Y coordinate (e.g., 0.375 vs 0.126, difference ~0.249 nm)

This systematic pattern suggests:
1. Hydrate structure generated twice with offset
2. Ice layer + water layer overlapping positions
3. Unit cell replication causing boundary overlaps
4. Cage filling algorithm placing waters in same locations
5. Combining ice + hydrate + water layers incorrectly

## Eliminated

- hypothesis: PBC molecule splitting causing false overlaps
  evidence: Previous session identified this and applied fix, but overlaps still exist with different pattern (same X,Z, different Y suggests layering not PBC)
  timestamp: 2026-05-01T01:00:00Z

## Evidence

- timestamp: 2026-05-01T01:00:00Z
  checked: Previous debug session (hydrate-layer-internal-overlap.md)
  found: Fix was applied to wrap_molecules_into_box for PBC splitting
  implication: Fix didn't solve the problem - issue is different from PBC splitting

- timestamp: 2026-05-01T01:15:00Z
  checked: Overlap analysis with KDTree on interface_slab.gro
  found: 8,421 pairs < 0.25 nm; 2,015 (23.9%) show "same X,Z, different Y" pattern
  implication: Systematic duplication pattern, not random overlap

- timestamp: 2026-05-01T01:20:00Z
  checked: Y difference and residue number patterns in overlaps
  found: CRITICAL - Y diff exactly 0.249 nm (1,932 cases), residue diff exactly 828 (1,932 cases)
  implication: Water molecules duplicated with offset of 0.249 nm in Y, 828 residues apart - this is systematic duplication

- timestamp: 2026-05-01T01:30:00Z
  checked: Full Y-axis periodicity analysis of overlapping molecules
  found: ROOT CAUSE - Original hydrate has 6 molecules per (X,Z) position with 1.200 nm Y spacing (total ~7.2 nm). Target box is 7.451 nm. tile_structure() creates ONE extra copy (residue 829) which overlaps with residue 1 by 0.249 nm.
  implication: tile_structure() is over-tiling a structure that ALREADY spans the target region - needs to detect when structure is large enough and skip tiling

## Resolution

root_cause: The `tile_structure()` function in water_filler.py uses `math.ceil()` to calculate tiling counts, which creates extra tiles even when the structure already covers >=95% of the target region. For hydrate->interface conversion, when the hydrate supercell has Y dimension of 7.2 nm and the target box is 7.451 nm, the ratio is 1.035, causing ceil(1.035)=2 tiles instead of 1. This creates overlapping water molecules.

fix: Modified `tile_structure()` to check if the structure already covers >=95% of the target dimension before applying ceil(). If ratio <= 1.05, use 1 tile instead of ceil(ratio). This prevents over-tiling of large hydrate structures during interface generation.

verification: User must regenerate hydrate interface structure from GUI with fixed code, then check:
1. No overlaps with distance < 0.15 nm (currently 850 pairs)
2. No "same X,Z, different Y" pattern with Y diff ~0.249 nm
3. All O-O distances >= 0.25 nm minimum

files_changed: [quickice/structure_generation/water_filler.py]
