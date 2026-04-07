# Phase 15: Phase Diagram Data Update - Research

**Researched:** 2026-04-08
**Domain:** Thermodynamic data correction, IAPWS R14-08(2011) compliance
**Confidence:** HIGH

## Summary

This phase corrects triple point data in QuickIce's phase diagram system to comply with IAPWS R14-08(2011) standards. The system currently has outdated values in two separate triple point dictionaries (triple_points.py and ice_boundaries.py) that must be kept in sync, plus polygon vertices derived from those values.

**Primary recommendation:** Update all data sources atomically in a single commit to prevent inconsistent states. Add validation tests that verify triple point consistency between files.

## Standard Stack

The established data structure for this domain:

### Core Files
| File | Purpose | Data Type |
|------|---------|-----------|
| `quickice/phase_mapping/triple_points.py` | Triple point coordinates | `Dict[str, Tuple[float, float]]` |
| `quickice/phase_mapping/data/ice_boundaries.py` | Triple points + polygons + melting curves | `Dict[str, dict]` |
| `quickice/phase_mapping/melting_curves.py` | IAPWS R14-08(2011) melting equations | Functions |
| `quickice/phase_mapping/solid_boundaries.py` | Solid-solid boundary interpolation | Functions |
| `quickice/phase_mapping/lookup.py` | Phase lookup (curve-based) | Functions |
| `quickice/output/phase_diagram.py` | Phase diagram generation | `_build_phase_polygon_from_curves()` |

### Supporting Files
| File | Purpose | Update Type |
|------|---------|-------------|
| `tests/test_phase_mapping.py` | Phase mapping tests | Comments only |
| `quickice/gui/phase_diagram_widget.py` | GUI phase diagram | Auto-fixed (uses get_triple_point()) |

**Key insight:** Triple points are defined in TWO places:
1. `triple_points.py` - Simple `Dict[str, Tuple[float, float]]`
2. `ice_boundaries.py` - Detailed `Dict[str, dict]` with "T", "P", "description"

Both must be updated to match IAPWS R14-08(2011).

## Architecture Patterns

### Current Triple Point Structure

```python
# triple_points.py (lines 16-33)
TRIPLE_POINTS: Dict[str, Tuple[float, float]] = {
    "Ih_III_Liquid": (251.165, 207.5),  # NEEDS: (251.165, 209.9)
    "Ih_II_III": (238.55, 212.9),       # NEEDS: (238.45, 212.9)
    # ... 8 total entries
}

# ice_boundaries.py (lines 26-76)
TRIPLE_POINTS = {
    "ih_iii_liquid": {
        "T": 251.165,
        "P": 207.5,  # NEEDS: 209.9
        "description": "Triple point: Ice Ih, Ice III, Liquid water"
    },
    # ... 8 total entries
}
```

### Phase Polygon Construction

The system has **two different** polygon systems:

1. **ice_boundaries.py PHASE_POLYGONS** (lines 162-252): Static vertex lists
   - Used for legacy compatibility
   - Hardcoded vertices from triple point values
   
2. **phase_diagram.py _build_phase_polygon_from_curves()** (lines 172-208): Dynamic curve-based
   - Uses IAPWS melting curves and solid boundaries
   - Single source of truth approach
   - Must register each phase in dispatch function

**Critical finding:** Ice Ic polygon exists in ice_boundaries.py (lines 179-186) but is NOT registered in phase_diagram.py's `_build_phase_polygon_from_curves()`.

### Lookup System (Curve-Based)

```python
# lookup.py - Uses curve evaluation, NOT polygon containment
# Source: verified in code (lines 65-363)

def lookup_phase(temperature: float, pressure: float) -> dict:
    """
    Determines phase using hierarchical curve evaluation:
    1. Check Ice X (P > 30 GPa)
    2. Check Ice VII/VIII (P > 2100 MPa, T-dependent)
    3. Check Ice XV (T=80-108K, P=950-2100 MPa)
    4. Check Ice VI (T >= 218.95K, P > 620 MPa)
    5. Check Ice V (T=218.95-273.31K, P > 344 MPa)
    6. Check Ice IX (T < 140K, P=200-400 MPa)
    7. Check Ice II (T < 248.85K, P > 200 MPa)
    8. Check Ice III (T=238.55-256.165K, P > 200 MPa)
    9. Check Ice XI (T < 72K, P < 200 MPa)
    10. Check Ice Ih (T <= 273.16K, P < melting)
    11. Check Ice Ic (T < 150K, P < 100 MPa) - FALLBACK
    """
```

**Important:** Ice Ic is currently checked at step 11 (fallback) in lookup_phase(). The NEW-02 requirement asks to register it in `_build_phase_polygon_from_curves()`, which is for diagram generation, NOT lookup.

## Don't Hand-Roll

Problems with existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Melting pressure calculation | Custom polynomials | `melting_curves.py` functions | IAPWS R14-08(2011) certified |
| Solid boundary calculation | Reinventing interpolation | `solid_boundaries.py` functions | Uses actual triple points |
| Triple point storage | Multiple dicts | Single source + derived | Prevents sync issues |

