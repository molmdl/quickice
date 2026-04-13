# QuickIce State

**Project:** QuickIce - Condition-based Ice Structure Generation
**Core Value:** Generate plausible ice structure candidates and interfaces quickly with intuitive visual interface
**Current Focus:** v3.5 shipped (water density deferred to v4.0)

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-14)

**Core value:** Generate plausible ice structure candidates and interfaces quickly with intuitive visual interface

**Current focus:** Complete water density integration (Phase 23 deferred work), then v4.0 planning

**Tech stack:**
- PySide6 6.10.2 (LGPL, MIT-compatible)
- VTK 9.5.2 (BSD-licensed)
- Matplotlib Qt backend
- GenIce2, spglib, numpy, scipy, iapws
- MVVM architecture with QThread workers

---

## Current Position

| Field | Value |
|-------|-------|
| Milestone | v3.5 shipped (partial - water density deferred) |
| Phase | — (ready for v4.0 planning) |
| Plan | — |
| Status | Ready to plan v4.0 or complete Phase 23 water density |
| Last activity | 2026-04-14 — Milestone archived, water density deferred |

**Progress:** ██████████ 100% (v3.5 shipped with deferred items)

---

## Milestone History

### v3.5 Interface Enhancements (SHIPPED 2026-04-13 - PARTIAL)

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
- Documentation: readme, in-app help, tab 2 tooltips

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
| scipy cKDTree for PBC | ✓ Automatic periodic boundary handling |
| Phase-distinct coloring | ✓ Ice=cyan, water=cornflower blue |
| Line-based bonds (Tab 2) | ✓ Performance for large systems |
| Single SOL molecule type | ✓ Simplifies GROMACS topology |
| Ctrl+I for interface export | ✓ No conflict with Ctrl+G |
| Native triclinic handling | ✓ Ice V/VI work, Ice II blocked |
| GROMACS atom wrapping at 100k | ✓ Large systems supported |

### v3.5 Shipped Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| IAPWS library for density | Already in environment, scientifically accurate | ✓ Shipped |
| Direct iapws._iapws._Ice usage | Already implements IAPWS R10-06(2009) | ✓ Shipped |
| Native triclinic instead of transformation | Transformation creates gaps during tiling | ✓ Shipped |
| Ice II blocked for interfaces | Rhombohedral crystal incompatible | ✓ Shipped |
| GROMACS atom number wrapping at 100000 | Standard convention for large systems | ✓ Shipped |

### Blockers

(None)

### Known Issues (to investigate)

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

---

## Session Continuity

**Last session:** 2026-04-14
**Completed:** v3.5 milestone archived (water density deferred)
**Next:** Complete Phase 23 water density integration OR start v4.0 planning

---

*State updated: 2026-04-14 — v3.5 shipped, water density deferred to v4.0*
