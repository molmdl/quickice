---
status: resolved
trigger: "Fix two hydrate issues: 1) Too many bonds in 3D viewer 2) XX in exported GRO atom names"
created: 2026-04-16T00:00:00Z
updated: 2026-04-16T00:00:00Z
---

## Current Focus

hypothesis: Issue 1: hydrate_renderer.py concatenates all atoms from all molecules into one vtkMolecule, then uses BOND_DISTANCE_THRESHOLD on ALL atom pairs - creates cross-molecule bonds. Issue 2: hydrate_generator.py parses wrong columns (12:17 vs 10:15) AND gromacs_writer.py uses hardcoded "XX" for atom names.
test: 
expecting: 
next_action: Fix hydrate_renderer.py to process each molecule separately using molecule_index. Fix hydrate_generator.py to use correct GRO column indices. Fix gromacs_writer.py to use atom_names from structure.

## Symptoms

expected: 
- Issue 1: 3D viewer shows correct bonds (explicit topology, no cross-molecule bonds)
- Issue 2: Exported GRO has proper atom names (not "XX")

actual:
- Issue 1: Distance-based bond detection creates spurious bonds between molecules
- Issue 2: Exported GRO file tmp/hydrate_sI_ch4_1x1x1.gro shows "XX" for all atoms

errors:
- None specific, visual issue in 3D viewer and text issue in exported GRO

reproduction:
- Issue 1: Generate hydrate structure and view in 3D viewer
- Issue 2: Export hydrate to GRO format

started: Unknown, appears to be a regression

## Eliminated

## Evidence

- timestamp: 2026-04-16T00:00:00Z
  checked: hydrate_renderer.py _build_vtk_molecule function
  found: Builds ONE vtkMolecule from ALL water atoms concatenated together, then applies BOND_DISTANCE_THRESHOLD (0.30nm) to ALL pairs - this creates bonds between different molecules
  implication: Need to build separate molecule per molecule in molecule_index

- timestamp: 2026-04-16T00:00:00Z
  checked: hydrate_generator.py line 239
  found: Uses line[12:17] for atom names, but gro_parser.py uses line[10:15] (correct per GRO spec)
  implication: Wrong column parsing causes "XX" at parse time

- timestamp: 2026-04-16T00:00:00Z
  checked: gromacs_writer.py line 448-449
  found: Uses hardcoded "XX" for atom names - does not use actual atom_names from structure
  implication: Even if parsing was correct, writer uses placeholder

- timestamp: 2026-04-16T00:00:00Z
  checked: Tab 1 molecular_viewer.py via vtk_utils.py
  found: Uses explicit O-H bonds based on molecule count and expected atom ordering (TIP3P/TIP4P pattern)
  implication: Tab 1 doesn't rely on distance-based bonding

## Resolution

root_cause: Issue 1: hydrate_renderer.py builds single vtkMolecule from concatenated atoms, applying distance threshold across molecules. Issue 2: hydrate_generator.py uses wrong GRO column (12:17 vs 10:15) AND gromacs_writer.py uses hardcoded "XX"

fix: 
- Issue 1: Created new _build_vtk_molecule_from_molecule_index() that iterates through molecule_index and only bonds atoms within each molecule (not across molecules). Updated create_water_framework_actor() and create_guest_actor() to use this.
- Issue 2: Fixed hydrate_generator.py to use line[10:15] for atom names (correct GRO columns). Updated gromacs_writer.py to accept optional atom_names parameter and use actual names. Updated hydrate_export.py to pass structure.atom_names.

verification: All 306 relevant tests pass. One pre-existing test failure (unrelated to hydrate issues - water_density.py returns None for rho at 273K/0MPa).

files_changed: [quickice/gui/hydrate_renderer.py, quickice/structure_generation/hydrate_generator.py, quickice/output/gromacs_writer.py, quickice/gui/hydrate_export.py]