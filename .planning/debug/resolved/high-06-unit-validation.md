---
status: resolved
trigger: "HIGH-06 unit-validation - No validation of overlap threshold units - hardcoded 0.25 nm without validation"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:20:00Z
---

## Current Focus
hypothesis: ROOT CAUSE CONFIRMED - No validation at any level: detect_overlaps, InterfaceConfig, or UI
test: Verify fix with comprehensive tests (validation, existing functionality, integration)
expecting: All tests pass, validation catches invalid values, existing code works
next_action: Archive resolved debug session

## Symptoms
expected: Overlap threshold should be validated to be in correct units (nm)
actual: Function signature indicates nm, but callers might pass Angstrom values by mistake
errors: If Angstrom passed instead of nm, threshold would be 10x larger than intended (0.25 Å vs 0.25 nm)
reproduction: Call detect_overlaps with value in Angstrom instead of nm
started: Always accepted any float without validation

## Eliminated

## Evidence

- timestamp: 2026-04-09T00:00:00Z
  checked: quickice/structure_generation/overlap_resolver.py
  found: Function signature uses _nm suffix for parameters, default threshold_nm=0.25, docstring explains units
  implication: Naming convention is good but no runtime validation exists

- timestamp: 2026-04-09T00:02:00Z
  checked: All mode files (piece.py, pocket.py, slab.py)
  found: All three modes call detect_overlaps with config.overlap_threshold from InterfaceConfig
  implication: Threshold flows from InterfaceConfig through modes to detect_overlaps - need to check InterfaceConfig

- timestamp: 2026-04-09T00:03:00Z
  checked: quickice/structure_generation/types.py
  found: InterfaceConfig.overlap_threshold = 0.25 with comment, InterfaceConfig.from_dict hardcodes 0.25
  implication: Threshold not exposed in UI, always hardcoded to 0.25 nm - reduces risk but still no validation

- timestamp: 2026-04-09T00:04:00Z
  checked: quickice/structure_generation/water_filler.py
  found: fill_region_with_water accepts overlap_threshold_nm but says "Used for informational purposes"
  implication: Parameter not used for validation in water_filler, just passed through

- timestamp: 2026-04-09T00:05:00Z
  checked: Codebase-wide search for Angstrom/nm unit handling
  found: Extensive documentation about nm internally, Å for display, pdb_writer multiplies by 10 for Å
  implication: Project has strong unit conventions but lacks validation at function boundaries

- timestamp: 2026-04-09T00:06:00Z
  checked: quickice/gui/interface_panel.py get_configuration()
  found: No overlap_threshold parameter exposed in UI, all config returned without threshold
  implication: Threshold always hardcoded to 0.25 nm in InterfaceConfig.from_dict - no user control

- timestamp: 2026-04-09T00:10:00Z
  checked: Complete code flow from UI to detect_overlaps
  found: UI → InterfaceConfig.from_dict(hardcode 0.25) → mode files → detect_overlaps (no validation)
  implication: ROOT CAUSE: No validation at ANY level. Hardcoded 0.25 reduces risk but code is vulnerable to direct modification or future UI additions without validation

## Resolution
root_cause: No validation of overlap_threshold at any level (detect_overlaps, InterfaceConfig, UI). Function accepts any float without checking if it's in reasonable range for nm units (0.1-1.0 nm). This allows silent failures if Angstrom values are accidentally passed (0.25 Å vs 0.25 nm = 10x difference).
fix: Added three-layer defense:
  1. detect_overlaps: Added ValueError for threshold_nm outside [0.1, 1.0] nm with helpful error message explaining unit conversion
  2. InterfaceConfig: Added __post_init__ validation for overlap_threshold in same range
  3. Unit conversion helpers: Added angstrom_to_nm() and nm_to_angstrom() functions for convenience
verification:
  - All 6 validation tests passed (valid/invalid thresholds in detect_overlaps and InterfaceConfig)
  - Unit conversion helpers work correctly (angstrom_to_nm(2.5) = 0.25, nm_to_angstrom(0.25) = 2.5)
  - Existing overlap detection functionality unchanged (detects correct overlaps with default threshold)
  - InterfaceConfig.from_dict works correctly with hardcoded threshold 0.25
  - 160 tests passed, 1 pre-existing test failure unrelated to changes
files_changed:
  - quickice/structure_generation/overlap_resolver.py: Added validation + unit conversion helpers
  - quickice/structure_generation/types.py: Added __post_init__ validation to InterfaceConfig
  - quickice/structure_generation/__init__.py: Exported unit conversion functions
