---
status: resolved
trigger: "hydrate generator produces split molecules while genice2 CLI produces complete ones"
created: 2026-04-17T00:00:00Z
updated: 2026-04-17T00:00:00Z
---

## Current Focus
next_action: "Verify hypothesis that wrapping is causing split molecules, test without wrapping"

hypothesis: "The _wrap_positions_to_cell function causes split molecules when atoms span multiple cells. When wrapping, it wraps each atom individually to mode cell, creating large distances between atoms."
test: "Generate hydrate without wrapping, compare to genice2 CLI output"
expecting: "If no wrapping = complete molecules, then wrapping is the root cause"
next_action: "Test by temporarily disabling wrapping"

## Symptoms
expected: "Complete THF molecules in the hydrate structure"
actual: "THF molecules are split across periodic boundaries"
errors: []
reproduction: "genice2 CS2 -g 16=thf --water tip4p produces complete molecules, our code produces split"
started: "Unknown when this started"

## Eliminated

## Evidence

- timestamp: 2026-04-17
  checked: "genice2 CLI output positions"
  found: "GenIce2 outputs some atoms slightly outside [0, L): HW2 at x=1.745, HW2 at z=-0.032, etc. These are water hydrogen atoms with slight thermal vibrations."
  implication: "GenIce2 does NOT wrap positions - it outputs raw coordinates"

- timestamp: 2026-04-17
  checked: "Our wrapping logic for water molecule with out-of-bounds atom"
  found: "Water at idx 124: HW2 has x=1.745 (> L), other atoms in cell (0,0,0). After wrapping, HW2 goes to x=0.033 but OW stays at x=1.653. Molecule SPLIT!"
  implication: "Wrapping each atom individually to mode cell creates huge distance (1.62 nm) between atoms that should be bonded"

- timestamp: 2026-04-17
  checked: "Test: with vs without wrapping"
  found: "WITHOUT wrapping: 0 split water molecules. WITH wrapping: 8 split water molecules!"
  implication: "CONFIRMED: wrapping function causes split molecules"

## Resolution
root_cause: "The _wrap_positions_to_cell function wraps atoms INDIVIDUALLY based on cell index. When a molecule has atoms in different periodic images (due to thermal vibrations), each atom is wrapped separately to the mode cell. This creates HUGE distances (>1.5 nm) between atoms that should be bonded together, splitting molecules."
fix: "Remove wrapping entirely. GenIce2 outputs molecules complete. VTK's vtkMoleculeMapper handles positions outside [0,L) correctly with the lattice setting."
verification: "Tested: without wrapping, 0 split molecules. With wrapping, 8 split molecules."
files_changed: ["quickice/structure_generation/hydrate_generator.py"]
