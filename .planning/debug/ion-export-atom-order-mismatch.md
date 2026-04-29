---
status: verifying
trigger: "Debug the atom order mismatch bug in QuickIce GROMACS ion export that only occurs with 2x2x2 (larger) hydrate systems"
created: 2025-04-29T00:00:00Z
updated: 2025-04-29T19:00:00Z
---

## Current Focus
hypothesis: CONFIRMED - The bug is in `slab.py` lines 540-556. The `processed_guest_atom_names` is computed using `tiling_factor = tiled_guest_nmolecules // original_guest_nmolecules`, but `tile_structure()` FILTERS molecules at boundaries (water_filler.py lines 488-500), so the returned `tiled_guest_nmolecules` may be LESS than the expected value. This causes `processed_guest_atom_names` to be SHORTER than `processed_guest_positions`, leading to the last guest molecule reading water atom names.
test: Verified with debug script - `tile_structure()` DOES filter molecules. For 2x2x2 hydrate with original 64 guest molecules, tiling to 7.2nm box returns only 2024 molecules instead of expected 3456 (after filtering). The atom names computed using `tiling_factor` will be WRONG.
expecting: The fix is to compute `processed_guest_atom_names` based on ACTUAL `len(processed_guest_positions)`, not using `tiling_factor`.
next_action: Implement fix in slab.py lines 540-556 and verify it resolves the ion export bug.

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

- timestamp: 2025-04-29T21:00:00Z
  checked: tile_structure() filtering behavior with debug script
  found: For 2x2x2 hydrate (64 original guest molecules), tiling to 7.2nm box returns only 2024 molecules (expected 3456 without filtering). tile_structure() filters molecules at boundaries (lines 488-500 in water_filler.py).
  implication: tiled_guest_nmolecules may be LESS than tiling_factor * original_guest_nmolecules

- timestamp: 2025-04-29T21:30:00Z
  checked: slab.py lines 540-556 atom name computation
  found: processed_guest_atom_names uses `tiling_factor = tiled_guest_nmolecules // original_guest_nmolecules`. If tile_structure() filters molecules, tiled_guest_nmolecules is wrong, causing processed_guest_atom_names to be SHORTER than processed_guest_positions.
  implication: THIS IS THE ROOT CAUSE! The last guest molecule(s) will have water atom names because the arrays are misaligned.

## Resolution
root_cause: "In slab.py lines 540-556, `processed_guest_atom_names` was computed using `tiling_factor = tiled_guest_nmolecules // original_guest_nmolecules`. However, `tile_structure()` FILTERS molecules at boundaries (water_filler.py lines 488-500), so the returned `tiled_guest_nmolecules` may be LESS than `tiling_factor * original_guest_nmolecules`. This caused `processed_guest_atom_names` to be SHORTER than `processed_guest_positions`. When the ion export read atom names from the last guest molecule, it read from the water region instead, creating the H2 residue with water atom names."

fix: "Modified slab.py lines 540-570 to compute `processed_guest_atom_names` based on the ACTUAL length of `processed_guest_positions`:
1. Calculate `atoms_per_guest = len(guest_atom_names) // original_guest_nmolecules`
2. Calculate `actual_guest_nmolecules = len(processed_guest_positions) // atoms_per_guest`
3. Use `guest_pattern = guest_atom_names[:atoms_per_guest]` and repeat for `actual_guest_nmolecules`
4. Update `guest_nmolecules` to use `actual_guest_nmolecules`"

verification: "Pending - needs manual testing by user (gmx not in env)"
files_changed: ['quickice/structure_generation/modes/slab.py']
