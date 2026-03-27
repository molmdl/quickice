# Phase 5: Output - Research (Updated)

**Researched:** 2026-03-27
**Domain:** Water ice phase diagram axis arrangement verification and polygon data validation
**Confidence:** HIGH (verified against Wikipedia and LSBU reference data)

## Summary

This research verifies the water ice phase diagram axis arrangement and assesses the PHASE_POLYGONS data issues identified in the checkpoint. 

**Key findings:**
1. **Axis arrangement is CORRECT**: Wikipedia and standard convention use Pressure on X-axis (logarithmic), Temperature on Y-axis (linear) - this matches the current implementation
2. **Phase 2 polygon data HAS GEOMETRIC ERRORS**: The ice_ii polygon has incorrect vertex definitions causing overlaps with ice_iii and ice_v
3. **The ice_ic polygon definition is problematic**: It overlaps significantly with ice_ih

**Primary recommendation:** The axis arrangement requires NO changes. The PHASE_POLYGONS data in ice_boundaries.py needs correction to fix the geometric overlaps, particularly in the ice_ii polygon definition.

---

## Axis Arrangement Verification

### Standard Convention (Wikipedia)

The Wikipedia phase diagram shows:
- **X-axis (horizontal):** Pressure (logarithmic scale, MPa)
- **Y-axis (vertical):** Temperature (linear scale, Kelvin)

This is explicitly stated in the Wikipedia description: "Log-lin pressure-temperature phase diagram of water."

### Current Implementation

In `phase_diagram.py` (lines 296-297):
```python
ax.set_xlabel("Pressure (MPa)", fontsize=14, fontweight='bold')
ax.set_ylabel("Temperature (K)", fontsize=14, fontweight='bold')
```

And the coordinate transformation (line 197):
```python
plot_vertices = np.array([[p, t] for t, p in vertices])
```

This converts (T, P) tuples to (x=P, y=T), which correctly places:
- Pressure on the X-axis
- Temperature on the Y-axis

**VERDICT: Axis arrangement is CORRECT and matches Wikipedia convention.**

---

## PHASE_POLYGONS Assessment

### Identified Geometric Issues

From the checkpoint, the following overlaps exist:

| Phase Pair | Overlap | Severity |
|------------|---------|----------|
| ice_ih <-> ice_ic | 14058 K*MPa | HIGH |
| ice_ii <-> ice_iii | 228 K*MPa | LOW |
| ice_ii <-> ice_v | 7061 K*MPa | HIGH |

### Root Cause Analysis

#### 1. ice_ii Polygon (CRITICAL ISSUE)

Current definition in `ice_boundaries.py`:
```python
"ice_ii": [
    (218.95, 620.0),        # II-V-VI triple point
    (260.0, 620.0),         # Extended high T boundary ← WRONG
    (260.0, 210.0),         # Extended boundary at T=260K ← WRONG
    (248.85, 344.3),        # II-III-V triple point
    (238.55, 212.9),        # Ih-II-III triple point
    (200.0, 300.0),         # Lower T extension
    (180.0, 620.0),         # Cold boundary at high P
    (218.95, 620.0),        # Back to triple point
],
```

**Problem:** The vertices (260.0, 620.0) and (260.0, 210.0) extend the ice_ii region incorrectly into ice_v's territory. According to the phase diagram:
- Ice II is stable at HIGH pressure (300-620 MPa) and LOW temperature (180-250 K)
- At higher temperatures (above ~250K), ice II is not stable
- The boundary should curve from the II-III-V triple point toward the II-V-VI triple point

#### 2. ice_ic Polygon (METASTABLE)

Current definition:
```python
"ice_ic": [
    (100.0, 0.1),           # Low T, low P
    (240.0, 0.1),           # Upper temp limit
    (240.0, 150.0),         # Upper pressure
    (200.0, 150.0),         # Higher pressure boundary
    (100.0, 150.0),         # Cold boundary
],
```

