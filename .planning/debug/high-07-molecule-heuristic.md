---
status: verifying
trigger: "HIGH-07 fragile-molecule-heuristic - Molecule count derivation heuristic in tile_structure is fragile and can fail"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:10:00Z
---

## Current Focus

hypothesis: CONFIRMED - Heuristic produces wrong molecule counts for ice1h, ice1c, ice7, ice8 due to ambiguous case; fallback is catastrophic
test: Calculate which ice phases trigger ambiguous case based on unit cell molecule counts
expecting: Find specific ice phases that will fail
next_action: Verify the fix with comprehensive testing

## Symptoms

expected: Robust molecule count calculation that works for all cases
actual: Heuristic based on modulo division can fail for ambiguous or unexpected atom counts
errors: Wrong molecule count propagates to downstream calculations
reproduction: Call tile_structure with unexpected total atom count (e.g., not divisible by 3 or 4)
started: Always used this heuristic, but fragile

## Eliminated

<!-- No hypotheses eliminated yet -->

## Evidence

- timestamp: 2026-04-09T00:00:00Z
  checked: Issue description
  found: Problematic code in lines 151-163 with fragile heuristic logic
  implication: Need to verify actual implementation and all call sites

- timestamp: 2026-04-09T00:02:00Z
  checked: water_filler.py lines 119-129
  found: Heuristic logic with three cases: (1) divisible by 3 only → 3, (2) divisible by 4 only → 4, (3) divisible by both → default to 4, (4) neither → fallback to n_original_atoms
  implication: Ambiguous case and fallback can produce wrong values

- timestamp: 2026-04-09T00:03:00Z
  checked: All call sites of tile_structure
  found: 4 call sites: (1) fill_region_with_water uses TIP4P (4 atoms), (2) piece.py tiles ice, (3) pocket.py tiles ice, (4) slab.py tiles ice (2 calls)
  implication: Call sites KNOW what type of structure they're tiling but don't communicate it

- timestamp: 2026-04-09T00:04:00Z
  checked: mapper.py UNIT_CELL_MOLECULES and calculated atom counts for each ice phase
  found: ice1h=48 atoms, ice1c=24 atoms, ice2=36 atoms, ice3=36 atoms, ice5=84 atoms, ice6=30 atoms, ice7=48 atoms, ice8=192 atoms
  implication: ice1h, ice1c, ice7, ice8 all have atom counts divisible by both 3 AND 4

- timestamp: 2026-04-09T00:05:00Z
  checked: Ambiguous case calculation
  found: ice1h (48 atoms), ice1c (24 atoms), ice7 (48 atoms), ice8 (192 atoms) all trigger ambiguous case → heuristic defaults to 4 atoms/molecule when it should be 3
  implication: CRITICAL BUG: Most common ice phases get wrong molecule count!

## Resolution

root_cause: The heuristic in tile_structure (lines 119-129) uses fragile modulo division to determine atoms_per_molecule. For ice structures where the atom count is divisible by both 3 and 4 (ice1h, ice1c, ice7, ice8), the heuristic defaults to 4 when it should be 3. The fallback case (not divisible by 3 or 4) treats the entire structure as one molecule, which is catastrophic. Call sites know the correct value but cannot pass it.
fix: Added optional atoms_per_molecule parameter to tile_structure. All call sites now pass explicit values: fill_region_with_water passes 4, ice modes (piece, pocket, slab) pass 3. Heuristic now raises ValueError for ambiguous cases (divisible by both 3 and 4) and non-divisible cases instead of guessing. Added deprecation warnings for inferred cases.
verification: Tested ice1h (48 atoms) - correctly raises ValueError without explicit parameter, works correctly with atoms_per_molecule=3. Tested TIP4P water - works correctly with atoms_per_molecule=4. Tested ambiguous and non-divisible cases - correctly raise ValueError. All call sites updated and working.
files_changed: ['quickice/structure_generation/water_filler.py', 'quickice/structure_generation/modes/piece.py', 'quickice/structure_generation/modes/pocket.py', 'quickice/structure_generation/modes/slab.py']
