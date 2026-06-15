# Feature Landscape: Hydrate Analysis

**Domain:** Gas hydrate molecular dynamics simulation analysis
**Researched:** 2026-06-12
**Context:** QuickIce (v4.5+) — PySide6/VTK GUI for GROMACS hydrate structure generation, adding analysis capabilities

## Table Stakes

Features hydrate MD researchers expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | MDAnalysis Support | Custom Code Needed | Algorithm Ref |
|---------|--------------|------------|-------------------|-------------------|---------------|
| Cage occupancy calculation | Core hydrate property; every hydrate paper reports this | Medium (with GenIce2 cage centers) | `distance_array` for guest-to-cage check | ~100-150 lines: cage center extraction, distance cutoff, per-type counting | ALGO-CAGE.md |
| F4 order parameter | Standard hydrate-vs-liquid discriminator; appears in nearly every hydrate MD paper | Medium | `capped_distance` (neighbors), `calc_dihedrals` (O-O-O-O) | ~100-150 lines: neighbor aggregation, dihedral selection, classification | ALGO-F3F4.md |
| F3 order parameter | Companion to F4; three-body angular distribution | Medium | `capped_distance` (neighbors), `calc_angles` (O-O-O) | ~100-150 lines: angle computation, product formula | ALGO-F3F4.md |
| RDF (g(r)) | Most fundamental structural descriptor | Low | `InterRDF` (native) | None — just call `InterRDF(ag1, ag2).run()` | — |
| Density profiles | Interface structure, hydrate-liquid boundary | Low | `LinearDensity` (native, 1D) | Minimal: select z-axis, call `run()` | ALGO-TIMESERIES.md |
| Potential energy monitoring | Thermodynamic stability assessment | Low | None (parse .edr) | Low: read GROMACS energy file | — |
| MSD | Guest/water diffusivity, dissociation kinetics | Medium | `EinsteinMSD` (native) | None — just call `EinsteinMSD(ag).run()` | — |
| Hydrogen bond analysis | Network topology, hydrate cage stability | Medium | `HydrogenBondAnalysis` (native) | Minimal: configure selection strings, call `run()` | — |

## Differentiators

