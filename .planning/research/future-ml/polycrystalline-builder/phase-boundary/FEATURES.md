# Feature Landscape: Phase Boundary Handling

**Domain:** Polycrystalline ice/hydrate/water builder — phase boundary types
**Researched:** 2026-06-28

## Table Stakes

Features users expect for a polycrystalline builder. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Voronoi grain tessellation | Standard approach for polycrystalline MD (Atomsk, OVITO, all MD papers use it) | Med | scipy.spatial.Voronoi + periodic boundary handling |
| Random crystal orientation per grain | Each grain must have a distinct orientation for polycrystalline behavior | Low | Random rotation matrix applied to unit cell positions |
| Overlap removal at grain boundaries | Adjacent grains have overlapping atoms at boundaries; must remove entire molecules | Med | QuickIce already has `overlap_resolver.py` with PBC-aware cKDTree |
| PBC-compatible box construction | Final structure must tile periodically for GROMACS MD | Low | `round_to_periodicity()` already exists in `water_filler.py` |
| GROMACS export of polycrystalline structure | User runs MD after generation; must produce valid .gro/.top | Low | Existing `gromacs_writer.py` handles multi-molecule-type structures |
| Minimum grain size validation | Grains too small produce unphysical starting structures | Low | Per-phase minimum molecular count; reject or warn |
| Energy minimization-ready output | The #1 use case: "generate structure → run gmx grompp → mdrun" | Med | Must have no steric clashes (O-O overlap ≤ 0.1 nm) after overlap removal |

## Differentiators

Features that set QuickIce apart from Atomsk and other polycrystalline builders.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Multi-phase polycrystal (Ice Ih + Ice II + liquid in one box) | No other tool does this. Atomsk only handles single-phase polycrystals. This is QuickIce's unique selling point. | High | Requires buffer zone algorithm for incompatible lattices |
| Hydrate-containing polycrystal (sI + Ice Ih + liquid) | Even more unique. No published tool generates polycrystalline hydrate structures. | Very High | Guest molecule handling at boundaries is unsolved in literature |
| Disordered buffer zone insertion | Automatic insertion of ~1 nm water buffer between incompatible phases | Med | Algorithm: detect boundary region → remove atoms within buffer_width/2 → fill with disordered water |
| Interactive grain shape drawing (GUI) | Users draw arbitrary polygonal grain shapes on 2D slice | Med | shapely for polygon ops; VTK for 3D extrusion |
| Phase-specific density scaling | Each grain is scaled to its phase's correct density | Low | Already exists per-phase in `PHASE_METADATA` |
| Grain boundary width control | User can set desired GB width (0.5–2.0 nm) | Low | Maps to overlap_threshold parameter |
| Crystal face orientation control | User chooses which crystal face (basal/prismatic) faces the boundary | Med | Requires unit cell rotation to expose specific Miller indices |
| Cross-grain molecule type assignment | Assign Ice Ih to grain A, Ice II to grain B, liquid to region C | Low | Per-grain metadata dict with phase_id |

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Direct lattice stitching between incompatible phases | Ice Ih (hexagonal, a=4.52Å) cannot tile seamlessly with Ice II (rhombohedral, a=12.96Å) or sI hydrate (cubic, a=11.88Å). Attempting this creates enormous steric clashes and unphysical strain. | Insert disordered water buffer zone (1–2 nm) between incompatible phases. Let MD equilibrate the boundary. |
| Single-phase polycrystal only | Atomsk already does this well. QuickIce would add no value. | Must support multi-phase as differentiator. Single-phase is Phase 1 (foundation), not the end goal. |
| Forcing PBC-wrap on user-drawn shapes in v7.0 | Shapely doesn't understand PBC. The geometric algorithm for splitting a polygon at a periodic boundary and wrapping it is complex and error-prone. | Constrain shapes to box boundaries in initial release. Add PBC-wrap as optional feature later. |
| Allowing grains below minimum unit cell size | A grain with <1 unit cell of a phase is not that phase — it's a cluster. MD starting from such structures will not equilibrate into the intended crystal. | Validate minimum grain size per phase; reject configurations that violate minimums; provide clear error messages with the minimum sizes. |
| Ignoring density mismatch between adjacent grains | Ice Ih (0.92 g/cm³) adjacent to Ice II (1.18 g/cm³) in the same box creates ~25% volume mismatch. If both grains fill their Voronoi cells completely, there will be either voids or massive overlaps at the boundary. | Use the lower-density phase as the "master" for box dimensions. Scale the higher-density phase or insert buffer zone. Or: let overlap_resolver handle it (remove overlapping molecules from BOTH sides). |
| Building polycrystalline structures at thermodynamically unstable conditions | Ice Ih at 300 MPa should be Ice II or Ice III. Users will generate unphysical structures that spontaneously transform in MD, defeating the purpose. | Add a phase-stability warning: if (T,P) is in a different phase's stability region, warn the user that the starting structure will likely transform during MD. Do NOT block generation (some users intentionally study metastable states). |
| Hardcoding grain boundary atomic structure | The GB structure depends on the specific misorientation, and trying to construct it atom-by-atom is a research-level problem. | Generate clean crystals per grain → overlap-remove at boundaries → let MD find the GB structure. This is the standard approach in all polycrystalline MD papers. |

## Feature Dependencies

