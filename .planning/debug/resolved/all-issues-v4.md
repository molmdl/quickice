---
status: resolved
trigger: "4 issues: no hydrate type in Interface Builder, ion insertion error, no keyboard shortcut for hydrate export, no tooltip for ion insertion"
created: '2026-04-19T00:00:00Z'
updated: '2026-04-19T00:00:00Z'
---

## ROOT CAUSE FOUND

### Issue 1 - Hydrate type in Interface Builder (Tab 3)
- **Root Cause**: Missing source type selector in Tab 3
- **Fix**: Added Source dropdown with two options:
  - "Ice Candidate" - existing behavior (uses Tab 1 ice)
  - "Hydrate Structure" - uses last Tab 2 hydrate

### Issue 2 - Ion insertion error  
- **Root Cause**: InterfaceStructure lacks molecule_index. When empty, insert_ions() found 0 water, returned 0 ions.
- **Secondary Issue**: _build_molecule_index_from_structure() grouped water as single entry (1 instead of water_nmolecules)
- **Fix**: Modified to create individual MoleculeIndex entries per molecule

### Issue 3 - No keyboard shortcut
- **Root Cause**: No Ctrl+E shortcut defined in _setup_shortcuts()
- **Fix**: Added Ctrl+E action in main_window.py _setup_shortcuts()

### Issue 4 - No tooltips
- **Root Cause**: ion_panel.py missing tooltips on all controls
- **Fix**: Added tooltips to concentration, ion count, volume, insert button

## VERIFICATION

- Issue 2: Tested with 50 ice + 50 water InterfaceStructure at 0.6M → 8 Na+ + 7 Cl- (from 10 calculated)
- Issues 3-4: Compilation verified

## FILES CHANGED

- quickice/gui/interface_panel.py: Added Source dropdown, modified generate flow
- quickice/structure_generation/ion_inserter.py: Added _build_molecule_index_from_structure() 
- quickice/gui/ion_panel.py: Added tooltips to all controls
- quickice/gui/main_window.py: Added Ctrl+E shortcut, hydrate generate handler