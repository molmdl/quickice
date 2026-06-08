---
phase: e2e-compute-export
plan: "08"
subsystem: testing
tags: [gromacs, grompp, validation, e2e, export, cross-combination]

requires:
  - phase: e2e-compute-export-07
    provides: "grompp validation helpers and existing 8 tests"
provides:
  - "4 cross-combination grompp validation tests"
  - "F2 (Interface→Custom→Ion) validation"
  - "F1+THF, F3+THF, F4+CH4 combinations"
affects: [e2e-compute-export-09]

key-files:
  created: []
  modified: ["tests/test_e2e_gmx_validation.py"]

key-decisions:
  - "F2 uses _insert_ions() not _insert_ions_from_solute() since no solute in chain"
  - "Cross-combination naming: f1_thf, f3_thf, f4_ch4 (distinct from original f1, f3, f4)"

duration: 1min
completed: 2026-06-08
---

# Phase e2e-compute-export Plan 08: Missing Grompp Cross-Combinations Summary

**4 cross-combination grompp validation tests covering F2 (no-solute), F1+THF, F3+THF, F4+CH4 atomtype dedup scenarios**

## Performance

- Execution time: ~1 minute
- All 12 grompp validation tests pass (8 existing + 4 new)
- All 116 bridge tests pass (no regressions)
- Total: 128 tests across e2e-compute-export

## Accomplishments

1. Added TestChainF2GmxValidation — F2 chain (Interface→Custom→Ion, 3 ITPs)
   - Tests Bug 2 fix (moleculetype name "etoh" in [molecules]) without solute atomtypes
   - Tests Bug 3 fix (custom-only atomtype dedup) without GAFF2 interference
   - Uses `_insert_ions()` (not `_insert_ions_from_solute()`) since no solute in chain

2. Added TestChainF1ThfGmxValidation — F1+THF chain (Interface→Custom→Solute(THF)→Ion, 4 ITPs)
   - Tests THF solute atomtypes (os, c5, hc, h1) + etoh custom atomtypes (oh, ho, hc)
   - "hc" shared between THF GAFF2 and etoh — validates dedup

3. Added TestChainF3ThfGmxValidation — F3+THF chain (Hydrate sI-CH4→Interface→Solute(THF)→Ion, 4 ITPs)
   - Tests CH4_H hydrate guest (c3, hc) + THF_L solute (os, c5, hc, h1)
   - "hc" shared across hydrate guest and solute — validates dedup

4. Added TestChainF4Ch4GmxValidation — F4+CH4 chain (Hydrate sI-THF→Custom→Solute(CH4)→Ion, 5 ITPs)
   - Most complex dedup scenario: THREE atomtype sources all sharing "hc"
   - THF_H hydrate guest (os, c5, hc, h1) + CH4_L solute (c3, hc) + etoh custom (oh, ho, hc)
   - Validates that all 3 bug fixes work together in the most demanding combination

5. Verified no regressions across the full e2e-compute-export test suite

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | df00279 | test(e2e-compute-export-08): add 4 cross-combination grompp validation tests |
| 2 | N/A | Verification only — no file changes |

## Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| tests/test_e2e_gmx_validation.py | Modified | Added 4 new test classes (TestChainF2GmxValidation, TestChainF1ThfGmxValidation, TestChainF3ThfGmxValidation, TestChainF4Ch4GmxValidation) + updated module docstring |

## Decisions Made

1. **F2 uses `_insert_ions()` not `_insert_ions_from_solute()`** — F2 chain has no solute, so ions are inserted directly from custom molecule structure using the standard path
2. **Cross-combination GRO/TOP naming uses underscore suffix** — f1_thf.gro, f3_thf.gro, f4_ch4.gro (distinct from original f1.gro, f3.gro, f4.gro to avoid workspace collisions)
3. **All 4 new classes follow the exact same 6-step pattern** as existing classes: Write GRO → Write TOP → Generate ion.itp → Copy MDP → Stage ITPs → Run grompp + assert exit code 0

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — all 4 new tests pass gmx grompp with exit code 0 on first run.

## Next Phase Readiness

- All 12 grompp validation tests pass across 12 test classes
- F2 (no-solute custom path), F1+THF, F3+THF, F4+CH4 all validated
- Bug fixes (atomtypes, moleculetype name, dedup) confirmed robust across all cross-combinations
- Ready for Plan 09 (final plan if any)
