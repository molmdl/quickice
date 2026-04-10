# Debug Context: Phase Lookup Mismatch (II-in-VI)

**Date:** 2026-04-10
**Status:** ACTIVE - needs fix in next session

---

## Issues Summary

### Issue 1: XV Polygon Fixed ✅
- XV polygon now correctly at T=50-100K, P=950-2100 MPa
- XV lookup matches polygon

### Issue 2: II-in-VI Lookup Mismatch (REGRESSION)
**Status:** ACTIVE - needs fix

**Symptoms:**
Clicking on VI region in diagram returns VI correctly, but the actual structure generation uses II instead.

**Problem coordinates:**
| T (K) | P (MPa) | Expected | Actual | Notes |
|-------|---------|----------|--------|-------|
| 205.6 | 816 | VI | II | |
| 104.5 | 1829.52 | XV | II | Below VI threshold |
| 218.5 | 1829.52 | VI | II | Just below threshold |
| 219.0 | 1829.52 | VI | VI | Works at slightly higher T |
| 150.0 | 1500 | VI | II | |

**Root Cause Found:**
The VI lookup check at line 239 in `lookup.py` only triggers for `T >= 218.95K`:

```python
if T >= 218.95 and P > 620:
    # ... returns ice_vi
```

But the VI polygon extends down to T=100K (touching XV at the VI-XV transition).

For T < 218.95K, the code falls through to the Ice II check (line 294), which returns II for many VI coordinates.

**Boundary values:**
```
T (K)   V-VI boundary  II-V boundary
100     725.6          1347.2
150     698.7          1015.3
200     671.8          683.4
218.95  661.6          557.6
```

At T=150K, P=1500 MPa:
- V-VI boundary = 698.7 MPa (so P > V-VI = above V-VI = should be VI)
- II-V boundary = 1015.3 MPa (so P > II-V = above II-V = NOT in V region)
- But VI check requires T >= 218.95K, so falls through to II check
- II check: P > ih_ii_boundary → returns II (wrong!)

**The Fix Needed:**
Need to add a VI check for T=100-218.95K range, checking against the V-VI boundary.

Currently:
- XV check: T=50-100K ✅
- VI check: T >= 218.95K ✗ (misses T=100-218.95K range!)
- II check: catches the gap incorrectly

Should be:
- XV check: T=50-100K ✅
- VI check for T=100-218.95K: Check P > V-VI boundary → VI ✅
- VI check for T >= 218.95K: existing logic ✅

### Issue 3: Quick Reference Window Too Long
**Status:** NEW - minor UI issue

**Description:**
Quick reference window is too long and needs a scrollbar.

**Likely file:** `quickice/gui/quick_reference_dialog.py` or similar

---

## Related Files

- `quickice/phase_mapping/lookup.py` - lookup_phase() function
  - Line 239: VI check threshold T >= 218.95K (TOO HIGH)
  - Line 294: II check catches coordinates that should be VI
- `quickice/output/phase_diagram.py` - polygon definitions
  - VI polygon: T >= 100K (correct)
- `quickice/gui/main_window.py` - diagram click handling

---

## Previous Fixes (for reference)

1. Commit `68b1a5e`: Fixed XV lookup from T=80-108K to T=50-100K
2. Commit `d2346f5` (REVERTED): Wrong fix that changed XV polygon to T=80-108K

---

## Code Snippets

**Current VI check (line 235-268 in lookup.py):**
```python
# 2. Ice VI region (between V-VI and VI-VII boundaries)
# Ice VI: T(273.31-355K at high P), P(626-2200 MPa)
# Note: At lower temperatures, Ice VI extends down to T=218.95K (II-V-VI TP)
# For T > 354.75K (VI-VII-Liquid TP): Ice VI doesn't exist, boundary is VII melting curve
if T >= 218.95 and P > 620:
    # ... VI logic
```

**Needs to add:**
```python
# 1c. Ice VI region at T=100-218.95K (above XV, below main VI check)
# This fills the gap between XV (T <= 100K) and main VI (T >= 218.95K)
if 100.0 < T < 218.95 and P > 620:
    # Check V-VI boundary
    P_v_vi = v_vi_boundary(T)
    if P > P_v_vi:
        phase_id = "ice_vi"
        return _build_result(phase_id, T, P)
```

---

## Next Steps for Next Session

1. Add VI check for T=100-218.95K range in lookup.py (before II check)
2. Test with problem coordinates
3. Fix quick reference window scrollbar (separate issue)
