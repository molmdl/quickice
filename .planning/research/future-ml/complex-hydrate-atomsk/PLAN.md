---
phase: research-complex-hydrate
plan: 01
type: research
wave: 1
depends_on: []
files_modified: []
autonomous: true
research_target: complex-hydrate-atomsk
research_mode: feasibility
target_milestone: post-v6

must_haves:
  truths:
    - "Atomsk's hydrate/clathrate capabilities are fully catalogued"
    - "All complex hydrate structure types beyond sI/sII/sH are identified"
    - "Integration blockers (licensing, API, technical) are documented"
    - "Alternative approaches using current environment libraries are evaluated"
    - "Scientific demand for complex hydrate MD is quantified"
  artifacts:
    - path: ".planning/research/future-ml/complex-hydrate-atomsk/SUMMARY.md"
      provides: "Executive summary with go/no-go recommendation"
    - path: ".planning/research/future-ml/complex-hydrate-atomsk/STACK.md"
      provides: "Technology recommendations and licensing analysis"
    - path: ".planning/research/future-ml/complex-hydrate-atomsk/FEATURES.md"
      provides: "Feature landscape for complex hydrate generation"
    - path: ".planning/research/future-ml/complex-hydrate-atomsk/ARCHITECTURE.md"
      provides: "Integration architecture patterns"
    - path: ".planning/research/future-ml/complex-hydrate-atomsk/PITFALLS.md"
      provides: "Domain pitfalls and licensing traps"
    - path: ".planning/research/future-ml/complex-hydrate-atomsk/FEASIBILITY.md"
      provides: "Feasibility assessment per integration approach"
---

<objective>
Full research workflow for complex hydrate formation using atomsk.

Purpose: Determine whether QuickIce can extend beyond simple clathrate hydrates (sI, sII, sH) to complex hydrate structures (filled ice, semi-clathrates, mixed phases). Evaluate atomsk as a potential tool, assess alternatives using current environment libraries, and produce comprehensive research deliverables that will inform post-v6 milestone planning.

Output: 6 research documents in `.planning/research/future-ml/complex-hydrate-atomsk/`
</objective>

<execution_context>
Research workflow: multi-wave investigation producing structured deliverables.
Each wave builds on prior findings. Final wave synthesizes into actionable recommendations.
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/MILESTONES.md
@.planning/research/GENICE2_API_RESEARCH.md
@.planning/research/CURRENT_GENICE2_FEATURES.md
@.planning/research/hydrate-analysis/SUMMARY.md
@.planning/research/STACK.md
@.planning/research/PITFALLS.md
@.planning/todos/pending/2026-05-09-complex-hydrate-formation-atomsk.md
@.planning/env_dev.yml

Current environment constraints (Python 3.14.3):
- genice2 2.2.13.1 (MIT license) - already supports filled ices (c0te, c1te, c2te, ice1hte, sTprime), semiclathrate groups, 249+ lattices
- MDAnalysis 2.10.0 (available for structure manipulation)
- scipy 1.17.1, numpy 2.4.3, shapely 2.1.2, spglib 2.7.0
- atomsk is NOT in environment (C tool, GPL-3.0 license)
- QuickIce itself is MIT license
</context>

<research_waves>

## Wave 1: Ecosystem Survey (Parallel)

Two parallel investigations to establish the landscape before feasibility analysis.

### Task 1A: Atomsk Tool Deep Dive

<task type="auto">
  <name>Research atomsk capabilities, licensing, and alternatives</name>
  <files>.planning/research/future-ml/complex-hydrate-atomsk/STACK.md</files>
  <action>
