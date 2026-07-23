---
status: testing
phase: 38-internal-pipeline-refactor
source: [38-01-SUMMARY.md, 38-02-SUMMARY.md, 38-03-SUMMARY.md, 38-04-SUMMARY.md]
started: 2026-07-23T12:00:00Z
updated: 2026-07-23T12:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Molecule identification via metadata (not pattern matching)
expected: |
  Generate a hydrate structure with THF as guest (e.g. sI lattice with THF in large cages).
  The generated .top file should correctly identify THF as the guest molecule (not misidentify
  THF oxygen atoms as water). The molecule index should be built from HydrateConfig guest
  metadata (name, atom labels, atom count) rather than pattern matching on atom/residue names.
awaiting: user response

## Tests

### 1. Molecule identification via metadata (not pattern matching)
expected: Generate a hydrate structure with THF as guest (e.g. sI lattice with THF in large cages). The generated .top file should correctly identify THF as the guest molecule (not misidentify THF oxygen atoms as water). The molecule index should be built from HydrateConfig guest metadata (name, atom labels, atom count) rather than pattern matching on atom/residue names.
result: [pending]

### 2. HydrateConfig carries guest metadata through pipeline
expected: Generate a hydrate structure with a built-in guest (CH4 or THF). The HydrateConfig should carry guest metadata (name, atom labels, atom count, ITP path) through the generation to export pipeline. Verify the exported .top and .gro files contain the correct guest moleculetype name and atom count matching the guest metadata.
result: [pending]

### 3. GRO writer rejects residue names >5 chars with clear error
expected: Attempt to export a GROMACS .gro file with a residue name longer than 5 characters (e.g. via a custom guest with a long name). The GRO writer should reject the name with a clear ValueError identifying which writer/branch produced the invalid name, instead of silently truncating or corrupting the fixed-width format.
result: [pending]

### 4. ITP transformation applies _H suffix, comments atomtypes, rewrites residue names
expected: Export a hydrate structure with a custom guest. The ITP transformation pipeline (transform_guest_itp) should: (a) apply the _H suffix to the moleculetype name, (b) comment out the [atomtypes] section in the bundled .itp, and (c) rewrite residue names in the [atoms] section. Verify the exported .itp file shows these transformations.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0

## Gaps

[none yet]
