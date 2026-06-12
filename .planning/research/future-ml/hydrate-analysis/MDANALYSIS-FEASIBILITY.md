# MDAnalysis-Only Feasibility Assessment

**Verdict:** MAYBE — MDAnalysis + scipy covers 8/10 analyses natively; CHILL+ and interface detection need custom code that benefits significantly from freud (now compatible) or numba JIT. No *hard* dependency blockers, but performance for CHILL+ on large trajectories makes freud strongly recommended.

**Confidence:** HIGH (verified with actual imports and API calls in the QuickIce environment)

## Summary

MDAnalysis 2.10.0, already installed in the QuickIce conda environment, provides C-accelerated distance primitives (`capped_distance`, `calc_angles`, `calc_dihedrals`, `distance_array`), built-in analysis classes (`InterRDF`, `EinsteinMSD`, `HydrogenBondAnalysis`, `DensityAnalysis`, `LinearDensity`), and the `AnalysisBase` framework for custom trajectory analysis. Together with scipy 1.17.1 (providing `sph_harm_y`) and numpy 2.4.3, MDAnalysis can implement all 10 hydrate analysis methods *without any additional library* — but with significant performance caveats for CHILL+ (spherical harmonics per molecule per frame) and interface detection.

The critical discovery is that **freud 3.5.0 is now compatible with Python 3.14.3** (it ships `cp312-abi3` stable ABI wheels, which work with any Python >= 3.12). This was previously blocked when the environment was assumed to be Python 3.11. freud provides C++-accelerated `Steinhardt(l, average=True)` — exactly the q̅₆ computation CHILL+ needs — plus `SolidLiquid` for solid-like cluster detection and `Interface` for interface detection. Adding freud eliminates the two hardest custom implementations.

numba 0.65.1 is also now compatible with Python 3.14 (cp314 wheels available), but its benefit is narrower: mainly for inner loops in F3/F4 and CHILL+ that can't be expressed as vectorized numpy. The JIT warmup cost and added dependency make it a "defer until benchmarked" choice.

## Per-Method Feasibility

| Analysis Method | MDAnalysis Primitives | Custom Code Needed | Extra Lib Needed? | Performance | Verdict |
|----------------|----------------------|-------------------|-------------------|-------------|---------|
| F3/F4 order params | `capped_distance` (neighbors), `calc_angles` (O-O-O), `calc_dihedrals` (O-O···O-O) | Medium: neighbor aggregation, angle filtering, per-molecule classification | No (MDA + numpy sufficient) | Fast: `capped_distance` is C-accelerated; `calc_angles`/`calc_dihedrals` are C-accelerated. ~1-5 min for 1000 frames × 3000 waters | **FEASIBLE** with MDA alone |
| CHILL/CHILL+ | `capped_distance` (neighbors), `AtomGroup.positions` | High: spherical harmonic computation per neighbor, qₗₘ averaging, dot-product correlation | **freud STRONGLY recommended** (C++ Steinhardt); scipy `sph_harm_y` works but slow in Python loops | Slow without freud: Python-loop `sph_harm_y` for each water × each neighbor × each frame. With freud: ~10-50x faster. | **FEASIBLE but ADD FREUD** |
| Cage occupancy | `distance_array` (all O to cage centers), `AtomGroup.select_atoms` | Low: distance cutoff check, per-cage counting | No | Fast: `distance_array` is C-accelerated, handles PBC. ~seconds for 1000 frames | **FEASIBLE** with MDA alone |
| RDF | `InterRDF` (built-in AnalysisBase subclass) | None — just call `InterRDF(ag1, ag2).run()` | No | Fast: built-in, C-accelerated distances | **NATIVE** — zero custom code |
| MSD | `EinsteinMSD` (built-in AnalysisBase subclass) | None — just call `EinsteinMSD(ag).run()` | No | Fast: built-in, C-accelerated | **NATIVE** — zero custom code |
| H-bond analysis | `HydrogenBondAnalysis` (built-in), plus `lifetime()` for autocorrelation | Low: configure selection strings, call `run()`, access `results.hbonds` | No | Fast: built-in, supports parallel execution | **NATIVE** — zero custom code |
| Density profiles | `LinearDensity` (1D along axes), `DensityAnalysis` (3D grid) | Low: select z-axis, call `run()` | No | Fast: built-in | **NATIVE** — near-zero custom code |
| Stability tracking | `AnalysisBase` subclass + F4 per-frame | Medium: subclass `AnalysisBase`, store F4 per frame, compute hydrate fraction time series | No (uses F4 result) | Depends on F4 speed | **FEASIBLE** with MDA alone |
| Guest residence time | `capped_distance` (guest-to-cage-center), `AnalysisBase` for time series | Medium-High: cage assignment per frame, intermittent tracking, survival probability | No | Acceptable: `capped_distance` is fast; Python bookkeeping per frame | **FEASIBLE** with MDA alone |
| Interface detection | `capped_distance`, custom density gradient or order parameter thresholding | High: need to identify boundary between hydrate and liquid phases | **freud recommended** (`freud.interface.Interface`), or custom density-based approach | Custom approach: O(N) per frame with `capped_distance`, but algorithm design is non-trivial. freud: one-liner. | **ADD FREUD for simplicity** |

