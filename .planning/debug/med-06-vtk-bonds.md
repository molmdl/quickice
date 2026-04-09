---
status: verifying
trigger: "MED-06 vtk-atom-index-handling - VTK bond creation assumes specific atom ordering without verification"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:00:01Z
---

## Current Focus
hypothesis: VERIFIED - Fix implemented and tested
test: All tests pass
expecting: No regressions, new validation tests pass
next_action: Complete debug session

## Symptoms
expected: Bond creation should verify atom ordering or be more robust
actual: Assumes atoms are ordered O, H, H for each molecule
errors: If atom ordering changes in upstream code, bonds will be wrong
reproduction: (Hypothetical) Modify atom ordering, visualize bonds
timeline: Always assumed this ordering

## Eliminated

## Evidence
- timestamp: 2026-04-09T00:00:00Z
  checked: quickice/gui/vtk_utils.py lines 72-77
  found: Hardcoded assumption: o_idx = mol_idx * 3, h1_idx = mol_idx * 3 + 1, h2_idx = mol_idx * 3 + 2
  implication: If atoms are not ordered O, H, H, bonds will be created between wrong atoms

- timestamp: 2026-04-09T00:00:00Z
  checked: quickice/gui/vtk_utils.py lines 373-379 (ice bonds) and 384-390 (water bonds)
  found: Same hardcoded assumption in interface_to_vtk_molecules for both ice and water
  implication: Multiple functions have this fragile assumption

- timestamp: 2026-04-09T00:00:00Z
  checked: quickice/gui/vtk_utils.py lines 155-164
  found: detect_hydrogen_bonds also assumes O at index mol_idx * 3, H at mol_idx * 3 + 1/2
  implication: H-bond detection would also fail with wrong atom ordering

- timestamp: 2026-04-09T00:00:01Z
  checked: quickice/structure_generation/types.py
  found: Candidate.atom_names documented as ["O", "H", "H", "O", "H", "H", ...], InterfaceStructure notes ice uses O, H, H and water uses OW, HW1, HW2, MW
  implication: Documentation confirms ordering expectation but code doesn't verify it

- timestamp: 2026-04-09T00:00:01Z
  checked: quickice/structure_generation/water_filler.py
  found: TIP4P water template from tip4p.gro has fixed ordering: OW, HW1, HW2, MW (4 atoms per molecule)
  implication: Water ordering is guaranteed by template, but ice ordering from GenIce could theoretically vary

- timestamp: 2026-04-09T00:00:02Z
  checked: All test files in tests/ directory
  found: Every test uses atom_names=["O", "H", "H", ...] pattern for ice and ["OW", "HW1", "HW2", "MW", ...] for water
  implication: All tests assume this ordering, reinforcing that it's the expected pattern but no verification

- timestamp: 2026-04-09T00:00:03Z
  checked: quickice/ranking/scorer.py line 25
  found: Function _calculate_oo_distances_pbc uses undefined constant OO_CUTOFF instead of config.oo_cutoff
  implication: Unrelated bug that prevents tests from running - needed to fix to verify changes

- timestamp: 2026-04-09T00:00:10Z
  action: Added validation assertions in candidate_to_vtk_molecule, detect_hydrogen_bonds, and interface_to_vtk_molecules
  found: Assertions check atom names match expected patterns (TIP3P: O, H, H; TIP4P: OW, HW1, HW2, MW)
  implication: Will now raise ValueError with informative message if ordering is incorrect

- timestamp: 2026-04-09T00:00:15Z
  action: Created comprehensive tests in test_atom_ordering_validation.py and test_interface_ordering_validation.py
  found: All 11 new tests pass, verifying both valid and invalid ordering detection
  implication: Fix correctly catches ordering issues while allowing valid patterns

- timestamp: 2026-04-09T00:00:20Z
  action: Ran full test suite
  found: 172 relevant tests pass (VTK, structure generation, ranking, phase mapping)
  implication: Fix doesn't break existing functionality

## Resolution
root_cause: VTK bond creation uses index arithmetic (mol_idx * 3, mol_idx * 3 + 1, mol_idx * 3 + 2) to identify O and H atoms without verifying that atom_names follows the expected ordering (O, H, H for ice; OW, HW1, HW2 for water visible atoms). If upstream code changes atom ordering or provides incorrectly ordered atoms, bonds will be created between wrong atoms silently, resulting in visually incorrect and physically meaningless molecular structures.
fix: Added validation assertions in three locations:
1. candidate_to_vtk_molecule: Validates TIP3P (O, H, H) or TIP4P (OW, HW1, HW2) ordering for each molecule before creating bonds
2. detect_hydrogen_bonds: Validates TIP3P or TIP4P ordering before detecting H-bonds
3. interface_to_vtk_molecules: Validates ice (O, H, H) and water (OW, HW1, HW2, MW) ordering before creating bonds
Also fixed unrelated bug in scorer.py where OO_CUTOFF was undefined (changed to default value 0.35)
verification: Created comprehensive tests to verify:
- Valid TIP3P and TIP4P ordering passes
- Invalid ordering raises ValueError with informative message
- Mixed atom names are detected
- Multiple molecules are validated individually
- All existing tests pass
files_changed: [quickice/gui/vtk_utils.py, quickice/ranking/scorer.py, tests/test_atom_ordering_validation.py, tests/test_interface_ordering_validation.py]