Features that set QuickIce apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | freud Helps? | Custom Code Needed | Algorithm Ref |
|---------|-------------------|------------|-------------|-------------------|---------------|
| CHILL+ water classification | Automatic 5-way classification: clathrate vs. ice Ih vs. ice Ic vs. interfacial vs. liquid | High | **Yes**: `Steinhardt(l=3)` for q₃ (core of CHILL+) — ~10-50x faster than scipy loops | ~200-300 lines: bond correlation c(i,j), classification rules, interfacial detection | ALGO-CHILL.md |
| Hydrate stability/dissociation tracking | Time evolution of hydrate phase fraction — core analysis for dissociation studies | Medium | No (downstream consumer) | ~100-150 lines: frame-by-frame CHILL+/F4 counting, time series | ALGO-TIMESERIES.md |
| Cage type time evolution | Track how cage populations change over simulation | High | No | ~150-200 lines: frame-by-frame cage occupancy + cage integrity tracking | ALGO-TIMESERIES.md |
| Guest residence time | How long guests stay in cages; kinetic stability measure | High | No | ~150-200 lines: occupancy timeline, continuous/intermittent correlation | ALGO-TIMESERIES.md |
| VTK-based 3D visualization of classified waters | See hydrate/liquid/ice regions in 3D with VTK — unique advantage over CLI tools | Medium | No | ~100-200 lines: color transfer function, per-molecule scalar array | CODEBASE.md |
| Pre-simulation structure validation | Verify generated hydrate structure quality before expensive MD | Medium | No | ~100-150 lines: cage completeness check, occupancy verification against requested | CODEBASE.md |
| Interface detection | Quantify hydrate-liquid interface location, width, roughness | Medium-High | **Yes**: `freud.interface.Interface` (one-liner) | ~100 lines with freud; ~300 lines custom density-gradient approach | ALGO-TIMESERIES.md |
| Tetrahedral order parameter (q) | Per-molecule continuous measure of local tetrahedral distortion; complements CHILL+ (discrete classification) and F3/F4 (different geometric formula) | Low-Medium | No | ~50 lines: Errington-Debenedetti formula, nearest-4-neighbor selection via `capped_distance`, `calc_angles` | NUCLEATION-TRACKER.md |
| H-bond ring distribution | Enumerate closed H-bonded rings (3-10 membered) — directly reveals cage topology; can detect early nucleation events before complete cages form; complementary to cage detection (ring distribution asks "how does the H-bond network topology change?" vs cage detection "how many complete cages exist?") | Medium-High | No | ~100 lines: MDAnalysis HydrogenBondAnalysis → adjacency graph → networkx DFS/cycle detection → ring pruning (common angle default) | NUCLEATION-TRACKER.md |
| Ring Summation Factor (RSF) | System-level scalar order parameter: RSF = #rings / (2×N_molecules); tracks global ordering | Low | No | ~10 lines: derived from ring distribution output | NUCLEATION-TRACKER.md |

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|----------|-------------------|
| Full MD engine integration | QuickIce is structure generation/analysis, not a simulation engine. Running GROMACS adds enormous complexity. | Launch GROMACS externally or provide mdp templates. Focus on pre/post analysis. |
| Real-time trajectory streaming analysis | Requires tight coupling with MD engine, continuous file handles, complex threading. Premature for GUI. | Batch analysis: load completed trajectory, run analysis, view results. |
| Free energy calculation (PLUMED/umbrella sampling) | Entirely different workflow, requires bias potentials, WHAM analysis. Out of scope. | Support reading PLUMED colvar files for simple CV tracking only. |
| Force field parameterization | Complex, specialized, error-prone. | Provide force field selection in generation, but don't build parameterization tools. |
| VMD-like full visualization suite | VMD already exists; competing dilutes focus. | Leverage VTK for targeted hydrate-specific visualization (cage rendering, classified molecules). |
| DFT/QM calculations | Completely different domain, massive dependency chain. | Stay firmly in classical MD territory. |
| Machine learning-based classification | ML models need training data, validation, heavy dependencies (PyTorch). No domain-specific models exist yet. | Use physics-based order parameters (F3/F4, CHILL+) — interpretable, validated, lightweight. |
| pytim dependency | GPL-3.0 license incompatible with QuickIce's MIT license. Cannot be required dependency. | Use freud.interface.Interface or custom density-gradient approach. Re-implement ITIM from published literature if needed (algorithm itself is not copyrighted). |
| Topological cage detection from scratch | Very high complexity (~500-1000 lines). Graph-based ring detection is notoriously difficult in periodic systems. | Use GenIce2 coordinate-based approach (cage centers from generation time + distance check). Note: H-bond ring enumeration (3-10 membered closed loops) is a DIFFERENT and simpler problem than full cage detection — it's feasible at ~100 lines using networkx + MDAnalysis, and fills a distinct analytical niche (early nucleation detection). |

## Feature Dependencies

```
GenIce2 Cage Data Capture (P0 infrastructure)
  └── Cage Occupancy Calculation
       ├── Guest Residence Time
       └── Cage Integrity Tracking

F3/F4 Order Parameters
  └── Hydrate Stability Tracking (F4 per frame)

CHILL+ Classification (requires freud for performance)
  ├── Hydrate Stability Tracking (CHILL+ per frame)
  ├── Cage Integrity Tracking (hydrate-surrounding water classification)
  └── VTK 3D Visualization of classified waters

MDAnalysis Trajectory Loading
  ├── RDF (built-in InterRDF)
  ├── MSD (built-in EinsteinMSD)
  ├── H-bond Analysis (built-in HydrogenBondAnalysis)
  │    └── H-bond Ring Distribution (adjacency graph from H-bonds → networkx DFS)
  │         ├── Ring Summation Factor (derived from ring counts)
  │         └── Early Nucleation Detection (5/6-membered ring surge)
  ├── Density Profiles (built-in LinearDensity)
  ├── F3/F4 per-frame (custom AnalysisBase)
  ├── CHILL+ per-frame (custom AnalysisBase + freud)
  └── Tetrahedral Order Parameter q (custom AnalysisBase, ~50 lines)

Tetrahedral Order Parameter (q)
  └── Complements CHILL+ (continuous vs. discrete classification)

Density Profile
  └── Interface Detection (tanh fit or freud.interface)

H-bond Ring Distribution
  └── Cage type inference (pentagon/hexagon counts → sI vs sII signature)
```

## MVP Recommendation

For the analysis milestone MVP, prioritize:

