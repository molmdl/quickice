---
phase: 002-fix-diagram-and-ranking-output
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/output/phase_diagram.py
  - quickice/main.py
autonomous: true
must_haves:
  truths:
    - "Melting curve is clearly visible as a thick boundary line on phase diagram"
    - "CLI displays ranking scores for top candidates"
    - "Users can see energy, density, diversity, and combined scores"
  artifacts:
    - path: quickice/output/phase_diagram.py
      provides: "Phase diagram with visible melting curves"
      contains: "linewidth=3.0"
    - path: quickice/main.py
      provides: "CLI output with ranking scores"
      contains: "energy_score"
  key_links:
    - from: "quickice/main.py"
      to: "ranking_result.ranked_candidates"
      via: "iteration over scores"
      pattern: "for.*ranked_candidates"
---

<objective>
Fix two UX issues: (1) make melting curve more visible as solid-liquid boundary, (2) display ranking scores in CLI output.

Purpose: Improve user experience by making phase boundaries clearly visible and providing transparency into ranking decisions.
Output: Updated phase_diagram.py and main.py with the fixes.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@quickice/output/phase_diagram.py
@quickice/main.py
@quickice/ranking/types.py
</context>

<tasks>

<task type="auto">
  <name>Add liquid-vapor boundary line to phase diagram</name>
  <files>quickice/output/phase_diagram.py</files>
  <action>
    After the melting curves section and before the Liquid/Vapor labels (around line 475), add a liquid-vapor boundary curve.
    
    The liquid-vapor boundary is the saturation curve. For the diagram's pressure range (0.1 to 10000 MPa), draw a simple approximation:
    
    ```python
    # Liquid-Vapor boundary (saturation curve approximation)
    # From triple point (273.16K, 0.0006 MPa) through boiling point (373K, 0.1 MPa)
    # Use a few key points for the curve
    lv_T = [273.16, 300, 350, 373, 400, 450, 500]  # K
    lv_P = [0.0006, 0.0035, 0.04, 0.1, 0.25, 1.0, 2.5]  # MPa (approximate saturation pressures)
    ax.plot(lv_T, lv_P, color='blue', linewidth=3.0, linestyle='--', alpha=0.8, label='Liquid-Vapor boundary')
    ```
    
    This adds a dashed blue line separating the Liquid and Vapor regions, making the phase boundaries clear.
  </action>
  <verify>grep -n "Liquid-Vapor" quickice/output/phase_diagram.py</verify>
  <done>Liquid-vapor boundary drawn as dashed blue line, clearly separating liquid and vapor regions</done>
</task>

<task type="auto">
  <name>Make melting curve more visible on phase diagram</name>
  <files>quickice/output/phase_diagram.py</files>
  <action>
    At line 473, the melting curves are drawn with `linewidth=1.5`. Change this to make the melting curve more prominent as a phase boundary:
    
    1. Increase linewidth from 1.5 to 3.0 (thicker, more visible)
    
    Change line 473 from:
    ```python
    ax.plot(T_curve, P_curve, color=color, linewidth=1.5, linestyle='-', alpha=0.8)
    ```
    To:
    ```python
    ax.plot(T_curve, P_curve, color=color, linewidth=3.0, linestyle='-', alpha=0.8)
    ```
  </action>
  <verify>grep -n "linewidth=3.0" quickice/output/phase_diagram.py</verify>
  <done>Melting curves drawn with linewidth=3.0, clearly visible as phase boundaries on the diagram</done>
</task>

<task type="auto">
  <name>Add ranking score output to CLI</name>
  <files>quickice/main.py</files>
  <action>
    After line 52 (`print(f"Ranked {len(ranking_result.ranked_candidates)} candidates")`), add score output showing top candidates.
    
    Add a new section that displays the top 5 candidates (or fewer if less than 5) with their scores:
    
    ```python
    # Print ranking scores for top candidates
    print("\nRanking scores (lower combined = better):")
    print("-" * 70)
    print(f"{'Rank':<6}{'Energy':<12}{'Density':<12}{'Diversity':<12}{'Combined':<12}")
    print("-" * 70)
    for rc in ranking_result.ranked_candidates[:5]:
        print(f"{rc.rank:<6}{rc.energy_score:<12.4f}{rc.density_score:<12.4f}{rc.diversity_score:<12.4f}{rc.combined_score:<12.4f}")
    print("-" * 70)
    ```
    
    This shows:
    - Rank (1 = best)
    - Energy score (lower = better, deviation from ideal O-O distance)
    - Density score (lower = better, deviation from expected density)
    - Diversity score (higher = more unique, 1.0 = unique seed)
    - Combined score (weighted combination, lower = better)
  </action>
  <verify>grep -n "energy_score" quickice/main.py</verify>
  <done>CLI displays a formatted table showing top 5 candidates with rank, energy, density, diversity, and combined scores</done>
</task>

</tasks>

<verification>
1. Run `python -m quickice.output.phase_diagram 273 0.1` to verify phase diagram generates correctly
2. Run `quickice 273 0.1 -n 128` to verify CLI shows ranking scores
3. Verify melting curve is visible as thick line on generated diagram
</verification>

<success_criteria>
- Phase diagram shows melting curve with linewidth=3.0
- CLI output displays ranking score table for top 5 candidates
- Both fixes are minimal and focused on the specific issues
</success_criteria>

<output>
After completion, create `.planning/quick/002-fix-diagram-and-ranking-output/002-SUMMARY.md`
</output>
