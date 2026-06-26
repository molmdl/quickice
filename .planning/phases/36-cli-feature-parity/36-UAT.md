---
status: testing
phase: 36-cli-feature-parity
source: 36-01-SUMMARY.md, 36-02-SUMMARY.md, 36-03-SUMMARY.md, 36-04-SUMMARY.md, 36-05-SUMMARY.md, 36-06-SUMMARY.md, 36-07-SUMMARY.md, 36-08-SUMMARY.md, 36-09-SUMMARY.md, 36-10-SUMMARY.md, 36-11-SUMMARY.md
started: 2026-06-26T12:00:00Z
updated: 2026-06-26T12:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: CLI Solute Insertion (CH4)
expected: |
  Running `python -m quickice --cli -T 270 -P 0.1 --interface --interface-mode slab --solute-type CH4 --solute-concentration 0.5` produces GROMACS files (.gro, .top, .itp) in the output directory with CH4_LIQ molecules listed after SOL in the .gro file and CH4_LIQ appearing in the .top [molecules] section.
awaiting: user response

## Tests

### 1. CLI Solute Insertion (CH4 via --solute-type)
expected: Running `python -m quickice --cli -T 270 -P 0.1 --interface --interface-mode slab --solute-type CH4 --solute-concentration 0.5` produces GROMACS files with CH4_LIQ molecules after SOL in .gro, CH4_LIQ in .top [molecules], and ch4_liquid.itp bundled in output directory
result: pending

### 2. CLI Solute Insertion (THF via --solute-type)
expected: Running `python -m quickice --cli -T 270 -P 0.1 --interface --interface-mode slab --solute-type THF --solute-concentration 0.3` produces GROMACS files with THF_LIQ molecules (13 atoms each) after SOL in .gro, THF_LIQ in .top [molecules], and thf_liquid.itp bundled
result: pending

### 3. CLI Custom Molecule Insertion (Random Placement)
expected: Running `python -m quickice --cli -T 270 -P 0.1 --interface --interface-mode slab --custom-gro quickice/data/custom/etoh.gro --custom-itp quickice/data/custom/etoh.itp --custom-placement random --custom-count 3` inserts 3 ethanol molecules randomly into liquid water with overlap checking, producing GROMACS files with MOL residues after SOL in .gro and etoh.itp bundled
result: pending

### 4. CLI Custom Molecule Insertion (Custom Placement via CSV)
expected: Running `python -m quickice --cli -T 270 -P 0.1 --interface --interface-mode slab --custom-gro quickice/data/custom/etoh.gro --custom-itp quickice/data/custom/etoh.itp --custom-placement custom --custom-positions-file quickice/data/examples/custom_positions.csv` places 3 ethanol molecules at the exact positions/rotations specified in the CSV file, producing GROMACS files
result: pending

### 5. CLI Ion Source Selection (Interface)
expected: Running `python -m quickice --cli -T 270 -P 0.1 --interface --interface-mode slab --ion-concentration 0.15 --ion-source interface` inserts Na+/Cl- ions from the interface structure as source, producing .gro with NA and CL residues and ion.itp bundled
result: pending

### 6. CLI Ion Source Selection (Custom)
expected: Running `python -m quickice --cli -T 270 -P 0.1 --interface --interface-mode slab --custom-gro quickice/data/custom/etoh.gro --custom-itp quickice/data/custom/etoh.itp --custom-placement random --custom-count 2 --ion-concentration 0.15 --ion-source custom` uses the Custom Molecule result as source for ion insertion, producing .gro with SOL→MOL→NA→CL ordering
result: pending

### 7. CLI Ion Source Selection (Solute)
expected: Running `python -m quickice --cli -T 270 -P 0.1 --interface --interface-mode slab --solute-type CH4 --solute-concentration 0.5 --ion-concentration 0.15 --ion-source solute` uses the Solute result as source for ion insertion, producing .gro with SOL→CH4_LIQ→NA→CL ordering
result: pending

### 8. CLI Solute Source Selection (Custom Molecule)
expected: Running `python -m quickice --cli -T 270 -P 0.1 --interface --interface-mode slab --custom-gro quickice/data/custom/etoh.gro --custom-itp quickice/data/custom/etoh.itp --custom-placement random --custom-count 2 --solute-type CH4 --solute-concentration 0.5 --solute-source custom` uses the Custom Molecule result as source for solute insertion (Custom→Solute workflow)
result: pending

### 9. CLI Hydrate Generation (sI CH4)
expected: Running `python -m quickice --cli --hydrate --lattice-type sI --guest CH4 -T 270 -P 0.1` generates a structure-I CH4 hydrate and exports GROMACS files with ch4_hydrate.itp bundled and guest residues in .gro
result: pending

### 10. CLI Hydrate→Interface→Solute Chain
expected: Running `python -m quickice --cli --hydrate --lattice-type sI --guest CH4 -T 270 -P 0.1 --interface --interface-mode slab --solute-type CH4 --solute-concentration 0.3` produces a hydrate→interface→solute chain with both CH4_H (hydrate guest) and CH4_LIQ (liquid solute) in the same .top [molecules] section and both ITPs bundled
result: pending

### 11. CLI Full Chain (Interface→Custom→Solute→Ion)
expected: Running `python -m quickice --cli -T 270 -P 0.1 --interface --interface-mode slab --custom-gro quickice/data/custom/etoh.gro --custom-itp quickice/data/custom/etoh.itp --custom-placement random --custom-count 2 --solute-type CH4 --solute-concentration 0.3 --ion-concentration 0.15` produces GROMACS files with SOL→MOL→CH4_LIQ→NA→CL ordering, 4 ITP files bundled (tip4p-ice.itp, etoh.itp, ch4_liquid.itp, ion.itp), and correct atom counts in .gro
result: pending

### 12. CLI --no-overwrite Flag
expected: Running a pipeline command twice with `--no-overwrite` flag: first run succeeds (exit code 0), second run skips output because files already exist (reports "Output files exist" and exits without error)
result: pending

### 13. CLI Cross-Flag Validation Errors
expected: Running commands with invalid flag combinations produces exit code 2 with clear error messages: (a) `--custom-gro` without `--custom-itp` (requires each other), (b) `--solute-type` without `--solute-concentration`, (c) `--ion-source custom` without `--custom-gro`, (d) `--custom-placement custom` without `--custom-positions-file`
result: pending

### 14. CLI Progress Reporting
expected: During any pipeline execution, [PROGRESS] messages appear on stderr (not stdout) indicating each step's status, while stdout remains clean (only file output goes to output directory)
result: pending

### 15. CLI Interface Modes (Slab, Pocket, Piece)
expected: Running `python -m quickice --cli -T 270 -P 0.1 --interface --interface-mode slab` produces slab interface, `--interface-mode pocket --pocket-diameter 1.5` produces pocket interface, `--interface-mode piece --piece-thickness 2.0` produces piece interface — all with correct GROMACS output
result: pending

## Summary

total: 15
passed: 0
issues: 0
pending: 15
skipped: 0

## Gaps

[none yet]
