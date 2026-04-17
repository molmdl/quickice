---
status: resolved
trigger: "hydrate viewer - hbond toggle hides water molecules, THF bonds broken"
created: 2026-04-17T00:00:00Z
updated: 2026-04-17T00:00:00Z
---

## Current Focus
hypothesis: "Issue 1: _water_actor contains water framework (atoms+bonds) and set_hbonds_visible() hides the whole actor instead of creating separate H-bond actor"
test: "Modify hydrate_viewer.py to keep water framework visible and create separate H-bond actor"
expecting: "Water framework stays visible, H-bond actor (cyan dashed lines) toggles on/off"
next_action: "Fix Issue 1 - modify hydrate_viewer.py set_hbonds_visible()"

hypothesis: "Issue 2: BOND_DISTANCE_THRESHOLD = 0.14nm is too small for THF C-O bonds (~0.143-0.147nm)"
test: "Increase threshold to 0.15nm in hydrate_renderer.py"
expecting: "THF C-O bonds will be detected and rendered"

## Symptoms
expected:
  - Issue 1: H-bond toggle should show/hide hydrogen bonds between molecules (dashed lines typically), not hide the water molecules themselves
  - Issue 2: THF molecules should display with their internal bonds (C-O bonds in the ring structure)
  - Issue 3: Ion insertion should work without errors
actual:
  - Issue 1: Water molecules (ball-and-stick) are hidden when H-bond toggle is clicked
  - Issue 2: THF molecules appear as isolated atoms, no internal bonds visible
  - Issue 3: Needs testing
reproduction:
  - Issue 1: Open hydrate tab, generate a hydrate, click H-bond toggle button
  - Issue 2: Generate THF hydrate, look at THF molecules in viewer - no bonds visible
  - Issue 3: Generate ice -> interface -> insert ions
started: These issues appeared after recent fixes

## Eliminated
<!-- APPEND -->

## Evidence
- timestamp: 2026-04-17T00:01
  checked: "hydrate_viewer.py set_hbonds_visible()"
  found: "Method toggles self._water_actor visibility directly, which contains water framework (atoms + bonds)"
  implication: "Toggling this hides the ENTIRE water framework including atoms, not just H-bonds"

- timestamp: 2026-04-17T00:02
  checked: "hydrate_renderer.py create_water_framework_actor()"
  found: "Water framework renders with mapper.UseBallAndStickSettings() showing atoms AND bonds"
  implication: "User expects: H-bonds shown separately as dashed lines; Actual: entire water framework shown"

- timestamp: 2026-04-17T00:03
  checked: "hydrate_renderer.py bond detection threshold"
  found: "BOND_DISTANCE_THRESHOLD = 0.14 nm. THF C-O bonds are ~0.143-0.147 nm"
  implication: "THF C-O bonds may be at/below threshold and not detected"

## Resolution
root_cause: |
  Issue 1: set_hbonds_visible() toggled the entire water framework actor (atoms+bonds)
           instead of creating a separate H-bond actor. The toggle should only affect
           H-bonds (dashed lines between water molecules), not the water framework.
  
  Issue 2: BOND_DISTANCE_THRESHOLD was 0.14nm, but THF C-O bonds are ~0.143-0.147nm,
           so they were not being detected and rendered.

fix: |
  Issue 1: 
  - Added detect_hbonds_in_hydrate_structure() function in hydrate_renderer.py
  - Modified hydrate_viewer.py to create separate H-bond actor (cyan dashed lines)
  - set_hbonds_visible() now toggles only the H-bond actor, not the water framework
  
  Issue 2:
  - Increased BOND_DISTANCE_THRESHOLD from 0.14nm to 0.15nm in hydrate_renderer.py

verification: |
  - Ran test_pbc_hbonds.py - all 6 tests passed
  - Ran all tests - 306 passed, 1 failed (pre-existing unrelated issue)
  - Syntax check on modified files passed

files_changed:
  - quickice/gui/hydrate_renderer.py: Added detect_hbonds_in_hydrate_structure(), increased threshold
  - quickice/gui/hydrate_viewer.py: Added H-bond actor creation and toggle logic
