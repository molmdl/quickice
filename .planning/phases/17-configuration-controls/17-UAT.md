---
status: complete
phase: 17-configuration-controls
source: [17-01-SUMMARY.md, 17-02-SUMMARY.md]
started: 2026-04-11T13:38:41Z
updated: 2026-04-11T13:38:41Z
---

## Current Test

[testing complete]

## Tests

### 1. Mode Selection Dropdown
expected: Tab 2 has a mode dropdown showing three options: "Slab", "Pocket", "Piece". Default selection is "Slab".
result: pass

### 2. Mode-Specific Input Panels
expected: Selecting "Slab" shows ice thickness + water thickness inputs. Selecting "Pocket" shows pocket diameter + shape selector. Selecting "Piece" shows informational label with candidate dimensions.
result: pass

### 3. Box Size Input Validation
expected: Box dimension inputs (X/Y/Z) accept values 0.5-100 nm. Invalid values (below 0.5, above 100, non-numeric) show validation errors. Box Z defaults to 10 nm (vs X/Y at 5 nm).
result: pass

### 4. Slab Mode Thickness Inputs
expected: Ice thickness and water thickness inputs accept 0.5-50 nm range. Both default to 3 nm. Invalid values show validation errors.
result: pass

### 5. Pocket Mode Inputs
expected: Pocket diameter input accepts 0.5-50 nm range (default 2 nm). Shape selector shows "Sphere" option.
result: pass

### 6. Piece Mode Informational Display
expected: Piece mode shows label with ice dimensions derived from selected candidate (e.g., "Ice dimensions: X × Y × Z nm"). No manual dimension inputs.
result: pass

### 7. Random Seed Input
expected: Seed input accepts integers 1-999999. Default is 42. Out-of-range or non-numeric values show validation errors.
result: pass

### 8. Tooltips on All Inputs
expected: Each input has descriptive tooltip. Mode selector explains geometry types. Box dimensions mention nm and range. Thickness/diameter explain layer/cavity size. Seed mentions reproducibility.
result: pass

### 9. Generate Button Enable/Disable
expected: Generate button is disabled when no candidate selected. Enabled when candidate is selected.
result: pass

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
