---
phase: 001-add-liquid-vapor-labels
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [quickice/output/phase_diagram.py]
autonomous: true

must_haves:
  truths:
    - "Liquid label visible above melting curves in high-T region"
    - "Vapor label visible at low pressure near bottom of diagram"
    - "Labels use consistent styling with existing phase labels"
  artifacts:
    - path: "quickice/output/phase_diagram.py"
      contains: "ax.text.*Liquid"
      min_lines: 1
    - path: "quickice/output/phase_diagram.py"
      contains: "ax.text.*Vapor"
      min_lines: 1
  key_links:
    - from: "phase_diagram.py"
      to: "matplotlib text rendering"
      via: "ax.text() calls after polygon plotting"
---

<objective>
Add "Liquid" and "Vapor" text labels to the phase diagram in appropriate regions.

Purpose: Complete the phase diagram labeling to show all major phase regions.
Output: Updated phase_diagram.py with two new labels.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Add Liquid and Vapor labels to phase diagram</name>
  <files>quickice/output/phase_diagram.py</files>
  <action>
    In the `generate_phase_diagram()` function, after the existing phase label loop (around line 459), add two `ax.text()` calls for Liquid and Vapor labels:

    **Liquid label:**
    - Position: T=340 K, P=50 MPa (in liquid region above melting curves)
    - Styling: Match existing phase labels exactly (fontsize=14, fontweight='bold', ha='center', va='center', color='black', alpha=0.8, zorder=5)

    **Vapor label:**
    - Position: T=400 K, P=0.2 MPa (low pressure region near bottom)
    - Styling: Same as Liquid label

    Add these labels after the melting curve plotting section (after line 473), before the triple points section.
  </action>
  <verify>grep -n "Liquid\|Vapor" quickice/output/phase_diagram.py | grep "ax.text"</verify>
  <done>Both "Liquid" and "Vapor" labels added with consistent styling, positioned in correct regions of the phase diagram</done>
</task>

</tasks>

<verification>
Run the phase diagram generation to confirm labels appear correctly:
```bash
python quickice/output/phase_diagram.py 300 1
```
Check output/phase_diagram.png for visible Liquid and Vapor labels.
</verification>

<success_criteria>
- Liquid label visible in high-T region above melting curves
- Vapor label visible at low pressure near diagram bottom
- Both labels use consistent styling (bold, black, fontsize=14, alpha=0.8)
- Labels do not overlap with melting curves or phase boundaries
</success_criteria>

<output>
After completion, create `.planning/quick/001-add-liquid-vapor-labels/001-SUMMARY.md`
</output>
