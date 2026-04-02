---
status: resolved
trigger: "export-dropdown-missing"
created: 2026-04-02T00:00:00Z
updated: 2026-04-02T00:15:00Z
---

## Current Focus
hypothesis: CONFIRMED - Misleading comment "# Candidate selectors (for export)" caused user to think dropdowns were export controls, not viewing controls
test: N/A - root cause identified
expecting: User expected export control separate from viewing, but dropdowns were always for viewing only
next_action: Implement fix to clarify UI or add separate export control

## Resolution
root_cause: Previous code comment "# Candidate selectors (for export)" was misleading. Dropdowns control which candidate is VIEWED in each viewer, not which is exported. Export uses left viewer's selection. User expected a separate export control after comment was removed during reorganization.
fix: 1) Added two separate menu items: "Save PDB (Left Viewer)..." and "Save PDB (Right Viewer)..." to allow exporting from either viewer. 2) Added get_selected_candidate_index_left() and get_selected_candidate_index_right() methods to view.py. 3) Added tooltips to candidate selectors in dual_viewer.py to clarify they control viewing, not exporting.
verification: Code imports successfully. All new methods exist. Tooltips added. User can now export from either left or right viewer via File menu.
files_changed: [quickice/gui/main_window.py, quickice/gui/view.py, quickice/gui/dual_viewer.py]
