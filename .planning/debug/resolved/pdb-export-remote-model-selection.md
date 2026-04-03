---
status: resolved
trigger: "pdb-export-remote-model-selection"
created: 2026-04-04T00:00:00Z
updated: 2026-04-04T00:00:02Z
---

## Current Focus

hypothesis: CONFIRMED - Model selection dropdowns are only created inside DualViewerWidget, which is never instantiated when VTK unavailable on remote
test: Reviewed view.py lines 357-374 and 532-548
expecting: Find alternative dropdown when VTK disabled
next_action: Implement fix - add standalone candidate selectors for remote mode

## Symptoms

expected: User should be able to select which model to export even when 3D viewer is disabled on remote
actual: Only the first model gets exported via left/right PDB export buttons, no way to select other models
errors: No error messages - the model selection dropdown is disabled together with the 3D viewer on remote
reproduction: Every time on remote when 3D viewer unavailable. Issue does not occur on local where 3D viewer works.
started: Never worked on remote, always been this way

## Eliminated

## Evidence

- timestamp: 2026-04-04T00:00:00Z
  checked: view.py lines 19-34 (_VTK_AVAILABLE detection)
  found: VTK is disabled when localhost in DISPLAY env var (SSH X11 forwarding)
  implication: _VTK_AVAILABLE = False on remote SSH

- timestamp: 2026-04-04T00:00:00Z
  checked: view.py lines 357-374 (ViewerPanel._setup_ui)
  found: When VTK unavailable, creates fallback QLabel message, sets dual_viewer = None
  implication: No DualViewerWidget created, so no candidate_selector1/2 dropdowns exist

- timestamp: 2026-04-04T00:00:00Z
  checked: view.py lines 532-548 (get_selected_candidate_index_left/right)
  found: Returns 0 when dual_viewer is None
  implication: Always exports first candidate on remote

- timestamp: 2026-04-04T00:00:00Z
  checked: dual_viewer.py lines 84-88, 104-108
  found: candidate_selector1 and candidate_selector2 are QComboBox inside DualViewerWidget
  implication: Dropdowns only exist when VTK available - they're part of the 3D viewer widget

- timestamp: 2026-04-04T00:00:00Z
  checked: main_window.py lines 370-411 (_on_save_pdb_left/right)
  found: Calls viewer_panel.get_selected_candidate_index_left/right() to get selection
  implication: On remote, these return 0 (first candidate) always

## Resolution

root_cause: Model selection dropdowns (candidate_selector1, candidate_selector2) are components of DualViewerWidget, which is never instantiated when VTK is unavailable on remote SSH. The fallback UI only shows a message label without any selector widgets, so users have no way to choose which candidate to export.
fix: Added standalone candidate selector dropdowns (standalone_selector_left, standalone_selector_right) to ViewerPanel that are always created. When VTK is unavailable, these are shown in a selector row above the fallback message. When VTK is available, they are hidden and the DualViewerWidget's internal selectors are used. Updated get_selected_candidate_index_left/right methods to return the correct selection based on VTK availability.
verification: |
  1. Import test passed - view.py imports without errors
  2. MainWindow import passed - main_window.py imports without errors
  3. Logic test passed - model selection dropdown logic works correctly:
     - Left selector defaults to Rank 1 (index 0)
     - Right selector defaults to Rank 2 (index 1)
     - Items are populated correctly with "Rank X (phase_id)" format
files_changed: [quickice/gui/view.py]
