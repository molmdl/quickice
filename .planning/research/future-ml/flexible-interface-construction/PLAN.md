---
phase: research-flexible-interface
plan: 01
type: research
wave: 1
depends_on: []
files_modified: []
autonomous: true
research_target: flexible-interface-construction
research_mode: feasibility+ecosystem
target_milestone: v5.x

must_haves:
  truths:
    - "GenIce2 API limits for interface configuration are documented"
    - "Physics constraints on slab orientation and mixed systems are identified"
    - "UI/UX patterns for multi-mode scientific configuration are catalogued"
    - "GROMACS export complications from flexible placement are documented"
    - "Feasibility per feature (slab flip, mixed hydrate, ice+hydrate) is assessed"
  artifacts:
    - path: ".planning/research/future-ml/flexible-interface-construction/SUMMARY.md"
      provides: "Executive summary with phased recommendation"
    - path: ".planning/research/future-ml/flexible-interface-construction/STACK.md"
      provides: "GenIce2 API capabilities, UI framework analysis"
    - path: ".planning/research/future-ml/flexible-interface-construction/FEATURES.md"
      provides: "Feature landscape with feasibility ratings"
    - path: ".planning/research/future-ml/flexible-interface-construction/ARCHITECTURE.md"
      provides: "UI architecture for flexible configuration"
    - path: ".planning/research/future-ml/flexible-interface-construction/PITFALLS.md"
      provides: "Technical pitfalls and GenIce2 API limits"
    - path: ".planning/research/future-ml/flexible-interface-construction/FEASIBILITY.md"
      provides: "Feasibility assessment per feature"
---

<objective>
Full research workflow for flexible interface construction modes.

Purpose: Determine how to extend QuickIce's interface construction beyond the current fixed slab orientation (ice-top, water-bottom). Research what the GenIce2 API actually supports for interface configuration, what physics constraints exist, what UI/UX patterns work for scientific multi-mode configuration, and what GROMACS export complications arise. Produce comprehensive research deliverables that will inform v5.x milestone planning.

Output: 6 research documents in `.planning/research/future-ml/flexible-interface-construction/`
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
@.planning/research/ARCHITECTURE-INTERFACE.md
@.planning/research/ARCHITECTURE_INTERFACE.md
@.planning/research/FEATURES-INTERFACE.md
@.planning/research/STACK-INTERFACE.md
@.planning/research/PITFALLS-INTERFACE.md
@.planning/research/SUMMARY-INTERFACE.md
@.planning/research/hydrate-analysis/SUMMARY.md
@.planning/todos/pending/2026-05-09-flexible-interface-construction.md
@.planning/env_dev.yml
@quickice/structure_generation/interface_builder.py
@quickice/structure_generation/modes/slab.py
@quickice/structure_generation/modes/pocket.py
@quickice/structure_generation/modes/piece.py
@quickice/structure_generation/types.py
@quickice/gui/interface_panel.py

Current architecture:
- InterfaceConfig has: mode, box_x/y/z, ice_thickness, water_thickness, pocket_diameter, pocket_shape, seed
- Slab mode: bottom ice → water → top ice (fixed Z-stacking)
- Pocket mode: spherical/cubic water cavity in ice
- Piece mode: ice crystal in water box
- Source: Candidate from Ice tab OR HydrateStructure from Hydrate tab (via to_candidate())
- GenIce2 has NO interface generation - QuickIce builds from scratch
- GenIce2's `shift` parameter shifts origin: potential for slab reorientation?
- GenIce2's `reshape` parameter and `rep` control cell replication
- Cross-tab flow: Ice/Hydrate → Interface → Custom Molecule/Solute/Ion

Current environment (Python 3.14.3):
- genice2 2.2.13.1, genice-core 1.4.3
- numpy 2.4.3, scipy 1.17.1, shapely 2.1.2, spglib 2.7.0
- PySide6 6.10.2, VTK 9.5.2
- MDAnalysis 2.10.0
</context>

<research_waves>

## Wave 1: Technical Foundations (Parallel)

Two parallel deep dives into the technical constraints.

### Task 1A: GenIce2 API Deep Dive for Interface Configuration

<task type="auto">
  <name>Investigate GenIce2 API capabilities and limits for flexible interface building</name>
  <files>.planning/research/future-ml/flexible-interface-construction/STACK.md</files>
  <action>
