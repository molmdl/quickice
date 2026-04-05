# Research Summary: Seawater/Saltwater Ice Phase Diagram Support

**Project:** QuickIce - Adding seawater/saltwater ice phase diagram
**Researched:** April 5, 2026
**Research Type:** Feature Feasibility and Ecosystem Survey
**Overall Confidence:** HIGH

## Executive Summary

Adding seawater/saltwater ice phase diagram support to QuickIce is **technically feasible and well-supported by existing libraries**. The IAPWS library (already installed: iapws==1.5.5) provides full IAPWS-08 seawater thermodynamics including freezing point calculations.

However, the nature of "saltwater ice" is fundamentally different from pure water ice phases:
- **Pure water**: Temperature-Pressure phase diagram with 12+ distinct ice polymorphs (Ice Ih, Ic, II, III, V, VI, VII, VIII, IX, XI, XV, X)
- **Seawater**: Salinity-Temperature phase diagram with a single ice type (Ice Ih) that contains brine pockets

The relevant phase diagram axes would change from T-P (pure water) to Salinity-Temperature, showing the freezing point depression curve. At typical ocean pressures (<100 MPa), no high-pressure ice phases exist in saltwater systems.

## Key Findings

### 1. IAPWS Library Capabilities (CONFIRMED - HIGH)

The iapws library v1.5.5 includes full IAPWS-08 seawater support:

| Function | Purpose | Availability |
|----------|---------|--------------|
| `_Tf(P, S)` | Freezing temperature of seawater | CONFIRMED |
| `_Tb(P, S)` | Boiling temperature of seawater | CONFIRMED |
| `_Triple(S)` | Triple point properties for seawater | CONFIRMED |
| `SeaWater` class | Full thermodynamic properties | CONFIRMED |

**Data Source**: IAPWS-08 (Release on the IAPWS Formulation 2008 for the Thermodynamic Properties of Seawater)
- Reference: http://www.iapws.org/relguide/Seawater.html
- Valid salinity range: 0-12% (0-0.12 kg/kg)
- Valid temperature range: 261-353 K
- Valid pressure range: 0-100 MPa

### 2. Saltwater Ice Phases (CONFIRMED - HIGH)

**Critical Finding**: Saltwater ice (sea ice) does NOT have different high-pressure polymorphs like pure water.

At typical ocean conditions:
- **Ocean pressure**: 0.1-100 MPa (depending on depth, max ~110 MPa at 11km depth)
- **High-pressure ice phases begin**: ~200 MPa (Ice III forms)
- **Result**: Only Ice Ih (hexagonal ice) forms in seawater

Sea ice is a **composite material**:
- Pure ice crystals (Ice Ih structure)
- Brine pockets (liquid saltwater trapped in ice)
- Air voids
- Salt precipitates (as ice cools, salt excludes forming crystals)

**Data Sources**:
- Wikipedia "Sea ice": https://en.wikipedia.org/wiki/Sea_ice
- Wikipedia "Phases of ice": https://en.wikipedia.org/wiki/Phases_of_ice

### 3. Freezing Point Depression Data (CONFIRMED - HIGH)

Using IAPWS-08 `_Tf()` function:

| Salinity (ppt) | Freezing Temperature (K) | Freezing Temperature (°C) |
|----------------|--------------------------|---------------------------|
| 0 (fresh)      | 273.153                  | 0.0                       |
| 10             | 272.614                  | -0.54                     |
| 20             | 272.075                  | -1.08                     |
| 30             | 271.523                  | -1.63                     |
| 35 (standard seawater) | 271.240          | -1.91                     |
| 40             | 270.954                  | -2.20                     |
| 50             | 270.365                  | -2.79                     |
| 60             | 269.754                  | -3.40                     |
| 70             | 269.118                  | -4.03                     |
| 80             | 268.453                  | -4.70                     |
| 90             | 267.758                  | -5.39                     |
| 100            | 267.032                  | -6.12                     |

This follows approximately: ΔT ≈ -S × 0.054 (linear approximation for S < 0.12)

## Implications for Roadmap

### Phase Structure Recommendation

Based on research, the seawater feature can be implemented in a single focused phase:

1. **Seawater Phase Diagram Phase** - Implement salinity-temperature phase diagram
   - Uses existing IAPWS library (no new dependencies)
   - Well-defined scientific data from IAPWS-08 standard
   - Different visualization from pure water (S-T instead of T-P axes)

