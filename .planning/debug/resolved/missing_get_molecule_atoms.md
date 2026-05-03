---
status: resolved
trigger: "Fix the missing `_get_molecule_atoms` function that causes hydrate export to fail with error: \"name '_get_molecule_atoms' is not defined\""
created: 2026-05-03T00:00:00Z
updated: 2026-05-03T00:10:00Z
---

## Current Focus

hypothesis: Missing _get_molecule_atoms function restored and verified
test: All tests pass, export functionality works correctly
expecting: Hydrate export succeeds without NameError
next_action: Archive debug session

## Symptoms

expected: Hydrate interface slab exports successfully to GRO file
actual: Export fails with NameError: name '_get_molecule_atoms' is not defined
errors: File "quickice/output/gromacs_writer.py", line 693, in detect_guest_type_from_atoms - calls _get_molecule_atoms which doesn't exist
reproduction: Generate CH4 hydrate interface slab - export fails during write_interface_gro_file
started: After consolidation commit a73afe0

## Eliminated

- hypothesis: Function never existed
  evidence: Found function in git history before commit a73afe0
  timestamp: 2026-05-03T00:00:00Z

## Evidence

- timestamp: 2026-05-03T00:00:00Z
  checked: quickice/output/gromacs_writer.py line 693
  found: detect_guest_type_from_atoms calls _get_molecule_atoms(atom_names) but function doesn't exist
  implication: Function is missing from current code

- timestamp: 2026-05-03T00:00:00Z
  checked: Git history commit a73afe0^:quickice/output/gromacs_writer.py
  found: Function existed before consolidation commit with full implementation
  implication: Function was accidentally deleted during code consolidation

- timestamp: 2026-05-03T00:00:00Z
  checked: Original _get_molecule_atoms implementation
  found: Function extracts atom names for one complete guest molecule, handles THF, CH4, H2, CO2, and Me
  implication: Need to restore this function and update to use count_guest_atoms from molecule_utils

- timestamp: 2026-05-03T00:05:00Z
  checked: Function import and basic functionality
  found: Function successfully imports and handles CH4, THF, H2 test cases correctly
  implication: Function is working as expected

- timestamp: 2026-05-03T00:05:00Z
  checked: Hydrate guest tiling tests
  found: tests/test_hydrate_guest_tiling.py passes (2 tests)
  implication: Hydrate generation works with restored function

- timestamp: 2026-05-03T00:05:00Z
  checked: Interface export tests
  found: .planning/debug/test_interface_export_itp.py passes - THF and CH4 export work correctly
  implication: Export functionality fully restored

## Resolution

root_cause: _get_molecule_atoms function was deleted during consolidation in commit a73afe0 but is still referenced by detect_guest_type_from_atoms
fix: Restored _get_molecule_atoms function in quickice/output/gromacs_writer.py (line 676). Updated to use count_guest_atoms from molecule_utils instead of deprecated _count_guest_atoms. Function extracts atom names for one complete guest molecule (THF, CH4, H2, CO2, or Me).
verification: All tests pass. Hydrate guest tiling tests pass (2 tests). Interface export tests pass (THF and CH4 export work correctly). Ion hydrate test passes. Function correctly detects CH4, THF, H2 guest types from atom names.
files_changed: [quickice/output/gromacs_writer.py]
