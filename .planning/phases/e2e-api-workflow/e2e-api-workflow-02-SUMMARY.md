---
phase: e2e-api-workflow
plan: 02
subsystem: testing
tags: [pytest, e2e, interface-generation, slab, pocket, piece, ice-ii-rejection, error-handling]
requires: [e2e-api-workflow-01, phase-mapping, structure-generation]
provides: [interface-e2e-tests]
affects: [e2e-api-workflow-03, e2e-api-workflow-04, e2e-api-workflow-05]
tech-stack:
  added: []
  patterns: [inline-fixture-for-variants, molecule-count-consistency-over-molecule-index]
key-files:
  created: [tests/test_e2e_interface_generation.py]
  modified: []
---

# Phase e2e-api-workflow Plan 02: Interface Generation E2E Tests Summary

**One-liner:** 21 interface generation e2e tests covering slab/pocket/piece modes, hydrate→interface, Ice II rejection, structural invariants (atom counts, cell volume), and error handling

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Create interface generation e2e tests for all modes | 1336179 | tests/test_e2e_interface_generation.py |
| 2 | Add edge case and error handling tests | 1336179 | tests/test_e2e_interface_generation.py |

Note: Tasks 1 and 2 were combined into a single commit since they modify the same file and the edge cases were written alongside the core tests for coherence.

## What Was Built

### tests/test_e2e_interface_generation.py — 21 Tests

| Class | Tests | Coverage |
|-------|-------|----------|
| TestIceIhSlabInterface | 5 | Slab mode generation, atom count sum, cell volume, water availability, positions within bounds |
| TestIceIhPocketInterface | 1 | Pocket mode with ice + water verification |
| TestIceIhPieceInterface | 1 | Piece mode with atom count invariant |
| TestHydrateSlabInterface | 2 | Hydrate sI+CH4→slab: guest tracking + atom count sum |
| TestInterfaceMoleculeIndex | 2 | Molecule count consistency (ice+water+guest), hydrate molecule counts |
| TestIceIIRejection | 2 | InterfaceGenerationError for Ice II, validate_interface_config rejection |
| TestIceIcSlabInterface | 1 | Ice Ic (cubic) slab mode structural invariants |
| TestPocketEdgeCases | 1 | Pocket diameter >= box → InterfaceGenerationError |
| TestPieceEdgeCases | 1 | Box smaller than ice cell → InterfaceGenerationError |
| TestSlabEdgeCases | 2 | Thin water layer handling, box_z mismatch error |
| TestInvalidConfigEdgeCases | 3 | Negative box, zero box, unknown mode errors |

### Inline Fixtures (module-scoped)

| Fixture | Type | Description |
|---------|------|-------------|
| `ice_ic_candidate` | Candidate | Ice Ic at 100K/0.1MPa, 96 target molecules |
| `ice_ii_candidate` | Candidate | Ice II at 200K/300MPa, 96 target molecules (for rejection testing) |
| `interface_piece` | InterfaceStructure | Piece-mode interface from Ice Ih |

### Test Coverage Summary

- ✅ Ice Ih + slab mode (5 tests, most comprehensive)
- ✅ Ice Ih + pocket mode (1 test)
- ✅ Ice Ih + piece mode (1 test)
- ✅ Ice Ic + slab mode (1 test)
- ✅ Hydrate sI+CH4 + slab mode (2 tests)
- ✅ Ice II rejection (2 tests)
- ✅ Molecule count consistency (2 tests)
- ✅ Edge cases: pocket diameter, piece box size, thin water, box_z mismatch (4 tests)
- ✅ Invalid config: negative/zero box, unknown mode (3 tests)

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Molecule count consistency over molecule_index | InterfaceStructure.molecule_index is NOT populated by generate_interface() — it's empty `[]`. Downstream steps (ion_inserter, solute_inserter, custom_molecule_inserter) build it from metadata. Tests verify ice_nmolecules + water_nmolecules + guest_nmolecules consistency instead. |
| Inline fixtures for Ice Ic, Ice II, piece mode | These variants aren't in shared conftest.py; creating them inline keeps conftest clean while still amortizing cost via module scope |
| Combined Tasks 1+2 into single commit | Both tasks write to the same file; writing them together ensures consistency and avoids an intermediate broken state |
| Ice II generated at 200K/300MPa | Confirmed via lookup_phase: 200K/300MPa → ice_ii. GenIce2 supports Ice II generation, but validate_interface_config rejects it before interface generation |
| box_z=4.1 for thin water test | Slab mode requires box_z = 2*ice_thickness + water_thickness; with ice_thickness=2.0 and water_thickness=0.1, box_z must be 4.1 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] molecule_index test adapted to actual API behavior**

