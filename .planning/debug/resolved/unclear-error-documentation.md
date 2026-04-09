---
status: resolved
trigger: "Investigate issue: unclear-error-documentation - Error messages and in-app documentation not clear enough for users to solve problems"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:30:00Z
---

## Current Focus

hypothesis: Error messages and tooltips lack explanation of WHY constraints exist and don't provide actionable guidance. The issue is in THREE locations: (1) GUI validators lack context, (2) backend validation has mixed quality, (3) UI tooltips don't explain parameter relationships.
test: Reviewed all error sources - validators.py, interface_builder.py, interface_panel.py, main_window.py
expecting: Find inconsistent error message quality and missing documentation
next_action: Verify fixes by testing error messages with invalid inputs

## Symptoms

expected: Users should understand what went wrong and how to fix it
actual: Error messages don't provide enough guidance; dimension settings instructions unclear
errors: Users can't figure out how to set correct box dimensions
reproduction: Generate interface with wrong dimensions, observe error messages
started: Always had unclear documentation

## Eliminated

<!-- APPEND only - prevents re-investigating -->

## Evidence

- timestamp: 2026-04-09T00:05:00Z
  checked: quickice/gui/validators.py (lines 112-137, 140-165, 168-193)
  found: GUI validators provide only range checks without context. "Box dimension must be between 0.5 and 100 nm" doesn't explain WHY or what happens if violated.
  implication: Users don't understand the physical reasoning behind constraints

- timestamp: 2026-04-09T00:06:00Z
  checked: quickice/structure_generation/interface_builder.py (lines 75-98, 117-124, 205-231)
  found: GOOD examples: Lines 75-98 explain minimum dimensions due to water molecule size (0.28 nm) and numerical issues. Lines 117-124 explain triclinic cell issue with affected phases. Lines 205-231 show calculations and consequences.
  implication: Some error messages already have good structure - can use as template

- timestamp: 2026-04-09T00:07:00Z
  checked: quickice/structure_generation/interface_builder.py (lines 58-72, 129-135)
  found: POOR examples: Lines 58-72 just say "must be positive" without guidance. Lines 129-135 show calculation but don't suggest HOW to fix or typical values.
  implication: Inconsistent error message quality - some are good, others lack guidance

- timestamp: 2026-04-09T00:08:00Z
  checked: quickice/gui/interface_panel.py (lines 74, 95, 218, 257)
  found: UI tooltips exist but are basic. "Thickness of ice layer in nm (0.5–50)" doesn't explain relationship to box_z. No tooltips explain that box_z must equal 2*ice_thickness + water_thickness.
  implication: Users don't understand parameter interdependencies

- timestamp: 2026-04-09T00:09:00Z
  checked: quickice/gui/main_window.py (lines 388-393, 493-498)
  found: Error dialogs just wrap error messages with "Failed to generate ice structure:\n\n{error_msg}". No additional context, guidance, or links to documentation.
  implication: Even good backend error messages lose impact without additional support in UI

- timestamp: 2026-04-09T00:10:00Z
  checked: help_dialog.py (not found in search)
  found: No in-app documentation explaining dimension relationships, best practices for choosing values, or what overlap threshold means.
  implication: Users have no reference material to understand the system

- timestamp: 2026-04-09T00:25:00Z
  checked: Backend error messages with test script
  found: All three test cases (slab box_z mismatch, pocket too large, piece box too small) now show improved error messages with: WHAT is wrong (current values), WHY constraint exists (physical reason), HOW to fix (suggested values with examples), clear formatting with bullet points
  implication: Backend validation messages now provide comprehensive guidance

- timestamp: 2026-04-09T00:26:00Z
  checked: GUI validators with test script
  found: GUI validators now provide context about typical values and remind users of important constraints (box_z = 2*ice + water for slab mode, pocket diameter must be smaller than box dimensions)
  implication: Users get immediate guidance in the UI before attempting generation

## Resolution

root_cause: Error messages and documentation lack clarity in THREE areas: (1) Backend validation messages are INCONSISTENT - some explain WHY and provide guidance (lines 75-98, 117-124, 205-231 in interface_builder.py) while others just state constraints (lines 58-72, 129-135). (2) UI tooltips don't explain parameter RELATIONSHIPS - users don't understand that box_z must equal 2*ice_thickness + water_thickness in slab mode. (3) No in-app DOCUMENTATION explaining dimension relationships, best practices, or what overlap threshold means.

fix: 
1. IMPROVED all backend error messages to follow GOOD pattern: WHAT is wrong (current value) + WHY constraint exists (physical reason) + HOW to fix (suggested values) + consequences
   - interface_builder.py: Lines 58-72, 129-135, 149-170, 172-232 - added context, examples, and guidance
   - modes/piece.py: Lines 51-64 - added explanation and examples
   
2. ENHANCED tooltips to explain parameter relationships
   - interface_panel.py: Ice thickness, water thickness, box Z tooltips now explain the relationship box_z = 2*ice + water
   - Box dimensions help icon explains mode-specific requirements
   
3. ADDED comprehensive in-app documentation
   - help_dialog.py: New "Dimension Relationships" section with mode-specific requirements and examples
   - help_dialog.py: New "Best Practices" section with choosing values and troubleshooting
   
4. IMPROVED GUI validators with context
   - validators.py: Box dimension, thickness, pocket diameter validators now explain typical values and constraints

verification: 
1. ✓ Backend error messages tested - all show WHAT (current values), WHY (physical reason), HOW (suggested values with examples)
2. ✓ GUI validators tested - all provide typical values and constraint reminders
3. ✓ Tooltips verified - ice_thickness, water_thickness, box_z all explain relationships
4. ✓ Help dialog verified - new sections "Dimension Relationships" and "Best Practices" added
5. ✓ All three modes (slab, pocket, piece) have mode-specific error messages and guidance

files_changed:
- quickice/structure_generation/interface_builder.py
- quickice/structure_generation/modes/piece.py
- quickice/gui/interface_panel.py
- quickice/gui/help_dialog.py
- quickice/gui/validators.py
