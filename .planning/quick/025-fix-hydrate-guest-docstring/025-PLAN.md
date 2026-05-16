---
phase: 025-fix-hydrate-guest-docstring
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [quickice/structure_generation/hydrate_generator.py]
autonomous: true

must_haves:
  truths:
    - "Docstring accurately reflects available guest molecules"
    - "No misleading claims about CO2/H2 support"
  artifacts:
    - path: "quickice/structure_generation/hydrate_generator.py"
      provides: "Accurate HydrateStructureGenerator documentation"
      line_range: [36, 37]
  key_links:
    - from: "hydrage_generator.py docstring"
      to: "types.py GUEST_MOLECULES"
      via: "documentation consistency"
      pattern: "CH4.*THF"
---

<objective>
Fix misleading docstring in HydrateStructureGenerator class.

Purpose: Ensure documentation accurately reflects implemented functionality.
Output: Corrected docstring matching actual GUEST_MOLECULES dictionary.
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
  <name>Update HydrateStructureGenerator docstring</name>
  <files>quickice/structure_generation/hydrate_generator.py</files>
  <action>
    Update the class docstring at lines 34-38 to accurately reflect implemented functionality:

    CURRENT (lines 34-38):
    ```python
    class HydrateStructureGenerator:
        """Generator for hydrate structures using GenIce2.
        
        Supports sI, sII, sH hydrate lattices with configurable guest molecules
        (CH4, THF, CO2, H2) and cage occupancy.
        """
    ```

    REPLACE WITH:
    ```python
    class HydrateStructureGenerator:
        """Generator for hydrate structures using GenIce2.
        
        Supports sI, sII, sH hydrate lattices with configurable guest molecules
        (CH4, THF) and cage occupancy.
        
        Note: GenIce2 supports additional guest types (CO2, H2), but these are not
        exposed in QuickIce's GUEST_MOLECULES configuration.
        """
    ```

    This aligns the docstring with the actual GUEST_MOLECULES dictionary in types.py
    which only contains "ch4" and "thf" entries.
  </action>
  <verify>
    1. Read lines 34-42 of hydrate_generator.py
    2. Confirm docstring mentions only CH4 and THF
    3. Confirm note about GenIce2's additional support
    4. Verify no reference to CO2 or H2 as supported guests
  </verify>
  <done>Docstring accurately lists CH4 and THF as the only configured guest molecules with explanatory note about GenIce2 capabilities.</done>
</task>

</tasks>

<verification>
- Docstring at lines 34-42 accurately reflects GUEST_MOLECULES content
- No false claims about CO2/H2 support in QuickIce
- Note provides context about GenIce2 capabilities
</verification>

<success_criteria>
Documentation accuracy: Docstring matches actual implementation.
</success_criteria>

<output>
After completion, create `.planning/quick/025-fix-hydrate-guest-docstring/025-SUMMARY.md`
</output>
