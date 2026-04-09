---
status: resolved
trigger: "MED-07 hydrogen-bond-pbc"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:00:00Z
---

## Current Focus
hypothesis: ROOT CAUSE CONFIRMED - H-bond detection lacks PBC support
test: Verify fix by checking detect_hydrogen_bonds() now uses _pbc_distance()
expecting: Function should correctly calculate distances across box boundaries
next_action: Run tests to verify fix

## Symptoms
expected: H-bonds should be detected correctly at box boundaries using PBC
actual: Uses simple distance without PBC wrapping
errors: Atoms near box boundaries might have incorrect H-bond detection
reproduction: Visualize interface structure with H-bonds, look for missing bonds at box edges
timeline: Always lacked PBC support

## Eliminated

## Evidence
- timestamp: 2026-04-09T00:00:00Z
  checked: quickice/gui/vtk_utils.py lines 139-148
  found: detect_hydrogen_bonds() uses np.linalg.norm(h_pos - o_pos) on line 147
  implication: Distance calculation is NOT PBC-aware, confirmed root cause
  
- timestamp: 2026-04-09T00:00:00Z
  checked: quickice/structure_generation/types.py Candidate class
  found: Candidate has cell attribute (3,3) array with box vectors
  implication: Box dimensions are available for PBC calculation

- timestamp: 2026-04-09T00:00:00Z
  checked: quickice/ranking/scorer.py _calculate_oo_distances_pbc function
  found: Existing PBC implementation using supercell approach with cKDTree
  implication: Similar PBC pattern already used in codebase, can adapt simpler version for H-bonds

- timestamp: 2026-04-09T00:00:00Z
  checked: Created tests/test_pbc_hbonds.py with PBC distance tests
  found: All 6 tests pass, including test_detect_hbonds_pbc_edge_case
  implication: Fix correctly detects H-bonds across PBC boundaries

## Resolution
root_cause: detect_hydrogen_bonds() uses simple Euclidean distance without applying minimum image convention for periodic boundary conditions
fix: Added _pbc_distance() helper function that implements minimum image convention. Modified detect_hydrogen_bonds() to use PBC-aware distance calculation by calling _pbc_distance() instead of np.linalg.norm(). The fix extracts box dimensions from cell diagonal (assuming orthorhombic box) and applies: delta = delta - cell_dims * np.round(delta / cell_dims)
verification: Created comprehensive test suite (tests/test_pbc_hbonds.py) with 6 tests covering PBC distance calculation and H-bond detection across boundaries. All tests pass. Key test verifies H-bond detection for atoms at positions 0.1 nm and 1.9 nm in a 2.0 nm box (PBC distance = 0.2 nm, correctly detected).
files_changed: [quickice/gui/vtk_utils.py, tests/test_pbc_hbonds.py]
