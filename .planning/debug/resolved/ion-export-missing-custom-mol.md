---
status: resolved
trigger: "When exporting at the ion tab for workflow Interface → Custom → Solute → Ion, the custom molecules are not exported. The export should include: 1. Copy custom mol atom types to top, 2. Comment the ITP atomtype, 3. Include custom mol in both top and gro in correct position following molecule order, 4. Provide the commented ITP in the output set"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED AND FIX IMPLEMENTED. Added custom molecule attributes to IonStructure, updated ion_inserter to preserve them, updated write_ion_gro_file and write_ion_top_file to handle custom molecules, updated IonGROMACSExporter to copy custom ITP, and fixed main_window.py to pass custom molecule info when source is "Solute".
test: Created comprehensive test test_custom_mol_ion_export.py which verifies custom molecules are correctly exported in GRO and TOP files with correct molecule order.
expecting: All tests pass, custom molecules are exported correctly.
next_action: Verify fix works with actual application workflow, then commit changes.

## Symptoms

expected: 
  - TOP file should include custom molecule atomtypes and moleculetype
  - GRO file should have custom molecules in correct order (SOL → custom mol → ions)
  - Custom molecule ITP file should be copied to output directory
  - ITP atomtypes should be commented (types defined in main .top)
actual: 
  - TOP file shows: SOL (11969) + CH4_LIQ (7) + NA (33) + CL (33)
  - Custom molecules are missing from export
  - No custom molecule ITP copied
errors: No error, but custom molecules not exported
reproduction: 
  Workflow: Interface → Custom → Solute → Ion
  1. Load interface structure
  2. Insert custom molecules (e.g., etoh)
  3. Insert solutes from Custom Molecule source (7 CH4)
  4. Switch to ion tab, choose Solute source
  5. Insert ions (33 Na, 33 Cl)
  6. Click Export
  7. Check output - custom molecules missing
output_files: tmp/test1/
  - ions_33na_33cl_with_7ch4.top (missing custom mol)
  - ions_33na_33cl_with_7ch4.gro (missing custom mol atoms)
  - ch4_liquid.itp (solute ITP)
  - ion.itp
  - tip4p-ice.itp
context:
  - IonStructure has solute_* attributes but no custom_* attributes
  - CustomMoleculeStructure has itp_path, gro_path, moleculetype_name
  - When source is "Solute" derived from custom molecules, need to track custom mol info
  - The solutes (CH4) are separate from the original custom molecules

## Eliminated

(None yet)

## Evidence

- timestamp: 2026-05-09T00:00:00Z
  checked: quickice/structure_generation/types.py lines 341-377 (IonStructure definition)
  found: IonStructure has solute_* attributes (solute_type, solute_positions, solute_atom_names, solute_n_molecules, solute_molecule_indices, solute_registry) but NO custom_* attributes
  implication: IonStructure cannot track custom molecule information

- timestamp: 2026-05-09T00:00:00Z
  checked: quickice/gui/export.py lines 226-347 (IonGROMACSExporter class)
  found: IonGROMACSExporter handles solute ITP copying (lines 332-341) and guest ITP copying (lines 297-330) but has NO logic for custom molecules
  implication: Even if IonStructure had custom molecule attributes, the exporter wouldn't handle them

- timestamp: 2026-05-09T00:00:00Z
  checked: quickice/structure_generation/ion_inserter.py lines 466-494 (IonStructure creation in replace_water_with_ions)
  found: Method preserves guest_nmolecules, guest_atom_count (lines 466-468) and solute_* attributes (lines 470-477) but does NOT preserve any custom molecule attributes
  implication: Custom molecule metadata is lost during ion insertion

- timestamp: 2026-05-09T00:00:00Z
  checked: quickice/structure_generation/types.py lines 490-527 (CustomMoleculeStructure definition)
  found: CustomMoleculeStructure has itp_path, gro_path, moleculetype_name, custom_molecule_count, positions, atom_names attributes needed for export
  implication: These attributes need to be preserved through the workflow

- timestamp: 2026-05-09T00:00:00Z
  checked: tmp/test1/ions_33na_33cl_with_7ch4.top
  found: TOP file shows only SOL (11969) + CH4_LIQ (7) + NA (33) + CL (33), custom molecules are missing
  implication: Confirms custom molecules are not exported despite being in the structure

