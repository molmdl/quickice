# QuickIce State

**Project:** QuickIce - Condition-based Ice Structure Generation
**Core Value:** Generate plausible ice structure candidates and interfaces quickly with intuitive visual interface
**Current Focus:** v4.0 Molecule Insertion (5 phases defined)

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-14)

**Core value:** Generate plausible ice structure candidates and interfaces quickly with intuitive visual interface

**Current focus:** v4.0 milestone: molecule insertion (hydrates, ions, custom molecules, viewer enhancements)

**Tech stack:**
- PySide6 6.10.2 (LGPL, MIT-compatible)
- VTK 9.5.2 (BSD-licensed)
- GenIce2 2.2.13.1, spglib, numpy, scipy, iapws
- MVVM architecture with QThread workers

---

## Current Position

| Field | Value |
|-------|-------|
| Milestone | v4.0 (in progress) |
| Phase | 28.1 (complete) |
| Plan | 03 of 03 complete |
| Status | Phase complete |
| Last activity | 2026-04-18 — Phase 28.1 human verified (tab ordering approved, ion insertion partially fixed) |

**Progress:** ███████░░ 70% (3.5/6 phases complete - Phase 28.1 in progress)

---

## v4.0 Roadmap Summary

**Phases:** 5 (Phases 28-32)
**Requirements:** 33 (HYDR, ION, CUST, VIEW, GRO, WATER)
**Depth:** comprehensive

| Phase | Goal | Requirements |
|-------|------|--------------|
| 28 | Pre-requisite Fixes | — (internal bug fixes) |
| 28.1 | Urgent Bugfixes + FF Corrections | — (bugfixes, FF corrections) |
| 29 | Data Structures + Multi-Molecule GROMACS | GRO-01 to GRO-03, HYDR-01 to HYDR-05 |
| 30 | Tab 4 - Ion Insertion (NaCl) | ION-01 to ION-07, WATER-02 |
| 31 | Tab 2 - Hydrate Generation | HYDR-06 to HYDR-08, WATER-03 |
| 32 | Custom Molecules + Display Controls | CUST-01 to CUST-07, VIEW-01 to VIEW-04, WATER-04 |

**Coverage:** 33/33 requirements mapped ✓

---

## Roadmap Evolution

- Phase 28.1 inserted after Phase 28: Urgent Bugfixes + FF Corrections (URGENT) — discovered during Phase 31 execution

---

## Milestone History

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

