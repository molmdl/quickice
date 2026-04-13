# Project Research Summary

**Project:** QuickIce v4.0 Molecule Insertion
**Domain:** Scientific GUI application — molecular dynamics ice structure generation with hydrate/ion insertion
**Researched:** 2026-04-14
**Confidence:** HIGH

## Executive Summary

QuickIce v4.0 adds molecule insertion to an existing MVVM-patterned PySide6/VTK application that already generates ice structures and ice-water interfaces. The key discovery is that **no new external dependencies are needed**: GenIce2 already supports hydrate generation via cage-based guest insertion (`guests` parameter) and the existing `scipy.cKDTree` overlap resolver can be repurposed for ion placement. The two new features — Tab 2 (hydrate generation) and Tab 4 (NaCl/custom molecule insertion into liquid phase) — require entirely new generation pipelines but reuse the existing worker/viewer/export architecture pattern.

The recommended approach is a **5-phase build**: (0) fix 4 pre-existing bugs that block v4.0 work, (1) design multi-molecule data structures and extend the GRO parser, (2) build Tab 4 ion insertion first because it reuses the most existing infrastructure (InterfaceStructure, cKDTree, overlap_resolver), (3) build Tab 2 hydrate generation which requires a new GenIce2 API path, and (4) add custom molecule upload and per-type display controls. This ordering minimizes risk by proving the multi-actor viewer and multi-type GROMACS export pattern with the simpler ion insertion feature before tackling hydrates.

The **single biggest risk** is Pitfall #5: the entire codebase assumes uniform `atoms_per_molecule` (3 for ice, 4 for water). Adding ions (1 atom) and guest molecules (variable) breaks every position-array iteration, bond-creation loop, and GROMACS export function. This must be resolved as a data structure design decision before any Tab 2/4 code works. The second major risk is that hydrate generation requires a completely separate pipeline from ice generation — attempting to shoehorn it into Tab 1's flow would create a god class with confusing conditionals.

## Key Findings

### Recommended Stack

**No new dependencies required.** All molecule insertion capabilities exist in the current environment (GenIce2 2.2.13.1, scipy 1.17.1, numpy 2.4.3, VTK 9.5.2, PySide6 6.10.2). The implementation is entirely application logic: UI tabs, data flow extensions, GROMACS topology additions, and VTK multi-actor rendering. Five alternatives were evaluated and rejected (RDKit, Open Babel, MDAnalysis/MDTraj, ParmEd, ASE) — each would add 50-200MB of dependency for functionality that existing libraries already provide or that can be built with ~50 lines of Python.

**Core technologies:**
- **GenIce2 2.2.13.1** — Hydrate lattice generation (CS1/sI, CS2/sII) with `guests` parameter for cage filling; verified working with CH₄ in sI structure
- **scipy cKDTree** — PBC-aware collision detection for ion placement; existing `detect_overlaps()` function directly reusable
- **VTK 9.5.2 multi-actor** — Per-molecule-type rendering (one vtkMoleculeMapper + vtkActor per type); verified working in testing
- **Joung-Cheatham ion parameters** — Standard TIP4P-compatible Na⁺/Cl⁻ parameters for GROMACS export; published values (J. Phys. Chem. B, 2008)

**New bundled data files required:**
- `quickice/data/ions-na-cl.itp` — Na⁺/Cl⁻ topology (Joung-Cheatham 2008)
- `quickice/data/ch4.itp` — Methane topology (OPLS-AA)
- `quickice/data/co2.itp` — Carbon dioxide topology (deferrable to post-MVP)

### Expected Features

**Must have (table stakes):**
- Tab 2: Hydrate lattice selection (sI, sII), guest molecule insertion (CH₄, CO₂), supercell sizing
- Tab 4: NaCl concentration input (mol/L), auto-calculate ion count from liquid volume, random placement with overlap removal
- Multi-type GROMACS export (.gro + .top + bundled .itp files)
- Per-molecule-type VTK rendering (VDW for ions, ball-and-stick for guests, lines for water)
- Cross-tab data flow: Tab 1 → Tab 3 (existing), Tab 3 → Tab 4 (new)

