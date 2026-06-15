# Research Summary: Hydrate Analysis for QuickIce

**Domain:** Molecular dynamics hydrate simulation analysis
**Researched:** 2026-06-12
**Overall confidence:** HIGH (stack/architecture/pitfalls), MEDIUM (threshold values, cage drift handling)

## Executive Summary

QuickIce is adding hydrate-specific MD analysis capabilities — order parameters (F3/F4, CHILL+), cage occupancy, stability tracking, residence time, and density profiles — to its existing PySide6/VTK GUI for GROMACS hydrate structure generation. The research spanned five waves across library comparisons, algorithm specifications, codebase readiness, and MDAnalysis-only feasibility, producing 11 detailed research files.

**The recommended approach**: Use MDAnalysis 2.10.0 (already installed) as the core trajectory I/O and analysis framework, supplement with freud 3.5.0 (now compatible with Python 3.14.3 via `cp312-abi3` stable ABI) specifically for CHILL+ spherical harmonics and interface detection, and implement hydrate-specific algorithms (F3/F4, cage occupancy, stability tracking) as custom `AnalysisBase` subclasses. The single most impactful infrastructure change is capturing GenIce2 cage center positions during structure generation — this eliminates the need for topological cage detection from scratch and reduces cage occupancy to a distance-check problem.

**Key risks and mitigations**: PBC-aware neighbor search is the #1 source of bugs across all algorithms — use MDAnalysis's `capped_distance` with `box=` parameter rather than implementing from scratch. The `scipy.special.sph_harm` API has been replaced by `sph_harm_y(l, m, theta, phi)` with reversed angle conventions — a critical gotcha for CHILL+ implementation. F3/F4 threshold values vary by water model and must be validated against known reference systems. Cage center positions drift during MD — re-centering per frame via nearest-water centroid is the recommended mitigation.

## Key Findings

### Recommended Stack

MDAnalysis 2.10.0 is the primary framework (trajectory I/O, PBC handling, built-in RDF/MSD/H-bond/density analysis). freud 3.5.0 is a strongly recommended supplement for CHILL+ (C++ Steinhardt order parameters, ~10-50x faster than Python scipy loops) and interface detection. All other analyses (F3/F4, cage occupancy, stability tracking, residence time) use MDAnalysis + numpy + scipy. No other new dependencies are needed. pytim is excluded due to GPL-3.0 license incompatibility with QuickIce's MIT license.

**nucleation_tracker** (FennellLab/nucleation_tracker) was evaluated as a potential dependency for H-bond ring distribution analysis. It enumerates 3-10 membered closed H-bonded rings, computes the Errington-Debenedetti tetrahedral order parameter (q), and calculates a Ring Summation Factor (RSF). These are **complementary** to QuickIce's planned F3/F4, CHILL+, and cage analyses — they fill a gap in topological network analysis. However, the tool has **no license** (cannot be used as dependency), poor code quality (8 levels of nested copy-pasted for-loops, global mutable state), and no trajectory support. The algorithms are from published literature and should be **reimplemented** cleanly within QuickIce's MDAnalysis-based framework (~100 lines for ring enumeration, ~50 lines for tetrahedral q). networkx 3.6.1 (already installed) provides cycle detection primitives, and cycless 0.7 (GenIce2 dependency, already installed) may also provide ring enumeration capabilities.

**Core technologies:**
- **MDAnalysis 2.10.0**: Trajectory I/O, PBC handling, built-in analysis (RDF, MSD, H-bonds, density) — already installed
- **freud 3.5.0**: CHILL+ spherical harmonics (Steinhardt q̅₆), interface detection — compatible with Python 3.14.3, ~10MB install
- **scipy 1.17.1**: `sph_harm_y` for spherical harmonics (backup if freud unavailable) — already installed
- **numpy 2.4.3**: Vectorized computation backbone — already installed
- **networkx 3.6.1**: Graph cycle detection for H-bond ring enumeration — already installed
- **cycless 0.7**: GenIce2 dependency; may provide ring enumeration primitives — already installed

### Expected Features

