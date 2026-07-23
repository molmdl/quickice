---
status: testing
phase: 41-gromacs-export-for-custom-guests
source: [41-01-SUMMARY.md, 41-02-SUMMARY.md, 41-03-SUMMARY.md, 41-04-SUMMARY.md, 41-05-SUMMARY.md, 41-06-SUMMARY.md, 41-07-SUMMARY.md, 41-08-SUMMARY.md, 41-09-SUMMARY.md, 41-10-SUMMARY.md, 41-11-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T19:00:00Z
---

## Current Test

[all script-runnable tests complete — 4/4 pass via Workflows C+G]

## Tests

### 1. Custom guest appears in .top with correct _H suffix moleculetype name
expected: Generate a hydrate structure with a custom guest, then export to GROMACS. The .top file should contain the custom guest with the _H suffix moleculetype name.
result: pass
verified: Workflow G — test_e2e_custom_guest_cli_grompp.py + test_multi_molecule_top_custom_guest.py + test_interface_top_custom_guest.py passed (MOL_H in [molecules])

### 2. Custom guest atomtypes commented out in .itp and merged into main .top with dedup
expected: Export a custom guest hydrate. The bundled .itp should have [atomtypes] commented out. The main .top should contain merged custom atomtypes with deduplication.
result: pass
verified: Workflow G — test_merge_custom_atomtypes.py + test_custom_guest_bridge.py (transform/atomtype tests) passed

### 3. GRO export writes correct <=5-char residue name for custom guest
expected: Export a custom guest hydrate. The .gro file should have custom guest atoms with a residue name ≤5 chars (including _H suffix).
result: pass
verified: Workflow G — test_e2e_custom_guest_cli_grompp.py + test_multi_molecule_gro_custom_guest.py + test_interface_gro_custom_guest.py passed (MOL_H = 5 chars)

### 4. GROMACS grompp validates successfully on exported custom guest hydrate
expected: Export a custom guest hydrate (both GUI and CLI paths). Run gmx grompp — return code 0.
result: pass
verified: Workflow C — test_e2e_custom_guest_gui_grompp.py + test_e2e_custom_guest_cli_grompp.py passed (gmx grompp rc=0, gmx available)

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
