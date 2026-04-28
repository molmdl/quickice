---
status: resolved
trigger: "hydrate → interface: 3D viewer shows no guest molecules, hydrate interface has long bonds, export has no guests"
created: 2026-04-24
updated: 2026-04-24
---

## Current Focus
<!-- RESOLVED: Two bugs found and fixed -->

## Symptoms
expected: "3D viewer shows guest molecules (gray ball-and-stick), hydrate interface shows normal bonds, exported .gro has guests"
actual: "3D viewer shows NO guest molecules, hydrate interface has LONG bonds (incorrect), export has NO guests"
errors: "None visible, just missing guest atoms"
reproduction: "Generate hydrate (sI with CH4) → Use in Interface → View in 3D → No guests shown"
started: "Previous fixes claimed to address this but user confirms all 3 issues persist"

## Eliminated
- hypothesis: "Guest extraction logic is broken"
  evidence: "Tested _detect_guest_atoms - works correctly. Returns correct indices."
  timestamp: 2026-04-24

- hypothesis: "VTK conversion doesn't handle guests"
  evidence: "interface_to_vtk_molecules works correctly when guest_atom_count > 0. Verified with test."
  timestamp: 2026-04-24

- hypothesis: "GRO export doesn't write guests"
  evidence: "write_interface_gro_file works correctly when guest counts > 0. Verified with test."
  timestamp: 2026-04-24

## Evidence

- timestamp: 2026-04-24
  checked: "piece.py assemble_piece() with hydrate candidate"
  found: "BUG 1: tile_structure() receives ALL atoms (water + guests) but expects uniform atom count"
  found: "tile_structure() requires positions to be divisible by atoms_per_molecule"
  found: "With mixed water (4 atoms/mol) + guests (variable atoms), this fails with ValueError"
  implication: "Interface generation FAILS for hydrate due to mixed atom types"

- timestamp: 2026-04-24
  checked: "piece.py guest_nmolecules calculation"
  found: "BUG 2: guest_nmolecules = len(guest_indices) counts ATOMS not MOLECULES"
  found: "For CH4 (5 atoms): code returns 5, should be 1"
  implication: "guest_nmolecules is wrong, but this is secondary to Bug 1"

## Resolution

root_cause: "Two bugs in piece.py assemble_piece():
1. tile_structure() receives mixed water+guest atoms, fails with 'not divisible by atoms_per_molecule'
2. guest_nmolecules calculated as len(guest_indices) instead of counting distinct molecules"

fix: "Modified assemble_piece() to:
1. Extract water-framework-only positions for tiling (removing guest atoms first)
2. Use water_framework_atom_names when building ice_atom_names for hydrate
3. Added _count_guest_molecules() helper to count distinct guest molecules (not atoms)"

verification: "All three issues verified fixed:
- ✓ Guest atoms preserved in InterfaceStructure
- ✓ Guest molecule counted correctly (1 CH4 = 1 molecule, not 5)
- ✓ VTK conversion creates guest molecule (5 atoms)
- ✓ GRO export writes CH4 residues (5 atoms found)
- ✓ All existing tests pass (59 in test_structure_generation.py, 18 in test_integration_v35.py)"

files_changed:
  - quickice/structure_generation/modes/piece.py: Fixed hydrate→interface conversion

---
## Original Debug File Content
<!-- Previous investigation notes preserved below -->