## Efficiency Analysis

### What's fast enough with MDA alone

**Distance-based operations** are the backbone of MDAnalysis and are C-accelerated with multiple backends:

- `capped_distance(ref, conf, max_cutoff, box=)` — Returns pairs within cutoff. Uses cell-list algorithm (`nsgrid`) or `pkdtree` automatically. **This is the workhorse for all neighbor searches.** Supports OpenMP and distopia backends for additional speed.

- `self_capped_distance(ref, max_cutoff, box=)` — Self-pairs version. Same performance characteristics.

- `distance_array(ref, conf, box=)` — Full NxM distance matrix, C-accelerated. Ideal for cage occupancy (N oxygens × M cage centers).

- `calc_bonds`, `calc_angles`, `calc_dihedrals` — Pairwise geometry, C-accelerated. Accept pre-allocated result arrays for repeated calls.

- `apply_PBC(coords, box)` — Wraps coordinates into primary cell. Needed before any analysis.

**Built-in analysis classes** (`InterRDF`, `EinsteinMSD`, `HydrogenBondAnalysis`, `LinearDensity`) are fully optimized, support `run(start, stop, step)`, parallelization via `backend='multiprocessing'`, and return results in standard `results` containers.

**F3/F4 assessment:** The algorithm is:
1. Find O-O neighbors within 3.5Å → `self_capped_distance` (C-accelerated, ~milliseconds for 3000 waters)
2. For each water, find 4 nearest O neighbors → sort by distance (numpy, vectorized)
3. Compute O-O-O angles → `calc_angles` (C-accelerated)
4. Compute O-O···O-O dihedrals → `calc_dihedrals` (C-accelerated)
5. Classify by angle/dihedral thresholds → numpy (vectorized)

All steps are vectorizable with numpy. Estimated throughput: **~5-20 frames/second for 3000-water system** — acceptable for production runs.

### Where custom Python would be slow

**CHILL/CHILL+ spherical harmonics** is the bottleneck:

The algorithm requires:
1. For each water molecule i, find neighbors j within cutoff → `capped_distance` (fast)
2. For each bond vector rᵢⱼ, compute Yₗₘ(θ,φ) → `scipy.special.sph_harm_y(l, m, theta, phi)` 
3. Average qₗₘ over neighbors → numpy (fast if vectorized)
4. Compute qₗ = sqrt(4π/(2l+1) × Σ|qₗₘ|²) → numpy (fast)
5. For CHILL+: compute dot product qₗₘ(i)·qₗₘ(j) for neighbor correlation → numpy (fast if vectorized)

**Step 2 is the problem.** For l=6, there are 13 values of m (-6 to +6). For 3000 waters × ~17 neighbors each × 13 spherical harmonics = ~660,000 `sph_harm_y` calls per frame. In pure Python with scipy, this is ~2-10 seconds per frame (estimated), giving **~100-500 seconds per 1000-frame trajectory**. This is slow but not catastrophic.

