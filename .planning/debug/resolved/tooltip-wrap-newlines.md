---
status: resolved
trigger: "tooltip-wrap-newlines"
created: 2026-04-13T12:00:00Z
updated: 2026-04-13T12:15:00Z
---

## Current Focus

hypothesis: CONFIRMED - Tooltip formatting inconsistency in interface_panel.py
test: box_x_input/box_y_input are brief single lines while box_z_input has detailed multi-line explanation
expecting: All box dimension inputs should have consistent formatting
next_action: Implement fix - add newline-formatted explanations to box_x_input, box_y_input, and pocket_diameter_input

## Symptoms

expected: Tooltips should display full content, wrapping with newlines when too long (consistent with other tooltips that already use newlines)

actual: Previous fix removed max-width constraint, showing full text, but the underlying issue of "tooltips too long" wasn't addressed with proper newline wrapping

errors: No errors, but inconsistent tooltip behavior

reproduction: Hover over any element with a tooltip, observe that it doesn't wrap with newlines like other tooltips do

timeline: Original issue was tooltips being chopped/truncated. Previous fix (commit 97f6158) removed max-width, but proper newline wrapping wasn't implemented.

context: Some tooltips in the codebase already use newlines successfully - should follow that pattern.

## Eliminated

## Evidence

- timestamp: 2026-04-13T12:01:00Z
  checked: main_window.py lines 912-920
  found: Current tooltip styling only has padding, no max-width. Comment says "Qt QToolTip doesn't support max-width for text wrapping. Tooltips with \n characters will wrap naturally."
  implication: The styling is correct. The issue is tooltip content not using newlines.

- timestamp: 2026-04-13T12:02:00Z
  checked: help_dialog.py for newline patterns
  found: help_dialog.py uses extensive `\n` for formatting multi-line help text
  implication: Newline pattern is established in codebase

- timestamp: 2026-04-13T12:03:00Z
  checked: interface_panel.py tooltip patterns
  found: Mixed patterns - some tooltips use newlines well, others are short single lines
  implication: Inconsistency in tooltip formatting

- timestamp: 2026-04-13T12:04:00Z
  checked: Detailed comparison of tooltips in interface_panel.py
  found: |
    ALREADY USES NEWLINES (good pattern):
    - ice_thickness_input (lines 94-100): Uses \n\n for paragraph breaks
    - water_thickness_input (lines 127-133): Uses \n\n for paragraph breaks
    - mode_combo (line 248): Uses \n• for bullet list
    - box_z_input (lines 308-315): Uses \n\n for paragraph breaks
    - seed_input (line 355): Uses \n for simple wrap
    - refresh_btn (line 394): Uses \n for simple wrap
    
    NEEDS NEWLINE FORMATTING:
    - pocket_diameter_input (line 172): "Diameter of water cavity in nm (0.5–50).\nVoid carved in ice (sphere/cubic)." - has newline but content is brief
    - pocket_shape_combo (line 189): "Cavity shape: sphere or cube" - very short, OK as is
    - box_x_input (line 282): "Box X dimension in nm (0.5–100)" - short, inconsistent with box_z_input which has detailed explanation
    - box_y_input (line 295): "Box Y dimension in nm (0.5–100)" - short, inconsistent with box_z_input
    - candidate_dropdown (line 382): "Select an ice candidate from Tab 1 for interface generation" - could be more descriptive
    - generate_btn tooltip changes dynamically (lines 402, 542, 555, 574, 579) - needs review
  implication: box_x_input and box_y_input are inconsistent with box_z_input. pocket_diameter_input could use more detail like the slab inputs.

## Resolution

root_cause: Inconsistent tooltip formatting in interface_panel.py. The box_z_input tooltip has a detailed multi-line explanation with newlines (lines 308-315), while box_x_input and box_y_input have brief single-line tooltips. Similarly, pocket_diameter_input is brief compared to ice_thickness_input and water_thickness_input which have detailed multi-line explanations. This inconsistency makes some tooltips appear "chopped" or incomplete.
fix: Added newline-formatted explanations to box_x_input, box_y_input, and pocket_diameter_input to match the pattern of other detailed tooltips in the file. Each tooltip now has: range info, blank line separator, mode-specific guidance, and examples where appropriate.
verification: Module imports successfully. git diff shows clean changes. All three tooltips now use consistent newline formatting matching the established pattern in ice_thickness_input, water_thickness_input, and box_z_input.
files_changed: [quickice/gui/interface_panel.py]
