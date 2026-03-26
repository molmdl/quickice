# QuickIce State

**Project:** QuickIce - ML-based Ice Structure Generation  
**Core Value:** Generate plausible ice structure candidates quickly for given thermodynamic conditions  
**Current Focus:** Phase 2 + Phase 5 unified correction (boundary consistency)

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
| Phase | 2 + 5 (unified correction) |
| Plan | 02-07 (triple point fix) → 05-08 (diagram rewrite) |
| Status | READY - New correction plans created |
| Last activity | 2026-03-27 - Created unified correction plans |
| Progress Bar | ███████████████░░░░░░░░░ 57% (4/7 phases) |

---

## ⚠️ CORRECTION IN PROGRESS

**Problem:** Phase 2 (lookup) and Phase 5 (diagram) use different boundary data sources, causing inconsistency.

**Root Cause:**
- Phase 2 `lookup.py` uses `PHASE_POLYGONS` from `ice_boundaries.py`
- Phase 5 `phase_diagram.py` uses `_build_phase_polygon_from_curves()` (rebuilds differently)
- Triple point II-III-V has 0.8K error (249.65 vs 248.85 K)

**Solution:** Unified correction with two plans:
1. **02-07**: Fix triple point II-III-V to match IAPWS reference (Wave 1)
2. **05-08**: Rewrite diagram to use PHASE_POLYGONS directly (Wave 2, depends on 02-07)

---

## Phase Summary

| Phase | Name | Goal | Status |
|-------|------|------|--------|
| 1 | Input Validation | Valid CLI flags | ✓ Complete |
| 2 | Phase Mapping | T,P → polymorph | ⚠️ CORRECTION (02-07) |
| 3 | Structure Generation | Valid GenIce output | ✓ Complete |
| 4 | Ranking | Scored candidates | ✓ Complete |
| 5 | Output | PDB files + phase diagram | ⚠️ CORRECTION (05-08) |
| 6 | Documentation | User guides | Pending |
| 7 | Audit & Correctness | Quality assurance | Pending |

---

## Phase 5 Progress

| Plan | Description | Status |
|------|-------------|--------|
| 05-01 | Output types (OutputResult dataclass) | ✓ Complete |
| 05-02 | PDB writer with TDD | ✓ Complete |
| 05-03 | Validator with TDD | ✓ Complete |
| 05-04 | Phase diagram generator | ⚠️ SUPERSEDED by 05-08 |
| 05-05 | Output orchestrator | Pending |
| 05-06 | CLI integration | Pending |
| 05-07 | Curved boundaries correction | ⚠️ SUPERSEDED by 05-08 |
| 05-08 | Unified diagram with PHASE_POLYGONS | Ready |

---

## Correction Plans

| Plan | Description | Wave | Depends On | Status |
|------|-------------|------|-----------|--------|
| 02-07 | Fix II-III-V triple point (248.85 K) | 1 | - | Ready |
| 05-08 | Rewrite diagram with PHASE_POLYGONS | 2 | 02-07 | Ready |

---

## Session Continuity

**Last Session:** 2026-03-27
**Stopped at:** Created unified correction plans for boundary consistency

**Next Session:**
1. Execute: `/gsd-execute-phase 2 --plans 07` (fix triple point)
2. Then: `/gsd-execute-phase 5 --plans 08` (rewrite diagram)

---

## Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| Use curved phase boundaries | Rectangular approximation is scientifically incorrect | ✓ Implemented |
| Single source of truth | PHASE_POLYGONS used by both lookup and diagram | Pending (05-08) |
| Fix triple point II-III-V | 0.8K error needs correction | Pending (02-07) |
| Labels on phase regions | Better UX than legend-only | Pending (05-08) |

---

## Dependencies

- iapws>=1.5.4 (IAPWS ice phase equations)
- scipy>=1.8 (boundary curve interpolation)
- shapely>=2.0 (point-in-polygon for curved boundaries)
- matplotlib (phase diagram visualization)

---

*State updated: 2026-03-27 (Created unified correction plans 02-07, 05-08)*
