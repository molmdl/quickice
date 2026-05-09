---
status: resolved
trigger: "custom-mol-random-crash-v2"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:10:00Z
---

## Current Focus
hypothesis: molecule_index construction uses wrong parameters for water/guest/custom molecules (passing end_idx instead of count)
test: Check all MoleculeIndex construction in custom_molecule_inserter.py
expecting: Find incorrect positional arguments passing current_idx + N instead of just N for count parameter
next_action: Fix all MoleculeIndex construction to use correct parameters

## Symptoms
expected: Custom molecule random insertion should complete successfully and show results
actual: Progress bar shows some percentage (not visible where it ends), then application crashes silently
errors: No error message shown
reproduction: 
  1. Load interface structure
  2. Select GRO file (etoh.gro)
  3. Select ITP file (etoh.itp)
  4. Use random placement mode
  5. Click generate
  6. Progress shows some percentage
  7. Application crashes before completion
started: Current issue - possibly related to recent water replacement and molecule_index fixes

## Eliminated

## Evidence
- timestamp: 2026-05-09T00:00:00Z
  checked: Previous fixes context
  found: Recent commits - 86d20a1 (error handling), cb04af9 (molecule_index fix), c66a109 (water replacement count)
  implication: Recent changes may have introduced crash or not properly handling all cases
- timestamp: 2026-05-09T00:01:00Z
  checked: MoleculeIndex dataclass definition (types.py lines 22-39)
  found: MoleculeIndex has fields: start_idx (int), count (int), mol_type (str)
  implication: Parameters should be (start_idx, count, mol_type) NOT (start_idx, end_idx, mol_type)
- timestamp: 2026-05-09T00:02:00Z
  checked: MoleculeIndex construction in custom_molecule_inserter.py
  found: Line 426, 613, 762 use positional args MoleculeIndex(current_idx, current_idx + N, "water") - WRONG, passes end_idx as count
  implication: count field gets huge value causing array indexing errors and crashes
- timestamp: 2026-05-09T00:03:00Z
  checked: Custom molecule index construction
  found: Lines 627, 775 use MoleculeIndex(current_idx, current_idx + (end - start), "custom") - same issue
  implication: All molecule index construction for water/guest/custom is broken
- timestamp: 2026-05-09T00:04:00Z
  checked: Guest molecule index construction
  found: Lines 435-438 use MoleculeIndex(mol_idx.start_idx - shift, mol_idx.end_idx - shift, "guest") - passes end_idx as count
  implication: Guest molecule index also broken

## Resolution
root_cause: MoleculeIndex construction passes end_idx instead of count parameter. Commit cb04af9 only fixed ice molecules but left water/guest/custom molecules broken. When count is end_idx (e.g., 1200+ instead of 4), array indexing goes out of bounds causing crash.
fix: Fixed all MoleculeIndex construction in custom_molecule_inserter.py to use keyword arguments with correct count values (not end_idx). Changed 6 locations: water molecules (lines 426, 613, 762), guest molecules (lines 435-438), and custom molecules (lines 627, 775).
verification: 
  - Created test_molecule_index_fix.py to verify MoleculeIndex.count values
  - Test confirms all molecules have correct count: ice=4, water=4, custom=3
  - Test confirms all indices are sequential and correct
  - Existing tests in tests/test_custom_molecule.py all pass (7/7)
files_changed: [quickice/structure_generation/custom_molecule_inserter.py]
