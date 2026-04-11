# Phase 22: Ice Ih IAPWS Density - Research

**Researched:** 2026-04-12
**Domain:** Thermodynamic property calculation (IAPWS R10-06(2009) Ice Ih equation of state)
**Confidence:** HIGH
**Revised:** 2026-04-12 — Corrected: iapws._iapws._Ice DOES implement Ice Ih EOS (initial research incorrectly stated it was not importable)

## Summary

The goal is to replace the hardcoded Ice Ih density (0.9167 g/cm³) with a temperature-dependent IAPWS R10-06(2009) calculation. **The existing `iapws` library (v1.5.5) already implements IAPWS R10-06(2009) Ice Ih equation of state** via `iapws._iapws._Ice(T, P)`. No new dependencies are needed.

The `iapws._iapws._Ice(T, P)` function:
- Accepts temperature in **Kelvin** and pressure in **MPa** (same units as our codebase — no conversion needed!)
- Returns a dict with `rho` in kg/m³ (divide by 1000 → g/cm³)
- Implements the full IAPWS R10-06(2009) Gibbs energy formulation
- Valid range: T ≤ 273.16K, P ≤ 208.566 MPa
- Raises `NotImplementedError("Incoming out of bound")` for P > 208.566 MPa
- Issues `warnings.warn` for metastable conditions (T > 273.16K or below sublimation line)

**Primary recommendation:** Use `iapws._iapws._Ice(T, P)` for Ice Ih density. Create a thin wrapper in `quickice/phase_mapping/` that handles fallback and caching. No new dependencies required.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| iapws | 1.5.5 | IAPWS R10-06(2009) Ice Ih density | Already in environment.yml, implements IAPWS R10-06(2009) directly |

### No New Dependencies
`iapws` is already in `environment.yml` (pip section: `iapws==1.5.5`). No new packages needed.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| iapws._iapws._Ice() | gsw.rho_ice() | gsw is NOT in environment.yml, would be a NEW dependency; requires °C/dbar unit conversion; no advantage since iapws already has Ice Ih EOS |
| iapws._iapws._Ice() | Custom IAPWS R10-06(2009) implementation | Custom is error-prone (23+ coefficient Gibbs equation); iapws already implements it |
| iapws._iapws._Ice() | iapws.IAPWS97 | IAPWS97 only covers FLUID water, fails below 273.15K; _Ice is specifically for solid Ice Ih |

## Architecture Patterns

### Recommended Project Structure
```
quickice/phase_mapping/
├── lookup.py              # Modify _build_result() to use Ice Ih density calculator
├── ice_ih_density.py      # NEW: Ice Ih density calculation wrapper
├── melting_curves.py       # Existing
├── solid_boundaries.py     # Existing
└── triple_points.py        # Existing
```

### Pattern 1: Density Calculator Wrapper
**What:** Thin wrapper around `iapws._iapws._Ice()` that handles validation, caching, and fallback.
**When to use:** Every time Ice Ih density is needed (replaces hardcoded 0.9167).
**Example:**
```python
# Source: IAPWS R10-06(2009) via iapws library
from functools import lru_cache
from iapws._iapws import _Ice

FALLBACK_DENSITY_GCM3 = 0.9167  # g/cm³ at 273.15K, 1 atm


@lru_cache(maxsize=256)
def ice_ih_density_kgm3(T_K: float, P_MPa: float) -> float:
    """Calculate Ice Ih density using IAPWS R10-06(2009).
    
    Args:
        T_K: Temperature in Kelvin
        P_MPa: Pressure in MPa
    
    Returns:
        Density in kg/m³
    """
    try:
        result = _Ice(T=T_K, P=P_MPa)
        return float(result["rho"])
    except (NotImplementedError, ValueError, OverflowError):
        return FALLBACK_DENSITY_GCM3 * 1000  # Convert fallback to kg/m³


def ice_ih_density_gcm3(T_K: float, P_MPa: float) -> float:
    """Calculate Ice Ih density in g/cm³ (QuickIce standard units).
    
    Args:
        T_K: Temperature in Kelvin
        P_MPa: Pressure in MPa
    
    Returns:
        Density in g/cm³
    """
    return ice_ih_density_kgm3(T_K, P_MPa) / 1000.0
```

