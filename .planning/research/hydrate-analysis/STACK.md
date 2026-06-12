# Technology Stack: Hydrate Analysis

## Project Constraints

- **Installation:** Do NOT auto-install dependencies. Add to environment.yml, seek user approval, wait for user to install.
- **License:** QuickIce is MIT-licensed. All dependencies must be license-compatible.
- **Lightweight philosophy:** QuickIce is a lightweight GUI tool. Heavy dependencies need strong justification.
- **Python version:** 3.14.3 (confirmed via environment inspection)

---

## Recommended Stack

### Already in Environment (No Action Needed)

| Technology | Version | Purpose | Leverage |
|------------|---------|---------|----------|
| MDAnalysis | 2.10.0 | Trajectory I/O + standard analysis | Core framework for all analysis: .xtc/.trr/.tpr/.gro reading, PBC handling, AtomGroup selections, built-in RDF/MSD/H-bonds/density. Already installed. |
| numpy | 2.4.3 | Array operations | Vectorized computation for all custom algorithms |
| scipy | 1.17.1 | Spatial, FFT, optimization | `cKDTree` for neighbor search, `sph_harm_y` for spherical harmonics (backup), `curve_fit` for interface fitting |
| VTK | 9.5.2 | 3D visualization | Analysis overlays (color-by-parameter, cage wireframes), existing rendering pipeline |
| PySide6 | 6.10.2 | GUI framework | Analysis tab, QThread workers, matplotlib embedding |
| matplotlib | 3.10.8 | 2D plotting | RDF, density profiles, stability time series |
| networkx | 3.6.1 | Graph operations | H-bond network analysis, cage topology (later phases) |
| pairlist | 0.6.4 | PBC neighbor search | GenIce2 dependency; backup for neighbor search (MDAnalysis `capped_distance` preferred) |
| cycless | 0.7 | Ring/cage topology | GenIce2 dependency; advanced topological cage detection (Phase 2+, not MVP) |

### New Dependencies Required

| Technology | Version | Purpose | Why | Approval Needed? |
|------------|---------|---------|-----|------------------|
| freud-analysis | 3.5.0 | CHILL+ spherical harmonics + interface detection | C++-accelerated `Steinhardt(l, average=True)` computes q̅₆ directly — ~10-50x faster than Python scipy loops. `Interface` class for hydrate-liquid boundary. `SolidLiquid` for solid-like cluster detection. BSD-3-Clause license (MIT-compatible). ~10MB install. Compatible with Python 3.14.3 via `cp312-abi3` stable ABI wheel. | Yes — user must approve pip install |

### Alternatives Considered (NOT Recommended)

| Technology | Why Not |
|------------|---------|
| MDTraj | Missing .tpr reader (critical for GROMACS topology), no MSD, no density profiles, no trajectory transformations, loads whole trajectory into memory. Redundant with MDAnalysis. |
| pytim | GPL-3.0 license — **incompatible with QuickIce's MIT license**. Cannot be a required dependency. ITIM/Willard-Chandler algorithms are the best available but the license is a dealbreaker. |
| numba | Compatible with Python 3.14 (cp314 wheels), but **defer until benchmarked**. Estimated benefit is marginal for F3/F4 (C-accelerated via MDA), moderate for CHILL+ Python loops (but freud eliminates this), and none for cage occupancy (already C-accelerated). ~100MB install. JIT warmup adds latency. |
| Custom .xtc/.trr reader | Binary XDR format — substantial effort, error-prone. MDAnalysis already solves this. |
| h5py | Not needed for GROMACS trajectory analysis. Only useful for caching intermediate results on very large trajectories (>100K frames). Defer. |
| netCDF4 | Only needed for AMBER NetCDF trajectories. Not relevant for GROMACS workflows. |

---

## MDAnalysis Key Capabilities for Hydrate Analysis

### C-Accelerated Distance Primitives (Core Building Blocks)

| Function | Purpose | Performance |
|----------|---------|-------------|
| `capped_distance(ref, conf, max_cutoff, box=)` | Find pairs within cutoff — **workhorse for all neighbor searches** | C-accelerated, cell-list algorithm |
| `self_capped_distance(ref, max_cutoff, box=)` | Self-pairs version | Same performance |
| `distance_array(ref, conf, box=)` | Full NxM distance matrix — ideal for cage occupancy | C-accelerated |
| `calc_bonds`, `calc_angles`, `calc_dihedrals` | Pairwise geometry — F3/F4 use `calc_angles` + `calc_dihedrals` | C-accelerated |
| `apply_PBC(coords, box)` | Wrap coordinates into primary cell | C-accelerated |

### Built-in Analysis Modules (Zero Custom Code)

