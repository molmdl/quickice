---
status: complete
phase: 44-gui-integration
source: [44-02-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T19:00:00Z
---

## Current Test

[2 pass, 1 issue (major), 1 skipped (GUI cage rows) — issue on test 2 (long name silently ignored)]

## Tests

### 1. Hydrate tab lattice dropdown includes all new lattice types
expected: Open the QuickIce GUI, go to the Hydrate tab. The lattice type dropdown should include all 10 lattice types. Selecting any new type should not crash and should update the cage info display.
result: pass
verified: Workflow F (user GUI verification) — dropdown lists all 10 types, selecting each works, no crash, cage info updates

### 2. Upload custom guest .gro+.itp pair with validation feedback
expected: In the Hydrate tab, use the custom guest upload panel to select a .gro and .itp file pair. If invalid, a specific validation error message should be displayed.
result: issue
reported: "long residue name upload (etoh_long_name.itp, 'ETHANOL' 6 chars) showed no validation error, generation proceeded, but export had no MOL — custom guest silently ignored, fell back to built-in CH4 only"
severity: major
verified: |
  Workflow F (user GUI verification) — uploaded etoh_long_name.itp.
  No validation error at upload. Export .top [molecules] = SOL+CH4_H only (no MOL_H).
  Comb-rule=1 upload (test 6) correctly rejected. Only the long-name validation is broken.

### 3. Cage-type guest assignment controls for mixed occupancy
expected: In the Hydrate tab, select a multi-cage lattice. Per-cage-type rows should appear with QComboBox + QDoubleSpinBox for each cage type. Changing lattice should rebuild rows.
result: skipped
reason: Requires GUI + human verification (headless environment). CLI --cage-guest flag verified in Workflow B.

### 4. Depol mode dropdown with strict as default
expected: In the Hydrate tab, a depol mode dropdown should be present with "strict" and "optimal". Default should be "strict".
result: pass
verified: Workflow F (user GUI verification) — depol dropdown present with strict/optimal, default strict

## Summary

total: 4
passed: 2
issues: 1
pending: 0
skipped: 1

## Gaps

- truth: "Upload custom guest .gro+.itp pair with validation feedback"
  status: failed
  reason: "User reported: long residue name upload (etoh_long_name.itp, 'ETHANOL' 6 chars) showed no validation error, generation proceeded, but export had no MOL — custom guest silently ignored, fell back to built-in CH4 only"
  severity: major
  test: 2
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
