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
| Phase | 28 (pre-requisite fixes) |
| Plan | 01 of 03 |
| Status | In progress |
| Last activity | 2026-04-14 — Completed 28-01-PLAN.md |

**Progress:** ░░░░░░░░░░ 0% (5 phases, 0 plans executed)

---

## v4.0 Roadmap Summary

**Phases:** 5 (Phases 28-32)
**Requirements:** 33 (HYDR, ION, CUST, VIEW, GRO, WATER)
**Depth:** comprehensive

| Phase | Goal | Requirements |
|-------|------|--------------|
| 28 | Pre-requisite Fixes | — (internal bug fixes) |
| 29 | Data Structures + Multi-Molecule GROMACS | GRO-01 to GRO-03, HYDR-01 to HYDR-05 |
| 30 | Tab 4 - Ion Insertion (NaCl) | ION-01 to ION-07, WATER-02 |
| 31 | Tab 2 - Hydrate Generation | HYDR-06 to HYDR-08, WATER-03 |
| 32 | Custom Molecules + Display Controls | CUST-01 to CUST-07, VIEW-01 to VIEW-04, WATER-04 |

**Coverage:** 33/33 requirements mapped ✓

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
| Variable atoms-per-molecule | Critical Pitfall #5 - must resolve before Tab 2/4 code works | Pending Phase 29 |
| IonInserter class | Concentration-based placement, not lattice replacement | Pending Phase 30 |
| HydrateStructureGenerator | Separate pipeline from ice generation (no phase lookup, no ranking) | Pending Phase 29/31 |
| Per-type VTK actors | One vtkMoleculeMapper + vtkActor per molecule type | Pending Phase 30 |
| Random state with finally block | Pitfall #7 - fixed in 28-01 | ✓ Implemented |
| T/P in Candidate metadata | Pitfall #15 - fixed in 28-01 | ✓ Implemented |

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

**Last session:** 2026-04-14
**Completed:** 28-01-PLAN.md (Phase 28 pre-requisite bug fixes)
**Next:** 28-02-PLAN.md (remaining plans in Phase 28)

---

*State updated: 2026-04-14 — v4.0 roadmap defined, ready for Phase 28 planning*