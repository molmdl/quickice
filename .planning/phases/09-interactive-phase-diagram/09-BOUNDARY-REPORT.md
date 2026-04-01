# Boundary and Triple Point Handling: CLI vs GUI

**Date:** 2026-04-01
**Context:** Investigating why GUI returns "Ih/Vapor" at 273.15K, 0.1 MPa while CLI correctly returns "Ih"

---

## Summary

| Aspect | CLI (`lookup.py`) | GUI (`phase_diagram_widget.py`) |
|--------|-------------------|--------------------------------|
| **Method** | Curve-based boundary evaluation | Polygon containment with shapely |
| **Boundary Detection** | Direct curve comparison | Buffer tolerance (2.0 MPa) |
| **Triple Points** | Used as vertices in curve interpolation | Implicit in polygon vertices |
| **On-Boundary Behavior** | Returns exact phase (first match) | Returns "Phase1/Phase2" for boundaries |
| **Precision** | Exact curve evaluation | Geometric approximation |

---

## 1. CLI Approach: Curve-Based Evaluation

**File:** `quickice/phase_mapping/lookup.py`

### How it works

- `lookup_phase(T, P)` evaluates boundary curves hierarchically
- Uses `melting_pressure(T, "Ih")` for Ih-Liquid boundary
- Uses `ih_ii_boundary(T)`, `ii_iii_boundary(T)`, etc. for solid-solid boundaries
- **First match wins** - no ambiguity

### Boundary handling

```python
# Example: Ice Ih detection (lines 332-338)
if T <= 273.16:
    P_melt = melting_pressure(T, "Ih")
    if P < P_melt:
        phase_id = "ice_ih"
        return _build_result(phase_id, T, P)
```

- If `P == P_melt` exactly → returns "ice_ih" (below melting curve)
- No explicit "on boundary" detection - just curve comparison

### Triple point handling

- Triple points are used as **curve interpolation endpoints**
- Example: `ih_ii_boundary(T)` interpolates from `Ih_II_III` triple point (238.55K, 212.9 MPa)
- Triple points define **where one boundary ends and another begins**
- Not explicitly detected - just part of the curve math

### Example at 273.15K, 0.1 MPa

```python
T = 273.15, P = 0.1
P_melt = melting_pressure(273.15, "Ih")  # ~0.135 MPa
P < P_melt → True → returns "ice_ih"
```

**Result:** Correctly identifies as Ice Ih.

---

## 2. GUI Approach: Polygon Containment

**File:** `quickice/gui/phase_diagram_widget.py`

### How it works

- `PhaseDetector` builds shapely polygons for each phase
- Uses `polygon.covers(point)` to check containment (includes boundary)
- Polygons built by `_build_phase_polygon_from_curves()` in CLI's phase_diagram.py

### Boundary detection

```python
# Lines 92-95
BOUNDARY_TOLERANCE = 2.0  # MPa

# Lines 153-181
def _check_near_boundary(self, point, inside_phase=None):
    buffered_point = point.buffer(self.BOUNDARY_TOLERANCE)
    for phase_id, polygon in self._phase_polygons.items():
        distance = polygon.boundary.distance(point)
        if distance < self.BOUNDARY_TOLERANCE:
            boundary_phases.append(phase_id)
```

- Creates buffer zone around point
- Checks if buffer intersects multiple polygons
- Returns "Phase1/Phase2" if on boundary

### Triple point handling

- Triple points are **polygon vertices** (from `_build_phase_polygon_from_curves`)
- No explicit triple point detection
- If point is exactly at triple point → covered by multiple polygons → returns "Multiple phases possible"

### Example at 273.15K, 0.1 MPa

```python
T = 273.15, P = 0.1
# Vapor polygon boundary at P ≈ 0.0006 MPa (saturation curve)
# Distance from point to vapor boundary ≈ 0.0994 MPa
# BOUNDARY_TOLERANCE = 2.0 MPa
# 0.0994 < 2.0 → False positive: "Ih/Vapor" instead of just "Ih"
```

**Result:** Incorrectly identifies as boundary. **This is the bug.**

---

## 3. Key Differences

| Feature | CLI | GUI |
|---------|-----|-----|
| **Boundary on curve** | Returns single phase | Returns "Phase1/Phase2" |
| **Triple point** | Returns one phase (first match) | Returns "Multiple phases possible" |
| **Near boundary** | Not detected | Detected via buffer tolerance |
| **Precision** | Curve equation | Polygon approximation |
| **Vapor region** | Raises `UnknownPhaseError` | Has vapor polygon |

---

## 4. Root Cause of the Bug

### CLI: No tolerance buffer

```python
# CLI logic (lookup.py lines 332-338)
if T <= 273.16:
    P_melt = melting_pressure(T, "Ih")  # 0.135 MPa at 273.15K
    if P < P_melt:  # 0.1 < 0.135 → True
        return "ice_ih"
```

Exact curve comparison. No ambiguity.

### GUI: Absolute tolerance too large

```python
# GUI logic (phase_diagram_widget.py)
BOUNDARY_TOLERANCE = 2.0  # MPa - PROBLEM!

# At P=0.1 MPa:
# - Vapor boundary at P ≈ 0.0006 MPa
# - Distance = 0.0994 MPa
# - 0.0994 < 2.0 → FALSE POSITIVE
```

The 2.0 MPa tolerance works at high pressures (e.g., P=1000 MPa) but fails at low pressures (P=0.1 MPa).

---

## 5. Solution for Item 2

Replace absolute tolerance with **relative tolerance**:

```python
# Proposed fix in phase_diagram_widget.py

# Replace line 95:
# BOUNDARY_TOLERANCE = 2.0

# With:
BOUNDARY_TOLERANCE_TEMP = 2.0      # K (absolute for temperature)
BOUNDARY_TOLERANCE_PRESSURE_FRAC = 0.05  # 5% of pressure (relative)

# In _check_near_boundary (line 166):
# Replace:
# buffered_point = point.buffer(self.BOUNDARY_TOLERANCE)

# With:
tolerance_P = max(0.01, pressure_mpa * BOUNDARY_TOLERANCE_PRESSURE_FRAC)
# At P=0.1 MPa: tolerance = 0.005 MPa (point at 0.099 MPa is NOT near boundary)
# At P=1000 MPa: tolerance = 50 MPa (appropriate for high pressure)
```

This maintains user-friendly boundary detection while matching CLI precision.

---

## 6. Triple Points Reference

From `quickice/phase_mapping/triple_points.py`:

| Triple Point | T (K) | P (MPa) | Phases |
|--------------|-------|---------|--------|
| Ih_III_Liquid | 251.165 | 207.5 | Ih, III, Liquid |
| Ih_II_III | 238.55 | 212.9 | Ih, II, III |
| II_III_V | 248.85 | 344.3 | II, III, V |
| III_V_Liquid | 256.165 | 346.3 | III, V, Liquid |
| II_V_VI | 218.95 | 620.0 | II, V, VI |
| V_VI_Liquid | 273.31 | 625.9 | V, VI, Liquid |
| VI_VII_Liquid | 354.75 | 2200.0 | VI, VII, Liquid |
| VI_VII_VIII | 278.0 | 2100.0 | VI, VII, VIII |
| Ih_XI_Vapor | 72.0 | 0.0001 | Ih, XI, Vapor |
| VII_VIII_X | 100.0 | 62000.0 | VII, VIII, X |
