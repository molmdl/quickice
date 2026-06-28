# Research Summary: Polycrystalline Builder — Region Filling (poly-gen)

**Domain:** Molecular dynamics structure generation — polycrystalline ice
**Researched:** 2026-06-28
**Overall confidence:** MEDIUM-HIGH

## Executive Summary

Building a polycrystalline ice structure generator is technically feasible using the existing QuickIce infrastructure, but requires careful algorithm design to handle the fundamental tension between crystallographic periodicity and arbitrary region boundaries. The core challenge is that GenIce2 generates periodic supercells, while user-defined regions are arbitrary polygons that cut through the crystal lattice.

The recommended algorithm is a **Generate-Clip-Resolve** pipeline: (1) generate each phase's structure as a supercell slightly larger than the region's bounding box, (2) clip molecules to the region boundary using center-of-mass membership, (3) resolve overlaps between adjacent phase regions, and (4) fill remaining space with liquid water. This approach is wasteful in generation (most atoms get clipped) but is correct, simple, and leverages the existing `tile_structure()` and `overlap_resolver.py` infrastructure.

Crystal rotation for polycrystalline grains is straightforward for orthogonal phases (Ice Ih, Ic, III, VI, VII) via rotation matrices applied to all atom positions, but problematic for triclinic phases (Ice II, Ice V) which have non-diagonal cell matrices. Ice II should be excluded from polycrystalline rotation entirely (already blocked for interfaces). Ice V can be rotated if the cell matrix is also rotated, but this creates a triclinic simulation box — we recommend deferring this to a later phase.

Grain boundaries between different crystal phases should use a **disordered water buffer zone** approach: remove molecules from both phases whose COM falls within a buffer width of the boundary, then fill the buffer with liquid water. This is physically reasonable (grain boundaries in ice are known to contain disordered water) and avoids the unsolvable problem of crystal-crystal overlap resolution.

Voronoi grain generation is fully supported by `scipy.spatial.Voronoi` (N-dimensional, using Qhull) and `shapely` (for polygon operations). The key technique is the **mirror-point method** to make all Voronoi regions finite, then clip to the box boundary. Both auto-generated (Voronoi) and user-drawn regions can coexist: generate Voronoi → allow user editing → proceed with fill algorithm.

## Key Findings

**Stack:** All required libraries exist in `environment.yml`. No new dependencies needed.
**Architecture:** Generate-Clip-Resolve pipeline extends existing `water_filler.py` + `overlap_resolver.py`.
**Critical pitfall:** Crystal rotation of triclinic cells (Ice II, Ice V) creates invalid structures if not done correctly.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Region definition & Voronoi generation** — Define region data model, implement Voronoi with mirror technique, convert to Shapely polygons
   - Addresses: FEATURES.md items R1, R2 (Voronoi + manual regions)
   - Avoids: PITFALLS.md items P1 (infinite Voronoi regions), P2 (overlapping user regions)

2. **Region filling for single phase** — Fill a single arbitrary polygon with one crystal phase
   - Addresses: FEATURES.md items F1, F2 (tiling + clipping)
   - Avoids: PITFALLS.md items P3 (molecular fragmentation), P4 (boundary artifacts)

3. **Crystal rotation** — Apply rotation matrices to generated supercells
   - Addresses: FEATURES.md item F3 (grain orientation)
   - Avoids: PITFALLS.md items P5 (triclinic rotation), P6 (hydrate cage topology)

4. **Multi-region assembly** — Handle overlapping regions, grain boundaries, water fill
   - Addresses: FEATURES.md items F4, F5 (grain boundaries + water fill)
   - Avoids: PITFALLS.md items P7 (crystal-crystal overlap), P8 (density mismatch)

5. **GUI integration** — VTK rendering of regions, interactive editing
   - Depends on Phase 1-4 algorithm completion
   - Research flags: VTK polygon rendering with Shapely data

**Phase ordering rationale:**
- Region definition must come first (everything depends on it)
- Single-phase filling must work before multi-region assembly
- Crystal rotation is independent but needed before multi-grain assembly
- GUI integration is last (pure UI, depends on core algorithm)

**Research flags for phases:**
- Phase 3 (Crystal rotation): Triclinic cell rotation needs deeper research for Ice V
- Phase 5 (GUI): VTK rendering of polygonal regions on 3D molecular view needs feasibility test

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libs in environment.yml, verified via API docs |
| Features | HIGH | Well-understood domain, MD community practices documented |
| Architecture | MEDIUM-HIGH | Generate-Clip-Resolve is sound but boundary artifacts need testing |
| Pitfalls | HIGH | Well-documented from existing QuickIce bugs + crystallography literature |

## Gaps to Address

- **Ice V rotation with triclinic cell:** Rotation matrix applied to cell vectors must preserve cell validity; needs explicit test
- **Hydrate rotation:** Rotating a hydrate supercell might break cage topology if guests were placed relative to PBC; needs GenIce2-specific testing
- **3D Voronoi with PBC:** The mirror technique works in 2D but extending to 3D periodic boundaries (mirroring across 6 faces × 12 edges × 8 corners = 26 mirror images) needs verification
- **Buffer zone width:** The optimal grain boundary buffer width for ice-ice interfaces is unknown; 0.5-1.0 nm is a reasonable starting range