**Must have (table stakes):**
- F4 order parameter — standard hydrate-vs-liquid discriminator in nearly every hydrate MD paper
- Cage occupancy calculation — core hydrate property; every hydrate paper reports this
- RDF (g(r)) — most fundamental structural descriptor; MDAnalysis provides natively
- Density profiles — interface structure and hydrate-liquid boundary characterization
- MSD — guest/water diffusivity, dissociation kinetics; MDAnalysis provides natively

**Should have (differentiators):**
- CHILL+ classification — automatic 5-way classification (clathrate, ice Ih, ice Ic, interfacial, liquid)
- Hydrate stability/dissociation tracking — time evolution of hydrate phase fraction
- Guest residence time — how long guests stay in cages; kinetic stability measure
- VTK-based 3D visualization of classified water molecules — unique advantage over CLI tools
- Tetrahedral order parameter (Errington-Debenedetti q) — per-molecule continuous tetrahedral distortion measure; complements CHILL+ (discrete classification) and F3/F4 (different geometric formula); ~50 lines as AnalysisBase subclass
- H-bond ring distribution — enumerates closed 3-10 membered H-bonded loops; directly reveals cage topology and can detect early nucleation events before complete cages form; reimplemented from published algorithms (~100 lines) using networkx + MDAnalysis

**Defer (v2+):**
- Interface detection (ITIM/Willard-Chandler) — pytim excluded by license; custom implementation or freud's basic `Interface`
- Machine learning classification — physics-based order parameters are interpretable and lightweight
- Full MD engine integration — out of scope for a structure generation/analysis tool
- Ring Summation Factor (RSF) — trivially computed from ring counts; deferrable until ring distribution is implemented
- Directional ring analysis — tracking proton directionality in rings; niche feature for H-bond network asymmetry studies

### Architecture Approach

Analysis integrates into QuickIce's MVVM pattern as a new Tab 6 (Analysis tab) with three layers: AnalysisPanel (GUI configuration), AnalysisWorker (QThread-based computation), and AnalysisViewer (3D overlays + matplotlib plots). All custom analyses subclass `MDAnalysis.analysis.base.AnalysisBase` for consistent API, progress tracking, and parallelization support. GenIce2 cage center positions are captured during structure generation and stored in extended `HydrateStructure` dataclass fields.

**Major components:**
1. **TrajectoryLoader** — wraps MDAnalysis Universe creation from .tpr + .xtc/.trr files
2. **StandardAnalyses** — thin wrappers around MDAnalysis built-in modules (InterRDF, EinsteinMSD, HydrogenBondAnalysis, LinearDensity)
3. **HydrateAnalyses** — custom AnalysisBase subclasses (F3Analyzer, F4Analyzer, CHILLPlusClassifier, CageTracker, StabilityTracker, ResidenceAnalyzer)
4. **AnalysisWorker** — QThread with progress signals, following existing GenerationWorker pattern
5. **AnalysisViewer** — VTK overlays (color-by-parameter, cage wireframes) + matplotlib panels (RDF, density profiles, stability time series)

### Critical Pitfalls

1. **PBC in distance calculations** — always pass `box=u.dimensions` to `capped_distance`; never use raw `np.linalg.norm` without minimum image convention
2. **scipy `sph_harm` → `sph_harm_y` API change** — argument order and angle conventions are reversed; wrong convention flips CHILL+ staggered/eclipsed classification
3. **Cage center drift during MD** — GenIce2 provides t=0 centers; must re-center each frame via nearest-water centroid or tracking displacements
4. **Confusing F3/F4 with Steinhardt qₗ** — these measure fundamentally different things; F3/F4 are tetrahedral angular correlations, not spherical harmonics bond order parameters
5. **Blocking GUI during long analysis** — CHILL+ at 0.5-2 sec/frame means minutes for full trajectories; must use QThread with progress bar and cancel button
6. **Unlicensed code cannot be used as dependency** — nucleation_tracker has no LICENSE file; default copyright means all rights reserved. Cannot import, copy, or redistribute. Must reimplement algorithms independently from published literature (legally sound since the underlying algorithms — Luzar-Chandler H-bond criteria, Errington-Debenedetti tetrahedral order, graph-based ring enumeration — are all published)

### Key Discovery

