# QuickIce State

**Project:** QuickIce - ML-based Ice Structure Generation  
**Core Value:** Generate plausible ice structure candidates quickly for given thermodynamic conditions  
**Current Focus:** Phase 2 Correction - Fixing scientifically incorrect rectangular phase boundaries

---

## Project Reference

| Attribute | Value |
|-----------|-------|
| Core Value | Generate plausible ice structure candidates quickly for given thermodynamic conditions |
| Mode | yolo |
| Depth | Comprehensive (7 phases) |
| Approach | Pure "vibe coding" — no physics simulations |

---

## Current Position

| Field | Value |
|-------|-------|
| Phase | 2 of 7 (Phase Mapping - CORRECTION IN PROGRESS) |
| Plan | 4 of 6 (correction plans) |
| Status | Completed 02-04 - Curved boundary data created |
| Last activity | 2026-03-27 - Completed 02-04-PLAN.md |
| Progress Bar | ████████████████████░░░░ 84% (16 of 19 plans complete) |

---

## ⚠️ CRITICAL ISSUE IDENTIFIED

**Problem:** Phase 2 (Phase Mapping) and Phase 5 (Phase Diagram) use **rectangular phase boundaries** which is SCIENTIFICALLY INCORRECT. Real ice phase boundaries are **curved lines**.

**Impact:**
- Phase lookup gives WRONG results near boundaries
- Example: T=260K, P=300MPa returns "ice_iii" (wrong) instead of "ice_ii" (correct)
- Phase diagram shows rectangles instead of curved regions

**Correction Plans Created:**
- Phase 2: Plans 02-04, 02-05, 02-06 (boundary data, lookup logic, tests)
- Phase 5: Plan 05-07 (phase diagram generator)

**New Dependencies Added:**
- iapws>=1.5.4 (IAPWS ice phase equations)
- scipy>=1.8 (boundary curve interpolation)
- shapely>=2.0 (point-in-polygon for curved boundaries)

---

## Phase Summary

| Phase | Name | Goal | Status |
|-------|------|------|--------|
| 1 | Input Validation | Valid CLI flags | ✓ Complete |
| 2 | Phase Mapping | T,P → polymorph | ⚠️ NEEDS CORRECTION |
| 3 | Structure Generation | Valid GenIce output | ✓ Complete |
| 4 | Ranking | Scored candidates | ✓ Complete |
| 5 | Output | PDB files + phase diagram | ⚠️ NEEDS CORRECTION |
| 6 | Documentation | User guides | Pending |
| 7 | Audit & Correctness | Quality assurance | Pending |

---

## Correction Plans

### Phase 2 Corrections (Wave 1-3)

| Plan | Description | Status |
|------|-------------|--------|
| 02-04 | Curved boundary data (IAPWS triple points, polygons) | ✓ Complete |
| 02-05 | Curved boundary lookup logic (shapely) | Pending |
| 02-06 | Update test expectations | Pending |

### Phase 5 Corrections (Wave 6)

| Plan | Description | Status |
|------|-------------|--------|
| 05-07 | Phase diagram with curved boundaries | Pending |

---

## Session Continuity

**Last Session:** 2026-03-27T03:41:44Z
**Last Completed:** 02-04-PLAN.md (Curved boundary data with IAPWS triple points)

**Next Session:** Continue Phase 2 corrections
- Run: `/gsd-execute-phase 2 --plans 05-06`
- Then: `/gsd-execute-phase 5 --plans 07`

---

## Todo

- [x] Phase 1: Input Validation — COMPLETE
- [ ] Phase 2: Phase Mapping — CORRECTION IN PROGRESS
  - [x] 02-01, 02-02, 02-03 — Original plans (rectangular - WRONG)
  - [x] 02-04 — Curved boundary data
  - [ ] 02-05 — Curved lookup logic
  - [ ] 02-06 — Updated tests
- [x] Phase 3: Structure Generation — COMPLETE
- [x] Phase 4: Ranking — COMPLETE
- [ ] Phase 5: Output — CORRECTION NEEDED
  - [x] 05-01, 05-02, 05-03 — Complete
  - [x] 05-04 — Phase diagram (rectangular - NEEDS FIX)
  - [ ] 05-05, 05-06 — Pending
  - [ ] 05-07 — Curved phase diagram
- [ ] Phase 6: Documentation
- [ ] Phase 7: Audit & Correctness

---

## Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| Use curved phase boundaries | Rectangular approximation is scientifically incorrect | Approved (correction) |
| Use iapws package | Implements IAPWS R14-08 certified ice phase equations | Approved |
| Use shapely for point-in-polygon | Handles curved boundary checking correctly | Approved |
| Re-plan from Phase 2 onwards | Phase lookup affects all downstream phases | Approved |
| Simon-Glatzel melting curves | Correctly fits triple points: P = P_ref + A * [(T/T_ref)^c - 1] | Approved (02-04) |
| Polygon vertex representation | (T, P) tuples ordered CCW for shapely compatibility | Approved (02-04) |

---

*State updated: 2026-03-27 (02-04 complete)*
