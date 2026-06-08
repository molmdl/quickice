---
phase: e2e-compute-export
plan: "09"
subsystem: testing
tags: [gromacs, grompp, validation, e2e, export, sII-hydrate]

requires:
  - phase: e2e-compute-export-08
    provides: "cross-combination grompp tests (4 new tests)"
provides:
  - "sII hydrate helper functions in e2e_export_helpers.py"
  - "2 sII grompp validation tests"
affects: []

key-files:
  created: []
  modified: ["tests/e2e_export_helpers.py", "tests/test_e2e_gmx_validation.py"]

key-decisions:
  - "sII uses same ITP filenames as sI (ch4_hydrate.itp, thf_hydrate.itp)"
  - "Clean stale .tpr backups before gmx grompp to prevent 99-backup limit failure"

duration: 3min
completed: 2026-06-08
---

# Phase e2e-compute-export Plan 09: sII Hydrate Grompp Validation Summary

**sII hydrate grompp validation tests covering F3-sII (CH4) and F4-sII (THF) chains with stale backup cleanup fix**

## Performance

- Execution time: ~3 minutes
- All 14 grompp validation tests pass (8 original + 4 cross-combinations + 2 sII)
- All 116 bridge tests pass (no regressions)
- Total: 130 tests across e2e-compute-export

## Accomplishments

1. Added `_hydrate_sII_ch4_candidate()` and `_hydrate_sII_thf_candidate()` helper functions to e2e_export_helpers.py
   - Mirror existing sI helpers with `lattice_type="sII"`
   - sII hydrates have different cage structure (5^12 6^4 large + 5^12 small) from sI (5^12 + 5^12 6^2)

2. Added TestChainF3SIIGmxValidation — F3-sII chain (Hydrate sII-CH4→Interface→Solute(CH4)→Ion, 4 ITPs)
   - Tests sII hydrate guest export through the full grompp pipeline
   - Validates CH4_H hydrate guest + CH4_L solute coexistence with sII lattice
   - GRO/TOP files: f3_sII.gro, f3_sII.top

3. Added TestChainF4SIIGmxValidation — F4-sII chain (Hydrate sII-THF→Interface→Custom→Solute(THF)→Ion, 5 ITPs)
   - Most complex sII chain — tests all 3 bug fixes with sII lattice
   - Validates THF_H hydrate guest + etoh custom + THF_L solute atomtype dedup with sII lattice
   - GRO/TOP files: f4_sII.gro, f4_sII.top

4. Fixed stale `.tpr` backup accumulation in `run_gmx_grompp()`
   - GROMACS refuses to create more than 99 backup `.tpr` files, causing grompp to fail on re-runs
   - Added cleanup of `em.tpr*` files before each grompp invocation
   - This fix benefits ALL grompp validation tests, not just sII

5. Verified no regressions across the full e2e-compute-export test suite (130 total tests)

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | b22696f | feat(e2e-compute-export-09): add sII hydrate grompp validation tests |
| 1 | ed494d3 | fix(e2e-compute-export-09): clean stale .tpr backups before gmx grompp |
| 2 | N/A | Verification only — no file changes |

## Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| tests/e2e_export_helpers.py | Modified | Added `_hydrate_sII_ch4_candidate()` and `_hydrate_sII_thf_candidate()` helper functions + stale .tpr cleanup in `run_gmx_grompp()` |
| tests/test_e2e_gmx_validation.py | Modified | Added 2 sII test classes (TestChainF3SIIGmxValidation, TestChainF4SIIGmxValidation) + updated imports |

## Decisions Made

1. **sII uses same ITP filenames as sI** — ch4_hydrate.itp and thf_hydrate.itp are the same for both lattice types; the difference is in the candidate structure (different water/guest atom counts)
2. **Clean stale .tpr backups before grompp** — The persistent `gmx_workspace` accumulates GROMACS backup files; cleaning before each run prevents the 99-backup limit error
3. **sII GRO/TOP naming uses `_sII` suffix** — f3_sII.gro, f4_sII.gro (distinct from sI equivalents f3.gro, f4.gro to avoid workspace collisions)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed stale .tpr backup accumulation in run_gmx_grompp()**

- **Found during:** Task 1 (re-running sII grompp tests)
- **Issue:** GROMACS refuses to create more than 99 backup `.tpr` files ("Won't make more than 99 backups of em.tpr for you"), causing grompp to return exit code 1 on persistent workspaces with accumulated backups
- **Fix:** Added cleanup of `em.tpr*` files and the target `tpr_file` before each grompp invocation in `run_gmx_grompp()`
- **Files modified:** tests/e2e_export_helpers.py
- **Commit:** ed494d3

## Issues Encountered

None beyond the stale backup fix documented above.

## Next Phase Readiness

- All 14 grompp validation tests pass across 14 test classes
- sI and sII hydrate lattice types both validated through grompp
- All 3 GROMACS-simulation-blocking bug fixes validated with sII lattice
- Stale backup cleanup makes tests robust for repeated execution
- e2e-compute-export phase COMPLETE (9/9 plans, 130 total tests)
