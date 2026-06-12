# Architecture Patterns: Hydrate Analysis Integration

**Domain:** Molecular dynamics analysis for gas hydrate simulations
**Researched:** 2026-06-12
**Context:** Adding analysis capabilities to QuickIce (PySide6/VTK GUI for GROMACS)

## Recommended Architecture

### Analysis Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     QuickIce GUI                             │
│  Tab 6: Analysis (TabIndex.ANALYSIS)                        │
├─────────────────────────────────────────────────────────────┤
│  AnalysisPanel (QWidget)                                     │
│  ├── File selection (.tpr + .xtc/.trr) or current structure  │
│  ├── Analysis type checkboxes + parameter inputs             │
│  ├── Run button + progress bar + cancel button               │
│  └── Result display (matplotlib + VTK)                       │
├─────────────────────────────────────────────────────────────┤
│  AnalysisWorker (QThread)                                     │
│  ├── TrajectoryLoader → MDAnalysis.Universe                  │
│  ├── StandardAnalyses (wrap MDAnalysis.analysis)             │
│  │   ├── RDFAnalyzer (InterRDF)                              │
│  │   ├── MSDAnalyzer (EinsteinMSD)                           │
│  │   ├── HBondAnalyzer (HydrogenBondAnalysis)                │
│  │   └── DensityProfileAnalyzer (LinearDensity)             │
│  ├── HydrateAnalyses (custom AnalysisBase classes)           │
│  │   ├── F3Analyzer                                          │
│  │   ├── F4Analyzer                                          │
│  │   ├── CHILLPlusClassifier (uses freud Steinhardt)         │
│  │   ├── CageTracker (uses GenIce2 cage centers)             │
│  │   ├── StabilityTracker                                    │
│  │   └── ResidenceAnalyzer                                   │
│  └── ResultCollector                                         │
├─────────────────────────────────────────────────────────────┤
│  AnalysisViewer                                              │
│  ├── MatplotlibPlotter (2D: RDF, MSD, density, F4 histogram) │
│  ├── VTKVisualizer (3D: classified waters, cage wireframes)  │
│  └── DataExporter (CSV, .xvg GROMACS format)                │
├─────────────────────────────────────────────────────────────┤
│  Dependencies                                                │
│  ├── MDAnalysis 2.10.0 (trajectory I/O, built-in analysis)  │
│  ├── freud 3.5.0 (Steinhardt, Interface — for CHILL+)       │
│  ├── numpy 2.4.3 + scipy 1.17.1 (vectorized computation)    │
│  └── VTK 9.5.2 + PySide6 6.10.2 (visualization + GUI)       │
└─────────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| AnalysisPanel | GUI event handling, parameter validation, thread management | AnalysisWorker, AnalysisViewer |
| TrajectoryLoader | Load GROMACS files into MDAnalysis Universe, validate format | AnalysisWorker |
| StandardAnalyses | Wrap MDAnalysis built-in analysis for QuickIce | AnalysisWorker, ResultCollector |
| HydrateAnalyses | Custom AnalysisBase classes for hydrate-specific metrics | AnalysisWorker, ResultCollector, MDAnalysis Universe |
| CageTracker | Track cage occupancy using GenIce2 cage centers | AnalysisWorker, ResidenceAnalyzer |
| AnalysisWorker | QThread-based execution with progress/cancel signals | AnalysisPanel, AnalysisViewer |
| ResultCollector | Aggregate results from analyzers, format for display | AnalysisWorker, AnalysisViewer |
| MatplotlibPlotter | 2D plotting (RDF, MSD, density profiles, histograms) | ResultCollector, AnalysisPanel |
| VTKVisualizer | 3D visualization (classified waters, cage wireframes) | ResultCollector, existing VTK infrastructure |
| DataExporter | Export results to CSV and GROMACS .xvg format | ResultCollector |

### Data Flow

```
User selects .tpr + .xtc → TrajectoryLoader → Universe
        OR: passes in-memory HydrateStructure/InterfaceStructure
                                                    ↓
User configures analysis → AnalysisPanel → AnalysisWorker
                                                    ↓
                              AnalysisWorker selects analyzers
                                                    ↓
                    ┌──────────┬───────────┬──────────────┐
                    ↓          ↓           ↓              ↓
              StandardAnalyses  F4Analyzer  CHILL+Classifier  CageTracker
                    ↓          ↓           ↓              ↓
                 results    results     results       results
                    └──────────┴───────────┴──────────────┘
                                    ↓
                          ResultCollector
                                    ↓
                    ┌───────────┬────────────────┐
                    ↓           ↓                ↓
            MatplotlibPlotter  VTKVisualizer  DataExporter
```

### Analysis Input Sources

**Source 1: Generated structure (in-memory)**
- `HydrateStructure` from hydrate generation tab → analysis on static structure
- `InterfaceStructure` from interface tab → density profiles, order parameters
- Pipeline: existing tab → Tab 6 (structure passed by reference, following cross-tab data flow pattern at `main_window.py:553-594`)

