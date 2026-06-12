# QuickIce Codebase Analysis Readiness

**Project:** QuickIce
**Researched:** 2026-06-12
**Mode:** Feasibility
**Confidence:** HIGH (direct codebase inspection + live GenIce2 API probing)

## Data Structure Inventory

### HydrateStructure (`types.py:632-722`)

| Field | Type | Analysis Use | Notes |
|-------|------|-------------|-------|
| `positions` | `np.ndarray (N,3)` | Core input: all atom coordinates | In nm, combined water+guest |
| `atom_names` | `list[str]` | Atom type identification | e.g. "OW","HW1","HW2","MW","C","H" |
| `cell` | `np.ndarray (3,3)` | PBC for neighbor analysis | Row vectors in nm |
| `molecule_index` | `list[MoleculeIndex]` | **Critical**: molecule boundaries + type | `MoleculeIndex(start_idx, count, mol_type)` |
| `config` | `HydrateConfig` | Lattice type, guest type, occupancy params | Preserved from generation |
| `lattice_info` | `HydrateLatticeInfo` | Cage type names, counts per unit cell | **Missing: cage center positions** |
| `report` | `str` | Human-readable summary | Not machine-parseable |
| `guest_count` | `int` | Quick cage occupancy estimate | Total guests, not per-cage-type |
| `water_count` | `int` | Water framework size | |

**What it enables:**
- Guest vs water molecule separation (via `molecule_index.mol_type`)
- Per-molecule coordinate extraction (via `start_idx`, `count`)
- Density calculation (positions + cell → volume)
- O-O distance analysis (filter OW atoms from positions)
- H-bond detection (existing code in `hydrate_renderer.py:558-627`)

**What it's MISSING (critical for analysis):**
- **Cage center positions** — not stored anywhere after generation
- **Cage type per guest molecule** — which guest is in which cage size
- **Cage occupancy data** — per-cage-type occupancy vs requested occupancy
- **Guest-to-cage assignment** — mapping of each guest molecule to its cage

### MoleculeIndex (`types.py:26-43`)

| Field | Type | Analysis Use |
|-------|------|-------------|
| `start_idx` | `int` | Locate molecule in positions array |
| `count` | `int` | Atoms per molecule (variable: 4 water, 5 CH4, 13 THF) |
| `mol_type` | `str` | Filter by molecule type ("water","ch4","thf","na","cl") |

**Analysis value:** MoleculeIndex is the backbone for any per-molecule analysis. It enables:
- Extracting all water O positions → RDF, coordination number
- Extracting all guest C positions → cage occupancy reconstruction
- Per-molecule COM calculation → MSD

### InterfaceStructure (`types.py:223-274`)

| Field | Type | Analysis Use |
|-------|------|-------------|
| `positions` | `np.ndarray` | All atom positions |
| `atom_names` | `list[str]` | Atom type identification |
| `cell` | `np.ndarray (3,3)` | PBC box |
| `ice_atom_count` | `int` | Ice/water boundary marker |
| `water_atom_count` | `int` | Liquid water count |
| `ice_nmolecules` | `int` | Ice molecule count |
| `water_nmolecules` | `int` | Water molecule count |
| `mode` | `str` | Interface mode (slab/pocket/piece) |
| `report` | `str` | gmx solvate-like report |
| `guest_atom_count` | `int` | Guest boundary marker |
| `molecule_index` | `list` | Per-molecule tracking (when multiple types present) |
| `guest_nmolecules` | `int` | Guest count |

**Analysis value for interfaces:**
- Ice/water boundary identification (via `ice_atom_count`) → density profile along Z
- Phase-specific analysis (ice vs liquid water) → order parameter profiles
- Pocket mode: confined water analysis

### Candidate (`types.py:98-127`)

| Field | Type | Analysis Use |
|-------|------|-------------|
| `positions` | `np.ndarray` | All atom positions |
| `atom_names` | `list[str]` | Atom names |
| `cell` | `np.ndarray (3,3)` | Unit cell |
| `nmolecules` | `int` | Molecule count |
| `phase_id` | `str` | Phase identifier |
| `seed` | `int` | Random seed |
| `metadata` | `dict` | **Carries density, T, P, guest_type_counts** |

