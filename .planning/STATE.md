# QuickIce State

**Project:** QuickIce - Condition-based Ice Structure Generation
**Core Value:** Generate plausible ice structure candidates, interfaces, and hydrates quickly with an intuitive visual interface
**Current Focus:** v4.5 Solute & Custom Molecule Insertion — Phase 34.3 inserted (tab order swap)

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-05)

**Core value:** Generate plausible ice structure candidates, interfaces, and hydrates quickly with an intuitive visual interface

**Current focus:** v4.5 Solute & Custom Molecule Insertion — Phase 34.3 inserted (tab order swap)

**Tech stack:**
- PySide6 6.10.2 (LGPL, MIT-compatible)
- VTK 9.5.2 (BSD-licensed)
- GenIce2 2.2.13.1, spglib, numpy, scipy, iapws
- MVVM architecture with QThread workers

---

## Current Position

| Field | Value |
|-------|-------|
| Milestone | v4.5 Solute & Custom Molecule Insertion |
| Phase | 34.3 - Tab Order Swap |
| Plan | 1 of 1 complete |
| Status | Phase complete |
| Last activity | 2026-05-07 — Completed 34.3-01-PLAN.md (tab swap for Custom→Solute workflow) |

**Progress:** █████████░ 90% (Phase 32-34.3 complete, Phase 35 paused for re-planning)

---

## Milestone History

### v4.5 Solute & Custom Molecule Insertion (IN PROGRESS)

**Phases:** 32-35 (6 phases planned)
**Requirements:** 39 total (ARCH: 7, SOLUTE: 9, CUSTOM: 12, VIS: 3, GROMACS: 3, DOCS: 5)
**Progress:** Phase 32-34.2 complete, Phase 34.3 inserted, Phase 35 paused for re-planning (36 requirements satisfied, 3 pending)
**Key features in progress:**
- ✓ Tab index constants and MoleculetypeRegistry
- ✓ ITP parser and molecule validator
- ✓ TabIndex refactoring complete
- ✓ Solute insertion tab (Tab 4) with THF/CH₄ concentration placement
- ✓ All-atom overlap checking for multi-atom molecules
- ✓ Ball-and-stick rendering with CPK colors
- ✓ Custom molecule validation infrastructure (GRO residue extraction)
- ✓ Custom molecule renderer with distinct colors (purple, cyan, yellow)
- ✓ Custom molecule insertion logic (CustomMoleculeInserter with two placement modes)
- ✓ Custom molecule upload tab (Tab 5) UI components (CustomMoleculePanel, CustomMoleculeWorker, CustomMoleculeViewerWidget)
- ✓ Tab reordering complete (Ion moves to Tab 6)
- ✓ GROMACS export with custom .itp bundling
- ✓ Integration tests for custom molecule workflow
- ✓ Unified export keyboard shortcut (Ctrl+S)
- ✓ Molecule ordering verification tests
- ✓ Ion source dropdown with charge warning
- ✓ Liquid solute ITP files with CH4_LIQ/THF_LIQ names
- ✓ Export pipeline uses correct ITP files for liquid solutes
- ⏳ Documentation and remaining keyboard shortcuts

**Roadmap:** [.planning/ROADMAP.md](./ROADMAP.md)

### v4.0 Molecule Insertion (SHIPPED 2026-05-01)

**Phases:** 28-31.2 (7 phases, 29 plans, 4 inserted decimal phases)
**Requirements:** 19 satisfied, 11 deferred to v4.5, 3 pending
**Key features delivered:**
- Hydrate generation (sI, sII, sH with CH4/THF guests)
- Dual-style 3D rendering (water lines, guest ball-and-stick)
- Ion insertion (Na+/Cl- with Madrid2019 parameters)
- Multi-molecule GROMACS export
- Four-tab workflow (Ice, Hydrate, Interface, Ion)

**Archive:** [.planning/milestones/v4.0-ROADMAP.md](./milestones/v4.0-ROADMAP.md)

### v3.5 Interface Enhancements (SHIPPED 2026-04-13)

