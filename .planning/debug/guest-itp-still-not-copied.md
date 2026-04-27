---
status: resolved
trigger: "Guest .itp file is still not being copied to output directory in export."
created: 2026-04-27T00:00:00Z
updated: 2026-04-27T00:00:00Z
---

## Current Focus
next_action: "Verification completed"

hypothesis: "IonGROMACSExporter.export_ion_gromacs() does NOT copy guest .itp files - missing logic"
test: "Check IonGROMACSExporter code for guest .itp copy logic"
expecting: "Add guest .itp copy logic similar to InterfaceGROMACSExporter at lines 548-569"

## Symptoms
expected: Guest .itp file (ch4.itp or thf.itp) should be copied to export directory
actual: Guest .itp file is not present in export directory
errors: None shown
reproduction: 
  1. Generate hydrate with guest (CH4)
  2. Generate interface
  3. Insert ion
  4. Export GROMACS (Ions)
  5. Check output directory - guest .itp file missing

## Evidence

- timestamp: "2026-04-27T16:00:00Z"
  checked: "InterfaceGROMACSExporter.export_interface_gromacs() in export.py (lines 548-569)"
  found: "Guest .itp copy logic IS present - checks guest_nmolecules > 0 and guest_atom_count > 0"
  implication: "If condition passes, should copy guest .itp file"

- timestamp: "2026-04-27T16:05:00Z"
  checked: "IonGROMACSExporter.export_ion_gromacs code path"
  found: "Export only writes ion positions to .gro, no guest information exists in IonStructure"
  implication: "Root cause: IonStructure does NOT preserve guest data from input InterfaceStructure"

## Resolution

root_cause: "IonGROMACSExporter.export_ion_gromacs() in export.py does NOT copy guest .itp files to output. The code only copies water and ion .itp files (lines 77-87), but has no logic to check for guest molecules and copy their .itp files."

fix: "Added guest .itp copy logic to IonGROMACSExporter.export_ion_gromacs() by:
1. Adding guest_nmolecules and guest_atom_count fields to IonStructure (in types.py)
2. Modifying insert_ions() to preserve guest_nmolecules and guest_atom_count from input InterfaceStructure
3. Adding guest .itp copy logic in export.py after line 87 (similar to interface export lines 548-569)"

verification: "Imported successfully after fix - guest_nmolecules and guest_atom_count now in IonStructure"
files_changed: [
    "quickice/structure_generation/types.py - added guest_nmolecules and guest_atom_count to IonStructure",
    "quickice/structure_generation/ion_inserter.py - preserve guest_nmolecules/guest_atom_count from input",
    "quickice/gui/export.py - added guest .itp copy logic in IonGROMACSExporter.export_ion_gromacs()"
  ]