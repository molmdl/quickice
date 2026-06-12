# Domain Pitfalls: Hydrate Analysis

**Domain:** Gas hydrate molecular dynamics simulation analysis
**Researched:** 2026-06-12
**Context:** Adding analysis capabilities to QuickIce

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Ignoring Periodic Boundary Conditions

**What goes wrong:** Distance calculations, neighbor finding, and molecular reconstruction produce incorrect results because atoms near box boundaries appear far from their periodic images.
**Why it happens:** PBC is non-intuitive. The minimum image convention requires explicit handling. Raw positions from .xtc files may have molecules split across boundaries.
**Consequences:**
- RDF artifacts: g(r) drops to zero near r_max instead of approaching 1
- F3/F4 wrong: Missing neighbors lead to incorrect order parameters
- Cage detection fails: Incomplete H-bond network at boundaries
- MSD wrong: Particles appear to "jump" across box, giving nonsensical diffusion coefficients
**Prevention:**
- Always pass `box=u.dimensions` to distance functions
- Use `MDAnalysis.lib.distances.capped_distance()` with `box` parameter
- Use `atomgroup.unwrap()` or `NoJump` transformation for MSD
- Use `atomgroup.make_whole()` before computing molecular properties
**Detection:** g(r) drops to 0 near r_max; MSD shows unphysical jumps; some water molecules have < 4 neighbors.

### Pitfall 2: scipy sph_harm → sph_harm_y API Change

**What goes wrong:** CHILL+ implementation calls `scipy.special.sph_harm(m, l, phi, theta)` — which is **removed** in scipy 1.17.1. Even if someone works around the removal, using the old argument order with `sph_harm_y` produces wrong results because the angle conventions are reversed.
**Why it happens:** scipy changed the API in version 1.12+. `sph_harm(m, l, phi, theta)` → `sph_harm_y(l, m, theta, phi)`. The argument order is swapped AND the meaning of theta/phi is reversed (old: theta=azimuthal, phi=polar; new: theta=polar, phi=azimuthal).
**Consequences:**
- Import fails if using old `sph_harm` name
- If using `sph_harm_y` with old argument order: wrong spherical harmonic values
- CHILL+ bond correlation c(i,j) sign flips, swapping staggered/eclipsed classification
- All molecules classified incorrectly — hydrate appears as liquid and vice versa
**Prevention:**
- Use `sph_harm_y(l, m, theta, phi)` where theta is polar (colatitude) and phi is azimuthal
- Better: use freud `Steinhardt(l=3)` which handles spherical harmonics internally
- Write a wrapper function with clear parameter names:
  ```python
  def compute_qlm(l, m, bond_vector):
      """Compute Y_lm for a bond vector. theta=polar, phi=azimuthal."""
      r = np.linalg.norm(bond_vector)
      theta = np.arccos(bond_vector[2] / (r + 1e-10))  # polar angle
      phi = np.arctan2(bond_vector[1], bond_vector[0])  # azimuthal angle
      return sph_harm_y(l, m, theta, phi)
  ```
**Detection:** CHILL+ classification gives >90% liquid on a known hydrate structure; c(i,j) values have wrong sign distribution.

### Pitfall 3: Confusing F3/F4 with Steinhardt Order Parameters

**What goes wrong:** Using freud's `Steinhardt(l=6)` q₆ as a substitute for F4 tetrahedral order parameter. These measure fundamentally different things.
**Why it happens:** Both are "order parameters for water" and both relate to tetrahedral structure. But F3/F4 are specific tetrahedral angular correlations designed for water, while Steinhardt q_l are spherical harmonics-based crystal order parameters.
**Consequences:**
- F4 values don't match literature: F4(clathrate) ≈ -0.04 to +0.8, q₆ has different scale entirely
- Comparison with published results is impossible
- Classification thresholds are wrong
**Prevention:**
- Implement F3/F4 explicitly — they are well-defined formulas, not available in any library
- Use Steinhardt q_l **only** for CHILL+ algorithm (which does use q₃/q₆ as intermediate), but don't confuse it with F4
- Document clearly which order parameter you're computing
**Detection:** Order parameter values don't match published ranges. Hydrate and liquid give similar values.

### Pitfall 4: Wrong Trajectory Wrapping for Slab Systems