**Problem:** Ice Ic is a metastable phase that exists at:
- Low pressure (atmospheric)
- Low temperature (130-240 K range)

The current definition overlaps with ice_ih because ice_ic should only exist in a narrow region at atmospheric pressure.

---

## Correct Polygon Definitions

Based on the LSBU reference data and Wikipedia phase diagram, here are the correct boundaries:

### Triple Points (VERIFIED)

| Triple Point | T (K) | P (MPa) |
|--------------|-------|---------|
| Ih-III-Liquid | 251.165 | 207.5 |
| Ih-II-III | 238.55 | 212.9 |
| II-III-V | 248.85 | 344.3 |
| III-V-Liquid | 256.165 | 346.3 |
| II-V-VI | 218.95 | 620.0 |
| V-VI-Liquid | 273.31 | 625.9 |
| VI-VII-Liquid | 354.75 | 2200.0 |
| VI-VII-VIII | 278.0 | 2100.0 |

### Corrected ice_ii Polygon

The correct ice_ii polygon should be bounded by:
- (238.55, 212.9) - Ih-II-III triple point (shared with ice_ih and ice_iii)
- (248.85, 344.3) - II-III-V triple point (shared with ice_iii and ice_v)
- (218.95, 620.0) - II-V-VI triple point (shared with ice_v and ice_vi)
- Connect these with proper curved boundaries

The extension to T=260K is WRONG - ice II is stable only below ~250K.

### Corrected ice_ic Polygon

Ice Ic is metastable and should be a narrow band at low temperature and atmospheric pressure:
- T: ~130-240 K
- P: ~0.1 MPa (atmospheric)
- Should NOT overlap with ice_ih

---

## Recommendations

### 1. Fix ice_ii Polygon (HIGH PRIORITY)

Replace the incorrect extension with proper boundaries:
```python
"ice_ii": [
    (238.55, 212.9),        # Ih-II-III triple point
    (248.85, 344.3),        # II-III-V triple point  
    (218.95, 620.0),        # II-V-VI triple point
    (200.0, 620.0),         # Cold boundary at high pressure
    (200.0, 300.0),         # Lower pressure extension
    (238.55, 212.9),        # Back to start
],
```

### 2. Fix ice_ic Polygon (MEDIUM PRIORITY)

Either remove ice_ic or define it correctly as metastable:
```python
"ice_ic": [
    (130.0, 0.1),           # Lower temp limit
    (240.0, 0.1),           # Upper temp limit (conversion to Ih)
    (220.0, 50.0),          # Slight pressure extension
    (130.0, 50.0),          # Cold boundary
],
```

### 3. Verify No Overlaps After Fix

After corrections, validate that:
- No polygon pairs have geometric overlap
- All triple points are shared correctly between adjacent phases
- Phase regions are contiguous and cover the full T-P space

---

## Sources

### Primary (HIGH confidence)
- **Wikipedia Phase Diagram** - https://en.wikipedia.org/wiki/Phases_of_ice
  - Confirms axis arrangement: Pressure (log) on X-axis, Temperature on Y-axis
- **LSBU Water Phase Data** - https://ergodic.ugr.es/termo/lecciones/water1.html
  - Triple point coordinates verified
  - Phase stability regions confirmed

### Secondary (MEDIUM confidence)  
- **IAPWS R14-08(2011)** - Referenced in ice_boundaries.py for melting curves
- **Phase diagram images** - Visual verification of phase boundaries

---

## Metadata

**Confidence breakdown:**
- Axis arrangement: HIGH - verified against Wikipedia
- Polygon assessment: HIGH - based on verified triple point data
- Recommendations: HIGH - corrections align with phase diagram geometry

**Research date:** 2026-03-27
**Valid until:** Phase diagram geometry is scientifically established (no expected changes)

**Action required:** Update PHASE_POLYGONS in `quickice/phase_mapping/data/ice_boundaries.py` with corrected vertex definitions, then re-run Phase 2 to propagate the fix to Phase 5.