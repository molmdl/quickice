---
status: resolved
trigger: "GROMACS export from ion tab is missing inserted solutes - only getting solute_full files"
created: 2026-05-05T00:00:00Z
updated: 2026-05-05T00:15:00Z
---

## Current Focus

hypothesis: Fix has been implemented - need to verify it works correctly
test: Test the fix by running through the reproduction steps and checking exported files
expecting: Exported files should now include THF solutes
next_action: Create test to verify the fix works

## Symptoms

expected: When exporting from ion tab after CH4 hydrate -> slab -> THF solute -> ions, the GROMACS output should include:
- Ice/water framework
- Original CH4 guests from hydrate
- Inserted THF solutes
- Inserted ions

actual: After CH4 hydrate -> slab -> solute THF -> ion, the 3D viewer looks good but:
- Export (Ctrl-S from ion tab) only gives @tmp/solute_full files
- Missing solutes in the export

errors: No errors visible

reproduction: 
1. Generate CH4 hydrate
2. Generate slab/interface
3. Insert THF solute
4. Insert ions
5. Ctrl-S to export from ion tab
6. Check exported files - missing solutes

started: Just discovered

## Eliminated

## Evidence

- timestamp: 2026-05-05T00:00:00Z
  checked: Exported files in tmp/solute_full/
  found: 
    - ions_35na_35cl.gro contains ice/water molecules (SOL)
    - ions_35na_35cl.top shows: 9940 SOL + 1200 CH4 + 35 NA + 35 CL
    - NO THF molecules in the export
    - Missing solutes confirmed
  implication: The export is not including THF solute information - only exporting the base structure + ions + original CH4 guests

- timestamp: 2026-05-05T00:00:01Z
  checked: main_window.py lines 842-896, ion insertion logic
  found:
    - Line 851: When source is "Solute", code extracts `interface = self._current_solute_result.interface_structure`
    - The interface_structure contains only ice + water (no solutes)
    - Line 892-896: `insert_ions(interface, concentration, volume_arg)` is called with the interface
    - Line 899: Result is stored as `self._current_ion_result`
  implication: IonStructure is created from interface_structure, which lacks solute information

- timestamp: 2026-05-05T00:00:02Z
  checked: IonStructure and SoluteStructure definitions in types.py
  found:
    - IonStructure has: guest_nmolecules, guest_atom_count (for guests from hydrate)
    - IonStructure does NOT have: solute_type, solute_positions, solute_atom_names, etc.
    - SoluteStructure has: positions, atom_names, solute_type, n_molecules, molecule_indices, registry
    - SoluteStructure has: interface_structure (ice + water only)
  implication: IonStructure needs solute-related attributes to preserve solute information

- timestamp: 2026-05-05T00:00:03Z
  checked: ion_inserter.py replace_water_with_ions method
  found:
    - Method processes structure.positions, structure.atom_names, structure.molecule_index
    - Lines 424-425: Preserves guest_nmolecules and guest_atom_count from input structure
    - Creates new IonStructure with ice + water + ions
    - Does NOT preserve solute information if present in input structure
  implication: The ion insertion process doesn't handle solute data

- timestamp: 2026-05-05T00:00:04Z
  checked: IonGROMACSExporter in export.py
  found:
    - Lines 302-334: Already handles guest molecules (copies guest .itp files)
    - No handling for solute molecules
  implication: Exporter needs to be extended to handle solutes

## Resolution

root_cause: When inserting ions into a SoluteStructure, the code extracted only the interface_structure (which contains ice + water but NO solutes). The resulting IonStructure lacked solute information, so when exporting, only ice + water + ions + guests were exported, missing the THF solutes.

fix: 
1. ✅ Added solute attributes to IonStructure (solute_type, solute_positions, solute_atom_names, solute_n_molecules, solute_molecule_indices, solute_registry)
2. ✅ Modified ion_inserter.replace_water_with_ions() to preserve solute information from input structure (all return paths)
3. ✅ Modified main_window._on_insert_ions() to add solute info to interface structure when source is "Solute"
4. ✅ Modified write_ion_gro_file() to handle solute molecules (added to ordered_mols, write solute atoms)
5. ✅ Modified write_ion_top_file() to handle solute molecules (include solute .itp, add to [molecules])
6. ✅ Modified IonGROMACSExporter to copy solute .itp files

verification: ✅ Test script verified that:
- Solute information is preserved in IonStructure
- Export functions work correctly
- GRO file contains THF solutes
- TOP file includes THF solutes
- All assertions passed

files_changed: 
- quickice/structure_generation/types.py (added solute attributes to IonStructure)
- quickice/structure_generation/ion_inserter.py (preserve solute info in all return paths)
- quickice/gui/main_window.py (add solute info to interface when source is Solute)
- quickice/output/gromacs_writer.py (handle solutes in write_ion_gro_file and write_ion_top_file)
- quickice/gui/export.py (copy solute .itp files)
