# Architecture Patterns

**Domain:** Polycrystalline ice structure generation
**Researched:** 2026-06-28

## Recommended Architecture

### Overall Pipeline: Generate-Clip-Resolve-Fill

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ 1. Define   │────▶│ 2. Generate  │────▶│ 3. Clip to   │────▶│ 4. Resolve   │
│    Regions  │     │    Phase      │     │    Region    │     │    Overlaps  │
│             │     │    Structures │     │    Boundary  │     │    & Fill    │
└─────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
  Voronoi or          GenIce2 per         Molecule-level        Crystal-crystal
  manual polygons     region, with        COM-in-polygon       overlap removal,
                      rotation if          membership           water fill for
                      specified                                 remaining space
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `PolycrystalConfig` | Region definitions (polygon, phase_id, rotation) | GUI → Core |
| `RegionDefiner` | Voronoi auto-generation + user editing | GUI, shapely, scipy |
| `PhaseFiller` | Generate + clip crystal structure for one region | GenIce2, water_filler, shapely |
| `CrystalRotator` | Apply rotation matrix to supercell positions + cell | numpy |
| `GrainBoundaryResolver` | Remove overlapping molecules between adjacent phases | overlap_resolver, PhaseFiller |
| `WaterFiller` | Fill remaining space with liquid water | water_filler (existing) |
| `PolycrystalAssembler` | Combine all phase positions, assign atom names, build cell | All above |

### Data Flow

```
1. User draws N regions (or auto-generates via Voronoi)
   → List[PolycrystalRegion] where each has:
     - polygon: shapely.Polygon (2D XY)
     - phase_id: str ("ice_ih", "ice_ii", "hydrate_sI", etc.)
     - rotation: tuple[float,float,float] (Euler angles, degrees)
     - z_min, z_max: float (extrusion range in Z)

2. For each region:
   a. Compute bounding box of polygon → (min_x, min_y, max_x, max_y)
   b. Compute Z-extent → [z_min, z_max]
   c. Generate GenIce2 supercell covering bounding box (with margin)
   d. If rotation specified: apply R @ positions, R @ cell
   e. Tile structure to fill bounding box
   f. For each molecule: compute COM, check if COM is inside polygon (XY) AND inside [z_min, z_max]
   g. Keep molecules whose COM is inside the region
   → Produces: (positions, atom_names, n_molecules) per region

3. Assemble all regions:
   a. Concatenate positions from all regions (ice first, then water)
   b. Detect overlaps between molecules of DIFFERENT regions
      - Build cKDTree for each region's oxygen positions
      - Find inter-region molecule pairs within overlap_threshold
   c. For overlapping molecules:
      - Option A (recommended): Remove from BOTH sides, create buffer zone
      - Option B (simple): Remove from the "less important" side
   d. Fill remaining space (not in any region) with liquid water
   e. Resolve water-crystal overlaps (reuse existing detect_overlaps)

4. Output InterfaceStructure (compatible with existing export pipeline)
```

## Patterns to Follow

### Pattern 1: Molecule-Level Clipping (NEVER atom-level)

**What:** When clipping a crystal structure to a region boundary, always check molecule membership, never individual atom membership.

**When:** Any time atoms must be filtered by spatial region.

**Why:** Clipping individual atoms splits molecules (e.g., O inside region but H outside), creating unphysical fragments with broken bonds.

**Example:**
```python
# CORRECT: Clip by molecule center-of-mass
n_molecules = len(positions) // atoms_per_molecule
mol_coms = positions.reshape(n_molecules, atoms_per_molecule, 3).mean(axis=1)
# Use shapely for 2D check
from shapely import Point
keep_mask = np.array([polygon.contains(Point(com[0], com[1])) for com in mol_coms])
filtered = positions[np.repeat(keep_mask, atoms_per_molecule)]

# WRONG: Clip by individual atom position
# This splits molecules at boundaries!
inside = positions[:, 0] < boundary_x  # DANGEROUS
```

### Pattern 2: Generate-Then-Clip (wasteful but correct)

**What:** Generate a crystal supercell larger than the target region, then clip molecules outside the region.

**When:** Filling arbitrary polygonal regions with periodic crystal structures.

**Why:** The alternative (placing unit cells only at grid points inside the polygon) requires complex geometric computation and risks missing molecules near boundaries. GenIce2 generation is fast (<0.1s), so waste is acceptable.

**Example:**
```python
# 1. Compute bounding box with margin
bbox = polygon.bounds  # (minx, miny, maxx, maxy)
margin = 0.5  # nm, ensures boundary coverage
region_dims = np.array([bbox[2]-bbox[0]+2*margin, bbox[3]-bbox[1]+2*margin, z_max-z_min+2*margin])

# 2. Generate supercell covering bounding box
candidate = generate_candidates(phase_info, target_molecules)
tiled, n_mol = tile_structure(candidate.positions, cell_dims, region_dims, ...)

# 3. Translate to region origin
tiled += np.array([bbox[0]-margin, bbox[1]-margin, z_min-margin])

# 4. Clip molecules by COM membership
keep = molecule_com_inside_polygon(tiled, polygon, z_min, z_max, atoms_per_mol)
filtered = tiled[np.repeat(keep, atoms_per_mol)]
```

### Pattern 3: Mirror-Point Voronoi for PBC

**What:** To create finite Voronoi regions under periodic boundary conditions, reflect seed points across all boundaries before computing the Voronoi diagram.

**When:** Auto-generating grain structure with PBC.

**Why:** `scipy.spatial.Voronoi` produces infinite regions (indices = -1) for boundary points. Mirroring eliminates infinite regions, then Shapely clips to the original box.

