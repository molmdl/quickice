---
status: investigating
trigger: "Debug the atom order mismatch bug in QuickIce GROMACS ion export that only occurs with 2x2x2 (larger) hydrate systems"
created: 2025-04-29T00:00:00Z
updated: 2025-04-29T19:00:00Z
---

## Current Focus
hypothesis: The `ion_structure.atom_names` array has water atom names at the position of the last guest. This is built by `replace_water_with_ions()` which reads from `interface_structure.atom_names[start_idx:end_idx]` where start_idx comes from `_build_molecule_index_from_structure()`. If `guest_atom_count` stored in InterfaceStructure is less than 9150 (actual), `guest_atoms_per_mol` would be calculated as 4 instead of 5, causing all start_idx values to be wrong.
test: Check if `guest_atom_count` in the actual InterfaceStructure passed to insert_ions() differs from 9150. Need to verify: 1) Is the stored `guest_atom_count` consistent with `len(positions)` for the guest region? 2) Is `processed_guest_positions` length correctly calculated in slab.py? 3) Is there any case where `len(processed_guest_positions)` != `tiled_guest_nmolecules * guest_atoms_per_mol`?
expecting: Find that `guest_atom_count` stored in InterfaceStructure is 9145-9149 instead of 9150, OR find that `processed_guest_positions` has wrong length due to tile_structure() returning inconsistent position count vs molecule count.
next_action: Write a test script to directly load the hydrate candidate and trace through slab.py assemble_slab() to check the exact values of `processed_guest_positions` length, `tiled_guest_nmolecules`, and the resulting `guest_atom_count`.

## Symptoms
expected: 1830 CH4 guest molecules (each with 5 atoms: C, H, H, H, H)
actual: 1829 CH4 + 1 H2 residue with atoms [H, OW, HW1, HW2, MW] (WRONG!)
errors: Last guest molecule gets water atom names instead of CH4 atom names
reproduction: Generate 2x2x2 sI hydrate → Create interface → Insert ions → Export → Check last CH4
started: Bug only appears with 2x2x2 hydrate, not with 1x1x1

## Eliminated
- hypothesis: _build_molecule_index_from_structure() incorrectly detects ice_atoms_per_mol=3
  evidence: Debug script shows ice_atoms_per_mol=4 is correctly detected (first atom is "OW")
  timestamp: 2025-04-29T19:00:00Z

## Evidence
- timestamp: 2025-04-29T00:00:00Z
  checked: Interface GRO file (interface_slab.gro)
  found: 78326 total atoms, ice=49752 atoms (12438 molecules × 4), guests=9150 atoms (1830 × 5), water=19424 atoms (4856 × 4)
  implication: Interface export is CORRECT - atom layout is correct
  
- timestamp: 2025-04-29T00:00:00Z
  checked: Ion GRO file (ions_40na_40cl.gro)
  found: Residue 19036 labeled "H2" with atoms [H, OW, HW1, HW2, MW] at atom index 77969 - WRONG!
  implication: Last guest molecule's atom names are corrupted - water atoms instead of CH4 atoms

- timestamp: 2025-04-29T19:00:00Z
  checked: Debug script simulating _build_molecule_index_from_structure() with CORRECT metadata
  found: molecule_index is CORRECT when ice_nmolecules=12438, ice_atoms_per_mol=4, guest_nmolecules=1830
  implication: The bug is NOT in _build_molecule_index_from_structure() logic - it's in the INPUT METADATA

- timestamp: 2025-04-29T19:00:00Z
  checked: Actual GRO file molecule counts
  found: Ice=12438, Guests=1830, Water=4856. User reported ice_nmolecules=22952 (WRONG!)
  implication: The InterfaceStructure.ice_nmolecules is set to wrong value (22952 instead of 12438)

## Resolution
root_cause: 
fix:
verification:
files_changed: []
