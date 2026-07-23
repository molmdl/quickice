---
status: testing
phase: 48-documentation
source: [48-01-SUMMARY.md, 48-02-SUMMARY.md, 48-03-SUMMARY.md, 48-04-SUMMARY.md, 48-05-SUMMARY.md, 48-06-SUMMARY.md, 48-07-SUMMARY.md, 48-08-SUMMARY.md, 48-09-SUMMARY.md, 48-10-SUMMARY.md, 48-11-SUMMARY.md, 48-12-SUMMARY.md, 48-13-SUMMARY.md, 48-14-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T12:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: README documents custom guest in hydrate workflow
expected: |
  Open README.md and find the custom guest in hydrate workflow documentation. It should
  describe the full workflow: upload (.gro + .itp pair) → validate (comb-rule, residue name
  checks) → generate (select lattice, assign to cages) → export (GROMACS .gro/.top/.itp).
  The documentation should be specific enough for a new user to follow without guessing.
awaiting: user response

## Tests

### 1. README documents custom guest in hydrate workflow
expected: Open README.md and find the custom guest in hydrate workflow documentation. It should describe the full workflow: upload (.gro + .itp pair) → validate (comb-rule, residue name checks) → generate (select lattice, assign to cages) → export (GROMACS .gro/.top/.itp). The documentation should be specific enough for a new user to follow without guessing.
result: [pending]

### 2. GUI guide covers new lattice types, custom guest upload, mixed occupancy, depol selector
expected: Open the GUI guide documentation (docs/gui-guide.md or similar). Verify it covers: (a) a lattice types table with all 10 types (sI, sII, sH, C0, C1, C2, Ih, sT', Ice XVI, Ice XVII), (b) custom guest upload subsection (how to upload .gro+.itp, validation feedback), (c) mixed cage occupancy controls (per-cage-type guest/occupancy), (d) depol mode selector (strict/optimal, strict as default). Version references should say v4.7 (not stale v4.5).
result: [pending]

### 3. CLI reference documents new flags and marks deprecated ones
expected: Open the CLI reference (docs/cli-reference.md). Verify it documents: --lattice-type extended to 10 choices, --cage-guest (repeatable flag for mixed occupancy), --depol (strict/optimal). The --guest, --cage-occupancy-small, --cage-occupancy-large flags should be marked as DEPRECATED with a note pointing to their replacements. Custom guest in hydrate should be noted as GUI-only for v4.7 (no CLI flag). Version references should say v4.7.
result: [pending]

### 4. Custom guest ITP requirements documented
expected: Open the GRO/ITP guide (docs/gro-itp-guide.md or similar). Find the custom guest ITP requirements section. It should document: comb-rule=2 is mandatory (Lorentz-Berthelot / AMBER-GAFF2 convention), residue name must be <=3 chars (for the _H suffix making 5 max in GRO format), and the _H suffix convention should be explained (hydrate guests get _H appended to moleculetype name).
result: [pending]

### 5. In-app help updated for v4.7 and restructured with TOC navigation
expected: Open the QuickIce GUI and launch the help dialog. It should be restructured with a QStackedWidget + QListWidget table of contents (not a single scrolling textbox — content has outgrown that). Verify 4 new v4.7 content pages exist covering: extended lattice types, custom guest upload, mixed cage occupancy, and depol mode. Tooltips on the Hydrate panel per-cage controls should provide guidance. Version string should show 4.7.0 (not 4.5.0).
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0

## Gaps

[none yet]
