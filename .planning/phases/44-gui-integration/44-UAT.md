---
status: testing
phase: 44-gui-integration
source: [44-02-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T12:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Hydrate tab lattice dropdown includes all new lattice types
expected: |
  Open the QuickIce GUI, go to the Hydrate tab. The lattice type dropdown should include all
  10 lattice types: sI, sII, sH, C0 (c0te), C1 (c1te), C2 (c2te), Ih (ice1hte), sT' (sTprime),
  Ice XVI (16), and Ice XVII (17). Selecting any of the 7 new types should not crash and should
  update the cage info display and controls appropriately.
awaiting: user response

## Tests

### 1. Hydrate tab lattice dropdown includes all new lattice types
expected: Open the QuickIce GUI, go to the Hydrate tab. The lattice type dropdown should include all 10 lattice types: sI, sII, sH, C0 (c0te), C1 (c1te), C2 (c2te), Ih (ice1hte), sT' (sTprime), Ice XVI (16), and Ice XVII (17). Selecting any of the 7 new types should not crash and should update the cage info display and controls appropriately.
result: [pending]

### 2. Upload custom guest .gro+.itp pair with validation feedback
expected: In the Hydrate tab, use the custom guest upload panel to select a .gro and .itp file pair. If the files are valid, no error is shown and the guest is ready for generation. If the files are invalid (name too long, wrong comb-rule, unparseable), a specific validation error message should be displayed identifying the problem (e.g. "Residue name too long: must be <=3 chars for _H suffix" or "comb-rule=1 rejected: must be Lorentz-Berthelot (comb-rule=2)").
result: [pending]

### 3. Cage-type guest assignment controls for mixed occupancy
expected: In the Hydrate tab, select a multi-cage lattice (e.g. sI or sH). Per-cage-type rows should appear with a QComboBox (guest type selection) and QDoubleSpinBox (occupancy percentage) for each cage type. Changing the lattice type should rebuild the cage rows (sI=2 rows, sH=3 rows, filled ice c0te=1 row, water-only sTprime=0 rows).
result: [pending]

### 4. Depol mode dropdown with strict as default
expected: In the Hydrate tab, a depol mode dropdown (QComboBox) should be present with "strict" and "optimal" options. The default selection should be "strict". The depol mode should be passed through to HydrateWorker and ultimately to GenIce2's generate_ice() call.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0

## Gaps

[none yet]