**Key insight:** The melting_curves.py file ALREADY has correct IAPWS R14-08(2011) Pref values:
- Line 39: `Pref = 350.100` (Ice V at 256.164 K) ✓
- Line 47: `Pref = 632.400` (Ice VI at 273.31 K) ✓  
- Line 55: `Pref = 2216.000` (Ice VII at 355 K) ✓

The incorrect values are in ice_boundaries.py MELTING_CURVE_COEFFICIENTS which uses Simon-Glatzel approximation, not the official IAPWS values.

## Common Pitfalls

### Pitfall 1: Triple Point Synchronization
**What goes wrong:** Updating one TRIPLE_POINTS dict but not the other causes inconsistent state
**Why it happens:** Two files define the same data independently
**How to avoid:** 
1. Update both files in same commit
2. Add validation test that compares values
**Warning signs:** Tests pass but phase diagram shows wrong boundaries

### Pitfall 2: Polygon Vertex Inconsistency
**What goes wrong:** PHASE_POLYGONS vertices don't match updated triple points
**Why it happens:** Vertices were manually calculated from old values
**How to avoid:** 
1. Update all polygon vertices that reference changed triple points
2. Verify with: `python -c "from quickice.phase_mapping.data.ice_boundaries import PHASE_POLYGONS; import pprint; pprint.pprint(PHASE_POLYGONS['ice_ih'])"`
**Warning signs:** Phase regions overlap or have gaps in diagram

### Pitfall 3: Ice Ic Registration Confusion
**What goes wrong:** Confusing diagram generation (phase_diagram.py) with lookup (lookup.py)
**Why it happens:** Both have "phase" in names, different purposes
**How to avoid:** 
- `_build_phase_polygon_from_curves()` → For DIAGRAM RENDERING
- `lookup_phase()` → For PHASE DETERMINATION
- Ice Ic needs to be added to diagram rendering, lookup already handles it
**Warning signs:** Ice Ic appears in lookup but not in generated diagram

### Pitfall 4: Test Value Hardcoding
**What goes wrong:** Tests with hardcoded triple point values fail after update
**Why it happens:** Tests verify specific (T, P) coordinates
**How to avoid:** 
1. Check test comments for triple point references
2. Update comments, not test logic (tests verify correct behavior)
**Warning signs:** pytest fails with "expected X, got Y" for triple points

### Pitfall 5: Melting Curve Pref vs melting_curves.py Pref
**What goes wrong:** Updating ice_boundaries.py Pref but melting_curves.py already has correct values
**Why it happens:** Two different implementations of melting curves
**How to avoid:** 
- melting_curves.py uses ACTUAL IAPWS equations (authoritative)
- ice_boundaries.py uses Simon-Glatzel approximation (for documentation only)
- Only update ice_boundaries.py to match melting_curves.py
**Warning signs:** Values in both files diverge

## Code Examples

### Triple Point Update Pattern

```python
# BEFORE (triple_points.py line 17)
"Ih_III_Liquid": (251.165, 207.5),

# AFTER
"Ih_III_Liquid": (251.165, 209.9),
```

```python
# BEFORE (ice_boundaries.py lines 28-31)
"ih_iii_liquid": {
    "T": 251.165,
    "P": 207.5,  # ← WRONG
    "description": "Triple point: Ice Ih, Ice III, Liquid water"
},

# AFTER
"ih_iii_liquid": {
    "T": 251.165,
    "P": 209.9,  # ← CORRECT per IAPWS R14-08(2011)
    "description": "Triple point: Ice Ih, Ice III, Liquid water"
},
```

### Ice Ic Polygon Builder Addition

```python
# Add to phase_diagram.py after line 172 (before _build_ice_ih_polygon)

def _build_ice_ic_polygon() -> List[Tuple[float, float]]:
    """Ice Ic region: metastable phase at low temperature and pressure.
    
    Ice Ic (cubic ice) is metastable with respect to Ice Ih but can form
    at very low temperatures (50-150 K) and low pressures (0-100 MPa).
    
    Returns:
        List of (T, P) tuples forming the polygon boundary
    """
    vertices = [
        (50.0, 0.1),      # Lower-left corner (cold, low P)
        (150.0, 0.1),     # Lower-right corner (T=150K upper limit)
        (150.0, 100.0),   # Upper-right corner (P=100 MPa upper limit)
        (50.0, 100.0),    # Upper-left corner
        (50.0, 0.1),      # Close polygon
    ]
    return vertices
```

```python
# Add to _build_phase_polygon_from_curves() dispatch (around line 186)

def _build_phase_polygon_from_curves(phase_id: str) -> List[Tuple[float, float]]:
    # ... existing elif clauses ...
    elif phase_id == "ice_ih":
        return _build_ice_ih_polygon()
    elif phase_id == "ice_ic":  # ← NEW
        return _build_ice_ic_polygon()
    # ... rest ...
```

### Polygon Vertex Update Pattern

