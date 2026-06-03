---
phase: e2e-api-workflow
plan: 03
subsystem: testing
tags: [pytest, e2e, custom-molecule, validation, random-placement, custom-placement, overlap-checking]
requires: [e2e-api-workflow-01]
provides: [custom-molecule-e2e-tests]
affects: [e2e-api-workflow-04, e2e-api-workflow-05]
---

# Phase e2e-api-workflow Plan 03: Custom Molecule Validation & Placement E2E Tests Summary

**One-liner:** 20 e2e tests covering GRO/ITP validation (atom count, residue name, atomtypes), random placement with overlap checking and water removal, custom placement with bounds/overlap validation, and edge cases (registry, hydrate interface)

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Create custom molecule validation and random placement tests | b56c43d | tests/test_e2e_custom_molecule.py |
| 2 | Add custom placement validation and edge case tests | 4451244 | tests/test_e2e_custom_molecule.py |

## What Was Built

### tests/test_e2e_custom_molecule.py — 20 Tests

| Class | Tests | Coverage |
|-------|-------|----------|
| TestCustomMoleculeValidation | 6 | GRO/ITP validation: valid etoh, atom count mismatch, generic residue name, real residue name mismatch, ITP without atomtypes, parse non-gro file error |
| TestRandomPlacement | 7 | Random placement: custom structure production, liquid region bounds, no ice overlap (cKDTree), water removal, complete system, concentration→count, concentration roundtrip |
| TestCustomPlacement | 5 | Custom placement: valid position, out of bounds, overlap detected, no-interface invalid, place_custom with user positions |
| TestCustomMoleculeEdgeCases | 2 | Moleculetype registration in registry, hydrate interface preserves guests |

### Test Helpers

- `write_minimal_gro()`: Creates temporary GRO files with configurable atom count and residue name
- `write_minimal_itp()`: Creates temporary ITP files with/without atomtypes section
- Uses `tmp_path` pytest fixture for temporary files
- Uses `interface_slab` and `interface_hydrate_slab` fixtures from conftest.py

### Validation Tests (Workflow 5a) — 6 Tests

1. **test_validate_etoh_molecule_valid** — Valid etoh.gro/itp passes with is_valid=True, no errors, gro_atom_count=9
2. **test_validate_atom_count_mismatch** — GRO with 10 atoms vs ITP 9 atoms → is_valid=False, "atom count mismatch"
3. **test_validate_generic_residue_name_no_mismatch** — GRO residue "MOL" (generic) + ITP "etoh" → residue_name_mismatch=False
4. **test_validate_real_residue_name_mismatch** — GRO residue "XXX_CUSTOM" (non-generic) + ITP "etoh" → residue_name_mismatch=True
5. **test_validate_itp_without_atomtypes_warning** — ITP without [ atomtypes ] → is_valid=True, warning mentions "atomtypes"
6. **test_parse_non_gro_file_raises_error** — Non-existent file → FileNotFoundError/ValueError

### Random Placement Tests (Workflow 5b) — 7 Tests

7. **test_random_placement_produces_custom_structure** — 3 ethanol molecules → custom_molecule_count=3, custom_molecule_atom_count=27
8. **test_random_placement_molecules_in_liquid_region** — All 5 molecule COMs within liquid region bounds (±0.2 nm tolerance)
9. **test_random_placement_no_ice_overlap** — cKDTree confirms min distance to ice ≥ 0.3 nm
10. **test_random_placement_water_removal** — custom.water_atom_count < interface_slab.water_atom_count
11. **test_random_placement_complete_system** — Total atoms = ice + water + guest + custom
12. **test_molecule_count_from_concentration** — calculate_molecule_count(1.0, V) returns positive integer
13. **test_concentration_roundtrip** — C→N→C₂ with |C₂-C| < 0.01

### Custom Placement Tests (Workflow 5c) — 5 Tests

14. **test_custom_placement_at_valid_position** — (1.5, 1.5, 4.0) in liquid region → within_bounds=True, is_valid=True
15. **test_custom_placement_out_of_bounds** — (0.5, 0.5, 0.1) in ice region → within_bounds=False, is_valid=False
16. **test_custom_placement_overlap_detected** — (0.1, 0.1, 0.1) → has_overlap=True or within_bounds=False
17. **test_custom_placement_no_interface_returns_invalid** — No liquid region → is_valid=False, "no liquid" in error
18. **test_place_custom_with_user_positions** — place_custom() yields 1 molecule with correct complete system counts

### Edge Case Tests — 2 Tests

19. **test_custom_molecule_moleculetype_registration** — moleculetype_name set, registry has custom_* keys
20. **test_custom_molecule_from_hydrate_interface** — Hydrate interface preserves guests, places 2 custom molecules

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| cKDTree for overlap verification | Reuses scipy.spatial.cKDTree (already in codebase) for efficient nearest-neighbor queries in ice overlap tests |
| 0.2 nm tolerance for COM bounds | Molecules extend beyond their center-of-mass; tolerance allows atoms near liquid region boundary |
| MoleculetypeRegistry._registered for key check | Registry uses `_registered` dict (not `_entries`); check for keys starting with "custom_" |
| tmp_path for temporary GRO/ITP files | pytest built-in fixture for per-test temporary directories; no cleanup needed |
| synthetic InterfaceStructure for no-water test | Create InterfaceStructure with water_atom_count=0 to test validate_single_placement edge case |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MoleculetypeRegistry._entries → _registered**

- **Found during:** Task 2 (test_custom_molecule_moleculetype_registration)
- **Issue:** Plan assumed `_entries` attribute but MoleculetypeRegistry uses `_registered` dict
- **Fix:** Changed test to check `inserter.registry._registered` with `k.startswith("custom_")`
- **Files modified:** tests/test_e2e_custom_molecule.py
- **Commit:** 4451244

## Verification Results

```
$ pytest tests/test_e2e_custom_molecule.py -v
20 passed, 1 warning in 1.80s

$ pytest tests/test_e2e_custom_molecule.py -v -k "validate or random"
12 passed, 1 deselected in 1.22s

$ pytest tests/test_e2e_custom_molecule.py -v -k "custom_placement or edge"
8 passed in 0.63s
```

All 5 must-have truths verified:
- ✅ Custom molecule GRO/ITP validation catches atom count mismatches
- ✅ Random placement produces molecules within liquid region bounds
- ✅ Custom placement validates bounds and detects overlaps
- ✅ Water removal reduces water_atom_count after molecule insertion
- ✅ Generic residue name 'MOL' does not trigger mismatch warning

## Tech Stack

### Added
- No new dependencies

### Patterns
- cKDTree-based overlap verification in tests
- Temporary GRO/ITP file generation for validation edge cases
- Synthetic InterfaceStructure for no-liquid-region edge case

## Key Files

### Created
- tests/test_e2e_custom_molecule.py

### Modified
- None

## Next Phase Readiness

- [x] Custom molecule e2e tests ready for solute insertion tests (Plan 04)
- [x] CustomMoleculeStructure accessible for solute source tests (Plan 04)
- [x] Hydrate interface with guests tested for solute + custom coexistence (Plan 04)
- [x] MoleculetypeRegistry registration pattern verified for CH4_H/CH4_L tests (Plan 04)
- No blockers or concerns

---

*Completed: 2026-06-03*
