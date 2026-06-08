# External Integrations

**Analysis Date:** 2026-06-08

## APIs & External Services

**GenIce2 (In-process, no network):**
- Purpose: Ice crystal lattice generation engine — generates physically valid ice and hydrate structures with diverse hydrogen bond networks
- SDK/Client: `genice2` pip package (v2.2.13.1)
- Integration pattern:
  - Direct import in `quickice/structure_generation/generator.py`: `from genice2.plugin import safe_import`, `from genice2.genice import GenIce`
  - Lazy import with thread-safe locking in `quickice/structure_generation/hydrate_generator.py`: `import genice2.genice as genice_lib`, `from genice2.formats import gromacs`, `from genice2.lattices import sI, sII, sH`, `from genice2.molecules.tip4p import Molecule as TIP4P`
- Key classes: `GenIce(lattice, density=, reshape=)`, `safe_import('lattice'|'molecule'|'format', name)`, `gromacs.Format()`, `tip3p.Molecule()`, `TIP4P()`
- API flow:
  1. `safe_import('lattice', lattice_name).Lattice()` — load lattice module
  2. `GenIce(lattice, density=density, reshape=supercell_matrix)` — create generator
  3. `safe_import('molecule', 'tip3p').Molecule()` — load water model (3-atom for ice generation)
  4. `safe_import('format', 'gromacs').Format()` — load GROMACS formatter
  5. `ice.generate_ice(formatter=formatter, water=water, depol='strict')` — produce GRO string
- Thread safety: NOT thread-safe — GenIce uses global `np.random` state; save/restore around each call in `quickice/structure_generation/generator.py`
- Auth: None required (local computation)

**IAPWS (In-process, no network):**
- Purpose: International Association for the Properties of Water and Steam thermodynamic formulations
- SDK/Client: `iapws` pip package (v1.5.5)
- Three formulations used:
  1. `iapws._iapws._Ice(T, P) → props["rho"]` — Ice Ih density via IAPWS R10-06(2009) in `quickice/phase_mapping/ice_ih_density.py`
  2. `iapws.IAPWS95(T=T, P=P).rho` — Liquid water density (including supercooled) via IAPWS-95 in `quickice/phase_mapping/water_density.py`
  3. `iapws.IAPWS97(T=T, P=P)` — Steam tables for phase diagram saturation curve in `quickice/gui/phase_diagram_widget.py`
- Integration pattern:
  - Cached with `@lru_cache(maxsize=256)` in both density modules for performance
  - IAPWS warnings suppressed via `warnings.catch_warnings()` for metastable states and extrapolated values
  - Fallback values: Ice Ih → `0.9167 g/cm³`, Water → `0.9998 g/cm³`
- Valid ranges:
  - `_Ice`: T ≤ 273.16 K, P ≤ 208.566 MPa (raises `NotImplementedError` outside)
  - `IAPWS95`: Supports supercooled water (T < 273.15 K) via extrapolation
  - `IAPWS97`: Used for steam/liquid saturation curve in phase diagram
- Auth: None required (local computation)

**scipy (In-process, no network):**
- `scipy.spatial.cKDTree` — PBC-aware overlap detection and neighbor search
  - Used in: `quickice/structure_generation/overlap_resolver.py`, `quickice/structure_generation/ion_inserter.py`, `quickice/structure_generation/solute_inserter.py`, `quickice/structure_generation/custom_molecule_inserter.py`, `quickice/gui/vtk_utils.py`, `quickice/ranking/scorer.py`, `quickice/output/validator.py`
- `scipy.spatial.transform.Rotation` — Random molecule orientation for solute/custom molecule placement
  - Used in: `quickice/structure_generation/solute_inserter.py`, `quickice/structure_generation/custom_molecule_inserter.py`
- Usage pattern: `tree = cKDTree(positions); pairs = tree.query_pairs(cutoff)` for O(n log n) neighbor search

