# External Integrations

**Analysis Date:** 2026-05-22

## APIs & External Services

**Scientific Libraries (in-process, no network calls):**

- **GenIce2** - Ice crystal lattice generation engine
  - SDK/Client: `genice2` pip package (v2.2.13.1)
  - Usage: Generates ice lattice structures (Ice Ih, Ic, II, III, V, VI, VII, VIII) and hydrate lattices (sI, sII, sH)
  - Integration pattern: Lazy import with thread-safe locking in `quickice/structure_generation/hydrate_generator.py`; direct import in `quickice/structure_generation/generator.py`
  - Key classes: `GenIce`, `safe_import`, `gromacs` format handler, `TIP4P` molecule, lattice modules (sI, sII, sH)
  - No authentication required (local computation)

- **IAPWS (iapws library)** - International Association for the Properties of Water and Steam thermodynamic formulations
  - SDK/Client: `iapws` pip package (v1.5.5)
  - Usage: Three IAPWS formulations used:
    1. `_Ice(T, P)` → `props["rho"]` - Ice Ih density via IAPWS R10-06(2009) in `quickice/phase_mapping/ice_ih_density.py`
    2. `IAPWS95(T=T, P=P).rho` - Liquid water density via IAPWS-95 in `quickice/phase_mapping/water_density.py`
    3. `IAPWS97(T=T, P=P)` - Steam tables for phase diagram saturation curve in `quickice/gui/phase_diagram_widget.py`
  - Integration pattern: Cached with `@lru_cache(maxsize=256)` in both density modules; warnings suppressed for metastable states
  - No authentication required (local computation)

- **scipy** - Scientific computing algorithms
  - `scipy.spatial.cKDTree` - PBC-aware overlap detection in `quickice/structure_generation/overlap_resolver.py`, `quickice/structure_generation/ion_inserter.py`, `quickice/structure_generation/solute_inserter.py`, `quickice/structure_generation/custom_molecule_inserter.py`, `quickice/gui/vtk_utils.py`, `quickice/ranking/scorer.py`
  - `scipy.spatial.transform.Rotation` - Molecule orientation for solute/custom molecule placement in `quickice/structure_generation/solute_inserter.py`, `quickice/structure_generation/custom_molecule_inserter.py`

- **VTK** - 3D visualization toolkit
  - SDK/Client: `vtkmodules` (v9.5.2, conda-forge)
  - Usage: Molecular rendering (vtkMolecule, vtkMoleculeMapper), hydrogen bond visualization, viewport screenshots
  - Qt integration: `vtkmodules.qt.QVTKRenderWindowInteractor` embedded in PySide6 widgets
  - Rendering modules used: `vtkRenderer`, `vtkInteractorStyleTrackballCamera`, `vtkMoleculeMapper`, `vtkColorTransferFunction`, `vtkWindowToImageFilter`, `vtkPNGWriter`, `vtkJPEGWriter`
  - Availability check: Runtime detection with fallback for SSH X11 forwarding (`_VTK_AVAILABLE` flag in viewer modules)

- **matplotlib** - Plotting library
  - SDK/Client: `matplotlib` (v3.10.8)
  - Usage: Phase diagram rendering with Qt embedding (`FigureCanvasQTAgg`), viewport export (PNG/JPEG)
  - Integration: `matplotlib.backends.backend_qtagg.FigureCanvasQTAgg` for in-app diagram; `matplotlib.pyplot` for static PNG/SVG generation

- **Shapely** - Computational geometry
  - SDK/Client: `shapely` (v2.1.2)
  - Usage: Phase polygon construction and point-in-polygon testing for interactive phase diagram
  - Integration: `shapely.geometry.Point`, `shapely.geometry.Polygon` in `quickice/gui/phase_diagram_widget.py`

- **NumPy** - Numerical computing
  - SDK/Client: `numpy` (v2.4.3)
  - Usage: Core array operations for all molecular coordinates, cell matrices, density calculations
  - Integration: Everywhere — positions, cells, supercell calculations, neighbor search, density computation

## Data Storage

**Databases:**
- None (no database layer)

**File Storage:**
- Local filesystem only
  - Output files written to user-specified directory (default: `output/`)
  - GROMACS format: `.gro` (coordinates), `.top` (topology), `.itp` (molecule topology)
  - PDB format: `.pdb` (coordinates with CRYST1 records)
  - Phase diagrams: `.png`, `.svg`
  - Force field data: `quickice/data/*.itp`, `quickice/data/*.gro`

