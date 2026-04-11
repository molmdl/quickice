---
status: complete
phase: 20-export
source: [20-01-SUMMARY.md, 20-02-SUMMARY.md]
started: 2026-04-11T13:38:41Z
updated: 2026-04-11T13:38:41Z
---

## Current Test

[testing complete]

## Tests

### 1. Export Menu Action and Ctrl+I Shortcut
expected: Generate an interface structure. File menu shows "Export Interface for GROMACS..." below a separator after "Export for GROMACS..." (Tab 1). Ctrl+I triggers the same action. Ctrl+G and Ctrl+I do not conflict.
result: pass

### 2. Export Save Dialog
expected: Click File → "Export Interface for GROMACS..." or Ctrl+I. Dialog title "Export Interface for GROMACS". Default filename "interface_slab.gro" (mode-specific). Filter "GRO Files (*.gro);;All Files (*)". Can cancel without error.
result: pass

### 3. GRO File 4-Atom Normalization
expected: Export and open .gro file. Title line "Ice/water interface (slab) exported by QuickIce". ALL molecules written as 4-atom TIP4P-ICE: OW, HW1, HW2, MW. Ice molecules: MW positions computed (not zero). Atom names: OW, HW1, HW2, MW (not O, H1, H2). Box dimensions at end match interface cell. Residues named "SOL".
result: pass

### 4. Single SOL Molecule Type
expected: Export and examine .gro and .top files. NO chain identifiers (no chain A/B). ALL residues named "SOL". .top [molecules] section has SINGLE entry: SOL {combined_count}. Combined count = ice + water molecules. NOT split into separate molecule types.
result: pass

### 5. TOP File Content
expected: Export and open .top file. Header mentions QuickIce and TIP4P-ICE. [defaults], [atomtypes], [moleculetype] name "SOL" nrexcl=3, [atoms] with 4 atoms, [settles], [virtual_sites3] with α=0.13458335, [exclusions], [system] name includes mode, [molecules] single SOL {N}, #include "interface_{mode}.itp".
result: pass
note: Self-contained, not using #include

### 6. ITP File Content
expected: Export and open .itp file. ITP is IDENTICAL to Tab 1's TIP4P-ICE force field. Copied from bundled quickice/data/tip4p-ice.itp. Defines OW, HW1, HW2, MW atom types.
result: pass
note: Identical, atomtypes commented

### 7. Export Without Generation
expected: Launch app, do NOT generate any interface structure. Press Ctrl+I or click File → "Export Interface for GROMACS...". Warning dialog appears. No crash, no exception.
result: pass

### 8. Export Success Dialog
expected: Generate and export. Information dialog "Export Complete" shows TIP4P-ICE citation, ice/water molecule counts, total count, and files generated (interface_{mode}.gro, .top, .itp).
result: pass

### 9. Mode-Specific Default Filename
expected: Generate POCKET mode interface, press Ctrl+I, default filename "interface_pocket.gro". Generate PIECE mode, press Ctrl+I, default filename "interface_piece.gro". Each mode gets its own default filename.
result: pass

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
