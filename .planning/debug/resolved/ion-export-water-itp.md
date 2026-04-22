---
status: resolved
trigger: "Fix ion export - missing water ITP file"
created: 2026-04-22T00:00:00.000Z
updated: 2026-04-22T00:00:00.000Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: Root cause identified - IonGROMACSExporter doesn't copy water ITP file
test: Adding water ITP file copy to ion export
expecting: Water ITP file will be exported alongside ion.itp
next_action: Fix implemented and verified

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: Export should include ion.itp AND tip4p-ice.itp (or similar water topology file)
actual: Only ion.itp is being exported, water ITP file is missing
errors: N/A
reproduction: Use File → Export Ions for GROMACS, check export directory
started: Unknown - feature not working

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-22
  checked: IonGROMACSExporter.export_ion_gromacs() in quickice/gui/export.py
  found: The method writes ion.itp (lines 78-80) but does NOT copy the water ITP file
  implication: Missing tip4p-ice.itp file in export

- timestamp: 2026-04-22
  checked: hydrate_export.py for comparison
  found: Uses shutil.copy(tip4p_itp_path, water_itp_path) to copy water ITP (lines 139-141)
  implication: Fix pattern identified - add similar code to IonGROMACSExporter

- timestamp: 2026-04-22
  checked: gromacs_writer.py
  found: get_tip4p_itp_path() returns path to tip4p-ice.itp in data directory
  implication: Can reuse this function

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: IonGROMACSExporter.export_ion_gromacs() only writes ion.itp but does not copy the water (tip4p-ice.itp) file to the export directory, unlike other exporters (InterfaceGROMACSExporter, hydrate export)
fix: Added shutil.copy() of tip4p-ice.itp to export directory after writing ion.itp (lines 82-87 in export.py)
verification: Code compiles successfully, import works, 307 tests pass (1 pre-existing unrelated failure)
files_changed: ["quickice/gui/export.py"]
