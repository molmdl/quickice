---
status: testing
phase: 34-custom-molecule-upload-(tab-5)
source: [34-01-SUMMARY.md, 34-02-SUMMARY.md, 34-03-SUMMARY.md, 34-04-SUMMARY.md, 34-05-SUMMARY.md]
started: 2026-05-05T08:18:04Z
updated: 2026-05-05T08:18:04Z
---

## Current Test

number: 1
name: Upload valid GRO and ITP files
expected: |
  Click the "Upload GRO" button, select a valid .gro file. Status shows success.
  Click the "Upload ITP" button, select a valid .itp file with matching atom count and residue name.
  Status shows "Validation successful" message with green indicator.
awaiting: user response

## Tests

### 1. Upload valid GRO and ITP files
expected: Click the "Upload GRO" button, select a valid .gro file. Status shows success. Click the "Upload ITP" button, select a valid .itp file with matching atom count and residue name. Status shows "Validation successful" message with green indicator.
result: [pending]

### 2. Validation status for atom count mismatch
expected: Upload GRO and ITP files with different atom counts. Status shows error message: "Atom count mismatch: GRO has X atoms, ITP has Y atoms." Upload button remains enabled for retry.
result: [pending]

### 3. Residue name mismatch dialog
expected: Upload GRO file with residue name "MOL" and ITP file with residue name "CUSTOM". Dialog appears asking "ITP residue name 'CUSTOM' differs from GRO 'MOL'. Use ITP name?" with Yes/No buttons. Clicking Yes allows proceeding with ITP name.
result: [pending]

### 4. Random placement mode controls
expected: Select "Random" from placement mode dropdown. Molecule count input appears (default 10, range 1-1000). Custom position controls are hidden. Generate button is enabled after valid file upload.
result: [pending]

### 5. Custom placement mode controls
expected: Select "Custom" from placement mode dropdown. Position inputs (X, Y, Z) and rotation inputs (α, β, γ) appear. "Add Position" button adds another set of inputs. Random count input is hidden.
result: [pending]

### 6. Generate molecules in 3D viewer
expected: After uploading valid files and entering molecule count in Random mode, click Generate. Progress bar appears. Molecules appear in 3D viewer within the liquid water region. No overlap visible.
result: [pending]

### 7. Custom molecules rendered with distinct colors
expected: Generate multiple custom molecules. Each molecule type (CUSTOM_MOL_1, CUSTOM_MOL_2, etc.) appears with distinct color: purple for first type, cyan for second, yellow for third. Colors differ from CH4, THF, ions, water, ice.
result: [pending]

### 8. Ball-and-stick rendering quality
expected: Custom molecules show ball-and-stick style with atoms as spheres and bonds as cylinders. Carbon atoms are gray, oxygen atoms are red, hydrogen atoms are white (CPK colors). Bonds appear automatically between nearby atoms.
result: [pending]

### 9. GROMACS export with bundled ITP
expected: Click Ctrl+M or menu "Export → Custom Molecule GROMACS". File dialog appears. Select output directory. Generated files include: .gro file with custom molecules, .top file with #include statement, .itp file copied to output directory with correct moleculetype name.
result: [pending]

### 10. Tab order verification
expected: Six tabs appear in order: Ice (0), Hydrate (1), Interface (2), Solute (3), Custom (4), Ion (5). Ion tab has moved from position 3 to position 5. All tabs clickable and functional.
result: ✅ passed (2026-06-19, WF1 — 6 tabs verified: Ice(0) Hydrate(1) Interface(2) Custom(3) Solute(4) Ion(5))

### 11. Invalid file type rejection
expected: Attempt to upload a non-GRO file (e.g., .txt) via "Upload GRO" button. Error message shows "Invalid file type. Please select a .gro file." Attempt to upload non-ITP file via "Upload ITP" button. Similar error appears.
result: [pending]

### 12. Missing [ atomtypes ] section warning
expected: Upload ITP file without [ atomtypes ] section. Status shows warning: "Missing [ atomtypes ] section. Force field parameters will not be included." Upload succeeds, user can proceed but warned.
result: [pending]

## Summary

total: 12
passed: 1
issues: 0
pending: 11
skipped: 0

## Gaps

[none yet]