**What goes wrong:** Hydrate simulations are often slab systems (hydrate|liquid|hydrate with vacuum gaps). Standard wrapping puts all molecules inside the box, destroying the slab structure.
**Why it happens:** GROMACS trajectory files may or may not be wrapped. MDAnalysis reads positions as-is from the trajectory.
**Consequences:**
- Density profiles show atoms at box edges instead of continuous distributions
- Interface detection fails because the interface is at the box boundary
- Visualization shows atoms "leaking" out of the hydrate region
**Prevention:**
- Detect slab geometry: check if box has vacuum gap (density near 0 in some z range)
- Apply `NoJump` transformation to maintain continuous trajectories
- Center the slab before analysis: translate so the hydrate center is at box center
- For density profiles, wrap water into the hydrate/liquid region using `wrap()`
**Detection:** Z-density profile shows atom pile-up at z=0 or z=Lz; VTK visualization shows atoms at unexpected positions.

### Pitfall 5: Memory Exhaustion from Large Trajectories

**What goes wrong:** Loading an entire trajectory into RAM crashes the application or makes it unusable.
**Why it happens:** `u.trajectory.timeseries()` in MDAnalysis loads ALL frames. A 100K-atom, 50K-frame trajectory needs ~120 GB for positions alone.
**Consequences:** Application crashes with OOM; system becomes unresponsive due to swapping.
**Prevention:**
- ALWAYS iterate frame-by-frame through `u.trajectory`
- NEVER call `.timeseries()` on large trajectories
- Use `stride` parameter to skip frames: `u.trajectory[::10]`
- Implement progress callback so users can see progress
**Detection:** Memory usage grows linearly during analysis; system swap increases.

## Moderate Pitfalls

Mistakes that cause delays or technical debt.

### Pitfall 6: Incorrect H-bond Criteria for Hydrate Water

**What goes wrong:** Using protein-oriented H-bond criteria (O-O distance < 3.5 Å, O-H...O angle > 150°) that miss many hydrate H-bonds.
**Why it happens:** MDAnalysis `HydrogenBondAnalysis` defaults to protein-oriented criteria. Hydrate water H-bonds often have wider angle distributions (especially at interfaces and in strained cages).
**Consequences:** Cage detection fails; CHILL+ classification misclassifies hydrate water as liquid; H-bond lifetimes underestimated.
**Prevention:** Use hydrate-appropriate criteria: O-O < 3.5 Å, O-H...O angle > 120° (not 150°). Validate against known hydrate structure (sI hydrate should have exactly 4 H-bonds per water). Make criteria configurable.
**Detection:** Average coordination < 4 in hydrate region; cage detection finds too few cages.

### Pitfall 7: Cage Center Drift During MD

**What goes wrong:** GenIce2 provides cage centers at t=0. During MD, the hydrate lattice deforms, and cage centers shift. Using t=0 centers on frame 1000 gives wrong occupancy.
**Why it happens:** Hydrate lattices are not rigid — thermal fluctuations, pressure effects, and dissociation all shift cage positions.
**Consequences:** Guests appear to "escape" cages when they haven't (center moved away from guest); occupancy drops artificially; residence time is underestimated.
**Prevention:** Re-center each cage every frame by computing the centroid of the nearest ~20-24 water molecules. Use KDTree for efficient nearest-neighbor lookup. For dissociated cages, switch to CHILL+ classification instead.
**Detection:** Occupancy fraction drops monotonically even for stable hydrate; cage center positions diverge from water molecule centroids.

### Pitfall 8: .tpr Version Incompatibility

**What goes wrong:** MDAnalysis .tpr reader doesn't support the user's GROMACS version.
**Prevention:** Check MDAnalysis release notes for .tpr support. Recommend MDAnalysis ≥ 2.9.0 for GROMACS 2024+. Provide fallback: user can convert .tpr to .gro + .top using `gmx editconf`.

### Pitfall 9: Not Handling GROMACS Virtual Sites (TIP4P)

**What goes wrong:** TIP4P water models have a virtual site (M atom) in addition to O and two H. Analysis that counts all atoms gets wrong results. Atom selection `"name OW"` may not find the oxygen in TIP4P-ICE models where it's named `O`.
**Prevention:** Use residue-based selection (`resname SOL`) rather than atom-name selection when possible. Document which water models are supported. Test with TIP4P, TIP4P/ICE, and TIP3P.