- **Found during:** Task 1, test 6 (test_interface_molecule_index_tracks_all_molecules)
- **Issue:** Plan specified verifying `interface.molecule_index` has entries for ice, water, and guest molecules. In reality, InterfaceStructure.molecule_index is empty `[]` — it's only populated by downstream inserters (IonInserter._build_molecule_index_from_structure, etc.)
- **Fix:** Adapted test to verify molecule COUNT consistency (ice_nmolecules + water_nmolecules + guest_nmolecules) and atom count metadata instead. Added clear docstring explaining the design choice.
- **Files modified:** tests/test_e2e_interface_generation.py (TestInterfaceMoleculeIndex class)
- **Commit:** 1336179

**2. [Rule 2 - Missing Critical] Added validate_interface_config test for Ice II**

- **Found during:** Task 1, test 8 (test_ice_ii_rejection_raises_error)
- **Issue:** Plan only tested generate_interface() rejection, but the fail-fast check is actually in validate_interface_config(). Testing both ensures the rejection happens BEFORE expensive generation operations.
- **Fix:** Added test_ice_ii_validation_rejects_before_generation that verifies validate_interface_config() rejects Ice II with "rhombohedral" in the error message
- **Files modified:** tests/test_e2e_interface_generation.py (TestIceIIRejection class)
- **Commit:** 1336179

**3. [Rule 2 - Missing Critical] Added additional edge case tests beyond plan**

- **Found during:** Task 2
- **Issue:** Plan specified 4 edge case tests; added 5 more for complete coverage of validate_interface_config error paths
- **Fix:** Added: slab box_z mismatch, negative box dimension, zero box dimension, unknown mode tests
- **Files modified:** tests/test_e2e_interface_generation.py (TestSlabEdgeCases, TestInvalidConfigEdgeCases)
- **Commit:** 1336179

## Verification Results

```
$ pytest tests/test_e2e_interface_generation.py -v
21 passed, 5 warnings in 0.96s

$ pytest tests/test_e2e_ice_generation.py tests/test_e2e_hydrate_generation.py tests/test_e2e_interface_generation.py -v
49 passed, 6 warnings in 1.28s
```

All 49 e2e tests pass (28 from Plan 01 + 21 from Plan 02).
Module-scoped fixtures amortize generation cost; total runtime < 2 seconds.

## Tech Stack

### Added
- No new dependencies

### Patterns
- Inline module-scoped fixtures for variant-specific tests (Ice Ic, Ice II, piece mode)
- Molecule count consistency checks (over molecule_index) for InterfaceStructure

## Key Files

### Created
- tests/test_e2e_interface_generation.py

### Modified
- None

## Next Phase Readiness

- [x] Interface generation tested for all 3 modes (slab, pocket, piece)
- [x] Hydrate → Interface tested with guest tracking
- [x] Ice II rejection verified with InterfaceGenerationError
- [x] Structural invariants (atom counts, cell volume) verified
- [x] Error handling tests for invalid configurations
- [x] No blockers or concerns for Plans 03-05
- Interface fixtures from conftest.py ready for custom molecule tests (Plan 03)
- ice_ih_candidate fixture ready for all downstream insertion tests

---

*Completed: 2026-06-03*