**Should have (competitive):**
- Custom molecule upload (.gro + .itp) for both Tab 2 and Tab 4
- Per-type visibility/color/style toggles in 3D viewer
- Electroneutrality validation for ion insertion
- Liquid volume calculation from InterfaceStructure for accurate concentration

**Defer (post-v4.0):**
- THF and H₂ guest molecule support (beyond CH₄ and CO₂)
- Custom ion types beyond NaCl (KCl, MgCl₂)
- Molecule orientation controls (rotation matrix for custom molecules)
- In-app documentation viewer

### Architecture Approach

The v4.0 architecture extends the existing MVVM pattern with two new tab pipelines. Each tab has its own Panel (View), Worker (QThread), and generation logic (Domain), following the established pattern. Key architectural decisions: (1) **Separate HydrateStructureGenerator** — not an extension of IceStructureGenerator, because hydrates have fundamentally different inputs (lattice selection vs phase lookup) and outputs (mixed residue types, no ranking); (2) **New InsertedStructure dataclass** — not modifying InterfaceStructure in-place, because ice/water boundary tracking would break; (3) **Per-type VTK actor dictionary** — not single-actor scalar coloring, because VTK's vtkMoleculeMapper renders all atoms with one style (can't mix VDW spheres and lines); (4) **Custom IonInserter** — not GenIce2's cation/anion system, because Tab 4 needs concentration-based placement in liquid phase, not index-based replacement in a lattice.

**Major components:**
1. **HydrateStructureGenerator** (NEW) — Wraps GenIce2 hydrate API with `guests` parameter; produces HydrateResult
2. **IonInserter** (NEW) — Concentration-based NaCl placement in liquid region using cKDTree overlap detection
3. **HydrateResult / InsertedStructure** (NEW) — Dataclasses with per-atom molecule type tagging for multi-type rendering
4. **Multi-actor VTK viewer** (EXTEND) — Dictionary of {molecule_type: (mapper, actor)} pairs with per-type styles
5. **Multi-type GROMACS writer** (EXTEND) — Multiple `[moleculetype]` sections with bundled .itp includes

### Critical Pitfalls

