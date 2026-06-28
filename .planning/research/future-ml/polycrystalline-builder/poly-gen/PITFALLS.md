# Domain Pitfalls

**Domain:** Polycrystalline ice structure generation
**Researched:** 2026-06-28

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Molecular Fragmentation at Boundaries

**What goes wrong:** Clipping crystal atoms individually by region boundary splits water molecules, creating unphysical fragments (e.g., O inside region but one H outside).

**Why it happens:** It's tempting to use simple array masking `positions[x < boundary]` for spatial filtering, which operates on individual atoms.

**Consequences:** MD simulation crashes or produces nonsensical results (broken O-H bonds, ghost charges from TIP4P massless sites, invalid GROMACS topology).

**Prevention:** ALWAYS clip at molecule level. Compute center-of-mass (or first-atom position) for each molecule, check membership, then include or exclude ALL atoms of that molecule.

**Detection:** After clipping, verify `len(positions) % atoms_per_molecule == 0`. If not, molecules were fragmented.

**Evidence from QuickIce:** The existing `water_filler.py::tile_structure()` implements this pattern correctly (lines 519-544: `filter_molecules` flag, molecule-level mask). The `pocket.py` mode also clips molecules by O-atom position (lines 220-241). This pattern MUST be followed for polycrystalline regions.

### Pitfall 2: Infinite Voronoi Regions Break Pipeline

**What goes wrong:** `scipy.spatial.Voronoi` produces regions with `-1` vertex indices (infinite regions) for points near the diagram boundary. Attempting to construct polygons from these regions raises errors.

**Why it happens:** Voronoi diagrams in finite domains always have infinite regions at the boundary. This is a mathematical certainty, not a bug.

**Consequences:** Code crashes when trying to build Shapely Polygons from vertices containing `-1`. OR: Grains near boundaries are silently dropped, leaving gaps.

**Prevention:** Use the mirror-point technique: reflect seed points across all boundaries before computing Voronoi. This guarantees all original-point regions are finite. Then clip to the original box using Shapely `polygon.intersection(box)`.

**Detection:** After Voronoi computation, check `any(-1 in r for r in vor.regions)`. If True and mirrors weren't used, the pipeline will fail.

**Verified:** Tested with `scipy.spatial.Voronoi` v1.17.1 on 2026-06-28. Mirror technique produces 100% coverage (sum of clipped areas = box area).

### Pitfall 3: Triclinic Cell Rotation Creates Invalid Box

**What goes wrong:** Applying an arbitrary rotation matrix to a triclinic crystal cell (Ice II, Ice V) while keeping the simulation box diagonal (orthogonal) creates gaps or overlaps at box boundaries.

**Why it happens:** Triclinic cells have non-zero off-diagonal elements. After rotation, the new cell vectors may have components outside the diagonal box, meaning atoms would need to be in a non-orthogonal box to be valid.

**Consequences:** Atoms near box edges are in wrong positions; PBC wrapping fails; MD simulation has image artifacts.

**Prevention:** 
- **Ice II:** Exclude from rotation entirely (already blocked for interfaces in `interface_builder.py` lines 103-116).
- **Ice V:** Use GenIce2's orthogonal variant `5R` (ice5R) which has a diagonal cell matrix, OR output triclinic box (more complex).
- **General rule:** Only rotate phases with orthogonal cell matrices (Ice Ih, Ic, III, VI, VII, VIII).

**Detection:** After rotation, check `is_cell_orthogonal(R @ cell)`. If False, the rotated cell won't fit in a diagonal box.

**Evidence from QuickIce:** `cell_utils.py::is_cell_orthogonal()` checks off-diagonal elements (already used in `water_filler.py` for triclinic-aware tiling).

### Pitfall 4: Hydrate Guest Molecules Displaced by Rotation

**What goes wrong:** Rotating a hydrate supercell rotates both the water framework and guest molecules. But guests are positioned at cage centers relative to the PBC cell. Rotation may move guests outside their cages.

**Why it happens:** Guest molecules (CH4, THF) are placed by GenIce2 at specific positions within the hydrate cages. When the entire supercell is rotated, guests that were near the PBC boundary may wrap to a different position, ending up outside their cage.

**Consequences:** Unphysical hydrate structure with guests in inter-cage spaces; MD simulation produces immediate instabilities.

**Prevention:** For hydrate rotation, rotate ONLY the water framework atoms. Then re-identify cage centers from the rotated framework and re-place guests. OR: don't rotate hydrates at all (reasonable simplification for MVP).

**Detection:** After rotation, verify guest molecules are inside their cages (distance from cage center < cage radius). GenIce2's `--assess_cages` option can help.

**Confidence:** MEDIUM — this is a theoretical concern; needs empirical testing with GenIce2's hydrate structures.

## Moderate Pitfalls

Mistakes that cause delays or technical debt.

### Pitfall 5: Overlapping User-Drawn Regions

**What goes wrong:** User draws two regions that overlap. Both regions get filled with crystal structure, creating double-density overlap.

**Why it happens:** Interactive polygon drawing doesn't enforce non-overlapping constraint.