Deep investigation of GenIce2's API to determine what's possible for interface configuration:

1. **GenIce2 coordinate manipulation capabilities**:
   - `shift=(x, y, z)` parameter: Can it shift the ice slab origin? What's the range?
   - `reshape` matrix (3x3 integer): Can it create non-cubic supercells? What are constraints?
   - `rep=(nx, ny, nz)`: How does replication work? Can we replicate asymmetrically?
   - `density` parameter: Can we change ice density to match a specific slab configuration?
   - `noise` parameter: Position noise for interfaces?

2. **GenIce2 raw format for structure extraction**:
   - The `raw` format outputs: reppositions, repcell, repcagetype, repcagepos, graph, digraph, rotmatrices, mols
   - Can we extract just the ice slab coordinates and place them at arbitrary Z positions?
   - Can we extract cage positions for hydrate structures and use them independently?
   - What's the coordinate system? (fractional vs absolute, origin location)

3. **Multi-structure GenIce2 calls**:
   - Can we call GenIce2 twice with different lattices (sI + sII) and merge the output?
   - What happens when two GenIce2 structures have different cell dimensions?
   - Can GenIce2's `AnalIce` analyze a combined structure?
   - Can `safe_import` load two different lattices simultaneously?

4. **Current QuickIce interface code analysis**:
   - Read quickice/structure_generation/modes/slab.py: how is Z-stacking implemented?
   - What would need to change to support ice-on-bottom vs ice-on-top?
   - Is the Z-stacking hardcoded or parameterized?
   - Can the slab assembly function be generalized to support arbitrary layer ordering?
   - Read InterfaceConfig dataclass: what fields need to be added?

5. **Water model handling**:
   - TIP3P used for ice, TIP4P used for hydrates
   - Can different water models coexist in the same simulation box?
   - GROMACS force field implications of mixed water models

Write findings to STACK.md with GenIce2 capability matrix and gaps.
  </action>
  <verify>STACK.md exists with sections: genice2_api_capabilities, coordinate_manipulation, multi_structure_calls, current_code_analysis, water_model_handling</verify>
  <done>GenIce2 API limits for interface config fully documented, current slab code analyzed for generalization points</done>
</task>

### Task 1B: Physics Constraints + Scientific Use Cases

<task type="auto">
  <name>Research physics constraints on slab orientation and scientific demand for flexible interfaces</name>
  <files>.planning/research/future-ml/flexible-interface-construction/FEATURES.md</files>
  <action>
Investigate the physics and scientific demand for flexible interface configurations:

