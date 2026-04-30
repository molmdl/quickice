---
phase: quick
plan: 006
type: execute
wave: 1
depends_on: []
files_modified: [sample_output/gui_v4/README.md]
autonomous: true

must_haves:
  truths:
    - "README contains complete citation for GAFF2 preparation method"
  artifacts:
    - path: "sample_output/gui_v4/README.md"
      provides: "Sample output documentation with proper citations"
  key_links: []
---

<objective>
Add the GAFF2 preparation method citation to sample_output/gui_v4/README.md

Purpose: Replace "(see docs for citation)" placeholder with actual citation information
Output: README.md with complete Multiwfn and Sobtop citations
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
  <name>Add GAFF2 preparation method citations</name>
  <files>sample_output/gui_v4/README.md</files>
  <action>
  Replace the Forcefield parameters section (lines 9-12) with a section that includes the full citation:
  
  The citation comes from `.planning/phases/28.1-urgent-bugfixes-ff-corrections/28.1-CONTEXT.md`:
  
  ```
  # Forcefield parameters
  
  - Ions: Madrid2019
  - Water/ice: TIP4P-ice
  - CH4 and THF: GAFF2 with RESP2(0.5) partial charge, prepared with Multiwfn and Sobtop.
  
  ## GAFF2 Preparation Method Citation
  
  GAFF2 parameters were prepared using Sobtop 2026.1.16 and Multiwfn 3.8(dev) with RESP2 partial charges using default settings in the bundled RESP2.sh script.
  
  **Multiwfn citation:**
  - Tian Lu, Feiwu Chen, Multiwfn: A Multifunctional Wavefunction Analyzer, J. Comput. Chem. 33, 580-592 (2012) DOI: 10.1002/jcc.22885
  - Tian Lu, A comprehensive electron wavefunction analysis toolbox for chemists, Multiwfn, J. Chem. Phys., 161, 082503 (2024) DOI: 10.1063/5.0216272
  
  **Sobtop citation:**
  - Tian Lu, Sobtop, Version 2026.1.16, http://sobereva.com/soft/Sobtop (accessed on 15 Apr 2026)
  ```
  
  This replaces the "(see docs for citation)" placeholder with the actual citation information.
  </action>
  <verify>grep -A 20 "Forcefield parameters" sample_output/gui_v4/README.md</verify>
  <done>README contains complete Multiwfn and Sobtop citations for GAFF2 preparation method</done>
</task>

</tasks>

<verification>
- README.md has complete citation section
- Both Multiwfn and Sobtop citations are present
- No "(see docs for citation)" placeholder remains
</verification>

<success_criteria>
README.md now contains complete citation for GAFF2 preparation method with Multiwfn and Sobtop references.
</success_criteria>

<output>
After completion, create `.planning/quick/006-add-gaff2-preparation-method-citation-to/006-SUMMARY.md`
</output>
