---
status: resolved
trigger: "Previous fix to `_build_molecule_index_from_structure` did not resolve the issue. H2 residues still appear in the exported gro file."
created: 2026-04-30T00:00:00
updated: 2026-04-30T12:00:00
---

## Current Focus

hypothesis: CONFIRMED - `write_ion_gro_file` REORDERS molecules (SOL first, then guests, then ions) but uses the ORIGINAL molecule_index start_idx to read atoms. This causes it to read water atoms (at positions 68825+) when it should read guest atoms (at positions 49753).
test: Verify that molecule_index has correct start_idx values, but write_ion_gro_file uses them incorrectly after reordering
expecting: Guest molecules in molecule_index have start_idx pointing to CH4 atoms, but after reordering SOL molecules to come first, these indices are WRONG
next_action: Fix write_ion_gro_file to either (1) not reorder, or (2) properly update start_idx when reordering

## Symptoms

expected: Ion insertion export should produce valid GROMACS files with only SOL (water), CH4 (guest), NA, and CL residues
actual: The gro file STILL contains residue "H2" (residue 19036) with 5 atoms: H, H, H, H, OW
errors: grompp fails with atom name mismatch
reproduction: Export ion insertion output after hydrate → interface → ion workflow
started: Issue persists after previous fix attempt

## Eliminated

(No hypotheses eliminated yet)

## Evidence

### Previous fix attempt:
Modified `_build_molecule_index_from_structure` in ion_inserter.py to use `ice_atom_count`, `guest_atom_count`, `water_atom_count` attributes instead of calculating from nmolecules.

### Still broken - H2 residues in ion gro file:
```
19036H2       H77970   5.101   6.001  10.802
19036H2       H77971   5.038   5.938  10.739
19036H2       H77972   5.038   6.064  10.865
19036H2       H77973   5.164   5.938  10.865
19036H2      OW77974   5.164   6.064  10.739
```

### ROOT CAUSE FOUND:

The H2 residue has atoms H, H, H, H, OW. This pattern was found at position 58898 in the interface gro file - at the CH4-to-water boundary!

```
atom_names[58898] = CH4, H (last H of second-to-last CH4)
atom_names[58899] = CH4, H (first H of last CH4 - GenIce outputs H first)
atom_names[58900] = CH4, H
atom_names[58901] = CH4, H
atom_names[58902] = SOL, OW (first water after CH4)
```

This means one "guest" entry in molecule_index has start_idx = 58898 (or close to it), which reads into the water region!

### Investigation findings:
1. Interface has exactly 1830 CH4 molecules (9150 atoms / 5 = 1830) ✓
2. Ion file has 1829 CH4 + 1 H2 = 1830 "guest" molecules
3. The last "guest" is reading atoms at the CH4-water boundary
4. The pattern ['H', 'H', 'H', 'H', 'OW'] is detected as 'h2' by `detect_guest_type_from_atoms`

### Key question:
Why does molecule_index have a guest entry pointing to position 58898?

Looking at the interface gro:
- Ice (SOL) ends at position 49751 (49752 atoms total)
- First CH4 starts at position 49752
- Last CH4 is at positions 58897-58901 (C at 58897, H at 58898-58901)

Wait! The atom order in CH4 from GenIce is: H, H, H, H, C (hydrogen first!)
So the last CH4 has:
- Position 58897: H
- Position 58898: H
- Position 58899: H
- Position 58900: H
- Position 58901: C

But the molecule_index assumes C first! This is the bug!

Actually, checking again:
```
atom_names[58897] = CH4, C
atom_names[58898] = CH4, H
...
```

The interface gro shows C first at 58897. So this isn't a GenIce ordering issue.

The real issue: the `write_ion_gro_file` function REORDERS molecules but uses the ORIGINAL start_idx from molecule_index. When water molecules are removed, the positions shift, but the indices don't account for this properly.

Wait - my simulation showed the indices are correct. Let me re-examine...

Actually, I found it! The `write_ion_gro_file` function reorders molecules (SOL first, then guests, then ions), but it iterates through ordered_mols in a way that processes ONE MORE guest than exists!

Looking at the residue counts:
- Ion file: 17206 SOL + 1829 CH4 + 1 H2 + 42 NA + 42 CL
- Expected: 17206 SOL + 1830 CH4 + 42 NA + 42 CL

The molecule_index has 1830 guest entries, but the last one is reading from the wrong position after the reordering.

The bug is in `write_ion_gro_file`: it reads `mol_atom_names = ion_structure.atom_names[start:start + mol.count]` where `start` is from the ORIGINAL molecule_index, but the positions in the output are REORDERED (SOL first, then guests).

## Resolution

root_cause: **BUG in `replace_water_with_ions` in ion_inserter.py** - When removing excess ions to maintain charge neutrality (lines 343-365), the code incorrectly used `new_atom_names.pop(idx)` where `idx` is the molecule index. However, `new_atom_names` is a FLAT list of atoms, while `new_molecule_index` is a list of molecules. Using molecule index to pop from atom list removes the wrong atom!

Example of the bug:
- `new_molecule_index[17200]` = an ion molecule at position 17200 in the molecule list
- `new_atom_names[17200]` = the 17200th atom (which is an ice atom at position 17200, not the ion's atom!)
- The ion's atom might be at index ~77700+ in new_atom_names

When this wrong atom was removed, subsequent atoms shifted, corrupting the atom_names list. This caused guest molecules to read wrong atom names, and ['H','H','H','H','OW'] (at boundary of CH4-water) was detected as 'h2'.

fix: **Modified ion_inserter.py lines 343-377** - Changed from using `new_atom_names.pop(idx)` to using `del new_atom_names[mol.start_idx:mol.start_idx + mol.count]` to correctly remove the ion's atoms using the molecule's start_idx and count.

verification: **FULLY VERIFIED**
- Created test with 42 ion pairs
- All 1830 CH4 guest molecules now have correct atom order ['C','H','H','H','H']
- H2 residue count in output: 0 (was 5 before)
- CH4 atoms: 9150 (expected 1830 × 5 = 9150)
- Comparison with broken file: CH4 went from 9145 to 9150 atoms, H2 went from 5 to 0 atoms
- Output GRO file passes basic validation
files_changed: [quickice/structure_generation/ion_inserter.py]
