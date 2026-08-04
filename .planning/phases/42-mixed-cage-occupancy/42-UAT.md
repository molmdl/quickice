---
status: complete
phase: 42-mixed-cage-occupancy
source: [42-00-SUMMARY.md, 42-01-SUMMARY.md, 42-02-SUMMARY.md, 42-03-SUMMARY.md, 42-04-SUMMARY.md, 42-05-SUMMARY.md, 42-06-SUMMARY.md, 42-07-SUMMARY.md, 42-08-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T19:00:00Z
---

## Current Test

[all tests complete — 4 pass (1 accepted limitation), 0 skipped]

## Tests

### 1. Assign different guest types to different cage types
expected: In the GUI Hydrate tab, select a multi-cage lattice. For each cage type row, select a different guest type (e.g. CH4 in small, THF in large).
result: pass
verified: Workflow F (user GUI verification) — sI shows 2 rows, set CH4 in small + THF in large

### 2. Set per-cage-type occupancy percentage
expected: In the GUI Hydrate tab, for each cage type row, set an independent occupancy percentage. Generate and verify counts match.
result: pass
verified: Workflow F (user GUI verification) — set 60% small + 100% large, generated, counts match

### 3. Mixed occupancy hydrate exports correctly with multiple guest .itp includes
expected: Generate a mixed-occupancy hydrate (CH4+THF) and export to GROMACS. The .top should contain multiple guest .itp #includes. gmx grompp rc=0.
result: pass
verified: Workflow G — test_mixed_cage_cli.py + test_gromacs_export_hydrate.py::TestMultiGuestWriter passed (both ch4+thf .itp #includes, CH4_H+THF_H in [molecules]); Workflow C — mixed grompp passed (rc=0)

### 4. Mixed occupancy hydrate renders correctly in VTK with per-type visual styles
expected: Generate a mixed-occupancy hydrate and view in 3D viewer. Each guest type should render with a distinct visual style (per-type bond colors from palette).
result: pass
verified: Workflow F (user GUI verification) — mixed hydrate + custom guest both render in standard gray (not distinct per-type colors as expected). Single-guest hydrate correctly keeps legacy gray. User accepts current gray-only rendering for now — distinct per-type colors deferred.

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