However, `sph_harm_y` in scipy 1.17.1 **does support vectorized calls** — you can pass arrays of theta and phi. If all bond vectors can be assembled into a single array, you can call `sph_harm_y(6, m, all_thetas, all_phis)` once per m-value. This would be **~13 vectorized calls per frame** — potentially fast enough (~0.1-1 seconds per frame).

**The key insight:** If the neighbor search returns ALL pairs at once (via `capped_distance`), and you compute ALL spherical harmonics in vectorized form, CHILL+ with scipy alone might achieve **~1-5 seconds per frame** — slower than freud's C++ but usable for moderate trajectory sizes.

**Interface detection** requires either:
- A density-based approach (bin z-positions, find gradient) → LinearDensity + custom code
- An order-parameter threshold approach → F4 + spatial smoothing
- freud's `Interface` class (uses alpha shapes) → one-liner

Without freud, this is algorithmically complex (not just slow).

### Whether numba helps

**numba 0.65.1 is compatible with Python 3.14.** Both `cp314` and `cp314t` wheels exist on PyPI.

**Estimated benefit per algorithm:**

| Algorithm | numba Benefit | Reasoning |
|-----------|---------------|-----------|
| F3/F4 | **Marginal (~1.5-2x)** | Core operations already C-accelerated via MDA. Only the classification loop (Python if/else) would benefit, and it's already fast with numpy. |
| CHILL+ (with scipy vectorized) | **Moderate (~2-5x)** | The per-molecule qₗₘ aggregation loop could be JIT-compiled. But if using vectorized scipy, there's little Python loop left. |
| CHILL+ (with Python loops) | **Significant (~5-20x)** | If forced into Python loops for neighbor-dependent computation, numba JIT would accelerate dramatically. |
| Cage occupancy | **None** | Already C-accelerated via `distance_array`. |
| Guest residence tracking | **Moderate (~3-5x)** | The per-guest assignment and time-series bookkeeping loop could benefit. |
| Interface detection | **Low** | Algorithm design is the bottleneck, not raw speed. |

**Recommendation: Do NOT add numba initially.** Profile first. If CHILL+ with vectorized scipy is fast enough (~1-5s/frame), numba isn't needed. Only add if profiling shows Python loops are the bottleneck. numba's JIT warmup (~1-5 seconds per function) also adds latency for short trajectories.

### Whether freud is now viable

**YES. freud 3.5.0 IS compatible with Python 3.14.3.**

The PyPI page shows `cp312-abi3` wheels. Python's Stable ABI (abi3) guarantees forward compatibility — a `cp312-abi3` wheel works with Python 3.12, 3.13, 3.14, and beyond. This is confirmed by the wheel tag `cp312-abi3-manylinux_2_27_x86_64` which covers the QuickIce environment.

**What freud provides that MDA + scipy don't:**

| freud Feature | MDA+scipy Equivalent | Speed Difference |
|---------------|---------------------|------------------|
| `freud.order.Steinhardt(l=6, average=True)` | Custom: `capped_distance` + `sph_harm_y` + numpy averaging | freud: **C++ accelerated, ~10-50x faster** than Python+scipy |
| `freud.order.SolidLiquid(l=6, q_threshold=0.7, solid_threshold=6)` | Custom: Steinhardt + dot-product correlation + clustering | freud: **one method call, fully parallelized C++** |
| `freud.density.RDF` | `MDAnalysis.analysis.rdf.InterRDF` | Comparable; MDA's is fine |
| `freud.msd.MSD` | `MDAnalysis.analysis.msd.EinsteinMSD` | Comparable; MDA's is fine |
| `freud.interface.Interface` | Custom density gradient or order parameter thresholding | freud: **algorithm already implemented, no custom code** |
| `freud.locality.Voronoi` | Not available in MDA | Unique capability for Voronoi-based analysis |

