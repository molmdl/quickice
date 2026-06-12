# Recommended Hydrate Analysis Features for QuickIce

**Domain:** Gas hydrate molecular dynamics simulation analysis
**Created:** 2026-06-12
**Source:** Synthesized from 5-wave research (12 research files in this directory)
**Overall confidence:** HIGH (stack/architecture/pitfalls), MEDIUM (threshold values, cage drift)

---

## Tier 1 — Table Stakes (every hydrate MD paper expects these)

| # | Analysis | What It Measures | Implementation | New Dependency? | Phase |
|---|----------|-----------------|----------------|----------------|-------|
| 1 | **Cage Occupancy** | % of small/large cages filled by guest molecules | ~100-150 lines custom + GenIce2 cage centers + `distance_array` | No | 1 |
| 2 | **RDF (g(r))** | O-O, O-guest radial distribution — most basic structural descriptor | MDAnalysis `InterRDF` — zero custom code | No (MDA already installed) | 1 |
| 3 | **Density Profiles** | 1D density along z-axis — hydrate-liquid boundary, interface width | MDAnalysis `LinearDensity` — minimal custom code | No | 1 |
| 4 | **F4 Order Parameter** | Dihedral-based hydrate-vs-liquid discriminator — appears in nearly every hydrate paper | ~100-150 lines custom: `capped_distance` + `calc_dihedrals` | No | 2 |
| 5 | **F3 Order Parameter** | Three-body angular companion to F4 | ~100-150 lines custom: `capped_distance` + `calc_angles` | No | 2 |
| 6 | **MSD** | Mean squared displacement — guest/water diffusivity, dissociation kinetics | MDAnalysis `EinsteinMSD` — zero custom code | No | 1 |
| 7 | **H-bond Analysis** | Water H-bond network topology, cage stability | MDAnalysis `HydrogenBondAnalysis` — minimal config | No | 1 |
| 8 | **Potential Energy** | Thermodynamic stability from GROMACS .edr | Parse energy file — low custom code | No | 2 |

## Tier 2 — Differentiators (sets QuickIce apart from CLI-only tools)