### Pitfall 10: Blocking GUI During Long Analysis

**What goes wrong:** Running trajectory analysis on the main thread freezes the PySide6 GUI for minutes.
**Prevention:** Always use QThread for analysis. Provide progress bar with frame counter. Add cancel button that stops the analysis loop.

### Pitfall 11: GenIce2 sH Lattice Uses Different Cage API

**What goes wrong:** sI and sII lattice modules use `self.cagepos, self.cagetype = parse_cages(...)` but sH uses the deprecated `self.cages` string attribute. Code that accesses `cagepos` on an sH lattice will fail.
**Prevention:** Check for both attributes. Use `hasattr(lattice, 'cagepos')` vs `hasattr(lattice, 'cages')`. Parse `cages` string format for sH if needed.
**Detection:** AttributeError when trying to access `cagepos` on sH lattice.

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 12: GROMACS Unit Confusion

**What goes wrong:** GROMACS uses nanometers for coordinates in .gro/.xtc/.trr but angstroms in .pdb. MDAnalysis normalizes to angstroms internally.
**Prevention:** MDAnalysis handles this automatically. Be careful when passing raw positions to other tools. Check units before computing distances.

### Pitfall 13: Not Saving Analysis Results

**What goes wrong:** User runs 30-minute analysis, then closes the window. All results are lost.
**Prevention:** Auto-save results to .csv/.xvg after each analysis. Provide "Save Results" button. Cache results in memory for re-display.

### Pitfall 14: EinsteinMSD Not MSD

**What goes wrong:** Trying to import `MDAnalysis.analysis.msd.MSD` — the class is actually `EinsteinMSD`.
**Prevention:** Use `from MDAnalysis.analysis.msd import EinsteinMSD`. Document this common mistake.

### Pitfall 15: CHILL+ ~2-3% False Positive Rate

**What goes wrong:** CHILL+ classifies ~2-3% of liquid water molecules as "clathrate" even in pure liquid. This is a known limitation.
**Prevention:** Filter by cluster size — use the largest cluster of 4E (4 eclipsed bonds) molecules for clathrate identification. Single "clathrate" molecules surrounded by liquid are likely false positives.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Cage data capture (P1) | sH lattice uses `cages` not `cagepos` | Check both attributes; parse string format for sH |
| RDF analysis (P1) | PBC artifacts near r_max | Use r_max < 0.5 × min(Lx, Ly, Lz); check g(r)→1 at large r |
| F3/F4 implementation (P2) | Confusing with Steinhardt qₗ; wrong thresholds | Implement from published formulas; calibrate per water model |
| CHILL+ classification (P3) | `sph_harm_y` angle convention; qₗₘ normalization | Use freud Steinhardt or wrapper with clear param names; verify c(i,j) signs |
| Slab density profiles (P2) | Wrapping destroys structure | Detect vacuum gap; center slab; use NoJump before binning |
| GUI integration (P4) | Blocking main thread | Use QThread with progress signals; add cancel button |
| Residence time (P5) | Guest trajectory unwrapping across PBC | Use NoJump transformation; validate with known diffusion |
| VTK visualization (P6) | Atoms at box boundaries | Wrap/unwrap correctly; apply same transformations as analysis |
| Large trajectory (all) | Memory exhaustion | Never use timeseries(); iterate frame-by-frame; use stride |

## Sources

- MDAnalysis PBC documentation: https://docs.mdanalysis.org/stable/ (HIGH confidence)
- MDAnalysis HydrogenBondAnalysis: https://docs.mdanalysis.org/ (HIGH confidence)
- scipy sph_harm_y migration: Verified in QuickIce environment (HIGH confidence)
- F3/F4 vs. Steinhardt distinction: Well-established in water physics literature (HIGH confidence)
- GROMACS trajectory wrapping behavior: GROMACS manual (HIGH confidence)
- TIP4P virtual site handling: GROMACS water model specifications (HIGH confidence)
- CHILL+ false positive rate: Nguyen & Molinero (2015) JPCB (HIGH confidence)
- H-bond criteria for hydrate: Community knowledge (MEDIUM confidence — values vary between groups)
- Cage center drift: Inferred from MD physics (MEDIUM confidence — needs trajectory validation)