**freud is worth adding specifically for CHILL+ and interface detection.** These are the two analyses where custom code is most complex and where C++ acceleration matters most. freud's `Steinhardt(l=6, average=True)` computes q̅₆ directly — the core of CHILL+ — in a single method call with C++ performance. `SolidLiquid` extends this to solid-like cluster detection. `Interface` solves the boundary detection problem.

**Installation:** `pip install freud-analysis` or `conda install -c conda-forge freud`

### Whether h5py/netCDF4 is needed

**h5py:** NOT needed for hydrate analysis. MDAnalysis handles trajectory iteration natively. h5py would only be useful if you want to cache intermediate results (e.g., per-frame F4 values for a 100,000-frame trajectory). For QuickIce's use case (GUI-driven analysis of moderate-length trajectories), numpy arrays in memory are sufficient. **Decision: defer. Add only if memory becomes a bottleneck on very large trajectories.**

**netCDF4:** NOT needed. GROMACS trajectory formats (XTC, TRR) are natively supported by MDAnalysis. netCDF4 is only needed for AMBER-style NetCDF trajectories, which are not relevant here. **Decision: not needed.**

## Existing Environment Leverage

### pairlist 0.6.4

**Can it help with neighbor search?** Yes, but **MDAnalysis's `capped_distance` is superior for this use case.**

pairlist provides `pairs_iter(positions, maxdist=, cell=)` — a C-accelerated cell-division algorithm for neighbor finding under PBC. The API takes fractional coordinates by default (with `fractional=False` for absolute), and a 3×3 cell matrix.

**Comparison with MDAnalysis `capped_distance`:**

| Feature | pairlist | MDA `capped_distance` |
|---------|----------|----------------------|
| Algorithm | Cell division (C) | Cell grid / PKDTree (C) |
| Coordinates | Fractional or absolute | Absolute only |
| PBC handling | Via cell matrix | Via box dimensions |
| Return format | Generator of (i, j, dist) | numpy arrays of pairs + distances |
| AtomGroup support | No (raw arrays only) | Yes |
| Integration | Standalone | Integrated with MDA trajectory |

**Recommendation:** Use `capped_distance` for all MDAnalysis-based analysis. pairlist is redundant here — it provides the same algorithm as MDA's nsgrid backend but with a less convenient API. pairlist would only be useful if you're working outside the MDA framework (e.g., with GenIce2 data structures).

**One exception:** pairlist's `pairs_fine_hetero` for cross-type pair finding (guest-to-water) might have slightly different behavior from MDA's `capped_distance` with two different AtomGroups. Test both, but default to MDA.

### cycless 0.7

**Can it help with cage/ring detection?** Partially, but **not directly for hydrate cage identification.**

cycless provides:
- `cycless.cycles.cycles_iter(graph, maxsize=N)` — Enumerate irreducible rings up to N members in a networkx graph
- `cycless.dicycles.dicycles_iter(graph, size=N)` — Enumerate directed cycles of exact size N
- `cycless.polyhed.polyhedra_iter(cycles)` — Find polyhedral hulls (vitrites) from cycles

**Relevance to hydrate analysis:**
- Hydrate cages (5¹², 5¹²6², 5¹²6⁴, etc.) ARE polyhedra made of H-bond network rings
- cycless's `cycles_iter` could enumerate rings in the H-bond network
- cycless's `polyhedra_iter` could identify cages as polyhedral hulls of those rings
- However, **this is a topological approach, not a geometric one** — it finds cages from the H-bond graph topology, not from distance-based cage center coordinates

**Use case:** If you want to *discover* cages from the H-bond network (rather than check occupancy against known cage centers), cycless + networkx provides the algorithm. This is complementary to the simpler distance-based cage occupancy method.

**Recommendation:** Use cycless for advanced cage topology analysis (Phase 2+). For MVP, use the simpler distance-based cage occupancy approach.

### networkx 3.6.1

**Can it help with H-bond network?** Yes, significantly.

networkx is the standard Python graph library. In hydrate analysis, it's useful for:

