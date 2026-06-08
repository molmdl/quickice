---
phase: e2e-compute-export
plan: "07"
subsystem: gromacs-validation
tags: [gromacs, grompp, tpr, validation, e2e, chain, ice, interface]

# Dependency graph
requires:
  - phase: e2e-compute-export-06
    provides: "Fixed TOP writers + grompp helpers (MDP_PATH, _stage_itp_files, run_gmx_grompp)"
  - phase: e2e-compute-export-01
    provides: "e2e_export_helpers.py chain-building helpers + parsing functions"
  - phase: e2e-compute-export-03
    provides: "BUG I5 workaround (_solute_to_ion_source, _insert_ions_from_solute)"
provides:
  - "8 grompp validation tests covering ice, interface, and all 7 chain scenarios (F1-F7)"
  - "tmp/e2e-gmx-validation/ workspace with .gro, .top, .itp, .mdp, .tpr files for debugging"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "6-step grompp validation pattern: Write GRO → Write TOP → Generate ion.itp → Copy MDP → Stage ITPs → Run grompp + assert"
    - "256-molecule ice candidate for >2nm box (96 too small for 1.0nm cutoffs)"
    - "Inline hydrate generation for F3/F4 chains (_hydrate_sI_*_candidate + _make_slab_interface)"

key-files:
  created:
    - "tests/test_e2e_gmx_validation.py"
  modified: []

key-decisions:
  - "256 molecules for ice candidate (96 too small for 1.0 nm cutoffs)"
  - "F3/F4 use inline hydrate generation (not interface_slab fixture)"
  - "F1 uses interface_slab fixture (regular ice-based interface)"
  - "gmx_workspace fixture with persistent tmp/e2e-gmx-validation/ directory"

patterns-established:
  - "6-step grompp validation: Write GRO → Write TOP → Generate ion.itp → Copy MDP → Stage ITPs → Run grompp"
  - "Ice candidate: skip step 3 (no ions) and step 5 (no ITPs)"
  - "F6/F7 use _insert_ions_from_solute() (BUG I5 workaround); F5 uses _insert_ions()"
  - "F3/F4 generate hydrate inline (_hydrate_sI_ch4_candidate/_hydrate_sI_thf_candidate + _make_slab_interface)"

# Metrics
duration: 3min
completed: 2026-06-08
---

# Phase e2e-compute-export Plan 07: Grompp Validation Tests Summary

**8 GROMACS grompp validation tests validating all export scenarios (ice, interface, F1-F7) produce simulation-ready .tpr files**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-08T08:26:41Z
- **Completed:** 2026-06-08T08:29:50Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Created 8 grompp validation tests that verify exported files pass `gmx grompp` (exit code 0)
- Validated all 3 GROMACS bug fixes from Plan 06 (solute atomtypes, moleculetype name, dedup)
- F4 (most complex chain, 5 ITPs) passes — confirms all 3 bug fixes work simultaneously
- Total test count increased from 228 to 236 (8 new grompp validation tests)
- All existing bridge tests continue to pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ice, interface, and simple chain gmx validation tests** - `d3cda32` (test)
2. **Task 2: Add F1, F3, F4 complex chain gmx validation tests** - `9971e59` (feat)

## Files Created/Modified
- `tests/test_e2e_gmx_validation.py` — 8 test classes with grompp validation tests

## Test Classes

| Class | Chain | ITPs | Bug Fix Validated |
|-------|-------|------|-------------------|
| TestIceCandidateGmxValidation | Ice (256 mol) | 0 (inline) | — |
| TestInterfaceGmxValidation | Interface slab | 1 (tip4p-ice.itp) | — |
| TestChainF5GmxValidation | Interface→Ion | 2 | — |
| TestChainF6GmxValidation | Interface→Solute(CH4)→Ion | 3 | Bug 1 (solute atomtypes) |
| TestChainF7GmxValidation | Interface→Solute(THF)→Ion | 3 | Bug 1 (solute atomtypes) |
| TestChainF1GmxValidation | Interface→Custom→Solute→Ion | 4 | Bug 2+3 (moleculetype name + dedup) |
| TestChainF3GmxValidation | Hydrate→Interface→Solute→Ion | 4 | CH4_H/CH4_L coexistence |
| TestChainF4GmxValidation | Hydrate→Interface→Custom→Solute→Ion | 5 | ALL 3 bugs simultaneously |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 256 molecules for ice candidate | 96 molecules produces ~1.5×1.5×1.8 nm box (half shortest = 0.74 nm < 1.0 nm cutoffs); 256 produces ~2.2×2.3×2.7 nm (half shortest = 1.1 nm > 1.0 nm) |
| F3/F4 use inline hydrate generation | Hydrate-based chains need inline generation (_hydrate_sI_*_candidate + _make_slab_interface), not conftest.py interface_slab fixture |
| F1 uses interface_slab fixture | F1 starts from regular ice-based interface, same pattern as existing F1 test |
| gmx_workspace fixture persists files | Enables post-test debugging of .gro, .top, .itp, .tpr files under tmp/e2e-gmx-validation/ |
| No external registry needed for grompp tests | SoluteInserter creates its own internal MoleculetypeRegistry and auto-registers liquid solutes |

## Deviations from Plan

None — plan executed exactly as written.

## Authentication Gates

None — all tasks executed autonomously.

## Verification Results

All verification criteria met:
1. ✅ 8/8 gmx grompp validation tests pass with exit code 0
2. ✅ F6 (CH4 solute) passes — validates Bug 1 fix
3. ✅ F1 (custom + solute + ions) passes — validates Bug 2 fix
4. ✅ F4 (THF + custom + solute + ions) passes — validates Bug 3 fix
5. ✅ All 228 existing bridge tests continue to pass (total 236)
6. ✅ Workspace files persist under tmp/e2e-gmx-validation/
7. ✅ .tpr files generated by gmx grompp

## Next Phase Readiness

- e2e-compute-export phase is COMPLETE (7/7 plans done)
- All GROMACS export pipeline components validated: bridge tests + grompp validation
- 236 total tests (228 bridge + 8 grompp validation)
- Ready for milestone completion and phase graduation