**VTK (In-process, no network):**
- Purpose: 3D molecular visualization with Qt integration
- SDK/Client: `vtkmodules` (v9.5.2, conda-forge)
- Qt integration: `vtkmodules.qt.QVTKRenderWindowInteractor` embedded as QWidget in PySide6 layouts
- Rendering modules used:
  - `vtkRenderer`, `vtkInteractorStyleTrackballCamera` — 3D scene and mouse controls
  - `vtkMolecule`, `vtkMoleculeMapper` — Ball-and-stick molecular rendering
  - `vtkColorTransferFunction`, `vtkFloatArray` — Atom coloring by element
  - `vtkActor`, `vtkPolyDataMapper`, `vtkPolyData`, `vtkPoints`, `vtkCellArray` — Hydrogen bond and unit cell actors
  - `vtkOutlineSource`, `vtkMatrix3x3` — Unit cell wireframe
  - `vtkWindowToImageFilter`, `vtkPNGWriter`, `vtkJPEGWriter` — Viewport screenshot export
- Availability detection: Runtime check with `_VTK_AVAILABLE` flag in all viewer modules
  - Pattern: Try `from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor`; if fails and `QUICKICE_FORCE_VTK` not set, fall back to placeholder widget
  - Files using this pattern: `quickice/gui/view.py`, `quickice/gui/interface_panel.py`, `quickice/gui/custom_molecule_viewer.py`, `quickice/gui/solute_viewer.py`, `quickice/gui/ion_viewer.py`, `quickice/gui/hydrate_viewer.py`
- Unit conversion: VTK periodic table provides radii in Å; QuickIce positions in nm → scale factor `ANGSTROM_TO_NM = 0.1`

**matplotlib (In-process, no network):**
- Purpose: Phase diagram rendering and export
- SDK/Client: `matplotlib` (v3.10.8)
- Qt integration: `matplotlib.backends.backend_qtagg.FigureCanvasQTAgg` for in-app interactive diagram in `quickice/gui/phase_diagram_widget.py`
- Static export: `matplotlib.pyplot` for PNG/SVG generation in `quickice/output/phase_diagram.py`
- Viewport export: `matplotlib.figure.Figure` for viewport image export in `quickice/gui/export.py`
- Usage: `from matplotlib.patches import Polygon` for phase region polygons; `FigureCanvasQTAgg` for interactive mouse hover/click

**Shapely (In-process, no network):**
- Purpose: Computational geometry for interactive phase diagram
- SDK/Client: `shapely` (v2.1.2)
- Usage: `shapely.geometry.Point`, `shapely.geometry.Polygon` for point-in-polygon detection in `quickice/gui/phase_diagram_widget.py`
- Used by `PhaseDetector` class for efficient phase lookup from mouse position

**spglib (In-process, no network):**
- Purpose: Space group symmetry detection for crystal structure validation
- SDK/Client: `spglib` (v2.7.0)
- Usage: `spglib.get_symmetry_dataset(cell_tuple, symprec=symprec)` in `quickice/output/validator.py`
- Returns: International space group number, symbol, Hall number, symmetry operations
- Input format: `(lattice, fractional_positions, atomic_numbers)` in Ångström (nm→Å conversion done internally)
- Also a transitive dependency of genice2 (used internally for lattice symmetry)

## Data Storage

**Databases:**
- None (no database layer)

**File Storage:**
- Local filesystem only
- Output files written to user-specified directory (default: `output/`)
- GROMACS format: `.gro` (coordinates), `.top` (topology), `.itp` (molecule topology)
- PDB format: `.pdb` (coordinates with CRYST1 records)
- Phase diagrams: `.png`, `.svg`
- Force field data: `quickice/data/*.itp`, `quickice/data/*.gro` (bundled with application)

**Caching:**
- Python `@lru_cache(maxsize=256)` — IAPWS density calculations in `quickice/phase_mapping/ice_ih_density.py` and `quickice/phase_mapping/water_density.py`
- Module-level dict `_SHARED_BOUNDARY_CACHE` — Phase diagram boundary vertex sampling in `quickice/output/phase_diagram.py` (ensures aligned polygon vertices)
- No Redis/Memcached or external caching