**Note:** `HydrateStructure.to_candidate()` (types.py:658-722) preserves hydrate metadata in `metadata` dict including `lattice_type`, `water_count`, `guest_count`, `guest_type_counts`, `original_hydrate`.

### HydrateLatticeInfo (`types.py:585-628`)

| Field | Type | Analysis Use |
|-------|------|-------------|
| `lattice_type` | `str` | "sI", "sII", "sH" |
| `cage_types` | `list[str]` | Cage type names e.g. ["5¹²", "5¹²6²"] |
| `cage_counts` | `dict[str,int]` | Count per cage type per unit cell |
| `unit_cell_molecules` | `int` | Water molecules in unit cell |
| `total_cages` | `int` | Total cages per unit cell |

**Analysis value:** Provides the theoretical cage count per unit cell, enabling:
- Expected vs actual guest count comparison
- Theoretical occupancy calculation (guests / (cages × supercell))

### HydrateConfig (`types.py:277-328`)

| Field | Type | Analysis Use |
|-------|------|-------------|
| `lattice_type` | `str` | Which hydrate structure |
| `guest_type` | `str` | "ch4" or "thf" |
| `cage_occupancy_small` | `float` | **Requested** small cage occupancy (0-100%) |
| `cage_occupancy_large` | `float` | **Requested** large cage occupancy (0-100%) |
| `supercell_x/y/z` | `int` | Supercell dimensions |

**Analysis value:** The requested occupancies vs actual occupancies is a basic validation metric.

---

## GenIce2 Data Capture

### What GenIce2 provides during generation

GenIce2 lattice objects expose the following analysis-relevant attributes (verified by live API inspection):

| Attribute | Type | Description | Available |
|-----------|------|-------------|-----------|
| `cagepos` | `np.ndarray (N_cages, 3)` | Cage center positions (fractional coords of unit cell) | sI, sII (NOT sH — uses `cages` string instead) |
| `cagetype` | `list[str]` | Cage type per cage position ("12"=5¹², "14"=5¹²6², "16"=5¹²6⁴, "20"=5¹²6⁸) | sI, sII |
| `cages` | `str` | Formatted cage data (cage type + fractional positions) | sH only |
| `cell` | `np.ndarray` | Unit cell matrix | All |
| `density` | `float` | Water density | All |
| `coord` | array-like | Water oxygen positions (fractional) | All |
| `waters` | `int` | Number of water molecules | All |
| `bondlen` | `int` | Bond length parameter | All |

After calling `GenIce.generate_ice()`, the GenIce object also exposes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `cagepos1` | `np.ndarray` | Unit cell cage positions (fractional) |
| `cagetype1` | `list[str]` | Unit cell cage types |
| `filled_cages` | `set` | **Currently empty** — appears to be unpopulated |
| `cell1` | `Cell` object | Unit cell (has `.mat` for cell matrix) |
| `waters1` | collection | Water molecule data |
| `pairs1` | `list` | Water pair connections (O-O neighbors = H-bond network) |
| `groups1` | `defaultdict` | Molecule groups (cage-based groupings) |

### What QuickIce currently captures vs discards

**Currently captured** (`hydrate_generator.py:78-126`):
- ✅ `positions` (from `_parse_gro_result`)
- ✅ `atom_names` (from GRO parsing)
- ✅ `cell` (from GRO box line)
- ✅ `residue_names` (used for THF identification)
- ✅ `residue_seq_nums` (used for molecule grouping)
- ✅ Water/guest counts (via `molecule_index`)
- ✅ `HydrateLatticeInfo` (from `HYDRATE_LATTICES` constant)

**Currently DISCARDED** (available from GenIce2 but not captured):

