---
status: investigating
trigger: "Fix ValueError in interface_viewer.py - hydrate uses TIP4P atoms, not classic ice"
created: 2026-04-21T00:00:00Z
updated: 2026-04-21T00:00:00Z
---

## Current Focus

hypothesis: Validation at line 482 strictly checks for ["O", "H", "H"], rejecting TIP4P
test: Modify validation to accept both classic (O, H, H) and TIP4P (OW, HW1, HW2)
expecting: Fix allows hydrate source to work
next_action: Apply fix to vtk_utils.py line 482

## Symptoms

expected: Generate interface from hydrate source should work with TIP4P atom names (OW, HW1, HW2)
actual: ValueError: Invalid ice atom ordering for molecule 0: expected ['O', 'H', 'H'], got ['OW', 'HW1', 'HW2']
errors:
- "ValueError: Invalid ice atom ordering for molecule 0: expected ['O', 'H', 'H'], got ['OW', 'HW1', 'HW2']"
reproduction: Generate interface from hydrate source and click "Generate"
started: Unknown

## Eliminated

## Evidence

- timestamp: 2026-04-21T00:00:00Z
  checked: Error message mentions "interface_to_vtk_molecules()" in vtk_utils.py
  found: Need to find this function and its validation logic
  implication: The function validates atom ordering

- timestamp: 2026-04-21T00:00:00Z
  checked: vtk_utils.py lines 477-494 (validate_ice_bonds logic)
  found: Validation at line 482 strictly checks ice_names_per_mol == ["O", "H", "H"]
  implication: This strict check breaks TIP4P hydrate which uses ["OW", "HW1", "HW2"]

## Resolution

root_cause: Validation at vtk_utils.py:482 strictly checked for classic ice (["O", "H", "H"]) only, rejecting TIP4P hydrate atoms (["OW", "HW1", "HW2"])
fix: Modified validation to accept both classic ice ["O", "H", "H"] and TIP4P ["OW", "HW1", "HW2"]
verification: |
  - All ordering tests pass (5/5)
  - New test_interface_tip4p_hydrate added and passes
  - Regression check: 307 tests passed, 1 pre-existing failure (unrelated to fix)
files_changed: [quickice/gui/vtk_utils.py, tests/test_interface_ordering_validation.py]