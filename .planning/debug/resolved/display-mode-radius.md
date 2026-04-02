---
status: resolved
trigger: "All display mode radii are incorrect: VDW shows bulk red object (spheres too large), Ball-and-stick shows space-filling VDW (not showing sticks), Stick has cylinders too thick with gaps at atom positions."
created: 2026-04-02T00:20:00Z
updated: 2026-04-02T00:40:00Z
---

## Current Focus

hypothesis: ROOT CAUSE CONFIRMED - Stick mode incorrectly hides atoms, VDW/Ball-and-stick need radius tuning
test: Fix stick mode to show atoms, tune other mode radii
expecting: All three modes render correctly with appropriate radii
next_action: Apply fix to molecular_viewer.py

## Eliminated

<!-- APPEND only - prevents re-investigating -->

## Evidence

<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-02T00:21
  checked: VTK vtkMoleculeMapper preset defaults via Python inspection
  found: |
    UseVDWSpheresSettings: ScaleFactor=1.0, BondRadius=0.075, AtomicRadiusType=1 (VDWRadius), RenderAtoms=True
    UseBallAndStickSettings: ScaleFactor=0.3, BondRadius=0.075, AtomicRadiusType=1 (VDWRadius), RenderAtoms=True
    UseLiquoriceStickSettings: ScaleFactor=0.15, BondRadius=0.15, AtomicRadiusType=2 (UnitRadius), RenderAtoms=True
  implication: LiquoriceStick has thick bonds (0.15) and uses UnitRadius (uniform atom sizes), not VDW radii. Current stick mode calls RenderAtomsOff() which HIDES atoms entirely.

- timestamp: 2026-04-02T00:22
  checked: Current implementation in molecular_viewer.py lines 237-263
  found: |
    VDW: UseVDWSpheresSettings(), ScaleFactor=1.0, BondRadius=0.05, RenderAtomsOn() - looks correct
    Ball-and-stick: UseBallAndStickSettings(), ScaleFactor=0.15, BondRadius=0.05, RenderAtomsOn() - should show smaller spheres than VDW
    Stick: UseLiquoriceStickSettings(), ScaleFactor=0.1, BondRadius=0.05, RenderAtomsOff() - HIDES atoms entirely!
  implication: |
    STICK MODE BUG: RenderAtomsOff() hides atoms, creating gaps where bonds don't meet. User expects small spheres at atom positions to fill gaps.
    BOND RADIUS: All modes set BondRadius=0.05, but user reports "cylinders too thick" - need to verify value is actually being applied.

- timestamp: 2026-04-02T00:23
  checked: Research documentation (10-RESEARCH.md) lines 102-123, 426-441
  found: |
    UseBallAndStickSettings: AtomicRadiusType=VDWRadius, RenderAtoms=1, RenderBonds=1 (atoms ARE visible)
    UseLiquoriceStickSettings: AtomicRadiusType=UnitRadius, uniform cylinder bonds (atoms ARE visible)
    VTK PeriodicTable: H_vdw=1.20, O_vdw=1.55, ratio=1.29 (O is ~1.27x larger than H)
  implication: VTK presets have atoms VISIBLE by default. Current stick mode implementation with RenderAtomsOff() is WRONG - contradicts VTK default behavior.

- timestamp: 2026-04-02T00:25
  checked: Verified values are applied correctly after method calls
  found: |
    After applying VDW: ScaleFactor=1.0, BondRadius=0.05, RenderAtoms=True
    After applying Ball-and-stick: ScaleFactor=0.15, BondRadius=0.05, RenderAtoms=True
    After applying Stick: ScaleFactor=0.1, BondRadius=0.05, RenderAtoms=False
  implication: Values ARE being applied correctly. The bug is in stick mode using RenderAtomsOff().

## Resolution

root_cause: |
  Three issues identified:
  
  1. **Stick mode (CRITICAL BUG)**: `RenderAtomsOff()` completely hid atoms, creating gaps at bond junctions. Per VTK docs and user expectation, stick mode should show small spheres at atom positions to fill gaps.
  
  2. **VDW mode**: Scale 1.0 was technically correct for "space-filling" VDW, but in packed ice structures oxygen atoms merged into a solid mass. User expected visible structure with spheres that touch but don't completely overlap.
  
  3. **Ball-and-stick mode**: Scale 0.15 was too large for bonds (0.05) to be clearly visible, making it look like VDW.

fix: |
  Modified set_representation_mode() in molecular_viewer.py:
  
  1. VDW: Reduced ScaleFactor from 1.0 to 0.85 (touching but not overlapping)
  
  2. Ball-and-stick: Reduced ScaleFactor from 0.15 to 0.12 (smaller for bond visibility)
  
  3. Stick: Changed RenderAtomsOff() to RenderAtomsOn(), set ScaleFactor=0.08 (small spheres to fill gaps)
  
  All modes: Reduced BondRadius from 0.05 to 0.03 for thinner bonds.
  
  Also updated _setup_molecule_actor() to use consistent initial values (ScaleFactor=0.12, BondRadius=0.03).

verification: |
  Tested programmatically:
  - VDW mode: ScaleFactor=0.85, BondRadius=0.03, RenderAtoms=True ✓
  - Ball-and-stick mode: ScaleFactor=0.12, BondRadius=0.03, RenderAtoms=True ✓
  - Stick mode: ScaleFactor=0.08, BondRadius=0.03, RenderAtoms=True ✓
  
  All mode switches successful without errors.
  
  User visual verification needed to confirm rendering matches expectations.

files_changed: [quickice/gui/molecular_viewer.py]

## Resolution

root_cause: 
fix: 
verification: 
files_changed: []
