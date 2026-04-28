---
status: resolved
trigger: "Fix issue: ion_export_residue_name_hardcoded - write_ion_gro_file() uses hardcoded \"GUE\" instead of reading residue name from itp."
created: 2026-04-28T12:00:00Z
updated: 2026-04-28T12:30:00Z
symptoms_prefilled: true
---

## Current Focus

hypothesis: FIXED - write_ion_gro_file() and write_ion_top_file() now use dynamic residue names
test: Ran test_ion_residue_fix.py - all 5 tests passed
expecting: Code now uses detect_guest_type_from_atoms() + get_guest_residue_name() instead of hardcoded "GUE"
next_action: Issue resolved, mark as complete

## Symptoms

expected: Residue name should be read from itp file, not hardcoded
actual: write_ion_gro_file() uses hardcoded "GUE" for guest molecules at line 1186
actual: write_ion_top_file() uses hardcoded "GUE" at line 1249 and includes "guest.itp" at line 1233
errors: N/A (functional issue, not error)
reproduction: Call write_ion_gro_file() with guest molecules - residue name always "GUE"
started: Always broken (hardcoded)

## Eliminated

- hypothesis: Issue is in molecule_index not storing guest type
  evidence: molecule_index stores mol_type="guest" (generic). Need to detect from atom names.
  timestamp: 2026-04-28T12:07:00Z

## Evidence

- timestamp: 2026-04-28T12:00:00Z
  checked: Task description and context
  found: get_guest_residue_name() and reorder_guest_atoms() already exist in gromacs_writer.py
  implication: Need to use these existing functions instead of hardcoded values

- timestamp: 2026-04-28T12:05:00Z
  checked: gromacs_writer.py lines 1077-1251 (write_ion_gro_file and write_ion_top_file)
  found: |
    HARDCODED "GUE" at line 1186 in write_ion_gro_file()
    HARDCODED "GUE" at line 1249 in write_ion_top_file()
    HARDCODED '#include "guest.itp"' at line 1233 in write_ion_top_file()
  implication: These need to be replaced with dynamic values based on guest type detection

- timestamp: 2026-04-28T12:06:00Z
  checked: How other functions handle guest type detection
  found: |
    write_interface_gro_file() (lines 560-645): Detects guest type by analyzing atom names using _get_molecule_atoms()
    write_interface_top_file() (lines 770-859): Similarly detects guest type from first atom
    write_multi_molecule_gro_file() (lines 861-941): Uses mol.mol_type directly ("ch4", "thf", etc.)
    write_multi_molecule_top_file() (lines 944-1075): Uses mol.mol_type directly
  implication: For ion_structure, molecule_index has mol_type="guest" (not specific), so need to detect from atom names

- timestamp: 2026-04-28T12:07:00Z
  checked: IonStructure and MoleculeIndex types (types.py)
  found: |
    MoleculeIndex has: start_idx, count, mol_type
    For guests in ion_structure, mol_type="guest" (generic, not "ch4" or "thf")
    IonStructure has: molecule_index, guest_nmolecules, guest_atom_count
  implication: Need to detect guest type from atom names when processing in write_ion_*_file()

- timestamp: 2026-04-28T12:10:00Z
  checked: Applied fix to gromacs_writer.py
  found: |
    ADDED: detect_guest_type_from_atoms() function (lines 671-719)
    FIXED: write_ion_gro_file() - now detects guest type, uses get_guest_residue_name(), applies reorder_guest_atoms()
    FIXED: write_ion_top_file() - now detects guest type, uses correct residue name and includes {guest_type}.itp
  implication: Fix is complete, needs verification

- timestamp: 2026-04-28T12:25:00Z
  checked: Fixed _get_molecule_atoms() to check THF before CH4
  found: |
    Original _get_molecule_atoms() checked CH4 first, causing THF to be misidentified
    Fixed by checking THF (has O) before CH4 (no O)
  implication: Both CH4 and THF now correctly detected

- timestamp: 2026-04-28T12:30:00Z
  checked: Ran test_ion_residue_fix.py (5 tests)
  found: |
    ALL TESTS PASSED:
    - Test 1: detect_guest_type_from_atoms() - CH4, THF, H2 detected correctly
    - Test 2: get_guest_residue_name() - returns CH4, THF, UNK correctly
    - Test 3: write_ion_gro_file() - CH4 - no "GUE" found, "CH4" present
    - Test 4: write_ion_top_file() - CH4 - no "GUE" found, "CH4" and "ch4.itp" present
    - Test 5: write_ion_gro_file() - THF - no "GUE" found, "THF" present
  implication: Fix verified and working

## Resolution

root_cause: write_ion_gro_file() and write_ion_top_file() used hardcoded "GUE" residue name and "guest.itp" include. The molecule_index stores mol_type="guest" (generic), so the code needs to detect the actual guest type from atom names.
fix: |
  1. Added detect_guest_type_from_atoms() function to detect guest type ("ch4", "thf", etc.) from atom names
  2. Fixed _get_molecule_atoms() to check THF (has O) BEFORE CH4 (no O) to avoid misidentification
  3. Modified write_ion_gro_file():
     - Detect guest type from atom names using detect_guest_type_from_atoms()
     - Use get_guest_residue_name() instead of hardcoded "GUE"
     - Apply reorder_guest_atoms() to reorder atom names AND positions
  4. Modified write_ion_top_file():
     - Detect guest type from first guest molecule's atom names
     - Use get_guest_residue_name() for residue name in [ molecules ] section
     - Include "{guest_type}.itp" instead of hardcoded "guest.itp"
verification: |
  Created and ran test_ion_residue_fix.py with 5 tests:
  - detect_guest_type_from_atoms() correctly identifies CH4, THF, H2
  - get_guest_residue_name() returns correct residue names from itp files
  - write_ion_gro_file() outputs correct residue name (CH4/THF) instead of "GUE"
  - write_ion_top_file() outputs correct residue name and includes correct .itp file
  - Atoms are properly reordered to match .itp canonical order
files_changed:
  - quickice/output/gromacs_writer.py: Added detect_guest_type_from_atoms(), fixed _get_molecule_atoms() THF detection, modified write_ion_gro_file() and write_ion_top_file()

## Resolution

root_cause: 
fix: 
verification: 
files_changed: []