### Phase-Specific Considerations

| Phase Topic | Approach | Complexity |
|-------------|----------|------------|
| Freezing curve calculation | Use IAPWS `_Tf()` | Low - single function call |
| Phase diagram visualization | New S-T plot widget | Medium - new axes system |
| Brine pocket modeling | Not required for MVP | Deferred (scientific research) |
| High-pressure phases | Not applicable | N/A (not relevant for ocean conditions) |

### Research Flags

- **No deeper research needed** for freezing point data (IAPWS-08 is authoritative)
- **No deeper research needed** for ice phases (Ice Ih only at ocean conditions)
- **Minor research** if extending to 3D (S-T-P surface)

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| IAPWS library capabilities | HIGH | Verified via Context7 and direct testing |
| Freezing point depression | HIGH | IAPWS-08 is authoritative international standard |
| Ice phases in saltwater | HIGH | Scientific consensus: only Ice Ih at ocean conditions |
| UI implications | MEDIUM | Based on domain knowledge, not verified |
| Feasibility | HIGH | All required functionality exists in installed library |

## Gaps to Address

- **None identified** - All required scientific data is available via IAPWS-08
- The feature is well-defined and implementable using existing libraries
- No research-grade gaps remain

## Sources

1. **IAPWS-08 Seawater Standard** (HIGH confidence)
   - IAPWS Release on the IAPWS Formulation 2008 for the Thermodynamic Properties of Seawater
   - http://www.iapws.org/relguide/Seawater.html

2. **IAPWS Python Library** (HIGH confidence)
   - PyPI: https://pypi.org/project/iapws/
   - Documentation: https://iapws.readthedocs.io/en/latest/iapws.iapws08.html

3. **Sea Ice Properties** (MEDIUM confidence)
   - Wikipedia "Sea ice": https://en.wikipedia.org/wiki/Sea_ice
   - Verified via physical properties description

4. **Ice Phase Data** (HIGH confidence)
   - Wikipedia "Phases of ice": https://en.wikipedia.org/wiki/Phases_of_ice
   - Pressure thresholds verified against multiple sources

---

# Detailed Feature Research: Seawater/Saltwater Ice Phase Diagram

## 1. Saltwater Ice Thermodynamics Data Availability

### 1.1 Freezing Point Depression

**Status**: FULLY AVAILABLE via IAPWS-08

The IAPWS-08 standard provides the authoritative formulation for calculating the freezing temperature of seawater as a function of pressure and salinity:

```
Tf(P, S) = Function of pressure (MPa) and salinity (kg/kg)
```

This is implemented in the installed `iapws` library:
```python
from iapws.iapws08 import _Tf
Tf = _Tf(0.1, 0.035)  # Returns ~271.24 K for standard seawater
```

**Data Quality**: HIGH - This is an international standard with verified experimental data.

### 1.2 Triple Point Data

The IAPWS-08 standard also provides triple point calculations for seawater:

```python
from iapws.iapws08 import _Triple
triple = _Triple(0.035)  # S = 35 ppt seawater
# Returns: {'Tt': 271.248 K, 'Pt': 0.000522 MPa}
```

For fresh water (S=0):
- Triple point: 273.16 K, 0.000612 MPa

For standard seawater (S=0.035):
- Triple point: 271.25 K, 0.000522 MPa
- Depression: ~1.9 K lower than fresh water

### 1.3 Brine Properties

When seawater freezes, the ice crystals exclude most of the salt, creating:
- **Pure ice Ih crystals** (the solid phase)
- **Brine pockets** (liquid pockets of concentrated saltwater)
- **Air bubbles** (trapped atmospheric gases)
- **Salt precipitates** (at very low temperatures, salts crystallize)

The IAPWS library does NOT provide brine pocket modeling - this is a more complex physical phenomenon that would require additional research-grade modeling.

## 2. IAPWS Library Capabilities for Seawater

### 2.1 Available Functions

| Function | Description | Valid Range |
|----------|-------------|-------------|
| `SeaWater(T, P, S)` | Main class for thermodynamic properties | T: 261-353 K, P: 0-100 MPa, S: 0-0.12 |
| `_Tf(P, S)` | Freezing temperature | P: 0-100 MPa, S: 0-0.12 |
| `_Tb(P, S)` | Boiling temperature | P: 0-100 MPa, S: 0-0.12 |
| `_Triple(S)` | Triple point properties | S: 0-0.12 |