**Prevention:** After region definition, check all region pairs for overlap using `shapely.Polygon.intersection()`. If overlap exists, either: (a) warn the user, (b) assign the overlap to one region and subtract from the other, or (c) use the buffer zone approach for the overlap.

### Pitfall 6: Density Mismatch Between Phases

**What goes wrong:** Different ice phases have different densities (0.79 g/cm³ for sI hydrate vs 1.65 g/cm³ for Ice VII). If the box dimensions are set based on one phase's density, other phases will be over- or under-compressed.

**Why it happens:** Box dimensions in MD must be the same for all phases (single simulation box).

**Prevention:** Box dimensions are set by the USER. Each phase generates its own structure with the correct density. At boundaries, the density transition creates a physical grain boundary (handled by buffer zone). Do NOT try to rescale one phase to match another's density.

### Pitfall 7: Crystal-Crystal Overlap at Grain Boundaries

**What goes wrong:** Two adjacent crystal phases (e.g., Ice Ih and Ice II) have molecules whose oxygen atoms are within overlap_threshold of each other at the boundary.

**Why it happens:** Both sides have valid crystal structure that extends to the boundary. Unlike ice-water interfaces (where water is removed), there's no clear "which side to remove from."

**Prevention:** Use the buffer zone approach: dilate both region polygons by `buffer_width`, compute the intersection (buffer zone), remove molecules from BOTH sides whose COM is in the buffer zone, then fill buffer with liquid water.

**Detection:** After assembly, check that no two O atoms from different phases are within `overlap_threshold` (reuse `detect_overlaps()`).

**Evidence from QuickIce:** The current `overlap_resolver.py` handles ice-water overlap (asymmetric: always remove water). For crystal-crystal, symmetric removal is needed.

### Pitfall 8: GenIce2 Supercell Size Mismatch

**What goes wrong:** GenIce2 requires certain minimum supercell sizes for valid hydrogen-bond network topology. For a small region (e.g., 2 nm diameter), the minimum GenIce2 cell for Ice Ih is ~7.8 nm, generating far more molecules than needed.

**Why it happens:** GenIce2's "unit cell" for some phases is actually a large supercell (418 molecules for Ice Ih). This is a fundamental constraint of the ice-rule topology algorithm.

**Consequences:** Wasted memory and compute for generating then discarding most atoms. For very small regions, the supercell may be larger than the entire box.

**Prevention:** This is acceptable — GenIce2 is fast (<0.1s even for large cells). For regions smaller than the minimum cell, just generate the minimum cell and clip. The waste is temporary (positions array is created and immediately filtered).

**Mitigation:** Cache generated supercells per phase. If two regions use the same phase, reuse the same generated candidate (just tile differently).

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 9: Shapely Z-Coordinate Blindness

**What goes wrong:** Using `shapely.Polygon` with 3D coordinates (x, y, z). Shapely ignores the z coordinate in all geometric operations, so `polygon.contains(point)` only checks XY membership.

**Prevention:** Use 2D polygons for XY membership + separate Z-range check. Don't include z in Shapely coordinates.

### Pitfall 10: Voronoi Seed Points Too Close

**What goes wrong:** Two seed points placed very close together create extremely thin Voronoi regions that can't fit any crystal unit cells.

**Why it happens:** User interaction or random generation can place points arbitrarily close.

**Prevention:** Enforce minimum separation between seed points (at least 2 × the largest unit cell dimension, ~12 nm for Ice V). Check `min(np.linalg.norm(p1 - p2))` after placement.

### Pitfall 11: Euler Angle Convention Confusion

**What goes wrong:** Different Euler angle conventions (ZXZ, ZYZ, XYZ) produce different rotations for the same angles.

**Why it happens:** Multiple conventions exist; GenIce2 uses Euler angles in its `euler` format but the convention isn't clearly documented.

**Prevention:** Choose ONE convention (recommend ZXZ, same as GenIce2's `euler` format) and document it prominently. Provide a visual indicator in the GUI showing the rotation axis.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Voronoi generation | P2: Infinite regions | Mirror technique + Shapely clipping |
| Region filling | P1: Molecular fragmentation | Molecule-level COM check |
| Crystal rotation | P3: Triclinic cell rotation | Only rotate orthogonal phases; exclude Ice II |
| Grain boundaries | P7: Crystal-crystal overlap | Buffer zone approach with water fill |
| Hydrate regions | P4: Guest displacement | Don't rotate hydrates in MVP |
| Multi-region assembly | P5: Overlapping user regions | Shapely overlap detection + warning |
| GUI polygon drawing | P10: Seeds too close | Minimum separation enforcement |

## Sources

- QuickIce bug history: `interface_builder.py` Ice II block (line 103-116) — already addresses P3
- QuickIce `water_filler.py` molecule filtering (line 519-544) — pattern for P1
- QuickIce `overlap_resolver.py` ice-water overlap — asymmetric removal that needs extension for P7
- QuickIce `modes/pocket.py` cavity filling — pattern for region-based clipping
- `scipy.spatial.Voronoi` docs — verified infinite region behavior (P2)
- Shapely 2.1.2 manual — confirmed z-coordinate is ignored (P9)
- GenIce2 README — confirmed Euler angle format and minimum cell sizes
