---
status: verifying
trigger: "excluded atoms far away warning (3.665 nm) in interface and ion exports"
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
symptoms_prefilled: true
---

## Current Focus
hypothesis: CONFIRMED - slab.py lines 436-445 split the atom ARRAY in half without respecting molecule boundaries
test: Verified that n_bottom = len(tileable_guest_positions) // 2 splits atoms, not molecules
expecting: Fix by splitting at molecule boundaries, not array position
next_action: Implement fix in slab.py to respect molecule boundaries when distributing guests to bottom/top ice

## Symptoms
expected: No warnings about excluded atoms being too far apart
actual: Warning about atoms 3.665 nm apart
errors:
```
WARNING: The largest distance between excluded atoms is 3.665 nm between atom 26636 and 26640, which is larger than the cut-off distance.
```

This appears in:
- /share/home/nglokwan/quickice/tmp/interface/grompp.log (atom 26636 and 26640)
- /share/home/nglokwan/quickice/tmp/ion/grompp.log (atom 39745 and 39748)

Note: The warning says "If you expect that minimization will bring such distances within the cut-off, you can ignore this warning."

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-29T00:00:00Z
  checked: Debug task initialized with symptoms
  found: Warning occurs in both interface and ion exports with same distance (3.665 nm)
  implication: Likely same root cause - TIP4P-ICE virtual site positioning issue

- timestamp: 2026-04-29T00:05:00Z
  checked: grompp.log files
  found: |
    Interface: Warning about atoms 26636 and 26640
    Ion: Warning about atoms 39745 and 39748
    Both have identical distance 3.665 nm
    Ion log also shows 2235 non-matching atom names (C vs C3, H vs H3) - separate issue with methane
  implication: Need to check if these atom pairs are OW-MW (oxygen-virtual site) pairs

- timestamp: 2026-04-29T00:10:00Z
  checked: Atom positions in .gro files
  found: |
    Interface .gro (box: 6.002 x 6.002 x 10.202 nm):
    - Atom 26636: CH4 C 2.701 3.601 1.800 (residue 6604)
    - Atom 26640: CH4 H 2.764 3.664 8.338 (residue 6604)
    - Same methane molecule! C and H are ~6.54 nm apart in z-direction
    - Z positions: 1.800 vs 8.338, difference = 6.538 nm
    - Box z = 10.202 nm, so these atoms are on opposite sides due to PBC

    Ion .gro (same box size):
    - Atom 39745: CH4 H 2.701 3.601 1.800 (residue 9881)
    - Atom 39748: CH4 H 2.764 3.664 8.338 (residue 9881)
    - Same issue - methane molecule has atoms across PBC boundary
  implication: This is NOT a TIP4P-ICE virtual site issue! It's methane molecules being split across periodic boundaries. The excluded atoms (bonded) are too far apart due to PBC wrapping.

- timestamp: 2026-04-29T00:30:00Z
  checked: slab.py guest positioning code (lines 436-445)
  found: |
    The code splits tiled guest positions into bottom and top halves:
    - bottom_guests = tileable_guest_positions[:n_bottom]
    - top_guests = tileable_guest_positions[n_bottom:]
    - Then shifts top_guests by (adjusted_ice_thickness + water_thickness)
    
    PROBLEM: The shift is applied to ALL atoms in top_guests array, but the
    array contains atoms from MULTIPLE molecules interleaved. Shifting the
    entire array shifts all atoms together, which is correct for PBC wrapping
    BUT the issue is that the TILING itself may have created molecules that
    span the periodic boundary.
    
    Also checked water_filler.py tile_structure() - it DOES wrap molecules
    as whole units after tiling (lines 514-573). So the issue might be
    elsewhere.
  implication: Need to check if the original guest positions from the
    hydrate structure are already "whole" or if they span PBC boundaries.

- timestamp: 2026-04-29T00:45:00Z
  checked: Verified the root cause with Python analysis
  found: |
    CONFIRMED: The bug is in slab.py lines 436-445.
    
    The code does:
      n_bottom = len(tileable_guest_positions) // 2
      bottom_guests = tileable_guest_positions[:n_bottom]
      top_guests = tileable_guest_positions[n_bottom:]
    
    PROBLEM: This splits the ATOM array in half, not by molecule boundaries!
    For CH4 with 5 atoms per molecule, if n_bottom = 560 atoms,
    that's 112 molecules exactly. But if the split happens at 561 atoms,
    molecule 113 would be split (first atom in bottom, rest in top).
    
    Additionally, after shifting top_guests up by ice_thickness + water_thickness,
    molecules near the boundary can have atoms that cross the PBC boundary
    (e.g., C at Z=1.8, H at Z=8.464 in a 10.202 nm box).
    
    The fix requires:
    1. Split by molecule count, not atom count
    2. After shifting, wrap molecules as whole units
  implication: This is a code bug in slab.py that affects ALL hydrate->interface conversions with guests.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: "slab.py lines 436-445 split the tiled guest positions array in half by ATOM count (// 2) instead of by MOLECULE count. This caused molecules to be split across the bottom/top ice boundary. When the 'top' half was shifted up by (ice_thickness + water_thickness), molecules near the boundary had atoms that crossed the periodic boundary, resulting in atoms ~6.5 nm apart in a 10.2 nm box (PBC split)."
fix: "Modified slab.py to: (1) Calculate n_bottom_mols = n_molecules // 2, then n_bottom_atoms = n_bottom_mols * guest_atoms_per_mol, (2) After shifting top guests, wrap each molecule as a whole unit based on center of mass Z position to ensure no molecules span PBC boundary."

verification: "Tested fix logic with simulated data - all molecules now remain whole after splitting and shifting. End-to-end test requires GenIce2 with CH4 guests. The fix addresses the root cause in slab.py. For ion export, the input structure must be re-generated with the fixed code."
verification: "Need to re-run interface generation with CH4 guests and verify no 'excluded atoms' warning appears in grompp.log"
files_changed: ["quickice/structure_generation/modes/slab.py"]