**Phases:** 22, 24-27 shipped; Phase 23 deferred
**Requirements:** 11 shipped, 4 deferred (WATER-01 to WATER-04)
**Key features delivered:**
- Ice Ih IAPWS density (temperature-dependent, replaces 0.9167 g/cm³)
- Native triclinic handling (Ice V, Ice VI work; Ice II blocked)
- CLI interface generation (--interface flag with full parameters)
- Crystal system documentation corrected

**Deferred:**
- Water density integration (Tab 1 display, Tab 2 interface spacing)

**Archive:** [.planning/milestones/v3.5-ROADMAP.md](./milestones/v3.5-ROADMAP.md)

### v3.0 Interface Generation (Shipped 2026-04-11)

**Phases:** 16-21 (6 phases, 15 plans)
**Key features:**
- Tab infrastructure: Ice Generation + Interface Construction tabs
- Configuration controls: mode, boxsize, thickness, seed inputs
- Structure generation: slab/pocket/piece modes with collision detection
- Visualization: phase-distinct coloring in single VTK viewer
- Export: GROMACS files with phase distinction (single SOL)

**Archive:** [.planning/milestones/v3.0-ROADMAP.md](./milestones/v3.0-ROADMAP.md)

### v2.1.1 Phase Diagram Data Update (Shipped 2026-04-08)

**Phase:** 15 (9 plans)
**Archive:** [.planning/milestones/v2.1.1-ROADMAP.md](./milestones/v2.1.1-ROADMAP.md)

### v2.1 GROMACS Export (Shipped 2026-04-07)

**Phases:** 14 (8 plans)
**Archive:** [.planning/milestones/v2.1-ROADMAP.md](./milestones/v2.1-ROADMAP.md)

### v2.0 GUI Application (Shipped 2026-04-04)

**Phases:** 8-13 (28 plans)
**Archive:** [.planning/milestones/v2.0-ROADMAP.md](./milestones/v2.0-ROADMAP.md)

### v1.1 Hotfix (Shipped 2026-03-31)

**Archive:** [.planning/milestones/v1.1-ROADMAP.md](./milestones/v1.1-ROADMAP.md)

### v1.0 MVP (Shipped 2026-03-29)

**Archive:** [.planning/milestones/v1-ROADMAP.md](./milestones/v1-ROADMAP.md)

---

## Accumulated Context

### Roadmap Evolution

- Phase 34.1 inserted after Phase 34: Ion Source Dropdown with charge warning (URGENT)
- Phase 34.2 inserted after Phase 34.1: Fix liquid solute ITP export with proper residue names (URGENT)
- Phase 34.3 inserted after Phase 34.2: Tab order swap (Custom→Tab 4, Solute→Tab 5) to enable Custom→Solute workflow (URGENT)

