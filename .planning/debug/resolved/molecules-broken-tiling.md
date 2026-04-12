---
status: resolved
trigger: "molecules-broken-tiling"
created: 2026-04-13T00:00:00Z
updated: 2026-04-13T00:00:03Z
---

## Current Focus

hypothesis: In `apply_transformation()` (transformer.py line 317), `frac_positions % 1.0` wraps INDIVIDUAL atoms to unit cell without considering molecular bonds. This breaks molecules apart when atoms cross PBC boundaries.
test: Examine the transformation code flow and confirm the wrapping logic treats atoms independently
expecting: Find that line 317 is the root cause - it needs to wrap molecules as units like `tile_structure()` does
next_action: Verify this is the only issue by tracing the full code path

## Symptoms

expected: All atoms of each water molecule should stay within ~0.1 nm of each other (O-H bond distance)
actual: Many molecules have atoms separated by 1+ nm - completely broken molecules scattered across the box
errors: No error messages, but output structure is corrupted
reproduction: 
1. Use default slab generation with triclinic phase (Ice II)
2. Export the output to GRO file
3. Check O-H distances - many are >1 nm instead of ~0.1 nm
started: Issue persists after all previous transformation fixes

## Eliminated

- hypothesis: Bug is in tile_structure() or GenIce output
  evidence: Original GenIce positions have correct O-H distances (0.095-0.096 nm). Transformation breaks them.
  timestamp: 2026-04-13T00:00:01Z

## Evidence

- timestamp: 2026-04-13T00:00:00Z
  checked: User-provided GRO file evidence
  found: Molecules 33, 34, 53 have O-H distances >1 nm (should be ~0.1 nm)
  implication: Atoms from same molecule are being scattered across supercell during tiling

- timestamp: 2026-04-13T00:00:01Z
  checked: Compared original GenIce positions vs transformed positions
  found: Original positions: all 10 molecules have O-H distances ~0.095 nm (CORRECT). Transformed: 6/10 molecules have O-H >0.15 nm, some >1.7 nm (BROKEN)
  implication: Bug is definitively in apply_transformation(), not in GenIce or tile_structure()

- timestamp: 2026-04-13T00:00:01Z
  checked: transformer.py line 317: `frac_positions = frac_positions % 1.0`
  found: This wraps ALL atoms independently to [0, 1) without considering molecular bonds
  implication: ROOT CAUSE FOUND - Line 317 breaks molecules by wrapping individual atoms instead of molecules as units

## Resolution

root_cause: In `apply_transformation()` (transformer.py), the original code used `frac_positions @ H_inv` to transform fractional coordinates. This transformation broke molecules because H_inv has non-integer elements that change the relative positions of atoms in fractional coordinate space, even though molecules were intact in Cartesian space.
fix: Changed the approach to replicate Cartesian positions directly (not fractional coords), then wrap molecules as units into the supercell. The key insight is that H transforms CELL VECTORS, not positions. Positions in Cartesian space should be replicated by adding lattice vector combinations, not transformed.
verification: O-H distance distribution matches original GenIce output (Min: 0.0948 nm, Max: 0.0965 nm, Mean: 0.0957 nm). Zero broken molecules.
files_changed: [quickice/structure_generation/transformer.py]
