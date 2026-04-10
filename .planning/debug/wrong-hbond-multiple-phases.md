---
status: resolved
trigger: "Hydrogen bond display in tab 1 shows incorrect h-bonds for non-Ih ice phases - bonds between wrong atoms, even showing H-H bonds within a single water molecule"
created: 2026-04-10T16:02:00
updated: 2026-04-10T16:12:00
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

hypothesis: Fix implemented - _pbc_distance() now uses fractional coordinates for triclinic support
test: Run verification tests with triclinic cells
expecting: All tests pass, H-bond detection works for all ice phases
next_action: Create comprehensive verification test and update Resolution section

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: H-bond count and visualization should correctly show hydrogen bonds between oxygen atoms (donor-acceptor pairs)
actual: H-bonds shown between wrong atoms, including H-H bonds within a single water molecule (which is not a real h-bond)
errors: No error message - incorrect visualization
reproduction: Load any non-Ih ice structure in tab 1 and toggle h-bond display - always wrong
started: Works correctly for Ih (ice Ih), but wrong for all other ice phases

## Eliminated
<!-- APPEND only - prevents re-investigating -->

(empty)

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-10T16:04:00
  checked: vtk_utils.py detect_hydrogen_bonds() function (lines151-239)
  found: Function extracts cell dimensions using `cell_dims = np.diag(candidate.cell)` at line 200
  implication: This assumes orthorhombic (diagonal) cell matrix - correct for Ih but WRONG for triclinic cells (II, V, etc)

- timestamp: 2026-04-10T16:04:30
  checked: interface_builder.py and help_dialog.py for triclinic cell information
  found: Lines 120-128 in interface_builder.py explicitly check for triclinic cells and reject them for interface generation. Help text mentions "ice_ii, ice_v are triclinic"
  implication: Non-Ih phases (II, V) are KNOWN to have triclinic cells, but detect_hydrogen_bonds() doesn't handle them correctly

- timestamp: 2026-04-10T16:05:00
  checked: _pbc_distance() function (lines 127-148)
  found: Function documentation at line 142 states "Assumes orthorhombic box (typical for ice structures)"
  implication: The PBC distance calculation is designed ONLY for orthogonal cells - this is the root cause

- timestamp: 2026-04-10T16:07:00
  checked: validator.py lines 53-56
  found: Shows how to convert Cartesian to fractional coordinates using cell matrix inverse: `positions = positions_cartesian @ inv(lattice)`
  implication: Found the correct algorithm for handling triclinic cells - use fractional coordinates

- timestamp: 2026-04-10T16:08:00
  checked: molecular_viewer.py _extract_bonds() method (lines 220-265)
  found: Also uses `np.diag(cell)` with assumption "orthorhombic" - same bug as detect_hydrogen_bonds()
  implication: Both PBC distance calculations need fixing

- timestamp: 2026-04-10T16:09:00
  checked: Fix implementation in vtk_utils.py and molecular_viewer.py
  found: Updated _pbc_distance() to use fractional coordinates: delta_frac = delta_cart @ inv(cell), wrap, then delta_cart = delta_frac @ cell
  implication: Fix should work for both orthorhombic (Ih) and triclinic (II, V) cells

- timestamp: 2026-04-10T16:10:00
  checked: Manual verification test with triclinic cell
  found: Triclinic distance calculation matches manual calculation; orthorhombic still works correctly
  implication: Fix is working correctly for both cell types

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: _pbc_distance() function assumed orthorhombic cells and used np.diag(cell) to extract box dimensions. For triclinic cells (ice II, V, etc.), this gives incorrect dimensions because off-diagonal elements are non-zero. This caused H-bond detection to calculate wrong distances, leading to incorrect H-bond visualization showing bonds between wrong atoms including impossible H-H bonds within molecules.

fix: Updated _pbc_distance() to use fractional coordinates algorithm: convert displacement to fractional coords using inv(cell), apply minimum image convention in fractional space, convert back to Cartesian. This works for both orthorhombic and triclinic cells. Also fixed _extract_bonds() in molecular_viewer.py with same approach.

verification: All PBC h-bond tests pass (13/13). Manual test with triclinic cell shows correct distance calculation. Test with both orthorhombic and triclinic candidates shows H-bond detection works correctly for both cell types.

files_changed: ['quickice/gui/vtk_utils.py', 'quickice/gui/molecular_viewer.py', 'tests/test_pbc_hbonds.py']
