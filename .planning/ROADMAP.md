# Roadmap: QuickIce v3.5 Interface Enhancements

**Milestone:** v3.5 Interface Enhancements  
**Start Phase:** 22  
**Depth:** Comprehensive  
**Generated:** 2026-04-12

## Overview

This roadmap delivers four tightly-scoped features for QuickIce v3.5: Ice Ih IAPWS density (temperature-dependent, replacing hardcoded 0.9167 g/cm³), water density calculation from T/P via IAPWS (with correct spacing for interface generation), triclinic-to-orthogonal cell transformation (enabling Ice II, V, VI in interface generation), and CLI interface generation (`--interface` flag). The phase structure follows the research-recommended build order: Ice Ih Density → Water Density → Triclinic → CLI → Integration.

## Phases

### Phase 22: Ice Ih IAPWS Density

**Goal:** Users can view accurate Ice Ih density that varies with temperature, replacing the hardcoded 0.9167 g/cm³ value.

**Dependencies:** None (foundation phase)

**Requirements:** ICE-01, ICE-02, ICE-03

**Success Criteria (3):**

1. System calculates Ice Ih density from IAPWS equation of state using temperature input (ICE-01)
2. System displays Ice Ih density in the UI with proper units (g/cm³) (ICE-03)
3. System uses IAPWS calculation throughout instead of hardcoded 0.9167 value (ICE-03)

**Coverage:** 3/3 requirements → Complete

**Plans (4):**
- [x] 22-01-PLAN.md — Create IAPWS Ice Ih density module (wrapper + tests) ✓
- [x] 22-02-PLAN.md — Integrate IAPWS density into lookup.py backend ✓
- [x] 22-03-PLAN.md — Update GUI/CLI density display for IAPWS values ✓
- [x] 22-04-PLAN.md — Update existing tests for IAPWS-calculated density ✓

**Completed:** 2026-04-12

---

### Phase 23: Water Density from T/P

**Goal:** Users can view water density calculated from temperature and pressure, and interface generation uses correct molecule spacing.

**Dependencies:** Phase 22 (shares IAPWS infrastructure)

**Requirements:** WATER-01, WATER-02, WATER-03, WATER-04

**Success Criteria (4):**

1. System calculates water density from T/P using IAPWS library (WATER-01)
2. System displays water density in Tab 1 info panel with proper units (WATER-02)
3. System generates water molecules at correct spacing matching target density in Tab 2 interface generation (WATER-03)
4. System caches IAPWS density lookups using @lru_cache for performance (WATER-04)

**Coverage:** 4/4 requirements → Complete

**Plans (2):**
- [x] 23-01-PLAN.md — Create IAPWS95 water density module (wrapper + tests) ✓
- [x] 23-02-PLAN.md — Integrate water density into Tab 1 display and Tab 2 interface generation ✓

**Completed:** 2026-04-12

---

### Phase 24: Triclinic Transformation Service

**Goal:** Users can generate ice-water interfaces for all ice phases including non-orthogonal phases (Ice II, V, VI) that were previously rejected.

**Dependencies:** Phase 23 (density calculations may optionally be used)

**Requirements:** TRAN-01, TRAN-02, TRAN-03

**Success Criteria (3):**

1. System auto-detects triclinic unit cells for Ice II and Ice V phases (TRAN-01)
2. System transforms triclinic cells to orthogonal while preserving crystal structure integrity (TRAN-02)
3. System skips transformation for already-orthogonal phases (Ih, Ic, III, VI, VII, VIII) without errors (TRAN-03)

**Coverage:** 3/3 requirements → Complete

**Plans (3):**
- [x] 24-01-PLAN.md — Triclinic transformation algorithm (TDD: types + transformer + tests) ✓
- [x] 24-02-PLAN.md — Integrate transformer into generator.py ✓
- [x] 24-03-PLAN.md — Update validation in interface_builder.py and piece.py ✓

**Completed:** 2026-04-12

---

### Phase 25: CLI Interface Generation

**Goal:** Users can generate ice-water interfaces entirely from the command line with full parameter control.

**Dependencies:** Phase 24 (transformation service must work before CLI can handle triclinic phases)

**Requirements:** CLI-01, CLI-02, CLI-03, CLI-04, CLI-05

**Success Criteria (5):**

1. User can trigger interface generation via `--interface` flag with mode parameter (slab/pocket/piece) (CLI-01)
2. User can specify box dimensions (box_x, box_y, box_z) and random seed for all modes (CLI-02)
3. User can specify ice_thickness and water_thickness for slab mode (CLI-03)
4. User can specify pocket_diameter and pocket_shape for pocket mode (CLI-04)
5. User can export interface structures to GROMACS format from CLI (CLI-05)

**Coverage:** 5/5 requirements

