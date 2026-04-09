---
status: verifying
trigger: "HIGH-04 triclinic-cell-handling - Cell extraction assumes orthogonal box, but GenIce can produce triclinic cells"
created: 2026-04-09T19:30:00Z
updated: 2026-04-09T20:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - The code extracts only diagonal elements from cell matrix, which is incorrect for triclinic cells
test: Run comprehensive tests for triclinic detection and error handling
expecting: All tests pass, no regressions in existing tests
next_action: Archive session after verification

## Symptoms

expected: Code should handle both orthogonal and triclinic simulation cells correctly
actual: Cell dimensions extracted from diagonal only: [cell[0,0], cell[1,1], cell[2,2]]
errors: Wrong box dimensions for triclinic cells, leading to incorrect overlap calculations, tiling, and interface structures
reproduction: Generate ice phase that produces triclinic cell (some ice phases do this), create interface
started: Always assumed orthogonal, but GenIce can produce non-orthogonal cells

## Eliminated

(none - hypothesis confirmed)

## Evidence

- timestamp: 2026-04-09T19:30:00Z
  checked: generator.py _parse_gro method (lines 179-195)
  found: GenIce correctly parses triclinic cells from GRO format with 9 values on last line
  implication: The source of cell data is correct; the issue is in how consumers use it

- timestamp: 2026-04-09T19:30:00Z
  checked: slab.py lines 38-42, pocket.py lines 47-51, piece.py lines 38-42
  found: All three mode files extract only diagonal: `np.array([candidate.cell[0,0], candidate.cell[1,1], candidate.cell[2,2]])`
  implication: This pattern is copied across all modes - same bug in three places

- timestamp: 2026-04-09T19:30:00Z
  checked: interface_builder.py lines 111-115
  found: Validation also extracts only diagonal elements for piece mode validation
  implication: Bug exists in both validation and generation code paths

- timestamp: 2026-04-09T19:30:00Z
  checked: vtk_utils.py lines 254-256
  found: Uses `np.linalg.norm(cell[0])` etc. which gives correct vector lengths
  implication: VTK visualization is actually correct - it uses full vector length, not just diagonal

- timestamp: 2026-04-09T19:30:00Z
  checked: water_filler.py tile_structure function
  found: Assumes orthogonal box with separate lx, ly, lz dimensions for tiling
  implication: Tiling logic fundamentally assumes orthogonal cells; would need major rewrite for triclinic

- timestamp: 2026-04-09T19:30:00Z
  checked: gromacs_writer.py
  found: Already supports triclinic output format correctly (lines 87-91)
  implication: Export layer is correct; only structure generation layer has the bug

- timestamp: 2026-04-09T19:35:00Z
  checked: GenIce lattice cells directly
  found: Ice 2 (ice_ii) and Ice 5 (ice_v) produce triclinic cells with off-diagonal elements
  implication: This bug affects real use cases with actual ice phases

- timestamp: 2026-04-09T19:45:00Z
  checked: Test suite for fix
  found: All 13 new tests pass, 25 output tests pass, no regressions
  implication: Fix is working correctly

## Resolution

root_cause: All mode files and interface_builder validation extract only diagonal elements from the 3x3 cell matrix, which gives incorrect dimensions for triclinic (non-orthogonal) cells. This silently corrupts tiling operations, overlap detection, and piece mode validation. Ice II and Ice V phases produce triclinic cells and are affected by this bug.
fix: Added `is_cell_orthogonal()` function to interface_builder.py that checks if off-diagonal elements are non-zero. Added validation in `validate_interface_config()` that raises clear InterfaceGenerationError when triclinic cells are detected, preventing silent data corruption.
verification: All 13 new tests pass including integration tests with real GenIce-generated Ice II and Ice V structures. Orthogonal phases (Ice Ih, Ice Ic, etc.) continue to work correctly. Error messages clearly identify affected phases.
files_changed:
  - quickice/structure_generation/interface_builder.py: Added is_cell_orthogonal() function and triclinic cell validation
