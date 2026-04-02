---
status: resolved
trigger: "Previous fix still has incorrect radii: VDW bulk red, ball-and-stick bond thicker than sphere, stick needs matching radii"
created: 2026-04-02T20:54:00Z
updated: 2026-04-02T21:03:00Z
---

## Current Focus

hypothesis: ROOT CAUSE CONFIRMED - Our custom radius values are too small compared to VTK defaults; scale factors are much smaller than VTK's built-in presets causing visibility issues
test: Compare our values (scale 0.12/0.85/0.08, bond 0.03) against VTK defaults (scale 0.30/1.0/0.15, bond 0.075/0.15)
expecting: Using VTK defaults or close to them will fix all three modes
next_action: Implement fix using VTK default radius values

## Symptoms

expected:
- VDW: Space-filling spheres that touch neighbors but don't completely overlap into solid mass
- Ball-and-stick: Small spheres with thin bonds (bond radius ≤ sphere scale)
- Stick: Cylinders with small spheres at atom positions, cylinder radius = sphere scale

actual:
- VDW: Bulk of red (spheres way too large, overlapping into solid)
- Ball-and-stick: Bond thicker than sphere (opposite of expected)
- Stick: Need to match cylinder and sphere radii

errors: None
reproduction: 1) Generate structure 2) Cycle through display modes 3) Observe incorrect sizing
started: After previous radius fix (scale 0.85/0.12/0.08, bond 0.03)

## Eliminated

<!-- APPEND only -->

## Evidence

<!-- APPEND only -->

- timestamp: 2026-04-02T20:55:00Z
  checked: molecular_viewer.py lines 237-265 (set_representation_mode)
  found: Current values - VDW: scale 0.85, ball_and_stick: scale 0.12, stick: scale 0.08, all with bond 0.03
  implication: Bond radius 0.03 is constant across modes; only atomic scale changes

- timestamp: 2026-04-02T20:56:00Z
  checked: VTK periodic table for VDW radii
  found: O VDW radius = 1.55 Å, H VDW radius = 1.20 Å
  implication: Ball-and-stick scale 0.12 → O sphere = 0.186 Å, which is SMALLER than expected for visibility

- timestamp: 2026-04-02T20:57:00Z
  checked: VTK preset method defaults
  found: VTK defaults - BallAndStick: scale=0.30, bond=0.075; VDW: scale=1.0, bond=0.075; Liquorice: scale=0.15, bond=0.15
  implication: ROOT CAUSE - Our values are much smaller than VTK defaults; stick mode needs scale=bond for gap-free joints

## Resolution

root_cause: Custom radius values were too small compared to VTK's built-in defaults; scale factors (0.12/0.85/0.08) and bond radius (0.03) were much smaller than VTK defaults (0.30/1.0/0.15 and 0.075/0.15), causing visibility issues
fix: |
  - VDW: scale=0.5 (reduced from 1.0 to prevent overlap), bond=0.075 (VTK default)
  - Ball-and-stick: scale=0.30, bond=0.075 (VTK defaults - 6.2x sphere/bond ratio)
  - Stick: scale=0.15, bond=0.15 (VTK default for Liquorice - EQUAL for gap-free joints)
verification: |
  - Smoke test passed: all radius values set correctly
  - Module imports successfully
  - Values align with VTK defaults:
    - Ball-and-stick: scale=0.30, bond=0.075 (matches VTK default)
    - VDW: scale=0.5 (reduced from 1.0 for less overlap)
    - Stick: scale=0.15, bond=0.15 (matches VTK Liquorice default)
  - Stick mode now has equal sphere and bond radii for seamless joints
files_changed: [quickice/gui/molecular_viewer.py]