| Data | GenIce2 Source | Lost At | Analysis Value |
|------|---------------|---------|----------------|
| **Cage center positions** | `ice.cagepos1` | `hydrate_generator.py:97` — `_run_via_api()` calls `generate_ice()` but returns only GRO string | **CRITICAL**: needed for cage occupancy, F3/F4 order parameters, cage visualization |
| **Cage types per position** | `ice.cagetype1` | Same as above | **CRITICAL**: maps each cage to its type (small/large) |
| **Supercell cage positions** | Derived from `cagepos1` × supercell | Not computed | Needed for per-cage analysis in supercell |
| **H-bond network (water pairs)** | `ice.pairs1` | Not captured after `generate_ice()` | Could enable H-bond network analysis |
| **Water oxygen positions (fractional)** | `ice.waters1` / `lattice.coord` | Lost — only GRO positions kept | Could verify cage center computation |

### Specific code paths where cage data is lost

1. **`hydrate_generator.py:128-218`** — `_run_via_api()`:
   - Line 205: `gro_string = ice.generate_ice(...)` — After this call, `ice.cagepos1` and `ice.cagetype1` are available on the `ice` object
   - Line 213: `return self._parse_gro_result(gro_string)` — Only the GRO string is returned; the `ice` object (with cage data) is discarded
   - **Fix location:** After line 205, before line 213, capture `ice.cagepos1`, `ice.cagetype1`, `ice.cell1.mat`

2. **`hydrate_generator.py:78-126`** — `generate()`:
   - Line 97: receives only `(positions, cell, atom_names, residue_names, residue_seq_nums)` from `_run_via_api()`
   - **Fix location:** Extend `_run_via_api()` return tuple to include cage data; extend `generate()` to pass it to `HydrateStructure`

### Recommendations for what to capture

**Minimal capture (enables basic cage analysis):**
```python
# In _run_via_api(), after generate_ice():
cage_positions_frac = ice.cagepos1.copy()  # Fractional coords
cage_types = list(ice.cagetype1)          # ['12', '12', '14', '14', ...]
cell_matrix = np.array(ice.cell1.mat)     # Unit cell matrix in nm
```

**Full capture (enables advanced analysis):**
```python
# Additionally:
h_bond_pairs = list(ice.pairs1)           # Water pair connectivity
filled_cages = set(ice.filled_cages)       # Which cages got guests (currently empty, may be GenIce2 bug)
```

**Supercell cage positions derivation:**
```python
# From unit cell cage positions + supercell matrix:
supercell = np.diag([config.supercell_x, config.supercell_y, config.supercell_z])
# For each cage in unit cell, replicate:
# cage_center = (fractional_pos @ cell_matrix) + i*cell[0] + j*cell[1] + k*cell[2]
# where i,j,k = supercell indices
```

---

## VTK Visualization Capability

### Current rendering pipeline

**MolecularViewerWidget** (`molecular_viewer.py:35-534`):
- Uses `vtkMoleculeMapper` with ball-and-stick/VDW/stick modes
- Atom coloring: CPK (element-based), property-based (energy/density ranking)
- Bond detection: by atom ordering (O-H-H pattern per molecule)
- Overlays: H-bond dashed lines (`vtkPolyDataMapper` with line cells), unit cell wireframe (`vtkOutlineSource`)
- PBC: `vtkMolecule.SetLattice()` for periodic rendering
- Camera: trackball, auto-rotation, zoom-to-fit

**HydrateViewerWidget** (`hydrate_viewer.py:56-487`):
- **Dual-actor rendering**: water framework actor + guest molecule actor (from `hydrate_renderer.py`)
- Water framework: rendered with `_build_vtk_molecule_from_molecule_index()` (bonds within same molecule only)
- Guest molecules: rendered with `create_guest_actor()` (CPK coloring, distance-based bonds)
- H-bond detection: `detect_hbonds_in_hydrate_structure()` (0.25nm H...O threshold)
- Unit cell: `vtkOutlineSource` (box wireframe)
- Stacked widget pattern: placeholder → 3D viewer

**HydrateRenderer** (`hydrate_renderer.py:1-628`):
- `render_hydrate_structure()` → `[water_actor, guest_actor]`
- `create_water_framework_actor()` — water bonds only (no H-H bonds)
- `create_guest_actor()` — guests with CPK coloring
- `detect_hbonds_in_hydrate_structure()` — PBC-aware H-bond detection
- Bond threshold: 0.16nm for covalent bonds

