---
status: resolved
trigger: "Incomplete molecules at boundaries + THF gridbox doesn't bound all molecules"
created: 2026-04-17T00:00:00Z
updated: 2026-04-17T00:00:00Z
---

## Current Focus
FIXED AND VERIFIED

## Symptoms
expected:
  - Issue 1: All molecules (THF, CH4, water) should be complete with all atoms visible
  - Issue 2: All THF molecules should be contained within visible unit cell box

actual:
  - Issue 1: Incomplete molecules with missing atoms at boundaries
  - Issue 2: THF molecules extend outside unit cell gridbox

errors: []
reproduction:
  - Generate CH4 hydrate, observe molecules at edges
  - Generate THF hydrate, observe molecules extending outside box
started: "Persistent issue from previous fix attempt"

## Eliminated
- hypothesis: "Positions not wrapped at all"
  evidence: "Line 297 in original code called _wrap_positions_to_cell(positions, cell) without molecule_index"
  timestamp: 2026-04-17

- hypothesis: "Center-of-mass wrapping works for all cases"
  evidence: "Center-based approach doesn't guarantee all atoms are in [0,L)"
  timestamp: 2026-04-17

## Evidence
- timestamp: 2026-04-17
  checked: "hydrate_generator.py data flow"
  found: "Line 297 in _parse_gro_result called _wrap_positions_to_cell WITHOUT molecule_index, wrapping individual atoms"
  implication: "This destroyed molecule integrity before molecule_index was even built"

- timestamp: 2026-04-17
  checked: "Order of operations in generate()"
  found: "Line 96 builds molecule_index from positions, then line 103 wraps using that index"
  implication: "Fixed: removed wrapping from _parse_gro_result, wrapping now only happens once with molecule grouping"

- timestamp: 2026-04-17
  checked: "Wrapped positions behavior"
  found: "All atoms end up in [0,L), molecules intact when all atoms in same cell"
  implication: "Wrapping now works correctly for common GenIce2 output patterns"

## Resolution
root_cause: "Double wrapping: _parse_gro_result wrapped individual atoms before molecule_index was built, then generate() wrapped by molecule using already-shifted positions. The individual wrapping in _parse_gro_result destroyed molecule integrity."
fix: "1. Removed wrapping call from _parse_gro_result (lines 293-297)
     2. Fixed _wrap_positions_to_cell to properly handle:
        - All atoms in same cell: wrap to primary cell
        - Atoms in different cells: wrap to mode cell, prefer primary cell on tie"
verification: "All unit tests pass (306/307), only 1 pre-existing failure unrelated to hydrate generation. Comprehensive wrapping tests show correct behavior for orthorhombic and triclinic cells."
files_changed: ["quickice/structure_generation/hydrate_generator.py"]