| # | Analysis | What It Measures | Implementation | New Dependency? | Phase |
|---|----------|-----------------|----------------|----------------|-------|
| 9 | **CHILL+ Classification** | 5-way per-molecule label: clathrate / ice Ih / ice Ic / interfacial / liquid | ~200-300 lines custom + freud `Steinhardt(l=3)` | **Yes: freud-analysis 3.5.0** (~10MB, BSD-3, MIT-compatible) | 3 |
| 10 | **Hydrate Stability Tracking** | Time evolution of % hydrate-like water — core dissociation/nucleation analysis | ~100-150 lines downstream of F4 or CHILL+ | No (uses #4 or #9 output) | 2-3 |
| 11 | **VTK 3D Classified Waters** | Color molecules by order parameter or CHILL+ class in 3D viewer — unique GUI advantage | ~100-200 lines VTK scalar coloring | No | 3-4 |
| 12 | **Pre-simulation Validation** | Verify generated structure quality (cage completeness, occupancy) before expensive MD | ~100-150 lines reusing cage occupancy | No | 1 |

## Tier 3 — Advanced (deferrable, high scientific value)

| # | Analysis | What It Measures | Implementation | New Dependency? | Phase |
|---|----------|-----------------|----------------|----------------|-------|
| 13 | **Guest Residence Time** | How long guests stay in cages — kinetic stability | ~150-200 lines: cage tracker + continuous/intermittent autocorrelation | No | 5 |
| 14 | **Cage Type Time Evolution** | Track cage population changes over simulation | ~150-200 lines per-frame cage occupancy | No | 5 |
| 15 | **Interface Detection** | Hydrate-liquid interface position, width, roughness | ~100 lines with freud `Interface` OR ~300 lines custom tanh-fit | No (if freud from #9) | 6 |
| 16 | **Cage Wireframe VTK** | Render hydrate cages as wireframe in 3D viewer | ~100-200 lines VTK | No | 6 |

---

## Explicitly NOT Building (Anti-Features)

| Anti-Feature | Why Not | Instead |
|-------------|---------|---------|
| Full MD engine (running GROMACS) | Scope creep — QuickIce is generation/analysis, not simulation | Launch GROMACS externally; provide .mdp templates |
| Real-time trajectory streaming | Complex threading, premature for GUI | Batch analysis: load → run → view |
| Free energy / PLUMED / umbrella | Entirely different workflow | Read PLUMED colvar files for simple CV tracking only |
| ML-based classification | Heavy deps (PyTorch), no trained models exist yet | Physics-based F3/F4 and CHILL+ are interpretable + lightweight |
| pytim (interface detection) | **GPL-3.0 incompatible with QuickIce's MIT license** | Use freud `Interface` or re-implement ITIM algorithm from literature |
| Topological cage detection from scratch | ~500-1000 lines, notoriously hard in PBC | Use GenIce2 cage centers (already available, just not captured) |

---

## Key Infrastructure Prerequisite (Phase 1, ~50 lines)

**Capture GenIce2 cage center positions** — currently discarded at `hydrate_generator.py:213`. GenIce2's `GenIce` object exposes `cagepos1` and `cagetype1` after `generate_ice()`. Storing these in `HydrateStructure` eliminates the need for the hardest algorithm (topological cage detection) and reduces cage occupancy to a simple distance-check problem.

## New Dependency Summary

| Package | Version | Size | License | Needed For |
|---------|---------|------|---------|-----------|
| **freud-analysis** | 3.5.0 | ~10MB | BSD-3-Clause (MIT-compatible) | CHILL+ (#9), Interface detection (#15) |

Everything else uses **MDAnalysis 2.10.0** (already installed), **numpy 2.4.3**, **scipy 1.17.1**, and **VTK 9.5.2** — all already in the environment.

---

## Feature Dependencies

```
GenIce2 Cage Data Capture (P0 infrastructure, ~50 lines)
  ├── Cage Occupancy (#1)
  │    ├── Guest Residence Time (#13)
  │    └── Cage Type Time Evolution (#14)
  └── Pre-simulation Validation (#12)

F3/F4 Order Parameters (#4, #5)
  └── Hydrate Stability Tracking — F4 variant (#10)

CHILL+ Classification (#9, requires freud)
  ├── Hydrate Stability Tracking — CHILL+ variant (#10)
  ├── VTK 3D Classified Waters (#11)
  └── Interface Detection via freud (#15)

MDAnalysis Trajectory Loading
  ├── RDF (#2) — InterRDF native
  ├── MSD (#6) — EinsteinMSD native
  ├── H-bond Analysis (#7) — HydrogenBondAnalysis native
  ├── Density Profiles (#3) — LinearDensity native
  ├── F3/F4 per-frame (#4, #5) — custom AnalysisBase
  └── CHILL+ per-frame (#9) — custom AnalysisBase + freud

Density Profile (#3)
  └── Interface Detection — tanh fit (#15)

VTK Rendering
  ├── VTK 3D Classified Waters (#11)
  └── Cage Wireframe VTK (#16)
```

## Suggested Phase Structure

| Phase | Focus | Deliverables | Research Needed? |
|-------|-------|-------------|-------------------|
| 1 | GenIce2 cage capture + basic analysis | Cage centers in HydrateStructure; RDF, density profiles, cage occupancy, MSD, H-bonds | No — reuses existing code patterns |
| 2 | F3/F4 order parameters | Per-molecule F3/F4; stability time series | Yes — threshold calibration per water model |
| 3 | CHILL+ classification + freud | 5-way classification; VTK color-by-class | Yes — freud Steinhardt convention vs paper |
| 4 | Analysis tab GUI + trajectory loading | User-accessible analysis; MDAnalysis Universe creation | No — follows existing MVVM/tab pattern |
| 5 | Advanced time-series | Guest residence time, cage evolution, H-bond persistence | Yes — guest trajectory unwrapping across PBC |
| 6 | Interface detection + VTK polish | Interface position/width; cage wireframes; scalar coloring | Yes — algorithm choice (freud vs custom) |

---

## Critical Pitfalls to Watch

1. **PBC in distance calculations** — always pass `box=u.dimensions` to `capped_distance`; never use raw `np.linalg.norm`
2. **scipy `sph_harm` removed in 1.17.1** — replaced by `sph_harm_y(l, m, theta, phi)` with reversed angle conventions; prefer freud to avoid entirely
3. **Cage center drift during MD** — GenIce2 provides t=0 centers only; must re-center each frame via nearest-water centroid
4. **F3/F4 ≠ Steinhardt q_l** — F3/F4 are tetrahedral angular correlations, CHILL+ uses spherical harmonics bond order; don't confuse them
5. **GUI blocking during long analysis** — CHILL+ at 0.5-2 sec/frame means minutes for trajectories; must use QThread

## Detailed Algorithm References

- **F3/F4 formulas and pseudocode:** `ALGO-F3F4.md`
- **CHILL+ algorithm and classification table:** `ALGO-CHILL.md`
- **Cage detection approaches:** `ALGO-CAGE.md`
- **Time-series methods (stability, residence, density):** `ALGO-TIMESERIES.md`
- **QuickIce codebase readiness (data structures, VTK hooks):** `CODEBASE.md`
- **MDAnalysis-only feasibility per method:** `MDANALYSIS-FEASIBILITY.md`
- **Library comparison (MDA vs MDTraj vs freud vs pytim vs custom):** `COMPARISON.md`

---
*Created: 2026-06-12*
*For milestone planning: use as input to roadmap creation when hydrate analysis milestone is formally started*
