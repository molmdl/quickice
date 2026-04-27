---
status: resolved

## Current Focus

hypothesis: "When _build_molecule_index_from_structure() builds molecule_index for interface, it ignores guest_nmolecules and guest_atom_count, so guest molecules are not included"
test: "Check _build_molecule_index_from_structure handles guests"
expecting: "Fix to include guest molecule entries in molecule_index"
next_action: "Completed - modified _build_molecule_index_from_structure to add guest molecules"

## Symptoms

expected: "Exported files (PDB, XYZ, etc.) should include guest molecules, water, and ions"
actual: "Exported files only contain water and ions, guest molecules are missing"
errors: "None shown"
reproduction: "
  1. Generate hydrate (uses CH4 as default guest)
  2. Generate interface from hydrate
  3. Insert ion
  4. Export structure (try different export formats)
  5. Check exported file - no guest molecules present
"
started: "Never worked"

## Eliminated

## Evidence

- timestamp: "2026-04-27T16:47:00Z"
  checked: "File structure overview"
  found: "Key files: hydrate_export.py, export.py, ion_viewer.py, ion_panel.py"
  implication: "Export functionality is split across multiple files"

- timestamp: "2026-04-27T16:50:00Z"
  checked: "InterfaceStructure vs IonStructure definitions"
  found: "InterfaceStructure has guest_nmolecules=0 and guest_atom_count=0; IonStructure lacks these fields completely"
  implication: "When ion insertion builds molecule_index from interface, it doesn't preserve guest info"

- timestamp: "2026-04-27T16:55:00Z"
  checked: "ion_inserter.py _build_molecule_index_from_structure()"
  found: "Method only builds ice and water molecule entries, ignoring guest_nmolecules and guest_atom_count"
  implication: "Root cause found - guest molecules not included in molecule_index"

## Resolution

root_cause: "_build_molecule_index_from_structure() in ion_inserter.py did not read guest_nmolecules and guest_atom_count from InterfaceStructure, so guest molecules were not added to molecule_index. When export code wrote the structure, it had no knowledge of guests."

fix: "Added guest molecule handling to _build_molecule_index_from_structure() - read guest_nmolecules and guest_atom_count attributes and add mol_type='guest' entries to molecule_index. Also updated write_ion_gro_file() and write_ion_top_file() in gromacs_writer.py to handle guest molecules."

verification: "Unit test confirmed guest entry appears in molecule_index after fix"

files_changed: ["quickice/structure_generation/ion_inserter.py", "quickice/output/gromacs_writer.py"]