1. **Physics of ice-water slab orientation**:
   - In PBC simulations, is ice-on-top vs ice-on-bottom physically meaningful?
   - With PBC, the slab repeats infinitely - so "top" and "bottom" are symmetric?
   - What happens with gravity effects? (Most MD simulations don't include gravity)
   - Does the basal/prismatic face orientation matter? (Current: always [001] face?)
   - Are there published studies that specifically need ice-on-bottom?
   - What about "water slab in ice" (inverse sandwich) - physically meaningful?
   - Does the current "bottom ice → water → top ice" orientation match literature conventions?

2. **Mixed hydrate system physics**:
   - Can sI and sII hydrates coexist in the same simulation box?
   - What's the lattice parameter mismatch between sI (a≈1.2nm) and sII (a≈1.73nm)?
   - Is there a miscibility gap? Do they phase-separate in reality?
   - What about sI + sH? sII + sH?
   - Are there published MD studies of mixed-hydrate systems?

3. **Ice + hydrate system physics**:
   - Can ice Ih and sII hydrate coexist in the same box?
   - What's the density difference? (Ice Ih ~0.92 g/cm³, sII ~0.93 g/cm³ empty, ~1.0 with guests)
   - What's the structural incompatibility at the ice-hydrate boundary?
   - Are there MD studies of ice-hydrate interfaces? (Yes: water-hydrate dissociation studies)
   - What about hydrate pockets in ice (reverse of pocket mode)?

4. **Scientific use case analysis**:
   - Literature survey: What interface configurations appear in hydrate MD papers?
   - Most common: single ice slab + water (current QuickIce already does this)
   - Second most common: hydrate slab + water (current QuickIce supports this via hydrate source)
   - Less common but real: ice-hydrate-water triple interface
   - Niche: multiple hydrate types in same system
   - What specific papers/studies would benefit from each flexible mode?

5. **Feature categorization**:
   Rate each proposed feature as: table-stakes / differentiator / anti-feature
   - Slab orientation flip (ice-on-bottom): ???
   - Sandwich configuration control: ???
   - Multiple hydrate types in same box: ???
   - Ice + hydrate in same system: ???
   - Arbitrary layer ordering UI: ???
   - Custom slab composition (pick any structure for any layer): ???

Write findings to FEATURES.md with physics constraints and scientific demand assessment.
  </action>
  <verify>FEATURES.md exists with sections: slab_orientation_physics, mixed_hydrate_physics, ice_hydrate_physics, scientific_use_cases, feature_categorization</verify>
  <done>Physics constraints on all flexible modes documented, each feature categorized by demand level</done>
</task>

---

## Wave 2: Design & Constraints (Depends on Wave 1)

Two parallel investigations building on Wave 1 technical foundations.

### Task 2A: UI/UX Patterns for Scientific Multi-Mode Configuration

<task type="auto">
  <name>Research UI/UX patterns for complex multi-mode scientific configuration</name>
  <files>.planning/research/future-ml/flexible-interface-construction/ARCHITECTURE.md</files>
  <action>
Using Wave 1 findings about what's technically feasible, research UI patterns:

1. **Current QuickIce interface panel analysis**:
   - Read quickice/gui/interface_panel.py (935 lines)
   - Current UI: mode selector (slab/pocket/piece) + mode-specific controls
   - Current slab controls: box_x, box_y, box_z, ice_thickness, water_thickness, seed
   - How are mode-specific controls shown/hidden? (QStackedWidget pattern)
   - What's the source selection mechanism? (Ice candidate vs hydrate)

2. **Scientific GUI patterns for multi-mode configuration**:
   - Avogadro: how does it handle multi-step build workflows?
   - VMD: how does it handle molecule selection + representation configuration?
   - LAMMPS-GUI: how does it handle simulation parameter configuration?
   - GROMACS tools (gmx ...): CLI parameter patterns for complex workflows
   - Packmol-GUI: how does it handle multi-molecule placement?
   - What patterns exist for "layer composition" UIs? (stacking order, layer types)

3. **Proposed UI architecture for flexible configuration**:
   - Layer-based composition model: each layer has type (ice/hydrate/water) + structure + thickness
   - Source selection per layer: ice candidate, hydrate type, or liquid water
   - Layer ordering: drag-and-drop? numbered list? up/down arrows?
   - Mode evolution: slab mode becomes a 3-layer composition, pocket/piece become special cases
   - How to handle mode-specific controls in a general composition model?
   - Preview panel: show layer stack diagram before generation

4. **PySide6 implementation patterns**:
   - QStackedWidget for mode-dependent controls (already used)
   - QComboBox for source selection (already used)
   - QListWidget with drag-and-drop for layer ordering?
   - QFormLayout for parameter inputs (already used)
   - Signal/slot architecture for cross-layer validation
   - How to extend InterfacePanel without breaking existing modes

5. **Configuration validation UI**:
   - Real-time validation: layer thicknesses must sum to box_z
   - Density mismatch warnings between adjacent layers
   - Lattice parameter incompatibility warnings
   - Preview: simple diagram showing layer stack with dimensions

Write findings to ARCHITECTURE.md with UI component diagrams and implementation patterns.
  </action>
  <verify>ARCHITECTURE.md exists with sections: current_ui_analysis, scientific_gui_patterns, proposed_ui_architecture, pyside6_patterns, validation_ui</verify>
  <done>UI architecture designed for flexible interface configuration, compatible with current InterfacePanel patterns</done>
</task>

### Task 2B: GROMACS Export + Technical Pitfalls

<task type="auto">
  <name>Document GROMACS export complications and technical pitfalls</name>
  <files>.planning/research/future-ml/flexible-interface-construction/PITFALLS.md</files>
  <action>
Using Wave 1 findings about physics and API constraints, document pitfalls:

1. **GROMACS export complications from flexible placement**:
   - Current export: single moleculetype for ice (SOL), guests as separate moleculetypes
   - With mixed hydrate types: two different hydrate frameworks in same box → two sets of cage positions, two guest moleculetype sets
   - With ice + hydrate: ice SOL vs hydrate SOL (same water model? different residue names?)
   - Coordinate ordering: ice molecules first, then water, then guests? Or layered by Z position?
   - Box vectors: do mixed structures with different lattice parameters create triclinic boxes?
   - .top [molecules] section complexity with multiple structure types
   - Force field parameter compatibility across ice/hydrate/water models

2. **GenIce2 API pitfalls for interface building**:
   - GenIce2 generates ENTIRE crystal structures - can't generate partial slabs
   - Shift parameter: fractional coordinates only, limited range
   - Multiple GenIce2 calls: different random seeds → different HB networks → may cause artifacts at boundaries
   - Cell dimension mismatches when merging structures (sI: a=1.2nm vs sII: a=1.73nm)
   - TIP3P vs TIP4P water model normalization at ice-hydrate boundaries
   - GenIce2's `depol` mode: different depolarization strategies for different structures

3. **Interface assembly pitfalls**:
   - Current slab.py: hardcoded bottom→water→top Z-stacking
   - Overlap detection: cKDTree must check across layer boundaries
   - Density transition: ice→water density mismatch creates void or overlap
   - Periodic image artifacts at layer boundaries
   - Pocket mode: spherical cavity in ice is clean; irregular cavities are not
   - Piece mode: ice-in-water is clean; water-in-ice requires carving

4. **UI pitfalls**:
   - Mode-dependent controls need careful show/hide logic (QStackedWidget)
   - Layer validation: thicknesses must sum to box dimensions
   - Source selection: multiple sources per configuration (ice + hydrate)
   - Backward compatibility: existing InterfaceConfig must still work
   - Performance: multiple GenIce2 calls per generation = longer wait times

5. **Risk matrix**: For each pitfall, rate: likelihood, impact, mitigation strategy.

Write findings to PITFALLS.md with risk matrix and mitigation strategies.
  </action>
  <verify>PITFALLS.md exists with sections: gromacs_export_complications, genice2_api_pitfalls, interface_assembly_pitfalls, ui_pitfalls, risk_matrix</verify>
  <done>All GROMACS export complications documented, GenIce2 API limits flagged, risk matrix complete</done>
</task>

---

## Wave 3: Feasibility Synthesis (Depends on Wave 2)

### Task 3A: Feasibility Assessment Per Feature

<task type="auto">
  <name>Assess feasibility for each flexible interface feature</name>
  <files>.planning/research/future-ml/flexible-interface-construction/FEASIBILITY.md</files>
  <action>
Using all Wave 1 and Wave 2 findings, assess feasibility per feature:

1. **Feature: Slab orientation flip (ice-on-bottom / water-on-top)**
   - Technical approach: Can we simply reorder the Z-stacking in slab.py?
   - Is it just a coordinate reversal (flip Z-axis) or does it require regenerating ice at new position?
   - GenIce2 constraint: ice is always centered at origin - can we shift it?
   - Physics constraint: is this even physically meaningful with PBC?
   - Effort estimate: LOW (likely just reordering coordinates)
   - Verdict: FEASIBLE / BLOCKED / CONDITIONAL

2. **Feature: Sandwich configuration control (ice/water/ice ordering)**
   - Current slab mode already does ice-water-ice sandwich
   - What about water-ice-water? ice-ice-water? hydrate-water-ice?
   - Is this a UI change or an algorithm change?
   - Effort estimate: LOW-MEDIUM (UI changes + validation)
   - Verdict: FEASIBLE / BLOCKED / CONDITIONAL

3. **Feature: Multiple hydrate types in same system (sI + sII)**
   - Requires two separate GenIce2 calls → merge into same box
   - Cell dimension mismatch: how to handle?
   - Physics: do these coexist or phase-separate?
   - GROMACS export: multiple moleculetype sets
   - Effort estimate: MEDIUM-HIGH (new assembly logic + GROMACS handling)
   - Verdict: FEASIBLE / BLOCKED / CONDITIONAL

4. **Feature: Ice + hydrate in same system**
   - Ice candidate from Tab 0 + hydrate from Tab 1 → merge
   - Water model normalization: TIP3P (ice) → TIP4P (hydrate) or vice versa
   - GROMACS export: how to distinguish ice SOL from hydrate SOL?
   - Density matching at ice-hydrate boundary
   - Effort estimate: MEDIUM-HIGH (water model handling + GROMACS complexity)
   - Verdict: FEASIBLE / BLOCKED / CONDITIONAL

5. **Feature: General layer composition UI**
   - Major UI redesign: layer list, drag-and-drop, per-layer configuration
   - Backward compatibility with existing modes
   - Effort estimate: HIGH (full UI rework)
   - Verdict: FEASIBLE / BLOCKED / CONDITIONAL

For each feature: verdict, blockers, dependencies, effort, risk, scientific justification.
  </action>
  <verify>FEASIBILITY.md exists with verdicts for 5+ features, each with blockers and effort estimates</verify>
  <done>Each flexible interface feature has clear feasibility verdict with specific blockers</done>
</task>

### Task 3B: Executive Summary + Roadmap Recommendations

<task type="auto">
  <name>Synthesize all research into SUMMARY.md with phased implementation plan</name>
  <files>.planning/research/future-ml/flexible-interface-construction/SUMMARY.md</files>
  <action>
Read all Wave 1 and Wave 2 deliverables and synthesize:

1. **Executive summary**:
   - One-paragraph verdict: which features are feasible, which are blocked, recommended phasing
   - Top-line finding: Is the current architecture extensible or does it need redesign?
   - GenIce2 API limits: what can we work around vs what's a hard blocker?

2. **Key findings** (bulleted):
   - What's the easiest win (likely slab orientation flip)
   - What's the hardest feature (likely multi-hydrate or general layer UI)
   - Physics constraints that limit some configurations
   - GROMACS export implications that affect all flexible features

3. **Phased implementation recommendation**:
   - Phase 1 (v5.0): Slab orientation flip + sandwich configuration control
   - Phase 2 (v5.1): Ice + hydrate in same system (if feasible)
   - Phase 3 (v5.2): Multiple hydrate types (if feasible)
   - Phase 4 (v6.0): General layer composition UI (if justified by demand)

4. **Architecture recommendation**:
   - Should InterfaceConfig be extended or replaced?
   - Should slab.py be refactored for generalization?
   - How should source selection work for multi-structure configurations?
   - What changes to InterfacePanel are needed?

5. **Quick wins**:
   - Is slab orientation flip just a coordinate reversal? (Likely yes)
   - Can current pocket mode already handle hydrate-in-ice?
   - Can current piece mode already handle ice-in-water with hydrate source?

6. **Open questions**:
   - What requires user/domain-expert input on physics constraints?
   - What requires prototyping to resolve (e.g., mixed water model handling)?
   - What depends on v4.5 completion (InterfaceConfig stability)?

7. **Dependencies on other milestones**:
   - v4.5 must be complete (solute/custom molecule infrastructure)
   - v4.5.1 CLI work may affect InterfaceConfig schema
   - v4.6 multi-guest hydrate may overlap with this work
  </action>
  <verify>SUMMARY.md exists with verdict, phased plan, architecture recommendation, quick wins, open questions</verify>
  <done>Clear phased implementation plan with feasibility-informed prioritization</done>
</task>

</research_waves>

<verification>
1. All 6 research files exist in `.planning/research/future-ml/flexible-interface-construction/`
2. STACK.md covers GenIce2 API capabilities + gaps for interface config
3. FEATURES.md catalogs physics constraints + scientific demand per feature
4. ARCHITECTURE.md has UI architecture proposal with component diagrams
5. PITFALLS.md has GROMACS complications + GenIce2 API limits + risk matrix
6. FEASIBILITY.md has verdicts for each flexible interface feature
7. SUMMARY.md has phased implementation plan
</verification>

<success_criteria>
- GenIce2 API limits for interface configuration fully documented
- Physics constraints on slab orientation and mixed systems identified
- Each flexible feature (slab flip, mixed hydrate, ice+hydrate, layer UI) has feasibility verdict
- UI architecture designed that's compatible with current InterfacePanel
- GROMACS export complications for each feature documented
- Phased implementation plan prioritized by feasibility and demand
- All recommendations use current environment libraries where possible
</success_criteria>

<output>
After completion, all 6 research files in `.planning/research/future-ml/flexible-interface-construction/` are ready for v5.x milestone planning.
</output>