### Phase 1: Infrastructure + Quick Wins
1. **GenIce2 cage center capture** — tiny change, enables cage occupancy
2. **RDF** — MDAnalysis native, zero custom code
3. **Density profiles** — MDAnalysis native + simple binning
4. **Cage occupancy** — distance-based with GenIce2 cage centers

### Phase 2: Hydrate Classification
5. **F4 order parameter** — simple, high-impact, validates structure quality
6. **F3 order parameter** — companion to F4
7. **Hydrate stability tracking** — F4 per frame + time series

### Phase 3: Advanced Classification
8. **CHILL+ classification** — most sophisticated classifier, needs freud
9. **Analysis tab GUI** — makes everything accessible to users

### Defer to post-MVP:
- **Interface detection**: Either freud.interface (simple) or custom density-gradient (complex). Plan for Phase 6.
- **Guest residence time**: Requires cage tracking + trajectory unwrapping. Phase 5.
- **Unit cell parameter tracking**: Niche analysis. Phase 6+.
- **VTK-based 3D classification visualization**: Use existing VTK infrastructure, but defer until analysis pipeline validated.
- **Cage time evolution**: Requires both cage tracking and CHILL+. Phase 5.
- **H-bond ring distribution**: Valuable for early nucleation detection and cage topology analysis; reimplement from published algorithms (~100 lines using networkx + MDAnalysis). Phase 5+ — lower priority than F3/F4, CHILL+, and cage occupancy.
- **Tetrahedral order parameter (q)**: Simple implementation (~50 lines); complements CHILL+ and F3/F4. Phase 5 — could move earlier if low effort justifies it.
- **RSF**: Trivially derived from ring distribution output; defer with ring distribution. Phase 5+.

## Tool Ecosystem Mapping

| Analysis | GROMACS CLI | MDAnalysis | freud | Must Custom-Implement |
|----------|-------------|------------|-------|----------------------|
| RDF | `gmx rdf` ✓ | ✓ `InterRDF` | ✓ | No |
| MSD | `gmx msd` ✓ | ✓ `EinsteinMSD` | ✓ | No |
| H-bonds | `gmx hbond` ✓ | ✓ `HydrogenBondAnalysis` | — | No |
| Density profile | `gmx density` ✓ | ✓ `LinearDensity` | — | No |
| Energy | `gmx energy` ✓ | — | — | No (parse .edr) |
| F3 order parameter | — | — | — | **Yes** |
| F4 order parameter | — | — | — | **Yes** |
| CHILL+ classification | — | — | ✓ (Steinhardt q₃ helps) | **Yes** (correlation + rules) |
| Cage occupancy | — | — | — | **Yes** (distance-based with GenIce2) |
| Guest residence time | — | — | — | **Yes** |
| Interface detection | — | — | ✓ `Interface` | Partial (freud simplifies) |
| H-bond ring distribution | — | — | — | **Yes** (reimplement from published algorithms; nucleation_tracker unsuitable — no license, poor code quality) |
| Tetrahedral order param (q) | — | — | — | **Yes** (~50 lines, Errington-Debenedetti formula) |
| RSF | — | — | — | **Yes** (~10 lines, derived from ring counts) |

### The Hydrate Gap

**Standard MD analysis tools cover ~40% of what hydrate researchers need.** The remaining 60% — cage occupancy, F3/F4, CHILL+, stability tracking, residence time, H-bond ring distribution, tetrahedral order parameter — must be custom-implemented. This is QuickIce's opportunity: become the tool that fills the hydrate-specific gap.

**Note on nucleation_tracker:** The FennellLab/nucleation_tracker tool covers part of this gap (ring distribution, tetrahedral q, RSF) but cannot be used as a dependency due to its absent license. Its algorithms should be reimplemented within QuickIce's MDAnalysis framework, which will also enable trajectory-wide time-series analysis that nucleation_tracker cannot do.

## Sources

- MDAnalysis 2.10.0 docs (HIGH confidence)
- freud 3.5.0 docs (HIGH confidence)
- GROMACS 2026.2 manual (HIGH confidence)
- Nguyen & Molinero (2015) JPCB — CHILL+ algorithm (HIGH confidence)
- Errington & Debenedetti (2001) — F3 definition (HIGH confidence)
- Chau & Hardwick (2009) — F4 definition (MEDIUM confidence)
- GenIce2 source code — cage positions (HIGH confidence)
- Community knowledge — hydrate H-bond criteria (MEDIUM confidence)
