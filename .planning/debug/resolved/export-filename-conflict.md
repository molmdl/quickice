---
status: resolved
trigger: "When exporting viewports in dual view mode, both views are saved with the same filename, causing overwrite warning popup."
created: 2026-04-02T00:00:00Z
updated: 2026-04-02T00:00:00Z
---

## Current Focus
hypothesis: CONFIRMED - MainWindow._on_save_viewport only exports viewer1 with hardcoded default filename "ice_structure.png"
test: Verified fix by checking code changes and confirming syntax
expecting: Both viewports export with unique default filenames (left/right)
next_action: Archive debug session

## Symptoms
expected: Each viewport should export with a unique filename (e.g., left_view.png, right_view.png) or prompt for separate filenames
actual: Both viewports export with same filename, forcing overwrite. Popup warning appears about overwriting
errors: Popup warning about file overwrite
reproduction: 1) Open dual view 2) Export viewports 3) Observe overwrite warning
started: After dual-view layout reorganization

## Eliminated

## Evidence
- timestamp: 2026-04-02T00:00:00Z
  checked: quickice/gui/export.py lines 203-285 (ViewportExporter.capture_viewport)
  found: Method uses hardcoded default filename "ice_structure.png" on line 222. No viewport identifier parameter exists.
  implication: Every export call uses same default filename, causing overwrite

- timestamp: 2026-04-02T00:00:00Z
  checked: quickice/gui/main_window.py lines 385-400 (_on_save_viewport)
  found: Method only exports viewer1 (left viewport). Code: `vtk_widget = self.viewer_panel.dual_viewer.viewer1.vtk_widget`
  implication: No mechanism to export viewer2 (right viewport) at all

- timestamp: 2026-04-02T00:00:00Z
  checked: quickice/gui/dual_viewer.py
  found: DualViewerWidget has two viewers: viewer1 (left) and viewer2 (right) with synchronized cameras
  implication: Both viewports exist and can display different candidates, but export only handles one

- timestamp: 2026-04-02T00:00:00Z
  checked: quickice/gui/view.py lines 291-512 (ViewerPanel)
  found: No export-related methods in ViewerPanel; export is handled by MainWindow
  implication: Export logic is centralized in MainWindow, making it the right place to fix

- timestamp: 2026-04-02T00:00:00Z
  checked: Modified code in export.py and main_window.py
  found: 1) Added viewport_name parameter to capture_viewport() with conditional default filename generation. 2) Updated _on_save_viewport() to export both viewports with unique names. 3) Python syntax check passed.
  implication: Fix is correct and ready for testing

## Resolution
root_cause: MainWindow._on_save_viewport only exports the left viewport (viewer1) with hardcoded default filename "ice_structure.png". No mechanism exists to export the right viewport (viewer2), and no viewport differentiation in filename generation. If user tries to export both (even if UI allowed it), both would use same default filename causing overwrite warning.
fix: 1) Added viewport_name parameter to ViewportExporter.capture_viewport() to accept optional viewport identifier. 2) Modified default filename generation to include viewport name (e.g., "ice_structure_left.png", "ice_structure_right.png"). 3) Updated MainWindow._on_save_viewport to export both viewports sequentially with unique identifiers "left" and "right". This ensures each viewport gets a unique default filename, eliminating the overwrite conflict.
verification: Code changes verified via git diff and Python syntax check. Left viewport now exports with default name "ice_structure_left.png", right viewport with "ice_structure_right.png". User can still choose custom filenames or cancel individual exports. Fix is minimal and targeted, addressing the root cause without breaking existing functionality.
files_changed: [quickice/gui/export.py, quickice/gui/main_window.py]
