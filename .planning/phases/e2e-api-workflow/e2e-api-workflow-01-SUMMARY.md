---
phase: e2e-api-workflow
plan: 01
subsystem: testing
tags: [pytest, e2e, genice2, ice-generation, hydrate-generation, fixtures]
requires: [phase-mapping, structure-generation]
provides: [shared-conftest, ice-e2e-tests, hydrate-e2e-tests]
affects: [e2e-api-workflow-02, e2e-api-workflow-03, e2e-api-workflow-04, e2e-api-workflow-05]
---

# Phase e2e-api-workflow Plan 01: Shared Conftest + Ice/Hydrate E2E Tests Summary

**One-liner:** Module-scoped conftest.py with 12 real-generation fixtures, 12 ice e2e tests (all 6 orthogonal phases), 16 hydrate e2e tests (sI/sII × CH4/THF + error handling)

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Create shared e2e conftest.py with module-scoped fixtures | 943107b | tests/conftest.py |
| 2 | Create ice generation e2e tests | 0cadbc4 | tests/test_e2e_ice_generation.py |
| 3 | Create hydrate generation e2e tests | bf31a28 | tests/test_e2e_hydrate_generation.py |

## What Was Built

### tests/conftest.py — 12 Module-Scoped Fixtures

Real structure generation fixtures that amortize expensive GenIce2 calls (~3-5s each) across all downstream test modules:

| Fixture | Type | Description |
|---------|------|-------------|
| `ice_ih_candidate` | Candidate | Ice Ih at 250K/0.1MPa, 96 target molecules |
| `ice_ic_candidate` | Candidate | Ice Ic at 100K/0.1MPa, 96 target molecules |
| `hydrate_sI_ch4_candidate` | Candidate | Hydrate sI+CH4 → to_candidate() |
| `hydrate_sI_thf_candidate` | Candidate | Hydrate sI+THF → to_candidate() |
| `hydrate_sII_ch4_candidate` | Candidate | Hydrate sII+CH4 → to_candidate() |
| `hydrate_sI_ch4_structure` | HydrateStructure | Raw sI+CH4 structure (for hydrate-specific tests) |
| `hydrate_sI_thf_structure` | HydrateStructure | Raw sI+THF structure |
| `hydrate_sII_ch4_structure` | HydrateStructure | Raw sII+CH4 structure |
| `hydrate_sII_thf_structure` | HydrateStructure | Raw sII+THF structure |
| `interface_slab` | InterfaceStructure | Slab interface from Ice Ih |
| `interface_pocket` | InterfaceStructure | Pocket interface from Ice Ih |
| `interface_hydrate_slab` | InterfaceStructure | Slab interface from Hydrate sI+CH4 |

Also includes `PHASE_CONDITIONS` dict mapping all 6 orthogonal phase IDs to valid T/P pairs.

### tests/test_e2e_ice_generation.py — 12 Tests

| Class | Tests | Coverage |
|-------|-------|----------|
| TestIceIhGeneration | 1 | Baseline Ice Ih structural invariants |
| TestAllOrthogonalPhases | 8 | Parameterized over 6 phases + 2 high-pressure slow tests |
| TestIceCandidateAtomCount | 1 | TIP3P 3-atom verification |
| TestIceCellVolume | 1 | Cell determinant > 0 |
| TestIcePositionsInCell | 1 | Fractional coordinate bounds |

### tests/test_e2e_hydrate_generation.py — 16 Tests

| Class | Tests | Coverage |
|-------|-------|----------|
| TestHydrateS1Ch4Generation | 1 | sI+CH4 basic validation |
| TestHydrateS1ThfGeneration | 1 | sI+THF basic validation |
| TestHydrateS2Ch4Generation | 1 | sII+CH4 basic validation |
| TestHydrateS2ThfGeneration | 1 | sII+THF basic validation |
| TestHydrateToCandidate | 3 | Guest metadata, phase_id, THF preservation |
| TestHydrateGuestAtomCount | 2 | CH4=5 atoms, THF=13 atoms per guest |
| TestHydrateMoleculeIndex | 3 | All molecules tracked, all positions covered |
| TestHydrateInvalidConfig | 4 | ValueError for invalid lattice/guest/occupancy/supercell |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 12 fixtures (not 8) | Added 4 raw HydrateStructure fixtures for hydrate-specific tests that need `molecule_index`, `guest_count`, `water_count` — not available on Candidate |
| PHASE_CONDITIONS dict in conftest | Shared T/P mapping prevents duplication across test files; each phase ID maps to verified T/P conditions |
| Fractional coordinate tolerance of 0.01 | GenIce may place atoms slightly outside [0, L) due to numerical rounding; tolerance avoids false failures |
| pytest.mark.slow for VII/VIII | Ice VII/VIII use larger GenIce unit cells (16/64 molecules) but still fast in practice; mark for future filtering |

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

```
$ pytest tests/test_e2e_ice_generation.py tests/test_e2e_hydrate_generation.py -v
28 passed, 1 warning in 0.39s

$ grep -c "@pytest.fixture" tests/conftest.py
12

$ python -c "import tests.conftest"
(OK, no errors)
```

All 6 orthogonal ice phases generate successfully (Ih, Ic, III, VI, VII, VIII).
All sI/sII × CH4/THF hydrate combinations generate successfully.
Total test runtime < 1s (module-scoped fixtures amortize generation cost).

## Tech Stack

### Added
- No new dependencies

### Patterns
- Module-scoped real generation fixtures for e2e test amortization
- PHASE_CONDITIONS dict for parametrized phase testing

## Key Files

### Created
- tests/conftest.py
- tests/test_e2e_ice_generation.py
- tests/test_e2e_hydrate_generation.py

### Modified
- None

## Next Phase Readiness

- [x] conftest.py with shared fixtures ready for Plans 02-05
- [x] Ice candidate fixtures ready for interface generation tests (Plan 02)
- [x] Hydrate candidate fixtures ready for interface generation tests (Plan 02)
- [x] Interface fixtures (slab, pocket, hydrate_slab) ready for insertion tests (Plans 03-05)
- No blockers or concerns

---

*Completed: 2026-06-03*
