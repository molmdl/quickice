---
status: resolved
trigger: "MED-02 piece-mode-box-validation - Box validation gap in piece mode - no validation that water filling will fit"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:00:00Z
---

## Current Focus
hypothesis: CONFIRMED - Box validation only checks if box > ice, but doesn't validate minimum water layer thickness
test: Implementing fix in interface_builder.py
expecting: Add minimum water layer validation based on overlap threshold
next_action: Implement minimum water layer thickness validation (at least overlap_threshold = 0.25 nm)

## Symptoms
expected: Validation should ensure water can fill remaining space with reasonable density
actual: Only checks if box dimensions are larger than ice piece
errors: Very thin water layers around ice could lead to high overlap removal rates or unrealistic structures
reproduction: Create piece mode interface with very thin water layer around ice piece
started: Always lacked this validation

## Eliminated

## Evidence
- timestamp: 2026-04-09T00:00:00Z
  checked: interface_builder.py lines 140-162
  found: Piece mode validation only checks box > ice_dims, no water layer validation
  implication: Thin water layers pass validation but cause problems

- timestamp: 2026-04-09T00:00:00Z
  checked: water_filler.py and types.py
  found: Default overlap_threshold = 0.25 nm (2.5 Å), TIP4P water template is 1.86824 nm box
  implication: Water layers thinner than overlap threshold will have most molecules removed

- timestamp: 2026-04-09T00:00:00Z
  checked: piece.py overlap detection
  found: Water molecules within overlap_threshold of ice O atoms are removed
  implication: If water layer < overlap_threshold, nearly all water removed -> unrealistic structure

## Resolution
root_cause: Missing validation for minimum water layer thickness in piece mode. Box can be just 0.01 nm larger than ice, but water molecules need at least 0.25 nm (overlap_threshold) spacing to avoid being removed as overlapping.
fix: Added minimum water layer validation requiring water_layer (box - ice) >= overlap_threshold for each dimension. Prevents unrealistic thin water layers that would result in zero or near-zero water molecules after overlap removal.
verification: Tested with 4 cases: (1) valid thick layer passes, (2) thin layer fails with correct error, (3) exact threshold passes, (4) box smaller than ice fails with original error. All 61 structure generation tests pass including 7 new validation tests.
files_changed: [quickice/structure_generation/interface_builder.py, tests/test_piece_mode_validation.py]
