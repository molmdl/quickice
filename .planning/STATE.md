# QuickIce State

**Project:** QuickIce - Condition-based Ice Structure Generation
**Core Value:** Generate plausible ice structure candidates quickly with intuitive visual interface
**Current Focus:** v3.0 Interface Generation

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-08)

**Core value:** Generate plausible ice structure candidates quickly with intuitive visual interface

**Current focus:** v3.0 Interface Generation — 3 geometry modes + new input controls

**Tech stack:**
- PySide6 6.10.2 (LGPL, MIT-compatible)
- VTK 9.5.2 (BSD-licensed)
- Matplotlib Qt backend
- GenIce2, spglib, numpy, scipy
- MVVM architecture with QThread workers

---

## Current Position

| Field | Value |
|-------|-------|
| Milestone | v3.0 Interface Generation |
| Phase | 16 (Tab Infrastructure) |
| Plan | 01 complete |
| Status | Phase in progress |
| Last activity | 2026-04-08 — Completed 16-01-PLAN.md |

**Progress:** ██░░░░░░░░ 20% (1/5 plans complete)

---

## Milestone History

### v3.0 Interface Generation (Active)

**Phases:** 16-20 (5 phases)
**Key features:**
- Tab infrastructure: Ice Generation + Interface Construction tabs
- Configuration controls: mode, boxsize, thickness, seed inputs
- Structure generation: slab/pocket/piece modes with collision detection
- Visualization: phase-distinct coloring in single VTK viewer
- Export: GROMACS files with phase distinction (chain A=ice, chain B=water)

### v2.1.1 Phase Diagram Data Update (Shipped 2026-04-08)

**Phase:** 15 (9 plans)
**Key features:**
- Corrected 32 triple point values per IAPWS R14-08(2011) and Journaux et al. (2019, 2020)
- Added Ice Ic metastable phase region (72-150K, 0-204 MPa)
- Fixed all polygon overlaps (zero area overlaps across all phases)
- Added metastability documentation with literature citations
- Maintained 62/62 tests passing with corrected thermodynamic data

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

### Decisions Carried Forward

| Decision | Outcome |
|----------|---------|
| MVVM architecture | ✓ Clean separation |
| VTK for 3D | ✓ Full interactivity |
| PyInstaller bundling | ✓ Linux executable |
| Exact version pinning | ✓ All deps =x.y.z |
| TIP4P-ICE water model | ✓ GROMACS compatible |
| Single export action | ✓ .gro/.top/.itp together |
| IAPWS/Journaux data sources | ✓ Scientific accuracy |
| Ice Ic lower boundary at 72K | ✓ Zero polygon overlaps |
| Tab-based workflow | ✓ Two tabs for v3.0 |
| Collision detection | ✓ Mandatory for interface generation |

### Blockers

(None)

---

## Archive Reference

- v1.0: [.planning/milestones/v1-ROADMAP.md](./milestones/v1-ROADMAP.md)
- v1.1: [.planning/milestones/v1.1-ROADMAP.md](./milestones/v1.1-ROADMAP.md)
- v2.0: [.planning/milestones/v2.0-ROADMAP.md](./milestones/v2.0-ROADMAP.md)
- v2.1: [.planning/milestones/v2.1-ROADMAP.md](./milestones/v2.1-ROADMAP.md)
- v2.1.1: [.planning/milestones/v2.1.1-ROADMAP.md](./milestones/v2.1.1-ROADMAP.md)
- v3.0: [.planning/ROADMAP.md](./ROADMAP.md)

---

## Session Continuity

**Last session:** 2026-04-08 13:09
**Completed:** 16-01-PLAN.md (Tab Infrastructure foundation)
**Next:** Continue Phase 16 or start next plan in roadmap

---

*State updated: 2026-04-08 — Phase 16 Plan 01 complete*