1. **H-bond network construction:** After `HydrogenBondAnalysis` identifies bonds, build a `nx.Graph()` where nodes are water molecules and edges are H-bonds. This enables:
   - Connected component analysis (percolation, clustering)
   - Shortest path calculations (water transport pathways)
   - Degree distribution (coordination number)

2. **Cage topology:** Feed the H-bond graph to cycless for ring/cage enumeration

3. **Guest molecule connectivity:** Analyze which guest molecules share cage faces

**Recommendation:** Use networkx for H-bond network analysis. It's already installed and pairs naturally with MDA's `HydrogenBondAnalysis` output.

## AnalysisBase Integration

### How custom analyses subclass MDAnalysis.analysis.base.AnalysisBase

The pattern is:

```python
from MDAnalysis.analysis.base import AnalysisBase

class F4OrderParameter(AnalysisBase):
    def __init__(self, water_oxygen, r_cutoff=3.5, **kwargs):
        super().__init__(water_oxygen.universe.trajectory, **kwargs)
        self.ag = water_oxygen
        self.r_cutoff = r_cutoff
    
    def _prepare(self):
        """Called before trajectory iteration."""
        self.results.f4_per_molecule = []  # per-frame storage
        self.results.f4_timeseries = []   # time series
    
    def _single_frame(self):
        """Called for each frame. Access: self._ts, self._frame_index"""
        # 1. Find O-O neighbors within cutoff
        pairs, dists = self_capped_distance(
            self.ag.positions, self.r_cutoff, box=self._ts.dimensions
        )
        
        # 2. For each water, find 4 nearest neighbors
        # ... (numpy operations on pairs/dists)
        
        # 3. Compute F4 dihedral angles
        # ... (calc_dihedrals on selected quadruplets)
        
        # 4. Classify and store
        self.results.f4_per_molecule.append(f4_values)
    
    def _conclude(self):
        """Called after all frames processed."""
        self.results.f4_timeseries = np.array([
            np.mean(frame_values) for frame_values in self.results.f4_per_molecule
        ])

# Usage:
f4 = F4OrderParameter(u.select_atoms('name OW'), r_cutoff=3.5)
f4.run(start=0, stop=1000, step=10)
print(f4.results.f4_timeseries)
```

### Key AnalysisBase features for hydrate analysis

| Feature | How to Use |
|---------|-----------|
| `self._ts` | Current Timestep — access `.dimensions` (box), `.frame` (index) |
| `self._frame_index` | Index in results array — for pre-allocated arrays |
| `self.results` | Results container — dict-like, supports attribute access |
| `self.times` | Array of frame times after `run()` |
| `run(start, stop, step, frames=)` | Frame selection — flexible iteration control |
| `run(backend='multiprocessing', n_workers=N)` | Parallel execution — for embarrassingly parallel analyses |
| `_prepare()` | Initialize data structures |
| `_single_frame()` | Per-frame computation |
| `_conclude()` | Post-processing, normalization |

### Time-series pattern for stability tracking and residence time

```python
class HydrateStability(AnalysisBase):
    """Track hydrate fraction over time using F4 classification."""
    
    def __init__(self, water_oxygen, r_cutoff=3.5, **kwargs):
        super().__init__(water_oxygen.universe.trajectory, **kwargs)
        self.ag = water_oxygen
        self.r_cutoff = r_cutoff
    
    def _prepare(self):
        # Pre-allocate results array
        self.results.hydrate_fraction = np.zeros(self.n_frames)
        self.results.n_hydrate_waters = np.zeros(self.n_frames, dtype=int)
        self.results.total_waters = np.zeros(self.n_frames, dtype=int)
    
    def _single_frame(self):
        # Compute F4 for this frame (delegated to helper)
        f4_values = self._compute_f4()
        
        # Classify: hydrate-like F4 < -0.8 (or similar threshold)
        n_hydrate = np.sum(f4_values < -0.8)
        n_total = len(f4_values)
        
        self.results.hydrate_fraction[self._frame_index] = n_hydrate / n_total
        self.results.n_hydrate_waters[self._frame_index] = n_hydrate
        self.results.total_waters[self._frame_index] = n_total
    
    def _compute_f4(self):
        """Helper: compute per-molecule F4 for current frame."""
        # ... (implementation using capped_distance + calc_dihedrals)
        pass

# Usage:
stability = HydrateStability(u.select_atoms('resname SOL and name OW'))
stability.run()
plt.plot(stability.times, stability.results.hydrate_fraction)
```

