---
status: verifying
trigger: "Investigate issue: sphere-size-tuning"
created: 2026-04-02T00:00:00Z
updated: 2026-04-02T00:15:00Z
---

## Current Focus

hypothesis: ROOT CAUSE CONFIRMED - Fix applied
test: User needs to visually verify by running application
expecting: 
  - Ball-and-stick: smaller spheres (0.15), thin bonds (0.05)
  - Stick: tiny atoms (0.05), thin bonds (0.05), O/H size distinction maintained
next_action: Archive session after user confirms fix works

## Symptoms

expected: Ball-and-stick should show smaller spheres (0.15-0.2) with visible bonds. Stick should show even smaller points (0.05 or less). Both should reveal hydrogen bonds clearly.
actual: After fix, spheres still too thick. Cylinders thicker than spheres. One mode shows pure red thick object with no visible detail. Cannot see hydrogen bonds.
errors: None reported
reproduction: 1) Generate structure 2) Switch to ball-and-stick - observe spheres still too thick 3) Switch to stick - one mode shows pure red thick object 4) Cannot verify hydrogen bonds
started: After previous fix (AtomicRadiusScaleFactor 0.3/0.1)

## Eliminated

<!-- APPEND only - prevents re-investigating -->

## Evidence

- timestamp: 2026-04-02T00:01
  checked: molecular_viewer.py lines 234-241
  found: "Ball-and-stick: UseBallAndStickSettings() + SetAtomicRadiusScaleFactor(0.3). Stick: UseLiquoriceStickSettings() + SetAtomicRadiusScaleFactor(0.1)"
  implication: "Values 0.3 and 0.1 are being applied, but user reports still too thick. Need to investigate VTK's interpretation of these scale factors."

- timestamp: 2026-04-02T00:02
  checked: Research document (10-RESEARCH.md) lines 117-122
  found: "UseLiquoriceStickSettings() sets AtomicRadiusType=UnitRadius (uniform radius). Also found SetBondRadius(0.075) for bond thickness - NOT being used in current implementation."
  implication: "BondRadius not set - may explain why cylinders are too thick. UnitRadius may cause uniform size (pure red object)."

- timestamp: 2026-04-02T00:03
  checked: VTK default values via Python inspection
  found: |
    BallAndStick defaults: AtomicRadiusScaleFactor=0.3, BondRadius=0.075, AtomicRadiusType=VDWRadius
    LiquoriceStick defaults: AtomicRadiusScaleFactor=0.15, BondRadius=0.15, AtomicRadiusType=UnitRadius
  implication: |
    ROOT CAUSE IDENTIFIED: 
    1. LiquoriceStick mode has BondRadius=0.15 (default), but we set AtomicRadiusScaleFactor=0.1. BondRadius > AtomicRadiusScaleFactor means cylinders thicker than spheres!
    2. UnitRadius in stick mode means all atoms (O and H) render at same size, explaining "pure red thick object".
    3. We never call SetBondRadius() - cylinders use default thickness.

## Resolution

root_cause: |
  Two issues identified:
  1. BondRadius was never set - defaults caused cylinders to be too thick. In LiquoriceStick mode, default BondRadius=0.15 was larger than AtomicRadiusScaleFactor=0.1, causing "cylinders thicker than spheres".
  2. Stick mode used UnitRadius (all atoms same size) causing "pure red thick object" - no distinction between O and H atoms.
fix: |
  Modified molecular_viewer.py to:
  1. Set explicit BondRadius values for both modes (0.05)
  2. Reduced AtomicRadiusScaleFactor: ball-and-stick 0.3→0.15, stick 0.1→0.05
  3. Switched stick mode to VDWRadius (instead of UnitRadius) to maintain O/H size distinction
  4. Updated both _setup_molecule_actor() and set_representation_mode()
verification: Pending user visual verification
files_changed: [quickice/gui/molecular_viewer.py]
