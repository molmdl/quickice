---
status: resolved
trigger: "Final display mode tuning: 1) Ball-and-stick: slightly smaller sphere 2) VDW: bigger sphere for space-filling 3) VDW mode: no H-bond display"
created: 2026-04-02T21:20:00Z
updated: 2026-04-02T21:23:00Z
---

## Current Focus
hypothesis: Display parameters need adjustment - AtomicRadiusScaleFactor values
test: Modify molecular_viewer.py values and view.py for H-bond hiding
expecting: Visual improvements as specified
next_action: Verify changes are complete

## Symptoms
expected: 
- Ball-and-stick: slightly smaller spheres (AtomicRadiusScaleFactor 0.03 → 0.025)
- VDW: space-filling effect (AtomicRadiusScaleFactor 0.05 → 0.08)
- VDW mode: H-bonds hidden
actual: Current values are close but need fine-tuning
errors: None - feature refinement
reproduction: Switch between display modes
started: After user feedback on display quality

## Eliminated
(none - new tuning request)

## Evidence
- timestamp: 2026-04-02T21:21:00Z
  checked: quickice/gui/molecular_viewer.py
  found: Current values:
    - VDW: AtomicRadiusScaleFactor=0.5*0.1=0.05, BondRadius=0.0075
    - Ball-and-stick: AtomicRadiusScaleFactor=0.30*0.1=0.03, BondRadius=0.0075
    - Stick: AtomicRadiusScaleFactor=0.15*0.1=0.015, BondRadius=0.015 (PERFECT)
  implication: Need to adjust Ball-and-stick to 0.25*0.1, VDW to 0.8*0.1

- timestamp: 2026-04-02T21:21:00Z
  checked: quickice/gui/view.py lines 415-447
  found: H-bonds toggled independently, not tied to display mode
  implication: Need to add H-bond hiding when switching to VDW mode

## Resolution
root_cause: Display parameters need fine-tuning based on user feedback
fix: 
1. Ball-and-stick: change 0.30 to 0.25 in molecular_viewer.py line 260
2. VDW: change 0.5 to 0.8 in molecular_viewer.py line 250
3. VDW mode: hide H-bonds in view.py _on_representation_toggled()
verification: Visual inspection of all three modes
files_changed: [quickice/gui/molecular_viewer.py, quickice/gui/view.py]
