---
phase: e2e-api-workflow
plan: 04
subsystem: testing
tags: [pytest, e2e, solute-insertion, CH4, THF, moleculetype-registry, custom-molecule-source, coexistence]
requires: [e2e-api-workflow-01]
provides: [solute-insertion-e2e-tests]
affects: [e2e-api-workflow-05]
---

# Phase e2e-api-workflow Plan 04: Solute Insertion E2E Tests Summary

**One-liner:** 17 e2e tests covering solute insertion from Interface/Custom sources, CH4_H/CH4_L coexistence (P0), THF 13-atom solutes, zero concentration, and attribute propagation through workflow chain

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Create solute insertion and cross-source tests | 2b20018 | tests/test_e2e_solute_insertion.py |

## What Was Built

### tests/test_e2e_solute_insertion.py — 17 Tests

| Class | Tests | Coverage |
|-------|-------|----------|
| TestSoluteFromInterfaceSource | 5 | CH4/THF from Interface source, liquid region bounds, no solute-solute overlap, zero concentration |
| TestCH4HCH4LCoexistence | 2 | P0 S3: CH4_H/CH4_L registry coexistence, hydrate guests preserved after insertion |
| TestSoluteFromCustomMoleculeSource | 2 | Custom→Solute workflow, custom attributes propagated (positions, atom_names, moleculetype, paths) |
| TestSoluteMoleculeCount | 2 | calculate_molecule_count returns positive int, approximate count matches C×V×NA |
| TestS4S5Combinations | 2 | S4: THF_H/THF_L coexistence, S5: CH4 hydrate + THF liquid mixed |
| TestSoluteAttributePropagation | 4 | Water removal, CH4 molecule indices (5 atoms), THF molecule indices (13 atoms), cell matches interface |

### Basic Insertion Tests (Workflow 6b — from Interface source) — 5 Tests

1. **test_solute_ch4_from_interface_source** — SoluteInserter with 0.5M CH4 produces SoluteStructure with n_molecules>0, solute_type="CH4", positions.shape[0]==n_molecules*5
2. **test_solute_thf_from_interface_source** — THF at 0.5M produces 13-atom molecules (P1 test S2)
3. **test_solutes_in_liquid_region_only** — Each molecule's COM within liquid region bounds (±0.2 nm tolerance)
4. **test_no_solute_solute_overlap** — cKDTree pairwise COM distance check exceeds min_separation*0.5
5. **test_zero_concentration_no_solutes** — 0.0M → n_molecules==0, positions.shape==(0,3), no crash

### P0 Critical: CH4_H/CH4_L Coexistence (S3) — 2 Tests

6. **test_ch4_h_ch4_l_coexistence_in_registry** — Register hydrate guest CH4_H, then insert CH4 liquid solutes CH4_L; verify BOTH in registry with DISTINCT names (P0 S3)
7. **test_hydrate_guests_preserved_after_solute_insertion** — After solute insertion, interface_structure still has guest_nmolecules>0 and guest_atom_count>0

### From Custom Molecule Source (Workflow 6c) — 2 Tests

8. **test_solute_from_custom_molecule_source** — Interface→Custom→Solute chain: custom_molecule_count>0, n_molecules>0
9. **test_solute_custom_attrs_preserved** — Custom attributes propagate: positions, atom_names, moleculetype, gro_path, itp_path

### Molecule Count Calculation — 2 Tests

10. **test_solute_molecule_count_from_concentration** — calculate_molecule_count(1.0, volume) returns positive int
11. **test_solute_molecule_count_approximately_correct** — At 0.5M, count within ±1 of C×V×NA

### S4/S5 Combinations (P2) — 2 Tests

12. **test_hydrate_thf_thf_liquid_coexistence** — THF hydrate interface → THF liquid solutes; THF_H and THF_L distinct in registry (S4)
13. **test_hydrate_ch4_thf_liquid_mixed** — CH4 hydrate interface → THF liquid solutes; both CH4_H and THF_L in registry, guests preserved (S5)

### Attribute Propagation — 4 Tests

14. **test_water_removal_after_solute_insertion** — interface_structure.water_atom_count < original water_atom_count
15. **test_solute_molecule_indices_valid** — Each (start, end) in molecule_indices has end-start==5 for CH4
16. **test_thf_molecule_indices_valid** — Each (start, end) in molecule_indices has end-start==13 for THF
17. **test_solute_cell_matches_interface** — SoluteStructure.cell matches source InterfaceStructure.cell

## Decisions Made

| Decision | Rationale | Status |
|----------|-----------|--------|
| Register hydrate guest before solute insertion | Simulates real workflow where hydrate export registers guests first, then solute insertion registers liquid solutes | Applied |
| Inline THF hydrate interface for S4 test | conftest.py only has CH4 hydrate fixture; THF hydrate generated inline to avoid fixture explosion | Applied |
| 0.2 nm COM tolerance for liquid region bounds | Molecules extend beyond center-of-mass; matches pattern from test_e2e_custom_molecule.py | Applied |
| THF_ATOMS_PER_MOLECULE=13 and CH4_ATOMS_PER_MOLECULE=5 as module constants | Avoids magic numbers, matches MOLECULE_TYPE_INFO in types.py | Applied |

## Success Criteria Verification

| # | Criterion | Status |
|---|-----------|--------|
| 1 | test_e2e_solute_insertion.py has 15+ tests, all pass | ✓ 17 tests, all pass |
| 2 | P0 test: CH4_H/CH4_L coexistence verified (S3) | ✓ test_ch4_h_ch4_l_coexistence_in_registry |
| 3 | Both Interface and Custom Molecule sources tested | ✓ 5 Interface source + 2 Custom source |
| 4 | THF solute (13 atoms) tested (S2) | ✓ test_solute_thf_from_interface_source |
| 5 | Zero concentration produces zero solutes without crash | ✓ test_zero_concentration_no_solutes |
| 6 | Attribute propagation from CustomMoleculeStructure to SoluteStructure verified | ✓ test_solute_custom_attrs_preserved |
| 7 | Water removal after solute insertion verified | ✓ test_water_removal_after_solute_insertion |

## Deviations from Plan

None — plan executed exactly as written.

## Tech Stack

### Added
- No new dependencies (uses existing scipy.spatial.cKDTree, numpy, pytest)

### Patterns
- Inline hydrate interface generation for test variants not in conftest.py
- Hydrate guest registration before solute insertion (simulates real workflow order)

## Metrics

- **Duration:** ~2 minutes
- **Completed:** 2026-06-03
- **Total e2e tests now:** 86 (28 ice/hydrate + 21 interface + 20 custom molecule + 17 solute insertion)