**VTK Utils** (`vtk_utils.py:1-802`):
- `candidate_to_vtk_molecule()` — Candidate → vtkMolecule
- `interface_to_vtk_molecules()` — InterfaceStructure → (ice_mol, water_mol, guest_mol)
- `detect_hydrogen_bonds()` — KDTree-based O(n log n) H-bond detection with 3×3×3 supercell PBC
- `create_hbond_actor()` — dashed cyan lines
- `create_unit_cell_actor()` — gray wireframe box
- `create_bond_lines_actor()` — simple 2D line bonds
- `_pbc_distance()` / `_pbc_min_image_position()` — PBC-aware distance/position utilities

### What analysis overlays are feasible with current VTK

| Analysis Visualization | VTK Feasibility | Required New Components |
|------------------------|----------------|------------------------|
| **Density isosurfaces** | ✅ VTK has `vtkContourFilter` + `vtkMarchingCubes` | Need to build density field on 3D grid first |
| **Cage wireframes** | ✅ `vtkPolyDataMapper` with polygon cells | Need cage vertex positions (from GenIce2 cage + nearest waters) |
| **Colored regions (ice/water/guest)** | ✅ Already partially done (ice/water/guest separate actors) | Extend with per-region coloring |
| **Labeled atoms** | ⚠️ VTK can do `vtkBillboardTextActor3D` but it's slow for many atoms | vtkLabeledDataMapper for limited labels |
| **Density profile (1D plot)** | ✅ Matplotlib overlay or separate panel | Need density calculation along axis |
| **RDF overlay** | ✅ Matplotlib plot in separate panel | Need RDF calculation |
| **Color-by-order-parameter** | ✅ `vtkColorTransferFunction` + scalar array on atoms | Need F3/F4 calculation per molecule |
| **Cage occupancy heatmap** | ✅ Color spheres at cage centers | Need cage center positions |
| **Time-series trajectory** | ✅ `vtkMoleculeMapper` per frame + animation timer | Need trajectory reader (MDAnalysis) |

### What would need new VTK components

1. **CageWireframeActor** — Given cage center + nearest water O positions, draw polyhedron wireframe
   - VTK: `vtkPolyData` with polygon cells → `vtkPolyDataMapper` → `vtkActor`
   - Pattern: similar to `create_unit_cell_actor()` but with cage vertices

2. **DensityProfileActor** — 1D density plot overlaid on 3D viewer
   - Alternative: Use matplotlib in a Qt panel alongside the 3D viewer
   - Simpler to implement and more scientifically standard

3. **ScalarColoringActor** — Color atoms/molecules by analysis scalar
   - Pattern already exists: `MolecularViewerWidget._apply_property_coloring()`
   - Extend to accept per-molecule or per-atom scalar arrays from analysis

4. **AnalysisOverlayPanel** — Qt panel showing analysis results alongside 3D viewer
   - Could contain: matplotlib density profile, RDF plot, occupancy table
   - Pattern: similar to `InfoPanel` but with embedded matplotlib

---

## Existing Analysis-Adjacent Code

### Code that does partial analysis (reusable)

| Module | Function | Analysis Reuse | Lines |
|--------|----------|----------------|-------|
| `overlap_resolver.py` | `detect_overlaps()` | cKDTree PBC neighbor search — **directly reusable** for coordination number, RDF | 14-85 |
| `overlap_resolver.py` | `cKDTree(boxsize=...)` | PBC-aware KDTree pattern — **copy for any neighbor analysis** | 72-73 |
| `scorer.py` | `_calculate_oo_distances_pbc()` | O-O distance histogram with PBC via 3×3×3 supercell + cKDTree — **directly usable for RDF** | 21-80 |
| `scorer.py` | `density_score()` | Density calculation from positions + cell — **reusable** | 138-193 |
| `vtk_utils.py` | `detect_hydrogen_bonds()` | PBC-aware H-bond detection with supercell + cKDTree — **directly reusable** | 201-316 |
| `hydrate_renderer.py` | `detect_hbonds_in_hydrate_structure()` | Hydrate-specific H-bond detection with `_pbc_distance()` — **reusable** | 558-627 |
| `vtk_utils.py` | `_pbc_distance()` / `_pbc_min_image_position()` | PBC utilities — **foundational for any analysis** | 128-198 |
| `water_filler.py` | `scale_positions_for_density()` | Density-based position scaling — **reference for density calculations** | 183-213 |
| `water_filler.py` | `fill_region_with_water()` | Region filling with density control — **water density reference** | 624-687 |
| `water_density.py` | `water_density_gcm3()` | IAPWS-95 water density — **reference for expected densities** | 96-117 |
| `ice_ih_density.py` | (entire module) | Temperature-dependent ice Ih density — **reference for ice density** | (entire file) |
| `gro_parser.py` | `parse_gro_string()` / `parse_gro_file()` | GRO file reading — **could read trajectory frames** | 14-110 |

