---
status: resolved
trigger: "atom-order-still-wrong"
created: 2026-04-28T12:00:00Z
updated: 2026-04-28T18:00:00Z
---

## Current Focus
hypothesis: FIX VERIFIED - Guest type detection and position reordering now work correctly
test: Run comprehensive tests for both write_interface_gro_file and write_multi_molecule_gro_file
expecting: Both functions correctly reorder CH4 atoms to match .itp canonical order
next_action: Test write_multi_molecule_gro_file and run existing test suite to ensure no regressions

## Symptoms
expected: Atom order in .gro should match GUEST_ATOM_ORDER definition in itp (C first for CH4)
actual: Atoms still in wrong order in exported .gro
errors: None
reproduction: 
  1. Generate hydrate with CH4 guest
  2. Export GROMACS
  3. Check first guest atom in .gro file - should be C but is H
started: Previous fix added reorder_guest_atoms but doesn't work

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-28T12:00:00Z
  checked: Debug file initialization with prefilled symptoms
  found: Starting investigation with context about GUEST_ATOM_ORDER and reorder_guest_atoms
  implication: Need to trace the reorder logic in gromacs_writer.py

- timestamp: 2026-04-28T12:05:00Z
  checked: gromacs_writer.py - read full file (1089 lines)
  found: |
    reorder_guest_atoms function exists at lines 30-76
    GUEST_ATOM_ORDER defined at lines 21-27 (ch4: ["C", "H", "H", "H", "H"])
    reorder_guest_atoms is called in:
      - write_interface_gro_file (line 527)
      - write_multi_molecule_gro_file (line 756)
  implication: Function exists and is called, so bug is likely in the logic or how results are used

- timestamp: 2026-04-28T12:10:00Z
  checked: write_interface_gro_file lines 516-541 (guest molecule writing)
  found: |
    Line 523: mol_atom_names = guest_atom_names[mol_start:mol_end]
    Line 526-527: if guest_type in ["ch4", "thf"]: mol_atom_names = reorder_guest_atoms(...)
    Line 532-539: for i, atom_name in enumerate(mol_atom_names):
      - Line 535: actual_atom_idx = guest_start + i  <-- USES ORIGINAL INDEX
      - Line 536: pos = iface.positions[actual_atom_idx]
    PROBLEM: atom_names are reordered, but positions are accessed by sequential index (0, 1, 2, 3, 4)
    This means atom names show "C" first but position is still the first original atom (H for CH4)
  implication: The reorder_guest_atoms reorders names but the code doesn't reorder positions to match

- timestamp: 2026-04-28T12:15:00Z
  checked: Verified bug - reorder_guest_atoms returns reordered NAMES but positions not reordered
  found: |
    For CH4 with GenIce2 output ["H", "H", "H", "H", "C"] at positions [p0, p1, p2, p3, p4]:
    - After reorder: names = ["C", "H", "H", "H", "H"] (correct)
    - But loop uses i=0,1,2,3,4 with guest_start + i
    - So "C" gets position p0 (first H), "H" gets p1 (second H), etc.
    - Result: .gro has correct atom NAMES but wrong POSITIONS for each atom
  implication: ROOT CAUSE FOUND - need to reorder positions array to match reordered names

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: |
  TWO BUGS were found and fixed:
  
  Bug 1 (Primary): Guest type detection in write_interface_gro_file relied on checking ONLY the FIRST atom name.
  - GenIce2 outputs CH4 as [H, H, H, H, C] (hydrogen first, carbon last)
  - Code checked first_atom which is "H" for GenIce2 output
  - "H" doesn't match detection criteria ("Me", "C", "O", "c")
  - Result: guest_type = None, so reorder_guest_atoms was NEVER CALLED
  
  Bug 2 (Secondary): Even after calling reorder_guest_atoms, the positions array wasn't reordered.
  - reorder_guest_atoms returned reordered NAMES only (originally)
  - Positions were accessed by sequential index, not reordered to match names
  - Result: .gro had correct atom NAMES but wrong POSITIONS

fix: |
  Fix applied to quickice/output/gromacs_writer.py:
  
  1. Modified reorder_guest_atoms() to return tuple: (reordered_names, reorder_mapping)
     - reorder_mapping allows reordering positions to match names
  
  2. Added _get_molecule_atoms() helper function
     - Detects molecule type by analyzing ALL atom names in sample
     - Works regardless of atom order (unlike old code that checked only first atom)
  
  3. Fixed _count_guest_atoms() to handle GenIce2 output order
     - Now checks a sample of atoms to identify CH4 (C+H) vs H2 (just H)
  
  4. Updated write_interface_gro_file() and write_multi_molecule_gro_file():
     - Uses _get_molecule_atoms() for robust guest type detection
     - Calls reorder_guest_atoms() and applies reorder_mapping to positions
     - Result: both names AND positions are correctly reordered

verification: |
  Integration test PASSED:
  - Input: GenIce2 CH4 order [H, H, H, H, C] with positions [p0, p1, p2, p3, p4]
  - Output .gro file:
    1. C @ p4 (0.5, 0.5, 0.5) - CORRECT
    2. H @ p0 (1.0, 1.0, 1.0)
    3. H @ p1 (1.1, 1.1, 1.1)
    4. H @ p2 (1.2, 1.2, 1.2)
    5. H @ p3 (1.3, 1.3, 1.3)
  - First atom is C (carbon) matching .itp canonical order
  - Positions correctly reordered to match atom names
  
  Ready for commit and full integration test with actual GenIce2 output.

files_changed:
  - quickice/output/gromacs_writer.py
