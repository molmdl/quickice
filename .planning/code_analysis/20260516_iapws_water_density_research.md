# IAPWS Usage and Water Density Handling in QuickIce

**Analysis Date:** 2026-05-16

## Executive Summary

IAPWS (International Association for the Properties of Water and Steam) calculations are **CRITICAL** for 3D model generation, not just cosmetic display. When IAPWS fails, QuickIce uses fallback density values that may introduce small errors in water layer density but will not crash or produce invalid structures.

---

## Part 1: IAPWS Overview

### What is IAPWS?

IAPWS (International Association for the Properties of Water and Steam) provides internationally standardized formulations for calculating thermodynamic properties of water and ice. QuickIce uses two IAPWS formulations:

1. **IAPWS-95** (`iapws.IAPWS95`) - For liquid water density
   - Reference: "Revised Release on the IAPWS Formulation 1995"
   - **Key feature:** Supports supercooled water (T < 273.15 K) via extrapolation
   - Unlike IAPWS-97, which raises `NotImplementedError` at sub-freezing temperatures

2. **IAPWS R10-06(2009)** (`iapws._iapws._Ice`) - For Ice Ih density
   - Reference: "Revised Release on the Equation of State 2006 for H2O Ice Ih"
   - Valid range: T ≤ 273.16 K, P ≤ 208.566 MPa

### Why IAPWS Matters

QuickIce generates ice-water interfaces at various temperatures and pressures. Accurate density calculations are essential for:
- Correct water molecule spacing in the interface
- Proper mass balance between ice and water layers
- Realistic molecular dynamics simulations

---

## Part 2: Usage Locations

### Water Density (`water_density_gcm3`)

**Module:** `quickice/phase_mapping/water_density.py`

**Called from:**

| File | Line | Purpose |
|------|------|---------|
| `structure_generation/modes/slab.py` | 227 | Calculate water layer density for slab interfaces |
| `structure_generation/modes/pocket.py` | 260 | Calculate water density for pocket filling |
| `structure_generation/modes/piece.py` | 259 | Calculate water density for piece mode |
| `gui/main_window.py` | 1840 | Display density in info panel |
| `gui/view.py` | 802 | Update water density label in UI |

### Ice Ih Density (`ice_ih_density_gcm3`)

**Module:** `quickice/phase_mapping/ice_ih_density.py`

**Called from:**

| File | Line | Purpose |
|------|------|---------|
| `phase_mapping/lookup.py` | 65 | Calculate temperature-dependent Ice Ih density |
| `gui/main_window.py` | 1837 | Display Ice Ih density in info panel |

### IAPWS Phase Boundaries

**Used in:** `quickice/phase_mapping/`
- `melting_curves.py` - IAPWS R14-08(2011) melting curve equations
- `data/ice_boundaries.py` - Triple point coordinates and melting curve coefficients
- `lookup.py` - Phase identification using IAPWS boundaries

---

## Part 3: Water Density Fallback Strategy

### Fallback Values

| Phase | Fallback Density | Source |
|-------|-----------------|--------|
| Liquid water | 0.9998 g/cm³ | Water at 273.15 K (0°C), 1 atm - the melting point |
| Ice Ih | 0.9167 g/cm³ | Ice Ih at 273.15 K, 1 atm |

### Exception Handling

**File:** `quickice/phase_mapping/water_density.py` (lines 70-92)

```python
try:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="extrapolated")
        water = IAPWS95(T=T_K, P=P_MPa)
        rho = water.rho
        
        # Sanity check: density should be in reasonable range
        if rho is not None and 100 < rho < 2000:
            return rho
        else:
            logger.warning(f"Using fallback density for water at T={T_K}K, P={P_MPa}MPa (calculated density {rho} out of range)")
            return FALLBACK_DENSITY_GCM3 * 1000
except (NotImplementedError, ValueError, OverflowError):
    logger.warning(f"Using fallback density for water at T={T_K}K, P={P_MPa}MPa")
    return FALLBACK_DENSITY_GCM3 * 1000
```

### Conditions That Trigger Fallback

| Condition | Exception | When It Occurs |
|-----------|-----------|----------------|
| Invalid input | `ValueError` | Negative T or P |
| Out of formulation range | `NotImplementedError` | Conditions IAPWS cannot handle |
| Numerical overflow | `OverflowError` | Extreme conditions |
| Unreasonable result | Sanity check | Density < 100 or > 2000 kg/m³ |

### IAPWS-95 Robustness

The IAPWS-95 formulation is **very robust**:
- Supports supercooled water via extrapolation (T < 273.15 K)
- Works at very low temperatures (tested down to 250 K)
- Works at high pressures (tested up to 10 MPa)

Fallback is primarily triggered by **invalid inputs** (negative T/P), not normal operating conditions.

---

## Part 4: Impact Assessment on 3D Model Generation

### Water Density IS Used in Structure Generation

The water density calculation **directly affects** 3D model generation:

**File:** `quickice/structure_generation/modes/slab.py` (lines 224-229)

```python
# Calculate water density and scaled cell dimension
T = candidate.metadata.get('temperature', 273.15)
P = candidate.metadata.get('pressure', 0.101325)
target_water_density = water_density_gcm3(T, P)
scale = (TEMPLATE_DENSITY_GCM3 / target_water_density) ** (1.0 / 3.0)
scaled_water_cell = water_template_cell * scale
```