```python
# BEFORE (ice_boundaries.py lines 166-175)
"ice_ih": [
    (100.0, 0.0),
    (273.16, 0.0),
    (273.16, 100.0),
    (251.165, 207.5),   # ← Ih-III-Liquid TP (WRONG)
    (238.55, 212.9),    # ← Ih-II-III TP (WRONG)
    # ...
]

# AFTER
"ice_ih": [
    (100.0, 0.0),
    (273.16, 0.0),
    (273.16, 100.0),
    (251.165, 209.9),   # ← Ih-III-Liquid TP (CORRECT)
    (238.45, 212.9),    # ← Ih-II-III TP (CORRECT)
    # ...
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Polygon containment lookup | Curve-based evaluation | Phase 2 (v1.0) | Eliminated overlap errors |
| Single PHASE_POLYGONS source | Dual polygon systems | Phase 5 (v1.0) | Diagram uses curves, legacy has static |
| Hardcoded triple points | Dict-based storage | Phase 2 (v1.0) | Centralized but duplicated |

**Deprecated/outdated:**
- **Simon-Glatzel approximation in ice_boundaries.py**: melting_curves.py has exact IAPWS equations. ice_boundaries.py version kept for reference only.
- **PHASE_POLYGONS for lookup**: Now uses curve evaluation. PHASE_POLYGONS still used by diagram generation legacy code.

## Data Changes Summary

### Triple Point Corrections (from phase_update_data.md)

| Triple Point | Current (WRONG) | Correct (IAPWS/LSBU) | Source |
|--------------|-----------------|---------------------|--------|
| Ih-III-Liquid | (251.165, 207.5) | (251.165, 209.9) | LSBU [537] |
| Ih-II-III | (238.55, 212.9) | (238.45, 212.9) | LSBU [537] |
| II-III-V | (248.85, 344.3) | (249.4, 355.5) | Journaux 2019 |
| III-V-Liquid | (256.165, 346.3) | (256.164, 350.1) | LSBU [537] |
| II-V-VI | (218.95, 620.0) | (201.9, 670.8) | Journaux 2019 |
| V-VI-Liquid | (273.31, 625.9) | (273.31, 632.4) | LSBU [537] |
| VI-VII-Liquid | (354.75, 2200.0) | (355.0, 2216.0) | LSBU [537] |
| VI-VII-VIII | (278.0, 2100.0) | (278.15, 2100.0) | LSBU [537] |

### Melting Curve Pref Corrections (ice_boundaries.py only)

| Line | Field | Current | Correct | Note |
|------|-------|---------|---------|------|
| 109 | P_ref | 207.5 | 209.9 | Ice III |
| 122 | P_ref | 346.3 | 350.1 | Ice V |
| 135 | P_ref | 2200.0 | 2216.0 | Ice VI |
| 149 | P_ref | 2200.0 | 2216.0 | Ice VII |
| 150 | A | 2200.0 | 2216.0 | Ice VII coefficient |

**Note:** melting_curves.py already has correct values. Do NOT modify it.

## Open Questions

1. **Ice Ic lookup priority**
   - What we know: Ice Ic is currently checked at step 11 (fallback) in lookup_phase()
   - What's unclear: Should it have higher priority? (Currently: X → VII/VIII → XV → VI → V → IX → II → III → XI → Ih → Ic)
   - Recommendation: Keep current priority (Ice Ic as fallback for metastable conditions)

2. **PHASE_POLYGONS necessity**
   - What we know: ice_boundaries.py PHASE_POLYGONS still exists but diagram uses curve-based
   - What's unclear: Is PHASE_POLYGONS still used anywhere?
   - Recommendation: Update for consistency, investigate removal in future phase

3. **Validation test coverage**
   - What we know: Tests verify lookup works, but don't test specific triple point values
   - What's unclear: Should we add tests that validate triple point consistency between files?
   - Recommendation: Add validation test: `assert triple_points.TRIPLE_POINTS["Ih_III_Liquid"][1] == ice_boundaries.TRIPLE_POINTS["ih_iii_liquid"]["P"]`

## Sources

### Primary (HIGH confidence)
- `.planning/phase_update_data.md` - Complete data change specification
- `quickice/phase_mapping/melting_curves.py` - IAPWS R14-08(2011) authoritative implementation
- `quickice/phase_mapping/lookup.py` - Curve-based phase lookup (verified)

### Secondary (MEDIUM confidence)
- `quickice/phase_mapping/triple_points.py` - Triple point definitions (needs update)
- `quickice/phase_mapping/data/ice_boundaries.py` - Multiple data structures (needs update)
- `tests/test_phase_mapping.py` - Test patterns verified

### Tertiary (LOW confidence)
- `state_reference.md` - Reference sources list (academic papers, websites)

### External References
- **IAPWS R14-08(2011)**: http://www.iapws.org/release/MeltIce.pdf
- **Journaux et al. (2019)**: J. Geophys. Res.: Planets, DOI: 10.1029/2019JE006176
- **Journaux et al. (2020)**: Space Science Review, 7:216
- **LSBU Water Phase Data**: https://ergodic.ugr.es/termo/lecciones/water1.html

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All files located and structure understood
- Architecture: HIGH - Curve-based system verified in code
- Pitfalls: HIGH - Common issues identified from code review
- Data changes: HIGH - Complete specification in phase_update_data.md

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable data, 30 days)