1. **Variable atoms-per-molecule breaks everything (Pitfall #5)** — The entire codebase iterates assuming uniform molecule size. Adding ions (1 atom) and guests (5+ atoms) shatters this assumption. Must design a molecule-segment index structure before ANY v4.0 code works.

2. **GenIce2 `guests` requires nested dict, not list (Pitfall #1)** — `guests={'12': {'ch4': 1.0}, '14': {'ch4': 1.0}}`, not a list. Wrong format crashes with cryptic `AttributeError`. Write adapter function with validation.

3. **Ion insertion must only replace liquid water, never ice (Pitfall #4)** — Accidentally replacing ice molecules destroys the crystal structure silently. Guard assertions: `assert mol_start_idx >= iface.ice_atom_count`.

4. **Multi-molecule GROMACS topology requires multiple `[moleculetype]` sections (Pitfall #3)** — The current single-SOL topology is invalid for systems with Na⁺, Cl⁻, and guest molecules. Must refactor writer to accept a list of molecule specifications.

5. **GenIce2 numpy random state not restored on exception (Pitfall #7)** — Pre-existing bug amplified by hydrate generation's higher exception likelihood. Move `set_state()` to `finally` block before any v4.0 work.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 0: Pre-requisite Fixes
**Rationale:** Four pre-existing bugs will silently corrupt results or crash the app during v4.0 development. Fixing them first prevents cascading failures.
**Delivers:** Stable foundation for multi-molecule work
**Addresses:** Pitfalls #7 (random state), #15 (missing T/P metadata), #16 (GRO parser duplication), #21 (dual is_cell_orthogonal)
**Avoids:** Polluted random state after hydrate errors; incorrect water density calculations; divergent cell-type detection

### Phase 1: Data Structures + GRO Parser Extension
**Rationale:** All downstream components (generators, viewers, exporters) need the multi-molecule data types and parser. This is the single biggest refactoring (Pitfall #5) and must be resolved before any Tab 2/4 code works.
**Delivers:** HydrateResult and InsertedStructure dataclasses, MoleculeType enum, `_parse_gro_multi_molecule()`, molecule-segment index structure
**Addresses:** Pitfalls #5 (atoms-per-molecule), #1 (GenIce2 guest dict adapter), #2 (lattice name mapping)
**Avoids:** All downstream code being built on broken assumptions

### Phase 2: Tab 4 — Ion Insertion (NaCl)
**Rationale:** Tab 4 reuses the most existing infrastructure (InterfaceStructure from Tab 3, cKDTree from overlap_resolver, GROMACS writer pattern). Proving multi-actor viewer and multi-type export with simpler ion insertion reduces risk before hydrate generation.
**Delivers:** IonInserter class, InsertPanel UI, InsertionWorker, 4-actor VTK viewer (ice, water, Na⁺, Cl⁻), multi-type GROMACS export, bundled ions-na-cl.itp
**Uses:** scipy cKDTree, existing overlap_resolver, Joung-Cheatham parameters
**Implements:** InsertedStructure pipeline, per-type VTK rendering, multi-moltype GROMACS writer
**Avoids:** Pitfalls #4 (ice replacement — guard assertions), #6 (electroneutrality — pair Na⁺ with Cl⁻), #8 (cross-tab volume dependency), #10 (atom-type overlap thresholds)

### Phase 3: Tab 2 — Hydrate Generation
**Rationale:** Requires a completely new GenIce2 API path (guests parameter, cage-based occupancy). Building after Phase 2 means the multi-actor viewer and multi-type export patterns are already proven.
**Delivers:** HydrateStructureGenerator, HydratePanel UI, HydrateGenerationWorker, 2-actor VTK viewer (water + guest), hydrate GROMACS export, bundled ch4.itp and co2.itp
**Uses:** GenIce2 hydrate lattices (CS1, CS2), molecule plugins (ch4, co2)
**Implements:** Separate generation pipeline (no phase lookup, no ranking)
**Avoids:** Pitfalls #12 (hydrate unit cells differ), #14 (separate pipeline, not Tab 1 modification)

### Phase 4: Custom Molecules + Display Controls
**Rationale:** Both Tab 2 and Tab 4 need custom molecule support. Building it last lets the basic NaCl and CH₄ flows stabilize first. File upload and validation add complexity best handled when core paths work.
**Delivers:** Custom .gro/.itp file upload, MoleculeTypeControls widget (visibility/style/color), custom molecule placement, .itp file bundling in export, molecule validation
**Avoids:** Pitfalls #9 (.itp file paths — copy to output directory), #19 (PBC boundary crossing — molecule-as-unit wrapping)

### Phase Ordering Rationale

- **Phase 0 before everything else:** Pre-existing bugs will silently corrupt results during v4.0 development. Fixing random state pollution (#7) is critical because hydrate generation is more likely to throw exceptions.
- **Phase 1 before Phases 2/3:** The variable atoms-per-molecule problem (#5) affects ALL downstream code. Every file that iterates over molecules, creates bonds, or writes GROMACS coordinates assumes uniform molecule size.
- **Phase 2 before Phase 3:** Tab 4 (ion insertion) reuses existing InterfaceStructure and overlap_resolver — it's simpler to implement and validates the multi-actor viewer and multi-type GROMACS export pattern with fewer unknowns.
- **Phase 4 last:** Custom molecule upload requires file validation, PBC wrapping, and per-type display controls. Getting the built-in molecule flows working first provides stable patterns to extend.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Multi-molecule data structure design — the molecule-segment index structure is the foundational decision; needs detailed design review before implementation
- **Phase 3:** GenIce2 hydrate API — the `guests` parameter format is undocumented in README; only discoverable from source code. The adapter function needs careful testing with each guest molecule type

Phases with standard patterns (skip research-phase):
- **Phase 0:** All four fixes are well-understood bugs with clear solutions documented in PITFALLS.md
- **Phase 2:** Ion insertion follows established patterns (cKDTree overlap, QThread worker, GROMACS writer)
- **Phase 4:** File upload and validation follow standard PySide6 patterns (QFileDialog, QProgressDialog)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | No new dependencies. All capabilities verified: GenIce2 hydrate API tested, VTK multi-actor tested, cKDTree overlap tested. Joung-Cheatham parameters are published standard values. |
| Features | **MEDIUM-HIGH** | v4.0 scope is clearly defined in v4-context.md. Custom molecule upload has moderate ambiguity (file validation edge cases). Hydrate guest occupancy UI needs design decision. |
| Architecture | **HIGH** | MVVM pattern well-established in existing codebase. New tabs follow exact same Panel→ViewModel→Worker→Domain pattern. Anti-patterns documented and preventable. |
| Pitfalls | **HIGH** | 21 pitfalls identified from direct codebase analysis and live GenIce2 testing. Phase 0 bugs are pre-existing with clear fixes. Critical Pitfall #5 (atoms-per-molecule) has explicit solution paths. |

**Overall confidence:** HIGH

### Gaps to Address

- **Custom molecule .itp compatibility:** CH₄ and CO₂ parameters are well-established but need verification for exact compatibility with the existing AMBER-force-field-based `tip4p-ice.itp`. Handle during Phase 4 implementation.
- **GenIce2 hydrate occupancy UI:** The `guests` dict format (`{'12': {'ch4': 1.0}}`) uses cage type numbers that aren't user-friendly. Need design for how users specify guest/cage occupancy in the HydratePanel. Handle during Phase 3 planning.
- **Liquid volume calculation for Tab 4:** InterfaceStructure currently doesn't carry `liquid_volume_nm3`. This field must be added during Phase 2 and computed by each interface mode (slab/pocket/piece). Handle during Phase 2 planning.
- **Large-system VTK performance:** Multi-actor rendering with >5 actors for >100K atoms may need LOD optimization. Defer until performance testing in Phase 2/3.
- **Force field compatibility:** Joung-Cheatham ions are parameterized for TIP4P water models, but the exact combination with TIP4P-ICE hasn't been validated in simulation. This is a user responsibility (GROMACS energy minimization will reveal issues), but we should document the combination.

## Sources

### Primary (HIGH confidence)
- **QuickIce codebase (v3.5)** — Direct analysis of generator.py, viewmodel.py, workers.py, vtk_utils.py, gromacs_writer.py, overlap_resolver.py, interface_builder.py, molecular_viewer.py, interface_viewer.py, export.py
- **GenIce2 source code (v2.2.13.1)** — GenIce class, `guests` parameter, Stage7 guest placement, `generate_ice()` with guests, lattice plugins (CS1, CS2, sI, sII), molecule plugins (ch4, co2, H2, thf, one)
- **Live GenIce2 API testing** — Verified: hydrate generation with CH₄ in sI structure (46 SOL + 8 CH₄), case-sensitive lattice names, guest dict format
- **VTK 9.5.2 multi-actor testing** — Verified: separate vtkMoleculeMapper + vtkActor per molecule type with different styles works correctly
- **Joung & Cheatham (2008)** — "Determination of Alkali and Halide Monovalent Ion Parameters," J. Phys. Chem. B, 112, 9020-9041. Standard published parameters.
- **v4-context.md** — Feature specification for molecule insertion

### Secondary (MEDIUM confidence)
- **GROMACS topology conventions** — Multi-molecule `[moleculetype]` sections, `#include` path resolution. Not yet tested with actual `gmx grompp` validation.
- **OPLS-AA parameters for CH₄** — Standard literature values for methane topology. Need verification for exact TIP4P-ICE compatibility.

### Tertiary (LOW confidence)
- **Custom molecule .gro parsing edge cases** — Users may provide unusual residue formats. Validation will be needed during implementation.
- **VTK performance with >5 actors and >100K atoms** — May need LOD optimization. Not yet benchmarked.

---
*Research completed: 2026-04-14*
*Ready for roadmap: yes*