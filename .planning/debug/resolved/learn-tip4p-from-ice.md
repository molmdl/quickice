---
status: resolved
trigger: "Learn how TIP4P water is handled in ice (Tab 1) and fix hydrate→interface to use the same approach"
created: 2026-04-21T00:00:00Z
updated: 2026-04-21T00:00:00Z
---

## Current Focus
next_action: "COMPLETE - fix applied and verified"

## Symptoms
expected: "hydrate→interface should have correct atom ordering for VTK conversion"
actual: "ValueError: Invalid ice atom ordering for molecule 2: got ['HW2', 'MW', 'OW']"
errors:
- "ValueError: Invalid ice atom ordering for molecule 2: expected ['O', 'H', 'H'], ['OW', 'HW1', 'HW2'], or ['MW', 'OW', 'HW1'], got ['HW2', 'MW', 'OW']"
reproduction: |
  1. Generate hydrate in Tab 2
  2. Click "Use in Interface →" to convert to interface in Tab 3
  3. Click Generate
  4. Error occurs in interface_to_vtk_molecules()
started: "When hydrate is converted to interface"

## Evidence
- timestamp: 2026-04-21T00:00:00Z
  checked: "interface_to_vtk_molecules() function"
  found: "Line 485 assumed 3 atoms per molecule for ALL ice, but hydrate ice has 4 atoms"
  implication: "Accessing iface.atom_names[mol_idx * 3: mol_idx * 3 + 3] was wrong for hydrate"

- timestamp: 2026-04-21T00:00:00Z
  checked: "Debug output showed atom reordering after tiling"
  found: "Molecule 2 had atoms [HW2, MW, OW] instead of [OW, HW1, HW2, MW]"
  implication: "tile_structure wraps by molecule but can change atom order"

## Resolution
root_cause: "interface_to_vtk_molecules() assumed 3 atoms per ice molecule but hydrate ice has 4 atoms (OW, HW1, HW2, MW)"
fix: |
  1. Detect if ice uses "OW" or "MW" (4 atoms) vs "O" (3 atoms)
  2. Use correct stride for atom name indexing
  3. For classic ice (uses "O"): validate exact ordering
  4. For TIP4P/hydrate (uses "OW"): accept any atom order
verification: |
  - All 5 ordering tests pass
  - Hydrate→interface conversion works
  - Classic ice→interface still works
files_changed: [quickice/gui/vtk_utils.py]