### What can be reused without modification

1. **`scorer._calculate_oo_distances_pbc()`** → RDF calculation (add histogram binning)
2. **`overlap_resolver.detect_overlaps()`** → Coordination number (count neighbors instead of set membership)
3. **`vtk_utils.detect_hydrogen_bonds()`** → H-bond network analysis (already counts per-molecule H-bonds)
4. **`vtk_utils._pbc_distance()` / `_pbc_min_image_position()`** → All PBC-aware distance calculations
5. **`scorer.density_score()`** → Structural density validation

### What needs to be built fresh

| Analysis | Algorithm | Complexity | Dependencies |
|----------|-----------|------------|-------------|
| **RDF** | g(r) histogram from O-O distances | Low | scipy cKDTree (already used) |
| **Coordination number** | Count O neighbors within cutoff per molecule | Low | cKDTree (already used) |
| **Density profile** | Bin atoms along Z-axis, compute density per bin | Low | numpy histogram |
| **F3/F4 order parameters** | Per-molecule orientational order parameter | Medium | Requires O and H positions per molecule (available via molecule_index) |
| **Cage occupancy** | Map guests to nearest cage center; count per type | Medium | Requires cage centers (must capture from GenIce2) |
| **CHILL+ classification** | Bond orientational order parameter (l=3, l=6) | High | Requires neighbor list + bond angles |
| **Cage detection** | Voronoi-based cage identification from water positions | Very High | scipy Voronoi or custom algorithm |
| **MSD (mean square displacement)** | Track molecule COM over time | Medium | Requires trajectory (MDAnalysis) |
| **Diffusion coefficient** | Slope of MSD vs time | Low | From MSD data |

---

## Architecture Integration Points

### Where analysis fits in MVVM pattern

**Current tab structure** (from `constants.py:9-28`):
```
Tab 0: Ice Generation    (TabIndex.ICE)
Tab 1: Hydrate Generation (TabIndex.HYDRATE)
Tab 2: Interface Construction (TabIndex.INTERFACE)
Tab 3: Custom Molecule   (TabIndex.CUSTOM)
Tab 4: Solute Insertion  (TabIndex.SOLUTE)
Tab 5: Ion Insertion     (TabIndex.ION)
```

**Proposed:** Tab 6: Analysis (TabIndex.ANALYSIS)

The analysis tab would follow the existing pattern:
- **Panel**: `AnalysisPanel` (QWidget with analysis configuration)
- **Viewer**: Reuse existing 3D viewer with analysis overlays, plus new matplotlib panels
- **Worker**: `AnalysisWorker` (QThread-based, following `GenerationWorker` pattern)
- **ViewModel**: Extend `MainViewModel` with analysis signals

### MVVM extension pattern (following existing code)

**View layer** (new files):
```
quickice/gui/analysis_panel.py      — Analysis configuration panel
quickice/gui/analysis_viewer.py     — Analysis results viewer (3D + plots)
quickice/gui/analysis_worker.py     — QThread-based analysis worker
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
quickice/analysis/rdf.py            — Radial distribution function
quickice/analysis/density_profile.py — 1D density profiles
quickice/analysis/cage_occupancy.py — Guest-to-cage mapping
quickice/analysis/hbond_network.py  — H-bond statistics
quickice/analysis/order_parameters.py — F3/F4, CHILL+
quickice/analysis/types.py          — AnalysisResult, AnalysisConfig dataclasses
```

