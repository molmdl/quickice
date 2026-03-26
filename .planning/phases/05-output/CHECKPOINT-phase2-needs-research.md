# CHECKPOINT: Phase 5 Diagram Fix Complete, Phase 2 Needs Re-research

**Date:** 2026-03-27
**Status:** Phase 5 diagram rendering fixed, but underlying data is incorrect

---

## What Was Fixed

### Phase 5 - Diagram Rendering

**Commit:** `60e9780`

**Issues Fixed:**
1. Centroid coordinates were swapped (x/y mix-up)
   - `centroid.x = T` (temperature)
   - `centroid.y = P` (pressure)
   - Plot expects `(x=P, y=T)`, so swap was needed
2. Removed redundant legend (labels now on phase regions)
3. Cleaned up unused imports

**Result:**
- Image size: 3568 x 2956 pixels (was 3068 x 36211)
- Aspect ratio: 1.21 (correct)

---

## What Still Needs Work

### Phase 2 - PHASE_POLYGONS Data is Incorrect

**Root Cause:** The polygon definitions in `quickice/phase_mapping/data/ice_boundaries.py` have geometric issues:

```
OVERLAPPING PHASES:
  ice_ih <-> ice_ic: overlap area = 14058 K*MPa
  ice_ii <-> ice_iii: overlap area = 228 K*MPa
  ice_ii <-> ice_v: overlap area = 7061 K*MPa
```

**Why This Matters:**
1. The lookup uses `PHASE_POLYGONS` for point-in-polygon testing
2. Overlapping polygons cause inconsistent lookup results
3. A point at (250K, 600 MPa) could match both ice_ii and ice_v

**Specific Issues in ice_ii polygon:**
```python
"ice_ii": [
    (218.95, 620.0),        # II-V-VI triple point
    (260.0, 620.0),         # Extended high temperature boundary ← WRONG
    (260.0, 210.0),         # Extended boundary at T=260K ← WRONG
    (248.85, 344.3),        # II-III-V triple point
    (238.55, 212.9),        # Ih-II-III triple point
    ...
]
```

The ice_ii polygon extends incorrectly into ice_v's territory.

---

## Next Steps

### 1. Re-research Phase 2

Run:
```bash
/gsd-research-phase 2
```

**Research Goals:**
- Find accurate ice phase boundary coordinates from scientific literature
- Use Wikipedia ice phase diagram as primary visual reference
- Identify correct polygon vertices for each ice phase
- Ensure no overlaps between phase regions
- Document sources (IAPWS, LSBU, papers)

### 2. Re-plan Phase 2

After research:
```bash
/gsd-plan-phase 2
```

**Plan Should Include:**
- Correct PHASE_POLYGONS with no overlaps
- Updated triple point coordinates if needed
- Validation tests for polygon geometry

### 3. Re-execute Phase 2

```bash
/gsd-execute-phase 2
```

### 4. Return to Phase 5

After Phase 2 is corrected:
```bash
/gsd-execute-phase 5
```

The diagram will then use correct PHASE_POLYGONS.

---

## File Locations

| File | Purpose |
|------|---------|
| `quickice/phase_mapping/data/ice_boundaries.py` | Contains PHASE_POLYGONS (needs fixing) |
| `quickice/output/phase_diagram.py` | Diagram renderer (FIXED) |
| `.planning/phases/05-output/05-08-PLAN.md` | Current plan (superseded by this checkpoint) |

---

## Current State

| Phase | Status |
|-------|--------|
| 1 - Input Validation | ✓ Complete |
| 2 - Phase Mapping | ⚠️ Needs re-research (polygon data incorrect) |
| 3 - Structure Generation | ✓ Complete |
| 4 - Ranking | ✓ Complete |
| 5 - Output | ⚠️ Diagram renderer fixed, waiting for Phase 2 fix |
| 6 - Documentation | Pending |
| 7 - Audit | Pending |

---

## Command to Resume

```bash
/new
/gsd-research-phase 2
```

This will start fresh with a new context window and research correct ice phase boundaries.
