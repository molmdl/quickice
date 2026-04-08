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
| Phase | 18 (Structure Generation) - In progress |
| Plan | 01 complete (1/4 plans) |
| Status | In progress |
| Last activity | 2026-04-08 — Completed 18-01-PLAN.md |

**Progress:** ██████░░░░ 62% (5/8 plans complete in v3.0)

---

## Milestone History

### v3.0 Interface Generation (Active)

**Phases:** 16-21 (6 phases)
**Key features:**
- Tab infrastructure: Ice Generation + Interface Construction tabs
- Configuration controls: mode, boxsize, thickness, seed inputs
- Structure generation: slab/pocket/piece modes with collision detection
- Visualization: phase-distinct coloring in single VTK viewer
- Export: GROMACS files with phase distinction (chain A=ice, chain B=water)
- Documentation: readme, in-app help, tab 2 tooltips

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
| Manual "Refresh candidates" button | ✓ User control over Tab 2 sync |
| Tab 2 keeps old candidates | ✓ Intentional behavior until refresh |
| Qt widget state preservation | ✓ Automatic state management |
| Slab/Pocket/Piece as mode options | ✓ Standard interface geometries |
| Box dimensions 0.5-100 nm | ✓ Typical simulation scale |
| Thickness/diameter 0.5-50 nm | ✓ Layer/cavity sizes |
| Seed 1-999999 | ✓ Wide reproducibility range |
| Piece mode informational label | ✓ Dimensions derived from candidate |
| Validate before generate signal | ✓ Prevents invalid configurations |
| Mode-specific validation | ✓ Only validate relevant parameters |
| Configuration dict with mode params | ✓ Clean data access pattern |
| All coordinates in nm internally | ✓ Å only for UI display |
| Overlap threshold 0.25 nm default | ✓ 2.5 Å for O-O distance |
| scipy cKDTree boxsize for PBC | ✓ Automatic periodic boundary handling |
| Ice atoms first in positions | ✓ water atoms follow, ice_atom_count marks boundary |
| Atom counts NOT normalized | ✓ ice=3, water=4 atoms/mol (export concern) |

### Roadmap Evolution

- Phase 21 added: Update readme, docs, in-app help, tab 2 tooltip help

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

**Last session:** 2026-04-08 17:24
**Completed:** 18-01-PLAN.md (Interface generation foundation)
**Next:** 18-02-PLAN.md (Slab mode implementation)

---

*State updated: 2026-04-08 — Plan 18-01 complete*