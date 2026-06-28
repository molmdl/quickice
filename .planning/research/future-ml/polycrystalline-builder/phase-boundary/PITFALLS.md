# Domain Pitfalls: Phase Boundary Handling

**Domain:** Polycrystalline ice/hydrate/water builder — phase boundary physics
**Researched:** 2026-06-28

## Critical Pitfalls

Mistakes that cause rewrites, MD simulation crashes, or unphysical results.

### Pitfall 1: Direct Lattice Stitching Between Incompatible Phases

**What goes wrong:** Attempting to tile Ice Ih and Ice II unit cells directly at a boundary, hoping that atomic positions will "line up." They won't. Ice Ih has hexagonal symmetry (a=4.52Å, c=7.36Å, space group P6₃/mmc) while Ice II has rhombohedral symmetry (a=rhombohedral setting, ~12.96Å, space group R-3). The oxygen positions in one phase have NO periodic correspondence to positions in the other.

**Why it happens:** Intuition from metals, where fcc↔fcc grain boundaries share a common lattice type with different orientations. In metals, rotating a grain creates a valid GB. In ice, different phases have completely different lattices.

**Consequences:** Massive steric clashes (O-O distances < 0.1 nm), GROMACS energy minimization diverges (EM step 0 already has F_max > 10⁶ kJ/mol/nm), resulting structure has no physical meaning.

**Prevention:** ALWAYS insert a disordered buffer zone (1–2 nm water layer) between grains of incompatible phases. This is the standard approach in every polycrystalline MD paper that handles multi-phase systems.

**Detection:** After structure generation, check for any O-O distances < 0.18 nm (severely overlapping molecules). If found, the boundary handling failed.

**Confidence:** HIGH — Nguyen et al. 2015 proved no lattice matching exists between ice and clathrate; this extends to all ice polymorph pairs with different Bravais lattices.

---

### Pitfall 2: Density Mismatch Creates Voids at Boundaries

**What goes wrong:** Placing Ice Ih (0.917 g/cm³) adjacent to Ice II (1.18 g/cm³) in a box sized for Ice Ih. The Ice II grain has ~28% more molecules per volume. When the Ice II grain is tiled to fill its Voronoi cell (sized for Ice Ih density), it either overflows (overlap with neighbors) or leaves voids (if truncated to fit).

**Why it happens:** The Voronoi cell volume is determined by the overall box and grain layout, not by the individual phase densities. Two adjacent grains of different density CANNOT both fill their Voronoi cells exactly.

**Consequences:** Voids → cavitation during MD → water vapor nucleation → unphysical behavior. Overlaps → steric crashes → GROMACS EM diverges.

**Prevention:** Two strategies (implement BOTH):
1. **Buffer zone approach**: Insert disordered water between grains. The buffer zone absorbs the density mismatch because liquid water is intermediate in density (0.997 g/cm³) between most ice phases.
2. **Box dimension strategy**: Size the overall box to the WEIGHTED AVERAGE density of all phases present. Each grain is tiled to its own density within the box. Some grain boundaries will have small gaps — these are acceptable if < 0.3 nm (hydrogen bond distance), and MD will close them during equilibration.

**Detection:** After generation, compute the total mass vs. box volume. If the average density deviates > 5% from the expected weighted average, there's a problem.

**Confidence:** MEDIUM-HIGH — Physical reasoning is solid; the specific algorithm (weighted-average box density) is standard practice but hasn't been tested on ice polymorphs specifically.

---

### Pitfall 3: Grain Too Small Loses Crystal Identity During MD

**What goes wrong:** A grain containing only 50 water molecules of Ice Ih (well below the minimum ~300 molecules = 2×2×2 unit cells). During energy minimization or NVT equilibration, the entire grain melts or transforms to a different structure because it doesn't have enough periodic images to stabilize the crystal.

**Why it happens:** Crystalline phases are stabilized by long-range order. A small cluster of water molecules in Ice Ih arrangement at ambient pressure will spontaneously transform to liquid or to a stacking-faulted structure within ~100 ps of MD, because the surface-to-volume ratio is too high and the grain boundary energy dominates.

**Consequences:** User places a small Ice II grain next to Ice Ih. During MD, the Ice II grain melts. The user doesn't get the structure they requested. This is NOT a QuickIce bug but a physics limitation — and the user needs to be warned.