## Authentication & Identity

**Auth Provider:**
- None (desktop application, no user authentication, no network services)

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Bugsnag, etc.)

**Logs:**
- Python `logging` module with `logging.getLogger(__name__)` pattern throughout
- Logger names follow module hierarchy (e.g., `quickice.phase_mapping.ice_ih_density`, `quickice.gui.main_window`)
- IAPWS warnings suppressed for metastable states via `warnings.catch_warnings()` in density modules
- Warning-level logging for fallback density values in `quickice/phase_mapping/ice_ih_density.py` and `quickice/phase_mapping/water_density.py`
- No log file persistence (stdout only)

## CI/CD & Deployment

**Hosting:**
- Desktop application (no server hosting)
- Source distribution via git repository
- Windows executable via GitHub Actions artifact

**CI Pipeline:**
- GitHub Actions: `.github/workflows/build-windows.yml`
  - Trigger: Manual (`workflow_dispatch`) only
  - Runner: `windows-latest`
  - Steps: Checkout → Miniconda setup (from `environment-build.yml`) → PyInstaller build → Package docs + licenses → ZIP artifact → Upload artifact
  - Output: `quickice-v4.0.0-windows-x86_64.zip`

**Dependabot:**
- `.github/dependabot.yml` — Weekly checks for conda and pip ecosystem updates

**Build Scripts:**
- `scripts/build-linux.sh` — Linux PyInstaller build (requires `quickice` conda env activated)
- `scripts/assemble-dist.sh` — Package build output into distributable tar.gz with docs and licenses

## Environment Configuration

**Required env vars:**
- `PYTHONPATH` — Must include project root for `quickice` package import (set by `setup.sh`)

**Optional env vars:**
- `QUICKICE_FORCE_VTK` — Set to `"true"` to force VTK initialization in SSH X11 forwarding environments (checked in 6 viewer modules)
- `DISPLAY` — X11 display variable (checked by VTK availability detection in viewer modules)

**Secrets location:**
- None (no secrets required — desktop application with no network authentication)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## GROMACS Integration (File-based, No GROMACS Installation Required)

**Input:**
- Reads `.gro` files: `quickice/structure_generation/gro_parser.py` — `parse_gro_string()`, `parse_gro_file()` for GRO coordinate parsing
- Reads `.itp` files: `quickice/structure_generation/itp_parser.py` — `parse_itp_file()` for topology parsing (custom molecules)
- Water template: `quickice/data/tip4p.gro` — TIP4P water coordinates for water filling in interface generation
- Custom molecule data: `quickice/data/custom/` — User-provided `.gro`, `.itp`, `.chg`, `.top` files

**Output (GROMACS format):**
- Writes `.gro` files: `quickice/output/gromacs_writer.py`
  - `write_gro_file()` — Single-phase ice candidates
  - `write_interface_gro_file()` — Ice-water interface structures
  - `write_multi_molecule_gro_file()` — Multi-molecule structures (ice + water + ions + solutes + guests + custom)
  - Utility: `wrap_positions_into_box()`, `wrap_molecules_into_box()` — PBC wrapping
  - Utility: `compute_mw_position()` — TIP4P dummy atom position calculation
- Writes `.top` files: `quickice/output/gromacs_writer.py`
  - `write_top_file()` — Single-phase ice topology
  - `write_interface_top_file()` — Interface topology
  - `write_multi_molecule_top_file()` — Multi-molecule topology with `[molecules]` section
  - `comment_out_atomtypes_in_itp()` — Strips atomtypes from solute ITP files (avoids conflict with tip4p-ice.itp)
