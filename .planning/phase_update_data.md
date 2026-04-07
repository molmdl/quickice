# Phase Diagram Data Update Report

## Reference Sources

1. **IAPWS R14-08(2011)** - Melting curve reference pressures (Pref values in melting_curves.py are correct)
2. **vitroid.github.io [537]** - Standard triple point measurements
3. **Journaux et al. (2019, 2020) [3832]** - Updated II-III-V and II-V-VI triple points
   - Journaux et al., J. Geophys. Res.: Planets (2019), DOI: 10.1029/2019JE006176
   - Journaux et al., Space Science Review (2020), 7:216

---

## Files to Update

### FILE 1: quickice/phase_mapping/triple_points.py

**Lines 16-33: TRIPLE_POINTS dictionary**

| Line | Key | Current | Correct | Source |
|------|-----|---------|---------|--------|
| 17 | Ih_III_Liquid | (251.165, 207.5) | (251.165, 209.9) | [537] |
| 18 | Ih_II_III | (238.55, 212.9) | (238.45, 212.9) | [537] |
| 19 | II_III_V | (248.85, 344.3) | (249.4, 355.5) | [3832] |
| 20 | III_V_Liquid | (256.165, 346.3) | (256.164, 350.1) | [537] |
| 21 | II_V_VI | (218.95, 620.0) | (201.9, 670.8) | [3832] |
| 22 | V_VI_Liquid | (273.31, 625.9) | (273.31, 632.4) | [537] |
| 23 | VI_VII_Liquid | (354.75, 2200.0) | (355.0, 2216.0) | [537] |
| 24 | VI_VII_VIII | (278.0, 2100.0) | (278.15, 2100.0) | [537] |

---

### FILE 2: quickice/phase_mapping/data/ice_boundaries.py

**Lines 26-76: TRIPLE_POINTS dictionary**

| Line | Field | Current | Correct | Source |
|------|-------|---------|---------|--------|
| 30 | 'P' | 207.5 | 209.9 | [537] |
| 36 | 'T' | 238.55 | 238.45 | [537] |
| 42 | 'T' | 248.85 | 249.4 | [3832] |
| 43 | 'P' | 344.3 | 355.5 | [3832] |
| 49 | 'P' | 346.3 | 350.1 | [537] |
| 54 | 'T' | 218.95 | 201.9 | [3832] |
| 55 | 'P' | 620.0 | 670.8 | [3832] |
| 61 | 'P' | 625.9 | 632.4 | [537] |
| 67 | 'P' | 2200.0 | 2216.0 | [537] |
| 72 | 'T' | 278.0 | 278.15 | [537] |

**Lines 78-154: MELTING_CURVE_COEFFICIENTS dictionary**

| Line | Field | Current | Correct | Source |
|------|-------|---------|---------|--------|
| 109 | 'P_ref' | 207.5 | 209.9 | [537] |
| 122 | 'P_ref' | 346.3 | 350.1 | [537] |
| 135 | 'P_ref' | 2200.0 | 2216.0 | [537] |
| 149 | 'P_ref' | 2200.0 | 2216.0 | [537] |
| 150 | 'A' | 2200.0 | 2216.0 | [537] |

**Lines 162-252: PHASE_POLYGONS dictionary**

| Line | Vertex | Current | Correct | Source |
|------|--------|---------|---------|--------|
| 171 | Ice Ih TP | (251.165, 207.5) | (251.165, 209.9) | [537] |
| 172 | Ice Ih TP | (238.55, 212.9) | (238.45, 212.9) | [537] |
| 194 | Ice II TP | (248.85, 344.3) | (249.4, 355.5) | [3832] |
| 205 | Ice III TP | (256.165, 346.3) | (256.164, 350.1) | [537] |
| 206 | Ice V TP | (273.31, 625.9) | (273.31, 632.4) | [537] |
| 215 | Ice V TP | (273.31, 625.9) | (273.31, 632.4) | [537] |
| 216 | Ice VI TP | (354.75, 2200.0) | (355.0, 2216.0) | [537] |
| 225 | Ice VI TP | (354.75, 2200.0) | (355.0, 2216.0) | [537] |
| 226 | Ice VII TP | (278.0, 2100.0) | (278.15, 2100.0) | [537] |

---

### FILE 3: quickice/output/phase_diagram.py

**Lines 233-237: _build_ice_ih_polygon() function**

