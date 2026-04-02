---
status: investigating
trigger: "export-dropdown-missing"
created: 2026-04-02T00:00:00Z
updated: 2026-04-02T00:00:00Z
---

## Current Focus
hypothesis: User expects a separate dropdown to control which candidate to export, independent of viewing selection. Currently, export is tied to left viewer's selection only.
test: Verify if candidate selectors are properly labeled and functional, check if export should allow choosing from either viewer
expecting: Find if this is a misunderstanding or missing functionality
next_action: Test the current UI to see how candidate selectors work and if export is functional

## Symptoms
expected: Should have a separate export dropdown or button to export the current view/model
actual: Export dropdown is missing. The left dropdown only selects which model to view, not export
errors: None reported
reproduction: 1) Open app 2) Look for export dropdown - not found 3) Left dropdown only changes viewed model
timeline: After dual-view layout reorganization fix

## Eliminated

## Evidence

- timestamp: 2026-04-02T00:00:00Z
  checked: git commit 8049450 (dual-view layout reorganization)
  found: Candidate selectors moved from toolbar to dual_viewer columns. No "export dropdown" existed - exports are in File menu.
  implication: User may be confused about what changed or expecting different functionality

- timestamp: 2026-04-02T00:00:00Z
  checked: main_window.py lines 188-200, 354-373
  found: Export actions are in File menu (Save PDB, Save Diagram, Save Viewport). get_selected_candidate_index() uses left viewer's selector for export.
  implication: Export uses left selector only, no way to export from right viewer

- timestamp: 2026-04-02T00:00:00Z
  checked: dual_viewer.py lines 84-87, 104-106, 297-323
  found: candidate_selector1 and candidate_selector2 are dropdowns above each viewer, control which candidate is displayed
  implication: These control viewing, not exporting. User may expect export control.

## Resolution
root_cause:
fix:
verification:
files_changed: []