### Pattern 2: Conditional Density in _build_result
**What:** `_build_result()` calls the IAPWS calculator only for Ice Ih, uses PHASE_METADATA for all other phases.
**When to use:** In `lookup_phase()` and `_build_result()`.
**Example:**
```python
def _build_result(phase_id: str, T: float, P: float) -> dict:
    """Build result dictionary for a matched phase."""
    meta = PHASE_METADATA[phase_id]
    
    # Use IAPWS R10-06(2009) for Ice Ih density (temperature-dependent)
    if phase_id == "ice_ih":
        from quickice.phase_mapping.ice_ih_density import ice_ih_density_gcm3
        density = ice_ih_density_gcm3(T, P)
    else:
        density = meta["density"]
    
    return {
        "phase_id": phase_id,
        "phase_name": meta["name"],
        "density": density,
        "temperature": T,
        "pressure": P,
    }
```

### Anti-Patterns to Avoid
- **Don't use IAPWS97 for ice:** `iapws.IAPWS97` only covers fluid water, fails with `NotImplementedError: Incoming out of bound` for T < 273.15K.
- **Don't implement the Gibbs equation manually:** The IAPWS R10-06(2009) equation has 23+ coefficients; iapws._iapws._Ice already implements it.
- **Don't call iapws._Ice at P > 208.566 MPa:** Raises `NotImplementedError("Incoming out of bound")`. The Ih-III-Liquid triple point is at 209.9 MPa, so near-boundary conditions may fail. Use fallback.
- **Don't add gsw as a new dependency:** iapws already provides Ice Ih density. No need for a new library.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ice Ih density vs T,P | Custom IAPWS Gibbs energy implementation | `iapws._iapws._Ice(T, P)` | Already implemented in installed library |
| Density caching | Manual dict cache | `@lru_cache(maxsize=256)` | Thread-safe, bounded, built-in |
| Fallback handling | Scattered try/except at every call site | Centralized wrapper function | Single source of truth for fallback logic |

## Common Pitfalls

### Pitfall 1: iapws._Ice Raises NotImplementedError for High Pressure
**What goes wrong:** Calling `_Ice(T, P)` with P > 208.566 MPa raises `NotImplementedError("Incoming out of bound")`.
**Why it happens:** IAPWS R10-06(2009) is only valid for P ≤ 208.566 MPa. The Ih-III-Liquid triple point is at 209.9 MPa.
**How to avoid:** Catch `NotImplementedError` in the wrapper and return fallback density 0.9167 g/cm³.
**Warning signs:** Crashes when user clicks near the Ih-III boundary.

### Pitfall 2: iapws._Ice Metastable Warnings
**What goes wrong:** `_Ice(T, P)` issues `UserWarning` for metastable conditions (T > 273.16K or below sublimation line).
**Why it happens:** The function warns when ice is outside its thermodynamically stable region.
**How to avoid:** The wrapper should suppress these warnings with `warnings.filterwarnings("ignore")` or the caller should handle them. Since our phase mapping already ensures only Ice Ih conditions reach this function, warnings should be rare.
**Warning signs:** Warning messages printed to console during normal use.

### Pitfall 3: Test Failures from Hardcoded 0.9167
**What goes wrong:** Existing tests assert `result["density"] == 0.9167` exactly. After switching to IAPWS, density at 273K is 0.91718, not 0.9167.
**Why it happens:** The hardcoded 0.9167 was the density at 273.15K (0°C) at 1 atm, but tests use 273K which gives a slightly different value.
**How to avoid:** Update tests to check approximate density values with `pytest.approx()` or check that density is in the expected range (0.91-0.94 g/cm³ for Ice Ih).
**Warning signs:** Tests failing with `AssertionError: 0.91718 != 0.9167`.

### Pitfall 4: Density Display Precision Mismatch
**What goes wrong:** IAPWS-calculated density has 5-6 decimal places (e.g., 0.91672), but the UI was showing 4 decimals (0.9167).
**Why it happens:** The hardcoded value had limited precision; IAPWS provides more.
**How to avoid:** Format to 4 decimal places for display: `f"{density:.4f}"`. This matches the existing display style while still using the accurate calculated value internally.
**Warning signs:** UI showing long decimals like "0.9167218 g/cm³" instead of "0.9167 g/cm³".