**Plans (2):**
- [x] 25-01-PLAN.md — Extend CLI parser with interface flags and validation (Wave 1) ✓
- [x] 25-02-PLAN.md — Add interface generation workflow and GROMACS export (Wave 2) ✓

**Completed:** 2026-04-12

---

### Phase 26: Integration & Polish

**Goal:** All features work together correctly with proper validation, GROMACS export updates, and GUI display.

**Dependencies:** Phases 22, 23, 24, 25 (all features must be stable before integration)

**Requirements:** None additional (cross-cutting integration)

**Success Criteria (4):**

1. Piece mode validation correctly allows transformed triclinic cells (fixes v3.0 orthogonal-only check in piece.py)
2. GROMACS export produces valid .gro files for all interface types including transformed cells
3. GUI displays density values correctly in both tabs with proper units (g/cm³)
4. Integration tests pass for end-to-end workflows: generation → interface → CLI → GROMACS export

**Coverage:** Cross-cutting phase, no new requirements

**Plans (1):**
- [x] 26-01-PLAN.md — Integration tests for v3.5 features (GROMACS validation + CLI + triclinic) ✓

**Completed:** 2026-04-12

---

### Phase 27: Documentation Update

**Goal:** All v3.5 features documented in README (concise), docs folder (detailed), in-app help, tooltips, and screenshots.

**Dependencies:** Phase 26 (all features complete and verified)

**Requirements:** None additional (documentation phase)

**Success Criteria (5):**

1. README updated with concise v3.5 feature summary and version bump
2. docs/ updated with detailed guides for new features (CLI interface, density, triclinic transformation)
3. In-app help dialog updated with v3.5 feature descriptions
4. Tooltips added for new UI elements (density displays, transformation indicators)
5. Screenshots updated to reflect v3.5 interface

**Coverage:** Documentation phase, no new requirements

**Plans (3):**
- [x] 27-01-PLAN.md — Update README, CLI reference, and GUI guide documentation ✓
- [x] 27-02-PLAN.md — Fix help dialog, add transformation status display, apply tooltip width fix ✓
- [x] 27-03-PLAN.md — Screenshot verification checkpoint ✓

**Completed:** 2026-04-13

---

## Coverage Summary

| Phase | Goal | Requirements | Success Criteria |
|-------|------|--------------|------------------|
| 22 - Ice Ih Density | Temperature-dependent Ice Ih density | ICE-01, ICE-02, ICE-03 | 3 criteria |
| 23 - Water Density | T/P-based water density for UI and interfaces | WATER-01, WATER-02, WATER-03, WATER-04 | 4 criteria |
| 24 - Triclinic Transformation | All ice phases work in interfaces | TRAN-01, TRAN-02, TRAN-03 | 3 criteria |
| 25 - CLI Interface | Full CLI interface generation | CLI-01, CLI-02, CLI-03, CLI-04, CLI-05 | 5 criteria |
| 26 - Integration & Polish | Features work together | — | 4 criteria |
| 27 - Documentation Update | README, docs, help, tooltips, screenshots | — | 5 criteria |

**Total:** 6 phases, 15 requirements mapped, 24 success criteria

---

## Progress

| Phase | Status | Plans | Must-Haves |
|-------|--------|-------|------------|
| 22 - Ice Ih Density | ✓ Complete | 4/4 complete | IAPWS density via iapws._Ice, backend/frontend integration, tests |
| 23 - Water Density | ✓ Complete | 2/2 complete | IAPWS95 water density with caching, Tab 1 display, Tab 2 interface spacing |
| 24 - Triclinic Transformation | ✓ Complete | 3/3 complete | TriclinicTransformer with detection, transformation, validation |
| 25 - CLI Interface | ✓ Complete | 2/2 complete | CLI flags, interface workflow, GROMACS export, all modes tested |
| 26 - Integration & Polish | ✓ Complete | 1/1 complete | GROMACS validation, CLI integration tests, triclinic phase tests |
| 27 - Documentation Update | ✓ Complete | 3/3 complete | README, docs, help dialog, tooltips, screenshots deferred |

---

## Notes

- **Phase ordering rationale:** Ice Ih density first (lowest risk, shared IAPWS infrastructure), then water density (builds on same service), then triclinic transformation (critical path blocker), then CLI (builds on transformation), then integration (cross-cutting)
- **Research flags:** Phase 24 (triclinic) needs algorithm validation against known structures; Phase 26 GROMACS export needs verification for transformed cells
- **No new dependencies:** All features use existing stack (numpy, argparse, iapws) — iapws._iapws._Ice() already implements IAPWS R10-06(2009) Ice Ih EOS
- **Density unit conversion:** IAPWS returns kg/m³, QuickIce uses g/cm³ (factor of 1000)

---

*Roadmap generated: 2026-04-12*
*Next: `/gsd-plan-phase 22` to plan Ice Ih IAPWS Density*