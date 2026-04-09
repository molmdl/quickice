---
status: resolved
trigger: "HIGH-07 fragile-molecule-heuristic - Molecule count derivation heuristic in tile_structure is fragile and can fail"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:20:00Z
---

## Current Focus

hypothesis: CONFIRMED AND FIXED
test: All verification tests passed
expecting: Fix is complete and verified
next_action: Archive debug session

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

- timestamp: 2026-04-09T00:10:00Z
  checked: Implementation of fix
  found: Added atoms_per_molecule parameter to tile_structure, updated all call sites to pass explicit values (water=4, ice=3), replaced fallback with ValueError
  implication: Fix implemented, need to verify

- timestamp: 2026-04-09T00:15:00Z
  checked: Verification testing
  found: (1) TIP4P water with atoms_per_molecule=4 works correctly, (2) Ice with atoms_per_molecule=3 works correctly, (3) Ambiguous cases (48 atoms) raise ValueError, (4) Non-divisible cases (50 atoms) raise ValueError, (5) Invalid atoms_per_molecule raises ValueError
  implication: Fix verified - all test cases pass

## Resolution

root_cause: The heuristic in tile_structure (lines 119-129) uses fragile modulo division to determine atoms_per_molecule. For ice structures where the atom count is divisible by both 3 and 4 (ice1h=48 atoms, ice1c=24 atoms, ice7=48 atoms, ice8=192 atoms), the heuristic defaults to 4 when it should be 3. The fallback case (not divisible by 3 or 4) treats the entire structure as one molecule, which is catastrophic. Call sites know the correct value but cannot pass it.
fix: Added optional atoms_per_molecule parameter to tile_structure with validation. All call sites now pass explicit values: fill_region_with_water passes ATOMS_PER_WATER_MOLECULE (4), ice modes (piece, pocket, slab) pass 3. Heuristic now raises ValueError for ambiguous cases (divisible by both 3 and 4) and non-divisible cases instead of guessing. Added deprecation warnings for inferred cases.
verification: Comprehensive testing confirmed: (1) TIP4P water with atoms_per_molecule=4 works correctly, (2) Ice with atoms_per_molecule=3 works correctly, (3) Ambiguous cases (48 atoms) raise ValueError, (4) Non-divisible cases (50 atoms) raise ValueError, (5) Invalid atoms_per_molecule raises ValueError. Fix was committed in 1a6d7d3 alongside HIGH-06.
files_changed: ['quickice/structure_generation/water_filler.py', 'quickice/structure_generation/modes/piece.py', 'quickice/structure_generation/modes/pocket.py', 'quickice/structure_generation/modes/slab.py']
