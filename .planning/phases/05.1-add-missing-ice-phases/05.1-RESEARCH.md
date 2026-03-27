# Missing Ice Phases Research Context

## Current Implementation

QuickIce currently implements **8 ice phases**:
- Ice Ih (hexagonal, 0.9167 g/cm³)
- Ice Ic (cubic, metastable, 0.92 g/cm³)
- Ice II (rhombohedral, 1.18 g/cm³)
- Ice III (tetragonal, 1.16 g/cm³)
- Ice V (monoclinic, 1.24 g/cm³)
- Ice VI (tetragonal, 1.31 g/cm³)
- Ice VII (cubic, 1.65 g/cm³)
- Ice VIII (ordered VII, 1.65 g/cm³)

**Current temperature range:** 100K - 500K
**Current pressure range:** 0.1 MPa - 10000 MPa (10 GPa)

---

## Missing Low-Temperature Phases (< 150K)

### Ice IX (Proton-ordered Ice III)
- **Formation:** From Ice III at T < 140K
- **Stability:** T < 140K, P = 200-400 MPa
- **Structure:** Tetragonal, antiferroelectric
- **Density:** 1.16 g/cm³
- **Key boundary:** Forms from Ice III cooling, narrow region

### Ice XI (Proton-ordered Ice Ih)
- **Formation:** From Ice Ih at T < 72K
- **Stability:** T < 72K, low pressure
- **Structure:** Orthorhombic, ferroelectric
- **Note:** Most thermodynamically stable form of ice at low T
- **Triple point:** (~72K, ~0 Pa) with Ice Ih and vapor

### Ice XV (Proton-ordered Ice VI)
- **Formation:** From Ice VI at T = 80-108K
- **Stability:** T = 80-108K, P ≈ 1.1 GPa
- **Note:** Requires cooling under pressure

### Ice XIX
- **Formation:** From Ice VIh at T < 100K
- **Stability:** T < 100K, P ≈ 2 GPa
- **Note:** Requires HCl doping

---

## Missing High-Pressure Phases (> 30 GPa)

### Ice X (Symmetrized Hydrogen Bonds)
- **Formation:** From Ice VII at P > 30 GPa
- **Stability:** P = 30-70 GPa, T > 165K
- **Structure:** Cubic, symmetric H bonds (O centered between H)
- **Density:** 2.79 g/cm³
- **Key feature:** Hydrogen bonds become symmetric

### Ice XVIII / Ice XX (Superionic Water)
- **Formation:** Ice VII at extreme conditions
- **Stability:** P = 20-60 GPa, T = 900-1800K
- **Structure:** Oxygen lattice + mobile hydrogen ions
- **Note:** Superionic phase, not molecular

---

## Research Sources

1. **Wikipedia Phases of Ice:** https://en.wikipedia.org/wiki/Phases_of_ice
2. **LSBU Water Phase Data:** https://ergodic.ugr.es/termo/lecciones/water1.html
3. **GenIce2 Library:** https://pypi.org/project/genice2/
4. **IAPWS Library:** https://pypi.org/project/iapws/

---

## Implementation Gaps

### Phase 2 (Phase Mapping)
1. **Triple points needed:**
   - Ih-XI-Vapor triple point (~72K, ~0 Pa)
   - IX boundaries from III cooling
   - XV boundaries from VI cooling

2. **Boundary curves needed:**
   - Ice IX stability region (narrow, T<140K, P=200-400 MPa)
   - Ice XI stability region (T<72K, low P)
   - Ice X transition (P>30 GPa)

3. **Phase lookup modifications:**
   - Detect Ice XI at T<72K, low P (ordered Ih)
   - Detect Ice IX at T<140K, P=200-400 MPa (ordered III)
   - Detect Ice X at P>30 GPa (symmetrized)

### Phase 5 (Phase Diagram)
1. **Extend temperature range:** Consider showing down to 50K for Ice XI
2. **Extend pressure range:** Consider showing up to 100 GPa for Ice X
3. **Add new phase regions:**
   - Ice XI (small region at bottom-left, T<72K)
   - Ice IX (small region near Ice III)
   - Ice X (region above Ice VII/VIII at P>30 GPa)

---

## Priority Assessment

### High Priority (Common in nature/research)
- **Ice XI:** Most stable form at low T, relevant for astrophysics
- **Ice IX:** Narrow but distinct stability region

### Medium Priority (Specialized conditions)
- **Ice X:** Extreme pressure physics, planetary interiors
- **Ice XV:** Proton-ordered VI, specialized research

### Low Priority (Very specialized)
- **Ice XIX, XIV:** Require doping, rare conditions
- **Ice XVIII/XX:** Superionic, extreme conditions

---

## Data Requirements for Implementation

For each missing phase, need:
1. Triple point coordinates (T, P)
2. Boundary curves (equations or interpolation points)
3. Density values
4. Crystal structure info (for GenIce template mapping)

**Key data gaps:**
- Ice XI boundaries are poorly defined (gradual transition from Ih)
- Ice X transition pressure varies with temperature
- Ice IX has narrow, well-defined region but limited IAPWS data

---

## Suggested Implementation Order

1. **Ice XI** - Simplest: just T<72K at low P (replaces Ih at very low T)
2. **Ice IX** - Well-defined: narrow region near Ice III
3. **Ice X** - Important for high-P: extend diagram to 100 GPa
4. **Ice XV** - Moderate: ordered VI variant

---

*Generated: 2026-03-27*
*For: Phase 2/5 enhancement planning*
