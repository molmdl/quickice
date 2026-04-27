---
status: resolved
trigger: "guest-itp-not-provided-or-included"
created: 2026-04-27T00:00:00.000Z
updated: 2026-04-27T00:00:00.000Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: ROOT CAUSE FOUND - InterfaceGROMACSExporter does NOT copy guest .itp files
test: Apply fix and verify
expecting: Verified by testing guest .itp path lookup and imports
next_action: COMPLETE - fix applied and verified

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: Guest .itp file should be copied to output directory and included via #include in .top file
actual: Guest .itp file is neither copied nor included in the .top file
errors: None
reproduction: 
  1. Generate hydrate with guest (CH4 or THF)
  2. Generate interface
  3. Insert ion
  4. Export GROMACS files
  5. Check output directory - guest .itp file is missing
  6. Check .top file - no #include for guest.itp

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-27T00:00:00.000Z
  checked: Glob for guest itp files
  found: Guest .itp files exist at:
    - /share/home/nglokwan/quickice/quickice/data/ch4.itp
    - /share/home/nglokwan/quickice/quickice/data/thf.itp
  implication: Guest files exist in data folder, need to find export logic

- timestamp: 2026-04-27T00:00:00.000Z
  checked: hydrate_export.py (HydrateGROMACSExporter)
  found: Successfully copies guest .itp files at lines 143-145:
    ```python
    guest_dest_path = path.with_name(guest_itp_path.name)
    shutil.copy(guest_itp_path, guest_dest_path)
    ```
  implication: Hydrate export works correctly

- timestamp: 2026-04-27T00:00:00.000Z
  checked: export.py (InterfaceGROMACSExporter, lines 466-522)
  found: ONLY copies tip4p-ice.itp, DOES NOT copy guest .itp files:
    ```python
    itp_source = get_tip4p_itp_path()
    shutil.copy(itp_source, itp_path)  # Only copies water .itp
    ```
  implication: MISSING - guest .itp file copy logic

- timestamp: 2026-04-27T00:00:00.000Z
  checked: gromacs_writer.py write_interface_top_file() and write_multi_molecule_top_file()
  found: Both functions correctly write #include for guest .itp files in .top
    - write_interface_top_file writes: #include "ch4.itp" or #include "thf.itp" (lines 499-508)
    - write_multi_molecule_top_file writes #include from itp_files dict (line 711-712)
  implication: .top file will reference guest .itp but file doesn't exist -> will fail in GROMACS

## Resolution
root_cause: InterfaceGROMACSExporter.export_interface_gromacs() in export.py does NOT copy guest .itp files to output directory. The .top file includes guest .itp but the file was never copied to the export directory.
fix: Added guest .itp file copy logic in InterfaceGROMACSExporter (lines 548-569) similar to HydrateGROMACSExporter. Added _get_guest_itp_path() helper function (lines 448-472). Guest type determined from first guest atom name in InterfaceStructure.
verification: - Import test passes: `from quickice.gui.export import InterfaceGROMACSExporter, _get_guest_itp_path`
- Guest .itp path lookup works for both ch4 and thf
- All existing tests pass (25 output tests, 1 export test)
files_changed: 
- quickice/gui/export.py: Added _get_guest_itp_path() function and guest .itp copy logic