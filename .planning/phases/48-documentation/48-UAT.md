---
status: complete
phase: 48-documentation
source: [48-01-SUMMARY.md, 48-02-SUMMARY.md, 48-03-SUMMARY.md, 48-04-SUMMARY.md, 48-05-SUMMARY.md, 48-06-SUMMARY.md, 48-07-SUMMARY.md, 48-08-SUMMARY.md, 48-09-SUMMARY.md, 48-10-SUMMARY.md, 48-11-SUMMARY.md, 48-12-SUMMARY.md, 48-13-SUMMARY.md, 48-14-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T19:00:00Z
---

## Current Test

[all script-runnable tests complete — 4 pass, 1 skipped (GUI) via Workflow D]

## Tests

### 1. README documents custom guest in hydrate workflow
expected: README.md describes the full workflow: upload → validate → generate → export.
result: pass
verified: Workflow D — README has custom guest workflow section with Upload/Generate/Export steps, .gro+.itp mention

### 2. GUI guide covers new lattice types, custom guest upload, mixed occupancy, depol selector
expected: docs/gui-guide.md covers all 10 lattice types, custom guest upload, mixed occupancy controls, depol mode. Version says v4.7.
result: pass
verified: Workflow D — GUI guide covers 10/10 lattice types, custom guest upload, mixed occupancy, depol mode, v4.7 reference

### 3. CLI reference documents new flags and marks deprecated ones
expected: docs/cli-reference.md documents --lattice-type (10 choices), --cage-guest, --depol. Deprecated flags marked. Version says v4.7.
result: pass
verified: Workflow D — CLI ref has --lattice-type, --cage-guest, --depol, DEPRECATED banners for --guest and --cage-occupancy, v4.7 reference

### 4. Custom guest ITP requirements documented
expected: docs/gro-itp-guide.md documents comb-rule=2 mandatory, residue name ≤3 chars, _H suffix convention.
result: pass
verified: Workflow D — GRO/ITP guide has comb-rule=2, residue ≤3 chars, _H suffix convention

### 5. In-app help updated for v4.7 and restructured with TOC navigation
expected: Open the QuickIce GUI help dialog. Should be QStackedWidget + QListWidget TOC with 4 new v4.7 content pages. Tooltips on Hydrate panel. Version 4.7.0.
result: pass
verified: Workflow H (user GUI verification) — QStackedWidget + QListWidget TOC confirmed, 4 new v4.7 content pages present, TOC navigation works, tooltips on Hydrate per-cage controls. Version string displays in code/CLI (4.7.0, verified Workflow D) — not shown in GUI but accepted as OK.

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
