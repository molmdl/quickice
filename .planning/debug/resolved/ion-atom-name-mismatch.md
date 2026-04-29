---
status: resolved
trigger: "Atom name mismatch (C vs C3, H vs H3) in hydrate->interface->ion export path"
created: 2026-04-28
updated: 2026-04-29
---

## Root Cause
**Two bugs fixed in `quickice/output/gromacs_writer.py`:**

**Bug 1: GRO format violation in `write_ion_gro_file()` (line 1309)**
- The atom name field (bytes 10-14) was overlapping with the atom number field (bytes 15-19)
- Bug: `atom_name[0:4]:>4s` = 4 chars for atom name (WRONG)
- Fix: `atom_name:>5s` = 5 chars for atom name (CORRECT)

**Bug 2: `reorder_guest_atoms()` returned input names instead of canonical names**
- The function was returning `[atom_names[i] for i in reorder]` (reordered INPUT names)
- If input contained atom TYPES ("c3", "hc"), output would also be types
- Fix: Return `list(canonical)` to always output canonical names ("C", "H")

## Evidence
1. **GRO format violation:**
   - OLD output: `" 9658CH4     C38629"` → atom name field = "    C3" (WRONG)
   - NEW output: `" 9658CH4      C38629"` → atom name field = "     C" (CORRECT)

2. **reorder_guest_atoms() fix:**
   - Input types ["hc","hc","hc","hc","c3"] → Output now ["C","H","H","H","H"] (CORRECT)
   - Previously returned ["hc","hc","hc","hc","c3"] (WRONG - these are types, not names)

## Files Changed
1. `quickice/output/gromacs_writer.py` line 1309: Fixed atom name format in `write_ion_gro_file()`
2. `quickice/output/gromacs_writer.py` lines 63-81: Fixed `reorder_guest_atoms()` to return canonical names

## Verification
- Tested format strings: confirmed 5-char atom name field works correctly
- Tested `reorder_guest_atoms()` with both names and types as input
- Ran comprehensive test simulating full workflow (hydrate → interface → ion)
- All CH4 atom names correctly output as "C" and "H" in .gro file

## Resolution Date
2026-04-29

## Symptoms

expected: .gro file should have atom NAMES (C, H) as defined in .itp file
actual: .gro file has atom TYPES (c3, hc) instead of names
errors: 
```
atom name 38629 in ions_28na_28cl.top and ions_28na_28cl.gro does not match (C - C3)
atom name 38630 in ions_28na_28cl.top and ions_28na_28cl.gro does not match (H - H3)
```
reproduction: 
1. Generate hydrate (sI + CH4)
2. Export as Interface GROMACS
3. Insert ions
4. Export ions as GROMACS
5. Run grompp - see atom name mismatch warnings

## Root Cause Hypothesis

The ion export function `write_ion_gro_file()` is writing atom TYPE (c3, hc) instead of atom NAME (C, H) in the .gro file.

The .itp file (ch4.itp) defines:
- Atom name: C (for carbon)
- Atom name: H (for hydrogen)
- Atom type: c3 (for carbon)  
- Atom type: hc (for hydrogen)

The .top file includes the .itp which defines atom names as C and H.
But the .gro file is being written with c3 and hc (the types) instead of C and H (the names).

## Files to Check

1. `quickice/output/gromacs_writer.py` - Look for `write_ion_gro_file()` function
2. Check how atom names are being written to the .gro file
3. The function should use the atom name from the .itp file, not the atom type

## Key Difference

- `.itp [atoms]` section: atom NAME is in column 5 (C, H for CH4)
- `.gro` file: column 10-14 should have atom NAME (C, H), not TYPE (c3, hc)

## Reference Files
- /share/home/nglokwan/quickice/tmp/ion/ions_28na_28cl.gro (has wrong names)
- /share/home/nglokwan/quickice/tmp/ion/ch4.itp (defines correct names: C, H)
- /share/home/nglokwan/quickice/tmp/ion/ions_28na_28cl.top (expects C, H)