## Code Examples

### Ice Ih Density Calculation (Core)
```python
# Source: IAPWS R10-06(2009) via iapws library
# https://www.iapws.org/release/Ice-2009.html
from iapws._iapws import _Ice

def ice_ih_density(T_K: float, P_MPa: float) -> float:
    """Calculate Ice Ih density using IAPWS R10-06(2009) equation of state.
    
    Args:
        T_K: Temperature in Kelvin (valid: 0-273.16 K)
        P_MPa: Pressure in MPa (valid: 0-208.566 MPa)
    
    Returns:
        Density in g/cm³
    """
    result = _Ice(T=T_K, P=P_MPa)
    # iapws returns kg/m³, convert to g/cm³
    return result["rho"] / 1000.0
```

### Validated Test Values
```python
# Source: Verified against iapws 1.5.5 _Ice() on 2026-04-12
# These values can be used as test reference values

# At 1 atm (0.101325 MPa):
REFERENCE_DENSITIES = {
    # (T_K, P_MPa): density_gcm3
    (100, 0.101325): 0.93305,
    (150, 0.101325): 0.93061,
    (200, 0.101325): 0.92613,
    (250, 0.101325): 0.92000,
    (270, 0.101325): 0.91718,
    (273.15, 0.101325): 0.91672,
}

# At 200 MPa (within valid range P ≤ 208.566):
(251, 200): 0.93983,
(273.15, 200): 0.93737,
```

### Modified _build_result
```python
def _build_result(phase_id: str, T: float, P: float) -> dict:
    """Build result dictionary for a matched phase."""
    meta = PHASE_METADATA[phase_id]
    
    # Ice Ih: use IAPWS R10-06(2009) temperature-dependent density
    if phase_id == "ice_ih":
        from quickice.phase_mapping.ice_ih_density import ice_ih_density_gcm3
        density = ice_ih_density_gcm3(T, P)
    else:
        density = meta["density"]
    
    return {
        "phase_id": phase_id,
        "phase_name": meta["name"],
        "density": density,
        "temperature": T,
        "pressure": P,
    }
```

### Modified GUI Display (main_window.py)
```python
# Current (line 762-778):
# density = meta.get("density", "Unknown")
# 
# After change: density already comes from lookup_phase result,
# which now uses IAPWS for Ice Ih. No change needed in GUI display code
# IF the density_note is updated to remove the "reference conditions" caveat.
```

### Updated density_note for PHASE_METADATA
```python
"ice_ih": {
    "name": "Ice Ih",
    "density": 0.9167,  # Fallback value only; actual density calculated via IAPWS
    "density_note": "Only Ice Ih has temperature-dependent density. Others use fixed values."
},
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded 0.9167 g/cm³ | IAPWS R10-06(2009) via iapws._iapws._Ice() | Phase 22 (this phase) | Density now varies with T,P; ~1.78% variation across Ice Ih range |
| gsw.rho_ice() (incorrect research) | iapws._iapws._Ice() | Research correction | No new dependency needed; no unit conversion needed |

## Sources

### Primary (HIGH confidence)
- iapws 1.5.5 installed and tested — `_Ice(T, P)` verified against known IAPWS values
- IAPWS R10-06(2009) official page: https://www.iapws.org/release/Ice-2009.html
- iapws._iapws._Ice docstring: "Basic state equation for Ice Ih... IAPWS, Revised Release on the Equation of State 2006 for H2O Ice Ih"

### Secondary (MEDIUM confidence)
- iapws._iapws._Ice source code: Validated range checks (T ≤ 273.16, P ≤ 208.566 MPa)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — iapws already installed, already implements IAPWS R10-06(2009) for Ice Ih
- Architecture: HIGH — Straightforward wrapper pattern; NO unit conversion needed (K and MPa match codebase)
- Pitfalls: HIGH — Edge cases tested (P > 208.566 → NotImplementedError, metastable warnings)

**Research date:** 2026-04-12
**Valid until:** 2027-04-12 (stable: IAPWS standard is unlikely to change; iapws is mature)