**Example:**
```python
# 2D mirror: reflect across 4 boundaries → 5 copies total (original + 4 mirrors)
mirrors = [points]
mirrors.append(np.column_stack([-points[:,0], points[:,1]]))          # left
mirrors.append(np.column_stack([2*Lx - points[:,0], points[:,1]]))    # right
mirrors.append(np.column_stack([points[:,0], -points[:,1]]))         # bottom
mirrors.append(np.column_stack([points[:,0], 2*Ly - points[:,1]]))   # top
all_pts = np.vstack(mirrors)

vor = Voronoi(all_pts)
# Original points are indices 0..N-1; their regions are guaranteed finite
for i in range(len(points)):
    region = vor.regions[vor.point_region[i]]
    poly = Polygon(vor.vertices[region])
    clipped = poly.intersection(box(0, 0, Lx, Ly))  # Clip to PBC box
```

### Pattern 4: Buffer Zone for Grain Boundaries

**What:** Instead of trying to resolve crystal-crystal overlaps (both sides have valid structure), create a disordered water buffer zone between adjacent phases.

**When:** Two different crystal phases share a boundary.

**Why:** Crystal-crystal boundaries in ice are inherently disordered at the atomic scale. Trying to merge two perfect lattices at an arbitrary boundary always creates unphysical overlaps or voids. A thin water layer is physically realistic and computationally simple.

**Example:**
```python
# For each pair of adjacent regions:
# 1. Dilate each polygon by buffer_width
# 2. Intersection = buffer zone
# 3. Remove molecules from BOTH regions whose COM is in buffer zone
# 4. Fill buffer zone with liquid water

buffer_width = 0.5  # nm (1-2 molecular diameters)
buffer_poly = region_a.polygon.buffer(buffer_width).intersection(
    region_b.polygon.buffer(buffer_width)
)
# Remove molecules in buffer from both regions
# Fill buffer with water
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Atom-Level Spatial Filtering

**What:** Filtering atoms individually based on spatial membership.
**Why bad:** Splits molecules at boundaries, creating unphysical fragments (e.g., water with O inside but H outside region).
**Instead:** Always filter at molecule level using center-of-mass.

### Anti-Pattern 2: Forcing Crystal Alignment to Boundary

**What:** Adjusting atom positions to align the crystal lattice with the region boundary.
**Why bad:** Crystal lattices have fixed periodicity; forcing alignment creates strain artifacts that propagate into the bulk.
**Instead:** Accept ragged boundaries; use buffer zone approach for realistic grain boundaries.

### Anti-Pattern 3: Rotating Triclinic Cells in Orthogonal Boxes

**What:** Applying arbitrary rotation to Ice II or Ice V supercell while keeping the simulation box orthogonal.
**Why bad:** Rotated triclinic cell vectors don't fit in a diagonal box matrix; forcing them creates gaps or overlaps at box edges.
**Instead:** For Ice II: exclude from rotation (already blocked for interfaces). For Ice V: rotate the cell matrix too and use triclinic box output, or use the orthogonal Ice V variant (ice5R in GenIce2).

### Anti-Pattern 4: Single-Pass Overlap Resolution

**What:** Trying to resolve all overlaps in one pass by removing molecules from both sides.
**Why bad:** Removing a molecule from one region can create a gap that overlaps with a different molecule from the other region. Multi-region overlap is transitive.
**Instead:** Use buffer zone approach — remove ALL molecules within the buffer width, then fill with water. This avoids cascading overlap issues.

## Scalability Considerations

| Concern | At 5 grains | At 50 grains | At 500 grains |
|---------|-------------|---------------|----------------|
| Voronoi generation | Instant (scipy Qhull) | ~10ms | ~100ms |
| GenIce2 per phase | ~0.05s × 5 = 0.25s | ~0.05s × 50 = 2.5s | ~0.05s × 500 = 25s |
| Shapely polygon clip | ~1ms × 5 | ~10ms × 50 | ~100ms × 500 |
| Overlap detection (cKDTree) | ~1ms | ~10ms | ~100ms |
| Water fill | ~1ms | ~5ms | ~50ms |
| **Total** | **~0.3s** | **~3s** | **~30s** |

For typical polycrystalline studies (5-50 grains), generation time is acceptable.
For 500+ grains, the bottleneck is GenIce2 calls — can be parallelized (each grain is independent).

## 2D vs 3D Regions

### Recommended: 2D Polygon Extruded Along Z (Prism Regions)

**Rationale:**
- Shapely is 2D-only (z coordinate ignored in geometric analysis)
- Polycrystalline ice studies typically use columnar grains (extruded along one axis)
- Simpler UI: draw regions in XY plane, set Z range per phase
- Most physical setups: ice grows from a surface, creating columnar grains

**Implementation:**
```python
@dataclass
class PolycrystalRegion:
    polygon: shapely.Polygon  # 2D region in XY plane
    phase_id: str             # e.g., "ice_ih"
    rotation: tuple[float, float, float]  # Euler angles (degrees)
    z_min: float              # Bottom of extrusion (nm)
    z_max: float              # Top of extrusion (nm)
    buffer_width: float = 0.5  # Grain boundary buffer (nm)
```

**If 3D polyhedral regions are needed later:**
- Would require a 3D CSG library (not in environment.yml)
- Alternative: stack 2D layers with different XY polygons per Z-slice
- This is a future enhancement, not needed for MVP

## Sources

- QuickIce `water_filler.py`: tile_structure() pattern for rectangular region filling
- QuickIce `overlap_resolver.py`: cKDTree + PBC overlap detection pattern
- QuickIce `modes/pocket.py`: cavity-filling pattern (sphere/cubic region with water)
- scipy.spatial.Voronoi docs (verified 2026-06-28)
- Shapely 2.1.2 manual (verified via official docs)