**GenIce2 cage positions**: GenIce2's lattice modules already define `cagepos` and `cagetype` (sI, sII) or `cages` (sH) for all supported hydrate structures. After `generate_ice()`, the `GenIce` object exposes `cagepos1` and `cagetype1`. QuickIce currently discards this data at `hydrate_generator.py:213` — only the GRO string is returned. Capturing these requires modifying ~2 files, ~50 lines total, and eliminates the need for the most complex algorithm (topological cage detection from scratch).

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: GenIce2 Cage Data Capture + Basic Analysis
**Rationale:** Enables all downstream cage-related analysis; smallest change with largest impact
**Delivers:** Cage centers stored in HydrateStructure; RDF, density profile, and cage occupancy on static structures
**Addresses:** Cage occupancy calculation (table stakes), RDF (table stakes), density profiles (table stakes)
**Avoids:** Pitfall of expensive topological cage detection; pitfall of PBC bugs by reusing existing KDTree code
**Research flag:** Standard patterns — reuses existing cKDTree/scorer code; no deep research needed

### Phase 2: F3/F4 Order Parameters
**Rationale:** Second highest-priority custom implementation; simpler than CHILL+ and immediately useful for hydrate-vs-liquid classification
**Delivers:** Per-molecule F3 and F4 values on static structures and trajectories; per-frame stability time series
**Uses:** MDAnalysis `capped_distance`, `calc_angles`, `calc_dihedrals` (all C-accelerated)
**Implements:** F3Analyzer, F4Analyzer as AnalysisBase subclasses; HydrateStability tracker
**Avoids:** Confusing F3/F4 with Steinhardt qₗ; PBC bugs by using MDAnalysis distance primitives
**Research flag:** Needs threshold validation — F3/F4 threshold values vary by water model and must be calibrated against known reference systems

### Phase 3: CHILL+ Classification + freud Integration
**Rationale:** Most sophisticated classifier; needs freud for performance; prerequisite for advanced time-series
**Delivers:** 5-way per-molecule classification (clathrate, ice Ih, ice Ic, interfacial ice, interfacial clathrate, liquid)
**Uses:** freud `Steinhardt(l=3)` for q₃ computation, MDAnalysis for trajectory I/O and neighbor lists
**Implements:** CHILLPlusClassifier as AnalysisBase subclass; classification → VTK color-by-class rendering
**Avoids:** scipy `sph_harm_y` performance bottleneck (Python loops); angle convention errors (freud handles internally)
**Research flag:** Needs research — spherical harmonics convention verification between freud's Steinhardt and the Nguyen & Molinero (2015) paper definition; interfacial classification ordering dependency

### Phase 4: Analysis Tab GUI + Trajectory Loading
**Rationale:** Makes all analyses accessible to users; adds MD trajectory support beyond static structures
**Delivers:** Analysis tab with configuration panel, progress tracking, result viewer (matplotlib + VTK overlays)
**Uses:** Existing tab pattern (hydrate_panel.py, hydrate_viewer.py, hydrate_worker.py)
**Implements:** AnalysisPanel, AnalysisViewer, AnalysisWorker; MDAnalysis trajectory loading
**Avoids:** GUI blocking pitfall (QThread); memory exhaustion (streaming frame-by-frame)
**Research flag:** Standard patterns — follows existing MVVM/tab pattern exactly

### Phase 5: Advanced Time-Series + Residence Time + Ring Distribution
**Rationale:** Downstream consumers of CHILL+ and cage tracking; ring distribution fills topological gap in nucleation analysis
**Delivers:** Guest residence time (continuous + intermittent correlation), cage integrity tracking, H-bond persistence, **H-bond ring distribution analysis** (3-10 membered closed loops, reimplemented from published algorithms using networkx + MDAnalysis), **tetrahedral order parameter** (Errington-Debenedetti q, ~50-line AnalysisBase subclass)
**Uses:** Cage tracker from Phase 1, CHILL+ from Phase 3, MDAnalysis HydrogenBondAnalysis, networkx cycle detection (or cycless ring enumeration)
**Implements:** ResidenceAnalyzer, CageIntegrityTracker, HBondPersistence, HBondRingAnalysis (AnalysisBase subclass), TetrahedralOrderParameter (AnalysisBase subclass)
**Avoids:** Guest trajectory unwrapping across PBC (use NoJump transformation); nucleation_tracker dependency (no license — reimplement from published algorithms); brute-force ring enumeration (use efficient DFS/networkx); PBC artifacts in H-bond network at boundaries (validate ring closures with MDAnalysis PBC primitives)
**Research flag:** Needs research — guest identity persistence across frames (GROMACS atom reordering); unwrap trajectory before residence analysis; **whether ring distribution is sensitive for early hydrate nucleation detection** (need validation on known nucleation trajectories); cycless API for ring enumeration primitives vs. custom networkx implementation

