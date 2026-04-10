---
status: resolved
trigger: "CRIT-01 atom-count-mismatch - Atom Count Mismatch in Interface GRO Export (gromacs_writer.py:200-268)"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:00:00Z
---

## Current Focus

hypothesis: Code is correct - problem description is based on misunderstanding of INPUT vs OUTPUT atoms
test: Verify header matches actual atoms in generated GRO file
expecting: Header atom count should equal actual atom lines written
next_action: Mark as resolved - no bug found

## Symptoms

expected: GRO file header should show correct total atom count matching actual atoms written
actual: n_atoms calculated as (ice_nmolecules + water_nmolecules) * 4, but ice molecules have 3 atoms each (O, H, H), not 4
errors: GRO file will have incorrect atom count header, causing GROMACS to fail or misread the file
reproduction: Generate interface structure with ice and water, export to GRO file, check atom count in header vs actual atoms
started: Always been wrong since interface GRO export was implemented

## Eliminated

- hypothesis: n_atoms formula should use ice_atom_count + water_atom_count
  evidence: This would give INPUT atom count (ice_nmolecules * 3 + water_nmolecules * 4), not OUTPUT atom count. The GRO file has OUTPUT atoms.
  timestamp: 2026-04-09T00:00:00Z

## Evidence

- timestamp: 2026-04-09T00:00:00Z
  checked: gromacs_writer.py lines 200-275 (write_interface_gro_file function)
  found: Line 212 calculates n_atoms = (iface.ice_nmolecules + iface.water_nmolecules) * 4
  implication: Formula calculates OUTPUT atoms (4 per molecule after normalization)

- timestamp: 2026-04-09T00:00:00Z
  checked: gromacs_writer.py lines 224-255 (ice molecule writing loop)
  found: Line 225 shows base_idx = mol_idx * 3, reads 3 INPUT atoms per ice molecule
  found: Lines 233-255 write 4 OUTPUT atoms per ice molecule (OW, HW1, HW2, MW with MW computed)
  implication: Ice molecules: 3 INPUT atoms -> 4 OUTPUT atoms

- timestamp: 2026-04-09T00:00:00Z
  checked: gromacs_writer.py lines 258-268 (water molecule writing loop)
  found: Line 259 shows base_idx = iface.ice_atom_count + mol_idx * 4
  found: Lines 262-268 write 4 OUTPUT atoms per water molecule (OW, HW1, HW2, MW)
  implication: Water molecules: 4 INPUT atoms -> 4 OUTPUT atoms

- timestamp: 2026-04-09T00:00:00Z
  checked: types.py lines 113-145 (InterfaceStructure dataclass)
  found: Has ice_atom_count and water_atom_count attributes
  found: Docstring lines 131-134 explicitly states ice has 3 atoms/mol, water has 4 atoms/mol
  implication: These represent INPUT atom counts, not OUTPUT

- timestamp: 2026-04-09T00:00:00Z
  checked: slab.py lines 132-154 (InterfaceStructure creation)
  found: ice_atom_count = len(combined_ice_positions) which equals ice_nmolecules * 3
  found: water_atom_count = len(trimmed_water_positions) which equals water_nmolecules * 4
  implication: Atom counts match the INPUT positions array

- timestamp: 2026-04-09T00:00:00Z
  checked: tmp/interface_slab.gro (generated GRO file)
  found: Header shows 31912 atoms
  found: File contains 31912 atom lines
  found: Atom count matches perfectly
  implication: Generated GRO file is CORRECT

- timestamp: 2026-04-09T00:00:00Z
  checked: Mathematical analysis
  found: Current formula: (ice_nmolecules + water_nmolecules) * 4 gives OUTPUT atoms
  found: Suggested fix: ice_atom_count + water_atom_count gives INPUT atoms
  found: OUTPUT atoms = ice_nmolecules * 4 + water_nmolecules * 4 = 600 (for 100 ice + 50 water)
  found: INPUT atoms = ice_nmolecules * 3 + water_nmolecules * 4 = 500 (for 100 ice + 50 water)
  implication: Suggested fix would introduce bug by using wrong count

## Resolution

root_cause: NO BUG FOUND - Code is correct. Problem description is based on misunderstanding.

The formula `(ice_nmolecules + water_nmolecules) * 4` correctly calculates the OUTPUT atom count for the GRO file. Each ice molecule (3 INPUT atoms: O, H, H) is normalized to 4 OUTPUT atoms (OW, HW1, HW2, MW) by adding the MW virtual site. Each water molecule (4 INPUT atoms) remains 4 OUTPUT atoms.

The problem description confuses:
- INPUT atoms (positions array): ice_nmolecules * 3 + water_nmolecules * 4
- OUTPUT atoms (GRO file): (ice_nmolecules + water_nmolecules) * 4

The suggested fix `ice_atom_count + water_atom_count` would use the INPUT atom count, which is WRONG for the GRO file header.

fix: Improved documentation/comments to clarify INPUT vs OUTPUT distinction. No code change needed.
verification: Verified generated GRO file has correct atom count matching header
files_changed: [quickice/output/gromacs_writer.py (comments only)]

## Summary

**RESULT: NO BUG FOUND**

The reported "bug" is based on a fundamental misunderstanding of how the code works. The original code is CORRECT and should NOT be changed.

**Key Points:**
1. Ice molecules have 3 atoms in INPUT positions array
2. Ice molecules are written as 4 atoms in OUTPUT GRO file (MW added)
3. Water molecules have 4 atoms in both INPUT and OUTPUT
4. GRO header must show OUTPUT atom count, not INPUT
5. Formula `(ice_nmolecules + water_nmolecules) * 4` correctly gives OUTPUT count
6. Generated GRO files have matching header and actual atom lines

**Recommendation:** Close this issue as "Not a bug" or "Works as designed"