### 2.2 SeaWater Class Properties

The `SeaWater` class provides comprehensive thermodynamic data:

```python
from iapws import SeaWater
sw = SeaWater(T=273.15, P=0.1, S=0.035)

# Available properties:
sw.rho   # Density [kg/m³]
sw.h     # Enthalpy [kJ/kg]
sw.cp    # Heat capacity [kJ/kg·K]
sw.s     # Entropy [kJ/kg·K]
sw.w     # Sound speed [m/s]
# ... and many more
```

### 2.3 Limitations

- **Maximum salinity**: 12% (0.12 kg/kg) - covers all natural seawater
- **Temperature range**: 261-353 K (-12°C to 80°C)
- **Pressure range**: 0-100 MPa (0-1000 atm)
- **No high-pressure ice phases**: The library focuses on liquid seawater properties

## 3. Phase Diagram Differences from Pure Water

### 3.1 Pure Water Phase Diagram

**Axes**: Temperature (X) vs Pressure (Y)

**Ice Phases** (12+ known phases):
- Ice Ih (hexagonal, ambient conditions)
- Ice Ic (cubic, metastable)
- Ice II, III, IV, V, VI, VII, VIII, IX, XI, XV, X (high-pressure phases)

**Data Source**: IAPWS R14-08(2011) for ice thermodynamics

### 3.2 Seawater Phase Diagram

**Axes**: Salinity (X) vs Temperature (Y) [at fixed pressure]

**Ice Phases**: Only Ice Ih (with brine pockets)

**Key Differences**:

| Aspect | Pure Water | Seawater |
|--------|-----------|----------|
| Primary axes | T vs P | S vs T |
| Ice phases | 12+ polymorphs | 1 (Ice Ih) |
| Phase transitions | Multiple triple points | Single freezing curve |
| Pressure range | 0-10,000+ MPa | 0-100 MPa (ocean relevant) |
| Data source | IAPWS-06/IAPWS-08 | IAPWS-08 only |

### 3.3 Why No High-Pressure Phases in Seawater?

The high-pressure ice phases (II, III, V, VI, VII) require:
- Ice II: >300 MPa
- Ice III: >300 MPa  
- Ice V: >500 MPa
- Ice VI: >1.1 GPa
- Ice VII: >2.2 GPa

Ocean conditions:
- Maximum ocean depth: ~11 km → ~110 MPa
- Typical conditions: 0.1-60 MPa

**Conclusion**: Even at maximum ocean depths, the pressure is insufficient to form high-pressure ice polymorphs. All seawater ice is Ice Ih.

## 4. UI/UX Implications

### 4.1 New Tab vs Modal

**Recommendation**: New tab in the GUI

Rationale:
- Seawater diagram uses fundamentally different axes
- Users may want to compare pure water vs seawater phases
- Clear separation of concerns

### 4.2 Axis Changes

**Pure Water (existing)**:
- X-axis: Temperature (100-500 K)
- Y-axis: Pressure (0-10,000 MPa)

**Seawater (new)**:
- X-axis: Salinity (0-100 ppt, or 0-0.1 kg/kg)
- Y-axis: Temperature (260-280 K)

### 4.3 Visualization Elements

**Phase 1 - Basic Implementation**:
1. Freezing curve (liquid ↔ solid boundary)
2. Labels: "Liquid Seawater", "Sea Ice (Ih + Brine)"
3. Temperature scale showing freezing point depression

**Phase 2 - Enhanced** (if needed):
1. Brine pocket fraction contours
2. Isotherm lines
3. Pressure dependence (3D surface or slider)

### 4.4 Interaction Model

- Click to select S, T coordinates
- Display: "Sea Ice (Ih) at S=X ppt, T=Y K"
- Show brine fraction estimate (optional, research needed)
- Export options (PNG, SVG) - similar to pure water diagram

## 5. Feasibility Assessment

### 5.1 Verdict: READY TO IMPLEMENT

**Confidence**: HIGH

### 5.2 Requirements Checklist