### v4.5 Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| TabIndex enum for tab positions | Prevents hardcoded index bugs after reordering | ✓ Shipped (32-01) |
| MoleculetypeRegistry for molecule tracking | Unique GROMACS naming (CH4_HYD vs CH4_LIQ) | ✓ Shipped (32-01) |
| ITP parser with regex parsing | Extracts molecule info from .itp files without dependencies | ✓ Shipped (32-01) |
| Molecule validator with specific errors | GRO/ITP consistency validation with clear user feedback | ✓ Shipped (32-02) |
| TabIndex enum for all indices | All hardcoded tab indices replaced with named constants | ✓ Shipped (32-02) |
| Optional registry parameter | Backward-compatible GROMACS export with future registry support | ✓ Shipped (32-02) |
| Tab structure documentation | Current and planned tab order documented in code | ✓ Shipped (32-03) |
| Cross-tab data flow verification | Verified Ice→Interface, Hydrate→Interface, Interface→Ion | ✓ Shipped (32-03) |
| Solute renderer follows hydrate pattern | Consistency with existing ball-and-stick rendering | ✓ Shipped (33-02) |
| All-atom overlap checking | Multi-atom molecules need full overlap check (not center-of-mass) | ✓ Shipped (33-01) |
| Rotation matrices for molecule orientation | Multi-atom molecules have orientation | ✓ Shipped (33-01) |
| SoluteViewerWidget extends QWidget | GenericViewerWidget doesn't exist, follows IonViewerWidget pattern | ✓ Shipped (33-03) |
| Real-time preview on valueChanged | User sees molecule count update while typing concentration | ✓ Shipped (33-03) |
| Concentration range 0.0-2.0 M | Based on typical solute concentrations | ✓ Shipped (33-03) |
| GAFF2 parameters for THF/CH₄ solutes | Consistent with hydrate guest parameters | ✓ Shipped (33-01) |
| GRO residue name extraction | Fixed-width column parsing (cols 6-10) | ✓ Shipped (34-01) |
| Residue name mismatch as non-blocking | Triggers UI dialog for user choice | ✓ Shipped (34-01) |
| Custom molecule distinct colors | Purple, cyan, yellow to differentiate from predefined molecules | ✓ Shipped (34-03) |
| Custom molecule renderer follows solute pattern | Consistency with ball-and-stick rendering, same bond threshold | ✓ Shipped (34-03) |
| CustomMoleculeConfig two-mode pattern | Random/custom placement with validation | ✓ Shipped (34-01) |
| Euler angles for custom rotation | ZXZ convention via scipy Rotation.from_euler | ✓ Shipped (34-02) |
| Two placement modes | Random (with overlap checking) and custom (user responsibility) | ✓ Shipped (34-02) |
| InsertionError for placement failures | Provides attempt count for user feedback | ✓ Shipped (34-02) |
| User-provided [ atomtypes ] required | Avoids force field database complexity | ⏳ Planned |
| Euler angles for UI input | More intuitive than rotation matrices | ✓ Shipped (34-04) |
| Separate file upload buttons | User can upload .gro and .itp files separately | ✓ Shipped (34-04) |
| Residue name mismatch dialog | ITP name override option for user choice | ✓ Shipped (34-04) |
| Placement mode dropdown | Dynamic controls for Random vs Custom mode | ✓ Shipped (34-04) |
| Unified Ctrl+S export | Qt standard "Save" action for active tab export | ✓ Shipped (35-01) |
| Hydrate shortcut Ctrl+H | More intuitive than Ctrl+E (H for hydrate) | ✓ Shipped (35-01) |
| Export As... submenu | Tab-specific exports for discoverability | ✓ Shipped (35-01) |
| Molecule ordering tests | Verification via .gro file parsing | ✓ Shipped (35-01) |
| Ion source dropdown follows Interface pattern | Consistency in source selection UI across tabs | ✓ Shipped (34.1-01) |
| Source change handler with immediate UI effect | Real-time feedback, not deferred to Generate time | ✓ Shipped (34.1-02) |
| Charge warning for Custom Molecule source | Non-neutral charge detection for custom molecules | ✓ Shipped (34.1-02) |
| Ion configuration always neutral | Equal Na+/Cl- with Madrid2019 charges (±0.85) | ✓ Shipped (34.1-02) |
| Manual QApplication setup for tests | Avoids pytest-qt dependency, matches project pattern | ✓ Shipped (34.1-03) |
| Comprehensive test coverage (11 tests) | Exceeds minimum 8 tests for better coverage | ✓ Shipped (34.1-03) |
| Hydrate shortcut Ctrl+H | More intuitive than Ctrl+E (H for hydrate) | ✓ Shipped (35-01) |
| Export As... submenu | Tab-specific exports for discoverability | ✓ Shipped (35-01) |
| Molecule ordering tests | Verification via .gro file parsing | ✓ Shipped (35-01) |
| Separate liquid solute ITP files | CH4_LIQ and THF_LIQ distinct from hydrate guests | ✓ Shipped (34.2-01) |
| Liquid solute ITP export logic | Exporters use {type}_liquid.itp for solutes | ✓ Shipped (34.2-02) |
| Copy-existing-ITP pattern | Preserve force field parameters exactly | ✓ Shipped (34.2-01) |
| Tab order swap (Custom before Solute) | Enables Custom → Solute → Ion workflow chain | ✓ Shipped (34.3-01) |

### v4.0 Key Decisions (Shipped)

