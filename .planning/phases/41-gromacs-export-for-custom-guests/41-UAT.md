---
status: testing
phase: 41-gromacs-export-for-custom-guests
source: [41-01-SUMMARY.md, 41-02-SUMMARY.md, 41-03-SUMMARY.md, 41-04-SUMMARY.md, 41-05-SUMMARY.md, 41-06-SUMMARY.md, 41-07-SUMMARY.md, 41-08-SUMMARY.md, 41-09-SUMMARY.md, 41-10-SUMMARY.md, 41-11-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T12:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Custom guest appears in .top with correct _H suffix moleculetype name
expected: |
  Generate a hydrate structure with a custom guest (e.g. ethanol), then export to GROMACS
  via either the GUI (export_hydrate) or CLI (_run_export_step). Open the exported .top file
  and verify the custom guest appears with the correct _H suffix moleculetype name
  (e.g. "MOL_H" if residue name is "MOL"). The [molecules] section should list this
  moleculetype with the correct molecule count.
awaiting: user response

## Tests

### 1. Custom guest appears in .top with correct _H suffix moleculetype name
expected: Generate a hydrate structure with a custom guest (e.g. ethanol), then export to GROMACS via either the GUI (export_hydrate) or CLI (_run_export_step). Open the exported .top file and verify the custom guest appears with the correct _H suffix moleculetype name (e.g. "MOL_H" if residue name is "MOL"). The [molecules] section should list this moleculetype with the correct molecule count.
result: [pending]

### 2. Custom guest atomtypes commented out in .itp and merged into main .top with dedup
expected: Export a custom guest hydrate to GROMACS. The bundled custom guest .itp file should have its [atomtypes] section commented out. The main .top file should contain the custom guest atomtypes merged into the [atomtypes] section with deduplication (shared atomtypes like hc, c3, h1 written only once, not duplicated between water/GAFF2 blocks and custom guest blocks).
result: [pending]

### 3. GRO export writes correct <=5-char residue name for custom guest
expected: Export a custom guest hydrate to GROMACS. Open the exported .gro file and verify the custom guest atoms have a residue name that is <=5 characters (including the _H suffix). For example, "MOL_H" (5 chars) is valid; "ETHANOL_H" (8 chars) would be invalid and should have been rejected. The residue name should be consistent between the .gro and .top files.
result: [pending]

### 4. GROMACS grompp validates successfully on exported custom guest hydrate
expected: Export a custom guest hydrate to GROMACS (both GUI and CLI paths). Run `gmx grompp` on the exported files (.gro + .top + .itp + .mdp). The grompp command should exit with return code 0 (no fatal errors). This confirms the exported files are valid GROMACS input for both the GUI export path (write_multi_molecule_*) and the CLI export path (write_interface_*).
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0

## Gaps

[none yet]
