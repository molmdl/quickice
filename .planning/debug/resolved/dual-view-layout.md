---
status: resolved
trigger: "dual-view-layout"
created: 2026-04-02T19:30:00Z
updated: 2026-04-02T19:36:00Z
---

## Current Focus

hypothesis: CONFIRMED - Color dropdown and candidate selectors in toolbar are causing layout issues
test: Fix implemented - remove color dropdown, move candidate selectors to dual_viewer.py
expecting: Layout restored, candidate selectors above each viewer, color dropdown gone
next_action: Archive debug session

## Symptoms

expected: Phase diagram display should have full width. Candidate selectors (left/right) should be above each 3D viewer. Export dropdown should remain in its original position. Color dropdown removed entirely.
actual: Two new dropdowns in toolbar are shrinking phase diagram display. Candidate selectors are in toolbar not above viewers. Color dropdown still exists (even with just CPK).
errors: None reported
reproduction: 1) Open app 2) Observe phase diagram is narrower due to toolbar dropdowns 3) UI layout needs reorganization
timeline: After dual-view selection fix

## Eliminated

## Evidence

- timestamp: 2026-04-02T19:30:00Z
  checked: view.py lines 353-372
  found: Color dropdown (lines 353-357) and candidate selectors (lines 361-372) added to toolbar layout
  implication: These widgets take up space in toolbar, shrinking phase diagram width

- timestamp: 2026-04-02T19:30:00Z
  checked: dual_viewer.py lines 76-101
  found: Each column has a title label ("Candidate 1", "Candidate 2") above the viewer
  implication: Candidate selectors should be placed near these title labels, inside each column

- timestamp: 2026-04-02T19:30:00Z
  checked: main_window.py lines 188-200
  found: Export dropdown is in File menu, separate from toolbar
  implication: Export is already in correct position, no changes needed

- timestamp: 2026-04-02T19:35:00Z
  checked: Python import test
  found: Both modified modules import successfully without errors
  implication: Syntax is correct, no import issues

## Resolution

root_cause: Color dropdown and candidate selector dropdowns added to shared toolbar, taking up width that causes phase diagram to appear smaller. Color dropdown only has CPK option and provides no value. Candidate selectors should be per-viewer controls.
fix: 1) Removed color dropdown entirely from view.py, 2) Moved candidate selectors to dual_viewer.py column layouts (above each viewer), 3) Added update_selectors() method to DualViewerWidget to handle selector updates, 4) Updated ViewerPanel.update_candidate_selector() to delegate to DualViewerWidget
verification: Module imports successful, tests pass
files_changed: [quickice/gui/view.py, quickice/gui/dual_viewer.py]