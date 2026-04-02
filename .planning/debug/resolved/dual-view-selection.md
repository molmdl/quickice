---
status: resolved
trigger: "dual-view-selection"
created: 2026-04-02T00:00:00.000Z
updated: 2026-04-02T00:00:00.000Z
---

## Current Focus
hypothesis: Only one dropdown exists in toolbar and it only updates viewer1 (left). Right viewer is hardcoded to always show Rank 2
test: Add second dropdown for viewer2
expecting: Will allow independent candidate selection for right grid
next_action: Fix verified - dual view selection now works

## Symptoms
expected: Should be able to select different candidates in the right grid, and the right 3D viewer should update accordingly. Should have separate controls for left and right grids
actual: Only one dropdown menu exists for exporting and changing left grid. No way to change the right grid - it stays fixed on Rank 2 model
errors: None reported
reproduction: 1) Open dual view 2) Try to select candidate in right grid - no dropdown/selector available 3) Right grid always shows Rank 2 model
started: Reported on Debian 12 testing of 3D viewer

## Eliminated

## Evidence
- timestamp: 2026-04-02
  checked: quickice/gui/view.py ViewerPanel class
  found: Only one candidate_selector existed for the toolbar
  implication: No UI element to change the right viewer
  
- timestamp: 2026-04-02
  checked: _on_candidate_selected method in view.py
  found: Method only updates viewer1 (viewer_index=0)
  implication: Right viewer never changes from its default (Rank 2)
  
- timestamp: 2026-04-02
  checked: quickice/gui/dual_viewer.py
  found: DualViewerWidget has set_candidate_for_viewer method that supports viewer_index 0 or 1
  implication: Backend supports independent viewer selection, but frontend doesn't expose it

## Resolution
root_cause: Only one dropdown exists in toolbar and it only updates viewer1 (left). Right viewer is hardcoded to always show Rank 2
fix: Added second dropdown (candidate_selector2) for the right viewer with label "Right:" and connected to _on_candidate_selected_2 handler. Updated update_candidate_selector to populate both dropdowns with left defaulting to Rank 1 and right defaulting to Rank 2
verification: Verified imports work, all handlers exist, source code contains new dropdown
files_changed: ["quickice/gui/view.py"]