| Line | Current | Correct |
|------|---------|---------|
| 233 | # Ih-III-Liquid triple point (251.165 K, 207.5 MPa) | # Ih-III-Liquid triple point (251.165 K, 209.9 MPa) |
| 234 | vertices.append((251.165, 207.5)) | vertices.append((251.165, 209.9)) |
| 236 | # Ih-II-III triple point (238.55 K, 212.9 MPa) | # Ih-II-III triple point (238.45 K, 212.9 MPa) |
| 237 | vertices.append((238.55, 212.9)) | vertices.append((238.45, 212.9)) |

**Line 468: _build_ice_vii_polygon() - comment only**

| Current | Correct |
|---------|---------|
| T_tp_liq, P_tp_liq = get_triple_point('VI_VII_Liquid') # (354.75, 2200) | T_tp_liq, P_tp_liq = get_triple_point('VI_VII_Liquid') # (355.0, 2216) |

**ADD NEW FUNCTION: _build_ice_ic_polygon()**

Insert after imports (around line 172), before _build_ice_ih_polygon():

```python
def _build_ice_ic_polygon() -> List[Tuple[float, float]]:
    """Ice Ic region: metastable phase at low temperature and pressure.
    
    Ice Ic (cubic ice) is metastable with respect to Ice Ih but can form
    at very low temperatures (T < 150 K) and low pressures (P < 100 MPa).
    
    Returns:
        List of (T, P) tuples forming the polygon boundary
    """
    vertices = [
        (50.0, 0.1),      # Lower-left corner (cold, low P)
        (150.0, 0.1),     # Lower-right corner (T=150K upper limit)
        (150.0, 100.0),   # Upper-right corner
        (50.0, 100.0),    # Upper-left corner
        (50.0, 0.1),      # Close polygon
    ]
    return vertices
```

**MODIFY: _build_phase_polygon_from_curves() function**

Add elif clause around line 188:

```python
    elif phase_id == "ice_ic":
        return _build_ice_ic_polygon()
```

---

### FILE 4: quickice/phase_mapping/lookup.py

**Comments only (documentation update)**

| Line | Current | Correct |
|------|---------|---------|
| 230 | # Ice VI: T(273.31-355K at high P), P(626-2200 MPa) | # Ice VI: T(273.31-355K at high P), P(632-2216 MPa) |
| 307 | # Ice III: T(238.55-256.165K), P(207.5-346.3 MPa) | # Ice III: T(238.45-256.164K), P(209.9-350.1 MPa) |
| 334 | # Ice Ih: T(100-273.16K), P(0-207.5 MPa at T=251.165K) | # Ice Ih: T(100-273.16K), P(0-209.9 MPa at T=251.165K) |

---

### FILE 5: tests/test_phase_mapping.py

**Comments only (documentation update)**

| Line | Current | Correct |
|------|---------|---------|
| 108 | # The Ih-III-Liquid triple point is at T=251.165K, P=207.5MPa. | # The Ih-III-Liquid triple point is at T=251.165K, P=209.9MPa. |
| 133 | # The V-VI-Liquid triple point is at T=273.31K, P=625.9MPa. | # The V-VI-Liquid triple point is at T=273.31K, P=632.4MPa. |
| 320 | result = lookup_phase(300, 2200) | result = lookup_phase(300, 2200) # P=2200 OK (in VII range up to 2216) |
| 398 | # The Ih-III-Liquid triple point is at T=251.165K, P=207.5MPa. | # The Ih-III-Liquid triple point is at T=251.165K, P=209.9MPa. |

---

### FILE 6: quickice/gui/phase_diagram_widget.py

**No changes required** - Uses `get_triple_point()` from triple_points.py, will be automatically fixed.

---

## Summary

| File | Type | Count |
|------|------|-------|
| triple_points.py | Values | 8 |
| ice_boundaries.py | Values | 20 |
| phase_diagram.py | Values + Function | 4 + 1 new |
| lookup.py | Comments | 3 |
| test_phase_mapping.py | Comments | 4 |
| phase_diagram_widget.py | Auto-fixed | 0 |

**Total: 32 value updates + 1 new function**

---

## Notes

1. **melting_curves.py is correct** - Pref values already match IAPWS R14-08(2011)
2. **Ice Ic is metastable** - Only included per user request; other metastable phases (IV, XII, XIII) excluded
3. **gas-liquid-Ih triple point** - Outside diagram range (P < 0.1 MPa), not displayed