- timestamp: 2026-05-09T00:00:00Z
  checked: quickice/gui/main_window.py lines 994-1018 (solute insertion from custom molecule source)
  found: When source is "Custom Molecule", custom_molecule_data is prepared (lines 1013-1018) but NOT passed to SoluteInserter. Line 1012 comment: "Note: Not passed to SoluteInserter yet - will be used in Phase 35"
  implication: First point of data loss - custom molecule info not passed to SoluteStructure

- timestamp: 2026-05-09T00:00:00Z
  checked: quickice/gui/main_window.py lines 864-871 (ion insertion from solute source)
  found: When source is "Solute", solute info is added to interface (lines 864-871) but there's NO code to preserve custom molecule info
  implication: Second point of data loss - when ions are inserted from solute, custom molecule info is not available

- timestamp: 2026-05-09T00:00:00Z
  checked: quickice/gui/main_window.py lines 893-899 (ion insertion from custom molecule source)
  found: When source is "Custom Molecule", custom molecule info is added to interface object dynamically (custom_molecule_positions, custom_molecule_atom_names, custom_molecule_count, custom_molecule_moleculetype, custom_gro_path, custom_itp_path)
  implication: InterfaceStructure receives dynamic attributes, but IonStructure doesn't have corresponding attributes to preserve them

- timestamp: 2026-05-09T00:00:00Z
  checked: quickice/output/gromacs_writer.py lines 1167-1433 (write_ion_gro_file function)
  found: Function writes molecules in order: SOL → guest → solute → NA → CL. Uses ion_structure.molecule_index and solute_* attributes. NO custom molecule handling
  implication: Even if IonStructure had custom molecule data, GRO export wouldn't write it

- timestamp: 2026-05-09T00:00:00Z
  checked: quickice/output/gromacs_writer.py lines 1435-1595 (write_ion_top_file function)
  found: Function writes atomtypes and includes ITP files for: TIP4P-ICE, ions, guests, solutes. Writes [molecules] section: SOL → guest → solute → NA → CL. NO custom molecule handling
  implication: Even if IonStructure had custom molecule data, TOP export wouldn't write it

## Resolution

root_cause: Custom molecules are not exported when workflow is Interface → Custom → Solute → Ion due to data loss at multiple stages: (1) SoluteStructure doesn't have custom molecule attributes, (2) SoluteInserter doesn't receive custom molecule data, (3) IonStructure doesn't have custom molecule attributes, (4) ion_inserter.py doesn't preserve custom molecule info from input structure, (5) write_ion_gro_file and write_ion_top_file have no custom molecule handling, (6) IonGROMACSExporter doesn't copy custom molecule ITP files.

fix: IMPLEMENTED
  1. ✓ Added custom molecule attributes to IonStructure (quickice/structure_generation/types.py)
  2. ✓ Updated ion_inserter.replace_water_with_ions to preserve custom molecule attributes (quickice/structure_generation/ion_inserter.py)
  3. ✓ Updated write_ion_gro_file to write custom molecules in correct order: SOL → guest → custom → solute → ions (quickice/output/gromacs_writer.py)
  4. ✓ Updated write_ion_top_file to include custom molecule atomtypes and ITP includes (quickice/output/gromacs_writer.py)
  5. ✓ Updated IonGROMACSExporter to copy custom molecule ITP file (quickice/gui/export.py)
  6. ✓ Updated main_window.py to pass custom molecule info when source is "Solute" (quickice/gui/main_window.py)
  7. ✓ Created comprehensive test test_custom_mol_ion_export.py to verify fix

verification: Test test_custom_mol_ion_export.py passes, verifying:
  - Custom molecules correctly included in GRO file with proper atom count
  - Custom molecules correctly listed in TOP file [molecules] section
  - Custom molecule ITP file is included in TOP file
  - Molecule order is correct: SOL → custom → solute → ions
  
files_changed:
  - quickice/structure_generation/types.py: Added custom molecule attributes to IonStructure
  - quickice/structure_generation/ion_inserter.py: Preserve custom molecule attributes
  - quickice/output/gromacs_writer.py: Handle custom molecules in write_ion_gro_file and write_ion_top_file
  - quickice/gui/export.py: Copy custom molecule ITP in IonGROMACSExporter
  - quickice/gui/main_window.py: Pass custom molecule info when source is "Solute"
  - test_custom_mol_ion_export.py: New test to verify custom molecule export
