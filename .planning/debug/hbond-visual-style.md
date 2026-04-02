---
status: investigating
trigger: "Investigate issue: hbond-visual-style"
created: 2026-04-02T00:00:00Z
updated: 2026-04-02T00:00:00Z
---

## Current Focus

hypothesis: Line stippling (SetLineStipplePattern) is not implemented in VTK's OpenGL2 backend - only works with legacy OpenGL, not default OpenGL2
test: Verify VTK documentation about OpenGL2 limitation and confirm by checking VTK backend
expecting: Confirm that stipple patterns don't work with OpenGL2, need alternative approach
next_action: Implement manual dashed lines using multiple line segments instead of stipple pattern

## Symptoms

expected: Hydrogen bonds should be dashed lines, colored cyan or green
actual: Hydrogen bonds are visible now but use same style as regular bonds (solid, default color)
errors: None
reproduction: 1) Generate structure with hydrogen bonds 2) View in stick mode 3) H-bonds visible but not dashed or colored differently
started: After sphere/bond size tuning made H-bonds visible

## Eliminated

<!-- None yet -->

## Evidence

- timestamp: 2026-04-02T00:00:00Z
  checked: vtk_utils.py create_hbond_actor function (lines 146-199)
  found: Function sets gray color (0.6, 0.6, 0.6) on line 194, sets stipple pattern 0x0F0F on line 195, sets repeat factor on line 196
  implication: Styling IS being applied in code, but may not be taking effect - VTK may require explicit enabling of line stippling

- timestamp: 2026-04-02T00:00:00Z
  checked: VTK documentation via help() and web fetch
  found: SetLineStipplePattern documentation states: "This is only implemented for OpenGL, not OpenGL2. The default is 0xFFFF."
  implication: Line stippling does NOT work with VTK's OpenGL2 backend (which is default). Need alternative approach - manually create dashed lines by splitting into short segments

- timestamp: 2026-04-02T00:00:00Z
  checked: REQUIREMENTS.md VIEWER-05 and CONTEXT.md
  found: VIEWER-05 requires "dashed lines between molecules", CONTEXT.md says "thin dashed lines (line style at OpenCode discretion)"
  implication: Requirement is just dashed lines, no specific color. User wants cyan/green to distinguish from regular bonds. Current gray is not ideal for distinction.

## Resolution

root_cause: Two issues: (1) VTK's SetLineStipplePattern does not work with OpenGL2 backend (only legacy OpenGL), so dashed lines appear solid. (2) Gray color (0.6, 0.6, 0.6) does not distinguish hydrogen bonds from regular bonds clearly - should use cyan or green.
fix: Implement manual dashed lines by splitting each H-bond into multiple short segments (dash pattern) and change color to cyan (0.0, 0.8, 0.8) for clear distinction from regular bonds.
verification: 
files_changed: []

## Resolution

root_cause: 
fix: 
verification: 
files_changed: []
