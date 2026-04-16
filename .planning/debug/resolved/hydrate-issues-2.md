---
status: resolved
trigger: "Investigate and fix hydrate issues in QuickIce GUI v4.0"
created: 2026-04-16T00:00:00Z
updated: 2026-04-16T00:00:00Z
---

## Resolution
root_cause: |
  - Issue 1: Missing unit cell toggle UI and method in hydrate_viewer.py
  - Issue 2: BOND_DISTANCE_THRESHOLD = 0.20 nm too low to capture O-O cage bonds (~0.30 nm)
  - Issue 3: Missing None check for config in export handler

fix: |
  - Issue 1: Added set_unit_cell_visible() to hydrate_viewer.py, btn_unit_cell to hydrate_panel.py
  - Issue 2: Changed BOND_DISTANCE_THRESHOLD from 0.20 to 0.30 nm
  - Issue 3: Added config None check with warning dialog in main_window.py

files_changed:
  - quickice/gui/main_window.py
  - quickice/gui/hydrate_viewer.py
  - quickice/gui/hydrate_panel.py
  - quickice/gui/hydrate_renderer.py

verification: "Syntactic verification passed, commit e340acb"

## Symptoms
expected: |
  - Issue 1: Toggle button to show/hide unit cell box
  - Issue 2: Clean ball-and-stick rendering
  - Issue 3: Export to GROMACS works without error

actual: |
  - Issue 1: No unit cell box shown, likely no toggle button
  - Issue 2: Atoms overlap, bonds look wrong
  - Issue 3: AttributeError: 'NoneType' object has no attribute 'lattice_type'

reproduction: "Generate hydrate, click Export → GROMACS"
started: Unknown

## Evidence
- timestamp: "2026-04-16"
  checked: "main_window.py:930-952 (_on_export_hydrate_gromacs)"
  found: "Config is checked for None after result, but config itself could be None if user goes straight to export without configuring first"
  implication: "Need to guard config in _on_export_hydrate_gromacs"

- timestamp: "2026-04-16"
  checked: "hydrate_renderer.py:90 (BOND_DISTANCE_THRESHOLD)"
  found: "Threshold = 0.20 nm (typical O-H is ~0.1 nm), hydrate O-O cage bonds ~0.30 nm - too low to capture cage bonds"
  implication: "Increase threshold to 0.30 nm to correctly render O-O cage bonds"

- timestamp: "2026-04-16"
  checked: "hydrate_viewer.py - missing unit cell support"
  found: "No set_unit_cell_visible method or unit cell actor - need support matching Tab 1's molecular_viewer.py"
  implication: "Add set_unit_cell_visible to hydrate_viewer.py and btn_unit_cell to hydrate_panel.py"