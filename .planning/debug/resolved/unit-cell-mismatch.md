---
status: resolved
trigger: "unit-cell-mismatch"
created: "2026-04-02T00:00:00.000Z"
updated: "2026-04-02T00:00:00.000Z"
---

## Current Focus
hypothesis: The SetLattice call in candidate_to_vtk_molecule has incorrect matrix orientation - it passes row-major but VTK expects vectors as columns. This causes the VTK molecule's internal unit cell to be wrong, while the separate unit cell wireframe (create_unit_cell_actor) uses raw cell data correctly. Result: two different unit cell visualizations.
test: Verify that VTK's SetLattice expects lattice vectors as columns, check if transpose is needed
expecting: Find that cell matrix needs to be transposed for VTK
next_action: Check VTK documentation for SetLattice expected format

## Symptoms
expected: Gridbox unit cell should match init cell, or clarity on which is correct
actual: Two different unit cells displayed - one in gridbox after generation, another after clicking init cell
errors: None reported
reproduction: 1) Generate a structure 2) Observe unit cell in gridbox 3) Click init cell button 4) Observe different unit cell appears
started: Reported on Debian 12 testing of 3D viewer

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: "2026-04-02"
  checked: "vtk_utils.py candidate_to_vtk_molecule function"
  found: "SetLattice uses candidate.cell directly without transpose. Comment says 'vectors as columns' but implementation is row-major."
  implication: "VTK expects lattice vectors as columns, but we're passing rows. Need to transpose."

- timestamp: "2026-04-02"
  checked: "generator.py _parse_gro method"
  found: "Cell is stored with each ROW being a lattice vector: [[a_x,a_y,a_z],[b_x,b_y,b_z],[c_x,c_y,c_z]]"
  implication: "To convert to VTK's column format, need to transpose the matrix"

- timestamp: "2026-04-02"
  checked: "vtk_utils.py create_unit_cell_actor function"
  found: "Uses np.linalg.norm(cell[i]) to get lengths - works for both orthogonal and non-orthogonal since it gets vector magnitudes"
  implication: "Wireframe box correctly uses raw cell vectors, but SetLattice may be wrong"

## Resolution
root_cause: "In candidate_to_vtk_molecule(), SetLattice was called with row-major matrix but VTK expects lattice vectors as columns. For orthogonal cells (ice Ih), this doesn't matter (transpose = self). For non-orthogonal cells (ice II, V), this causes VTK's internal unit cell to be wrong, while the separate wireframe box (create_unit_cell_actor) uses raw cell data correctly - resulting in two different unit cell visualizations."
fix: "Transpose the cell matrix before setting elements in vtkMatrix3x3. Change: candidate.cell[i,j] → candidate.cell.T[i,j] = candidate.cell[j,i]"
verification: "Tested with non-orthogonal cells (ice II, ice V) - now VTK lattice matches expected column-based layout. Orthogonal cells (ice Ih) unchanged (transpose of diagonal = self)."
files_changed: ["quickice/gui/vtk_utils.py"]