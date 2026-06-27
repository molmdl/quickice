# QuickIce State

**Project:** QuickIce - Condition-based Ice Structure Generation
**Core Value:** Generate ready-to-use initial models and topologies for GROMACS for the simulation of ice, hydrates, solutes, and custom molecules in water
**Current Focus:** Planning next milestone

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-27)

**Core value:** Generate ready-to-use initial models and topologies for GROMACS for the simulation of ice, hydrates, solutes, and custom molecules in water

**Current focus:** Planning next milestone

**Tech stack:**
- Python 3.14, PySide6 6.10.2, VTK 9.5.2
- GenIce2 2.2.13.1, spglib, numpy, scipy, iapws
- MVVM architecture with QThread workers
- Unified CLI+GUI entry point (`python -m quickice`)

---

## Current Position

| Field | Value |
|-------|-------|
| Milestone | v4.5 SHIPPED — archived |
| Phase | — |
| Plan | — |
| Status | Ready for next milestone via `/gsd-new-milestone` |
| Last activity | 2026-06-27 — v4.5 milestone archived |

**Progress:** N/A — milestone complete

---

## Milestone History

### v4.5 Solute & Custom Molecule Insertion (SHIPPED 2026-06-27)

**Phases:** 32-37.2 + e2e-export/api/compute (20 phases, 131 plans)
**Requirements:** 44 total (ARCH: 7, SOLUTE: 9, CUSTOM: 12, VIS: 3, GROMACS: 3, DOCS: 5, CLI: 5)
**Key features delivered:**
- Six-tab workflow (Ice, Hydrate, Interface, Custom, Solute, Ion) with cross-tab data flow
- Solute insertion (THF/CH₄) with concentration-based placement
- Custom molecule upload (.gro/.itp) with validation, random/custom placement, preview
- CLI feature parity (full 6-step pipeline)
- Unified entry point (`python -m quickice`)
- 45 GROMACS grompp validation tests
- Critical bug fixes (TIP4P-ICE LJ parameters, PBC wrapping, comb-rule, DOIs)

**Tech debt:**
- SoluteStructure.molecule_indices naming (tuple vs MoleculeIndex — working workaround)
- Liquid volume TODO (uses total box volume instead of liquid region)
- 2 missing low-priority screenshots
- Stale code comments in main_window.py

**Archive:** [.planning/milestones/v4.5-ROADMAP.md](./milestones/v4.5-ROADMAP.md)

### v4.0 Molecule Insertion (SHIPPED 2026-05-01)

**Phases:** 28-31.2 (7 phases, 29 plans, 4 inserted decimal phases)
**Requirements:** 19 satisfied, 11 deferred to v4.5, 3 pending
**Key features delivered:**
- Hydrate generation (sI, sII, sH with CH4/THF guests)
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

**Archive:** [.planning/milestones/v3.5-ROADMAP.md](./milestones/v3.5-ROADMAP.md)

### v3.0 Interface Generation (Shipped 2026-04-11)

**Phases:** 16-21 (6 phases, 15 plans)
**Archive:** [.planning/milestones/v3.0-ROADMAP.md](./milestones/v3.0-ROADMAP.md)

### v2.1.1 Phase Diagram Data Update (Shipped 2026-04-08)

**Phases:** 15 (9 plans)
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

### Pending Todos

- [2026-06-20] Decide disposition of 26 rogue pip packages in quickice env (tooling)
- [2026-05-24] Pre-built small molecules for custom mol with GROMACS format (feature)
- [2026-05-16] Install UPX for bundle compression (tooling)
- [2026-05-07] Capture screenshots per Phase 35 suggestions (docs)
- [2026-05-09] Provide CLI-only executable for automation (tooling)
- [2026-05-09] Support flexible interface construction modes (feature)
- [2026-05-09] Explore complex hydrate formation using atomsk (research)

### Deferred Items

- PERF-01: wrap_molecules_into_box triple-nested Python loop (performance, not correctness)
- PERF-04: Nested loops in guest molecule detection (N is small, low impact)
- TEST-03: Triclinic cell interface tests (blocked by Ice II rejection)
- TEST-06: VTK rendering fallback path (headless VTK tricky)
- Bundle optimization (scipy collect_all, GenIce2 narrowing, CLI-only binary)

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
- v4.5: [.planning/milestones/v4.5-ROADMAP.md](./milestones/v4.5-ROADMAP.md)

---
*State updated: 2026-06-27 — v4.5 milestone archived, ready for next milestone*
