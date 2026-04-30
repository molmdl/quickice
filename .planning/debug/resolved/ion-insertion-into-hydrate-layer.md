---
status: resolved
trigger: "ion-insertion-into-hydrate-layer"
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
---

## Current Focus
hypothesis: CONFIRMED - The _build_molecule_index_from_structure method in ion_inserter.py uses wrong ordering (ice→guest→water) instead of correct (ice→water→guest)
test: Fixed the ordering and verified with unit test
expecting: Water molecules correctly identified, ions placed in liquid water region
next_action: Archive resolved session

## Symptoms
expected: Ions should be inserted only into the liquid water region of the interface, avoiding the solid ice/hydrate layer
actual: Ions are being inserted into the THF hydrate layer (solid phase) instead of the liquid water region
errors: No explicit errors, but ions in wrong location
reproduction: |
  - Generate THF sII hydrate
  - Export to interface tab (creates ice/hydrate + liquid water interface)
  - Insert ions (e.g., Na+, Cl-)
  - Ions appear in hydrate layer instead of liquid water
started: New issue discovered during testing

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->
- timestamp: 2026-04-30T00:00:00Z
  checked: InterfaceStructure type definition in types.py lines 251-254
  found: |
    Actual ordering documented:
    - positions[0:ice_atom_count] = ice atoms
    - positions[ice_atom_count:ice_atom_count+water_atom_count] = water atoms
    - positions[ice_atom_count+water_atom_count:] = guest atoms
  implication: Order is ice → water → guest

- timestamp: 2026-04-30T00:00:00Z
  checked: ion_inserter.py _build_molecule_index_from_structure method lines 68-70 and 95-132
  found: |
    Code assumes wrong ordering:
    - Ice atoms: 0 to ice_atom_count-1 (CORRECT)
    - Guest atoms: ice_atom_count to ice_atom_count + guest_atom_count - 1 (WRONG - these are water!)
    - Water atoms: ice_atom_count + guest_atom_count onward (WRONG - these are guests!)
  implication: Molecule index assigns water labels to guest positions, causing ions to be placed in hydrate cages

- timestamp: 2026-04-30T00:00:00Z
  checked: ion_inserter.py line 220
  found: water_mols = [m for m in structure.molecule_index if m.mol_type == "water"]
  implication: This selects molecules marked as "water" but they're actually guest molecules (THF) in hydrate cages

- timestamp: 2026-04-30T00:00:00Z
  checked: Verification test after fix
  found: |
    Created mock InterfaceStructure with ice→water→guest ordering:
    - 2 ice molecules (8 atoms), 3 water molecules (12 atoms), 2 THF guests (24 atoms)
    - After fix: water molecules correctly identified at positions 8-19
    - After fix: guest molecules correctly identified at positions 20-43
    - Z-coordinate verification: water in Z=2-3 (liquid), guests in Z=4-5
  implication: Fix works correctly

## Resolution
root_cause: _build_molecule_index_from_structure in ion_inserter.py used incorrect atom ordering (ice→guest→water) when building molecule_index from InterfaceStructure attributes. The correct order after commit 90afe86 is (ice→water→guest). This caused the molecule_index to mark guest molecule positions (THF in hydrate cages) as "water" molecules, so ion insertion replaced guest molecules instead of actual liquid water.
fix: |
  Changed ordering in _build_molecule_index_from_structure to:
  1. Ice molecules at positions 0 to ice_atom_count-1
  2. Water molecules at positions ice_atom_count to ice_atom_count+water_atom_count-1
  3. Guest molecules at positions ice_atom_count+water_atom_count onward
  
  Also updated docstring comment to reflect correct ordering.
verification: |
  1. All 316 existing tests pass (2 pre-existing failures unrelated to this fix)
  2. Custom verification test confirmed:
     - Water molecules correctly identified in liquid water region
     - Guest molecules correctly identified in guest region
     - Z-coordinate verification shows correct region assignment
files_changed: [quickice/structure_generation/ion_inserter.py]
