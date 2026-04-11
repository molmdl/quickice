# Feature Landscape: QuickIce v3.5 Interface Enhancements

**Domain:** Molecular dynamics ice structure generation with interface construction
**Researched:** April 2026
**Confidence:** HIGH (direct codebase analysis + domain knowledge)

---

## Executive Summary

This document maps the four new features for v3.5 Interface Enhancements:
1. Triclinic→orthogonal transformation
2. CLI interface generation  
3. Water density calculation from T/P
4. Ice Ih density from IAPWS

Features are categorized as:
- **Table Stakes** — Must have for product completeness
- **Differentiators** — Competitive advantage
- **Anti-Features** — Deliberately NOT built

---

## Table Stakes

Features users expect. Missing = product feels incomplete.

### Feature 1: Triclinic→Orthogonal Transformation

| Aspect | Detail |
|--------|--------|
| **What** | Transform GenIce2's triclinic unit cells to orthogonal (rectangular) cells |
| **Why Expected** | GenIce2 produces triclinic cells for most ice phases (Ice II, V, VI, VII). QuickIce v3.0 rejects these with error. Interface generation requires orthogonal boxes. |
| **Complexity** | Medium-High |
| **Dependencies** | Existing `is_cell_orthogonal()` function in `interface_builder.py` (lines 25-40) |
| **Current State** | Code already detects triclinic cells and raises `InterfaceGenerationError` (lines 119-130) |

**Implementation Requirements:**
- Compute transformation matrix from triclinic to orthogonal cell
- Preserve crystallographic structure during transformation
- Handle atom positions correctly (wrap to new cell bounds)
- Common approach: Use cell's lattice vectors to compute equivalent orthogonal box that preserves volume

**Algorithm approach:**
```python
# Triclinic cell: cell matrix with off-diagonal elements
# Orthogonal cell: only diagonal elements non-zero
# Transformation preserves volume: det(orthogonal) ≈ det(triclinic)
# Common method: Compute conventional cell via Niggli reduction or similar
```

**Validation:**
- Test with Ice II (known triclinic), Ice V (monoclinic), Ice VI (tetragonal)
- Verify output cell is orthogonal: `np.allclose(off_diagonal, 0)`
- Verify atom positions are preserved within tolerance

---

### Feature 2: CLI Interface Generation

| Aspect | Detail |
|--------|--------|
| **What** | Add `--interface` flag to CLI with mode/thickness/seed parameters |
| **Why Expected** | Full CLI parity with GUI. Users expect command-line access to all features. |
| **Complexity** | Low-Medium |
| **Dependencies** | Existing `InterfaceConfig`, `generate_interface()` in `interface_builder.py` |
| **Current State** | CLI documented as GUI-only (see `docs/cli-reference.md` line 5) |

**Implementation Requirements:**

Existing CLI parser structure (`quickice/cli/parser.py`):
- Add `--interface` flag with sub-options
- Mode selection: `--interface-mode {slab,pocket,piece}`
- Mode-specific parameters:
  - Slab: `--ice-thickness`, `--water-thickness`
  - Pocket: `--pocket-diameter`, `--pocket-shape`
  - Piece: (no extra params - derived from candidate)
- Box dimensions: `--box-x`, `--box-y`, `--box-z`
- Random seed: `--seed`
- Candidate selection: `--candidate` (already exists)

**Proposed CLI syntax:**
```bash
# Slab interface
python quickice.py -T 260 -P 0.1 -N 100 --interface --interface-mode slab \
  --ice-thickness 3.0 --water-thickness 4.0 --box-x 5.0 --box-y 5.0 --box-z 10.0

# Pocket interface  
python quickice.py -T 260 -P 0.1 -N 100 --interface --interface-mode pocket \
  --pocket-diameter 2.0 --pocket-shape sphere --box-x 5.0 --box-y 5.0 --box-z 5.0

# Piece interface
python quickice.py -T 260 -P 0.1 -N 100 --interface --interface-mode piece \
  --box-x 6.0 --box-y 6.0 --box-z 6.0 --candidate 1
```

**Key differences from GUI:**
- No 3D visualization (text output only)
- Must output GROMACS files for interface structure
- Candidate selection via `--candidate` flag

---

### Feature 3: Water Density from Thermodynamic Conditions

| Aspect | Detail |
|--------|--------|
| **What** | Calculate liquid water density (ρ) from temperature and pressure using IAPWS |
| **Why Expected** | Interface generation needs correct water molecule spacing. Current approach uses static TIP4P template without accounting for T/P effects. |
| **Complexity** | Low |
| **Dependencies** | `iapws` library already installed (v1.5.5 in `environment.yml`) |
| **Current State** | Used in phase diagram widget for vapor boundary (see `phase_diagram_widget.py` lines 61-90) |

**Implementation Requirements:**

Use `IAPWS97` class from `iapws` library:
```python
from iapws import IAPWS97

# For liquid water at given T, P
st = IAPWS97(T=temperature_K, P=pressure_MPa)  # x not specified = liquid
water_density = st.rho  # kg/m³, convert to g/cm³
```

**Usage scenarios:**
1. **Display in UI**: Show calculated water density alongside ice density
2. **Internal calculation**: Use density to estimate molecule count for given volume
   - `n_molecules = (volume_nm³ * 1e-21) * (density_g_cm3 / 18.015) * NA`
3. **Validation**: Verify water layer has expected density

**IAPWS97 capabilities:**
- Temperature range: 273.16 K to 647.096 K (critical point)
- Pressure range: 0.1 MPa to 100 MPa (liquid region)
- Returns: density (kg/m³), enthalpy, entropy, etc.

**Error handling:**
- Above critical point: IAPWS97 returns error for two-phase region
- Below freezing: May return ice properties instead of liquid
- Graceful fallback to reference density (~1.0 g/cm³) if calculation fails