### Density Scaling Mechanism

**File:** `quickice/structure_generation/water_filler.py` (lines 183-213)

Water molecules are scaled to match target density:

```
scale = (template_density / target_density)^(1/3)
```

Where:
- `template_density` = 0.991 g/cm³ (from tip4p.gro template)
- `target_density` = IAPWS-calculated water density

### Impact of Fallback on Models

| Scenario | Impact | Severity |
|----------|--------|----------|
| Normal conditions (T: 250-300 K, P: 0.1-10 MPa) | IAPWS succeeds, no fallback | None |
| Supercooled water (T < 273 K) | IAPWS-95 extrapolates, still accurate | Minimal |
| Extreme T/P outside IAPWS range | Fallback used (0.9998 g/cm³) | Small error in density |
| Invalid input (negative T/P) | Fallback used | Indicates bug elsewhere |

### Quantifying the Error

If fallback is used when it shouldn't be:

**Example:** Water at 298 K, 0.101325 MPa
- IAPWS density: ~0.9970 g/cm³
- Fallback density: 0.9998 g/cm³
- Error: ~0.3% in density

**Impact on molecular spacing:**
- Scale factor error: ~0.1%
- For a 5 nm water layer: ~0.005 nm error

This is **negligible** for most simulations but should be avoided for high-precision work.

---

## Part 5: Exception Context

### When Does IAPWS Fail?

**For Liquid Water (IAPWS-95):**
- Very rare due to extrapolation support
- Fallback mainly triggered by programming errors (negative T/P)

**For Ice Ih (IAPWS R10-06):**
- P > 208.566 MPa (above Ih-III-Liquid triple point)
- T > 273.16 K (above Ih-Liquid-Vapor triple point)

### Current Logging Level

**The code uses `logger.warning()`, NOT `logger.debug()`**

```python
logger.warning(f"Using fallback density for water at T={T_K}K, P={P_MPa}MPa")
```

This is appropriate - users will see warnings in logs if fallback is used.

### Is This Sufficient?

**Yes, for the current implementation:**

1. **Warnings are logged** - Users can check logs to see if fallback was used
2. **Fallback is reasonable** - 0.9998 g/cm³ is physically reasonable for water
3. **IAPWS-95 is robust** - Rarely fails in normal operating range

**Potential improvements:**

1. **Add return indicator** - Function could return `(density, used_fallback: bool)` to allow callers to report to users
2. **Show in UI** - Water density display could show an asterisk or warning if fallback was used
3. **Test coverage** - Add tests for extreme conditions that trigger fallback

---

## Recommendations

### 1. Current Implementation is Adequate

The fallback strategy is sound:
- Fallback values are physically reasonable
- Warnings are logged at appropriate level
- IAPWS-95 is robust for normal operating conditions

### 2. Optional Enhancement: User Visibility

Consider adding a visual indicator in the GUI when fallback is used:

```python
# In water_density.py
def water_density_gcm3(T_K: float, P_MPa: float) -> tuple[float, bool]:
    """Returns (density, used_fallback)"""
    ...

# In gui/view.py
def update_water_density(self, T_K: float, P_MPa: float):
    rho, used_fallback = water_density_gcm3(T_K, P_MPa)
    indicator = " *" if used_fallback else ""
    self.water_density_label.setText(f"Liquid water: {rho:.4f} g/cm³{indicator}")
```

### 3. Document Fallback Behavior

The code already documents this well, but consider adding a note in the user-facing help about fallback behavior for extreme conditions.

### 4. No Action Required for Ice Ih

Ice Ih density fallback (P > 208.566 MPa) is **expected behavior** - Ice Ih is not stable above this pressure, so the fallback is appropriate when users select conditions in other phase regions.

---

## Summary

| Question | Answer |
|----------|--------|
| What is IAPWS? | International standard for water/ice thermodynamic properties |
| Is IAPWS used in 3D model generation? | **Yes, critically** - water layer density is scaled based on IAPWS |
| What happens on IAPWS failure? | Fallback density (0.9998 g/cm³) is used with warning logged |
| Is this a cosmetic issue? | **No** - affects water layer density in generated structures |
| Is the error significant? | Small (~0.3% if fallback incorrectly used) |
| Is logging sufficient? | Yes - uses `logger.warning()`, appropriate level |
| Should exception handling change? | Optional: could add user-visible indicator in GUI |

---

## Files Analyzed

**Core Modules:**
- `quickice/phase_mapping/water_density.py` - Water density calculation
- `quickice/phase_mapping/ice_ih_density.py` - Ice Ih density calculation
- `quickice/structure_generation/water_filler.py` - Water template and density scaling

**Structure Generation:**
- `quickice/structure_generation/modes/slab.py` - Slab interface generation
- `quickice/structure_generation/modes/pocket.py` - Pocket filling
- `quickice/structure_generation/modes/piece.py` - Piece mode

**GUI:**
- `quickice/gui/main_window.py` - Density display
- `quickice/gui/view.py` - Info panel updates

**Tests:**
- `tests/test_water_density.py` - Water density tests
- `tests/test_ice_ih_density.py` - Ice Ih density tests
