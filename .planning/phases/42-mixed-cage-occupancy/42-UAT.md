---
status: testing
phase: 42-mixed-cage-occupancy
source: [42-00-SUMMARY.md, 42-01-SUMMARY.md, 42-02-SUMMARY.md, 42-03-SUMMARY.md, 42-04-SUMMARY.md, 42-05-SUMMARY.md, 42-06-SUMMARY.md, 42-07-SUMMARY.md, 42-08-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T12:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Assign different guest types to different cage types
expected: |
  In the GUI Hydrate tab, select a lattice with multiple cage types (e.g. sI with small+large
  cages, or sH with small+medium+large). For each cage type row, select a different guest type
  (e.g. CH4 in small cages, THF in large cages). The per-cage-type guest assignment controls
  (QComboBox per cage row) should allow independent selection of guest types.
awaiting: user response

## Tests

### 1. Assign different guest types to different cage types
expected: In the GUI Hydrate tab, select a lattice with multiple cage types (e.g. sI with small+large cages, or sH with small+medium+large). For each cage type row, select a different guest type (e.g. CH4 in small cages, THF in large cages). The per-cage-type guest assignment controls (QComboBox per cage row) should allow independent selection of guest types.
result: [pending]

### 2. Set per-cage-type occupancy percentage
expected: In the GUI Hydrate tab, for each cage type row, set an independent occupancy percentage using the QDoubleSpinBox (e.g. 60% CH4 in small cages + 100% THF in large cages). Generate the structure and verify the occupancy is respected (guest counts match the specified percentages for each cage type).
result: [pending]

### 3. Mixed occupancy hydrate exports correctly with multiple guest .itp includes
expected: Generate a mixed-occupancy hydrate (e.g. CH4 in small + THF in large) and export to GROMACS. The exported .top file should contain multiple guest .itp #include statements (one per guest type, e.g. ch4_hydrate.itp + thf_hydrate.itp). The [molecules] section should list both guest moleculetypes with correct counts. Run `gmx grompp` to confirm the export is valid.
result: [pending]

### 4. Mixed occupancy hydrate renders correctly in VTK with per-type visual styles
expected: Generate a mixed-occupancy hydrate (e.g. CH4 + THF) and view it in the 3D hydrate viewer. Each guest type should render with a distinct visual style (per-type bond colors from the palette: gray/cyan/yellow/red/purple). The two guest types should be visually distinguishable from each other and from water. Single-guest hydrates should keep the legacy gray style (unchanged from pre-v4.7).
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0

## Gaps

[none yet]
