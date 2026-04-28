---
status: resolved
trigger: "Missing menu shortcut labels for Ctrl-E and ion export"
created: 2026-04-28
updated: 2026-04-28T10:40:00Z
---

## Current Focus

hypothesis: CONFIRMED - Issues identified and fixes ready to apply
test: Examined _setup_shortcuts() and _create_menu_bar() methods in main_window.py
expecting: Fix by adding setShortcut() to menu items and removing redundant window-level actions
next_action: Apply fixes to main_window.py and help_dialog.py

## Evidence

- timestamp: 2026-04-28T10:30:00Z
  checked: main_window.py _setup_shortcuts() method (lines 246-274)
  found: Ctrl-E shortcut defined as window-level QAction (line 271-274) but NOT connected to menu item
  implication: Shortcut works but doesn't show in menu because it's not associated with the QAction used in menu

- timestamp: 2026-04-28T10:31:00Z
  checked: main_window.py _create_menu_bar() method (lines 276-343)
  found: |
    Line 328-329: export_hydrate_gromacs_action = file_menu.addAction("Export Hydrate for GROMACS...")
    - NO setShortcut() call for this action
    
    Line 334-335: export_ion_gromacs_action = file_menu.addAction("Export Ions for GROMACS...")
    - NO setShortcut() call for this action
    
    Other menu items HAVE shortcuts: save_pdb_left_action.setShortcut("Ctrl+S") (line 289)
  implication: Both hydrate and ion export menu items are missing shortcut labels

- timestamp: 2026-04-28T10:32:00Z
  checked: help_dialog.py keyboard shortcuts section (lines 63-78)
  found: Help dialog does NOT list Ctrl-E for hydrate export or any shortcut for ion export
  implication: Documentation also needs updating

## Root Cause

**Issue 1 (Ctrl-E for hydrate export):**
- `_setup_shortcuts()` creates a window-level QAction with Ctrl+E shortcut (lines 271-274)
- `_create_menu_bar()` creates menu item "Export Hydrate for GROMACS..." but doesn't assign the shortcut to this QAction
- The shortcut works (via window action) but doesn't appear in the menu because the menu QAction doesn't have it

**Issue 2 (Ion export missing shortcut):**
- `_create_menu_bar()` creates menu item "Export Ions for GROMACS..." (lines 334-335) without any shortcut
- No shortcut is defined anywhere for ion export functionality

## Resolution

root_cause: |
  Issue 1 (Ctrl-E for hydrate export):
  - _setup_shortcuts() created window-level QAction with Ctrl+E shortcut (lines 271-274)
  - _create_menu_bar() created menu item without shortcut assignment
  - Shortcut worked but didn't appear in menu because menu QAction lacked setShortcut()
  
  Issue 2 (Ion export missing shortcut):
  - _create_menu_bar() created menu item "Export Ions for GROMACS..." without any shortcut
  - No shortcut was defined anywhere for ion export functionality

fix: |
  1. Removed redundant window-level Ctrl+E shortcut from _setup_shortcuts() (removed lines 269-274)
  2. Added export_hydrate_gromacs_action.setShortcut("Ctrl+E") in _create_menu_bar()
  3. Added export_ion_gromacs_action.setShortcut("Ctrl+J") in _create_menu_bar()
  4. Updated help_dialog.py keyboard shortcuts section to document both shortcuts
  5. Updated help_dialog.py workflow section to mention all tabs including ion export

verification: |
  Syntax check passed for both files:
  - main_window.py: Syntax OK
  - help_dialog.py: Syntax OK
  
  Changes verified:
  1. Removed redundant window-level Ctrl+E shortcut from _setup_shortcuts() (lines 269-274 removed)
  2. Added export_hydrate_gromacs_action.setShortcut("Ctrl+E") at line 322
  3. Added export_ion_gromacs_action.setShortcut("Ctrl+J") at line 329
  4. Updated help_dialog.py keyboard shortcuts section (lines 73-74)
  5. Updated help_dialog.py workflow section with all 4 tabs (lines 100-109)

  The menu items now have proper shortcuts that will display in the menu bar.
  - "Export Hydrate for GROMACS..." now shows "Ctrl+E" in menu
  - "Export Ions for GROMACS..." now shows "Ctrl+J" in menu

files_changed:
  - quickice/gui/main_window.py
  - quickice/gui/help_dialog.py

## Fix Plan

1. **Remove redundant window-level shortcut** in `_setup_shortcuts()`: Remove lines 269-274 (Ctrl+E action)
2. **Add shortcut to hydrate export menu item**: Add `export_hydrate_gromacs_action.setShortcut("Ctrl+E")` after line 329
3. **Add shortcut to ion export menu item**: Add `export_ion_gromacs_action.setShortcut("Ctrl+J")` after line 335 (J = "Ion" mnemonic, adjacent to I for Interface)
4. **Update help dialog**: Add both shortcuts to the keyboard shortcuts list in help_dialog.py

## Evidence

- timestamp: 2026-04-28T10:30:00Z
  checked: main_window.py _setup_shortcuts() method (lines 246-274)
  found: Ctrl-E shortcut defined as window-level QAction (line 271-274) but NOT connected to menu item
  implication: Shortcut works but doesn't show in menu because it's not associated with the QAction used in menu

- timestamp: 2026-04-28T10:31:00Z
  checked: main_window.py _create_menu_bar() method (lines 276-343)
  found: |
    Line 328-329: export_hydrate_gromacs_action = file_menu.addAction("Export Hydrate for GROMACS...")
    - NO setShortcut() call for this action
    
    Line 334-335: export_ion_gromacs_action = file_menu.addAction("Export Ions for GROMACS...")
    - NO setShortcut() call for this action
    
    Other menu items HAVE shortcuts: save_pdb_left_action.setShortcut("Ctrl+S") (line 289)
  implication: Both hydrate and ion export menu items are missing shortcut labels

## Eliminated

- hypothesis: Ctrl-E shortcut not working
  evidence: Shortcut IS defined in _setup_shortcuts() and works, just not shown in menu
  timestamp: 2026-04-28T10:31:00Z

## Symptoms

### Issue 1: Missing menu shortcut label for Ctrl-E
expected: Ctrl-E shortcut should show in menu with proper label
actual: Shortcut works but no label shown in menu
errors: None (functional but UI issue)
reproduction: Open menu, look for Ctrl-E shortcut label
started: Unknown

### Issue 2: Missing shortcut and menu label for ion export
expected: Ion export should have keyboard shortcut and menu label
actual: No shortcut or menu label for ion export functionality
errors: None (missing feature)
reproduction: Try to find ion export in menu or keyboard shortcut
started: Unknown

## Investigation Plan

1. Check main_window.py _setup_shortcuts() method for Ctrl-E definition
2. Check _create_menu_bar() for shortcut labels
3. Check if ion export has any shortcut defined
4. Check QAction setup for proper QKeySequence and text display
5. Fix: Add proper shortcut labels to menu items

## Key Areas to Check
- quickice/gui/main_window.py:
  - _setup_shortcuts() method
  - _create_menu_bar() method
  - Any QAction creation for export functions
  - Specifically look for:
    - Ctrl-E shortcut (what does it do?)
    - Ion export action (IonGROMACSExporter)
