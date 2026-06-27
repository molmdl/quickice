---
status: complete
phase: 36-cli-feature-parity
source: 36-01-SUMMARY.md, 36-02-SUMMARY.md, 36-03-SUMMARY.md, 36-04-SUMMARY.md, 36-05-SUMMARY.md, 36-06-SUMMARY.md, 36-07-SUMMARY.md, 36-08-SUMMARY.md, 36-09-SUMMARY.md, 36-10-SUMMARY.md, 36-11-SUMMARY.md
started: 2026-06-27T12:00:00Z
updated: 2026-06-27T13:30:00Z
---

## Current Test

[testing complete — 15/15 passed after debug fixes]

## Tests

### 1. CLI Solute Insertion (CH4 via --solute-type)
expected: CH4_L residues after SOL in GRO, CH4_L in TOP [molecules], ch4_liquid.itp bundled
result: pass
detail: GRO has CH4_L residues, TOP has SOL:5627 + CH4_L:21, ch4_liquid.itp + tip4p-ice.itp bundled

### 2. CLI Solute Insertion (THF via --solute-type)
expected: THF_L residues after SOL in GRO, THF_L in TOP [molecules], thf_liquid.itp bundled
result: pass
detail: GRO has THF_L residues, TOP has SOL:5610 + THF_L:13, thf_liquid.itp + tip4p-ice.itp bundled

### 3. CLI Custom Molecule Insertion (Random Placement)
expected: MOL residues after SOL in GRO, etoh in TOP, etoh.itp bundled
result: pass
detail: GRO has MOL residues, TOP has SOL:5772 + etoh:3, etoh.itp + tip4p-ice.itp bundled

### 4. CLI Custom Molecule Insertion (Custom Placement via CSV)
expected: MOL residues placed at CSV-specified positions
result: pass
detail: GRO has MOL residues (3 molecules from CSV)

### 5. CLI Ion Source Selection (Interface)
expected: NA+CL residues in GRO, ion.itp bundled
result: pass
detail: GRO has SOL+NA+CL, ion.itp + tip4p-ice.itp bundled

### 6. CLI Ion Source Selection (Custom)
expected: SOL→MOL→NA→CL ordering in GRO
result: pass
detail: GRO has SOL+MOL+NA+CL residues

### 7. CLI Ion Source Selection (Solute)
expected: CH4_L+NA+CL in GRO
result: pass
detail: GRO has SOL+CH4_L+NA+CL residues

### 8. CLI Solute Source Selection (Custom Molecule)
expected: MOL+CH4_L in GRO, both ITPs bundled
result: pass
detail: GRO has MOL+CH4_L+SOL, etoh.itp + ch4_liquid.itp + tip4p-ice.itp

### 9. CLI Hydrate Generation (sI CH4)
expected: CH4_H residues in GRO, ch4_hydrate.itp bundled
result: pass
detail: GRO has CH4_H+SOL, ch4_hydrate.itp + tip4p-ice.itp

### 10. CLI Hydrate→Interface→Solute Chain
expected: CH4_H + CH4_L coexistence in TOP, both ITPs
result: pass
detail: TOP has SOL:2188 + CH4_H:144 + CH4_L:8, ch4_hydrate.itp + ch4_liquid.itp + tip4p-ice.itp

### 11. CLI Full Chain (Interface→Custom→Solute→Ion)
expected: SOL+MOL+CH4_L+NA+CL in GRO, 4+ ITPs
result: pass
detail: GRO has {SOL, MOL, CH4_L, NA, CL}, 4 ITPs (tip4p-ice.itp, etoh.itp, ch4_liquid.itp, ion.itp), atom count match. Fixed by auto-chaining in pipeline.py.

### 12. CLI --no-overwrite Flag
expected: First run succeeds, second run with --no-overwrite skips gracefully (exit 0)
result: pass
detail: 1st run rc=0, 2nd run with --no-overwrite rc=0 with "[PROGRESS] Output directory not empty; --no-overwrite set". Fixed by changing return 1→0 in pipeline.py.

### 13. CLI Cross-Flag Validation Errors
expected: Invalid flag combinations produce exit code 2
result: pass
detail: All 4 tested validation errors correctly return exit code 2

### 14. CLI Progress Reporting
expected: [PROGRESS] on stderr, clean stdout
result: pass
detail: [PROGRESS] messages appear on stderr, stdout is empty

### 15. CLI Interface Modes (Slab, Pocket, Piece)
expected: All three modes produce valid GROMACS output
result: pass
detail: slab=23220 atoms, pocket=13496 atoms, piece=5232 atoms

## Summary

total: 15
passed: 15
issues: 0
pending: 0
skipped: 0

## Gaps

[none — all resolved]