Investigate atomsk (https://atomsk.univ-lille.fr/, https://github.com/pierrehirel/atomsk/) comprehensively:

1. **What atomsk IS**: 
   - Language (C), build system, distribution method
   - Core capabilities: lattice creation, defect insertion, surface creation, grain boundaries, dislocations, alloy generation, coordinate transformation
   - File format I/O: which formats can it read/write? (XSF, CIF, POSCAR, CFG, LAMMPS, etc.)
   - Does it have ANY hydrate, clathrate, or ice-specific functionality?
   - Can it create custom lattice structures from parameters?
   - Can it manipulate existing structures (rotate, translate, cut, duplicate)?

2. **Licensing analysis**:
   - Atomsk license (GPL-3.0) vs QuickIce license (MIT)
   - What does GPL-3.0 constrain? (subprocess execution OK, code adaptation NOT OK, static linking NOT OK)
   - Can atomsk be used as an external tool via subprocess without license contamination?
   - Can atomsk output files be processed by MIT-licensed code?
   - Precedent: other MIT projects calling GPL tools via subprocess

3. **Alternative tools in current environment**:
   - Can GenIce2's custom lattice plugin system create complex hydrate structures?
   - Can MDAnalysis + numpy + scipy build complex hydrate structures from CIF files?
   - Can spglib (2.7.0, already installed) help with crystallographic manipulation?
   - Can shapely (2.1.2, already installed) help with geometric operations for structure assembly?
   - ASE (Atomic Simulation Environment) - Python, MIT-compatible? In conda-forge?
   - pymatgen - Python, MIT-compatible? Structure generation capabilities?
   - Packmol - packing molecules into boxes, license compatibility?

4. **Atomsk Python bindings**:
   - Does atomsk have a Python API/wrapper?
   - Can it be called from Python via subprocess?
   - What are the input file formats atomsk accepts?

Write findings to STACK.md with technology recommendations.
  </action>
  <verify>STACK.md exists with sections: atomsk_capabilities, licensing_analysis, alternative_tools, environment_compatible_options</verify>
  <done>Atomsk capabilities fully catalogued, licensing constraints documented, 3+ alternative approaches identified using current environment libraries</done>
</task>

### Task 1B: Complex Hydrate Scientific Landscape

<task type="auto">
  <name>Survey complex hydrate structure types and scientific demand</name>
  <files>.planning/research/future-ml/complex-hydrate-atomsk/FEATURES.md</files>
  <action>
Research the scientific landscape of complex hydrate structures beyond sI/sII/sH:

1. **Complex hydrate structure taxonomy**:
   - Filled ice phases: C0, C1, C2 (what are these structurally? how different from clathrates?)
   - Semi-clathrates: alkali metal + water frameworks (e.g., TBAB, TBPB, TMAF)
   - Binary clathrates: two guest types in same cage system
   - Mixed clathrates: sI + sII in same system (phase separation? miscibility gap?)
   - Gas hydrates with multiple guests: CH4+CO2, CH4+THF, H2+THF
   - High-pressure hydrate phases (Ice VII-filled, etc.)
   - Helium and hydrogen hydrates (sII, sH with small guests)

2. **GenIce2 coverage of complex hydrates**:
   - Cross-reference with GENICE2_API_RESEARCH.md (already loaded)
   - GenIce2 already has: filled ices (c0te, c1te, c2te, ice1hte, sTprime), semiclathrate groups (-H flag), mixed cage occupancy (-g flag)
   - What complex hydrate types does GenIce2 ALREADY support that QuickIce doesn't expose?
   - What types are genuinely impossible with GenIce2's current plugin architecture?

3. **Scientific demand assessment**:
   - Literature survey: How many MD simulation papers use filled ice vs clathrate structures?
   - Which fields need complex hydrate MD? (climate science, energy storage, planetary science, flow assurance)
   - What's the relative demand: simple clathrates (sI/sII/sH) vs complex hydrates?
   - Are there open-access databases of complex hydrate crystallographic data? (CSD, ICSD, COD)

4. **Crystallographic data availability**:
   - Are CIF files available for complex hydrate structures?
   - Can GenIce2's genice2-cif plugin load these CIF files directly?
   - What lattice parameters are needed for common complex hydrate types?

Write findings to FEATURES.md with table-stakes/differentiator/anti-feature categorization.
  </action>
  <verify>FEATURES.md exists with sections: complex_hydrate_taxonomy, genice2_coverage, scientific_demand, crystallographic_data</verify>
  <done>All complex hydrate structure types catalogued, GenIce2 coverage gaps identified, scientific demand characterized as high/medium/low</done>
</task>

---

## Wave 2: Feasibility & Architecture (Depends on Wave 1)

Two parallel investigations using Wave 1 findings.

### Task 2A: GenIce2 Gap Analysis + Custom Plugin Feasibility

<task type="auto">
  <name>Analyze GenIce2's coverage gaps and custom lattice plugin feasibility</name>
  <files>.planning/research/future-ml/complex-hydrate-atomsk/FEASIBILITY.md</files>
  <action>
Using findings from Wave 1 (STACK.md and FEATURES.md), conduct deep feasibility analysis:

1. **GenIce2 custom lattice plugin for complex hydrates**:
   - Read GenIce2's plugin architecture (from GENICE2_API_RESEARCH.md)
   - What's needed to create a custom lattice plugin for semi-clathrate TBAB?
   - Can existing lattice plugins be modified for filled ice variants?
   - GenIce2's `cagepos`, `cagetype`, `waters`, `cell`, `bondlen` fields - what data is needed?
   - How does the ice-rules algorithm handle non-standard cage geometries?
   - Can `assess_cages=True` auto-detect cages in custom lattice structures?

2. **GenIce2 CIF import pathway**:
   - genice2-cif plugin: what does it actually do? Can it load arbitrary CIF files?
   - genice2 zeolite[ITT] syntax - how does this work?
   - If CIF files exist for complex hydrates, can GenIce2 use them directly?
   - What happens after CIF import? Does GenIce2 apply ice rules? Does it fill cages?

3. **Code-level feasibility with current environment**:
   - Can MDAnalysis + spglib create hydrate structures from crystallographic data?
   - Can numpy + scipy generate filled ice structures from lattice parameters?
   - What would a "pure Python" complex hydrate builder require? (lines of code, complexity)
   - Is atomsk even necessary, or can GenIce2 plugins + CIF import cover 90% of use cases?

4. **Feasibility verdict per approach**:
   Rate each approach on FEASIBILITY.md:
   - A: Atomsk subprocess (feasible/blocked/alternative)
   - B: GenIce2 custom lattice plugins (feasible/blocked/alternative)
   - C: GenIce2 CIF import (feasible/blocked/alternative)
   - D: Pure Python builder with MDAnalysis (feasible/blocked/alternative)
   - E: External pipeline (atomsk → CIF → GenIce2) (feasible/blocked/alternative)

For each: effort estimate (low/medium/high), blockers, dependencies, risk level.
  </action>
  <verify>FEASIBILITY.md exists with verdicts for 5+ approaches, each with blockers and effort estimates</verify>
  <done>Each integration approach has a clear feasibility verdict with specific blockers documented</done>
</task>

### Task 2B: Integration Architecture + Pitfall Analysis

<task type="auto">
  <name>Design integration architectures and document domain pitfalls</name>
  <files>.planning/research/future-ml/complex-hydrate-atomsk/ARCHITECTURE.md,.planning/research/future-ml/complex-hydrate-atomsk/PITFALLS.md</files>
  <action>
Using findings from Wave 1, design integration architectures and document pitfalls:

1. **Integration architecture options** (for ARCHITECTURE.md):

   **Option A: Atomsk subprocess pipeline**
   - QuickIce generates input file → subprocess calls atomsk → parse output → import into QuickIce
   - Data flow diagram, error handling, timeout management
   - Cross-platform concerns (atomsk binary distribution)
   - How atomsk output maps to QuickIce's Candidate/InterfaceStructure dataclasses

   **Option B: GenIce2 custom lattice plugin**
   - New lattice module in genice2's plugin directory
   - Crystallographic data stored as module constants
   - Plugin follows existing Lattice class interface
   - No external tool dependency

   **Option C: CIF import via genice2-cif**
   - User provides CIF file → genice2-cif loads → GenIce2 processes
   - QuickIce adds CIF file upload UI
   - May need post-processing for cage filling

   **Option D: Pure Python structure builder**
   - New module in quickice/structure_generation/
   - Uses MDAnalysis for I/O, spglib for symmetry, numpy for coordinates
   - Follows existing MVVM patterns (Worker + ViewModel + Panel)

   For each option: component diagram, data flow, file structure, affected existing files.

2. **Domain pitfalls** (for PITFALLS.md):
   - GPL-3.0 license contamination risk with atomsk
   - Ice rules violation in custom structures (genice-core enforces, but what about non-ice frameworks?)
   - Cage occupancy for unknown cage types
   - PBC handling for non-orthogonal hydrate cells
   - Water model compatibility (TIP4P-ICE vs other models for complex hydrates)
   - GROMACS force field parameters for exotic guest molecules
   - Density matching between hydrate and liquid phases
   - Crystallographic data quality (CIF file accuracy, missing hydrogen positions)
   - GenIce2 version compatibility (plugin API stability)
   - Python 3.14 compatibility for any new dependencies

3. **Risk matrix**: For each pitfall, rate: likelihood, impact, mitigation.
  </action>
  <verify>ARCHITECTURE.md has 4+ architecture options with component diagrams; PITFALLS.md has 8+ pitfalls with risk ratings</verify>
  <done>Integration architectures designed for each feasible approach, all major pitfalls documented with mitigations</done>
</task>

---

## Wave 3: Synthesis (Depends on Wave 2)

### Task 3: Executive Summary + Roadmap Implications

<task type="auto">
  <name>Synthesize all research into SUMMARY.md with roadmap recommendations</name>
  <files>.planning/research/future-ml/complex-hydrate-atomsk/SUMMARY.md</files>
  <action>
Read all Wave 1 and Wave 2 deliverables and synthesize:

1. **Executive summary**:
   - One-paragraph verdict: go/no-go/conditional-go for atomsk integration
   - Top-line finding: Is atomsk necessary, or can GenIce2 plugins cover the gap?
   - License constraint impact: How does GPL-3.0 limit options?

2. **Key findings** (bulleted):
   - What complex hydrate structures GenIce2 ALREADY supports (likely more than QuickIce exposes)
   - What atomsk can/cannot do for hydrate generation
   - Best integration approach given licensing + technical constraints
   - Scientific demand level (high/medium/low)

3. **Recommended approach**:
   - Primary recommendation (most feasible path)
   - Alternative if primary is blocked
   - What can be done NOW with existing GenIce2 features (low-hanging fruit)

4. **Roadmap implications**:
   - How does this affect the post-v6 milestone definition?
   - Should any of this be moved earlier (e.g., exposing GenIce2's existing filled ice lattices)?
   - What dependencies need to be resolved first?
   - Effort estimate for the recommended approach

5. **Quick wins**:
   - Are there GenIce2 features already available that QuickIce doesn't expose?
   - Can exposing filled ices (c0te, c1te, c2te, ice1hte) be done as a v5 task?
   - Can semiclathrate group placement (-H flag) be exposed in the UI?

6. **Open questions**:
   - What remains unknown after this research?
   - What requires user/domain-expert input?
   - What requires prototyping to resolve?
  </action>
  <verify>SUMMARY.md exists with verdict, key findings, recommended approach, roadmap implications, quick wins</verify>
  <done>Clear go/no-go verdict with actionable recommendations for post-v6 milestone planning</done>
</task>

</research_waves>

<verification>
1. All 6 research files exist in `.planning/research/future-ml/complex-hydrate-atomsk/`
2. STACK.md covers atomsk + 3+ alternatives using current environment
3. FEATURES.md catalogs all complex hydrate types + GenIce2 coverage gaps
4. ARCHITECTURE.md has 4+ integration options with diagrams
5. PITFALLS.md has 8+ pitfalls with risk ratings
6. FEASIBILITY.md has verdicts for each approach
7. SUMMARY.md has clear go/no-go recommendation
</verification>

<success_criteria>
- Complex hydrate taxonomy complete (filled ice, semi-clathrate, binary, mixed)
- Atomsk capabilities fully catalogued with licensing constraints
- GenIce2 gap analysis identifies what's missing vs what's just not exposed
- Feasibility verdict for each integration approach (at least 4 approaches)
- Recommended path forward with quick wins identified
- All findings use current environment libraries where possible (no unnecessary new dependencies)
</success_criteria>

<output>
After completion, all 6 research files in `.planning/research/future-ml/complex-hydrate-atomsk/` are ready for milestone planning.
</output>
