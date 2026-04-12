---
status: resolved
trigger: "tab1-restore-original-triclinic"
created: 2026-04-13T00:00:00Z
updated: 2026-04-13T00:00:02Z
---

## Current Focus

hypothesis: CONFIRMED - Transformation in generator.py modifies candidate in-place, affecting all downstream usage
test: Implement fix to store both original and transformed versions
expecting: Tab 1 shows original, Tab 2 uses transformed
next_action: Modify Candidate type to store original positions/cell, update generator to preserve original

## Symptoms

expected: Tab 1 viewer should show the original triclinic structure with correct unit cell and intact molecules (no transform applied)

actual: Tab 1 shows transformed structure with orthogonal unit cell, broken molecules, atoms half outside the white gridbox due to PBC wrapping issues

errors: No error messages, but visualization is corrupted

reproduction: Load a triclinic phase (e.g., Phase II) in the interface, observe tab 1 viewer

started: Issue started after adding triclinic transform code. Previously tab 1 worked correctly for triclinic phases.

user_solution: For tab 1, keep original triclinic (no transform) so the original viewer works. Only apply transform in tab 2.

## Eliminated

<!-- APPEND only - prevents re-investigating -->

## Evidence

<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-13T00:00:00Z
  checked: generator.py lines 128-170
  found: TriclinicTransformer.transform_if_needed() is called on the Candidate, and its result REPLACES the original positions/cell
  implication: The original triclinic structure is lost - all downstream code (Tab 1 viewers, Tab 2 interface) sees only the transformed orthogonal structure

- timestamp: 2026-04-13T00:00:00Z
  checked: main_window.py line 366
  found: Tab 1's dual_viewer.set_candidates() receives the already-transformed candidates
  implication: Tab 1 cannot display original triclinic because the data is already transformed

- timestamp: 2026-04-13T00:00:00Z
  checked: types.py Candidate dataclass
  found: Candidate only stores one set of positions/cell, no field for original triclinic data
  implication: Need to add fields to store original positions/cell alongside transformed versions

## Resolution

root_cause: The TriclinicTransformer.transform_if_needed() in generator.py (_generate_single method, lines 131-144) modifies the Candidate in-place, replacing the original triclinic positions/cell with transformed orthogonal versions. This means both Tab 1 (viewer) and Tab 2 (interface construction) receive the transformed structure. The user wants Tab 1 to show original triclinic while Tab 2 uses transformed.
fix: Added original_positions and original_cell fields to Candidate type. Generator stores original triclinic data before transformation. MolecularViewer.set_candidate() checks for original data and uses it for display, preserving transformed data for Tab 2 interface construction.
verification: Tests pass, Ice II/Ice V show original_positions with triclinic cells, orthogonal phases have None
files_changed: [quickice/structure_generation/types.py, quickice/structure_generation/generator.py, quickice/gui/molecular_viewer.py]
