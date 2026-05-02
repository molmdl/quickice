---
phase: 011-split-phase-diagram
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/output/phase_diagram.py
  - quickice/output/phase_diagram/__init__.py
  - quickice/output/phase_diagram/renderer.py
  - quickice/output/phase_diagram/data_loader.py
  - quickice/output/phase_diagram/boundaries.py
autonomous: true

must_haves:
  truths:
    - "phase_diagram.py split into modules under quickice/output/phase_diagram/"
    - "Each module <500 lines with single responsibility"
    - "Phase diagram renders correctly"
    - "All boundaries and annotations display properly"
  artifacts:
    - path: "quickice/output/phase_diagram/renderer.py"
      provides: "Matplotlib rendering logic"
      max_lines: 500
    - path: "quickice/output/phase_diagram/data_loader.py"
      provides: "Phase data loading"
      max_lines: 500
    - path: "quickice/output/phase_diagram/boundaries.py"
      provides: "Boundary calculations"
      max_lines: 500
  key_links:
    - from: "quickice/output/phase_diagram.py"
      to: "quickice/output/phase_diagram/*"
      via: "import delegation"
      pattern: "from quickice.output.phase_diagram import"
---

<objective>
Split phase_diagram.py (1132 lines) into smaller, focused modules.

Purpose: Improve maintainability of phase diagram generation
Output: Modular structure with each file <500 lines
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/codebase/CONCERNS.md
@.planning/codebase/ARCHITECTURE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Split phase_diagram.py into modules</name>
  <files>
    quickice/output/phase_diagram.py
    quickice/output/phase_diagram/__init__.py
    quickice/output/phase_diagram/renderer.py
    quickice/output/phase_diagram/data_loader.py
    quickice/output/phase_diagram/boundaries.py
  </files>
  <action>
    Refactor `quickice/output/phase_diagram.py` (1132 lines) into smaller modules:

    1. **Create module structure**:
       ```
       quickice/output/phase_diagram/
       ├── __init__.py           # Public API exports
       ├── renderer.py           # Matplotlib rendering, annotations
       ├── data_loader.py        # Load phase data from files
       └── boundaries.py         # Boundary curve calculations
       ```

    2. **Assign responsibilities**:
       - `renderer.py`: render_diagram(), plot_boundaries(), add_annotations()
       - `data_loader.py`: load_phase_data(), parse_triple_points()
       - `boundaries.py`: calculate_boundaries(), interpolate_curves()

    3. **Maintain backward compatibility**:
       - Keep `quickice/output/phase_diagram.py` as thin wrapper
       - Public API unchanged: `from quickice.output.phase_diagram import render_diagram`

    4. **Verify line counts**:
       Each file should be <500 lines after split.

    Reference: quickice/output/phase_diagram.py current structure
  </action>
  <verify>
    - New directory structure created
    - Each file <500 lines
    - Phase diagram renders (generate test diagram)
    - All boundaries and labels display
    - Triple points visible
  </verify>
  <done>phase_diagram.py refactored into 4 modules, each <500 lines, rendering preserved</done>
</task>

</tasks>

<verification>
- [ ] quickice/output/phase_diagram/ directory exists
- [ ] renderer.py <500 lines
- [ ] data_loader.py <500 lines
- [ ] boundaries.py <500 lines
- [ ] __init__.py exports public API
- [ ] Phase diagram renders correctly
- [ ] All ice phase boundaries display
- [ ] Triple points annotated
</verification>

<success_criteria>
phase_diagram.py (1132 lines) split into 4 modules, each <500 lines, all rendering functionality preserved.
</success_criteria>

<output>
After completion, create `.planning/quick/011-split-phase-diagram/011-SUMMARY.md`
</output>
