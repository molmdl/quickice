---
phase: 012-remove-deprecated-heuristic
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/structure_generation/water_filler.py
autonomous: true

must_haves:
  truths:
    - "Deprecated atoms_per_molecule heuristic removed from water_filler.py"
    - "All callers provide explicit atoms_per_molecule parameter"
    - "No DeprecationWarning emitted during generation"
    - "Water filling still works correctly"
  artifacts:
    - path: "quickice/structure_generation/water_filler.py"
      provides: "Water filling without deprecated heuristic"
      not_contains: "atoms_per_molecule heuristic"
  key_links:
    - from: "quickice/structure_generation/*"
      to: "water_filler.py"
      via: "atoms_per_molecule parameter"
      pattern: "fill_water.*atoms_per_molecule"
---

<objective>
Remove deprecated atoms_per_molecule heuristic from water_filler.py.

Purpose: Eliminate technical debt and prevent incorrect results from heuristic inference
Output: Clean code requiring explicit atoms_per_molecule parameter
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/codebase/CONCERNS.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove deprecated heuristic and update callers</name>
  <files>
    quickice/structure_generation/water_filler.py
  </files>
  <action>
    Remove the deprecated atoms_per_molecule heuristic from water_filler.py:

    1. **Locate deprecated code**:
       - Lines 335-359 in water_filler.py
       - Heuristic attempts to infer atoms_per_molecule from atom count
       - Emits DeprecationWarning

    2. **Update function signature**:
       - Make `atoms_per_molecule` a required parameter (remove default None)
       - Remove heuristic logic entirely
       - Update docstring to reflect required parameter

    3. **Find and update all callers**:
       - Search codebase for calls to `fill_water()`
       - Ensure all callers pass explicit `atoms_per_molecule=3` for water
       - Files likely affected:
         - quickice/structure_generation/interface_builder.py
         - quickice/structure_generation/hydrate_generator.py
         - quickice/gui/workers.py

    4. **Verify no regressions**:
       - Generate test structures with water filling
       - Confirm correct molecule counts
       - No DeprecationWarning in output

    Reference: quickice/structure_generation/water_filler.py:335-359
  </action>
  <verify>
    - Deprecated code removed from water_filler.py
    - All callers updated with explicit parameter
    - No DeprecationWarning during generation
    - Water filling produces correct results
  </verify>
  <done>Deprecated heuristic removed, all callers updated with explicit atoms_per_molecule parameter</done>
</task>

</tasks>

<verification>
- [ ] Lines 335-359 removed from water_filler.py
- [ ] atoms_per_molecule is required parameter
- [ ] All callers pass explicit value
- [ ] No DeprecationWarning emitted
- [ ] Interface generation works
- [ ] Hydrate generation works
</verification>

<success_criteria>
Deprecated atoms_per_molecule heuristic removed, all callers updated, no DeprecationWarning, water filling works correctly.
</success_criteria>

<output>
After completion, create `.planning/quick/012-remove-deprecated-heuristic/012-SUMMARY.md`
</output>