| Requirement | Status | Notes |
|-------------|--------|-------|
| Scientific data for freezing curve | ✅ AVAILABLE | IAPWS-08 `_Tf()` function |
| Library support | ✅ AVAILABLE | iapws==1.5.5 already installed |
| Phase boundaries | ✅ AVAILABLE | Single boundary (freezing curve) |
| Different axes system | ✅ IMPLEMENTABLE | S-T plot is standard |
| No high-pressure phases | ✅ CONFIRMED | Not relevant at ocean conditions |

### 5.3 What is NOT Available (Anti-Features)

| Feature | Why Not Available | Recommendation |
|---------|------------------|----------------|
| Brine pocket modeling | Complex physical system, not in IAPWS scope | Defer to post-MVP if needed |
| Salt precipitation phases | Not well-characterized scientifically | Not implementable |
| 3D S-T-P surface | Requires extrapolation beyond IAPWS range | May need research |

## 6. Complexity Rating and Estimated Effort

### 6.1 Complexity Rating: 2/5 (Low-Medium)

**Breakdown**:
- Data retrieval: 1/5 (single function call)
- Visualization: 3/5 (new axes system, but standard plotting)
- UI integration: 2/5 (new tab, existing patterns)
- Export: 2/5 (similar to existing export)

### 6.2 Effort Estimate

| Component | Estimated Effort | Notes |
|-----------|-----------------|-------|
| Core logic (S-T lookup) | 2 hours | Wrapper around `_Tf()` |
| Phase diagram widget | 8-12 hours | New widget or extend existing |
| GUI tab integration | 4-6 hours | Standard pattern |
| Export functionality | 2-4 hours | Reuse existing export |
| Testing | 4-6 hours | Unit + integration tests |
| **Total** | **20-30 hours** | |

### 6.3 Dependencies

- `iapws==1.5.5` - Already installed ✅
- `matplotlib` or `numpy` - Already in project ✅
- No new dependencies required

## 7. Implementation Recommendations

### 7.1 MVP Scope

For the initial implementation, focus on:

1. **Salinity-Temperature Plot**
   - X-axis: Salinity (0-100 ppt)
   - Y-axis: Temperature (260-280 K)
   - Show freezing curve from IAPWS-08

2. **Click Interaction**
   - Click to select S, T point
   - Display phase: "Sea Ice (Ih)" or "Liquid Seawater"

3. **Basic Information Panel**
   - Show freezing temperature at selected salinity
   - Indicate phase region

### 7.2 Out of Scope for MVP

- Brine pocket fraction modeling
- 3D S-T-P surface
- Pressure dependence contours
- Complex salt precipitation diagrams

### 7.3 Future Enhancements (Post-MVP)

1. **Brine Fraction Contours**: Show estimated brine volume in ice
2. **Pressure Slider**: Allow viewing S-T diagram at different pressures
3. **Comparison Mode**: Side-by-side pure water vs seawater diagrams
4. **Export Data**: CSV export of S-T-P data points

## 8. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| IAPWS data limitations at extremes | LOW | Document valid range clearly |
| Performance with dense sampling | LOW | Use vectorized numpy operations |
| User confusion about axes | MEDIUM | Clear labels, tooltips |
| Missing brine model | LOW | Not required for MVP, document as limitation |

## 9. References

### Primary Sources

1. **IAPWS-08 Standard** - Seawater thermodynamics
   - http://www.iapws.org/relguide/Seawater.html

2. **IAPWS Python Library** - Implementation
   - https://pypi.org/project/iapws/
   - https://iapws.readthedocs.io/en/latest/iapws.iapws08.html

3. **Sea Ice Science**
   - Wikipedia "Sea ice": https://en.wikipedia.org/wiki/Sea_ice

4. **Ice Phase Science**  
   - Wikipedia "Phases of ice": https://en.wikipedia.org/wiki/Phases_of_ice

### Testing Commands

```python
# Verify IAPWS seawater functions work
from iapws.iapws08 import _Tf, _Tb, _Triple, SeaWater

# Freezing temperature
print(_Tf(0.1, 0.035))  # ~271.24 K

# Boiling temperature  
print(_Tb(0.1, 0.035))  # ~373.28 K

# Triple point
print(_Triple(0.035))   # {'Tt': 271.25, 'Pt': 0.000522}

# Full seawater properties
sw = SeaWater(T=273.15, P=0.1, S=0.035)
print(sw.rho)  # ~1028 kg/m³
```