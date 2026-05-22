---
phase: pocket-edge-tests
plan: 01-03
subsystem: structure-generation
tags: [pocket, FRAG-02, assertions, cubic, guest-removal, edge-cases, invariants]
requires: [e2e-export-test]
provides: [pocket-invariants, pocket-edge-tests, cubic-guest-fix]
affects: [future-pocket-features]
tech-stack:
  added: []
  patterns: [shape-aware-distance-criterion, FRAG-02-assertions-in-pocket]
key-files:
  created:
    - tests/test_pocket_invariants.py
    - tests/test_pocket_edge_cases.py
    - tests/test_pocket_cubic_guests.py
  modified:
    - quickice/structure_generation/modes/pocket.py
decisions:
  - id: D1
    choice: Add FRAG-02 assertions inside `if` blocks (matching slab.py pattern)
    rationale: Assertions only fire when molecules are actually removed; no-overlap cases already valid
  - id: D2
    choice: Shape-aware guest removal with cubic criterion for cubic pockets
    rationale: Bug fix — cubic pockets used Euclidean distance which missed guests at cube corners
  - id: D3
    choice: Place test files in flat tests/ directory instead of tests/test_structure_generation/
    rationale: Name collision with existing tests/test_structure_generation.py module (752 lines)
  - id: D4
    choice: Defensive fallback to Euclidean distance for unknown pocket shapes
    rationale: Unknown shapes should have been caught by earlier validation, but graceful degradation is safer
completed: 2026-05-22
duration: 6m
---

# Phase Pocket-Edge-Tests Plans 01-03: Pocket Mode Edge Cases Summary

**One-liner:** Added FRAG-02 assertions to pocket.py, 51 edge-case tests, and fixed cubic pocket guest removal bug

## What Was Done

### PLAN-01: Invariants
Added 3 assertion blocks (6 assertions total) to `pocket.py` after each overlap removal phase, matching the FRAG-02 pattern in `slab.py`:
1. After water-outside-cavity removal: `assert len(water_positions) % 4 == 0` + `assert len(water_atom_names) == len(water_positions)`
2. After guest-water overlap removal: same two assertions
3. After ice-water overlap removal: same two assertions

Created `test_pocket_invariants.py` with 11 tests across 4 classes (sphere, cubic, size extremes, rectangular box).

### PLAN-02: Edge Cases
Created `test_pocket_edge_cases.py` with 33 tests across 5 classes:
- TestPocketShapeVariants: sphere/cubic validity, water count comparison, error case
- TestPocketSizeExtremes: small, near-boundary, thin-shell
- TestPocketBoxGeometry: rectangular, elongated
- TestPocketStructuralInvariants: ice-outside-cavity, water-inside-cavity, positions-within-box, atom-ordering, total-atoms, cell-matrix
- TestPocketWithHydrate: basic structure, atom ordering, ice-outside-cavity, positions-within-box

Includes 4 reusable helper functions: `assert_ice_outside_cavity`, `assert_water_inside_cavity`, `assert_positions_within_box`, `assert_atom_ordering`.

### PLAN-03: Cubic Guest Bug Fix
Fixed the guest removal bug in `assemble_pocket()` where Euclidean distance (sphere criterion) was used for ALL pocket shapes. For cubic pockets, guests near cube corners that were inside the cubic cavity but outside the inscribed sphere were NOT removed.

The fix adds shape-aware guest removal:
- Sphere: Euclidean distance (unchanged)
- Cubic: `|dx| < radius AND |dy| < radius AND |dz| < radius` criterion
- Unknown: fallback to Euclidean (defensive)

Created `test_pocket_cubic_guests.py` with 7 tests across 3 classes:
- TestCubicGuestRemoval: guests inside cubic cavity are removed
- TestSphereGuestRemoval: sphere behavior unchanged (regression)
- TestGuestAtCubeCorner: corner guest removed for cubic, kept for sphere

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test directory name collision**
- **Found during:** Running full test suite after Wave 1 commit
- **Issue:** `tests/test_structure_generation/` directory conflicts with existing `tests/test_structure_generation.py` file (752 lines). pytest import system cannot resolve both.
- **Fix:** Moved all 3 test files to flat `tests/` directory matching existing project convention. Removed `tests/test_structure_generation/` directory.
- **Files modified:** File locations only (no logic changes)
- **Commit:** 6a43594

## Test Summary

| Test File | Tests | Classes | Key Coverage |
|-----------|-------|---------|-------------|
| test_pocket_invariants.py | 11 | 4 | FRAG-02 assertions for sphere, cubic, extremes, rectangular |
| test_pocket_edge_cases.py | 33 | 5 | Shape variants, size extremes, box geometry, structural invariants, hydrate |
| test_pocket_cubic_guests.py | 7 | 3 | Cubic guest removal fix, sphere regression, corner bug |
| **Total** | **51** | **12** | |

## Verification Results

- All 51 new pocket tests pass
- All 23 existing overlap/interface tests pass (no regressions)
- 2 pre-existing failures unrelated to this change (test_cli_integration, test_triclinic_interface)
- pocket.py has 6 assertions (verified: `grep -c "assert len" pocket.py` = 6)
- Cubic guest removal uses cubic criterion (verified: `grep "pocket_shape.*cubic" pocket.py` shows 3 hits including guest removal block)

## Next Phase Readiness

No blockers. The FRAG-02 assertions and cubic guest removal fix provide a safety net for future pocket mode changes. The 51 tests verify structural invariants that would catch regressions if the overlap removal logic is modified.