**Prevention:** Set per-phase minimum grain sizes and validate before generation:
- Ice Ih: ≥ 2×2×2 unit cells = 9.0×9.0×14.7 Å ≈ 288 molecules (HARD MINIMUM)
- Ice Ih: ≥ 3×3×3 unit cells = 13.5×13.5×22.1 Å ≈ 972 molecules (RECOMMENDED)
- Ice II: ≥ 1 unit cell ≈ 312 molecules (HARD MINIMUM)
- Ice III: ≥ 1 unit cell ≈ 324 molecules (HARD MINIMUM)
- Ice V: ≥ 1 unit cell ≈ 336 molecules (28 molecules per monoclinic unit cell × 12)
- Ice VI: ≥ 1 unit cell ≈ 600 molecules
- sI hydrate: ≥ 1 unit cell ≈ 46 water + 8 guest = 54 molecules min (HARD MINIMUM for framework; guests may vary)
- sII hydrate: ≥ 1 unit cell ≈ 136 water + 24 guest = 160 molecules min
- Liquid water: ≥ 100 molecules (arbitrary but reasonable for bulk-like behavior)

**Detection:** Compute grain volume from Voronoi cell → multiply by phase density → get molecule count → compare to minimum. Warn if below recommended, error if below hard minimum.

**Confidence:** MEDIUM — The specific minimum numbers are estimates based on unit cell sizes. No systematic MD study of "minimum grain size for ice" was found. The recommended minimums (3×3×3 for Ice Ih) are conservative based on typical MD practice.

---

### Pitfall 4: Phase Instability at Boundary Conditions

**What goes wrong:** User places Ice Ih at (T=250K, P=300 MPa), which is inside the Ice II stability region. During MD, the Ice Ih grain spontaneously transforms to Ice II. The user's intended Ice Ih + Ice II polycrystal becomes Ice II + Ice II = useless.

**Why it happens:** The TIP4P-ICE model reproduces the water phase diagram, including which phase is stable at each (T,P). If you place a metastable phase in conditions where another phase is thermodynamically favored, the simulation will eventually transform. This is physics, not a bug.

**Consequences:** User doesn't get the structure they intended. Waste of MD time.

**Prevention:** Check each grain's phase stability using `lookup_phase(T, P)` from `quickice.phase_mapping.lookup`. If the grain's assigned phase differs from the thermodynamically stable phase at (T,P):
1. **WARN** the user: "Ice Ih at (250K, 300 MPa) is in the Ice II stability region. The Ice Ih grain may transform to Ice II during MD."
2. **Do NOT block** generation — some users intentionally study metastable structures or phase transformation kinetics.
3. **Suggest** the stable phase: "Consider using Ice II at these conditions instead."

**Detection:** After the user specifies (T, P) for the system, run `lookup_phase(T, P)` for each grain's assigned phase. Compare to actual phase assignment.

**Confidence:** HIGH — QuickIce already has the phase lookup infrastructure (`solid_boundaries.py`, `lookup.py`). The TIP4P-ICE model's phase diagram is well-characterized (Abascal & Vega 2005).

---

### Pitfall 5: Shapely PBC Violation

**What goes wrong:** User draws a polygon that crosses x=0 (PBC boundary). Shapely treats this as a polygon extending to negative coordinates. When the polygon is used to define a grain region, the part near x=0 is fine but the "wrapped" part (near x=Lx) is missing. The grain is incomplete.

**Why it happens:** Shapely operates in Euclidean 2D space with no concept of periodicity. A polygon with vertices at (−0.5, 0), (0.5, 0), (0.5, 5), (−0.5, 5) is valid in shapely but represents a shape that wraps from x=Lx−0.5 to x=0.5 in PBC space.

**Consequences:** Grain missing part of its region → unphysical structure → MD artifacts.

**Prevention:** In v7.0, **constrain all user-drawn shapes to stay within [0, Lx) × [0, Ly)**. Reject any polygon with vertices outside this range. This is simpler, less error-prone, and sufficient for most use cases.

For future (v8.0+): implement PBC-aware shape handling:
1. If a polygon crosses a box edge, split it into two polygons: the "main" part (in [0, Lx)) and the "wrapped" part (shifted by +Lx or +Ly)
2. Merge the wrapped part into the grain definition as a separate polygon
3. This requires careful handling at corners (shapes crossing both x and y boundaries)

**Detection:** After polygon creation, check all vertex coordinates. If any < 0 or ≥ Lx/Ly, the shape violates PBC constraints.

**Confidence:** HIGH — This is geometric reasoning, not physics. shapely documentation confirms no PBC support.

---

### Pitfall 6: Guest Molecule Escape at Hydrate Boundaries

**What goes wrong:** A hydrate grain (sI with CH₄ guests) is placed adjacent to an Ice Ih grain with a buffer zone. During MD equilibration, some guest molecules escape through the disordered buffer into the ice region or the vacuum of a nearby void. The hydrate becomes partially empty, which destabilizes the clathrate framework.

**Why it happens:** The disordered water buffer zone near a hydrate surface has incomplete cage structures. Guest molecules near the hydrate-buffer boundary can diffuse through the partially-formed cages into the buffer, then into adjacent phases.

**Consequences:** Hydrate dissociation during equilibration → framework collapse → the hydrate grain becomes amorphous ice. User doesn't get the hydrate-containing structure they requested.