**Caching:**
- Python `@lru_cache(maxsize=256)` - IAPWS density calculations in `quickice/phase_mapping/ice_ih_density.py` and `quickice/phase_mapping/water_density.py`
- Matplotlib boundary sampling cache (`_SHARED_BOUNDARY_CACHE`) - Phase diagram polygon vertices in `quickice/output/phase_diagram.py`
- No Redis/Memcached or external caching

## Authentication & Identity

**Auth Provider:**
- None (desktop application, no user authentication)

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Bugsnag, etc.)

**Logs:**
- Python `logging` module with `logging.getLogger(__name__)` pattern
- Logger names follow module hierarchy (e.g., `quickice.phase_mapping.ice_ih_density`, `quickice.gui.main_window`)
- IAPWS warnings suppressed for metastable states via `warnings.catch_warnings()` in density modules
- Warning-level logging for fallback density values in `quickice/phase_mapping/ice_ih_density.py` and `quickice/phase_mapping/water_density.py`

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
- `.github/dependabot.yml` - Weekly checks for conda and pip ecosystem updates (PR limit: 0, so only detection, no auto-PRs)

## Environment Configuration

**Required env vars:**
- `PYTHONPATH` - Must include project root for `quickice` package import (set by `setup.sh`)

**Optional env vars:**
- `QUICKICE_FORCE_VTK` - Set to `"true"` to force VTK initialization in SSH X11 forwarding environments
- `DISPLAY` - X11 display variable (checked by VTK availability detection in viewer modules)

**Secrets location:**
- None (no secrets required — desktop application with no network authentication)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## GROMACS Integration (File-based)

**Input:**
- Reads `.gro` files: `quickice/structure_generation/gro_parser.py` (GRO coordinate parsing)
- Reads `.itp` files: `quickice/structure_generation/itp_parser.py` (topology parsing for custom molecules)
- Water template: `quickice/data/tip4p.gro` (TIP4P water coordinates for water filling)

**Output:**
- Writes `.gro` files: `quickice/output/gromacs_writer.py` - `write_gro_file()`, `write_interface_gro_file()`, `write_ion_gro_file()`, `write_solute_gro_file()`, `write_multi_molecule_gro_file()`
- Writes `.top` files: `quickice/output/gromacs_writer.py` - `write_top_file()`, `write_interface_top_file()`, `write_ion_top_file()`, `write_solute_top_file()`, `write_multi_molecule_top_file()`
- Generates `.itp` content: `quickice/structure_generation/gromacs_ion_export.py` - `generate_ion_itp()`, `write_ion_itp()`
- Copies ITP files: `tip4p-ice.itp`, `ch4_hydrate.itp`, `thf_hydrate.itp`, `ch4_liquid.itp`, `thf_liquid.itp`, `ion.itp`
- Utility functions: `comment_out_atomtypes_in_itp()`, `detect_guest_type_from_atoms()`, `wrap_molecules_into_box()`, `wrap_positions_into_box()`, `compute_mw_position()`, `get_tip4p_itp_path()`

**PDB Output:**
- `quickice/output/pdb_writer.py` - `write_pdb_with_cryst1()`, `write_ranked_candidates()` (CRYST1 records with cell parameters)

**Molecule Naming Registry:**
- `quickice/structure_generation/moleculetype_registry.py` - Ensures unique GROMACS moleculetype names (e.g., `CH4_H` for hydrate guests vs `CH4_L` for liquid solutes)

## GenIce2 Lattice Mapping

**Phase ID → GenIce lattice name mapping** (in `quickice/structure_generation/mapper.py`):

| QuickIce Phase ID | GenIce Lattice | Unit Cell Molecules |
|-------------------|---------------|--------------------|
| ice_ih | ice1h | 16 |
| ice_ic | ice1c | 8 |
| ice_ii | ice2 | 12 |
| ice_iii | ice3 | 12 |
| ice_v | ice5 | 28 |
| ice_vi | ice6 | 10 |
| ice_vii | ice7 | 16 |
| ice_viii | ice8 | 64 |

**Hydrate lattice mapping:**

| QuickIce Type | GenIce Lattice | Water Molecules/Unit Cell |
|---------------|---------------|--------------------------|
| sI | CS1 | 46 |
| sII | CS2 | 136 |
| sH | sH | 34 |

---

*Integration audit: 2026-05-22*
