---
status: testing
phase: 38-internal-pipeline-refactor
source: [38-01-SUMMARY.md, 38-02-SUMMARY.md, 38-03-SUMMARY.md, 38-04-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T19:00:00Z
---

## Current Test

[all script-runnable tests complete — 4/4 pass via Workflows A+G]

## Tests

### 1. Molecule identification via metadata (not pattern matching)
expected: Generate a hydrate structure with THF as guest. The generated .top file should correctly identify THF as the guest molecule (not misidentify THF oxygen atoms as water).
result: pass
verified: Workflow A — test_build_molecule_index.py passed (metadata-driven identification, THF not misidentified as water); Workflow G — test_gromacs_export_hydrate.py passed (metadata threads to export)

### 2. HydrateConfig carries guest metadata through pipeline
expected: Generate a hydrate structure with a built-in guest. The HydrateConfig should carry guest metadata (name, atom labels, atom count, ITP path) through the generation→export pipeline.
result: pass
verified: Workflow A — test_hydrate_config_metadata.py passed

### 3. GRO writer rejects residue names >5 chars with clear error
expected: Attempt to export a GROMACS .gro file with a residue name longer than 5 characters. The GRO writer should reject the name with a clear ValueError.
result: pass
verified: Workflow A — test_gro_resname_validation.py passed (ValueError on overlong names)

### 4. ITP transformation applies _H suffix, comments atomtypes, rewrites residue names
expected: Export a hydrate structure with a custom guest. The ITP transformation pipeline should apply the _H suffix, comment out [atomtypes], and rewrite residue names.
result: pass
verified: Workflow A — test_custom_guest_bridge.py (transform/itp tests) passed

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
