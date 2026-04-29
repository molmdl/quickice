---
status: investigating
trigger: "Ion Export Atom Order Mismatch - CH4 missing and extra water molecule"
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:05:00Z
symptoms_prefilled: true
goal: find_root_cause_only
---

## Current Focus

hypothesis: A water molecule is being included in guest_indices during hydrate guest extraction, causing atom count mismatch during tiling
test: Trace _detect_guest_atoms logic to find where water molecule gets added to guest_indices
expecting: Find the specific condition that causes a water molecule to be misclassified as guest
next_action: Check _count_guest_atoms for CH4 handling and verify if atoms_per_mol affects water detection

## Symptoms

expected: 1830 CH4 molecules, no extra water, then ions in correct order
actual: 1829 CH4 molecules, 1 extra water (H2 residue), then ions - causing atom order mismatch
errors: GROMACS grompp fails with atom name mismatch (C-H, H-OW) at positions 77970-77971
reproduction: Export hydrate→interface→ion workflow
started: Unknown - discovered in user testing

## Eliminated

- hypothesis: GenIce2 outputs CH4 in wrong order (H first)
  evidence: GenIce2 outputs CH4 as [C, H, H, H, H] - correct order
  timestamp: 2026-04-29T00:02:00Z

- hypothesis: _count_guest_atoms has bug with CH4 counting
  evidence: _count_guest_atoms correctly returns 5 for CH4 starting with C
  timestamp: 2026-04-29T00:03:00Z

## Evidence

- timestamp: 2026-04-29T00:00:00Z
  checked: GRO file atom positions 77970-77974
  found: Residue 19036 named "H2" has atoms [H, OW, HW1, HW2, MW] - a TIP4P water with wrong atom order
  implication: Water molecule is being misidentified as H2 guest type

- timestamp: 2026-04-29T00:00:30Z
  checked: GRO file header and counts
  found: 9145 CH4 atoms (1829 CH4), 5 "H2" atoms (1 misidentified water), 39 NA, 39 CL
  implication: The 1830th expected CH4 is actually a water molecule

- timestamp: 2026-04-29T00:01:00Z
  checked: detect_guest_type_from_atoms() in gromacs_writer.py
  found: When atoms [H, OW, HW1, HW2, MW] are passed, _get_molecule_atoms returns ['H', 'H'], then mol_unique == {'H'} triggers "h2" type
  implication: The detection logic correctly identifies based on atom composition, but the input is wrong - a water molecule shouldn't be in guest region

- timestamp: 2026-04-29T00:02:30Z
  checked: GenIce2 CH4 output format
  found: GenIce2 outputs CH4 as [C, H, H, H, H] with residue "CH4", which matches expected .itp order
  implication: The issue is NOT in GenIce2 output, but in QuickIce processing

- timestamp: 2026-04-29T00:03:30Z
  checked: _detect_guest_atoms logic in slab.py
  found: Function expects OW first for water, but if first atom is not OW, calls _count_guest_atoms. The _count_guest_atoms default case returns 1 for unrecognized atoms like "H"
  implication: If a molecule starts with "H", only 1 atom would be added to guest_indices, potentially leaving the next atom (OW) for the next iteration

- timestamp: 2026-04-29T00:04:00Z
  checked: tile_structure and atom name tiling in slab.py
  found: tile_structure filters molecules by atoms_per_molecule, but atom name tiling uses tiling_factor = tiled_guest_nmolecules // original_guest_nmolecules. Also, atoms_per_guest = len(guest_atom_names) // original_guest_nmolecules assumes all guests have same atom count
  implication: If guest_atom_names includes a water molecule (4 atoms) among CH4 (5 atoms), the atoms_per_guest calculation is wrong

- timestamp: 2026-04-29T00:04:30Z
  checked: GRO file residue pattern around problem area
  found: Residue 19035CH4 ends with H77969, then residue 19036H2 has [H77970, OW77971, HW177972, HW277973, MW77974]. The H77970 at (5.101, 6.001, 10.802) is ~0.11nm from OW77971 at (5.038, 5.938, 10.739)
  implication: The extra H atom is close to the OW, suggesting it might be a CH4 hydrogen that got separated from its carbon

## Resolution

root_cause:
fix:
verification:
files_changed: []