| Module | Class | Relevance to Hydrate |
|--------|-------|---------------------|
| RDF | `analysis.rdf.InterRDF`, `InterRDF_s` | O-O, O-guest radial distribution |
| MSD | `analysis.msd.EinsteinMSD` | Mean squared displacement (diffusion) |
| H-bonds | `analysis.hbonds.HydrogenBondAnalysis` | Water H-bond network, cage stability |
| Density | `analysis.density.DensityAnalysis` | 3D density maps |
| Linear Density | `analysis.lineardensity.LinearDensity` | 1D density profiles (z-axis) |

### Custom Analysis Required

| Analysis | Why Custom | Effort | Dependencies |
|----------|-----------|--------|-------------|
| F3 order parameter | No library implements hydrate-specific tetrahedral order parameter | ~100-150 lines | MDAnalysis `capped_distance`, `calc_angles` |
| F4 order parameter | Same as F3; different geometric formula | ~100-150 lines | MDAnalysis `capped_distance`, `calc_dihedrals` |
| CHILL+ classification | No standalone Python implementation exists | ~200-300 lines | freud `Steinhardt` (recommended) or scipy `sph_harm_y` (backup) |
| Cage occupancy | No library implements clathrate cage identification | ~100-150 lines | GenIce2 cage centers (distance-based approach) |
| Stability tracking | Downstream of F4/CHILL+ | ~100-150 lines | F4 or CHILL+ output |
| Guest residence time | No standard tool | ~150-200 lines | Cage tracker, MDAnalysis `capped_distance` |

---

## Critical API Notes

### scipy 1.17.1 Spherical Harmonics Breaking Change

**`scipy.special.sph_harm` is REMOVED in scipy 1.17.1.** Replaced by `sph_harm_y(l, m, theta, phi)`.

Key differences:
- **Argument order**: Old was `sph_harm(m, l, phi, theta)`. New is `sph_harm_y(l, m, theta, phi)`.
- **Angle convention**: Old had theta=azimuthal, phi=polar. New has theta=polar (colatitude), phi=azimuthal — **the opposite convention!**
- This is a **critical gotcha for CHILL+ implementation**. Using the wrong convention flips the sign of c(i,j), swapping staggered/eclipsed classification.

### MDAnalysis AnalysisBase Pattern

All custom analyses must subclass `MDAnalysis.analysis.base.AnalysisBase`:

```python
class MyAnalyzer(AnalysisBase):
    def __init__(self, atomgroup, **kwargs):
        super().__init__(atomgroup.universe.trajectory, **kwargs)
    
    def _prepare(self):   # Called once before iteration
    def _single_frame(self):  # Called per frame; access self._ts, self._frame_index
    def _conclude(self):  # Called once after iteration
```

Key features: `self._ts.dimensions` for PBC box, `run(start, stop, step)`, `backend='multiprocessing'` for parallelization.

### freud Integration with MDAnalysis

```python
import freud
# freud accepts MDAnalysis frames directly:
box = freud.box.Box.from_matrix(ts.triclinic_dimensions)
stei = freud.order.Steinhardt(l=3, average=True)
stei.compute(system=(box, oxygen_positions))
# stei.particle_order gives q̅₃ per particle
```

---

## Installation Order

1. **Now (pre-approved, already installed):** MDAnalysis 2.10.0 + numpy + scipy + VTK + PySide6 + matplotlib
2. **Before Phase 3 (user approval needed):** `pip install freud-analysis==3.5.0` — add to environment.yml
3. **Never:** pytim (GPL-3.0 incompatible), MDTraj (redundant), custom XDR readers

---

## Sources

- MDAnalysis 2.10.0 docs: https://docs.mdanalysis.org/stable/ (HIGH confidence)
- MDAnalysis PyPI: https://pypi.org/project/MDAnalysis/ (HIGH confidence)
- freud 3.5.0 PyPI: https://pypi.org/project/freud-analysis/ (HIGH confidence — cp312-abi3 wheel verified)
- freud docs: https://freud.readthedocs.io/en/stable/ (HIGH confidence)
- scipy 1.17.1 `sph_harm_y` API: Verified by import in QuickIce environment (HIGH confidence)
- Python 3.14.3 environment: Verified by `python --version` (HIGH confidence)
- MDTraj PyPI: https://pypi.org/project/mdtraj/ (HIGH confidence)
- pytim PyPI: https://pypi.org/project/pytim/ (HIGH confidence — GPL-3.0 verified)
- License compatibility: FSF LGPL/GPL guidelines (HIGH confidence)
- numba PyPI: https://pypi.org/project/numba/ (HIGH confidence — cp314 wheel exists)