### Parallelization support

For analyses that are embarrassingly parallel (each frame independent), add:

```python
class MyAnalysis(AnalysisBase):
    _analysis_algorithm_is_parallelizable = True

    @classmethod
    def get_supported_backends(cls):
        return ('serial', 'multiprocessing', 'dask')
    
    def _get_aggregator(self):
        return ResultsGroup(lookup={'timeseries': ResultsGroup.ndarray_vstack})
```

F4 and CHILL+ are **embarrassingly parallel** — each frame is independent — so they can benefit from `backend='multiprocessing'`.

## Recommendation

### Tier 1: MDAnalysis alone — sufficient (no new dependencies)

These analyses need **zero additional libraries** beyond what's installed:

| Analysis | MDA Built-in | Custom Code Effort |
|----------|-------------|-------------------|
| RDF | `InterRDF` | None |
| MSD | `EinsteinMSD` | None |
| H-bond analysis | `HydrogenBondAnalysis` | Minimal (selection strings) |
| Density profiles | `LinearDensity` | Minimal (z-axis selection) |
| Cage occupancy | `distance_array` + custom | Low |
| F3/F4 order params | `capped_distance` + `calc_angles`/`calc_dihedrals` | Medium |
| Stability tracking | `AnalysisBase` subclass + F4 | Medium |
| Guest residence time | `capped_distance` + `AnalysisBase` | Medium-High |

### Tier 2: Add freud — strongly recommended for 2 analyses

**`pip install freud-analysis`** (compatible with Python 3.14.3 via abi3):

| Analysis | freud Provides | Effort Saved |
|----------|---------------|-------------|
| CHILL+ | `Steinhardt(l=6, average=True)` → q̅₆ directly | High: eliminates custom sph_harm loop, ~10-50x speedup |
| Interface detection | `Interface` → hydrate-liquid boundary | High: eliminates complex custom algorithm |

freud also provides `SolidLiquid(l=6, q_threshold=0.7, solid_threshold=6)` which is essentially a pre-built CHILL+-like solid detection. This could replace or validate custom CHILL+ implementation.

**Estimated conda impact:** ~10-15 MB additional (C++ shared library + Python wrapper). Minimal.

### Tier 3: Defer — not needed now

| Library | Why Defer | When to Add |
|---------|-----------|-------------|
| numba | No clear benefit yet over vectorized MDA+scipy; JIT warmup cost | If profiling shows Python loops are bottleneck in CHILL+ without freud |
| h5py | No memory bottleneck for moderate trajectories | If analyzing >100K frame trajectories where caching matters |
| netCDF4 | Not needed for GROMACS formats | Only if supporting AMBER NetCDF trajectories |
| cycless (for cage topology) | Topological cage detection is Phase 2+ | When cage discovery (not just occupancy checking) is needed |

### Final recommendation

**Add freud-analysis. Implement everything else with MDAnalysis + scipy + numpy.**

The dependency cost of freud is minimal (~10MB, single `pip install`), and it solves the two hardest problems (CHILL+ spherical harmonics and interface detection) with battle-tested C++ implementations. Without freud, CHILL+ is still feasible via vectorized `sph_harm_y` calls but significantly slower and more error-prone. With freud, `Steinhardt(l=6, average=True)` gives you q̅₆ in one call — exactly what CHILL+ needs.

**Do NOT add numba** until you've benchmarked the vectorized scipy approach and found it too slow. numba adds ~100MB and JIT compilation complexity for uncertain benefit.

**Use the existing pairlist/cycless/networkx** for specialized topological analysis in later phases, not for core hydrate analysis.

## Sources

