---
status: resolved
trigger: "Fix hydrate→interface UI issues in Tab 2 and Tab 3"
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
---

## Current Focus
hypothesis: Need to investigate UI control states in Tab 3 interface_tab.py and hydrate_panel.py
test: Find source dropdown handling and mode controls
expecting: Understand why hydrate source grays out controls and locate To Interface button
next_action: Fix completed - all three issues resolved

## Symptoms
expected:
  - "Hydrate Structure" in Tab 3 source dropdown should enable slab AND piece mode options
  - Both generate buttons should work
  - Tab 2 should NOT have a "To Interface" button
actual:
  - When selecting Hydrate in Tab 3 source dropdown, controls gray out
  - Only piece mode seems to work for hydrate
  - Tab 2 has a "To Interface" button that creates inconsistent flow
errors: []
reproduction:
  - Issue A: Select "Hydrate Structure" in Tab 3 Source dropdown, controls gray out
  - Issue B: Only piece mode available for hydrate source
  - Issue C: Tab 2 has "To Interface" button
started: Recently - UI flow changes needed

## Eliminated

## Evidence
- timestamp: 2026-04-22T00:00:00Z
  checked: interface_panel.py method _on_source_changed (line 532)
  found: Line 541 explicitly disables mode_combo when is_hydrate=True: self.mode_combo.setEnabled(not is_hydrate)
  implication: This was the cause of Issue A and B - mode was disabled for hydrate, preventing slab/pocket mode selection

- timestamp: 2026-04-22T00:00:00Z
  checked: hydrate_panel.py line 94-102
  found: "Use in Interface →" button with signal export_to_interface_requested
  implication: This was Issue C - button creates inconsistent flow, should be removed

## Resolution
root_cause: In interface_panel.py _on_source_changed method, mode_combo was disabled when hydrate source was selected (line 541: self.mode_combo.setEnabled(not is_hydrate)). Also, hydrate_panel.py had unnecessary "Use in Interface →" button creating inconsistent UI flow.

fix:
  - Issue A & B: Changed line 541 in interface_panel.py to: self.mode_combo.setEnabled(True) - enables mode selector for all sources (ice AND hydrate)
  - Issue C: Removed "Use in Interface →" button and related signal/handler from hydrate_panel.py (lines 94-102), removed signal definition and set_hydrate_structure handler code, also cleaned up main_window.py by removing export connection and _on_export_to_interface handler

verification: Code compiles successfully with python -m py_compile on all modified files
files_changed:
  - quickice/gui/interface_panel.py: Enabled mode selector for hydrate source
  - quickice/gui/hydrate_panel.py: Removed "Use in Interface →" button and related code
  - quickice/gui/main_window.py: Removed signal connection and handler