# QuickIce State

**Project:** QuickIce - Condition-based Ice Structure Generation
**Core Value:** Generate plausible ice structure candidates quickly with intuitive visual interface
**Current Focus:** Phase 15 - Phase Diagram Data Update

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-08)

**Core value:** Generate plausible ice structure candidates quickly with intuitive visual interface

**Current focus:** Phase 15 - Phase Diagram Data Update

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
| Milestone | v2.1.1 Phase Diagram Data Update |
| Phase | 15 |
| Plan | 07 of 07 (gap closure) |
| Status | Gap closure in progress |
| Last activity | 2026-04-08 — Completed 15-07-PLAN.md |

**Progress:** ██████████ 100% (Phase 15 complete)

---

## Current Phase Details

### Phase 15: Phase Diagram Data Update

**Goal:** Users receive accurate ice phase predictions based on IAPWS R14-08(2011) compliant thermodynamic data

**Requirements (14):**
- DATA-01 through DATA-08 (triple point updates)
- NEW-01, NEW-02 (Ice Ic phase region)
- CODE-01 through CODE-04 (code updates)

**Success Criteria:**
1. Phase lookup returns correct ice phase for any (T,P) input using updated triple point data
2. Ice Ic phase is available for metastable conditions (50-150K, 0-100 MPa)
3. All existing tests pass with corrected triple point values
4. New test validates Ice Ic region boundaries work correctly
5. Phase diagram boundaries reflect updated data accurately

---

## Milestone History

### v2.1 GROMACS Export (Shipped 2026-04-07)

**Phases:** 14 (8 plans)
**Key features:**
- GROMACS export (.gro, .top, .itp files)
- TIP4P-ICE water model (4-point)
- CLI --gromacs flag and GUI Ctrl+G export
- Complete documentation with academic citation
- Fixed AttributeError crash in export dialog
- Clear GUI labeling for molecule count

**Archive:** [.planning/milestones/v2.1-ROADMAP.md](./milestones/v2.1-ROADMAP.md)

### v2.0 GUI Application (Shipped 2026-04-04)

**Phases:** 8-13 (28 plans)
**Code:** 10,992 lines Python
**Key features:**
- PySide6 GUI with MVVM architecture
- Interactive 12-phase ice diagram
- VTK 3D molecular viewer with dual viewport
- Export: PDB, PNG, SVG
- Standalone Linux executable

**Archive:** [.planning/milestones/v2.0-ROADMAP.md](./milestones/v2.0-ROADMAP.md)

### v1.1 Hotfix (Shipped 2026-03-31)

**Phase:** 7.1 - Fix Performance & Critical Bugs
**Plans:** 4 of 6

**Archive:** [.planning/milestones/v1.1-ROADMAP.md](./milestones/v1.1-ROADMAP.md)

### v1.0 MVP (Shipped 2026-03-29)

**Phases:** 1-7 (30+ plans)
**Code:** ~7,151 lines Python

**Archive:** [.planning/milestones/v1-ROADMAP.md](./milestones/v1-ROADMAP.md)

---

## Key Decisions Summary

Full decision log: .planning/PROJECT.md

| Decision | Outcome |
|----------|---------|
| MVVM architecture | ✓ Clean separation |
| VTK for 3D | ✓ Full interactivity |
| PyInstaller bundling | ✓ Linux executable |
| Exact version pinning | ✓ All deps =x.y.z |
| TIP4P-ICE water model | ✓ GROMACS compatible |
| Single export action | ✓ .gro/.top/.itp together |
| Algorithm thresholds match TP values | ✓ Correct phase identification |
| Docstrings cite data sources | ✓ Scientific traceability |

---

## Archive Reference

- v1.0: [.planning/milestones/v1-ROADMAP.md](./milestones/v1-ROADMAP.md)
- v1.1: [.planning/milestones/v1.1-ROADMAP.md](./milestones/v1.1-ROADMAP.md)
- v2.0: [.planning/milestones/v2.0-ROADMAP.md](./milestones/v2.0-ROADMAP.md)
- v2.1: [.planning/milestones/v2.1-ROADMAP.md](./milestones/v2.1-ROADMAP.md)
- v1 Requirements: [.planning/milestones/v1-REQUIREMENTS.md](./milestones/v1-REQUIREMENTS.md)
- v2 Requirements: [.planning/milestones/v2.0-REQUIREMENTS.md](./milestones/v2.0-REQUIREMENTS.md)
- v2.1 Requirements: [.planning/milestones/v2.1-REQUIREMENTS.md](./milestones/v2.1-REQUIREMENTS.md)
- v2.1.1 Requirements: .planning/REQUIREMENTS.md

---

## Session Continuity

**Last session:** 2026-04-08
**Completed:** All Phase 15 plans including gap closure (15-01 through 15-07)
**Next:** Phase 15 complete. Ready for final verification and next milestone planning.

---

*State updated: 2026-04-08 — Completed Phase 15 gap closure (15-07)*