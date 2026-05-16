---
phase: quick-021
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [quickice/utils/molecule_utils.py]
autonomous: true

must_haves:
  truths:
    - "Module imports without errors after removal"
    - "Only count_guest_atoms() function remains in the module"
  artifacts:
    - path: "quickice/utils/molecule_utils.py"
      provides: "Guest atom counting utility"
      contains: "def count_guest_atoms"
  key_links: []
---

<objective>
Remove unused `build_molecule_index()` function from molecule_utils.py.

Purpose: Clean up dead code that was added for future consolidation but never used (private implementations kept separate).
Output: Streamlined module with only the active `count_guest_atoms()` function.
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
  <name>Remove unused build_molecule_index function</name>
  <files>quickice/utils/molecule_utils.py</files>
  <action>
    Remove the `build_molecule_index()` function (lines 111-180, 70 lines total).

    Also update the module docstring (lines 1-14) to remove references to this function:
    - Line 5: Remove "- Building molecule indices from structure data"
    - Lines 7-13: Update the consolidation history to only reference modules that use `count_guest_atoms()`

    The module should end with only `count_guest_atoms()` function remaining.
  </action>
  <verify>python -c "from quickice.utils.molecule_utils import count_guest_atoms; print('Import successful')"</verify>
  <done>Module contains only count_guest_atoms() function, imports without errors, docstring accurately reflects remaining functionality</done>
</task>

</tasks>

<verification>
- Module imports successfully: `python -c "from quickice.utils.molecule_utils import count_guest_atoms"`
- No references to removed function in codebase: `grep -r "build_molecule_index" quickice/`
- File size reduced by ~70 lines (removed function + updated docstring)
</verification>

<success_criteria>
- build_molecule_index() function completely removed from molecule_utils.py
- Module docstring updated to remove references to the deleted function
- Module imports without errors
- grep confirms zero references to build_molecule_index in codebase
</success_criteria>

<output>
After completion, create `.planning/quick/021-remove-unused-build-molecule-index/021-SUMMARY.md`
</output>