---

## Differentiators

Features that set product apart. Not expected, but valued.

### Feature 4: Ice Ih Density from IAPWS

| Aspect | Detail |
|--------|--------|
| **What** | Replace hardcoded Ice Ih density (0.9167 g/cm³) with temperature-dependent IAPWS calculation |
| **Why Expected** | IAPWS provides scientifically accurate equation of state. Hardcoded value is only valid at 273.15 K, 0.101325 MPa. |
| **Complexity** | Low |
| **Dependencies** | `iapws` library; existing `PHASE_METADATA` in `lookup.py` |
| **Current State** | Hardcoded in `lookup.py` line 30: `"density": 0.9167` |

**Implementation Requirements:**

IAPWS provides Ice Ih equation of state via `IAPWS97` with `x=1` (solid):
```python
from iapws import IAPWS97

# For Ice Ih at given T, P
st = IAPWS97(T=temperature_K, P=pressure_MPa, x=1)  # x=1 for solid
ice_ih_density = st.rho  # kg/m³ → g/cm³
```

**Benefits:**
- Accurate across full T range (50-273 K)
- Accounts for pressure dependence
- Matches IAPWS R10-06(2009) standard

**Current vs. IAPWS comparison:**
| Temperature | Current (hardcoded) | IAPWS |
|-------------|---------------------|-------|
| 100 K | 0.9167 | ~0.93 |
| 200 K | 0.9167 | ~0.92 |
| 273 K | 0.9167 | ~0.917 |

**Fallback:**
- If IAPWS calculation fails (out of range), use hardcoded value
- Store reference to IAPWS R10-06 in documentation

---

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain.

### Anti-Feature 1: Real-time MD Simulation

| Anti-Pattern | Why Avoid | What To Do Instead |
|--------------|-----------|-------------------|
| Running actual molecular dynamics simulation | Outside scope; requires GROMACS/AMBER installed; computationally expensive | Generate initial structures only, let users run their own MD |

**QuickIce scope:** Structure generation, not simulation.

---

### Anti-Feature 2: Automatic Unit Conversion Without User Control

| Anti-Pattern | Why Avoid | What To Do Instead |
|--------------|-----------|-------------------|
| Auto-converting between nm/Å/Åström without explicit units | Causes confusion; scientific errors | Always use explicit units (nm in output files, documented clearly) |

**QuickIce output:** GROMACS .gro files use nanometers. Make this explicit.

---

### Anti-Feature 3: Triclinic Support Without Transformation

| Anti-Pattern | Why Avoid | What To Do Instead |
|--------------|-----------|-------------------|
| Supporting triclinic cells directly in interface generation | Complex; many MD codes have issues with non-orthogonal boxes | Always transform to orthogonal; document this limitation |

**Current behavior:** Rejects triclinic with error. **v3.5:** Transform and continue.

---

## Feature Dependencies

```
┌─────────────────────────────────────────────────────────────────┐
│                    Feature Dependency Graph                      │
└─────────────────────────────────────────────────────────────────┘

[Ice Generation] ──► [Triclinic→Orthogonal] ──► [Interface Generation]
       │                                                │
       │                                                ▼
       │                                       ┌──────────────────┐
       │                                       │ CLI Interface    │
       │                                       │ Generation       │
       │                                       └──────────────────┘
       │
       ▼
[Phase Lookup] ◄──── [Ice Ih IAPWS Density]
       │
       ▼
[Water Density from T/P] ──► [Interface Generation - Water Layer]
```

**Dependency explanation:**
1. **Triclinic→orthogonal** must happen BEFORE interface generation for affected phases
2. **Ice Ih density** is a drop-in replacement in phase lookup (no downstream changes needed)
3. **Water density** can be computed independently but feeds into interface generation
4. **CLI interface generation** builds on existing CLI + interface generation modules

---

## MVP Recommendation

For v3.5, prioritize in this order:

### Phase 1 (Must Have)
1. **Triclinic→orthogonal transformation** — Unblocks interface generation for Ice II, V, VI
2. **CLI interface generation** — Full CLI parity, high user demand

### Phase 2 (Should Have)
3. **Water density from T/P** — Useful for display and internal calculations
4. **Ice Ih IAPWS density** — Scientific accuracy improvement, low risk

### Post-v3.5 (Consider Later)
- Support for more ice phases (currently 8 supported by GenIce2)
- Automated interface geometry optimization
- Integration with GROMACS gmx solvate for alternative water filling

---

## Complexity Assessment

| Feature | Complexity | Risk | Estimate |
|---------|------------|------|----------|
| Triclinic→orthogonal | Medium-High | Medium | 2-3 sprints |
| CLI interface generation | Low-Medium | Low | 1-2 sprints |
| Water density from T/P | Low | Low | 0.5-1 sprint |
| Ice Ih IAPWS density | Low | Low | 0.5 sprint |

---

## References

- **IAPWS97 Python library:** `pip install iapws==1.5.5` (already in environment)
- **IAPWS R10-06(2009):** Equation of State for Ice Ih — https://www.iapws.org/release/Ice-2009.html
- **IAPWS R14-08(2011):** Melting curves — https://www.iapws.org/release/MeltIce.pdf
- **GROMACS documentation:** https://manual.gromacs.org/
- **GenIce2:** https://github.com/vitroid/GenIce2 (MIT licensed)
- **Current CLI reference:** `docs/cli-reference.md`
- **Interface builder:** `quickice/structure_generation/interface_builder.py`
- **Phase lookup:** `quickice/phase_mapping/lookup.py`

---

*Research for: QuickIce v3.5 Interface Enhancements*
*Generated: 2026-04-12*