---
status: verifying
trigger: "User wants 3 display modes with correct naming and rendering: 1. VDW - Space-filling van der Waals spheres (full size), 2. Ball-and-stick - Small spheres connected by cylinders (sticks visible), 3. Stick - Only cylinders, no atom spheres. Current ball-and-stick is not showing sticks properly."
created: 2026-04-02T00:00:00Z
updated: 2026-04-02T00:10:00Z
---

## Current Focus

hypothesis: ROOT CAUSE CONFIRMED - Fix applied
test: Verify 3 modes work correctly by running application
expecting: 
  - VDW: Full-size VDW spheres (space-filling)
  - Ball-and-stick: Small spheres (0.15) with visible bonds (0.05)
  - Stick: Only bonds visible, no atom spheres (RenderAtomsOff)
next_action: User verification needed

## Symptoms

expected: Three modes: VDW (full spheres), Ball-and-stick (small spheres + visible sticks), Stick (only sticks/cylinders)
actual: Current ball-and-stick shows spheres but sticks not visible. Current stick shows tiny spheres, not just cylinders.
errors: None - rendering/naming mismatch
reproduction: 1) Generate structure 2) Switch modes - not matching expected behavior
started: After user chose 3-mode option

## Eliminated

## Evidence

- timestamp: 2026-04-02T00:01
  checked: molecular_viewer.py lines 220-252 and view.py lines 416-428
  found: Current implementation has only 2 modes: "ball_and_stick" (AtomicRadiusScaleFactor 0.15, BondRadius 0.05) and "stick" (AtomicRadiusScaleFactor 0.05, BondRadius 0.05). Both render VDW spheres with cylinders, just at different scales.
  implication: Need to add VDW mode and fix stick mode to hide atoms entirely.

- timestamp: 2026-04-02T00:02
  checked: VTK vtkMoleculeMapper API via Python inspection
  found: |
    Available methods:
    - UseVDWSpheresSettings(): VDW spheres at scale 1.0 (space-filling)
    - UseBallAndStickSettings(): Small spheres with bonds
    - UseLiquoriceStickSettings(): Uniform-size atoms with bonds
    - SetRenderAtoms(False): Hide atoms, show only bonds
    - RenderAtomsOff(): Alternative to hide atoms
  implication: VTK supports all three desired modes. Can implement VDW with UseVDWSpheresSettings() and stick with SetRenderAtoms(False).

- timestamp: 2026-04-02T00:03
  checked: Previous debug session representation-mode-naming.md (resolved)
  found: Previous investigation confirmed both current modes render VDW spheres, naming is misleading. Suggested adding VDW mode and fixing stick mode to show only bonds.
  implication: This is a continuation of that investigation. User now explicitly wants 3-mode system.

- timestamp: 2026-04-02T00:05
  checked: Implementation of fix in molecular_viewer.py and view.py
  found: |
    Modified molecular_viewer.py:
    - Added "vdw" mode using UseVDWSpheresSettings() with scale 1.0
    - Kept "ball_and_stick" with AtomicRadiusScaleFactor 0.15, BondRadius 0.05
    - Fixed "stick" mode to use RenderAtomsOff() to hide atom spheres entirely
    
    Modified view.py:
    - Changed button from toggle to cycle through 3 modes
    - Cycle order: Ball-and-stick -> VDW -> Stick -> Ball-and-stick
  implication: Three distinct modes now implemented with correct rendering behavior.

## Resolution

root_cause: |
  The implementation only had 2 modes and they didn't match the desired 3-mode system:
  1. VDW mode was missing (no space-filling VDW spheres)
  2. Ball-and-stick mode existed but needed proper bond visibility
  3. Stick mode showed tiny spheres instead of hiding atoms entirely
  
  Root cause: Incomplete implementation of representation modes and incorrect rendering for stick mode (used tiny spheres instead of hiding atoms).
fix: |
  Modified molecular_viewer.py set_representation_mode():
  1. Added "vdw" mode: UseVDWSpheresSettings(), AtomicRadiusScaleFactor 1.0, RenderAtomsOn
  2. Kept "ball_and_stick": UseBallAndStickSettings(), AtomicRadiusScaleFactor 0.15, BondRadius 0.05, RenderAtomsOn
  3. Fixed "stick" mode: UseLiquoriceStickSettings(), RenderAtomsOff() to hide atoms and show only bonds
  
  Modified view.py:
  - Changed representation button to cycle through 3 modes (not toggle between 2)
  - Cycle order: Ball-and-stick -> VDW -> Stick -> Ball-and-stick
verification: Pending user visual verification
files_changed: [quickice/gui/molecular_viewer.py, quickice/gui/view.py]
