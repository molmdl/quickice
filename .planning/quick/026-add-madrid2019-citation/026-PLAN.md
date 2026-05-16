---
phase: quick
plan: 026
type: execute
wave: 1
depends_on: []
files_modified: [README.md, docs/gui-guide.md]
autonomous: true
---

<objective>
Add Madrid2019 citation to README.md and gui-guide.md for scientific attribution.

Purpose: Provide proper citation for Madrid2019 ion parameters used in ion insertion feature
Output: Both files updated with the approved citation
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
  <name>Add Madrid2019 citation to README.md References section</name>
  <files>README.md</files>
  <action>
1. Add new subsection "### Madrid2019 Ion Parameters" after the existing references (after line 332, before "## Testing" at line 333)
2. Use this exact citation format:

```
### Madrid2019 Ion Parameters
- Zeron, I. M., Abascal, J. L. F., & Vega, C. (2019). A force field of Li+, Na+, K+, Mg2+, Ca2+, Cl−, and SO42− in aqueous solution based on the TIP4P/2005 water model and scaled charges for the ions. Journal of Chemical Physics, 151, 134504.
- DOI: https://doi.org/10.1063/1.5121392
```

3. Update line 169 to reference the citation:
   - Current: `- **Charge neutrality** — Equal Na⁺/Cl⁻ with Madrid2019 parameters (±0.85e)`
   - Change to: `- **Charge neutrality** — Equal Na⁺/Cl⁻ with Madrid2019 parameters (±0.85e) [Madrid2019]`
  </action>
  <verify>`grep -A 3 "Madrid2019 Ion Parameters" README.md` shows the citation</verify>
  <done>README.md has Madrid2019 subsection in References, and line 169 includes [Madrid2019] reference</done>
</task>

<task type="auto">
  <name>Add Madrid2019 citation to gui-guide.md</name>
  <files>docs/gui-guide.md</files>
  <action>
Update line 790 to include the full citation inline:

Current:
```
- Madrid2019 force field parameters used (Na⁺ charge = +0.85, Cl⁻ charge = -0.85)
```

Change to:
```
- Madrid2019 force field parameters used (Na⁺ charge = +0.85, Cl⁻ charge = -0.85) — Zeron, Abascal, & Vega, J. Chem. Phys. 151, 134504 (2019), DOI: https://doi.org/10.1063/1.5121392
```
  </action>
  <verify>`grep "Zeron, Abascal" docs/gui-guide.md` shows the citation</verify>
  <done>gui-guide.md line 790 includes the Madrid2019 citation with DOI</done>
</task>

</tasks>

<verification>
- README.md contains "### Madrid2019 Ion Parameters" in References section
- README.md line 169 references [Madrid2019]
- gui-guide.md line 790 includes Zeron et al. citation with DOI
</verification>

<success_criteria>
Both documentation files properly cite the Madrid2019 ion parameter paper with the approved citation text.
</success_criteria>

<output>
After completion, create `.planning/quick/026-add-madrid2019-citation/026-SUMMARY.md`
</output>