### Phase 6: Interface Detection + Visualization Polish
**Rationale:** Advanced feature; needs either freud.interface.Interface or custom density-gradient method
**Delivers:** Hydrate-liquid interface position, width, and roughness; cage wireframe VTK rendering; color-by-order-parameter VTK visualization
**Uses:** freud `Interface` (if available), or custom tanh-fit density profile approach
**Implements:** InterfaceDetector, cage VTK wireframe actor, scalar coloring transfer function
**Avoids:** pytim license pitfall (GPL-3.0); slab wrapping destroying structure (detect vacuum gap, center slab)
**Research flag:** Needs research — interface detection algorithm choice (freud vs. custom); VTK cage wireframe from cage center + nearest waters

### Phase Ordering Rationale

- Phase 1 first because cage data capture is a tiny code change (~50 lines) that unlocks the hardest analysis (cage occupancy) without topological detection
- Phase 2 before Phase 3 because F3/F4 are simpler than CHILL+ and immediately useful for stability tracking
- Phase 3 before Phase 4 because CHILL+ is the core algorithm that makes advanced time-series valuable
- Phase 4 makes everything accessible to users; must come after core algorithms are validated
- Phase 5 depends on CHILL+ output and cage tracking; purely downstream
- Phase 6 is polish/advanced; deferrable without losing core value

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** F3/F4 threshold values for specific water models (TIP4P/Ice, TIP3P, SPC/E, mW) — need calibration test systems
- **Phase 3:** freud Steinhardt convention vs. CHILL+ paper convention for qₗₘ normalization; interfacial classification ordering dependency (must classify bulk first, then interfacial)
- **Phase 5:** Guest trajectory unwrapping across PBC for residence time; GROMACS atom reordering between frames
- **Phase 6:** Interface detection algorithm selection; VTK cage wireframe rendering from cage center + nearest water positions

Phases with standard patterns (skip research-phase):
- **Phase 1:** Reuses existing cKDTree/scorer code patterns; GenIce2 API verified by live inspection
- **Phase 4:** Follows exact existing MVVM/tab pattern from hydrate generation tab

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack (MDAnalysis) | HIGH | Already installed, verified in environment, comprehensive docs |
| Stack (freud) | HIGH | cp312-abi3 wheel confirmed compatible with Python 3.14.3 |
| Stack (scipy sph_harm_y) | HIGH | Verified import and execution in QuickIce environment |
| Features (table stakes) | HIGH | Well-established in hydrate MD literature |
| Features (CHILL+) | HIGH | Algorithm fully specified in Nguyen & Molinero (2015) paper |
| Features (cage occupancy) | HIGH | GenIce2 cage positions verified by source code inspection + live API probing |
| Architecture | HIGH | Follows existing MVVM pattern; AnalysisBase is well-documented |
| Pitfalls (PBC) | HIGH | Common pitfall, well-documented mitigation strategies |
| Pitfalls (sph_harm API) | HIGH | Verified by direct testing in QuickIce environment |
| F3/F4 thresholds | MEDIUM | Values vary by water model; need calibration against reference systems |
| Cage center drift | MEDIUM | Re-centering approach is sound but needs validation on MD trajectories |
| Performance (CHILL+) | MEDIUM | Estimated 0.5-2 sec/frame for 10K waters; needs benchmarking |
| Residence time criteria | MEDIUM | Conceptually clear but exchange criteria must be defined carefully |

**Overall confidence:** HIGH

### Gaps to Address

