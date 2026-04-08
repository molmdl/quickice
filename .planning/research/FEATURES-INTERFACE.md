# Feature Landscape: Ice-Water Interface Generation

**Domain:** Scientific GUI application — Ice-water interface structure generation
**Researched:** 2026-04-08
**Confidence:** MEDIUM-HIGH

---

## Executive Summary

This document categorizes features for the QuickIce v3.0 milestone: ice-water interface generation with three geometry modes (slab, ice-in-water, water-in-ice). Based on research into computational chemistry approaches, existing GenIce2 capabilities, and the current QuickIce architecture, this analysis identifies table stakes features essential for functional interface generation, differentiators that add competitive value, and anti-features to avoid.

Key findings:
- **GenIce2 does not support liquid water or interfaces** — Must build interface generation as a layer on top of existing ice generation
- **Three geometry modes require different assembly algorithms** — Slab (layer stacking), ice-in-water (particle embedding), water-in-ice (cavity/carving)
- **Existing VTK viewer can handle phase differentiation** — Minor enhancements needed for ice vs. liquid coloring
- **New controls: boxsize, mode selector, seed, ice_thickness, water_thickness** — Replace nmolecules with thickness-based sizing

---

## Table Stakes (Must Have)

Features users expect in any interface generation tool. Missing these makes the product feel incomplete or unusable.

### Interface Configuration Controls

| Feature | Why Expected | Complexity | Notes | Dependency |
|---------|--------------|------------|-------|------------|
| Mode selector (slab/ice-in-water/water-in-ice) | Core differentiator for this milestone | LOW | Dropdown or radio buttons, 3 options | None (new) |
| Box size input (nm) | Controls simulation box dimensions | LOW | Numeric input, default ~3.0 nm | None (new) |
| Ice thickness input (nm) | Controls solid layer size in slab mode | LOW | Numeric input, range 0.5-5.0 nm | None (new) |
| Water thickness input (nm) | Controls liquid layer size in slab mode | LOW | Numeric input, range 0.5-5.0 nm | None (new) |
| Seed input | Reproducibility for random elements | LOW | Integer, default 1000 | None (new) |
| Phase selector | Which ice polymorph for solid phase | LOW | Dropdown (Ih, Ic, II-VI, etc.) | Existing phase diagram |
| Generate button | Primary action to create interface | LOW | Triggers interface assembly | All inputs |

### Interface Structure Generation

| Feature | Why Expected | Complexity | Notes | Dependency |
|---------|--------------|------------|-------|------------|
| Slab assembly (ice layer + water layer) | Standard sandwich geometry | MEDIUM | Stack ice slab with liquid layer, handle density transition | GenIce2 (ice), liquid generator (new) |
| Ice-in-water assembly (embedded crystal) | Particle embedding geometry | MEDIUM-HIGH | Place ice crystal in water box, handle boundary conditions | GenIce2, liquid generator |
| Water-in-ice assembly (cavity in ice) | Inverse embedding geometry | MEDIUM-HIGH | Create cavity/carving in ice matrix, fill with water | GenIce2, liquid generator |
| Liquid water generation | Non-crystalline water configuration | MEDIUM | Generate disordered water positions at realistic density | None (new algorithm) |
| Periodic boundary handling | Ensure continuous simulation box | MEDIUM | Proper wrapping at box edges for MD compatibility | None (new) |

### Visualization

| Feature | Why Expected | Complexity | Notes | Dependency |
|---------|--------------|------------|-------|------------|
| Phase differentiation coloring | Distinguish ice vs. liquid regions | LOW | Ice = blue/cyan, liquid = lighter/different hue | Existing VTK viewer |
| 3D viewport display | Show generated interface | LOW | Reuse existing VTK molecular viewer | Existing viewer |
| Ball-and-stick representation | Standard molecular visualization | LOW | Existing representation modes | Existing viewer |
| Unit cell boundary | Show simulation box | LOW | Toggle existing cell boundary | Existing toggle |

### Export

| Feature | Why Expected | Complexity | Notes | Dependency |
|---------|--------------|------------|-------|------------|
| PDB export | Standard structure format | LOW | Export combined ice-water coordinates | Existing PDB writer |
| GROMACS export (.gro) | MD simulation input | LOW | Export interface in GROMACS format | Existing GRO writer |
| GROMACS export (.top/.itp) | Topology for simulation | LOW | Include both phases in topology | Existing GRO writer |
| PNG/SVG export | Visualization capture | LOW | Screenshot of 3D viewport | Existing export |

