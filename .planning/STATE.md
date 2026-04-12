# QuickIce State

**Project:** QuickIce - Condition-based Ice Structure Generation
**Core Value:** Generate plausible ice structure candidates and interfaces quickly with intuitive visual interface
**Current Focus:** v3.5 Interface Enhancements — Roadmap created

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-12)

**Core value:** Generate plausible ice structure candidates and interfaces quickly with intuitive visual interface

**Current focus:** v3.5 Interface Enhancements — Roadmap created, phases 22-26 defined

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
| Milestone | v3.5 Interface Enhancements |
| Phase | 24 of 28 (triclinic-transformation) |
| Plan | 1 of 3 complete |
| Status | In progress |
| Last activity | 2026-04-12 — Completed 24-01 |

**Progress:** ██████████ 100% (Phase 24: 1/3 plans complete)

---

## Milestone History

### v3.5 Interface Enhancements (Active)

**Phases:** 22-26 (5 phases)
**Requirements:** 15 (ICE-01 to CLI-05)
**Key features:**
- Ice Ih IAPWS density (temperature-dependent, replaces 0.9167 g/cm³)
- Water density from T/P via IAPWS (display + interface spacing)
- Triclinic→orthogonal transformation for Ice II, V, VI
- CLI interface generation (--interface flag with full parameters)
- Integration and polish

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

### v3.5 New Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| Build order: Ice Ih → Water → Triclinic → CLI → Integration | Research-identified dependency graph | Approved |
| IAPWS library for density | Already in environment, scientifically accurate | Approved |
| numpy for transformation | No external crystallography library needed | Approved |
| Service layer pattern | Matches existing architecture | Approved |
| Direct iapws._iapws._Ice usage | Already implements IAPWS R10-06(2009) | Implemented (22-01) |
| @lru_cache(maxsize=256) for density | Performance for IAPWS iterative solver | Implemented (22-01) |
| Fallback density 0.9167 g/cm³ | Handle out-of-range conditions gracefully | Implemented (22-01) |
| IAPWS density in lookup_phase | Ice Ih uses T-dependent density, other phases use fixed | Implemented (22-02) |
| Inline IAPWS density in GUI | Calculate Ice Ih density directly in display code | Implemented (22-03) |
| 4 decimal density formatting | Consistent display between GUI and CLI | Implemented (22-03) |
| Test fixtures with 0.9167 are input data | Not assertions about IAPWS output | Verified (22-04) |
| IAPWS95 for water density | Supports supercooled water (T < 273.15K) via extrapolation | Implemented (23-01) |
| Water fallback 0.9998 g/cm³ | Water density at melting point (0°C, 1 atm) | Implemented (23-01) |
| Water density sanity check rho > 100 kg/m³ | Catches numerical issues from invalid inputs | Implemented (23-01) |
| TEMPLATE_DENSITY_GCM3 = 0.991 | TIP4P template density from tip4p.gro | Implemented (23-02) |
| Cube root scaling for density | scale = (template_density / target_density)^(1/3) | Implemented (23-02) |
| Water density in GUI for Liquid phase | Lazy import, 4 decimal formatting | Implemented (23-02) |
| 0.1° angle tolerance for orthogonal detection | CONTEXT.md decision for triclinic identification | Implemented (24-01) |
| Ice II 6x multiplier | Rhombohedral→hexagonal→orthogonal chain | Implemented (24-01) |
| Density validation 1% tolerance | Ensures structure preservation | Implemented (24-01) |

### Research Findings (v3.5)

- **Triclinic transformation:** Highest risk - must validate against known structures
- **IAPWS range violations:** Need bounds checking with fallback (~1.0 g/cm³)
- **Density units:** IAPWS returns kg/m³, QuickIce uses g/cm³ - factor-of-1000 conversion
- **Performance:** Use @lru_cache for density lookups (IAPWS-95 iterative solver)

### Pitfalls to Avoid (v3.5)

1. Incorrect triclinic coordinate transformation (silent invalid crystals)
2. Breaking piece.py validation (orthogonal-only check at lines 61-71)
3. IAPWS range violations returning NaN
4. Performance regression from uncached IAPWS calls
5. Density units confusion (kg/m³ vs g/cm³)

### Blockers

(None)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 004 | Interface viewer improvements (remove spheres, pocket types, UI layout) | 2026-04-10 | 48d8352 | [004-interface-viewer-improvements](./quick/004-interface-viewer-improvements/) |
| 005 | Simplify pocket shapes (remove rectangular/hexagonal, keep sphere/cubic) | 2026-04-10 | 35ce9a5, 860004e | [005-simplify-pocket-shapes](./quick/005-simplify-pocket-shapes/) |

---

## Archive Reference

- v1.0: [.planning/milestones/v1-ROADMAP.md](./milestones/v1-ROADMAP.md)
- v1.1: [.planning/milestones/v1.1-ROADMAP.md](./milestones/v1.1-ROADMAP.md)
- v2.0: [.planning/milestones/v2.0-ROADMAP.md](./milestones/v2.0-ROADMAP.md)
- v2.1: [.planning/milestones/v2.1-ROADMAP.md](./milestones/v2.1-ROADMAP.md)
- v2.1.1: [.planning/milestones/v2.1.1-ROADMAP.md](./milestones/v2.1.1-ROADMAP.md)
- v3.0: [.planning/milestones/v3.0-ROADMAP.md](./milestones/v3.0-ROADMAP.md)

---

## Session Continuity

**Last session:** 2026-04-12 05:07 UTC
**Completed:** Phase 24 Plan 01: Triclinic Transformation Core (TDD: RED, GREEN, REFACTOR)
**Next:** `/gsd-execute-plan 24-02` — Integration with Generator

---

*State updated: 2026-04-12 — Phase 24 Plan 01 complete*