### Analysis input sources

**Source 1: Generated structure (in-memory)**
- `HydrateStructure` from hydrate generation
- `InterfaceStructure` from interface generation
- `Candidate` from ice generation
- Pipeline: Tab 1/2/0 → Tab 6 (structure passed by reference)
- Pattern: Same as current cross-tab data flow (e.g., ice → interface at `main_window.py:553-594`)

**Source 2: Loaded trajectory (from file)**
- .gro/.xtc/.trr/.tpr files loaded by MDAnalysis
- Requires new file loading UI in AnalysisPanel
- Pipeline: User loads file → MDAnalysis Universe → AnalysisWorker

**Source 3: GRO file loading (minimal, without MDAnalysis)**
- `gro_parser.py` can already read .gro files
- Could add frame-by-frame reading for small trajectories
- Pipeline: User loads .gro → parse_gro_file → single-frame analysis

### Worker pattern (following `workers.py:26-130`)

```python
class AnalysisWorker(QObject):
    """Worker for running analysis in background thread."""
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(object)  # AnalysisResult
    error = Signal(str)
    cancelled = Signal()
    
    def __init__(self, structure, config):
        super().__init__()
        self._structure = structure  # HydrateStructure, InterfaceStructure, or Candidate
        self._config = config       # AnalysisConfig
    
    def run(self):
        # Import inside run() for thread safety (pattern from workers.py:75-100)
        from quickice.analysis.rdf import compute_rdf
        from quickice.analysis.density_profile import compute_density_profile
        # ... etc.
```

### Viewer pattern (analysis overlays in existing 3D viewer)

**Option A: Overlay on existing viewer** (recommended for MVP)
- Add analysis overlay actors to `HydrateViewerWidget` or `MolecularViewerWidget`
- Follow pattern of existing H-bond overlay: `set_hbonds_visible()` at `hydrate_viewer.py:461-479`
- New methods: `set_cage_overlay_visible()`, `set_density_overlay_visible()`, `set_order_param_coloring()`

**Option B: Separate analysis viewer** (more flexible, better for later)
- New `AnalysisViewerWidget` with dedicated VTK renderer + matplotlib panels
- Stacked widget pattern: analysis config → analysis results
- Allows independent camera/orientation from structure viewer

### Export pattern

Following existing exporters (from `main_window.py:29`):
- `GROMACSExporter` → `AnalysisCSVExporter` (CSV data export)
- `ViewportExporter` → `AnalysisPlotExporter` (PNG/SVG for plots)
- Pattern: File → Save dialog → write

### State flow: Where analysis input comes from

```
Ice Generation (Tab 0) ──────────────┐
                                      │
Hydrate Generation (Tab 1) ──────────┤→ Analysis Tab (Tab 6)
                                      │   Input: positions, cell, molecule_index
Interface Construction (Tab 2) ──────┤   + cage_centers (new field)
                                      │   + cage_types (new field)
OR: File → Load .gro/.xtc/.tpr ─────┘
```

---

## Path of Least Resistance

### Phase 1: Capture GenIce2 cage data (data structure extension)

**Effort:** Low (modify 2 files, add ~50 lines)
**Impact:** Enables ALL cage-related analysis

Changes needed:
1. **`hydrate_generator.py:_run_via_api()`** (line 213):
   - Capture `ice.cagepos1`, `ice.cagetype1` after `generate_ice()` call
   - Return cage data alongside GRO string

2. **`types.py:HydrateStructure`** (add new fields):
   ```python
   cage_centers_frac: np.ndarray | None = None  # (N_cages, 3) fractional in unit cell
   cage_types: list[str] | None = None           # ['12', '12', '14', ...]
   cage_centers_cart: np.ndarray | None = None    # (N_cages_total, 3) nm, including supercell
   guest_cage_assignments: dict | None = None     # {guest_idx: cage_idx}
   ```

