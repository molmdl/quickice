# Feasibility: Python Polycrystalline Hydrate Assembly Without Atomsk

**Goal:** Replace atomsk's `--polycrystal` with pure Python using current environment libraries
**Verdict:** YES — with one managed gap (periodic Voronoi tessellation requires image replication, not natively supported by scipy)
**Confidence:** HIGH
**Date:** 2026-06-12

## Summary

Python can replace atomsk's `--polycrystal` mode for polycrystalline hydrate assembly. The core algorithm — 3D Voronoi tessellation of grain nodes, rotation of seed structures, atom truncation to Voronoi polyhedra, and overlap removal — maps directly to capabilities already present in QuickIce's environment: `scipy.spatial.Voronoi` for tessellation, `scipy.spatial.transform.Rotation` for grain orientations, `scipy.spatial.ConvexHull` for point-in-polyhedron tests, and the existing `cKDTree`-based `overlap_resolver.py` for grain boundary cleanup. The one non-trivial gap is that `scipy.spatial.Voronoi` does not natively support periodic boundary conditions; this is solved by replicating grain nodes as 3×3×3 periodic images before tessellation, a well-established workaround used in multiple computational materials science codes.

Building this in Python rather than wrapping atomsk via subprocess delivers three concrete advantages that matter for QuickIce's scientific users: (1) multi-phase polycrystals where individual grains can be sI, sII, sH, or even ice — atomsk cannot do this; (2) direct GenIce2 → GROMACS GRO output without format conversion — atomsk has no GRO support; (3) molecular-integrity-preserving overlap removal using QuickIce's existing `cKDTree` code. The implementation is estimated at ~250-300 lines of non-trivial geometry code, heavily leveraging existing QuickIce components. Performance for typical hydrate polycrystals (50K-500K atoms) is acceptable (5-30 seconds) and becomes a non-issue compared to the subsequent MD simulation time.

## Approach: scipy.spatial.Voronoi + GenIce2 + numpy

### Step 1: Voronoi Tessellation with Periodic Boundary Conditions

**The gap:** `scipy.spatial.Voronoi` computes N-dimensional Voronoi diagrams but does NOT support periodic boundary conditions. It uses Qhull internally, which operates on finite point sets without PBC awareness.

**The solution:** Replicate grain node positions as periodic images before computing the Voronoi diagram.

```python
def compute_periodic_voronoi(grain_nodes, box_dims):
    """
    Compute 3D Voronoi tessellation with PBC by replicating grain nodes.
    
    For N grain nodes in a box [0, Lx) × [0, Ly) × [0, Lz),
    replicate each node to its 26 periodic images (3×3×3 grid minus center).
    Compute scipy.spatial.Voronoi on all 27N points.
    Extract only the Voronoi regions for the N original (center-cell) nodes.
    
    This is the standard approach used in:
    - VORO++ (Rycroft et al., 2006, official Voronoi code with PBC)
    - Ovito's Polyhedral Template Matching
    - Multiple polycrystal generation codes in the literature
    
    For 10-50 grain nodes, this means 270-1350 total points, which is
    trivially fast for Qhull (sub-second).
    """
    # Generate 3×3×3 periodic images
    images = []
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            for dz in [-1, 0, 1]:
                shift = np.array([dx, dy, dz]) * box_dims
                shifted = grain_nodes + shift
                images.append(shifted)
    
    all_points = np.vstack(images)  # (27*N, 3)
    vor = Voronoi(all_points)
    
    # Extract regions for original N points (indices 0..N-1 in center cell)
    # The center-cell nodes are in the image (dx=0, dy=0, dz=0)
    center_start = 9 * len(grain_nodes)  # offset for (0,0,0) image
    # Actually: we need to track which image block is the center
    center_idx = 13  # (0,0,0) is the 14th of 27 images (index 13)
    center_nodes_start = center_idx * len(grain_nodes)
    center_nodes_end = center_nodes_start + len(grain_nodes)
    
    # Get Voronoi region vertex indices for each center-cell node
    grain_regions = []
    for i in range(len(grain_nodes)):
        region_idx = vor.point_region[center_nodes_start + i]
        region_vertices = vor.regions[region_idx]
        grain_regions.append(region_vertices)
    
    return vor, grain_regions
```

**Important detail:** After computing the periodic Voronoi, vertices near the box boundaries must be wrapped back into the primary cell `[0, box_dims)`. Any vertex with a coordinate outside `[0, L)` is shifted by the appropriate multiple of `L`. This ensures all Voronoi polyhedra are defined in the same coordinate space.