- Generates `.itp` content: `quickice/structure_generation/gromacs_ion_export.py`
  - `generate_ion_itp()` — Na+ and Cl- ITP from Madrid2019 parameters
  - `write_ion_itp()` — Write ion ITP to disk
  - `get_ion_molecule_section()` — Format ion `[molecules]` line for .top file
- Copies ITP files from `quickice/data/`: `tip4p-ice.itp`, `ch4_hydrate.itp`, `thf_hydrate.itp`, `ch4_liquid.itp`, `thf_liquid.itp`, custom molecule `.itp` files

**Output (PDB format):**
- `quickice/output/pdb_writer.py` — `write_pdb_with_cryst1()`, `write_ranked_candidates()`
  - CRYST1 records with unit cell parameters (a, b, c, alpha, beta, gamma)
  - Unit conversion: nm → Å for PDB output

**Molecule Naming Registry:**
- `quickice/structure_generation/moleculetype_registry.py` — `MoleculetypeRegistry` class
  - Ensures unique GROMACS moleculetype names (e.g., `CH4_H` for hydrate guests vs `CH4_L` for liquid solutes)
  - `_H` suffix for hydrate cage guests, `_L` suffix for liquid solutes
  - GRO format constraint: molecule names max 5 characters
  - Reserved names: `SOL`, `NA`, `CL`, `CH4`, `THF`, `CO2`, `H2`, `CH4_H`, `CH4_L`, `THF_H`, `THF_L`

**GRO/ITP Validation:**
- `quickice/structure_generation/molecule_validator.py` — Consistency checks between GRO and ITP files
  - Residue name mismatch detection (non-blocking warning)
  - Atom count verification
  - Generic residue names (`MOL`, `UNK`, `LIG`, etc.) exempted from mismatch warnings

**Structure Validation:**
- `quickice/output/validator.py` — `validate_space_group()`, `check_atomic_overlap()`
  - spglib for space group symmetry detection
  - cKDTree for atomic overlap detection with PBC (3×3×3 supercell approach)

## GenIce2 Lattice Mapping

**Phase ID → GenIce lattice name mapping** (in `quickice/structure_generation/mapper.py`):

| QuickIce Phase ID | GenIce Lattice | Unit Cell Molecules | Supported |
|-------------------|---------------|--------------------|-----------|
| ice_ih | ice1h | 16 | Yes |
| ice_ic | ice1c | 8 | Yes |
| ice_ii | ice2 | 12 | Yes |
| ice_iii | ice3 | 12 | Yes |
| ice_v | ice5 | 28 | Yes |
| ice_vi | ice6 | 10 | Yes |
| ice_vii | ice7 | 16 | Yes |
| ice_viii | ice8 | 64 | Yes |
| ice_ix | — | — | No (proton-ordered, not in GenIce) |
| ice_xi | — | — | No (proton-ordered, not in GenIce) |
| ice_xv | — | — | No (proton-ordered, not in GenIce) |
| ice_x | — | — | No (symmetric H bonds, not in GenIce) |

**Hydrate lattice mapping:**

| QuickIce Type | GenIce Lattice | Water Molecules/Unit Cell | Guest Types |
|---------------|---------------|--------------------------|-------------|
| sI | CS1 | 46 | CH4, THF |
| sII | CS2 | 136 | CH4, THF |
| sH | sH | 34 | CH4 (small/medium), THF (large) |

## Water Model Pipeline

**Generation:** TIP3P (3-atom: O, H, H) via `safe_import('molecule', 'tip3p').Molecule()`
  - TIP3P used because interface modes expect 3 atoms per molecule
  
**Export:** TIP4P-ICE (4-atom: OW, HW1, HW2, MW) via `tip4p-ice.itp`
  - TIP3P → TIP4P-ICE normalization at export time
  - MW (dummy atom) position computed from: `MW = O + α*(M - O)` where `TIP4P_ICE_ALPHA = 0.13458335`
  - Hydrate generation uses TIP4P directly: `from genice2.molecules.tip4p import Molecule as TIP4P`

---

*Integration audit: 2026-06-08*
