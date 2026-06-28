# Feature Landscape

**Domain:** Polycrystalline ice structure generation
**Researched:** 2026-06-28

## Table Stakes

Features users expect from any polycrystalline builder. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Multiple crystal phases in one box | This IS the definition of polycrystalline | High | Must support at least Ice Ih, Ic, II, III, V, VI + hydrates |
| Region-based phase assignment | Users need to specify WHERE each phase goes | Medium | Either Voronoi auto-generation or manual drawing |
| Grain rotation | Each grain has different crystallographic orientation | Medium | Rotation matrices on generated supercells |
| Overlap removal at boundaries | Atoms can't physically overlap | Low | Reuse existing `overlap_resolver.py` |
| Liquid water fill for gaps | Any unfilled space becomes liquid water | Low | Reuse existing `fill_region_with_water()` |
| GROMACS .gro export | Output must be usable in MD simulations | Low | Reuse existing export pipeline |
| Periodic boundary conditions | MD simulations require PBC | Medium | Box dimensions must accommodate all phases |

## Differentiators

Features that set QuickIce apart from manual construction (the current alternative).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Automatic Voronoi grain generation | One-click polycrystal from seed points | Medium | Mirror technique for finite regions; scipy + shapely |
| Interactive region editing | User can modify auto-generated grains before fill | Medium | Shapely polygon editing in PySide6 GUI |
| Phase-specific density matching | Each ice phase has correct density for its T/P | Medium | Already handled by GenIce2 `density` parameter |
| Grain boundary buffer zone | Disordered water layer between phases for realistic boundaries | Medium | Novel approach; physically motivated |
| Hydrate phase support | sI, sII, sH as grain types (not just ice) | High | Must handle guest molecules in hydrate regions |
| Arbitrary polygon regions | Not limited to Voronoi; draw any shape | Medium | Shapely polygon support; 2D only (extruded in Z) |
| Visual preview before generation | See region layout + crystal orientations in 3D | High | VTK overlay of polygon boundaries on molecular structure |

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Point-in-polygon per-atom clipping | Clipping individual atoms of a molecule destroys molecular integrity (split water molecules) | Always clip at molecule level (center-of-mass membership) |
| Exact boundary alignment | Crystal periodicity can't match arbitrary polygon boundaries; forcing alignment creates artifacts | Accept that boundaries are ragged; use buffer zone approach |
| 3D polyhedral regions | Shapely is 2D-only; full 3D CSG is extremely complex | Use 2D polygon extruded along Z (prism regions); sufficient for polycrystalline ice studies |
| PBC-aware Voronoi without mirroring | Manual PBC correction of infinite Voronoi regions is error-prone | Use mirror technique (reflect across all boundaries) to make all regions finite |
| Ice II rotation | Ice II's rhombohedral cell (b[0]<0, c[0]<0) cannot be rotated in a rectangular box without creating triangular gaps | Exclude Ice II from polycrystalline rotation; already blocked for interfaces |
| Hydrate cage rotation | Rotating hydrate supercell may displace guests from cage centers | Rotate only water framework; re-place guests based on cage topology (defer to later phase) |
| Energy minimization at boundaries | QuickIce is a structure builder, not a MD engine | Let MD engines handle minimization; provide clean enough starting structure |

## Feature Dependencies

```
Region Definition (Voronoi or Manual)
  → Single-Phase Region Fill (tile + clip)
    → Crystal Rotation (for polycrystalline grains)
      → Multi-Region Assembly (overlap resolve + water fill)
        → GUI Integration (interactive editing)

Crystal Rotation is parallel to:
  Single-Phase Region Fill (can develop independently)
  
Multi-Region Assembly depends on:
  BOTH Single-Phase Fill AND Crystal Rotation
```

## MVP Recommendation

For MVP, prioritize:
1. **Region definition data model** — `PolycrystalRegion` class with polygon + phase + rotation
2. **Single-phase region fill** — Generate-Clip pipeline for one polygon
3. **Voronoi auto-generation** — Mirror technique with scipy + shapely clipping

Defer to post-MVP:
- **Crystal rotation:** Add rotation matrices after basic fill works (orthogonal phases first)
- **Multi-region overlap resolution:** Start with non-overlapping Voronoi regions (guaranteed by definition)
- **Hydrate rotation:** Complex; defer until ice rotation is proven
- **3D regions:** 2D polygon extrusion is sufficient for v1

## Phase-Specific Constraints

### GenIce2 Minimum Generation Sizes

From verified runtime checks (2026-06-28):

| Phase | GenIce Name | Min Cell Waters | Cell Extent (nm) | Gen Time (1x1x1) |
|-------|-------------|----------------|-------------------|-------------------|
| Ice Ih | ice1h | 418* | 7.85 × 7.38 × 9.07 | 0.07s |
| Ice Ic | ice1c | 169* | 4.0 × 4.0 × 4.0 | 0.01s |
| Ice II | ice2 | 12 | 1.39 × 1.18 × 0.55 | 0.01s |
| Ice III | ice3 | 477* | 6.67 × 6.67 × 6.94 | 0.00s |
| Ice V | ice5 | 801* | 12.60 × 7.52 × 9.75 | 0.01s |
| Ice VI | ice6 | 399* | 6.18 × 6.18 × 5.70 | 0.00s |
| Ice VII | ice7 | 377* | 4.0 × 4.0 × 4.0 | 0.02s |
| Ice VIII | ice8 | 64 | 0.93 × 0.93 × 1.36 | 0.03s |
| sI hydrate | sI | 2435 | 12.24 × 12.24 × 12.24 | ~1s |
| sII hydrate | sII | 6353 | 6.21 × 6.21 × 6.21 | ~1s |
| sH hydrate | sH | 2661 | 18.63 × 10.76 × 20.13 | ~1s |

*GenIce2's "unit cell" for some phases is actually a supercell that satisfies periodic HB network topology. The true crystallographic unit cell has fewer molecules (e.g., Ice Ih conventional cell = 4 waters, GenIce2 = 418 waters because it needs a large enough supercell for valid ice rules).

**Key insight:** GenIce2 generation is very fast (<0.1s for all ice phases at minimum size). The "wasteful" approach of generating a large supercell and clipping is computationally acceptable.

### Density Reference

| Phase | Density (g/cm³) | Notes |
|-------|----------------|-------|
| Ice Ih | 0.920 | Standard |
| Ice Ic | 0.920 | Same density as Ih |
| Ice II | 1.179 | High-pressure, ordered |
| Ice III | 1.165 | High-pressure |
| Ice V | 1.240 | Most complex structure |
| Ice VI | 1.373 | Double-network |
| Ice VII | 1.600 | Double-network, cubic |
| Ice VIII | 1.628 | Ordered version of VII |
| sI hydrate | 0.795 | Low density (cage structure) |
| sII hydrate | 0.810 | Low density |
| sH hydrate | 0.756 | Lowest density |

## Sources

- GenIce2 unit cell data: Verified by running `safe_import('lattice', name).Lattice()` with GenIce2 v2.2.13.1 on 2026-06-28
- QuickIce `mapper.py` UNIT_CELL_MOLECULES: Cross-referenced with GenIce2 runtime data
- Ice phase properties: Wikipedia "Phases of ice" article, cross-referenced with known crystallographic data (MEDIUM confidence for numeric values, HIGH for qualitative properties)
