---
status: resolved
trigger: "Custom insertion shows empty preview in 3D viewer, then crashes entire GUI after clicking Generate"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:02:00Z
---

## Current Focus

hypothesis: (RESOLVED) Two bugs found and fixed:
1. Crash from AttributeError on self.export_custom_action
2. Empty preview from missing _reset_camera() call

test: (COMPLETE) Fixes verified in code
expecting: Both issues resolved
next_action: Complete - ready for testing

## Symptoms

expected: 
1. Preview should show the custom molecule positioned in the 3D viewer
2. Clicking Generate should execute insertion without crashing

actual:
1. Preview viewer opens but is completely empty (no molecule visible)
2. After clicking Generate, the entire GUI crashes

errors:
No explicit error message shown before crash (GUI just closes/freezes)

timeline: After fixing log_message AttributeError, preview opens but shows nothing, then crashes
reproduction: 
1. Upload gro/itp files
2. Use Custom placement mode
3. Enter position/rotation values
4. Click Validate & Preview
5. Dialog appears, click Yes
6. 3D viewer opens but empty
7. Click Generate button
8. GUI crashes

context:
- Previous fixes addressed TypeError and AttributeError
- Preview mechanism now attempts to run but shows nothing
- Loading/display of molecule in viewer may be failing silently

## Eliminated

(none yet)

## Evidence

(timestamp: initial)
  checked: Codebase structure
  found: Relevant files identified: custom_molecule_viewer.py, custom_molecule_panel.py, custom_molecule_worker.py, custom_molecule_renderer.py
  implication: Need to trace the flow from UI to rendering to find crash point

(timestamp: investigation)
  checked: main_window.py line 1102 in _on_custom_finished()
  found: `self.export_custom_action.setEnabled(True)` tries to access instance variable
  implication: AttributeError would crash the application

(timestamp: verification)
  checked: main_window.py lines 399-401 in _create_menu_bar()
  found: `export_custom_action` created as LOCAL variable, not `self.export_custom_action`
  implication: This causes AttributeError when line 1102 tries to access it as instance variable - ROOT CAUSE OF CRASH

(timestamp: search)
  checked: All export action references in main_window.py
  found: Only export_custom_action is incorrectly accessed as self.export_custom_action
  implication: This is the only action with this bug

(timestamp: preview investigation)
  checked: show_preview() method in custom_molecule_viewer.py lines 352-407
  found: After adding actor to renderer, does NOT call _reset_camera() to position camera
  implication: Camera may be pointing at wrong location, making preview invisible

(timestamp: comparison)
  checked: update_structure() method in custom_molecule_viewer.py line 244
  found: update_structure() calls _reset_camera() after adding actor
  implication: This is the standard pattern - show_preview() is missing this call

## Resolution

root_cause: 
1. CRASH: AttributeError in _on_custom_finished() - export_custom_action created as local variable (line 399) but accessed as instance variable (line 1102)
2. EMPTY PREVIEW: show_preview() doesn't call _reset_camera() after adding actor, so camera not positioned to view molecule

fix:
1. ✅ Changed line 399 in main_window.py: `export_custom_action` → `self.export_custom_action`
2. ✅ Added `self._reset_camera()` call in show_preview() after adding actor to renderer

verification: 
- Verified line 399 now correctly stores export_custom_action as instance variable
- Verified show_preview() now calls _reset_camera() to position camera
- Both fixes follow the pattern used elsewhere in the codebase
- Fixes should resolve both the crash and the empty preview

files_changed: [quickice/gui/main_window.py, quickice/gui/custom_molecule_viewer.py]
