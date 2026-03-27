# Phase 5: Output - Research (CORRECTED)

**Researched:** 2026-03-27 (Updated with user correction)
**Domain:** Water ice phase diagram axis arrangement verification and polygon data validation
**Confidence:** HIGH (verified against Wikipedia and LSBU reference data)

## Summary

This research verifies the water ice phase diagram axis arrangement and assesses the approach for rendering phase regions.

**Key findings:**
1. **Axis arrangement is WRONG in current implementation**: Wikipedia uses Temperature on X-axis (linear), Pressure on Y-axis (logarithmic) - the current implementation has these SWAPPED
2. **Should NOT use polygons**: Fill space within curves instead of using pre-defined polygon vertices
3. **Single source of truth**: Use the same curve functions as Phase 2's lookup

**Primary recommendation:** 
1. Swap axis arrangement (T on X-axis, P on Y-axis with log scale)
2. Replace PHASE_POLYGONS with curve-based region filling

---

## Axis Arrangement Verification

### Standard Convention (Wikipedia - CORRECTED)

The Wikipedia phase diagram shows:
- **X-axis (horizontal):** Temperature (linear scale, Kelvin)
- **Y-axis (vertical):** Pressure (logarithmic scale, MPa)

The caption "Log-lin pressure-temperature phase diagram of water" indicates:
- Logarithmic scale for Pressure (Y-axis)
- Linear scale for Temperature (X-axis)

This is the standard convention for water/ice phase diagrams.

### Current Implementation (WRONG)

In `phase_diagram.py` (lines 296-297):
```python
ax.set_xlabel("Pressure (MPa)", fontsize=14, fontweight='bold')
ax.set_ylabel("Temperature (K)", fontsize=14, fontweight='bold')
```

And the coordinate transformation (line 197):
```python
plot_vertices = np.array([[p, t] for t, p in vertices])
```

This converts (T, P) tuples to (x=P, y=T), which places:
- Pressure on the X-axis (WRONG)
- Temperature on the Y-axis (WRONG)

**VERDICT: Axis arrangement is WRONG - needs to be SWAPPED.**

### Correct Implementation

To match Wikipedia convention:
```python
# Correct axis labels
ax.set_xlabel("Temperature (K)", fontsize=14, fontweight='bold')
ax.set_ylabel("Pressure (MPa)", fontsize=14, fontweight='bold')

# Correct coordinate transformation
plot_vertices = np.array([[t, p] for t, p in vertices])  # (x=T, y=P)

# Correct user point plotting
ax.plot(user_t, user_p, ...)  # x=T, y=P

# Set log scale on Y-axis (Pressure)
ax.set_yscale('log')

# Correct axis limits
ax.set_xlim(100, 500)  # Temperature range
ax.set_ylim(0.1, 10000)  # Pressure range (log scale)
```

**CRITICAL FIX 1: Swap axis arrangement in phase_diagram.py**

---

## Phase Region Filling Approach

### Current Approach (WRONG - Uses Polygons)

The current implementation uses `PHASE_POLYGONS` to fill phase regions:
```python
# Current approach - uses polygons
vertices = PHASE_POLYGONS[phase_id]
plot_vertices = np.array([[p, t] for t, p in vertices])
poly = Polygon(plot_vertices, closed=True)
ax.add_patch(poly)
```

This approach:
- Requires pre-defined polygon vertices
- Causes geometric overlap errors
- Is inconsistent with curve-based phase lookup
- Duplicates data that already exists as curves

### Correct Approach (CURVE-BASED FILLING)

The phase diagram should fill regions BETWEEN curves, not use pre-defined polygons:

1. **Draw phase boundary curves** (melting curves, solid-solid boundaries)
2. **Fill regions between curves** using matplotlib's `fill_between` or polygon patches derived from curves
3. **Single source of truth**: Use the same curve functions as Phase 2's lookup

Example approach:
```python
def fill_phase_region(ax, phase_id, T_range, P_range):
    """Fill a phase region between boundary curves."""
    # Get boundary curves for this phase
    boundaries = get_phase_boundaries(phase_id)  # curve functions
    
    # Sample points along boundaries
    points = sample_boundary_points(boundaries, T_range, P_range)
    
    # Create closed polygon from curve points
    if len(points) >= 3:
        poly = Polygon(points, closed=True)
        poly.set_facecolor(PHASE_COLORS[phase_id])
        ax.add_patch(poly)
```

**Benefits:**
- No pre-defined polygons that can have overlaps
- Consistency with curve-based phase lookup (Phase 2)
- Easier to maintain - change a curve, diagram updates automatically
- Scientifically accurate - regions follow actual phase boundaries

**CRITICAL FIX 2: Replace PHASE_POLYGONS with curve-based region filling**

---

## Triple Points (VERIFIED from LSBU)

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

These are correctly defined in `ice_boundaries.py` - no changes needed.

---

## Recommendations

### Fix 1: Swap Axis Arrangement

In `phase_diagram.py`:
1. Swap `set_xlabel` and `set_ylabel`
2. Change coordinate transformation from `[[p, t] ...]` to `[[t, p] ...]`
3. Swap arguments in `ax.plot(user_p, user_t, ...)` to `ax.plot(user_t, user_p, ...)`
4. Change `set_xscale('log')` to `set_yscale('log')`
5. Swap axis limits

### Fix 2: Curve-Based Region Filling

In `phase_diagram.py`:
1. Remove usage of `PHASE_POLYGONS`
2. Use curve functions from `ice_boundaries.py`:
   - `get_melting_pressure()` for melting curves
   - Boundary functions for solid-solid transitions
3. Generate polygon vertices dynamically from curves
4. Fill regions between adjacent curves

### Fix 3: Update Labels and Triple Points

1. Swap coordinates in triple point annotations
2. Update text positions for labels on phase regions

---

## Sources

### Primary (HIGH confidence)
- **Wikipedia Phase Diagram** - https://en.wikipedia.org/wiki/Phases_of_ice
  - Confirms axis arrangement: Temperature on X-axis, Pressure on Y-axis (log)
- **LSBU Water Phase Data** - https://ergodic.ugr.es/termo/lecciones/water1.html
  - Triple point coordinates verified
  - Phase stability regions confirmed

### Secondary (MEDIUM confidence)  
- **IAPWS R14-08(2011)** - Referenced in ice_boundaries.py for melting curves
- **Phase diagram images** - Visual verification of phase boundaries

---

## Metadata

**Confidence breakdown:**
- Axis arrangement: HIGH - verified against Wikipedia (corrected by user)
- Curve-based filling: HIGH - standard approach for phase diagrams
- Triple points: HIGH - verified against LSBU reference

**Research date:** 2026-03-27
**Valid until:** Phase diagram geometry is scientifically established (no expected changes)

**Action required:** 
1. Fix axis arrangement in `quickice/output/phase_diagram.py`
2. Replace polygon filling with curve-based filling
3. Verify output matches Wikipedia diagram style