| Decision | Rationale | Status |
|----------|-----------|--------|
| MoleculeIndex dataclass | Variable atoms-per-molecule tracking | ✓ Shipped |
| HydrateConfig/HydrateLatticeInfo | Configuration management | ✓ Shipped |
| Madrid2019 ion parameters | Scientifically validated charges (±0.85) | ✓ Shipped |
| GAFF2 guest parameters | CH4/THF topology for GROMACS | ✓ Shipped |
| Dual-style hydrate rendering | Water lines + guest ball-and-stick | ✓ Shipped |
| Concentration-based ion placement | mol/L → ion count calculation | ✓ Shipped |
| Per-type VTK actors | Multi-molecule visualization | ✓ Shipped |
| Tab order: Ice→Hydrate→Interface→Ion | User-approved deviation | ✓ Shipped |

### Blockers

**Phase 35 documentation plans need re-planning:**
- Phase 35-02 to 35-06 reference incorrect tab numbers (Solute=Tab 4, Custom=Tab 5)
- After Phase 34.3 completes (tab swap), all documentation plans need to be re-created
- 35-01 (unified export) is complete but references old tab order

**User-identified issues (from 35-01 checkpoint):**
- Missing function found during verification
- Documentation may need redo
- User suggests considering adding a phase before continuing with docs

**Recommendation:** Complete Phase 34.3 first, then re-plan Phase 35 documentation (35-02 to 35-06) with correct tab numbering

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 016 | ❌ REVERTED: Minimize bundle dependencies (broke executable) | 2026-05-04 | N/A (reverted) | [016-minimize-bundle-dependencies](./quick/016-minimize-bundle-dependencies/) |
| 008 | Optimize PyInstaller bundle size | 2026-05-03 | deae8b8 | [008-optimize-pyinstaller-bundle-size](./quick/008-optimize-pyinstaller-bundle-size/) |
| 007 | Code quality improvements (logging, deduplication, validation) | 2026-05-02 | 886ce83 | [007-code-quality-improvements-logging-dedu](./quick/007-code-quality-improvements-logging-dedu/) |
| 006 | Add GAFF2 preparation method citation to main documentation | 2026-04-30 | f319157 | [006-add-gaff2-preparation-method-citation-to](./quick/006-add-gaff2-preparation-method-citation-to/) |

### Pending Todos

- [2026-05-07] prepare custom molecule gro top to test custom mol fx (testing) — `.planning/todos/pending/2026-05-07-prepare-custom-molecule-gro-top-to-test-custom-mol-fx.md`
- [2026-05-07] Group UAT items by workflow for batch testing (testing) — `.planning/todos/pending/2026-05-07-group-uat-items-by-workflow-for-batch-testing.md`
- [2026-05-07] Capture screenshots per Phase 35 suggestions (docs) — `.planning/todos/pending/2026-05-07-capture-screenshots-per-phase-35-suggestions.md`

---

## Archive Reference

- v1.0: [.planning/milestones/v1-ROADMAP.md](./milestones/v1-ROADMAP.md)
- v1.1: [.planning/milestones/v1.1-ROADMAP.md](./milestones/v1.1-ROADMAP.md)
- v2.0: [.planning/milestones/v2.0-ROADMAP.md](./milestones/v2.0-ROADMAP.md)
- v2.1: [.planning/milestones/v2.1-ROADMAP.md](./milestones/v2.1-ROADMAP.md)
- v2.1.1: [.planning/milestones/v2.1.1-ROADMAP.md](./milestones/v2.1.1-ROADMAP.md)
- v3.0: [.planning/milestones/v3.0-ROADMAP.md](./milestones/v3.0-ROADMAP.md)
- v3.5: [.planning/milestones/v3.5-ROADMAP.md](./milestones/v3.5-ROADMAP.md)
- v4.0: [.planning/milestones/v4.0-ROADMAP.md](./milestones/v4.0-ROADMAP.md)

---

## Session Continuity

**Last session:** 2026-05-07
**Completed:** Phase 34.3 complete (Tab order swap - Custom Tab 3, Solute Tab 4)
**Next:** Re-plan Phase 35 documentation with correct tab numbering

---
*State updated: 2026-05-07 — Phase 34.3 complete*