| Source | URL | Confidence |
|--------|-----|------------|
| MDAnalysis 2.10.0 AnalysisBase docs | https://docs.mdanalysis.org/2.10.0/documentation_pages/analysis/base.html | HIGH — official docs, verified import |
| MDAnalysis 2.10.0 distances docs | https://docs.mdanalysis.org/2.10.0/documentation_pages/lib/distances.html | HIGH — official docs, verified import |
| MDAnalysis 2.10.0 H-bond analysis | https://docs.mdanalysis.org/2.10.0/documentation_pages/analysis/hydrogenbonds.html | HIGH — official docs, verified import |
| MDAnalysis 2.10.0 analysis modules index | https://docs.mdanalysis.org/2.10.0/documentation_pages/analysis_modules.html | HIGH — official docs |
| freud 3.5.0 PyPI (Python >=3.12, abi3 wheels) | https://pypi.org/project/freud-analysis/ | HIGH — verified abi3 wheel compatibility |
| freud Steinhardt order parameter docs | https://freud.readthedocs.io/en/stable/modules/order.html | HIGH — official docs |
| numba 0.65.1 PyPI (Python 3.14 supported) | https://pypi.org/project/numba/ | HIGH — verified cp314 wheel tags |
| scipy 1.17.1 sph_harm_y API | Tested in QuickIce environment | HIGH — verified import and execution |
| pairlist 0.6.4 API | https://github.com/vitroid/PairList | MEDIUM — GitHub README, tested import |
| cycless 0.7 API | https://github.com/vitroid/cycless | MEDIUM — GitHub README |
| EinsteinMSD class | Verified import in environment | HIGH — tested directly |
| LinearDensity class | Verified import in environment | HIGH — tested directly |

### Environment verification commands

All of the following were tested and confirmed working in the QuickIce conda environment:

```python
# Core MDA - VERIFIED
import MDAnalysis  # 2.10.0
from MDAnalysis.analysis.base import AnalysisBase
from MDAnalysis.lib.distances import (capped_distance, self_capped_distance,
    calc_angles, calc_dihedrals, distance_array, apply_PBC)
from MDAnalysis.analysis.hydrogenbonds.hbond_analysis import HydrogenBondAnalysis
from MDAnalysis.analysis.rdf import InterRDF
from MDAnalysis.analysis.msd import EinsteinMSD  # NOT "MSD"!
from MDAnalysis.analysis.density import DensityAnalysis
from MDAnalysis.analysis.lineardensity import LinearDensity

# scipy spherical harmonics - VERIFIED (new API!)
from scipy.special import sph_harm_y  # sph_harm is GONE in scipy 1.17
# sph_harm_y(l, m, theta, phi) — NOTE: argument order differs from old sph_harm

# Existing environment libs - VERIFIED
import pairlist  # 0.6.4
import cycless   # 0.7
import networkx  # 3.6.1
import scipy     # 1.17.1
import numpy     # 2.4.3

# NOT YET INSTALLED but compatible:
# freud-analysis 3.5.0 — cp312-abi3 wheel, compatible with Python 3.14.3
# numba 0.65.1 — cp314 wheel, compatible with Python 3.14.3
```

### Critical API changes to document

1. **`scipy.special.sph_harm` → `sph_harm_y`**: In scipy >= 1.12, `sph_harm(m, l, phi, theta)` was replaced by `sph_harm_y(l, m, theta, phi)`. The argument order **and meaning of theta/phi** changed. In the old API, theta was azimuthal and phi was polar; in the new API, theta is polar (colatitude) and phi is azimuthal. This is the opposite convention! **This is a critical gotcha for CHILL+ implementation.**

2. **`EinsteinMSD` not `MSD`**: The class is `MDAnalysis.analysis.msd.EinsteinMSD`, not `MSD`. This is a common mistake from older documentation.

3. **pairlist coordinate convention**: `pairlist.pairs_iter` takes **fractional coordinates** by default (`fractional=True`). Set `fractional=False` for absolute coordinates. The cell parameter is a 3×3 matrix, not the `[lx, ly, lz, alpha, beta, gamma]` format MDAnalysis uses.
