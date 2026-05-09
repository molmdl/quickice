---
status: resolved
trigger: "custom-mol-random-insertion"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - Worker uses wrong attribute name n_molecules instead of custom_molecule_count
test: Verified fix by running tests - test_custom_molecule_inserter_random PASSED
expecting: Tests pass, no AttributeError
next_action: Archive debug session

## Symptoms

expected: Custom molecule insertion should complete successfully and display the number of molecules inserted
actual: Insertion fails at the end with AttributeError. The progress shows: 10, 20, 40, 90, 100 then crashes
errors: "AttributeError: 'CustomMoleculeStructure' object has no attribute 'n_molecules'" at quickice/gui/custom_molecule_worker.py line 120
reproduction: Load interface structure, select GRO file (etoh.gro), select ITP file (etoh.itp), use random placement mode, click generate
started: Current issue - no indication if it ever worked
context:
  - Interface structure loaded for validation
  - Liquid region: 41256 water atoms
  - Files validated successfully
  - Progress: 10, 20, 40, 90, 100 then error

## Eliminated

## Evidence

- timestamp: 2026-05-09T00:00:00Z
  checked: Line 120 in custom_molecule_worker.py
  found: Error occurs when accessing result.n_molecules where result is returned from inserter.place_random()
  implication: Either CustomMoleculeStructure lacks n_molecules attribute, or place_random returns wrong type

- timestamp: 2026-05-09T00:00:00Z
  checked: CustomMoleculeStructure dataclass in types.py (lines 489-527)
  found: CustomMoleculeStructure has attribute custom_molecule_count (line 526), NOT n_molecules
  implication: Worker is using wrong attribute name

- timestamp: 2026-05-09T00:00:00Z
  checked: place_random and place_custom methods in custom_molecule_inserter.py
  found: Both methods return CustomMoleculeStructure with custom_molecule_count attribute (lines 463, 589)
  implication: Confirmed - the attribute name mismatch is the root cause

- timestamp: 2026-05-09T00:00:00Z
  checked: main_window.py line 1112
  found: Correctly uses result.custom_molecule_count
  implication: main_window.py is already correct, only custom_molecule_worker.py had the bug

- timestamp: 2026-05-09T00:00:00Z
  checked: Syntax validation with py_compile
  found: No syntax errors after fix
  implication: Fix is syntactically correct

- timestamp: 2026-05-09T00:00:00Z
  checked: tests/test_custom_molecule.py - test_custom_molecule_inserter_random
  found: Test PASSED - verifies result.custom_molecule_count is correctly accessible
  implication: Fix resolves the AttributeError issue

## Resolution

root_cause: Worker code uses n_molecules attribute but CustomMoleculeStructure defines custom_molecule_count attribute. Attribute name mismatch causes AttributeError.
fix: Changed result.n_molecules to result.custom_molecule_count in custom_molecule_worker.py line 120
verification: Test test_custom_molecule_inserter_random PASSED, confirming the attribute is correctly accessible. Syntax validation passed.
files_changed: ["quickice/gui/custom_molecule_worker.py"]
