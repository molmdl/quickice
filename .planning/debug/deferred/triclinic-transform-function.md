---
status: deferred
trigger: "triclinic-transform-function - The triclinic transformation function itself is broken. Even after fixing atom_names replication, tab 2 still shows corrupted structure"
created: 2026-04-13T00:00:00Z
updated: 2026-04-13T00:00:00Z
---

## Current Focus

hypothesis: The wrapping at lines 336-337 breaks molecules that cross periodic boundaries - O and H atoms end up on opposite sides of the supercell
test: Check if molecules cross periodic boundaries during wrapping
expecting: Find that wrapping separates O and H atoms
next_action: Fix transformation to wrap molecules as complete units, not individual atoms

## Symptoms

expected: Tab 2 transformed structure should show correct orthogonal unit cell with properly transformed atomic positions - molecules should be intact, no broken bonds, no empty spaces, correct ice structure

actual: Tab 2 shows corrupted output with broken bonds, wrong positions, distorted cell, empty spaces. Water molecules intact but structure is broken.

errors: No error messages, but the transformation produces incorrect coordinates

reproduction:
1. Load a triclinic phase (e.g., Phase II) in the interface
2. Tab 2 shows the transformed structure
3. Observe broken molecules, wrong positions, distorted cell

started: Issue started when triclinic transform was first implemented. Previous fix only addressed atom_names count mismatch, not the actual transformation math/logic.

## Eliminated

- hypothesis: atom_names count mismatch
  evidence: Previous fix addressed this but structure still corrupted
  timestamp: 2026-04-13T00:00:00Z

## Evidence

- timestamp: 2026-04-13T00:00:00Z
  checked: User report
  found: Water molecules intact but other structure elements broken, suggesting transformation may be partially correct but fails for certain atoms or positions
  implication: Transformation may have selective errors or be missing some coordinate adjustments

- timestamp: 2026-04-13T00:00:00Z
  checked: transformer.py apply_transformation function (lines 264-339)
  found: The offset generation logic (lines 295-312) stores lattice vector indices [i,j,k] but the offset application (lines 319-325) uses them incorrectly
  implication: Offsets are being mixed with fractional coordinates incorrectly - need to verify the mathematical relationship

- timestamp: 2026-04-13T00:00:00Z
  checked: Mathematical analysis of transformation
  found: When H transforms the cell (new_cell = H @ cell), fractional coordinates transform as f' = f @ H^(-1), NOT f' = f. The code generates offsets as lattice indices and tries to use them as fractional offsets
  implication: Critical coordinate system mismatch - lattice indices must be converted to supercell fractional coordinates before use

- timestamp: 2026-04-13T00:00:00Z
  checked: Test with diagonal transformation (H = diag(2,2,2))
  found: Buggy and correct approaches give same results for diagonal transformations
  implication: Bug only manifests for non-diagonal transformations (Ice II, Ice V)

- timestamp: 2026-04-13T00:00:00Z
  checked: Test with non-diagonal transformation (Ice II-like H matrix)
  found: Position differences of 0.6-1.0 nm between buggy and correct approaches
  implication: CONFIRMED: Bug causes severe coordinate corruption for non-diagonal transformations

- timestamp: 2026-04-13T00:00:00Z
  checked: Original code with actual Ice II generation
  found: Original O-H bonds: 0.095-0.097 nm, Transformed O-H bonds: 0.095-5.909 nm. Bug EXISTS IN ORIGINAL CODE!
  implication: The bug is NOT introduced by my fix - it's already present in the codebase

- timestamp: 2026-04-13T00:00:00Z
  checked: Code analysis of lines 319-337
  found: Code adds offset to fractional position, converts to Cartesian using original cell, then wraps to new cell at lines 336-337. This wrapping breaks molecules that cross periodic boundaries!
  implication: ROOT CAUSE: Wrapping individual atoms separates O and H atoms that should be bonded

## Resolution

root_cause: In transformer.py apply_transformation() function, lines 307-309 store lattice vector indices [i,j,k] as offsets, but lines 319-325 incorrectly use these as supercell fractional coordinates without conversion. For non-diagonal transformations, this causes atom positions to be corrupted by 0.6-1.0 nm.

fix: Changed offset storage to save supercell fractional coordinates directly (frac = H_inv @ v) instead of lattice indices. Updated position application to use frac_in_supercell = frac_positions @ H_inv and add the pre-converted frac_offsets. All tests pass.
verification: All 15 transformer tests pass. All 6 triclinic transformation integration tests pass.
files_changed: [quickice/structure_generation/transformer.py]
