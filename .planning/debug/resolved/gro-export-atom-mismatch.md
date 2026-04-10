---
status: resolved
trigger: "gro-export-atom-mismatch - Ctrl-G (GRO+TOP+ITP export for tab 1 - ice only) fails with 'atom mismatch' error after previous bugfix"
created: 2026-04-10T00:00:00Z
updated: 2026-04-10T00:06:00Z
---

## Current Focus

hypothesis: ROOT CAUSE CONFIRMED - write_gro_file() incorrectly uses base_idx = mol_idx * 4 (line 59) and expects 4 atoms per molecule, but ice Candidates have only 3 atoms (O, H, H). The MW virtual site must be COMPUTED during export, not read from positions.
test: Implement fix by changing base_idx to mol_idx * 3 and computing MW position, mirroring write_interface_gro_file logic
expecting: After fix, write_gro_file will correctly read 3 atoms per molecule and compute MW position for export
next_action: Implement fix in gromacs_writer.py

## Symptoms

expected: Ctrl-G should export GRO+TOP+ITP files successfully for ice structure in tab 1
actual: Export fails with error message saying "atom mismatch"
errors: "atom mismatch" error message displayed
reproduction: Press Ctrl-G on any ice structure in tab 1 - always reproducible
started: Regression - worked before a previous bugfix was applied

## Eliminated

<!-- APPEND only - prevents re-investigating -->

## Evidence

- timestamp: 2026-04-10T00:01:00Z
  checked: grep for "atom mismatch" error in codebase
  found: NO MATCHES in code - only found in debug file
  implication: Error message might be different than "atom mismatch", need to search for related errors

- timestamp: 2026-04-10T00:01:00Z
  checked: Ctrl-G export code location
  found: main_window.py:651 _on_export_gromacs calls _gromacs_exporter.export_gromacs(ranked, T, P)
  implication: Need to examine GROMACSExporter class in export.py

- timestamp: 2026-04-10T00:01:00Z
  checked: Previous critical issues
  found: crit-02-index-overflow, crit-03-inconsistent-atom-names, med-05-atom-names
  implication: Previous fixes may have affected atom counting logic

- timestamp: 2026-04-10T00:02:00Z
  checked: gromacs_writer.py write_gro_file() (lines 18-96)
  found: Bounds check at line 38-42: if len(candidate.positions) < nmol * 4, raise ValueError
  implication: Code assumes Candidate has 4 atoms per molecule (TIP4P-ICE with MW), but ice structures may have only 3

- timestamp: 2026-04-10T00:02:00Z
  checked: write_interface_gro_file() (lines 204-287)
  found: Ice molecules use 3 atoms per molecule (line 235: base_idx = mol_idx * 3), water uses 4 atoms
  implication: Ice structures store 3 atoms per molecule (O, H, H), MW is computed during export

- timestamp: 2026-04-10T00:03:00Z
  checked: Candidate type definition (types.py:10-36)
  found: positions is numpy array, atom_names is list like ["O", "H", "H", ...], nmolecules is int
  implication: No documentation about atoms per molecule, need to check how ice generators create positions

- timestamp: 2026-04-10T00:03:00Z
  checked: write_interface_gro_file ice atom indexing (lines 234-266)
  found: base_idx = mol_idx * 3 for ice molecules, MW position computed via compute_mw_position()
  implication: Ice Candidates store 3 atoms per molecule (O, H, H), MW is added during export

- timestamp: 2026-04-10T00:04:00Z
  checked: Generated ice Candidate actual structure
  found: nmolecules=16, positions.shape=(48,3), atom_names=['O','H','H',...], atoms_per_molecule=3.0
  implication: CONFIRMED - ice Candidates have 3 atoms per molecule (O, H, H), not 4

- timestamp: 2026-04-10T00:04:00Z
  checked: write_gro_file indexing logic (line 59)
  found: base_idx = mol_idx * 4, then accesses positions[base_idx], positions[base_idx+1], positions[base_idx+2], positions[base_idx+3]
  implication: BUG - code tries to read 4 atoms per molecule from positions, but only 3 exist; position[base_idx+3] is actually O of next molecule

## Resolution

root_cause: write_gro_file() in gromacs_writer.py incorrectly assumed ice Candidate objects store 4 atoms per molecule (O, H1, H2, MW) for TIP4P-ICE format, but ice Candidates actually store only 3 atoms per molecule (O, H, H). The MW virtual site must be computed during export, not read from positions. The code used base_idx = mol_idx * 4 (line 59) which caused it to read positions[3] as MW of molecule 0, when actually positions[3] is the O atom of molecule 1. This led to wrong atom assignments and index overflow errors.

fix: Modified write_gro_file() to:
1. Use base_idx = mol_idx * 3 (ice has 3 atoms per molecule)
2. Read O, H1, H2 positions from Candidate
3. Compute MW virtual site position using compute_mw_position()
4. Write all 4 atoms (OW, HW1, HW2, MW) to GRO file for TIP4P-ICE format

This mirrors the logic in write_interface_gro_file() which correctly handles ice molecules.

verification: 
1. Created ice Candidate (16 molecules, 48 positions) - confirmed 3 atoms per molecule
2. Successfully wrote GRO file with 64 atoms (16 × 4 for TIP4P-ICE)
3. Verified MW positions computed correctly (within GRO precision of 0.001 nm)
4. Verified O, H positions match original candidate (rounded to GRO precision)
5. Verified TOP file contains correct molecule count
6. All 247 existing tests pass
7. Error no longer occurs

files_changed: [quickice/output/gromacs_writer.py]