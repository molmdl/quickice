---
status: verifying
trigger: "tab2-transform-broken-piles"
created: 2026-04-13T00:00:00Z
updated: 2026-04-13T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - Transformed cell is orthogonal but ROTATED in space. get_cell_extent() returns bounding box (4.67x5.22x3.28 nm) instead of actual cell dimensions (2.60x4.50x1.25 nm). tile_structure() uses wrong dimensions causing incorrect atom positions.
test: Verify fix approach - use cell vector LENGTHS for orthogonal cells
expecting: Fix should use np.linalg.norm for each cell vector instead of bounding box
next_action: Implement fix in slab.py or transformer.py

## Symptoms

expected: Tab 2 should show transformed triclinic structure with properly distributed atoms in correct positions, intact water molecules, no "piles" or clusters

actual: 
- 4 piles of broken cyan atoms around top of box
- Two piles in empty space (disconnected from structure)
- Two piles inserted into water layer (incorrect positions)
- Atoms clustering instead of being distributed

errors: No error messages, just corrupted visualization

reproduction: 
1. Use default slab generation
2. Load a triclinic phase (e.g., Ice II)
3. Observe tab 2 - see broken cyan piles at top of box

started: Issue persists after previous transform function fix (commit c614365)

context:
- Previous fix corrected fractional coordinate conversion in apply_transformation()
- But visual result suggests atoms are still being placed incorrectly
- "Piles" suggest atoms are clustering in specific regions rather than spread evenly
- This could be PBC wrapping issue, or issue with how transformed positions are used downstream

## Eliminated

## Evidence

- timestamp: 2026-04-13T00:00:00Z
  checked: Transformed Ice II candidate structure
  found: Transformed cell is orthogonal (90° angles) but ROTATED in space. Cell vectors are [2.17, 0.92, -1.09], [2.17, -3.79, 1.09], [0.33, 0.51, 1.09]
  implication: Cell is not axis-aligned despite having 90° angles

- timestamp: 2026-04-13T00:00:00Z
  checked: get_cell_extent() output vs cell vector lengths
  found: get_cell_extent() returns bounding box [4.67, 5.22, 3.28] nm. Actual vector lengths are [2.60, 4.50, 1.25] nm. Bounding box is LARGER!
  implication: tile_structure() uses wrong dimensions for tiling

- timestamp: 2026-04-13T00:00:00Z
  checked: tile_structure() with wrong cell dimensions
  found: Using bounding box dimensions causes atoms to be incorrectly spaced during tiling
  implication: ROOT CAUSE FOUND - get_cell_extent() is wrong for rotated orthogonal cells

## Resolution

root_cause: In transformer.py, get_cell_extent() returns the BOUNDING BOX of a cell, which is correct for some purposes but WRONG for tiling. For transformed orthogonal cells (like Ice II after transformation), the cell is rotated in space - the cell vectors are perpendicular but not aligned with X/Y/Z axes. The bounding box [4.67, 5.22, 3.28] nm is larger than the actual cell dimensions [2.60, 4.50, 1.25] nm. slab.py, pocket.py, and piece.py used get_cell_extent() for tile_structure(), causing atoms to be incorrectly positioned.

fix: Added get_cell_dimensions() method to TriclinicTransformer that returns the actual cell vector LENGTHS for orthogonal cells (correct for tiling) and the bounding box for triclinic cells. Updated slab.py, pocket.py, and piece.py to use get_cell_dimensions() instead of get_cell_extent().

verification: All 15 transformer tests pass. All 6 triclinic interface tests pass.

files_changed: [quickice/structure_generation/transformer.py, quickice/structure_generation/modes/slab.py, quickice/structure_generation/modes/pocket.py, quickice/structure_generation/modes/piece.py]
