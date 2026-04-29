---
status: resolved
trigger: "Ion insertion export creates malformed H2 residues that shouldn't exist. Interface export of the same system has no problem. The H2 residue has wrong atom names (H, H, H, H, OW instead of proper water atoms)."
created: 2026-04-29T00:00:00
updated: 2026-04-29T00:00:00
---

## Current Focus

hypothesis: CONFIRMED - The molecule_index builder assumes ice→guest→water ordering, but .gro file has water1→guest→water2 ordering. When building molecule_index for 17206 ice molecules, it assigns ice atoms 0-68823, which includes the guest CH4 atoms (49752-58901). Then guest atoms are assigned to water molecules, detecting them as "H2" because HW1/HW2 atoms look like H2 molecules.
test: Fix _build_molecule_index_from_structure to find guests by their actual position in atom_names, not by assuming they come after ice
expecting: molecule_index should correctly identify guest molecules at their actual positions (atoms 49752-58901)
next_action: Implement fix in ion_inserter.py _build_molecule_index_from_structure method

## Symptoms

expected: Ion insertion export should produce valid GROMACS files with only SOL (water), CH4 (guest), NA, and CL residues
actual: The gro file contains a residue named "H2" (residue 19036) with 5 atoms: H, H, H, H, OW. This causes atom name mismatches with the topology file.
errors: 
  - grompp error: "atom name 77970 in ions_43na_43cl.top and ions_43na_43cl.gro does not match (C - H)"
  - "atom name 77974 in ions_43na_43cl.top and ions_43na_43cl.gro does not match (H - OW)"
  - "Fatal error: Too many warnings (1)"
reproduction: 
  - Run hydrate → interface → ion workflow
  - Export ion insertion output
  - Run gmx grompp on the output
started: Issue discovered in tmp/ion_2x2x2 output files

## Eliminated

(No hypotheses eliminated yet)

## Evidence

### Atom ordering in interface file:
```
Atoms 1-49752: SOL (12438 molecules)
Atoms 49753-58902: CH4 (1830 molecules, 9150 atoms)
Atoms 58903-78326: SOL (4856 molecules)
```

### The BUG - Wrong atom ordering:
**Expected order:** ice_SOL → guest_CH4 → water_SOL
**Actual order:** water_SOL → guest_CH4 → water_SOL

### Root cause analysis:
1. Interface generation places CH4 molecules in the MIDDLE of water molecules
2. Ion insertion's `_build_molecule_index_from_structure` assumes: ice → guest → water ordering
3. The calculation:
   - Expects CH4 at positions: ice_atom_count to ice_atom_count + guest_atom_count
   - But actual CH4 are at: 49752 to 58902 (in middle of water!)
4. When molecule_index is built:
   - Ice: assigned atoms 0 to ice_nmolecules * 4
   - Guest: assigned atoms ice_end to ice_end + 9150
   - If ice_nmolecules = 17206, ice_end = 68824
   - Expected guest region: 68824-77974
   - **This region contains WATER molecules, not CH4!**
5. When export detects guest type from atoms:
   - Reads atoms at position 68824+ (which are water molecules)
   - Water atoms (OW, HW1, HW2, MW) get detected as "h2" type
   - Result: H2 residue with wrong atom names

### Key finding:
The interface generation code in slab.py places CH4 molecules at the WRONG position in the combined positions array. CH4 should come after ALL SOL (ice + water) molecules, not in the middle.

## Resolution

root_cause: _build_molecule_index_from_structure calculated ice region size as ice_nmolecules * atoms_per_mol, which was incorrect when ice_nmolecules referred to total SOL count rather than just hydrate framework count. The correct approach is to use ice_atom_count, guest_atom_count, and water_atom_count attributes from InterfaceStructure which mark the exact boundaries in the positions array.
fix: Modified _build_molecule_index_from_structure in ion_inserter.py to use ice_atom_count, guest_atom_count, water_atom_count instead of calculating from nmolecules
verification: Tested with simulated InterfaceStructure - guest molecules now correctly identified at position 49752 with 5 atoms each (C, H, H, H, H)
files_changed: [quickice/structure_generation/ion_inserter.py]
