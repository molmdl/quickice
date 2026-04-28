---
status: active
trigger: "Multiple minor issues: atom name mismatches in GROMACS export + missing shortcuts for ion export + IonPanel AttributeError"
created: 2026-04-28
updated: 2026-04-28
---

## Current Focus
Investigating multiple related issues in QuickIce GUI and export functionality.

## Symptoms

### Issue 1: Atom name mismatch for ice -> interface GROMACS export
expected: Atom names in .gro file should match .itp file (e.g., OW, HW1, HW2, MW for TIP4P-ICE)
actual: Atom names may not match between .gro and .itp files, causing grompp warnings
errors: Likely "atom name mismatch" warnings from grompp
reproduction: Generate ice structure -> Export as Interface GROMACS -> Check .gro vs .itp atom names
started: Unknown

### Issue 2: Atom name mismatch for hydrate -> interface (and with ion)
expected: Atom names consistent between .gro, .itp, and .top files
actual: Atom name mismatches in export output (examples in ./tmp/)
errors: grompp warnings about atom name mismatches
reproduction: Generate hydrate (sI + CH4) -> Export as Interface GROMACS -> Check output in tmp/
started: Unknown

Note: User says "no problem for ice -> interface -> ion gromacs export" - so the issue is specifically with:
- ice -> interface (direct)
- hydrate -> interface
- hydrate -> interface -> ion

### Issue 3: Missing menu shortcut label for Ctrl-E
expected: Ctrl-E shortcut should show in menu with proper label
actual: Shortcut works but no label shown in menu
errors: None (functional but UI issue)
reproduction: Open menu, look for Ctrl-E shortcut label
started: Unknown

### Issue 4: Missing shortcut and menu label for ion export
expected: Ion export should have keyboard shortcut and menu label
actual: No shortcut or menu label for ion export functionality
errors: None (missing feature)
reproduction: Try to find ion export in menu or keyboard shortcut
started: Unknown

### Issue 5: AttributeError: 'IonPanel' object has no attribute 'hide_planeholder'
expected: No attribute errors when using IonPanel
actual: AttributeError raised but may have no actual effect
errors: `AttributeError: 'IonPanel' object has no attribute 'hide_planeholder'`
reproduction: Use IonPanel functionality, check logs for error
started: Unknown
note: User says this has no actual effect but may worry users

## Investigation Plan

1. Check GROMACS export code for atom naming (gromacs_writer.py)
2. Compare .gro output with .itp definitions for interface exports
3. Check main_window.py for shortcut definitions (Ctrl-E, ion export)
4. Check IonPanel class for hide_planeholder attribute
5. Fix issues found

## Output Files for Reference
- ./tmp/interface_slab.gro (atom names: OW, HW1, HW2, MW)
- ./tmp/interface_slab.itp (atom names: OW, HW1, HW2, MW)
- ./tmp/interface_slab.top (references tip4p-ice.itp)
- ./tmp/hydrate_sI_ch4_2x2x2.gro (atom names: OW, HW1, HW2, MW + C, H)
- ./tmp/hydrate_sI_ch4_2x2x2.top (references tip4p-ice.itp and ch4.itp)
