---
status: resolved
trigger: "interface-export-missing-itp-copy-and-verify-ch4"
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:06:00Z
---

## Current Focus

hypothesis: VERIFIED - Guest .itp copy now uses correct index and detect_guest_type_from_atoms()
test: Created comprehensive test verifying THF and CH4 exports work correctly
expecting: Both THF and CH4 exports should copy correct .itp file
next_action: Update debug file with verification results and commit

## Symptoms

expected: 
1. When exporting interface to GROMACS, the thf.itp (or ch4.itp) file should be copied to the export directory alongside the .gro and .top files
2. CH4 hydrate exports should work correctly with all recent THF-related fixes

actual:
1. Interface export creates interface_slab.gro and interface_slab.top, but doesn't copy thf.itp (the TOP file includes it but file is missing)
2. Unknown if CH4 still works after all the THF-specific changes

errors: No explicit errors, but incomplete export package

reproduction:
1. Generate THF sII hydrate → Export to interface → GROMACS export → Check export directory for thf.itp
2. Generate CH4 sI hydrate → Export to interface → GROMACS export → Verify all files correct

started: Current issue discovered during testing

## Eliminated

<!-- None yet -->

## Evidence

- timestamp: 2026-04-30T00:01:00Z
  checked: export.py lines 584-605 (InterfaceGROMACSExporter.export_interface_gromacs)
  found: Code uses ice_end index (ice_atom_count) to look for guest atoms, but guests now start at ice_atom_count + water_atom_count
  implication: Wrong atom is checked, so guest_type detection fails

- timestamp: 2026-04-30T00:02:00Z
  checked: export.py lines 587-595 (guest type detection logic)
  found: Uses simplistic check: first_guest_atom in ["Me", "C"] for ch4, ["O", "c"] for thf
  implication: This doesn't match GAFF2 atom types (os, c5, hc, h1 for THF; c3, hc for CH4)

- timestamp: 2026-04-30T00:03:00Z
  checked: gromacs_writer.py detect_guest_type_from_atoms() (lines 649-699)
  found: Robust function that correctly detects guest type from atom composition
  implication: IonGROMACSExporter uses this function correctly, InterfaceGROMACSExporter should too

- timestamp: 2026-04-30T00:04:00Z
  checked: types.py InterfaceStructure documentation (lines 218-269)
  found: Documentation confirms atom ordering: ice → water → guests
  implication: Guest atoms start at ice_atom_count + water_atom_count, not ice_atom_count

- timestamp: 2026-04-30T00:05:00Z
  checked: Created test_interface_export_itp.py and ran tests
  found: All tests pass - THF and CH4 .itp files are correctly copied
  implication: Fix works correctly for both THF and CH4 guest types

## Resolution

root_cause: InterfaceGROMACSExporter.export_interface_gromacs used ice_end index (ice_atom_count) to look for guest atoms, but guests actually start at ice_atom_count + water_atom_count due to ordering change in commit 90afe86. This caused the wrong atom to be checked for guest type detection, leading to incorrect guest type or None, which prevented .itp file from being copied.
fix: Updated export_interface_gromacs to use detect_guest_type_from_atoms() with correct guest atom range (starting at ice_atom_count + water_atom_count)
verification: Created comprehensive test that verifies: (1) Guest type detection works for THF and CH4, (2) .itp files are copied correctly, (3) .top files include correct .itp references
files_changed: [quickice/gui/export.py]