- **F3/F4 threshold calibration**: Run test calculations on known phase systems (pure ice Ih, pure sI hydrate, pure liquid TIP4P/Ice) to validate threshold values. This must happen during Phase 2 implementation.
- **GenIce2 cage data extraction API**: While `cagepos1`/`cagetype1` are verified as available, the exact code to extract them and compute supercell cage positions needs a small prototype before Phase 1 implementation.
- **freud Steinhardt normalization**: Need to verify that `freud.order.Steinhardt(l=3, average=True)` computes the same qₗₘ as defined in the ten Wolde/Steinhardt convention used by the CHILL+ paper. Different normalization conventions can flip the sign of c(i,j).
- **Cage center re-centering strategy**: For MD trajectories where the hydrate lattice deforms, the recommended approach (find nearest waters to initial center, compute centroid) needs testing on a real trajectory to verify accuracy.
- **Performance benchmarking**: CHILL+ performance estimate (0.5-2 sec/frame for 10K waters) needs validation. If >5 sec/frame, may need numba JIT or frame subsampling strategies.
- **Ring distribution sensitivity for early nucleation**: H-bond ring distribution can theoretically detect 5- and 6-membered ring formation before complete cages, but this has not been validated on hydrate nucleation trajectories. Need test on known nucleation trajectory to verify sensitivity. Deferrable to Phase 5 implementation.
- **cycless ring enumeration API**: cycless 0.7 (GenIce2 dependency, already installed) may provide ring enumeration primitives that could accelerate Phase 5 ring distribution implementation. Need to inspect cycless API to determine if it exposes ring-finding as a callable function or only as an internal GenIce2 stage.
- **Ring pruning strategy selection**: nucleation_tracker provides four pruning algorithms (vertex, common edge, common angle, common torsion) with the paper recommending "common angle" as default. QuickIce implementation should start with common angle pruning but may need to validate which is most appropriate for hydrate systems.

## Sources

### Primary (HIGH confidence)
- MDAnalysis 2.10.0 official docs — trajectory I/O, AnalysisBase, built-in analysis modules
- freud 3.5.0 PyPI + docs — cp312-abi3 wheel, Steinhardt, SolidLiquid, Interface
- GenIce2 source code (direct inspection) — cagepos, cagetype, cagepos1, cagetype1
- QuickIce codebase (direct inspection) — types.py, hydrate_generator.py, scorer.py, vtk_utils.py
- Nguyen & Molinero (2015) JPCB — CHILL+ algorithm specification (doi:10.1021/jp510289t)
- scipy 1.17.1 (verified in environment) — sph_harm_y API

### Secondary (MEDIUM confidence)
- Errington & Debenedetti (2001) Nature — F3 order parameter definition
- Chau & Hardwick (2009) Mol. Phys. — F4 order parameter definition
- OVITO CHILL+ modifier documentation — C++ reference implementation
- Community knowledge — hydrate H-bond criteria, typical F3/F4 threshold values

### Tertiary (LOW confidence)
- HashMap cage detection (Venditti group) — described in papers only, no public implementation
- F3/F4 threshold values for specific water models — from training data, need validation

### Supplementary Research Files

Detailed algorithm specifications and analysis preserved in:
- `ALGO-F3F4.md` — F3/F4 mathematical definitions, pseudocode, pitfalls
- `ALGO-CHILL.md` — CHILL/CHILL+ algorithm, classification rules, pseudocode
- `ALGO-CAGE.md` — Cage detection approaches, GenIce2 coordinate-based method, cage radii
- `ALGO-TIMESERIES.md` — Stability tracking, residence time, density profiles
- `CODEBASE.md` — QuickIce data structures, VTK capability, reusable code inventory
- `COMPARISON.md` — Detailed library comparison (MDAnalysis vs MDTraj vs freud vs pytim)
- `MDANALYSIS-FEASIBILITY.md` — Per-method feasibility, efficiency analysis, API verification
- `NUCLEATION-TRACKER.md` — nucleation_tracker research (ring distribution, tetrahedral q, license assessment); see also `../../hydrate-analysis/NUCLEATION-TRACKER.md`

---
*Research completed: 2026-06-12*
*Ready for roadmap: yes*