**Prevention:** Three strategies (ranked by reliability):
1. **Thick buffer zone** (2 nm instead of 1 nm): Gives guest molecules more disordered water to diffuse through before reaching another crystalline phase. Increases the "escape distance."
2. **Position restraints on guest molecules during minimization/equilibration**: In GROMACS, add `position_restraints = yes` for guest atoms during the first 100 ps of NVT. This prevents guest escape while the boundary equilibrates. User must remove restraints for production MD.
3. **Place hydrate grains away from incompatible-phase boundaries**: If a hydrate grain is surrounded by liquid water (compatible boundary), guest escape is less likely than if surrounded by ice (which creates a harder boundary).

**Detection:** After energy minimization, count guest molecules still in hydrate cages. If significant loss (>10%), warn user.

**Confidence:** MEDIUM — Naeiji et al. 2019 showed ice shells can stabilize hydrates during dissociation. Guest escape through disordered regions is physically expected but the rate depends on many factors. This needs empirical validation.

---

## Moderate Pitfalls

Mistakes that cause delays, suboptimal structures, or confusing user experiences.

### Pitfall 7: Triclinic Cell Handling in Polycrystalline Box

**What goes wrong:** Ice II, III, V have triclinic unit cells. When tiling these into an orthorhombic simulation box, the cell vectors don't align with the box axes. If QuickIce tries to force triclinic cell positions into an orthorhombic box, atoms end up outside [0, Lx) × [0, Ly) × [0, Lz).

**Prevention:** Use `get_cell_extent()` (already exists in `cell_utils.py`) for bounding-box calculations. For tiling, transform triclinic positions to the orthorhombic box using fractional coordinates: `positions_orth = positions_frac @ cell_matrix_orth`. QuickIce's existing slab mode already handles triclinic cells for tiling.

**Confidence:** HIGH — QuickIce already handles this in the existing interface modes.

---

### Pitfall 8: GROMACS Energy Minimization Non-Convergence for Multi-Phase Systems

**What goes wrong:** User generates a multi-phase polycrystal (Ice Ih + Ice II + liquid) and runs `gmx grompp` + `gmx mdrun -defflm em`. The energy minimization reaches the step limit (50000) without converging to F_max < 1000 kJ/mol/nm. The user thinks the structure is broken.

**Why it happens:** Multi-phase boundaries have inherently higher energy than single-phase crystals. The steepest descent algorithm may get stuck in a local minimum near a grain boundary where some atoms have residual strain. This is normal for polycrystalline starting structures.

**Prevention:** 
1. QuickIce should export a `.mdp` file with recommended minimization settings for polycrystalline structures: `emtol = 1000` (relaxed from the default 100), `nsteps = 100000` (increased from default 50000), `emstep = 0.01` (smaller step for stability).
2. Warn users: "Polycrystalline structures may require extended energy minimization (100K+ steps). This is normal."
3. Suggest a two-stage minimization: steepest descent (rough) → conjugate gradient (refined).

**Confidence:** MEDIUM — Standard MD practice; specific convergence criteria for ice polycrystals haven't been benchmarked.

---

### Pitfall 9: Voronoi Tessellation Artifacts at Box Corners

**What goes wrong:** A standard 3D Voronoi tessellation places seed points in [0, Lx) × [0, Ly) × [0, Lz). Grains near the box boundary get cut off because the Voronoi cell extends beyond the box. With PBC, these should wrap, but scipy.spatial.Voronoi doesn't support PBC.

**Why it happens:** scipy's Voronoi tessellation operates in infinite space. For periodic boundaries, you need to replicate the seed points across all 26 neighboring images and then clip the result to the original box.

**Prevention:** Use the standard PBC-Voronoi approach:
1. Replicate seed points in all 27 boxes (original + 26 periodic images)
2. Run Voronoi tessellation on the 27×N seed points
3. Clip resulting Voronoi cells to the original box [0, Lx) × [0, Ly) × [0, Lz)
4. Assign each grain's atoms from the original (non-replicated) seeds only

This is well-documented in Atomsk's polycrystal mode and in Davies et al. 2025.

**Detection:** After tessellation, verify that all Voronoi cells are fully contained within the box. If any cell extends beyond, the PBC handling is wrong.

**Confidence:** HIGH — This is a well-known algorithmic issue with a standard solution. Atomsk implements it correctly.

---

### Pitfall 10: TIP4P-ICE Virtual Site (MW) Overlap at Boundaries

**What goes wrong:** QuickIce uses TIP4P-ICE water model with 4 atoms per molecule (OW, HW1, HW2, MW). The MW (massless virtual site) position is computed from OW, HW1, HW2 positions. When overlap removal deletes water molecules at a boundary, it removes all 4 atoms (including MW). But when checking for overlaps, only OW positions are compared (by design — the overlap_resolver.py checks O-O distances). If two MW atoms from different molecules are at the same position, it doesn't matter because MW has no LJ interactions.