**Source 2: Loaded trajectory (from file)**
- .tpr + .xtc/.trr files loaded via MDAnalysis
- Requires new file loading UI in AnalysisPanel
- Pipeline: User loads file → MDAnalysis Universe → AnalysisWorker

### MVVM Integration Points

**View layer** (new files following existing pattern):
```
quickice/gui/analysis_panel.py      — Analysis configuration panel (~200 lines)
quickice/gui/analysis_viewer.py     — Analysis results viewer (3D + plots) (~300 lines)
quickice/gui/analysis_worker.py     — QThread-based analysis worker (~100 lines)
```

**ViewModel layer** (extend `viewmodel.py`):
```python
# New signals (following existing pattern at viewmodel.py:39-46)
analysis_started = Signal()
analysis_progress = Signal(int)
analysis_status = Signal(str)
analysis_complete = Signal(object)    # AnalysisResult
analysis_error = Signal(str)
analysis_cancelled = Signal()
analysis_ui_enabled_changed = Signal(bool)
```

**Model layer** (new analysis module):
```
quickice/analysis/__init__.py
quickice/analysis/rdf.py            — Radial distribution function (~80 lines)
quickice/analysis/density_profile.py — 1D density profiles (~60 lines)
quickice/analysis/cage_occupancy.py — Guest-to-cage mapping (~100 lines)
quickice/analysis/hbond_network.py  — H-bond statistics (~60 lines)
quickice/analysis/order_parameters.py — F3/F4 order parameters (~250 lines)
quickice/analysis/chillplus.py      — CHILL+ classification (~250 lines)
quickice/analysis/stability.py      — Hydrate stability tracking (~120 lines)
quickice/analysis/residence.py      — Guest residence time (~180 lines)
quickice/analysis/types.py          — AnalysisResult, AnalysisConfig dataclasses (~50 lines)
quickice/analysis/trajectory.py     — MDAnalysis Universe wrapper (~60 lines)
```

### Data Structure Extensions

**HydrateStructure** (add new fields in `types.py`):
```python
cage_centers_frac: np.ndarray | None = None   # (N_cages, 3) fractional in unit cell
cage_types: list[str] | None = None            # ['12', '12', '14', ...]
cage_centers_cart: np.ndarray | None = None     # (N_cages_total, 3) nm, including supercell
guest_cage_assignments: dict | None = None      # {guest_idx: cage_idx}
```

**Capture location**: `hydrate_generator.py:_run_via_api()`, after `generate_ice()` call (line 205), before returning GRO string (line 213):
```python
cage_positions_frac = ice.cagepos1.copy()
cage_types = list(ice.cagetype1)
cell_matrix = np.array(ice.cell1.mat)
```

### Existing Reusable Code

| Module | Function | Analysis Reuse |
|--------|----------|----------------|
| `overlap_resolver.py` | `detect_overlaps()` | cKDTree PBC neighbor search — directly reusable for coordination number |
| `scorer.py` | `_calculate_oo_distances_pbc()` | O-O distance histogram with PBC — directly usable for RDF |
| `vtk_utils.py` | `detect_hydrogen_bonds()` | PBC-aware H-bond detection with supercell + cKDTree — reusable |
| `vtk_utils.py` | `_pbc_distance()` / `_pbc_min_image_position()` | PBC utilities — foundational for any analysis |
| `scorer.py` | `density_score()` | Density calculation — reusable |
| `gro_parser.py` | `parse_gro_string()` | GRO reading — could read single frames without MDAnalysis |

## Patterns to Follow

### Pattern 1: MDAnalysis AnalysisBase Subclass

**What:** All custom analysis classes extend `MDAnalysis.analysis.base.AnalysisBase` for consistent API, progress tracking, and parallelization.

**When:** Every hydrate-specific analyzer (F3, F4, CHILL+, cage occupancy, stability tracking, residence time).

**Key features:**
- `self._ts.dimensions` — PBC box for current frame
- `self._frame_index` — index in results array for pre-allocation
- `self.results` — dict-like results container
- `run(start, stop, step)` — flexible frame selection
- `backend='multiprocessing'` — parallel execution for embarrassingly parallel analyses

### Pattern 2: Threaded Analysis Execution

**What:** Run MD analysis in QThread to prevent GUI freeze. Follows existing `GenerationWorker` pattern from `workers.py:26-130`.

**When:** Any analysis that iterates over trajectory frames.

```python
class AnalysisWorker(QObject):
    progress = Signal(int)
    finished = Signal(object)
    error = Signal(str)
    
    def run(self):
        try:
            self.analyzer.run()
            self.finished.emit(self.analyzer.results)
        except Exception as e:
            self.error.emit(str(e))
```

### Pattern 3: Lazy Trajectory Loading

**What:** NEVER load entire trajectory into memory. Use MDAnalysis's streaming reader.

**When:** Always. GROMACS trajectories can be GB-sized.