**2D Voronoi mode:** If one box dimension is ≤ the seed dimension, switch to 2D Voronoi (columnar grains). This matches atomsk's behavior. In 2D mode, only X-Y images are replicated (3×3 grid), and all grains share the same Z extent.

**Confidence:** HIGH — this image-replication approach is well-established in computational geometry for periodic Voronoi tessellation. The only edge case is when grain nodes are very close to box boundaries, which is handled by the 3×3×3 replication.

### Step 2: Grain Rotation

Each grain is a rotated copy of the seed structure. Rotation is applied using `scipy.spatial.transform.Rotation`:

```python
from scipy.spatial.transform import Rotation

def rotate_grain(positions, orientation):
    """
    Rotate seed structure by grain orientation.
    
    Args:
        positions: (N, 3) atom positions in nm, relative to grain node
        orientation: Either 
            - Rotation object (scipy.spatial.transform.Rotation)
            - Euler angles (alpha, beta, gamma) in degrees
            - Miller indices [h, k, l] as rotation axis
            - "random" for random orientation
    
    Returns:
        (N, 3) rotated positions
    """
    if isinstance(orientation, str) and orientation == "random":
        rot = Rotation.random()
    elif isinstance(orientation, (list, tuple, np.ndarray)):
        if len(orientation) == 3:
            # Euler angles (ZXZ convention, matching atomsk)
            rot = Rotation.from_euler('ZXZ', orientation, degrees=True)
        else:
            raise ValueError(f"Unknown orientation format: {orientation}")
    elif isinstance(orientation, Rotation):
        rot = orientation
    else:
        raise TypeError(f"orientation must be Rotation, Euler angles, or 'random'")
    
    # Rotate positions around the grain node (origin)
    rotated = rot.apply(positions)
    return rotated
```

**Key consideration:** The seed structure positions must be translated so the grain node is at the origin before rotation, then translated back after rotation. For cubic hydrate unit cells (sI: Pm-3n, sII: Fd-3m), the center of the unit cell is the natural rotation origin.

**GenIce2 integration:** QuickIce already calls GenIce2's Python API in `hydrate_generator.py` to produce structures. For polycrystal mode, each grain's seed is generated via `HydrateStructureGenerator.generate(config)` and then converted to a `Candidate` via `HydrateStructure.to_candidate()`. This eliminates the need for any format conversion — GenIce2's Python objects flow directly into the polycrystal builder.