3. **`hydrate_generator.py:generate()`** (line 97-126):
   - Compute supercell cage centers from unit cell cage positions
   - Map guest molecules to nearest cage (KDTree, 0.5nm cutoff)
   - Store in HydrateStructure

### Phase 2: Basic analysis from existing structures (no MDAnalysis needed)

**Effort:** Low-Medium (3 new modules, ~300 lines total)
**Impact:** RDF, density profile, coordination number — the most commonly requested analyses

New modules:
1. **`quickice/analysis/rdf.py`** (~80 lines)
   - Reuse `scorer._calculate_oo_distances_pbc()` pattern
   - Add histogram binning on top of distance array
   - Works on any structure with positions + atom_names + cell

2. **`quickice/analysis/density_profile.py`** (~60 lines)
   - Bin atoms along chosen axis (Z for interfaces)
   - Separate ice/water/guest density using `ice_atom_count` boundary
   - numpy histogram, no new dependencies

3. **`quickice/analysis/cage_occupancy.py`** (~100 lines)
   - Requires Phase 1 cage data
   - Map guest positions → nearest cage center (cKDTree)
   - Report: per-type occupancy (small/large), total occupancy
   - Compare requested vs actual occupancy

4. **`quickice/analysis/types.py`** (~40 lines)
   ```python
   @dataclass
   class AnalysisConfig:
       analyses: list[str]          # ["rdf", "density_profile", "cage_occupancy"]
       rdf_cutoff: float = 1.0     # nm
       rdf_bin_width: float = 0.01 # nm
       density_axis: str = "z"
       density_bin_width: float = 0.1 # nm
   
   @dataclass
   class AnalysisResult:
       rdf_data: dict | None
       density_profile: dict | None
       cage_occupancy: dict | None
       hbond_stats: dict | None
   ```

### Phase 3: Analysis tab in GUI

**Effort:** Medium (follow existing tab pattern exactly)
**Impact:** Makes analysis accessible to users

New files (following exact pattern of existing tabs):
1. **`quickice/gui/analysis_panel.py`** (~200 lines)
   - Analysis type checkboxes (RDF, density profile, cage occupancy)
   - Parameter inputs (cutoff, bin width, axis)
   - Source selector (current structure / load from file)
   - Generate button + progress panel + log panel
   - Pattern: follow `hydrate_panel.py`

2. **`quickice/gui/analysis_viewer.py`** (~300 lines)
   - 3D viewer with analysis overlays (cage wireframes, color-by-parameter)
   - Matplotlib panels for RDF and density profile
   - Stacked widget: placeholder → results
   - Pattern: follow `hydrate_viewer.py`

3. **`quickice/gui/analysis_worker.py`** (~100 lines)
   - QThread-based analysis computation
   - Pattern: follow `hydrate_worker.py`

4. **Extend `constants.py`**: Add `ANALYSIS = 6` to TabIndex

5. **Extend `main_window.py`**: Add Tab 6, analysis signals, cross-tab data flow

### Phase 4: Advanced analyses (MDAnalysis for trajectories)

**Effort:** Medium-High (requires MDAnalysis dependency + trajectory I/O)
**Impact:** Enables time-series analysis of MD simulations

New modules:
1. **`quickice/analysis/trajectory_loader.py`** — MDAnalysis Universe wrapper
2. **`quickice/analysis/msd.py`** — Mean square displacement
3. **`quickice/analysis/f3f4.py`** — F3/F4 order parameters for hydrate stability
4. **`quickice/analysis/chillplus.py`** — CHILL+ ice identification
5. **`quickice/analysis/hbond_timeseries.py`** — H-bond persistence

### Recommended implementation priority

| Priority | What | Why | Dependencies |
|----------|------|-----|-------------|
| **P0** | Capture cage centers from GenIce2 | Enables everything else; tiny change | None |
| **P1** | RDF module | Most requested analysis; reuses existing KDTree code | P0 (for cage RDF) |
| **P1** | Density profile module | Simple; high value for interface structures | None |
| **P1** | Cage occupancy module | Key hydrate-specific metric | P0 |
| **P2** | Analysis tab GUI | Makes analysis user-accessible | P0+P1 |
| **P3** | F3/F4 order parameters | Hydrate stability tracking | P0 |
| **P3** | Trajectory loading (MDAnalysis) | Time-series analysis | MDAnalysis install |
| **P4** | CHILL+ classification | Advanced ice identification | Neighbor analysis |
| **P4** | MSD / diffusion | Requires trajectory loading | MDAnalysis |

