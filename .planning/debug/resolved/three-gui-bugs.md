---
status: resolved
trigger: "Three GUI bugs: hbond toggle missing in hydrate tab, THF guest not inserted, ion insertion AttributeError"
created: 2026-04-16T00:00:00Z
updated: 2026-04-16T00:00:00Z
---

## Resolution Summary

### Issue 1: HBond toggle missing in hydrate tab - FIXED
**Root cause:** hydrate_panel.py toolbar was missing the btn_hbonds button that exists in tab 1.
**Fix:** 
- Added set_hbonds_visible() and get_hbonds_visible() methods to hydrate_viewer.py
- Added btn_hbonds toggle button to hydrate_panel.py toolbar
- Added _on_hbonds_toggled() handler to hydrate_panel.py

### Issue 2: THF hydrate - no guest inserted - FIXED
**Root cause:** 
- hydrate_generator.py line 103 only counted mol_type == "ch4" for guest_count
- _build_molecule_index didn't recognize THF molecules from GenIce2 output
- THF uses residue name "THF" with atoms O, CA, CA, CB, CB, H... (13 atoms)

**Fix:**
- Modified _parse_gro_result to also capture residue_names
- Updated _build_molecule_index to recognize THF by residue name
- Fixed guest_count calculation to count all non-water molecules

### Issue 3: Ion insertion AttributeError - FIXED
**Root cause:** replace_water_with_ions had early returns that returned the original InterfaceStructure instead of IonStructure.
**Fix:** Modified early returns to always return a properly typed IonStructure with na_count=0, cl_count=0.

## Evidence
- timestamp: 2026-04-16
  checked: All three issues verified with tests
  found: All fixes work correctly

## Files Changed
- quickice/gui/hydrate_viewer.py
- quickice/gui/hydrate_panel.py
- quickice/structure_generation/hydrate_generator.py
- quickice/structure_generation/ion_inserter.py

## Verification
- All 141 relevant tests pass
- Manual tests confirm all three issues are fixed
