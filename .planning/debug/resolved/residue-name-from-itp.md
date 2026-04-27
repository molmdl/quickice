---
status: resolved
trigger: "residue-name-from-provided-itp"
created: 2026-04-27T00:00:00Z
updated: 2026-04-27T00:00:00Z
---

## Current Focus
hypothesis: RESOLVED - residue name now correctly read from itp file
test: All tests pass, verified with manual testing
expecting: Residue names match the values in provided itp files
next_action: Archive session

## Symptoms
expected: Residue name in exported files matches guest itp provided in quickice/data
actual: Residue name hardcoded as "CH4"/"THF" in gromacs_writer.py
errors: None
reproduction:
  1. Check ch4.itp in quickice/data for residue name (shows "ch4" in [moleculetype], "CH4" in [atoms])
  2. Generate hydrate/interface/ion
  3. Export GROMACS
  4. Residue name hardcoded instead of parsed from itp file
started: Unknown

## Eliminated

## Evidence
- timestamp: 2026-04-27
  checked: ch4.itp and thf.itp files in quickice/data
  found: 
    - ch4.itp: [moleculetype] name = "ch4" (lowercase), [atoms] resname = "CH4" (uppercase)
    - thf.itp: [moleculetype] name = "thf" (lowercase), [atoms] resname = "THF" (uppercase)
  implication: The residue name in the .gro file should match what's in the .itp file's [atoms] section

- timestamp: 2026-04-27
  checked: gromacs_writer.py lines 343-363, 524-529
  found: Residue name hardcoded as "CH4"/"THF" based on first atom detection
  implication: Should parse from itp file instead of guessing

- timestamp: 2026-04-27
  checked: MOLECULE_TO_GROMACS dict (lines 19-28)
  found: Maps "ch4" -> {"res_name": "CH4", ...} with hardcoded uppercase values
  implication: Should be read from actual itp file

- timestamp: 2026-04-27
  checked: Implementation verification
  found: All tests pass (59 tests), manual testing confirms residue names read correctly from itp
  implication: Fix works correctly

## Resolution
root_cause: Residue name was hardcoded as "CH4" or "THF" in gromacs_writer.py instead of being parsed from the provided itp file
fix: 
  1. Added parse_itp_residue_name() function to read residue name from .itp file's [atoms] section
  2. Added get_guest_residue_name() function to get residue name for a guest type from bundled itp
  3. Updated write_interface_gro_file() to use get_guest_residue_name() instead of hardcoded values
  4. Updated write_interface_top_file() to use get_guest_residue_name() for [molecules] section
  5. Updated write_multi_molecule_gro_file() to use get_guest_residue_name() for guest molecules
  6. Updated write_multi_molecule_top_file() to use get_guest_residue_name() for [molecules] section
verification: 
  - All 59 structure generation tests pass
  - Manual verification shows CH4 residue name correctly read from ch4.itp
  - Manual verification shows THF residue name correctly read from thf.itp
  - GRO files now use correct residue names matching itp files
  - TOP files [molecules] section now uses correct residue names
files_changed:
  - quickice/output/gromacs_writer.py