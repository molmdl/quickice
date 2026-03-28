---
phase: quick-003
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/phase_mapping/triple_points.py
  - quickice/phase_mapping/solid_boundaries.py
  - quickice/output/phase_diagram.py
  - quickice/phase_mapping/lookup.py
autonomous: true
depth: quick

must_haves:
  truths:
    - "VII_VIII_X triple point (100K, 62 GPa) is in TRIPLE_POINTS dict"
    - "VII_X_Liquid triple point (~1000K, 43 GPa) is in TRIPLE_POINTS dict"
    - "VII_VIII_X marker appears on phase diagram"
    - "x_boundary correctly interpolates between triple points"
  artifacts:
    - path: quickice/phase_mapping/triple_points.py
      provides: "Triple point coordinates"
      contains: "VII_VIII_X"
    - path: quickice/phase_mapping/solid_boundaries.py
      provides: "Updated x_boundary function"
      exports: ["x_boundary"]
    - path: quickice/output/phase_diagram.py
      provides: "Phase diagram with VII_VIII_X marker"
  key_links:
    - from: solid_boundaries.x_boundary
      to: triple_points.VII_VIII_X
      via: "interpolation"
---

<objective>
Add two missing triple points from LSBU Water Phase Data to the codebase.

Purpose: Complete the triple point data for ice phases VII, VIII, and X.
Output: Updated triple points dict, corrected x_boundary interpolation, and phase diagram marker.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@quickice/phase_mapping/triple_points.py
@quickice/phase_mapping/solid_boundaries.py
@quickice/output/phase_diagram.py
@quickice/phase_mapping/lookup.py

**LSBU Water Phase Data triple points to add:**
1. VII_VIII_X: (100 K, 62000 MPa) - Where Ice VII, VIII, and X meet
2. VII_X_Liquid: (1000 K, 43000 MPa) - Where Liquid, Ice VII, and Ice X meet (outside current diagram bounds)
</context>

<tasks>

<task type="auto">
  <name>Add two triple points to TRIPLE_POINTS dict</name>
  <files>quickice/phase_mapping/triple_points.py</files>
  <action>
    Add two new entries to the TRIPLE_POINTS dictionary:
    
    ```python
    "VII_VIII_X": (100.0, 62000.0),  # 100K, 62 GPa - Ice VII/VIII/X triple point
    "VII_X_Liquid": (1000.0, 43000.0),  # ~1000K, 43 GPa - Liquid/VII/X (outside diagram bounds)
    ```
    
    Add these after the existing "VI_XV_Transition" entry. Include descriptive comments explaining each triple point.
  </action>
  <verify>grep -q "VII_VIII_X" quickice/phase_mapping/triple_points.py && grep -q "VII_X_Liquid" quickice/phase_mapping/triple_points.py</verify>
  <done>Both triple points added with correct coordinates and comments</done>
</task>

<task type="auto">
  <name>Update x_boundary to use correct interpolation</name>
  <files>quickice/phase_mapping/solid_boundaries.py</files>
  <action>
    Update the x_boundary function to interpolate between the new triple points:
    
    The VII/VIII-X boundary should use:
    - VII_VIII_X at (100K, 62000 MPa) for T <= 100K
    - VII_X_Transition at (300K, 30000 MPa) for T >= 300K
    - Linear interpolation between these points for 100K < T < 300K
    - VII_X_Liquid at (1000K, 43000 MPa) for extrapolation at T > 300K
    
    Current x_boundary returns: `30000.0 + 10.0 * max(0, T - 165.0)`
    
    New x_boundary should:
    ```python
    def x_boundary(T: float) -> float:
        """
        Ice X boundary: interpolates between triple points.
        
        Uses:
        - VII_VIII_X at (100K, 62000 MPa) for T <= 100K
        - VII_X_Transition at (300K, 30000 MPa) for T = 300K
        - VII_X_Liquid at (1000K, 43000 MPa) for T >= 1000K
        """
        if T <= 100.0:
            return 62000.0  # VII_VIII_X triple point
        elif T <= 300.0:
            # Linear interpolation: (100K, 62000) to (300K, 30000)
            return 62000.0 + (30000.0 - 62000.0) * (T - 100.0) / (300.0 - 100.0)
        elif T <= 1000.0:
            # Linear interpolation: (300K, 30000) to (1000K, 43000)
            return 30000.0 + (43000.0 - 30000.0) * (T - 300.0) / (1000.0 - 300.0)
        else:
            return 43000.0 + 10.0 * (T - 1000.0)  # Slight increase at very high T
    ```
    
    This ensures the boundary correctly passes through all three triple points.
  </action>
  <verify>python -c "from quickice.phase_mapping.solid_boundaries import x_boundary; assert x_boundary(100) == 62000.0, f'Expected 62000, got {x_boundary(100)}'; assert x_boundary(300) == 30000.0, f'Expected 30000, got {x_boundary(300)}'"</verify>
  <done>x_boundary returns correct values at VII_VIII_X (62000 at T=100K) and VII_X_Transition (30000 at T=300K)</done>
</task>

<task type="auto">
  <name>Add VII_VIII_X marker to phase diagram and update polygons</name>
  <files>quickice/output/phase_diagram.py</files>
  <action>
    1. Add "VII_VIII_X" to the triple_point_names list (around line 750-763):
       ```python
       ("VII_VIII_X", "VII-VIII-X"),
       ```
       Add after the existing ("VII_X_Transition", "VII-X") entry.
       
       Do NOT add VII_X_Liquid since it's outside diagram bounds (T=1000K > 500K limit).
    
    2. Update _build_ice_x_polygon to use the updated x_boundary for its lower boundary:
       - At T=50K: use x_boundary(50) which returns 62000 MPa (clamped at T <= 100)
       - At T=450K: use x_boundary(450) which returns ~33928 MPa
       
       Replace the fixed P_boundary = 30000.0 with dynamic calculation:
       ```python
       # Lower boundary uses x_boundary function
       P_boundary_low = x_boundary(T_low)  # At T=50K
       P_boundary_mid = x_boundary(450.0)   # At T=450K
       ```
    
    3. Similarly update _build_ice_vii_polygon and _build_ice_viii_polygon to extend to the x_boundary instead of fixed P=30000.
  </action>
  <verify>python -c "from quickice.output.phase_diagram import generate_phase_diagram; from pathlib import Path; generate_phase_diagram(250, 500, Path('/tmp/test_output'))" && ls /tmp/test_output/phase_diagram.png</verify>
  <done>VII_VIII_X marker visible on diagram, polygons correctly use updated x_boundary</done>
</task>

</tasks>

<verification>
1. Run unit tests: `pytest tests/ -v`
2. Verify triple points exist: `grep "VII_VIII_X\|VII_X_Liquid" quickice/phase_mapping/triple_points.py`
3. Verify x_boundary values: `python -c "from quickice.phase_mapping.solid_boundaries import x_boundary; print(f'T=100K: {x_boundary(100)}, T=300K: {x_boundary(300)}')"`
4. Generate phase diagram to verify marker: `python -m quickice.output.phase_diagram`
</verification>

<success_criteria>
- Both triple points added to TRIPLE_POINTS dict
- x_boundary correctly interpolates through VII_VIII_X (62000 at T=100K) and VII_X_Transition (30000 at T=300K)
- VII_VIII_X marker appears on generated phase diagram
- VII_X_Liquid is in code but NOT on diagram (outside bounds)
- All existing tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/003-add-missing-triple-points/003-SUMMARY.md`
</output>