**Prevention:** This is actually handled correctly by the existing code — `overlap_resolver.py` operates on oxygen positions only and removes entire molecules (all 4 atoms). No change needed. BUT: document this clearly in the polycrystalline builder code so future developers don't try to "fix" it by checking MW overlaps.

**Confidence:** HIGH — Existing code behavior is correct. This is a documentation pitfall, not a code pitfall.

---

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 11: Overlap Threshold Too Aggressive

**What goes wrong:** Using overlap_threshold = 0.25 nm (2.5 Å, QuickIce's default for ice-water interfaces) for grain boundaries between same-phase grains removes too many molecules. The O-O distance in ice is 2.75 Å, so a threshold of 2.5 Å catches almost every molecule at the boundary. This creates an excessively wide grain boundary gap.

**Prevention:** For same-phase grain boundaries (where both grains have identical lattice parameters), use a smaller overlap threshold: 0.20 nm (2.0 Å). This removes only molecules that are seriously overlapping (< 2.0 Å O-O distance) while preserving molecules that are at the correct ice spacing (2.75 Å) but slightly displaced.

**Confidence:** MEDIUM — The 0.25 nm threshold was calibrated for ice-water interfaces (where water is ~2.8 Å spacing). For grain boundaries, a slightly lower threshold is appropriate.

---

### Pitfall 12: GenIce2 Default Orientation Not Documented

**What goes wrong:** When generating Ice Ih with GenIce2, the default crystal orientation places the c-axis along Z. When the user assigns "random orientation" to grains, some grains will have c-axis along X or Y. This is correct physics, but the user may not realize that the grain boundary structure depends on whether the boundary is parallel or perpendicular to the c-axis (basal vs prismatic boundary).

**Prevention:** Document that:
- Ice Ih c-axis default = Z
- "Random orientation" means random rotation of the entire unit cell
- Basal-plane grain boundaries (c-axis perpendicular to GB plane) are structurally different from prismatic-plane GBs (c-axis parallel to GB plane)
- Users who want specific GB types should use "crystal face orientation control" (deferred feature)

**Confidence:** HIGH — Basic crystallography knowledge; confirmed by GenIce2 behavior.

---

### Pitfall 13: User Draws Overlapping Grain Shapes

**What goes wrong:** In the GUI, user draws two grain regions that overlap. Both regions get assigned different phases (e.g., Ice Ih and Ice II). The overlapping region is ambiguous — which phase wins?

**Prevention:** Two approaches:
1. **Strict (v7.0):** Reject any overlapping shapes. Require non-overlapping regions that exactly tile the box.
2. **Priority-based (v7.5+):** Later-drawn shapes override earlier shapes. The "top" shape wins in the overlapping region. This is intuitive for drawing but requires careful implementation.

**Confidence:** HIGH — Standard GUI design decision.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Same-phase polycrystal (v7.0) | Voronoi PBC handling (Pitfall 9) | Replicate seeds in 27 boxes before tessellation |
| Same-phase polycrystal (v7.0) | Overlap threshold calibration (Pitfall 11) | Use 0.20 nm for same-phase GBs |
| Multi-phase polycrystal (v8.0) | Direct lattice stitching (Pitfall 1) | Always insert buffer zone between incompatible phases |
| Multi-phase polycrystal (v8.0) | Density mismatch voids (Pitfall 2) | Weighted-average box density + buffer zones |
| Multi-phase polycrystal (v8.0) | Phase instability warning (Pitfall 4) | Use existing `lookup_phase()` to check stability |
| Hydrate polycrystal (v8.0) | Guest escape at boundaries (Pitfall 6) | Position restraints during equilibration; thick buffer zones |
| Hydrate polycrystal (v8.0) | GROMACS multi-moleculetype export | MoleculetypeRegistry already handles `_H` suffix; extend for multi-grain |
| GUI shape drawing (v7.0+) | PBC violation (Pitfall 5) | Constrain shapes to box bounds; reject out-of-bounds |
| GUI shape drawing (v7.0+) | Overlapping shapes (Pitfall 13) | Reject overlaps initially; add priority-based resolution later |
| Energy minimization | Non-convergence (Pitfall 8) | Export recommended .mdp settings; warn about extended minimization |
| Triclinic phases (Ice II, III, V) | Cell transformation (Pitfall 7) | Reuse existing `get_cell_extent()` + `round_to_periodicity()` |

## Sources

- See SUMMARY.md for complete reference list
- QuickIce codebase: `overlap_resolver.py`, `cell_utils.py`, `water_filler.py`, `gromacs_writer.py`, `lookup.py`
- Atomsk documentation (atomsk.univ-lille.fr) — polycrystal mode algorithm
