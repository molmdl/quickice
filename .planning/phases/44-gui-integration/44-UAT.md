---
status: testing
phase: 44-gui-integration
source: [44-02-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T19:00:00Z
---

## Current Test

number: 1
name: Hydrate tab lattice dropdown includes all new lattice types
expected: |
  Open the QuickIce GUI, go to the Hydrate tab. The lattice type dropdown should include all
  10 lattice types. Selecting any of the 7 new types should not crash.
awaiting: user response (interactive — Workflow F)

## Tests

### 1. Hydrate tab lattice dropdown includes all new lattice types
expected: Open the QuickIce GUI, go to the Hydrate tab. The lattice type dropdown should include all 10 lattice types. Selecting any new type should not crash and should update the cage info display.
result: [pending]
note: Interactive — Workflow F (GUI dropdown). CLI --lattice-type choices verified in Workflow B (all 10 types).

### 2. Upload custom guest .gro+.itp pair with validation feedback
expected: In the Hydrate tab, use the custom guest upload panel to select a .gro and .itp file pair. If invalid, a specific validation error message should be displayed.
result: [pending]
note: Interactive — Workflow F (GUI upload + validation feedback). Validation logic verified in Workflow A (name/comb-rule checks).

### 3. Cage-type guest assignment controls for mixed occupancy
expected: In the Hydrate tab, select a multi-cage lattice. Per-cage-type rows should appear with QComboBox + QDoubleSpinBox for each cage type. Changing lattice should rebuild rows.
result: [pending]
note: Interactive — Workflow F (GUI per-cage rows). CLI --cage-guest flag verified in Workflow B.

### 4. Depol mode dropdown with strict as default
expected: In the Hydrate tab, a depol mode dropdown should be present with "strict" and "optimal". Default should be "strict".
result: [pending]
note: Interactive — Workflow F (GUI dropdown). CLI --depol verified in Workflow B (strict default).

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0

## Gaps

[none]
