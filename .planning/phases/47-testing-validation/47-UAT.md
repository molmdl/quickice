---
status: testing
phase: 47-testing-validation
source: [47-05-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T12:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Unit tests cover custom guest GRO/ITP validation
expected: |
  Run the custom guest validation unit tests. They should cover: valid custom guest files
  (accepted), name too long (>3 chars rejected with specific message), wrong comb-rule
  (comb-rule=1 rejected, comb-rule=2 accepted, no [defaults] section accepted), unparseable
  files (rejected with parse error). Also verify sys.modules injection/cleanup tests and
  _build_molecule_index tests with custom guest types pass.
awaiting: user response

## Tests

### 1. Unit tests cover custom guest GRO/ITP validation
expected: Run the custom guest validation unit tests. They should cover: valid custom guest files (accepted), name too long (>3 chars rejected with specific message), wrong comb-rule (comb-rule=1 rejected, comb-rule=2 accepted, no [defaults] section accepted), unparseable files (rejected with parse error). Also verify sys.modules injection/cleanup tests and _build_molecule_index tests with custom guest types pass.
result: [pending]

### 2. E2E tests cover filled ice generation and custom guest hydrate + GROMACS export
expected: Run the e2e test suite. Filled ice generation tests should cover C0, C1, C2, Ih, sT' lattice types (parametrized structural validation, ~157 tests). Custom guest hydrate generation + GROMACS export e2e tests should cover the full workflow (generate → export → grompp). All tests should pass.
result: [pending]

### 3. E2E tests cover mixed cage occupancy hydrate generation
expected: Run the mixed cage occupancy e2e tests. They should cover: mixed built-in guests (CH4+THF) in different cage types, sH cage occupancy (with corrected cage_type_map), CLI --cage-guest flag. All tests should pass. The sH test should use empirically-verified GenIce2 counts (2 large / 6 small / 8 total for sH 1x1x1).
result: [pending]

### 4. Grompp validation tests confirm custom guest and new lattice exports produce valid GROMACS inputs
expected: Run the grompp validation tests (@gmx_skipif). They should confirm: custom guest hydrate exports (GUI + CLI) pass `gmx grompp` with rc=0, new lattice type exports pass grompp, filled-ice (c2te, ice1hte) CLI hydrate-only branch grompp passes. All tests should pass (or skip if gmx not available).
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0

## Gaps

[none yet]
