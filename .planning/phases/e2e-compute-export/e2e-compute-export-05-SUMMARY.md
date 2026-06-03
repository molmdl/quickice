---
phase: e2e-compute-export
plan: "05"
subsystem: test
tags: [pytest, e2e, gromacs, export, chain, invariant, CH4, THF]
---

# Phase e2e-compute-export Plan 05: Simple Chain + Cross-Chain Invariant Tests Summary

**One-liner:** F5-F7 chain export bridge tests (21 tests) + cross-chain invariant tests (4 tests) with ice-count preservation invariant

## Dependency Graph

- **requires:** e2e-compute-export-01 (e2e_export_helpers.py), e2e-compute-export-03 (ion export pattern + BUG I5 workaround)
- **provides:** F5-F7 chain export validation, cross-chain structural invariant validation
- **affects:** None (pure test addition, no production code changes)

## Tech Stack

### Added
None (uses existing test infrastructure)

### Patterns
- Cross-chain comparison testing (comparing ITP counts and molecule types across chain depths)
- Ice count invariant (crystalline base never modified by pipeline steps)
- THF 13-atom per molecule validation in chain export context

## Key Files

### Created
- `tests/test_e2e_chain_export_2.py` — 3 test classes (F5-F7), 21 test methods
- `tests/test_e2e_cross_chain_invariants.py` — 1 test class, 4 test methods

### Modified
None (no production code changes)

## Test Summary

| File | Classes | Tests | Status |
|------|---------|-------|--------|
| tests/test_e2e_chain_export_2.py | 3 | 21 | All pass |
| tests/test_e2e_cross_chain_invariants.py | 1 | 4 | All pass |
| **Total** | **4** | **25** | **All pass** |

### Test Details

**TestChainF5** (7 tests): Interface→Ion (minimal chain)
- GRO: SOL→NA→CL (3 molecule types, no interleaving)
- GRO atom count matches header and molecule_index
- TOP [molecules]: SOL, NA, CL
- TOP #include: exactly 2 ITPs (tip4p-ice.itp + ion.itp)
- ITP files valid with [ moleculetype ]
- No guests, no custom, no solutes
- Atom conservation + charge neutrality

**TestChainF6** (7 tests): Interface→Solute(CH4)→Ion
- GRO: SOL→CH4_L→NA→CL (4 molecule types)
- GRO atom count matches header
- TOP [molecules]: SOL, CH4_L, NA, CL
- TOP #include: exactly 3 ITPs (tip4p-ice.itp + ch4_liquid.itp + ion.itp)
- No custom molecules
- Solute preserved: type=="CH4", n_molecules>0
- Atom conservation + charge neutrality

**TestChainF7** (7 tests): Interface→Solute(THF)→Ion
- GRO: SOL→THF_L→NA→CL (4 molecule types, THF fits 5-char GRO limit)
- GRO atom count matches header
- TOP [molecules]: SOL, THF_L, NA, CL
- TOP #include: exactly 3 ITPs (tip4p-ice.itp + thf_liquid.itp + ion.itp)
- Solute preserved: type=="THF", n_molecules>0
- THF_L has 13 atoms per molecule (not 5 like CH4)
- Atom conservation + charge neutrality

**TestCrossChainInvariants** (4 tests): Cross-chain structural invariants
- ITP count increases with chain depth: F5(2) < F6(3) < F1(4)
- Ice count preserved across chains from same interface (F5 vs F1)
- Molecule type count increases with depth: F5(3) < F6(4) < F1(5)
- Hydrate chain adds guest ITP: F3 has ch4_hydrate.itp, F5 does not

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Ice count invariant instead of SOL count | Ion replacement varies by chain depth (F1 replaces more water than F5 due to different liquid volumes); ice count is the true invariant |
| F6/F7 use _insert_ions_from_solute() | BUG I5 workaround required for Solute→Ion pathway |
| F5 uses _insert_ions() directly | No intermediate steps; no workaround needed |
| THF 13-atom validation via solute_molecule_indices | Confirms THF_L molecule integrity through export pipeline |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Changed SOL count invariant to ice count invariant**

- **Found during:** Task 2, test_base_atom_count_preserved_across_chains
- **Issue:** Plan asserted f5_sol == f1_sol (SOL count preserved), but F5=5396 vs F1=5268 SOL. The difference is because F1 has custom molecules + solutes that displace liquid volume, causing different ion pair calculations and thus different water replacement counts.
- **Fix:** Changed assertion to verify ice molecule count is preserved (ice is never replaced by ions), while acknowledging total SOL count varies due to ion replacement differences.
- **Files modified:** tests/test_e2e_cross_chain_invariants.py
- **Commit:** 42e529d

## Authentication Gates

None — all tests run fully autonomously.

## Verification Results

All verification criteria met:
1. ✅ pytest tests/test_e2e_chain_export_2.py passes (3 classes, 21 methods)
2. ✅ pytest tests/test_e2e_cross_chain_invariants.py passes (1 class, 4 methods)
3. ✅ F5: minimal chain with 3 molecule types and 2 ITPs
4. ✅ F6: CH4 solute chain with 4 types and 3 ITPs
5. ✅ F7: THF solute chain with 4 types and 3 ITPs
6. ✅ Cross-chain: ITP count monotonically increases with depth
7. ✅ Cross-chain: Ice count preserved across chains from same interface
8. ✅ Cross-chain: Molecule type count increases with depth

## Next Phase Readiness

- e2e-compute-export phase is COMPLETE (all 5 plans executed)
- Total bridge tests: 90 (Plans 01-05 combined)
- All must-haves verified
- No blockers for downstream phases