---

## Summary: Data Flow for Analysis

### With current data structures (no GenIce2 changes)

```
HydrateStructure
  ├─ positions[] → RDF, density profile, coordination number, H-bond stats
  ├─ molecule_index[] → per-type filtering (water vs guest)
  ├─ cell → PBC for all distance calculations
  ├─ config.cage_occupancy_* → expected occupancy (validation target)
  └─ lattice_info.cage_counts → theoretical cage count
     Missing: cage_centers, cage_type_per_guest

InterfaceStructure
  ├─ positions[] → density profile along Z, RDF
  ├─ ice_atom_count / water_atom_count → phase boundary identification
  ├─ cell → PBC
  └─ mode → determines analysis approach (slab vs pocket vs piece)
     Missing: region labels for confined water analysis

Candidate
  ├─ positions[] → RDF, O-O distance distribution
  ├─ cell → PBC
  ├─ nmolecules → density calculation
  └─ metadata → density, T, P for validation
     Complete: sufficient for ice-phase analysis
```

### With cage data capture (P0 change)

```
Extended HydrateStructure
  ├─ [existing fields]
  ├─ cage_centers_cart[] → cage occupancy, F3/F4, cage visualization
  ├─ cage_types[] → per-type occupancy, small vs large cage analysis
  └─ guest_cage_assignments → direct occupancy measurement
```

---

## Sources

| File | Lines Examined | Purpose |
|------|---------------|---------|
| `quickice/structure_generation/types.py` | 1-722 | All data structures |
| `quickice/structure_generation/hydrate_generator.py` | 1-595 | GenIce2 data capture/loss |
| `quickice/structure_generation/generator.py` | 1-265 | Ice generation, what's exposed |
| `quickice/structure_generation/interface_builder.py` | 1-354 | Interface generation, validation |
| `quickice/structure_generation/overlap_resolver.py` | 1-218 | cKDTree PBC neighbor search |
| `quickice/structure_generation/gro_parser.py` | 1-159 | GRO file reading |
| `quickice/structure_generation/water_filler.py` | 1-687 | Water density calculations |
| `quickice/gui/molecular_viewer.py` | 1-534 | VTK rendering pipeline |
| `quickice/gui/hydrate_viewer.py` | 1-487 | Hydrate-specific VTK viewer |
| `quickice/gui/hydrate_renderer.py` | 1-628 | Hydrate rendering + H-bond detection |
| `quickice/gui/vtk_utils.py` | 1-802 | VTK conversion + PBC utilities |
| `quickice/gui/viewmodel.py` | 1-276 | MVVM ViewModel pattern |
| `quickice/gui/main_window.py` | 1-2024 | Tab structure, cross-tab data flow |
| `quickice/gui/workers.py` | 1-225 | Background worker pattern |
| `quickice/gui/constants.py` | 1-28 | Tab index constants |
| `quickice/ranking/scorer.py` | 1-373 | O-O distance analysis, density calculation |
| `quickice/ranking/types.py` | 1-58 | RankedCandidate, ScoringConfig |
| `quickice/utils/molecule_utils.py` | 1-108 | Guest molecule atom counting |
| `quickice/phase_mapping/water_density.py` | 1-117 | IAPWS-95 water density |
| `quickice/validation/validators.py` | 1-147 | Input validation |

**Live GenIce2 API inspection** (performed 2026-06-12):
- `genice2.lattices.sI.Lattice()` — cagepos, cagetype, cell, density, coord, waters, bondlen
- `genice2.lattices.sII.Lattice()` — cagepos (24 cages), cagetype
- `genice2.lattices.sH.Lattice()` — cages (formatted string), cell, coord, waters
- `genice2.genice.GenIce` post-generation — cagepos1, cagetype1, filled_cages, cell1, waters1, pairs1, groups1
