---
status: resolved
trigger: "Hydrate tab has incomplete molecules at boundaries - ice and interface tabs handle this correctly"
created: 2026-04-17T00:00:00Z
updated: 2026-04-17T00:00:00Z
---

## Current Focus
hypothesis: "HydrateRenderer doesn't set lattice on vtkMolecule, unlike ice which uses candidate_to_vtk_molecule with SetLattice()"
test: "Compare hydrate_renderer.py with molecular_viewer.py and interface_viewer.py"
expecting: "Find that ice sets lattice, interface applies PBC wrapping, hydrate does neither"
next_action: "Verified fix works - committing"

## Symptoms
expected: "Molecules should be complete at unit cell boundaries"
actual: "Hydrate tab shows incomplete molecules at boundaries"
errors: "None visible, but visual evidence of molecules split across edges"
reproduction: "Open hydrate tab with any structure, observe edges"
started: "Unknown - likely always present"

## Eliminated

## Evidence
- timestamp: 2026-04-17T00:00:00Z
  checked: "ice tab - molecular_viewer.py and candidate_to_vtk_molecule in vtk_utils.py"
  found: "candidate_to_vtk_molecule() sets mol.SetLattice(lattice_matrix) on line 122"
  implication: "VTK knows about periodic boundaries and handles molecule completeness"

- timestamp: 2026-04-17T00:00:00Z
  checked: "interface tab - interface_viewer.py and _extract_bonds method"
  found: "interface_viewer._extract_bonds() applies minimum image convention (lines 185-190)"
  implication: "Bonds are explicitly wrapped to show shortest connection"

- timestamp: 2026-04-17T00:00:00Z
  checked: "hydrate tab - hydrate_renderer.py"
  found: "No SetLattice() call found, no PBC wrapping in bond creation"
  implication: "Hydrate molecules were incomplete because VTK didn't know about PBC"

## Resolution
root_cause: "HydrateRenderer creates vtkMolecule objects without setting the lattice, so VTK didn't know about periodic boundary conditions"
fix: "Added _set_molecule_lattice() function and calls in create_water_framework_actor() and create_guest_actor() to match ice tab pattern"
verification: "306 tests pass. The 1 failing test (test_ice_ih_still_works) was already failing before this change - it's a pre-existing issue unrelated to hydrate rendering."
files_changed: ["quickice/gui/hydrate_renderer.py"]
