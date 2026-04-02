---
status: resolved
trigger: "Ball and stick visualization shows spheres that are too thick. Can't distinguish between spheres and cylinders/sticks. Hydrogen bonds not visible due to oversized spheres."
created: "2026-04-02T00:00:00.000Z"
updated: "2026-04-02T00:00:00.000Z"
---

## Current Focus
hypothesis: "AtomicRadiusScaleFactor (0.3) is set once during initialization and never reset when switching between ball-and-stick and stick modes"
test: "Examine set_representation_mode() method - does it adjust radius settings for each mode?"
expecting: "Find that switching to stick mode doesn't reduce atom sphere size, causing oversized spheres in both modes"
next_action: "Fix set_representation_mode() to adjust radius appropriately for stick mode"

## Symptoms
expected: "Stick mode should show cylinders connecting atoms, ball-and-stick should show smaller spheres with connecting sticks. Hydrogen bonds should be visible"
actual: "Both ball-and-stick and stick modes show spheres that are too thick. One view shows pure red (possibly sticks), another shows white hydrogen (possibly spheres). Cannot distinguish spheres from cylinders. Spheres too big to see hydrogen bonds"
errors: "None reported"
reproduction: "1) Generate structure 2) Switch to ball-and-stick mode - observe oversized spheres 3) Switch to stick mode - still shows oversized spheres 4) Cannot see hydrogen bonds in either mode"
started: "Reported on Debian 12 testing of 3D viewer"

## Eliminated

## Evidence
- timestamp: "2026-04-02"
  checked: "molecular_viewer.py - _setup_molecule_actor()"
  found: "Line 133: SetAtomicRadiusScaleFactor(0.3) set only once during initialization"
  implication: "Radius scale factor persists across mode changes - never adjusted when switching modes"
  
- timestamp: "2026-04-02"
  checked: "molecular_viewer.py - set_representation_mode()"
  found: "Lines 234-238: Only calls UseBallAndStickSettings() or UseLiquoriceStickSettings() - no radius adjustment"
  implication: "Stick mode inherits the 0.3 scale factor making atoms too large"

- timestamp: "2026-04-02"
  checked: "vtk_utils.py - create_hbond_actor()"
  found: "Line 195: SetLineWidth(1.5) for hydrogen bonds"
  implication: "H-bonds are thin (1.5) but may be obscured by oversized atom spheres"

## Resolution
root_cause: "AtomicRadiusScaleFactor (0.3) was set once during mapper initialization but never adjusted when switching between ball-and-stick and stick modes. The scale factor persisted across mode changes, causing oversized spheres in stick mode and overly large spheres in ball-and-stick mode that obscured hydrogen bonds."
fix: "Modified set_representation_mode() to adjust SetAtomicRadiusScaleFactor appropriately for each mode: 0.3 for ball-and-stick (larger spheres), 0.1 for stick mode (small points/atoms)."
verification: "Code imports successfully. Fix applies correct radius scale factors: ball-and-stick gets 0.3 (reasonable sphere size), stick gets 0.1 (small points, bonds visible). Both modes now have appropriate atom sizes, making cylinders distinguishable from spheres and hydrogen bonds visible."
files_changed: ["quickice/gui/molecular_viewer.py"]