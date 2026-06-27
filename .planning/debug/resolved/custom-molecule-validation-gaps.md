---
status: resolved
trigger: "Two validation gaps in custom molecule GRO/ITP upload flow: (1) No dialog when GRO resname MOL ≠ ITP moleculetype etoh, (2) Missing [ atomtypes ] section passes validation silently"
created: 2026-06-27T00:00:00Z
updated: 2026-06-27T00:30:00Z
---

## Current Focus

hypothesis: CONFIRMED — Two bugs found:
  1. molecule_validator.py lines 157-161: When GRO resname is in GENERIC_RESIDUE_NAMES, it logs info but sets residue_name_mismatch=False (no dialog triggered)
  2. custom_molecule_panel.py lines 645-663: _validate_files() never checks/displays warnings list from ValidationResult
test: Code analysis complete, now implementing fixes
expecting: After fix 1, MOL vs etoh triggers dialog; After fix 2, missing atomtypes warning is shown
next_action: Implement fixes in molecule_validator.py and custom_molecule_panel.py

## Symptoms

expected_1: When user uploads etoh.gro (resname "MOL") and etoh.itp (moleculetype "etoh"), a dialog should appear offering the user a choice about the residue name mismatch
actual_1: No dialog appears — validation passes without any name mismatch notification
errors_1: None (silent omission)

expected_2: When user uploads etoh_no_atomtypes.itp (which has [ atomtypes ] section removed), a warning should appear about missing [ atomtypes ]
actual_2: Validation passes silently — no warning about missing atomtypes
errors_2: None (silent omission)

reproduction_1: Upload quickice/data/custom/etoh.gro + etoh.itp → no dialog
reproduction_2: Upload quickice/data/custom/etoh.gro + test_invalid/etoh_no_atomtypes.itp → no warning
started: Possibly since Phase 34.6-01 (generic residue name suppression)

## Eliminated

## Evidence

- timestamp: 2026-06-27T00:01
  checked: molecule_validator.py validate_custom_molecule() lines 156-171
  found: When gro_residue_name is in GENERIC_RESIDUE_NAMES (e.g., "MOL"), code just logs info and does NOT set residue_name_mismatch=True — dialog never triggered in GUI
  implication: Bug 1 root cause: generic name suppression is too aggressive, auto-suppresses instead of offering dialog choice

- timestamp: 2026-06-27T00:01
  checked: custom_molecule_panel.py _validate_files() lines 645-663
  found: When validation passes (is_valid=True), code checks residue_name_mismatch but NEVER checks/iterates self.validation_result.warnings — warnings are silently ignored
  implication: Bug 2 root cause: GUI never displays warnings from ValidationResult, even though validator correctly adds them

- timestamp: 2026-06-27T00:02
  checked: molecule_validator.py validate_custom_molecule() lines 173-178
  found: The validator DOES check itp_info.has_atomtypes_section and DOES add a warning for missing atomtypes — the validator logic is correct, but the GUI never displays it
  implication: Bug 2 is purely a GUI issue — validator works, panel doesn't show warnings

- timestamp: 2026-06-27T00:02
  checked: itp_parser.py parse_itp_file() lines 134-139
  found: has_atomtypes_section is correctly set via regex search for [ atomtypes ] — parser works correctly

- timestamp: 2026-06-27T00:02
  checked: test_custom_molecule_panel_34_6.py test_generic_residue_suppression()
  found: Existing test asserts not result.residue_name_mismatch for MOL case — this test will need updating after fix 1 since MOL vs etoh SHOULD now trigger mismatch dialog

## Resolution

## Resolution

root_cause: Three bugs found:
  1. molecule_validator.py: When GRO resname in GENERIC_RESIDUE_NAMES, code auto-suppressed mismatch (residue_name_mismatch=False) instead of flagging it for dialog
  2. custom_molecule_panel.py: _validate_files() never checked/iterated validation_result.warnings — warnings (including missing atomtypes) silently ignored
  3. itp_parser.py: has_atomtypes_section regex matched [ atomtypes ] in COMMENT lines, causing false positives

fix: Applied three targeted fixes:
  1. molecule_validator.py: Always set residue_name_mismatch=True when names differ; added is_generic_residue_name flag so dialog shows appropriate message for generic names
  2. custom_molecule_panel.py: Added _show_validation_warnings() and _show_remaining_warnings() methods; updated _validate_files() to display warnings; updated _show_residue_mismatch_dialog() to handle generic vs real mismatch differently
  3. itp_parser.py: Strip comment lines before regex searching for [ atomtypes ] section

verification: All 1030 tests pass (2 skipped). New tests added covering both bugs.
files_changed:
  - quickice/structure_generation/molecule_validator.py
  - quickice/structure_generation/itp_parser.py
  - quickice/gui/custom_molecule_panel.py
  - tests/test_custom_molecule_panel_34_6.py
  - tests/test_e2e_custom_molecule.py
