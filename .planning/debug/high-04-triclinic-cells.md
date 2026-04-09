---
status: investigating
trigger: "HIGH-04 triclinic-cell-handling - Cell extraction assumes orthogonal box, but GenIce can produce triclinic cells"
created: 2026-04-09T19:30:00Z
updated: 2026-04-09T19:30:00Z
---

## Current Focus

hypothesis: The code extracts only diagonal elements from cell matrix, which is incorrect for triclinic cells. The fix should detect triclinic cells and raise a clear error message since full triclinic support requires significant changes to tiling logic.
test: Write a test that creates a triclinic cell candidate and verify it fails with a clear error message
expecting: Error raised when triclinic cell is detected, preventing silent data corruption
next_action: Implement cell orthogonality check in interface_builder.py validation

## Symptoms

expected: Code should handle both orthogonal and triclinic simulation cells correctly
actual: Cell dimensions extracted from diagonal only: [cell[0,0], cell[1,1], cell[2,2]]
errors: Wrong box dimensions for triclinic cells, leading to incorrect overlap calculations, tiling, and interface structures
reproduction: Generate ice phase that produces triclinic cell (some ice phases do this), create interface
started: Always assumed orthogonal, but GenIce can produce non-orthogonal cells

## Eliminated

(none yet)

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

## Resolution

root_cause: All mode files and interface_builder validation extract only diagonal elements from the 3x3 cell matrix, which gives incorrect dimensions for triclinic (non-orthogonal) cells. This silently corrupts tiling operations, overlap detection, and piece mode validation.
fix: (pending)
verification: (pending)
files_changed: []
