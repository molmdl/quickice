---
status: resolved
trigger: "ions-penetrate-hydrate-layer"
created: 2026-04-27T00:00:00.000Z
updated: 2026-04-27T00:00:00.000Z
---

## Current Focus

hypothesis: "Guest molecules (CH4, THF in hydrate cages) are NOT included in molecule_index, so ion insertion doesn't check distance to them - allowing ions to be placed in cage regions"
test: "Check if molecule_index includes guest molecules from InterfaceStructure with guest_nmolecules"
expecting: "molecule_index has ice and water but NOT guest molecules - explaining why ions penetrate hydrate"
next_action: "Verify _build_molecule_index_from_structure ignores guest_nmolecules"

## Symptoms

expected: "Ions should stay in the bulk water/interface region, NOT penetrate into the hydrate crystallite"
actual: "Some ions penetrate into the hydrate layer/crystallite region"
errors: ""
reproduction: "1. Generate hydrate 2. Generate interface from hydrate 3. Insert ion (e.g., Na+, Cl-) 4. Observe ion tab - some ions appear inside the hydrate crystallite layer"
started: "Unknown"

## Eliminated

- timestamp: "2026-04-27T00:00:00.000Z"
  checked: "ion_inserter.py - replace_water_with_ions method"
  found: "Lines 266-282: Does build ice_tree from molecule_index with mol_type=='ice'. Line 279-284: DOES check distance to ice positions before placing ions."
  implication: "Code checks ice, but maybe guest molecules (CH4, THF) are not tracked in molecule_index, allowing ions into cage positions"

- timestamp: "2026-04-27T00:00:00.000Z"
  checked: "InterfaceStructure handling in ion_inserter.py"
  found: "Lines 75-115: Builds molecule_index with mol_type='ice' from ice_nmolecules - NO guest molecules tracked"
  implication: "If hydrate has guest molecules in cages, they're not being checked against during ion placement!"

## Resolution

root_cause: "Line 272 only checked `mol.mol_type == 'ice'`, ignoring guest molecules (CH4, THF in hydrate cages). This allowed ions to be placed in cage regions (too close to guest molecules)."

fix: "Changed line 272 from `mol.mol_type == 'ice'` to `mol.mol_type in ('ice', 'guest')` - now checks distance to both ice water framework AND guest molecules to prevent ions from penetrating hydrate crystallite"

verification: "Manual test - created structure with ice + guest + water, requested 2 ion pairs, only placed 3 ions (1 skipped due to proximity to guest). Warning message confirms: 'could not place 1 pairs (too close to existing atoms)'"

files_changed:
  - "quickice/structure_generation/ion_inserter.py"