---

## Differentiators (Competitive Advantage)

Features that set QuickIce apart from competitors or add significant user value beyond basic expectations.

### Advanced Interface Controls

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Ice crystal size control (ice-in-water mode) | Control embedding crystal size | MEDIUM | Number of molecules or unit cells |
| Cavity size control (water-in-ice mode) | Control water pocket size | MEDIUM | Diameter or molecule count |
| Interface orientation control | Scientific flexibility for crystal face | MEDIUM-HIGH | [001], [100], [110] for Ih |
| Automatic density matching | Physically reasonable interfaces | MEDIUM | Match ice/liquid densities at interface |

### Enhanced Visualization

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Interface boundary plane | Visual indicator of transition | LOW | Dashed line or plane at interface |
| Phase legend | Clarity on colors | LOW | Color key for ice vs. liquid |
| Atom count display | Show molecule distribution | LOW | Display ice N, water N separately |
| Hydrogen bond network | Show connectivity in both phases | MEDIUM | May show different patterns in liquid |

### Information & Education

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Interface info panel | Scientific context | LOW | Show interface type, dimensions, phase info |
| Density calculation display | Show calculated densities | LOW | Ice density vs. water density |
| Generation parameters summary | Reproducibility aid | LOW | List all parameters used |

### User Experience

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Dual viewport (ice alone / interface) | Compare before/after | MEDIUM | Existing dual viewport can reuse |
| Quick presets | Common configurations | LOW | Ih-slab-3nm, Ic-in-water, etc. |
| Dimension preview | Before generation | LOW | Show expected box size |

---

## Anti-Features (Do NOT Build)

Features commonly requested but problematic for this domain. Documented to prevent scope creep and ensure focused development.

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Real-time interface preview | "Modern" UX expectation | Interface generation is computationally non-trivial, would freeze UI | Generate button is appropriate |
| In-app MD simulation | Comprehensive tool | Outside project scope (generation only), requires GROMACS/OpenMM | Export for external MD |
| Automatic interface optimization | Physically perfect interfaces | Requires energy minimization, new dependencies | Keep simple generation |
| Multiple interface types beyond 3 modes | Flexibility | Complicates UI, modes cover most use cases | Stick to slab/ice-in/water-in |
| Melting curve calculation | Scientific depth | Would require external data or complex thermodynamics | Document as out of scope |
| Temperature-dependent interface width | Physical accuracy | Requires MD simulation to determine | Use fixed reasonable defaults |
| Surface energy calculation | Research metric | Requires MD simulation | Export structure for external analysis |
| Guest molecule inclusion in interface | Advanced users | Interface with guests is complex | Keep pure water-ice only |

---

## Feature Dependencies

### Interface Generation Pipeline

```
User Input (mode, boxsize, thickness, phase, seed)
         │
         ▼
Input Validation ──────► Error Display
         │
         ▼
Phase Selection (ice polymorph)
         │
         ▼
Ice Generation (GenIce2)
         │
         ▼
Liquid Generation (new algorithm)
         │
         ▼
Interface Assembly (mode-specific)
         │
         ▼
Periodic Boundary Handling
         │
         ▼
Combined Structure + Display
```

### Mode-Specific Assembly

**Slab Mode:**
```
Ice slab (generated) + Liquid slab (generated)
         │
         ▼
Stack: [ice layer][water layer]
         │
         ▼
Smooth interface region (optional)
```

**Ice-in-Water Mode:**
```
Water box (generated) + Ice crystal (generated)
         │
         ▼
Place ice at center of water box
         │
         ▼
Handle boundary conditions (wrap or pad)
```

**Water-in-Ice Mode:**
```
Ice matrix (generated) + Water cavity (computed)
         │
         ▼
Create spherical/elliptical cavity in ice
         │
         ▼
Fill cavity with liquid water molecules
```

### Key Dependency Notes

1. **GenIce2 used for solid phase only** — Cannot generate liquid, must create separate algorithm
2. **Mode selector determines assembly algorithm** — Each mode has different geometric requirements
3. **Thickness → molecule count conversion** — Must calculate based on ice density and box area
4. **VTK viewer needs phase identification** — Add flag to distinguish ice vs. liquid atoms
5. **Export must handle mixed phases** — GROMACS topology includes both ice and water

---

