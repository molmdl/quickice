---
status: resolved
trigger: "Investigate GROMACS export issues with molecules crossing periodic boundary conditions."
created: 2026-05-01T00:00:00Z
updated: 2026-05-01T00:02:00Z
---

## Current Focus

hypothesis: CONFIRMED - wrap_positions_into_box() wraps each atom independently, splitting molecules across PBC boundaries
test: Checked both ion and slab GRO files for evidence of split molecules
expecting: Found molecules with atoms on opposite sides of box
next_action: Implement molecule-aware wrapping function that keeps atoms in same molecule together

## Symptoms

expected: 
1. Ion interface export should produce valid GRO files with molecules intact (no splitting across PBC)
2. Slab interface export should produce valid GRO files with molecules intact

actual:
1. Ion interface GRO file has atoms wrapped individually, causing molecules to be split across PBC boundaries (e.g., OW at 7.456 nm, HW1 at 7.452 nm, HW2 at 7.376 nm - same molecule but HW2 wrapped to opposite side)
2. Slab interface GRO file has same issue - molecules split across PBC cause grompp "excluded atom too far away" error

errors: grompp reports "excluded atom too far away" for slab interface

reproduction: 
- Check molecule 6SOL in tmp/ch4/ion/ions_50na_50cl.gro: OW at X=7.456, HW1 at X=7.452, HW2 at X=7.376 (wrapped)
- This is the same water molecule but atoms are on opposite sides of the box

started: Currently broken

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-05-01T00:00:00Z
  checked: User-provided context
  found: write_interface_gro_file calls wrap_positions_into_box at line 525; write_ion_gro_file does NOT call it
  implication: At least one function wraps positions, need to verify if both have the issue

- timestamp: 2026-05-01T00:00:00Z
  checked: User-provided example from ion file
  found: Molecule 6SOL has atoms split across PBC: OW=7.456, HW1=7.452, HW2=7.376, MW=7.445
  implication: Confirms atoms are being wrapped independently, not as molecules

- timestamp: 2026-05-01T00:00:01Z
  checked: tmp/ch4/ion/ions_50na_50cl.gro line 23-26
  found: 6SOL molecule: OW(7.456), HW1(7.452), HW2(7.376), MW(7.445) - OW and HW1 wrapped beyond box (7.45086), HW2 not wrapped
  implication: Atoms in same molecule on opposite sides of PBC boundary

- timestamp: 2026-05-01T00:00:02Z
  checked: tmp/ch4/interface/interface_slab.gro line 23-26
  found: 6SOL molecule: OW(0.005), HW1(0.001), HW2(7.376), MW(0.996) - OW,HW1,MW wrapped to near 0, HW2 left at 7.376
  implication: Same molecule split across PBC - some atoms wrapped, some not, causing grompp error

- timestamp: 2026-05-01T00:00:03Z
  checked: wrap_positions_into_box function lines 15-33
  found: Uses np.mod(positions[:, dim], cell[dim, dim]) for each dimension independently
  implication: No molecule awareness - each atom wrapped individually regardless of which molecule it belongs to

## Resolution

root_cause: wrap_positions_into_box() wraps each atom coordinate independently using np.mod, without considering molecule boundaries. When a molecule spans a periodic boundary (e.g., oxygen near box edge with hydrogen on other side), the atoms get wrapped to opposite sides of the box, causing "excluded atom too far away" errors in grompp.
fix: Created new wrap_molecules_into_box() function that wraps molecules as whole units by: (1) using first atom as reference, (2) calculating shift to wrap reference into box, (3) applying same shift to all atoms in molecule. Updated write_interface_gro_file and write_ion_gro_file to use this function instead of wrap_positions_into_box.
verification: 
1. Created unit tests in tests/test_output/test_molecule_wrapping.py - all 5 tests pass
2. Ran all output tests - all 25 tests pass
3. Ran integration tests - all tests pass
4. Manual test with synthetic data shows molecules are kept together, not split
5. Relative distances within molecules are preserved
6. NOTE: grompp not available in environment. User should regenerate GRO files with fixed code and verify with grompp to confirm "excluded atom too far away" error is resolved.
files_changed: [quickice/output/gromacs_writer.py, tests/test_output/test_molecule_wrapping.py]