### v4.0 Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| No new dependencies | GenIce2 hydrate API, scipy cKDTree, VTK multi-actor already available | Pending implementation |
| 5-phase structure | Research recommends: fixes → data structures → ion → hydrate → custom | Defined |
| Variable atoms-per-molecule | Critical Pitfall #5 - resolved via MoleculeIndex dataclass | ✓ Implemented (29-01) |
| HydrateConfig dataclass | Configuration for hydrate lattice generation with validation | ✓ Implemented (29-02) |
| HydrateLatticeInfo dataclass | Display info for hydrate lattice selection | ✓ Implemented (29-02) |
| HYDRATE_LATTICES constant | sI, sII, sH GenIce2 lattice info | ✓ Implemented (29-02) |
| GUEST_MOLECULES constant | ch4, thf only (co2, h2 removed in 28.1-02) | ✓ Implemented (29-02, updated 28.1-02) |
| IonInserter class | Concentration-based placement, not lattice replacement | ✓ Implemented (30-01) |
| gromacs_ion_export.py | ion.itp generator with [moleculetype] sections | ✓ Implemented (30-02) |
| Water density display | IAPWS-95 in Tab 1 info panel | ✓ Implemented (30-05) |
| HydrateStructureGenerator | Separate pipeline from ice generation (no phase lookup, no ranking) | Pending Phase 29/31 |
| Per-type VTK actors | One vtkMoleculeMapper + vtkActor per molecule type | Pending Phase 30 |
| MOLECULE_TO_GROMACS mapping | Internal types to GROMACS residue/itp names | ✓ Implemented (29-03) |
| write_multi_molecule_gro_file | Multi-molecule .gro export via MoleculeIndex | ✓ Implemented (29-03) |
| write_multi_molecule_top_file | #include-based topology with per-type counts | ✓ Implemented (29-03) |
| HydratePanel widget | UI widget for hydrate configuration (lattice/guest/occupancy) | ✓ Implemented (29-04) |
| IonRenderer class | VDW sphere creation for Na+ (gold) and Cl- (green) in 3D viewer | ✓ Implemented (30-04) |
| cKDTree overlap checking | Prevents ion overlap using MIN_SEPARATION (0.3 nm) | ✓ Implemented (30) |
| Random state with finally block | Pitfall #7 - fixed in 28-01 | ✓ Implemented |
| T/P in Candidate metadata | Pitfall #15 - fixed in 28-01 | ✓ Implemented |
| Shared GRO parser module | Duplicate code in generator/water_filler consolidated in 28-02 | ✓ Implemented |
| HydrateWorker class | QThread subclass for background hydrate generation with signals | ✓ Implemented (31-01) |
| HydrateRenderer dual-style | Water as lines (SetRenderAtoms=False), guests as ball-and-stick (UseBallAndStickSettings) | ✓ Implemented (31-02) |
| HydrateViewerWidget | QWidget with stacked placeholder/3D viewer, VTK availability check, camera auto-fit | ✓ Implemented (31-03) |
| HydratePanel integration | HydratePanel with viewer section, log panel, generation workflow wired to HydrateWorker | ✓ Implemented (31-04) |
| HydrateGROMACSExporter | Export hydrate structures to GROMACS .gro/.top/.itp with bundled guest parameters | ✓ Implemented (31-05) |
| Bundled guest .itp files | ch4.itp (GAFF methane), thf.itp (GAFF THF) for GROMACS export | ✓ Implemented (31-05) |
| Madrid2019 ion parameters | Na charge=0.85, Cl charge=-0.85 per research | ✓ Implemented (28.1-03) |
| GROMACS atomtype ordering | All [atomtypes] grouped after [defaults] before #include | ✓ Implemented (28.1-03) |
| Sobtop GAFF2 guest parameters | CH4/THF atomtypes commented in .itp, defined in main .top | ✓ Implemented (28.1-03) |

### v3.5 Shipped Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| IAPWS library for density | Already in environment, scientifically accurate | ✓ Shipped |
| Native triclinic instead of transformation | Transformation creates gaps during tiling | ✓ Shipped |
| Ice II blocked for interfaces | Rhombohedral crystal incompatible | ✓ Shipped |
| GROMACS atom number wrapping at 100000 | Standard convention for large systems | ✓ Shipped |

### Blockers

(None)

---

## Archive Reference

- v1.0: [.planning/milestones/v1-ROADMAP.md](./milestones/v1-ROADMAP.md)
- v1.1: [.planning/milestones/v1.1-ROADMAP.md](./milestones/v1.1-ROADMAP.md)
- v2.0: [.planning/milestones/v2.0-ROADMAP.md](./milestones/v2.0-ROADMAP.md)
- v2.1: [.planning/milestones/v2.1-ROADMAP.md](./milestones/v2.1-ROADMAP.md)
- v2.1.1: [.planning/milestones/v2.1.1-ROADMAP.md](./milestones/v2.1.1-ROADMAP.md)
- v3.0: [.planning/milestones/v3.0-ROADMAP.md](./milestones/v3.0-ROADMAP.md)
- v3.5: [.planning/milestones/v3.5-ROADMAP.md](./milestones/v3.5-ROADMAP.md)
- v4.0: [.planning/ROADMAP.md](./ROADMAP.md)

---

## Session Continuity

**Last session:** 2026-04-18
**Stopped at:** Phase 28.1 human verified (approved: tab ordering Ice→Hydrate→Interface→Ion, ion insertion partially fixed)
**Next:** Phase 29 ready - Data Structures + Multi-Molecule GROMACS required before Phases 30-32

---

*State updated: 2026-04-15 — Phase 28.1 inserted after Phase 28 for urgent bugfixes and FF corrections*