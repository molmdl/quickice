---
status: complete
phase: 36-cli-feature-parity
source: 36-01-SUMMARY.md, 36-02-SUMMARY.md, 36-03-SUMMARY.md, 36-04-SUMMARY.md, 36-05-SUMMARY.md, 36-06-SUMMARY.md, 36-07-SUMMARY.md, 36-08-SUMMARY.md, 36-09-SUMMARY.md, 36-10-SUMMARY.md, 36-11-SUMMARY.md
started: 2026-06-27T12:00:00Z
updated: 2026-06-27T12:30:00Z
---

## Current Test

[testing complete — 13/15 passed, help text verified]

## Tests

### 1. CLI Solute Insertion (CH4 via --solute-type)
expected: CH4_LIQ molecules after SOL in GRO, CH4_L in TOP [molecules], ch4_liquid.itp bundled
result: pass
detail: GRO has CH4_L residues, TOP has SOL:5627 + CH4_L:21, ch4_liquid.itp + tip4p-ice.itp bundled

### 2. CLI Solute Insertion (THF via --solute-type)
expected: THF_LIQ molecules after SOL in GRO, THF_L in TOP [molecules], thf_liquid.itp bundled
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
detail: TOP has SOL:2186 + CH4_H:144 + CH4_L:8, ch4_hydrate.itp + ch4_liquid.itp + tip4p-ice.itp

### 11. CLI Full Chain (Interface→Custom→Solute→Ion)
expected: SOL+MOL+CH4_L+NA+CL in GRO, 4+ ITPs
result: issue
reported: "Full chain with custom+solute+ion but without --ion-source solute drops custom molecules and solutes from output. When --ion-source solute is used, solutes appear but custom molecules (etoh) still missing from GRO/TOP. Root cause: --ion-source defaults to 'interface' which doesn't have custom/solute attributes. Also SoluteStructure→IonInserter propagation of custom molecules may be incomplete."
severity: major

### 12. CLI --no-overwrite Flag
expected: First run succeeds, second run with --no-overwrite skips gracefully
result: issue
reported: "Second run with --no-overwrite exits with rc=1 instead of rc=0. Pipeline treats existing files as runtime error (exit 1). Design question: should graceful skip return exit 0?"
severity: minor

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
passed: 13
issues: 2
pending: 0
skipped: 0

## Gaps

- truth: "Full chain (custom+solute+ion) includes all molecule types in GROMACS output"
  status: failed
  reason: "User reported: Full chain with custom+solute+ion without --ion-source solute drops custom/solute from output. Even with --ion-source solute, custom molecules (etoh) missing from GRO/TOP."
  severity: major
  test: 11
  root_cause: "1) Default --ion-source=interface doesn't see custom/solute results. 2) SoluteStructure→IonInserter custom molecule propagation may be incomplete (custom_molecule_positions may be None when solute source was 'interface', not 'custom')"
  artifacts:
    - path: "quickice/cli/pipeline.py"
      issue: "_run_ion_step defaults to interface source; when --ion-source solute, custom molecule attributes may not propagate correctly from solute result when solute source was interface"
  missing:
    - "When custom+solute+ion without explicit --ion-source, auto-detect best source (solute if present, custom if present, else interface)"
    - "OR: Document that --ion-source must be explicitly set for chained workflows"
    - "Verify SoluteStructure carries custom_molecule_positions when source is interface (not custom)"

- truth: "--no-overwrite exits gracefully with code 0 when files exist"
  status: failed
  reason: "User reported: exits with rc=1 instead of rc=0 when output files already exist and --no-overwrite is set"
  severity: minor
  test: 12
  root_cause: "Pipeline.execute() returns 1 on --no-overwrite skip (line 80), treating it as runtime error"
  artifacts:
    - path: "quickice/cli/pipeline.py"
      issue: "Line 80: return 1 on --no-overwrite skip; should arguably be return 0 (graceful skip)"
  missing:
    - "Change return 1 to return 0 on --no-overwrite skip (graceful exit, not error)"
    - "OR: Document that --no-overwrite returns exit 1 when files exist"