## MVP Recommendation

For v3.0 initial release, prioritize:

### Phase 1 (MVP - Must Have)

1. Mode selector (slab/ice-in-water/water-in-ice)
2. Box size input (nm)
3. Ice thickness input (nm) — applies to slab mode
4. Water thickness input (nm) — applies to slab mode
5. Seed input for reproducibility
6. Phase selector (Ih default)
7. Generate button with slab mode implementation
8. Basic 3D display with phase coloring
9. PDB and GROMACS export

### Phase 2 (Enhanced Experience)

1. Ice-in-water mode implementation
2. Water-in-ice mode implementation
3. Interface boundary visualization
4. Phase legend in UI
5. Quick presets for common configurations

### Phase 3 (Differentiation)

1. Cavity size control (water-in-ice)
2. Crystal size control (ice-in-water)
3. Interface orientation (advanced)
4. Dual viewport comparison
5. Density calculation display

---

## Technical Implementation Notes

### Liquid Water Generation Approaches

| Approach | Complexity | Scientific Validity | Notes |
|----------|------------|---------------------|-------|
| Random placement with density | LOW | Low | Simple, fast, but unrealistic |
| Grid-based with noise | LOW-MEDIUM | Low-Medium | Better ordering, still artificial |
| Pre-generated equilibrium configuration | MEDIUM | MEDIUM-HIGH | Use bundled TIP4P.gro as template |
| MD-relaxed configuration | HIGH | HIGH | Requires GROMACS, too complex for MVP |

**Recommendation:** Use grid-based placement with random orientation noise for MVP. This provides:
- Realistic density (~1.0 g/cm³)
- Disordered orientations (liquid-like)
- No external dependencies
- Fast generation (seconds)

### Box Size Calculations

```
Slab Mode:
- Box area = boxsize² (assuming square XY)
- Ice molecules = (ice_thickness × box_area × ice_density) / water_molecule_mass
- Water molecules = (water_thickness × box_area × water_density) / water_molecule_mass

Ice-in-Water Mode:
- Box volume = boxsize³
- Total water molecules = (box_volume × water_density) / water_molecule_mass
- Ice crystal = generated from GenIce2, placed at center

Water-in-Ice Mode:
- Box volume = boxsize³
- Ice molecules = generated to fill box minus cavity
- Cavity water = fill spherical cavity with water molecules
```

### Density Values (TIP4P-ICE)

| Phase | Density (g/cm³) | Notes |
|-------|-----------------|-------|
| Ice Ih | 0.92 | At 273 K, 1 atm |
| Ice Ic | ~0.93 | Similar to Ih |
| Ice II | 1.18 | High pressure |
| Ice III | 1.16 | High pressure |
| Ice V | 1.24 | High pressure |
| Ice VI | 1.31 | High pressure |
| Liquid water | 1.00 | At 273 K |

---

## Research Sources

### Verified Sources (HIGH Confidence)

1. **GenIce2 GitHub repository** — Confirmed ice-only generation, no liquid support
   - https://github.com/genice-dev/GenIce2

2. **GenIce2 architecture** — Seven-stage pipeline for ice generation
   - Cell repetition → Graph → Ice rules → Depolarize → Orient → Place atoms → Guests

3. **QuickIce existing code** — Current implementation patterns
   - Structure generation in `quickice/structure_generation/`
   - VTK viewer in `quickice/gui/molecular_viewer.py`
   - Export in `quickice/output/`

### Domain Knowledge (MEDIUM Confidence)

4. **Ice phase properties** — Densities from IAPWS and literature
   - Ice Ih: 0.92 g/cm³
   - Liquid water: 1.00 g/cm³ (at freezing)
   - Typical interface widths: 3-10 Å

5. **Interface generation approaches** — Rule-based assembly is standard for visualization
   - Layer stacking for slab geometry
   - Center embedding for inclusion geometries
   - Periodic boundaries essential for MD compatibility

---

## Open Questions for Later Research

1. **Interface validation:** How to verify generated interfaces are physically reasonable?
2. **Orientation control:** Should users specify crystallographic face for ice slab?
3. **Cavity shapes:** Only spherical, or allow ellipsoidal/irregular?
4. **Performance:** How large can boxes get before generation becomes slow?
5. **Memory:** How many atoms can VTK handle in single viewport?

---

*Research for: QuickIce v3.0 Interface Generation*
*Generated: 2026-04-08*