# QuickIce State

**Project:** QuickIce - ML-based Ice Structure Generation  
**Core Value:** Generate plausible ice structure candidates quickly for given thermodynamic conditions  
**Current Focus:** Phase 2 needs re-research (PHASE_POLYGONS have geometric errors)

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
| Phase | 2 (needs re-research) |
| Plan | - |
| Status | Phase 5 diagram fixed, Phase 2 polygon data incorrect |
| Last activity | 2026-03-27 - Checkpoint created |
| Progress Bar | ████████████████░░░░░░░ 71% (5/7 phases, Phase 5 blocked on Phase 2) |

---

## Phase Summary

| Phase | Name | Goal | Status |
|-------|------|------|--------|
| 1 | Input Validation | Valid CLI flags | ✓ Complete |
| 2 | Phase Mapping | T,P → polymorph | ⚠️ NEEDS RE-RESEARCH (polygon overlaps) |
| 3 | Structure Generation | Valid GenIce output | ✓ Complete |
| 4 | Ranking | Scored candidates | ✓ Complete |
| 5 | Output | PDB files + phase diagram | ⚠️ Renderer fixed, waiting for Phase 2 |
| 6 | Documentation | User guides | Pending |
| 7 | Audit & Correctness | Quality assurance | Pending |

---

## Known Issues

### Phase 2 - PHASE_POLYGONS Overlap

```
OVERLAPPING PHASES:
  ice_ih <-> ice_ic: overlap area = 14058 K*MPa
  ice_ii <-> ice_iii: overlap area = 228 K*MPa
  ice_ii <-> ice_v: overlap area = 7061 K*MPa
```

**Impact:** Lookup can return wrong results near phase boundaries.

**Solution:** Re-research correct phase boundaries from Wikipedia/literature, then replan Phase 2.

### Phase 5 - Diagram (FIXED)

**Commit:** `60e9780`
- Fixed centroid coordinate swap
- Removed redundant legend
- Image now correct size (3568 x 2956 px)

---

## Session Continuity

**Last Session:** 2026-03-27
**Stopped at:** Phase 5 diagram fix complete, Phase 2 needs re-research

**Next Session:**
1. Run: `/gsd-research-phase 2` (research correct phase boundaries)
2. Run: `/gsd-plan-phase 2` (replan with correct data)
3. Run: `/gsd-execute-phase 2` (execute corrected plans)
4. Run: `/gsd-execute-phase 5` (complete Phase 5)

---

## Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| Use curved phase boundaries | Rectangular approximation is scientifically incorrect | ✓ Implemented |
| Single source of truth | PHASE_POLYGONS used by both lookup and diagram | ⚠️ Data incorrect |
| Fix triple point II-III-V | 0.8K error corrected to 248.85 K (LSBU source) | ✓ Complete |
| Labels on phase regions | Better UX than legend-only | ✓ Complete (Phase 5) |
| Data source citation | LSBU for triple points, IAPWS for Ice Ih | ✓ Complete |

---

## Dependencies

- iapws>=1.5.4 (IAPWS ice phase equations)
- scipy>=1.8 (boundary curve interpolation)
- shapely>=2.0 (point-in-polygon for curved boundaries)
- matplotlib (phase diagram visualization)

---

*State updated: 2026-03-27 (Checkpoint: Phase 2 needs re-research)*