```
Voronoi tessellation → Random orientation per grain → Overlap removal at GBs
                     ↓
               GROMACS export
                     ↓
           Minimum grain size validation

Multi-phase polycrystal:
  Phase assignment per grain → Density scaling per grain → Buffer zone insertion (if incompatible)
                                                                      ↓
                                                              Overlap removal at buffer-grain interface
                                                                      ↓
                                                              GROMACS export

Hydrate-containing polycrystal:
  Hydrate generation (GenIce2) → Guest handling at boundaries → Buffer zone insertion
                                                                    ↓
                                                            GROMACS export (dual moleculetype)

Shape drawing (GUI):
  shapely polygon → 2D→3D extrusion → Phase assignment → Voronoi fill → rest of pipeline
```

## Boundary Type Classification

### Tier 1: Same-Phase Grain Boundaries (Easiest)

| Boundary Type | Compatibility | Buffer Needed | Physical Basis | Implementation |
|---------------|--------------|---------------|----------------|----------------|
| Ice Ih ↔ Ice Ih (different orientations) | High — same lattice, different orientation | No — overlap removal suffices | Well-studied; ~1 nm disordered region forms naturally in MD | Voronoi + rotate + overlap-remove |
| Ice Ic ↔ Ice Ic (different orientations) | High — cubic diamond lattice | No | Less studied but same principle | Same as Ice Ih |
| Ice Ih ↔ Ice Ic (stacking fault boundary) | Medium — hex/cubic stacking boundary | No — stacking faults are physical | Zhang et al. 2024 "Multitwinned ice nanocrystals" — Ih↔Ic boundary is a stacking fault | Special handling: align c-axis, switch stacking sequence |

### Tier 2: Compatible Water-Model Boundaries (Medium)

| Boundary Type | Compatibility | Buffer Needed | Physical Basis | Implementation |
|---------------|--------------|---------------|----------------|----------------|
| Ice Ih ↔ Liquid water | Medium — density mismatch ~8% | Optional — overlap removal works | Well-studied; QuickIce already does this | Existing `slab.py`/`pocket.py`/`piece.py` modes |
| Hydrate ↔ Liquid water | Medium — density mismatch ~20% | Optional — overlap removal works | Hydrate growth from solution is well-studied | Extend existing interface modes |
| Ice Ih ↔ Hydrate (same T/P) | Low — no lattice matching (Nguyen 2015) | YES — 1–2 nm disordered buffer | No plane of ice matches any plane of clathrate | Buffer zone + overlap-remove |

### Tier 3: Incompatible Lattice Boundaries (Hardest)

| Boundary Type | Compatibility | Buffer Required | Density Mismatch | Implementation |
|---------------|--------------|----------------|-----------------|----------------|
| Ice Ih ↔ Ice II | None — hexagonal vs rhombohedral | 1–2 nm minimum | 0.92 vs 1.18 = 28% | Buffer + overlap-remove |
| Ice Ih ↔ Ice V | None — hexagonal vs monoclinic | 1–2 nm minimum | 0.92 vs 1.24 = 35% | Buffer + overlap-remove |
| Ice II ↔ Ice V | None — different lattices | 1–2 nm minimum | 1.18 vs 1.24 = 5% | Buffer (thinner possible) |
| Ice V ↔ Ice VI | None — both high-P but very different | 1–2 nm minimum | 1.24 vs 1.31 = 5% | Buffer (thinner possible) |
| Any ice ↔ Hydrate | None — no lattice matching exists | 1–2 nm minimum | Varies widely | Buffer + overlap-remove + guest handling |

## MVP Recommendation

For polycrystalline builder MVP (v7.0), prioritize:

1. **Tier 1 boundaries only**: Voronoi-based Ice Ih polycrystal with random orientations + overlap removal
2. **PBC-safe box construction**: Ensure periodic tiling works
3. **Minimum grain size validation**: Reject too-small grains
4. **GROMACS export**: Energy minimization-ready output

Defer to post-MVP:
- **Tier 2 boundaries** (v7.5): Ice + liquid water polycrystal; hydrate + liquid water polycrystal
- **Tier 3 boundaries** (v8.0): Multi-ice-phase polycrystal with buffer zones; hydrate + ice polycrystal
- **Crystal face orientation control** (v7.5): Basal/prismatic face selection per grain
- **PBC-wrap for shapes** (v8.0): Split-and-wrap algorithm for shapes crossing periodic boundaries
- **Interactive grain shape drawing** (v7.0 or v7.5 depending on GUI bandwidth)

## Buffer Zone Specification

For Tier 3 boundaries (incompatible lattices), the buffer zone algorithm:

1. **Detect boundary region**: Find atoms within `buffer_width/2` of the grain boundary plane
2. **Remove atoms from both grains**: Delete all molecules whose center of mass falls within the buffer zone
3. **Fill with disordered water**: Use `fill_region_with_water()` from `water_filler.py` to insert TIP4P-ICE water at the target density for the given (T,P)
4. **Remove overlaps**: Run `detect_overlaps()` + `remove_overlapping_molecules()` at the buffer-grain interfaces
5. **Result**: A ~1–2 nm disordered water region between incompatible crystalline phases

**Buffer width recommendation:**
- Minimum: 1.0 nm (based on Yagasaki et al. 2020 GB width for same-phase; Nguyen et al. 2015 interface thickness)
- Recommended: 1.5 nm (provides safety margin for density mismatch)
- Maximum: 2.0 nm (beyond this, the "boundary" becomes a separate water grain)

**Why this works for MD:**
- The disordered water at the boundary is thermodynamically reasonable — quasi-liquid layers at ice GBs and hydrate-ice interfaces are physical
- Energy minimization will relax the boundary structure without steric clashes
- Short NVT equilibration (100–500 ps) will establish the correct boundary structure
- Production MD will show realistic grain boundary dynamics

## Sources

- See SUMMARY.md for complete reference list
