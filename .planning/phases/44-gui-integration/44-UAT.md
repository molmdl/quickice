---
status: complete
phase: 44-gui-integration
source: [44-02-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T19:00:00Z
---

## Current Test

[4/4 pass — Issue 1 fixed (commit 0baf0043)]

## Tests

### 1. Hydrate tab lattice dropdown includes all new lattice types
expected: Open the QuickIce GUI, go to the Hydrate tab. The lattice type dropdown should include all 10 lattice types. Selecting any new type should not crash and should update the cage info display.
result: pass
verified: Workflow F (user GUI verification) — dropdown lists all 10 types, selecting each works, no crash, cage info updates

### 2. Upload custom guest .gro+.itp pair with validation feedback
expected: In the Hydrate tab, use the custom guest upload panel to select a .gro and .itp file pair. If invalid, a specific validation error message should be displayed.
result: pass
verified: Workflow F (user GUI verification, post-fix) — long residue name (etoh_long_name.itp, "ETHANOL" 6 chars) now correctly blocked with validation error. Comb-rule=1 (etoh_comb_rule_1.itp) correctly rejected. Fix: commit 0baf0043.

### 3. Cage-type guest assignment controls for mixed occupancy
expected: In the Hydrate tab, select a multi-cage lattice. Per-cage-type rows should appear with QComboBox + QDoubleSpinBox for each cage type. Changing lattice should rebuild rows.
result: pass
verified: Workflow F (user GUI verification) — sI shows 2 rows with QComboBox + QDoubleSpinBox, sH shows 3, c0te shows 1, sTprime shows 0. Rows rebuild on lattice change.

### 4. Depol mode dropdown with strict as default
expected: In the Hydrate tab, a depol mode dropdown should be present with "strict" and "optimal". Default should be "strict".
result: pass
verified: Workflow F (user GUI verification) — depol dropdown present with strict/optimal, default strict

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
