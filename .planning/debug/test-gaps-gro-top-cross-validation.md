---
status: verifying
trigger: "test-gaps-gro-top-cross-validation: Existing E2E test suite has structural gaps that allowed two bugs to slip through"
created: 2026-06-19T00:00:00Z
updated: 2026-06-19T00:02:00Z
---

## Current Focus

hypothesis: All three test gaps have been fixed. Verifying comprehensive regression.
test: Run full test_output suite and chain export suites
expecting: All tests pass (both new and existing)
next_action: Update debug file to resolved status

## Symptoms

expected: Tests should catch mismatches between .gro residue names and .top [molecules] entries. Tests should catch missing custom molecule atoms in .gro files. Tests should catch .gro/.top atom count mismatches.
actual: Existing tests either manually construct IonStructure with all fields populated (bypassing propagation), pass CustomMoleculeStructure directly to IonInserter (bypassing the GUI/CLI intermediary step), or only check file existence rather than file content.
errors: No test failures when the bugs were present — the bugs were found by manual inspection.
reproduction: Run the test suite against the pre-fix code (before commits 939e5a2 and 13d0302) — all tests pass despite the bugs.
started: These test gaps have existed since the chain export tests were written.

## Eliminated

## Evidence

- timestamp: 2026-06-19T00:00:30
  checked: test_gromacs_export_chain.py lines 403-434
  found: IonStructure manually constructed with custom_molecule_atom_count=9 hardcoded (line 429). Bypasses GUI/CLI propagation entirely.
  implication: GAP 1 CONFIRMED - No test exercises the GUI/CLI propagation pattern

- timestamp: 2026-06-19T00:00:45
  checked: test_gromacs_export_chain.py lines 443-481
  found: Only checks file existence (.gro, .top, .itp) and .top content. Never reads .gro file content.
  implication: GAP 2 CONFIRMED - No .gro content validation (no residue name checks, no atom count checks)

- timestamp: 2026-06-19T00:01:00
  checked: e2e_export_helpers.py (full 529 lines)
  found: Has parse_gro_residue_names, parse_gro_atom_count, parse_top_molecules but NO cross-validation helper
  implication: GAP 3 CONFIRMED - No assert_gro_top_consistent helper exists

- timestamp: 2026-06-19T00:01:05
  checked: main_window.py lines 898-905, cli/pipeline.py lines 606-619
  found: Both GUI and CLI copy custom_molecule_atom_count from CustomMoleculeStructure to InterfaceStructure before passing to IonInserter. This is the propagation pattern that had the bug.
  implication: The propagation pattern is: CustomMoleculeStructure → set attrs on InterfaceStructure → pass InterfaceStructure to IonInserter

- timestamp: 2026-06-19T00:01:10
  checked: ion_inserter.py lines 227-228, 271-272
  found: IonInserter uses getattr(structure, 'custom_molecule_atom_count', 0) to read custom_molecule_atom_count from the source structure.
  implication: If propagation doesn't set custom_molecule_atom_count on InterfaceStructure, it defaults to 0 — the bug

- timestamp: 2026-06-19T00:01:15
  checked: write_ion_gro_file lines 1413-1419, write_ion_top_file lines 1768-1769
  found: .gro writer checks custom_molecule_count > 0 AND custom_molecule_positions is not None. .top writer checks same. Both use custom_molecule_atom_count for atom counting. If custom_molecule_atom_count=0, atoms_per_custom=0, no custom atoms written.
  implication: Missing custom_molecule_atom_count propagation causes zero custom atoms in .gro AND wrong counts in .top

- timestamp: 2026-06-19T00:01:20
  checked: gromacs_writer.py get_hydrate_guest_residue_name (line 399-429)
  found: Returns "CH4_H" or "THF_H" from ITP file (with _H suffix). Both .gro and .top use this for guest residue names.
  implication: The _H suffix bug would show as mismatch: .gro says "CH4" but .top says "CH4_H" (if get_hydrate_guest_residue_name wasn't called for .gro)

- timestamp: 2026-06-19T00:01:25
  checked: test_e2e_chain_export_1.py and test_e2e_chain_export_2.py
  found: These DO check .gro residue names and atom counts, but use write_ion_gro_file/write_ion_top_file directly (NOT the GUI exporter). The GUI exporter path (IonGROMACSExporter) .gro content is untested in chain tests.
  implication: The GUI export path for .gro content is a gap — chain export tests in test_output/ use GUI exporters but don't read .gro content

- timestamp: 2026-06-19T00:01:55
  checked: All 5 new test methods pass
  found: test_ion_export_gro_residue_names_match_top_molecules ✓, test_ion_export_gro_atom_count_matches_header ✓, test_ion_export_gro_top_cross_validation ✓, test_gui_propagation_custom_molecule_atom_count_preserved ✓, test_gro_top_cross_validation (hydrate) ✓
  implication: All new tests pass against the current (fixed) code

- timestamp: 2026-06-19T00:02:00
  checked: Full test_output suite (34 tests) + chain export suites (47 tests)
  found: All 34 + 47 = 81 tests pass with no regressions
  implication: Changes are non-breaking

## Resolution

root_cause: Three test gaps existed: (1) No test exercised the GUI/CLI propagation pattern where custom molecule attrs are copied from CustomMoleculeStructure to InterfaceStructure before passing to IonInserter, (2) No test read .gro file content after GUI/CLI export to verify residue names and atom counts, (3) No cross-validation helper asserted .gro residue names match .top [molecules] entries
fix: Added assert_gro_top_consistent() helper to e2e_export_helpers.py; added 4 new test methods to test_gromacs_export_chain.py (tests 5-8) and 1 new test method to test_gromacs_export_hydrate.py
verification: All 5 new tests pass against current code. Full regression suite (81 tests) passes with zero failures.
files_changed: [tests/e2e_export_helpers.py, tests/test_output/test_gromacs_export_chain.py, tests/test_output/test_gromacs_export_hydrate.py]
