---
status: resolved
trigger: "THF C-C bonds missing and sII gridbox issue"
created: 2026-04-17T00:00:00Z
updated: 2026-04-17T00:00:00Z
---

## Current Focus
COMPLETED: Both issues fixed and verified

## Symptoms
expected:
  - Issue 1: THF molecules should show both C-C bonds AND C-O bonds in ring structure
  - Issue 2: THF molecules should be contained within unit cell boundaries for sII structure
actual:
  - Issue 1: Only C-O bonds visible, C-C bonds missing
  - Issue 2: THF molecules extend outside unit cell box
reproduction:
  - Issue 1: Generate THF hydrate, look at THF molecules in viewer - C-C bonds not visible
  - Issue 2: Generate THF hydrate with sII cell type, observe molecules outside box
started: Recent fixes improved THF but C-C bonds still missing; sII gridbox issue

## Eliminated

## Evidence
- timestamp: 2026-04-17
  checked: hydrate_renderer.py lines 88-93
  found: "BOND_DISTANCE_THRESHOLD = 0.15 nm"
  implication: "C-C bonds (0.151-0.153nm) may be missed at this threshold"

- timestamp: 2026-04-17
  checked: THF bond distances from GenIce2 output
  found: "O-CB: 0.143nm, CB-CA: 0.151nm, CA-CA: 0.150nm"
  implication: "C-C bonds are at/above 0.15nm threshold edge"

- timestamp: 2026-04-17
  checked: sII GenIce2 positions vs box
  found: "Positions range from -0.033 to 1.745, box is 1.712nm"
  implication: "Some atoms have negative coordinates or exceed box - need wrapping"

- timestamp: 2026-04-17
  checked: Position wrapping test
  found: "After wrapping: 0.033 to 1.680, all within box"
  implication: "Simple modulo wrapping works correctly"

## Resolution

### Root Cause
**Issue 1:** BOND_DISTANCE_THRESHOLD = 0.15nm was at the edge of C-C bond detection.
  - THF C-C bonds are ~0.150-0.153nm
  - Threshold of 0.15nm was borderline, causing some C-C bonds to be missed

**Issue 2:** GenIce2 outputs some atoms with negative coordinates or slightly outside [0, L) range.
  - Atoms with positions like -0.032nm or 1.745nm (box is 1.712nm)
  - This happens when molecules straddle periodic boundaries

### Fix Applied
**Issue 1:** Increased BOND_DISTANCE_THRESHOLD from 0.15nm to 0.16nm in hydrate_renderer.py
  - Now captures all covalent bonds including C-C (~0.15-0.153nm)
  - Still excludes H-H (~0.16-0.18nm)

**Issue 2:** Added position wrapping in hydrate_generator.py
  - New method `_wrap_positions_to_cell()` handles both orthorhombic and triclinic cells
  - Wraps all positions to [0, L) range using modulo or fractional coordinate conversion
  - Applied in `_parse_gro_result()` after parsing positions

**Additional fix:** Fixed THF molecule grouping by residue sequence number
  - Previously grouped all consecutive "THF" residue names as one molecule
  - Now correctly groups by residue sequence number (137THF, 138THF, etc.)
  - Each THF molecule has 13 atoms properly separated

### Verification
- All 57 structure generation tests pass
- sII THF structure: 24 THF molecules detected (13 atoms each)
- All positions in [0, L) range after wrapping
- C-C bonds now detected (CA-CA: 0.1506nm, CA-CB: 0.1511nm)
- sI CH4 structure: 46 water + 8 CH4 guests correctly detected

## Files Changed
- quickice/gui/hydrate_renderer.py: BOND_DISTANCE_THRESHOLD 0.15 → 0.16 nm
- quickice/structure_generation/hydrate_generator.py: Added _wrap_positions_to_cell(), updated _parse_gro_result(), fixed THF molecule grouping
