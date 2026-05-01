---
status: verifying
trigger: "Investigate atom overlap issue in ion interface export with hydrate layer."
created: 2026-05-01T00:00:00Z
updated: 2026-05-01T02:00:00Z
---

## Current Focus

hypothesis: Fix implemented - need to verify that it resolves the issue
test: Review the code changes and confirm the logic is correct
expecting: After fix, ions should be >= MIN_SEPARATION from all existing atoms
next_action: Write unit test to verify fix works correctly

## Symptoms

expected: Ion interface export should produce GRO files with ions positioned without overlapping with water/hydrate layer atoms
actual: Ion interface GRO file has atoms overlapping near the hydrate layer boundary
errors: User reported "atom overlap in ion interface with the hydrate layer"
reproduction: Check tmp/ch4/ion/ions_50na_50cl.gro for ion positions, compare with water/hydrate positions, look for ions too close to water molecules
started: Currently broken

## Eliminated

## Evidence

- timestamp: Initial investigation
  checked: ion_inserter.py and ion placement logic
  found: Code has MIN_SEPARATION=0.3nm check against ice AND guest molecules using KDTree (lines 302-307)
  implication: Code should prevent overlap, but overlap is reported

- timestamp: GRO file analysis
  checked: Actual output file tmp/ch4/ion/ions_50na_50cl.gro
  found: 100 ions total (50 NA, 50 CL), box size 7.45 x 7.45 x 10.93 nm, ions have z-coords ranging from ~3.7 to ~7.2 nm
  implication: Need to determine where hydrate layer is in z-direction to check for overlap

- timestamp: Structure analysis
  checked: Z-coordinate distribution of all molecule types
  found: Hydrate layers at z=0-4nm (bottom) and z=7-11nm (top), liquid water at z=4-7nm (middle). Ions distributed at z=3.7-7nm with some in transition zones.
  implication: Ions are positioned correctly in liquid region, but need to check actual distances

- timestamp: Distance analysis to representative atoms
  checked: Distance from ions to OW (water oxygen) and C (CH4 carbon)
  found: Min distance 0.425nm, all ions > 0.3nm MIN_SEPARATION
  implication: Checking against representative atoms shows no violation, but this is incomplete

- timestamp: Distance analysis to ALL atoms
  checked: Distance from ions to ALL hydrate atoms (including H atoms)
  found: ALL 50 NA ions and ALL 50 CL ions are within 0.3nm of hydrate atoms! Min distances: 0.156nm (CL), 0.172nm (NA). ALL ions violate MIN_SEPARATION!
  implication: ROOT CAUSE FOUND: Ion placement only checks against ice and guest molecules, but hydrate water framework is labeled as "water" not "ice"!

- timestamp: Code review
  checked: ion_inserter.py lines 275-307
  found: Line 278 checks "if mol.mol_type in ('ice', 'guest'):" to build remain_positions. This excludes water molecules even if they're part of the hydrate framework.
  implication: CONFIRMED ROOT CAUSE: Hydrate water framework molecules are labeled as "water", not "ice", so they're excluded from the distance check. Ions can be placed too close to hydrate water molecules.

- timestamp: Fix implementation
  checked: Modified ion_inserter.py lines 272-307
  found: Changed distance check to include ALL existing molecules (ice, water, guest) instead of just ice and guest. This ensures ions are not placed within MIN_SEPARATION of any atoms.
  implication: Fix should resolve the issue for both ice/water interfaces AND hydrate structures

- timestamp: Verification test
  checked: Ran test_ion_fix.py on existing GRO file
  found: Confirmed ALL 100 ions violate MIN_SEPARATION (min distances: 0.156nm CL, 0.172nm NA). This verifies the original problem.
  implication: After fix is deployed and ions are re-inserted, should see 0 violations

## Resolution

root_cause: Ion placement algorithm (ion_inserter.py line 278) only checks distance to molecules with mol_type="ice" or mol_type="guest". In hydrate structures, the water molecules forming the hydrate framework are labeled as "water", not "ice", so they are excluded from the distance check. This allows ions to be placed within MIN_SEPARATION (0.3nm) of hydrate water molecules, causing atom overlap.
fix: Modified ion_inserter.py lines 272-307 to check distance to ALL existing molecules (ice, water, guest) instead of just ice and guest. This ensures ions are not placed too close to any atoms, including hydrate water framework molecules.
verification: Test script confirms all 100 ions in current GRO file violate MIN_SEPARATION. After fix, re-running ion insertion should produce 0 violations.
files_changed: [quickice/structure_generation/ion_inserter.py]
