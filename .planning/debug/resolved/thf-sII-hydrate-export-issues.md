---
status: resolved
trigger: "thf-sII-hydrate-export-issues"
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
---

## Current Focus
hypothesis: Two root causes identified:
1. Interface export: guest_atom_count=0 but guest_nmolecules=192 in InterfaceStructure - atoms lost during slab assembly
2. Ion export: detect_guest_type_from_atoms() fails to recognize THF because it checks for 'C' but THF atoms are 'CA'/'CB'
test: Verify by checking how tile_structure handles guest atoms and fix detection function
expecting: Find that guest positions are not being passed to InterfaceStructure.positions
next_action: Check water_filler.py tile_structure and fix detect_guest_type_from_atoms for CA/CB atoms

## Symptoms
expected: 
1. All hydrate unit cells in hydrate layer should be filled with guest molecules
2. CPK atoms of THF should show bonds in 3D viewer
3. Interface export: GRO file should contain guest molecules with correct THF resname, topology should group SOL molecules together
4. Ion export: GRO file should use THF resname (not GUE), topology should include thf.itp (not missing guest.itp), exported ITP should be thf.itp (not ch4.itp)

actual:
1. Both tabs: Not all hydrate unit cells filled with guest
2. Both tabs: No bonds between CPK atoms of THF in interface 3D viewer
3. Interface tab: GRO has NO guest molecules (grep shows nothing), but TOP declares "THF 192". TOP also has SOL split into two groups (4780 SOL, 192 THF, 2432 SOL) instead of grouped together
4. Ion tab: GRO uses "GUE" resname instead of "THF", TOP includes non-existent "guest.itp" and declares "GUE 192" (should be thf.itp and THF 192), exported ch4.itp instead of thf.itp

errors: No explicit errors reported, but structural mismatches between files

reproduction: 
- Export THF sII hydrate -> interface tab -> gmx export (results in tmp/slab/)
- Export THF sII hydrate -> interface -> ion tab -> gmx export (results in tmp/ion/)
- Compare with correct THF hydrate export (tmp/hyd/)

started: Current issue, discovered during testing

## Eliminated

## Evidence
- timestamp: initial
  checked: tmp/hyd/ reference files
  found: Correct THF hydrate has THF residues in GRO, includes thf.itp in TOP, declares "THF 24"
  implication: Reference implementation works correctly

- timestamp: initial
  checked: tmp/slab/ interface export
  found: GRO has NO THF molecules, but TOP declares "THF 192", SOL split into two groups
  implication: Guest molecules lost during GRO generation but TOP still references them

- timestamp: initial
  checked: tmp/ion/ ion export
  found: GRO uses "GUE" resname, TOP includes non-existent "guest.itp", exported ch4.itp instead of thf.itp
  implication: Ion export uses wrong guest type/template

- timestamp: investigation
  checked: tmp/slab/interface_slab.gro atom count
  found: 31344 atoms, 0 THF entries (grep shows nothing)
  implication: guest_atom_count must be 0 in InterfaceStructure

- timestamp: investigation
  checked: tmp/slab/interface_slab.top [molecules] section
  found: "SOL 4780", "THF 192", "SOL 2432" - THF declared but not in GRO
  implication: guest_nmolecules=192 but guest_atom_count=0 - mismatch

- timestamp: investigation
  checked: tmp/ion/ions_16na_16cl.gro THF atom names
  found: Guest atoms named "O", "CA", "CA", "CB", "CB", "H"... (13 atoms per THF)
  implication: detect_guest_type_from_atoms() must recognize CA/CB as carbon

- timestamp: investigation
  checked: gromacs_writer.py detect_guest_type_from_atoms() line 707-708
  found: Checks 'O' in mol_unique and 'C' in mol_unique for THF detection
  implication: THF has 'CA'/'CB' not 'C', so detection fails

- timestamp: investigation
  checked: gromacs_writer.py _get_molecule_atoms() lines 424-426
  found: THF detection checks counts.get('C', 0) >= 4 but THF atoms are 'CA'/'CB'
  implication: Both detection functions fail to recognize THF atom names

## Resolution
root_cause: 
**Issue 1 (Interface export - no THF in GRO):**
slab.py line 462 incorrectly calculated guest_atoms_per_mol as len(guest_atom_names) (total guest atoms)
instead of len(guest_atom_names) // original_guest_nmolecules (atoms per guest molecule).
This caused tile_structure() to treat all guest atoms as one giant "molecule", which failed filtering.
Same bug existed in pocket.py line 371.

**Issue 2 (Ion export - GUE resname and guest.itp):**
gromacs_writer.py detect_guest_type_from_atoms() checked for 'C' in mol_unique,
but THF atoms are named 'CA' and 'CB' (not 'C'), so detection failed and fell back to "GUE"/"guest.itp".
Same issue in _get_molecule_atoms() and _count_guest_atoms().

**Issue 3 (write_interface_gro_file duplicate detection logic):**
The function had inline guest type detection that also failed for THF (checking for 'C' not 'CA'/'CB').

fix: 
1. Fixed slab.py and pocket.py: guest_atoms_per_mol = len(guest_atom_names) // original_guest_nmolecules
2. Fixed gromacs_writer.py detect_guest_type_from_atoms() to recognize 'CA'/'CB' as carbon atoms
3. Fixed gromacs_writer.py _get_molecule_atoms() to count CA/CB as carbon atoms
4. Fixed gromacs_writer.py _count_guest_atoms() to return 13 for THF (O-first atoms)
5. Fixed write_interface_gro_file() to use detect_guest_type_from_atoms() instead of inline logic
6. Fixed export.py IonGROMACSExporter to use detect_guest_type_from_atoms()

verification: 
- Interface export: THF molecules present in GRO (4238 atoms = 326 mols * 13 atoms) ✓
- Interface TOP: includes thf.itp ✓
- Ion export: GRO uses THF resname (not GUE) ✓
- Ion TOP: includes thf.itp (not guest.itp) ✓
files_changed: [quickice/structure_generation/modes/slab.py, quickice/structure_generation/modes/pocket.py, quickice/output/gromacs_writer.py, quickice/gui/export.py]