```python
# GOOD: Streaming — one frame at a time
u = mda.Universe('topol.tpr', 'traj.xtc')
for ts in u.trajectory:
    process_frame(ts)

# BAD: Loads ALL frames into RAM — can exhaust memory
positions = u.trajectory.timeseries()
```

### Pattern 4: PBC-Aware Analysis

**What:** Always pass box dimensions to distance calculations.

**When:** Every analysis involving spatial relationships.

```python
from MDAnalysis.lib.distances import capped_distance

# Find neighbors within cutoff, respecting PBC
pairs, dists = capped_distance(
    ref.positions, conf.positions,
    max_cutoff=r_max, box=u.dimensions  # Critical: pass box
)
```

### Pattern 5: VTK Analysis Overlays

**What:** Add analysis visualization to existing 3D viewer rather than creating separate viewers for MVP.

**When:** Color-by-order-parameter, cage wireframes, classified molecule rendering.

**Approach:** Extend existing `HydrateViewerWidget` with:
- `set_order_param_coloring(scalar_array)` — vtkColorTransferFunction
- `set_cage_overlay_visible(cage_centers)` — cage wireframe actor
- `set_classification_coloring(classifications)` — per-molecule color array

## Anti-Patterns to Avoid

### Anti-Pattern 1: Loading Full Trajectory Into Memory

**What:** `u.trajectory.timeseries()` or `traj.xyz` loads all frames.
**Why bad:** 100K atoms × 10K frames = ~24 GB RAM for positions alone.
**Instead:** Iterate frame-by-frame through `u.trajectory`.

### Anti-Pattern 2: Ignoring PBC in Distance Calculations

**What:** Computing `np.linalg.norm(pos_i - pos_j)` without periodic images.
**Why bad:** Atoms near box edges appear artificially far apart. Neighbor lists incomplete. RDF wrong near r_max.
**Instead:** Always use `capped_distance(..., box=u.dimensions)` or `distance_array(..., box=u.dimensions)`.

### Anti-Pattern 3: Blocking the GUI Thread

**What:** Running analysis in the main PySide6 thread.
**Why bad:** CHILL+ for 10K waters at 0.5-2 sec/frame = minutes for full trajectory. GUI becomes unresponsive.
**Instead:** QThread with progress signals + cancel button.

### Anti-Pattern 4: Hardcoding Atom Selections

**What:** `u.select_atoms('name OW')` assumes TIP4P naming conventions.
**Why bad:** Different water models use different atom names. TIP3P uses OW, TIP4P-ICE uses O with virtual site MW.
**Instead:** Configurable selection strings with sensible defaults. Use residue-based selection (`resname SOL`) when possible.

### Anti-Pattern 5: Custom XDR Reader

**What:** Implementing .xtc/.trr reading from scratch.
**Why bad:** Binary XDR format with compression, endianness, precision handling. Hundreds of edge cases.
**Instead:** Use MDAnalysis's battle-tested readers.

### Anti-Pattern 6: Using scipy.special.sph_harm (Removed)

**What:** Calling the old `sph_harm(m, l, phi, theta)` API.
**Why bad:** It's **removed** in scipy 1.17.1. Import will fail.
**Instead:** Use `sph_harm_y(l, m, theta, phi)` — note reversed argument order AND reversed angle convention (theta=polar, phi=azimuthal in new API).

## Scalability Considerations

| Concern | At 1K atoms | At 100K atoms | At 1M atoms |
|---------|-----------|--------------|-------------|
| Trajectory I/O | Instant | Fast (streaming) | Slow — use stride |
| Neighbor finding | Fast (brute force OK) | Need cell lists (MDAnalysis uses them) | Must use stride + subsample |
| Memory per frame | ~24 KB | ~2.4 MB | ~24 MB |
| F3/F4 per frame | Fast (<0.1s) | Moderate (~1-5s) | Slow — limit to subset |
| CHILL+ per frame (with freud) | Fast (<0.1s) | Moderate (~0.5-2s) | Slow — use stride |
| CHILL+ per frame (scipy only) | Moderate (~0.5s) | Slow (~5-10s) | Very slow — subsample |
| Cage occupancy | Fast (<0.01s) | Fast (~0.05s) | Moderate — restrict region |
| H-bond analysis | Fast | Moderate | Slow — reduce cutoff |

## Sources

- MDAnalysis architecture docs: https://docs.mdanalysis.org/stable/ (HIGH confidence)
- MDAnalysis AnalysisBase: https://docs.mdanalysis.org/stable/documentation_pages/analysis/base.html (HIGH confidence)
- QuickIce codebase inspection: types.py, hydrate_generator.py, viewmodel.py, workers.py, main_window.py (HIGH confidence)
- QThread pattern: PySide6 documentation (HIGH confidence)
- freud Steinhardt docs: https://freud.readthedocs.io/en/stable/modules/order.html (HIGH confidence)
- scipy sph_harm_y migration: Verified in QuickIce environment (HIGH confidence)