**Confidence:** HIGH — `scipy.spatial.transform.Rotation` is mature and well-tested. Euler angle conventions are the only subtlety (must match atomsk's ZXZ convention for compatibility with published parameter files).

### Step 3: Atom Truncation (Point-in-Polyhedron Test)

After rotating a seed structure, atoms that fall outside the grain's Voronoi polyhedron must be removed. This requires a point-in-polyhedron test.

**Approach: ConvexHull half-plane test**

Voronoi polyhedra are convex by construction. A point is inside a convex polyhedron if and only if it is on the interior side of all the polyhedron's facet planes. The `scipy.spatial.ConvexHull` provides exactly this information via its `equations` attribute:

```python
def point_in_voronoi_polyhedron(points, vor, region_vertices, grain_node, box_dims):
    """
    Test which points fall inside a Voronoi polyhedron.
    
    Uses the convex hull / half-plane approach:
    1. Get Voronoi region vertices for this grain
    2. Compute ConvexHull of those vertices
    3. For each atom, check if it's on the interior side of all facet planes
    4. ConvexHull.equations gives [normal, offset] for each facet
    5. Point is inside if dot(normal, point) + offset <= 0 for ALL facets
    
    This is O(M atoms × F facets) per grain, but F is small (typically 6-20)
    and M can be vectorized with numpy.
    """
    # Get Voronoi region vertices (skip -1 = infinity)
    valid_vertices = [v for v in region_vertices if v >= 0]
    if not valid_vertices:
        return np.ones(len(points), dtype=bool)  # Open region = all inside
    
    region_coords = vor.vertices[valid_vertices]
    
    # Wrap region coordinates into primary cell
    for dim in range(3):
        region_coords[:, dim] = np.mod(region_coords[:, dim], box_dims[dim])
    
    # Compute convex hull for half-plane equations
    hull = ConvexHull(region_coords)
    
    # Test all points against all facet equations (vectorized)
    # hull.equations: (n_facets, 4) = [normal_x, normal_y, normal_z, offset]
    # Point is inside if normal·point + offset <= 0
    inside = np.ones(len(points), dtype=bool)
    for eq in hull.equations:
        normal = eq[:3]
        offset = eq[3]
        # For each point: dot(normal, point) + offset
        projections = points @ normal + offset
        inside &= (projections <= 1e-8)  # Small tolerance for numerical precision
    
    return inside
```

**Alternative approach: `cKDTree`-based region assignment**

Instead of point-in-polyhedron testing, a simpler (and potentially faster for many atoms) approach assigns each atom to the nearest grain node:

```python
from scipy.spatial import cKDTree

def assign_atoms_to_grains(atom_positions, grain_nodes, box_dims):
    """
    Assign each atom to its nearest grain node using cKDTree with PBC.
    
    This is equivalent to Voronoi region assignment for the inside/outside test,
    because the Voronoi region of a node IS the set of points closer to that
    node than to any other.
    
    Much simpler than the polyhedron approach, and leverages cKDTree's PBC support.
    """
    tree = cKDTree(grain_nodes, boxsize=box_dims.tolist())
    distances, grain_ids = tree.query(atom_positions)
    return grain_ids
```

**Recommendation:** Use the `cKDTree` approach for atom assignment (Step 3), NOT the polyhedron approach. The `cKDTree` approach:
- Is mathematically equivalent (Voronoi regions = nearest-neighbor regions)
- Has built-in PBC support via `boxsize` parameter
- Is already proven in QuickIce's `overlap_resolver.py` (lines 69-73)
- Is simpler to implement (~15 LOC vs ~50 LOC)
- Handles edge cases naturally (atoms near boundaries, small grains)

The polyhedron approach is still useful for **visualization** (rendering grain boundaries in VTK) and for generating auxiliary files (grain sizes, node positions).

**Confidence:** HIGH — `cKDTree.query()` with `boxsize` is already the standard approach in QuickIce for PBC-aware nearest-neighbor queries.

### Step 4: Grain Boundary Cleanup

After placing all rotated grains and assigning atoms to their grains, atoms at grain boundaries may be too close (overlap). QuickIce already has a battle-tested overlap resolver:

**Reusable component: `overlap_resolver.py`**

| Function | Purpose | Reusability |
|----------|---------|-------------|
| `detect_overlaps()` | PBC-aware cKDTree overlap detection | ✅ Direct reuse |
| `remove_overlapping_molecules()` | Whole-molecule removal | ✅ Direct reuse |
| `filter_atom_names()` | Synchronize atom names with filtered positions | ✅ Direct reuse |
| `angstrom_to_nm()` / `nm_to_angstrom()` | Unit conversion | ✅ Direct reuse |

**The grain boundary cleanup algorithm:**

```python
def remove_grain_boundary_overlaps(all_positions, all_atom_names, grain_ids, 
                                     n_grains, box_dims, threshold_nm=0.25):
    """
    Remove overlapping molecules at grain boundaries.
    
    Strategy: For each pair of adjacent grains, detect atoms from the
    "newer" grain that overlap with atoms from the "older" grain, 
    then remove whole molecules from the newer grain.
    
    This preserves molecular integrity (never removes partial molecules)
    and handles PBC correctly via cKDTree's boxsize parameter.
    """
    # Build oxygen-only position arrays per grain
    # (Use oxygen positions for overlap detection, not H positions)
    for grain_id in range(n_grains):
        grain_mask = grain_ids == grain_id
        grain_o_positions = all_positions[grain_mask][::atoms_per_molecule]
        # ... detect overlaps with previously-placed grains
        # ... remove whole molecules from current grain
```

**Key insight from slab.py:** QuickIce's slab mode already handles a similar problem — removing water molecules that overlap with ice. The polycrystal grain boundary cleanup is conceptually identical, just applied grain-to-grain instead of phase-to-phase.

**Molecular integrity preservation:** QuickIce's overlap resolver removes whole molecules, never partial molecules. This is critical for hydrate structures where guest molecules must remain intact. Atomsk's `-remove-doubles` removes individual atoms, potentially splitting molecules — QuickIce's approach is strictly better.

**Confidence:** HIGH — the overlap detection and removal code is already written, tested, and proven in QuickIce's production interface generation pipeline.

### Step 5: GRO Export

QuickIce has a mature GROMACS export pipeline that directly produces `.gro` + `.top` + `.itp` files.

**Reusable component: `gromacs_writer.py`**

| Function | Purpose | Reusability |
|----------|---------|-------------|
| `write_gro_file()` | Write Candidate → GRO (ice-only) | ⚠️ Need polycrystal variant |
| `write_interface_gro_file()` | Write InterfaceStructure → GRO | ✅ Pattern to follow |
| `write_multi_molecule_gro_file()` | Write multi-molecule system → GRO | ✅ Best starting point |
| `compute_mw_position()` | TIP4P-ICE MW virtual site | ✅ Direct reuse |
| `wrap_molecules_into_box()` | PBC wrapping | ✅ Direct reuse |
| `wrap_positions_into_box()` | PBC wrapping (fallback) | ✅ Direct reuse |
| `detect_guest_type_from_atoms()` | Guest molecule type detection | ✅ Direct reuse |
| `reorder_guest_atoms()` | Canonical atom ordering | ✅ Direct reuse |
| `write_multi_molecule_top_file()` | Multi-molecule TOP with #include | ✅ Direct reuse |

**For the polycrystal builder, the output structure maps to `InterfaceStructure` or a new `PolycrystalStructure` dataclass** that carries:
- Combined positions from all grains
- Atom names
- Cell matrix
- Molecule index (with grain_id as a per-molecule property)
- Per-grain counts (ice molecules, guest molecules, grain orientation)

**Advantage over atomsk:** Atomsk cannot output GRO format. Any atomsk-based pipeline requires format conversion (LAMMPS `lmp` → MDAnalysis → GRO), which loses residue names and requires molecular connectivity reconstruction. QuickIce's native GRO writer preserves everything.

**Confidence:** HIGH — the export pipeline is complete and functional. A polycrystal variant of `write_interface_gro_file()` is a straightforward extension.

## Advantages Over Atomsk

| Capability | Atomsk `--polycrystal` | Python (this approach) |
|-----------|----------------------|----------------------|
| Multi-phase (sI + sII grains in same system) | ❌ No — single seed only | ✅ Yes — each grain has its own seed type + orientation |
| Multi-seed with different guests | ❌ No | ✅ Yes — grain 1 = sI+CH4, grain 2 = sII+THF, grain 3 = ice Ih |
| GRO format output | ❌ No (only LAMMPS/XYZ/XSF) | ✅ Yes — native GRO + TOP + ITP |
| GenIce2 integration | ⚠️ Format bridge (XYZ → atomsk → LAMMPS → MDAnalysis → GRO) | ✅ Direct Python (GenIce2 → polycrystal builder → GRO writer) |
| PBC support | ✅ Yes (native) | ✅ Yes (image replication, same result) |
| 2D Voronoi (columnar grains) | ✅ Yes (auto-detect) | ✅ Yes (implement same auto-detect) |
| Molecular integrity at boundaries | ❌ `-remove-doubles` removes individual atoms | ✅ Whole-molecule removal via `overlap_resolver.py` |
| Grain boundary density matching | ❌ No | ✅ Can adjust water density at boundaries |
| Performance (1M atoms) | ✅ ~1-5s (compiled Fortran) | ⚠️ ~30-60s (Python, but negligible vs. MD time) |
| Grain auxiliary files | ✅ grain sizes, node positions, COM | ✅ Can generate same files |
| Random + explicit node positions | ✅ Yes | ✅ Yes |
| Lattice-based grain arrangements | ✅ Yes (bcc, fcc, diamond, hcp) | ✅ Yes (trivial to add with numpy) |
| grainID per-atom property | ✅ Yes | ✅ Yes (via grain_ids array from cKDTree) |

## Implementation Estimate

| Component | LOC | Reuses Existing Code | Complexity |
|-----------|-----|---------------------|------------|
| Periodic Voronoi tessellation | ~60 | No (new) | Medium — image replication + vertex wrapping |
| Grain node generation (random/lattice/explicit) | ~40 | Partial (`numpy` for lattice generation) | Low |
| Grain rotation + seed placement | ~50 | Partial (`scipy.spatial.transform.Rotation`) | Low |
| Atom assignment to grains (cKDTree) | ~30 | Yes (pattern from `overlap_resolver.py`) | Low |
| Atom truncation + assembly | ~40 | No (new) | Low |
| Grain boundary overlap removal | ~50 | Yes (`overlap_resolver.py` + `remove_overlapping_molecules`) | Low |
| Guest molecule handling per grain | ~30 | Yes (pattern from `slab.py`) | Medium |
| GRO/TOP export for polycrystal | ~40 | Yes (`write_multi_molecule_gro_file()` pattern) | Low |
| Validation + error handling | ~30 | No (new) | Low |
| **Total** | **~370** | **~55% reusable** | |

**Comparison with atomsk's Fortran95 implementation:** Atomsk's `--polycrystal` mode is likely ~1500+ lines of Fortran95 including all options, error handling, and format I/O. The Python implementation is ~4× shorter because:
1. `scipy.spatial.Voronoi` replaces the Voronoi computation (atomsk uses VORO++ internally)
2. `scipy.spatial.cKDTree` replaces the overlap detection (atomsk uses a hand-coded KD-tree)
3. `scipy.spatial.transform.Rotation` replaces the rotation matrix computation
4. QuickIce's existing export pipeline replaces the format I/O

## Reusable QuickIce Components

### Direct Reuse (no modification needed)

| Component | File | Lines | What it provides |
|-----------|------|-------|-----------------|
| `detect_overlaps()` | `overlap_resolver.py` | 14-85 | PBC-aware cKDTree overlap detection with `boxsize` parameter |
| `remove_overlapping_molecules()` | `overlap_resolver.py` | 88-133 | Whole-molecule removal from positions array |
| `filter_atom_names()` | `overlap_resolver.py` | 136-185 | Synchronize atom names with filtered positions |
| `cKDTree` with `boxsize` | `overlap_resolver.py` | 69-73 | PBC-aware nearest-neighbor queries |
| `compute_mw_position()` | `gromacs_writer.py` | 595-612 | TIP4P-ICE MW virtual site computation |
| `wrap_molecules_into_box()` | `gromacs_writer.py` | 62-135 | Molecule-integrity-preserving PBC wrapping |
| `detect_guest_type_from_atoms()` | `gromacs_writer.py` | 894-944 | Guest molecule type detection |
| `reorder_guest_atoms()` | `gromacs_writer.py` | 153-214 | Canonical atom ordering for .itp compatibility |
| `write_multi_molecule_gro_file()` | `gromacs_writer.py` | 1055-1149 | Multi-molecule GRO export with `MoleculeIndex` |
| `write_multi_molecule_top_file()` | `gromacs_writer.py` | 1152+ | Multi-molecule TOP with #include directives |
| `HydrateStructureGenerator` | `hydrate_generator.py` | 31-127 | GenIce2 Python API for hydrate generation |
| `HydrateStructure.to_candidate()` | `types.py` | 658-722 | Hydrate → Candidate conversion (preserves guests) |
| `Candidate` dataclass | `types.py` | 99-127 | Standard structure container (positions, cell, atom_names) |
| `MoleculeIndex` dataclass | `types.py` | 26-43 | Molecule boundary tracking |
| `HydrateConfig` | `types.py` | 277-327 | Hydrate generation parameters |
| `tile_structure()` | `water_filler.py` | (used in slab.py) | Periodic structure tiling for grain expansion |
| `round_to_periodicity()` | `water_filler.py` | (used in slab.py) | Dimension adjustment for periodic images |

### Pattern Reuse (follow existing patterns)

| Pattern | Source File | Pattern Description | Polycrystal Application |
|---------|------------|--------------------|-----------------------|
| Guest extraction from hydrate | `slab.py` lines 176-200 | Separate water framework from guests before tiling | Extract per-grain guests before rotation, recombine after |
| Guest tiling in ice regions | `slab.py` lines 384-530 | Tile guests separately, shift to layer position | Tile guests per grain, shift to grain position |
| PBC wrapping after shift | `slab.py` lines 296-313 | Wrap whole molecules that exceed box after Z-shift | Wrap molecules at grain boundaries after truncation |
| Guest-water overlap fix | `slab.py` lines 533-564 | Remove water overlapping with guests | Remove grain boundary atoms overlapping with guests |
| Format-specific atom reordering | `gromacs_writer.py` | CH4 atom reorder (H-first → C-first) | Same reordering for guest molecules in polycrystal output |
| Cell dimension rounding | `slab.py` lines 207-244 | Round to ice unit cell periodicity | Round box to grain seed periodicity for clean PBC |

## Performance Estimate

| System Size | N Grains | Atomsk (Fortran95) | Python (scipy + numpy) | Notes |
|------------|----------|--------------------|-----------------------|-------|
| 50K atoms (~500 molecules/grain) | 8 | ~0.5s | ~2-5s | Acceptable; 4-10× slower but negligible vs. MD |
| 200K atoms (~2000 mol/grain) | 16 | ~2s | ~8-20s | Acceptable; MD minimization takes minutes |
| 500K atoms (~5000 mol/grain) | 32 | ~5s | ~20-60s | Acceptable; production MD takes hours |
| 2M atoms (~20K mol/grain) | 64 | ~15s | ~2-5min | May want progress bar; still < MD setup time |

**Breakdown of Python time:**
1. Voronoi tessellation (N_nodes=64, 27×64=1728 points): ~0.01s — negligible
2. GenIce2 generation per grain (N_grains=64): ~5-20s — dominates for many grains with different seeds
3. Grain rotation (numpy matrix multiply): ~0.1s — negligible
4. cKDTree atom assignment (500K atoms): ~0.5s — fast
5. Overlap removal (cKDTree + whole-molecule filtering): ~1-3s — proven in QuickIce
6. GRO writing: ~0.5s — trivial

**Optimization opportunity:** For single-seed polycrystals (all grains same structure), generate the seed ONCE and reuse. This reduces GenIce2 time from O(N_grains) to O(1). This is the common case for homogeneous polycrystals.

**Real-world context:** Polycrystalline hydrate MD simulations in the literature (Sveinsson & Cao 2025, Qu et al. 2025/2026) use 50K-500K atom systems. Even at the high end, 30-60 seconds of structure generation is negligible compared to the 10-100 hours of MD simulation that follows. Performance is a non-issue.

## Existing Python Libraries

| Library | Polycrystal Support | License | In Environment? | Verdict |
|---------|-------------------|---------|----------------|---------|
| **AtomMan** (NIST) | ❌ No — focus on point defects, stacking faults, dislocations, free surfaces. No Voronoi polycrystal generator. | NIST (custom) | No | Not useful for polycrystal |
| **pymatgen** | ⚠️ Partial — has `GrainBoundaryGenerator` (bicrystal grain boundaries, 2 grains only, CSL-based). No Voronoi polycrystal. Also has `Interface` class for heterointerfaces. | MIT | No (but MIT-compatible) | Useful for bicrystal GB, not polycrystal |
| **ASE** | ⚠️ Partial — has `stack()` for heterostructure stacking and `cut()` for surface extraction. No Voronoi polycrystal. | LGPL | No | Not useful for polycrystal |
| **OVITO** | ❌ Analysis only — can analyze grain boundaries but not generate polycrystals | GPL | No | Not useful |
| **nanopolycrystal** | ❌ No such package found | — | — | Does not exist |
| **VORO++** | ✅ Voronoi computation with PBC (C++ library) | BSD | No | Could use via subprocess, but scipy is sufficient |
| **scipy** | ✅ `scipy.spatial.Voronoi` (N-dim, PBC via image replication) + `cKDTree` (PBC-native) + `ConvexHull` + `Rotation` | BSD | ✅ **Yes** | **The right tool for this job** |

**No existing Python library provides Voronoi polycrystal generation.** This is a gap in the Python scientific ecosystem. Building it in QuickIce would be a genuine contribution.

## Risks

| Risk | Likelihood | Impact | Mitigation | Residual Risk |
|------|-----------|--------|-----------|--------------|
| **Periodic Voronoi edge cases** | Medium | High | Test with known crystal systems (BCC Fe, FCC Al) where Voronoi regions are well-characterized; validate grain volumes sum to box volume | Low with testing |
| **Voronoi vertex wrapping errors** | Low | Medium | After image replication, wrap all vertices to `[0, box)`. Check for -1 (infinity) vertices and handle gracefully | Low |
| **Grain near box boundary** | Medium | Medium | Image replication (3×3×3) naturally handles this — the grain's Voronoi region extends correctly across the boundary | Low |
| **Point-in-polyhedron accuracy** | Low | Medium | Use `cKDTree` approach instead (nearest-grain-node assignment) — avoids polyhedron testing entirely | Very Low |
| **Performance for large systems (>1M atoms)** | Medium | Low | Vectorize all numpy operations; use `cKDTree` which is C-optimized; add progress bar for UX; generate seed once for homogeneous polycrystals | Low |
| **Multi-seed density mismatch** | Medium | Medium | When mixing sI and sII grains, box dimensions must accommodate both lattices. Require all seeds to have compatible cross-sections (within 1-2% mismatch) | Medium (user must validate) |
| **Guest molecule integrity at grain boundaries** | Low | High | Use QuickIce's whole-molecule removal (never partial). Verify all guests have correct atom counts after truncation | Low |
| **Rotation of triclinic cells** | Low | Medium | For hydrate lattices (all cubic: sI, sII, sH), rotation is straightforward. If future ice phases (hexagonal) are added, handle fractional coordinate rotation | Low for current scope |

## Multi-Phase Polycrystal: The Killer Feature

Atomsk's single-seed limitation means you cannot create a polycrystal where different grains are different crystal structures. This is the #1 advantage of building our own:

**Scientific use cases for multi-phase polycrystals:**

1. **sI + sII mixed hydrate**: Some grains are structure I (small cages only, e.g., CH4), others are structure II (large cages, e.g., THF). This models realistic natural gas hydrate reservoirs where both structures coexist.

2. **Hydrate + ice polycrystal**: Some grains are ice Ih (water ice), others are sI or sII hydrate. This models the hydrate-ice interface at grain boundaries, relevant for permafrost and glacial hydrate deposits.

3. **Filled-ice + hydrate**: Some grains are filled ice (Ice II with guests), others are conventional hydrate. Models high-pressure hydrate phases.

**Implementation for multi-phase:**

```python
# Each grain specifies its own seed type
grain_specs = [
    {"lattice_type": "sI",  "guest_type": "ch4", "orientation": "random"},
    {"lattice_type": "sI",  "guest_type": "ch4", "orientation": "random"},
    {"lattice_type": "sII", "guest_type": "thf", "orientation": "random"},
    {"lattice_type": "ice_ih", "guest_type": None, "orientation": "random"},
    ...
]

# For each grain, generate its own seed via GenIce2
seeds = {}
for spec in grain_specs:
    key = (spec["lattice_type"], spec["guest_type"])
    if key not in seeds:
        config = HydrateConfig(
            lattice_type=spec["lattice_type"],
            guest_type=spec["guest_type"] or "ch4",
            ...
        )
        hydrate = HydrateStructureGenerator().generate(config)
        seeds[key] = hydrate.to_candidate()
```

**Critical constraint for multi-phase:** When mixing lattices with different unit cell sizes, the box dimensions must accommodate the largest grain's seed. Smaller grains will have their seeds tiled to fill the box dimensions. This is analogous to atomsk's `--merge` lattice mismatch problem, but since we control the tiling, we can ensure density matching.

## Implementation Plan

### Phase 1: Core Voronoi Polycrystal Builder (~200 LOC, ~3-5 days)

```
quickice/structure_generation/modes/polycrystal.py
├── PolycrystalConfig dataclass
│   ├── box_x, box_y, box_z (nm)
│   ├── n_grains (int)
│   ├── grain_arrangement: "random" | "lattice" | "explicit"
│   ├── lattice_type: "sI" | "sII" | "sH" | "ice_ih" | ...  (for homogeneous)
│   ├── guest_type: "ch4" | "thf" | None
│   ├── grain_specs: list[GrainSpec] | None  (for multi-phase)
│   ├── overlap_threshold_nm: float = 0.25
│   └── seed: int
│
├── GrainSpec dataclass  
│   ├── lattice_type: str
│   ├── guest_type: str | None
│   ├── orientation: Rotation | Euler angles | "random"
│   └── position: (3,) nm | None  (for explicit mode)
│
├── PolycrystalStructure dataclass (extends InterfaceStructure pattern)
│   ├── All InterfaceStructure fields
│   ├── grain_ids: np.ndarray  (per-molecule grain assignment)
│   ├── grain_count: int
│   └── grain_info: list[dict]  (orientation, lattice type per grain)
│
├── compute_periodic_voronoi()
├── generate_grain_nodes()  (random, lattice, or explicit)
├── rotate_and_place_grain()  
├── assign_atoms_to_grains()  (cKDTree approach)
├── remove_grain_boundary_overlaps()  
└── assemble_polycrystal()  (main orchestrator)
```

### Phase 2: GenIce2 Multi-Seed Integration (~50 LOC, ~1-2 days)

- Generate different hydrate types per grain
- Handle guest molecule extraction per grain
- Ensure molecular integrity across grain boundaries

### Phase 3: GROMACS Export for Polycrystal (~50 LOC, ~1-2 days)

- Extend `write_multi_molecule_gro_file()` for polycrystal
- Add grain_id to TOP file as comment (for user reference)
- Generate grain size distribution file (matching atomsk's auxiliary output)

### Phase 4: GUI Integration (~100 LOC, ~2-3 days)

- Add "Polycrystal" mode to QuickIce's interface panel
- Grain count slider, arrangement selector, lattice type selector
- Multi-phase option with per-grain type selection
- Visualization of grain boundaries via VTK

## Verdict

**Build it in Python. Do not use atomsk.**

**Rationale:**

1. **All required libraries are already in the environment** — scipy (Voronoi, cKDTree, ConvexHull, Rotation), numpy, GenIce2, and QuickIce's own overlap resolver and GRO writer. No new dependencies needed.

2. **The implementation is tractable** — ~250-300 LOC of non-trivial geometry code, heavily leveraging existing QuickIce components (~55% reusable). The hardest part (periodic Voronoi) is solved by image replication, a well-established technique.

3. **The multi-phase capability is the killer feature** — atomsk cannot create polycrystals with different crystal structures in different grains. This is a genuine scientific need for realistic hydrate simulations. Building our own unlocks this.

4. **No format conversion needed** — GenIce2 Python API → polycrystal builder → GRO writer, all in Python, all in nm, all preserving molecular connectivity and residue names. Atomsk requires GenIce2 → XYZ → atomsk → LAMMPS → MDAnalysis → GRO, losing residue names at every step.

5. **Performance is acceptable** — For typical hydrate polycrystals (50K-500K atoms), 5-30 seconds of generation time is negligible compared to the 10-100+ hours of subsequent MD simulation. Python's slower speed relative to Fortran is irrelevant in this context.

6. **No GPL complications** — All code is MIT/BSD licensed. No subprocess calls to GPL-3.0 atomsk. No format conversion pipeline. Clean intellectual property.

7. **The one managed gap (periodic Voronoi) is well-understood** — Image replication is the standard solution, used in VORO++ and other codes. It adds ~20 LOC and is trivially correct for the grain counts used in hydrate research (2-50 grains).

**When to still consider atomsk:**

If QuickIce users specifically need LAMMPS-format polycrystals AND need atomsk's auxiliary files (grain size distribution, node positions), AND are working with a single homogeneous seed, AND atomsk is already installed, THEN a subprocess fallback to atomsk could be offered as an alternative. But this should be a secondary path, not the primary one.

## Sources

| Source | URL/Reference | Confidence | Used For |
|--------|---------------|------------|----------|
| `scipy.spatial.Voronoi` documentation | https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.Voronoi.html | HIGH | Confirmed N-dimensional Voronoi, no PBC, uses Qhull, `regions` attribute for polyhedra |
| `scipy.spatial.ConvexHull` documentation | https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.ConvexHull.html | HIGH | Confirmed `equations` attribute for half-plane test, convex hull computation |
| `scipy.spatial.cKDTree` | QuickIce codebase `overlap_resolver.py` | HIGH | Confirmed PBC support via `boxsize` parameter, already used in production |
| `scipy.spatial.transform.Rotation` | Training data + scipy docs | HIGH | Euler angles, random rotations, rotation matrix computation |
| AtomMan (NIST) GitHub | https://github.com/usnistgov/atomman | HIGH | No polycrystal generation — confirmed focus on point/line/plane defects |
| pymatgen `pymatgen.core.interface` | https://pymatgen.org/pymatgen.core.interface.html | HIGH | Has `GrainBoundaryGenerator` (bicrystal CSL only) and `Interface` class — NOT Voronoi polycrystal |
| ASE build tools | https://wiki.fysik.dtu.dk/ase/ase/build/tools.html | HIGH | Has `stack()` and `cut()` but NO polycrystal builder |
| Atomsk `--polycrystal` documentation | https://atomsk.univ-lille.fr/doc/en/mode_polycrystal.html | HIGH | Reference implementation behavior, parameter file format, limitations |
| Previous deep dive | `.planning/research/future-ml/complex-hydrate-atomsk/ATOMSK-HYDRATE-DEEPDIVE.md` | HIGH | Atomsk capabilities, hydrate paper citations, format analysis |
| QuickIce source code | `overlap_resolver.py`, `slab.py`, `types.py`, `hydrate_generator.py`, `gromacs_writer.py` | HIGH | Reusable component identification, pattern reuse |
| Sveinsson & Cao (2025) | Phys. Rev. Research 7, L012007 | MEDIUM | Explicit "using ATOMSK" for polycrystalline hydrate; validates the scientific use case |
| VORO++ (Rycroft 2006) | http://math.lbl.gov/voro++/ | MEDIUM | Reference for PBC-aware Voronoi computation; our image-replication approach is simpler but equivalent |
