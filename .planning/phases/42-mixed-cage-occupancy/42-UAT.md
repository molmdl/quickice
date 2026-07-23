---
status: testing
phase: 42-mixed-cage-occupancy
source: [42-00-SUMMARY.md, 42-01-SUMMARY.md, 42-02-SUMMARY.md, 42-03-SUMMARY.md, 42-04-SUMMARY.md, 42-05-SUMMARY.md, 42-06-SUMMARY.md, 42-07-SUMMARY.md, 42-08-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T19:00:00Z
---

## Current Test

number: 1
name: Assign different guest types to different cage types
expected: |
  In the GUI Hydrate tab, select a lattice with multiple cage types (e.g. sI with small+large
  cages). For each cage type row, select a different guest type (e.g. CH4 in small, THF in large).
awaiting: user response (interactive — Workflow F)

## Tests

### 1. Assign different guest types to different cage types
expected: In the GUI Hydrate tab, select a multi-cage lattice. For each cage type row, select a different guest type (e.g. CH4 in small, THF in large).
result: [pending]
note: Interactive — Workflow F (GUI per-cage controls). CLI --cage-guest flag verified in Workflow B.

### 2. Set per-cage-type occupancy percentage
expected: In the GUI Hydrate tab, for each cage type row, set an independent occupancy percentage. Generate and verify counts match.
result: [pending]
note: Interactive — Workflow F (GUI per-cage spinners).

### 3. Mixed occupancy hydrate exports correctly with multiple guest .itp includes
expected: Generate a mixed-occupancy hydrate (CH4+THF) and export to GROMACS. The .top should contain multiple guest .itp #includes. gmx grompp rc=0.
result: pass
verified: Workflow G — test_mixed_cage_cli.py + test_gromacs_export_hydrate.py::TestMultiGuestWriter passed (both ch4+thf .itp #includes, CH4_H+THF_H in [molecules]); Workflow C — mixed grompp passed (rc=0)

### 4. Mixed occupancy hydrate renders correctly in VTK with per-type visual styles
expected: Generate a mixed-occupancy hydrate and view in 3D viewer. Each guest type should render with a distinct visual style (per-type bond colors from palette).
result: [pending]
note: Interactive — Workflow F (VTK rendering, visual check).

## Summary

total: 4
passed: 1
issues: 0
pending: 3
skipped: 0

## Gaps

[none]
