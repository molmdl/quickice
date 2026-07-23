---
status: testing
phase: 47-testing-validation
source: [47-05-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T19:00:00Z
---

## Current Test

[all script-runnable tests complete — 4/4 pass via Workflows A+C+E]

## Tests

### 1. Unit tests cover custom guest GRO/ITP validation
expected: Custom guest validation unit tests cover: valid files (accepted), name too long (rejected), wrong comb-rule (rejected), unparseable (rejected), sys.modules injection/cleanup, _build_molecule_index with custom guest types.
result: pass
verified: Workflow A — test_custom_guest_bridge.py + test_hydrate_config_custom.py + test_build_molecule_index.py passed; Workflow E — same tests confirmed pass

### 2. E2E tests cover filled ice generation and custom guest hydrate + GROMACS export
expected: Filled ice generation tests cover C0, C1, C2, Ih, sT' lattice types. Custom guest hydrate generation + GROMACS export e2e tests pass.
result: pass
verified: Workflow C — test_hydrate_lattice_types.py passed (157 parametrized structural validation tests for all new lattice types); test_e2e_custom_guest_gui/cli_grompp.py passed

### 3. E2E tests cover mixed cage occupancy hydrate generation
expected: Mixed cage occupancy e2e tests cover mixed built-in guests (CH4+THF), sH cage occupancy, CLI --cage-guest flag. All tests pass.
result: pass
verified: Workflow C — test_e2e_mixed_cage_occupancy.py + test_e2e_sH_cage_occupancy.py passed (sH uses empirically-verified GenIce2 counts: 2 large / 6 small / 8 total)

### 4. Grompp validation tests confirm custom guest and new lattice exports produce valid GROMACS inputs
expected: Grompp validation tests (@gmx_skipif) confirm custom guest + new lattice exports pass gmx grompp with rc=0. All tests pass (or skip if gmx not available).
result: pass
verified: Workflow C — test_e2e_filled_ice_cli_hydrate_grompp.py passed (c2te@3x3x3, ice1hte@4x4x4, gmx grompp rc=0); test_e2e_custom_guest_gui/cli_grompp.py passed (gmx available)

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
