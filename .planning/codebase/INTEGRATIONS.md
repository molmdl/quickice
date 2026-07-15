# External Integrations

**Analysis Date:** 2026-07-14

## APIs & External Services

**GenIce2 Plugin System (core physics engine):**
- GenIce2 2.2.13.1 - Ice + clathrate hydrate lattice generation via plugin architecture
  - SDK/Client: `genice2.plugin.safe_import` for dynamic lattice/molecule/format loading
  - Ice path (`quickice/structure_generation/generator.py`): `safe_import('lattice', name).Lattice()`, `safe_import('molecule', 'tip3p').Molecule()`, `safe_import('format', 'gromacs').Format()` (all via `safe_import`)
  - Hydrate path (`quickice/structure_generation/hydrate_generator.py`): mixed strategy — direct imports `from genice2.lattices import sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime` and `from genice2.formats import gromacs`; falls back to `safe_import('lattice', name)` for numeric-named lattices (`16` = Ice XVI, `17` = Ice XVII) which cannot be `from`-imported
  - Ice lattice plugins used: `ice1h`, `ice1c`, `ice2`, `ice3`, `ice5`, `ice6`, `ice7`, `ice8` (mapped via `quickice/structure_generation/mapper.py:get_genice_lattice_name()`)
  - Hydrate lattice plugins used (10 types): `sI`, `sII`, `sH`, `c0te`, `c1te`, `c2te`, `ice1hte`, `sTprime`, `16`, `17` (mapped in `hydrate_generator.py:_LATTICE_MODULES`)
  - Molecule plugins used: `tip3p` (3-atom water for ice generation), `tip4p` (4-atom water for hydrate generation)
  - Format plugins used: `gromacs` (GRO output format)
  - Auth: None (local computation, no network)
  - Thread safety: `_genice_lock = threading.Lock()` in `hydrate_generator.py:39` guards lazy GenIce2 import (`_ensure_genice_import()`); ice generator is NOT thread-safe (uses global `np.random` state, saved/restored per call in `generator.py:_generate_single()`)

**IAPWS Thermodynamic Properties:**
- iapws 1.5.5 - International Association for the Properties of Water and Steam formulations
  - `iapws._iapws._Ice` for Ice Ih density (R10-06(2009)) — `quickice/phase_mapping/ice_ih_density.py`
  - Melting curve equations: `quickice/phase_mapping/melting_curves.py` (IAPWS R14-08(2011)) — pure Python math functions, not API calls
  - Water density: `quickice/phase_mapping/water_density.py` (IAPWS-95 via `iapws.IAPWS95`)
  - Auth: None (local computation, no network)

**GROMACS Simulation Engine (external binary, test-only):**
- GROMACS `gmx` command-line tool
  - Used for: `gmx grompp` validation in e2e tests (NOT used by the application itself at runtime)
  - Availability: Optional; tests use `gmx_skipif` marker from `tests/conftest.py` to skip if `gmx` not on PATH
  - Detection: `shutil.which("gmx")` in `tests/conftest.py:_gmx_available()` (line 18-20)
  - `gmx_skipif = pytest.mark.skipif(not _gmx_available(), reason="GROMACS (gmx) not found on PATH")` (line 24-27)
  - Test MDP file: `tests/em.mdp` (energy minimization parameters for grompp validation)
  - Auth: None (local binary, no network)

## Data Storage

**Databases:**
- No database; all data is in-memory or file-based

**File Storage:**
- Local filesystem only
- Output directory (default: `output/`) for generated PDB, GRO, TOP, ITP, PNG, SVG files
- Bundled data in `quickice/data/`:
  - `tip4p-ice.itp` - TIP4P-ICE water model GROMACS topology (canonical OW_ice/HW_ice/MW atomtypes + virtual_sites3)
  - `tip4p-ice.itp.bak` - Backup of water model topology
  - `tip4p.gro` - TIP4P water molecule coordinate template
  - `ch4.itp`, `thf.itp` - Guest molecule topologies (hydrate)
  - `ch4_hydrate.itp`, `thf_hydrate.itp` - Guest topologies for hydrate cages (`_H` suffix moleculetype)
  - `ch4_liquid.itp`, `thf_liquid.itp` - Solute topologies for liquid phase (`_L` suffix moleculetype)
  - `custom/` - Directory for custom molecule templates: `etoh.gro`, `etoh.itp`, `etoh.chg`, `etoh.top`, plus `test_invalid/` subdir for negative tests
  - `examples/` - Example input files: `custom_positions.csv`

**Caching:**
- `functools.lru_cache` in `quickice/phase_mapping/ice_ih_density.py` (IAPWS density, maxsize=256)
- `functools.lru_cache` in `quickice/phase_mapping/water_density.py` (water density, maxsize=256)
- `functools.lru_cache` in `quickice/structure_generation/water_filler.py` (water template loading)
- Module-level `_SHARED_BOUNDARY_CACHE` dict in `quickice/output/phase_diagram.py` (boundary vertices)
- No Redis, Memcached, or external caching

## Authentication & Identity

**Auth Provider:**
- None; desktop application with no user accounts or authentication
- No login, no API keys, no tokens

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Rollbar, or similar)
- Errors handled via Python exceptions and the `logging` module

**Logs:**
- Python `logging` module with `logging.getLogger(__name__)` pattern throughout
- No centralized log aggregation
- No log file configuration visible; defaults to stderr
- CLI errors printed to `sys.stderr`
- CLI pipeline progress: `quickice/cli/pipeline.py:report_progress()` prints `[PROGRESS]` messages to stderr

## CI/CD & Deployment

**Hosting:**
- N/A (desktop application, not hosted)

**CI Pipeline:**
- GitHub Actions (`.github/workflows/build-windows.yml`)
  - Manual trigger only (`workflow_dispatch`) — no automated CI on push/PR
  - Runs on `windows-latest`
  - Uses `actions/checkout@v6`, `conda-incubator/setup-miniconda@v3` with `environment-build.yml` → env `quickice-build`
  - Sets `PYTHONPATH` to project root, runs `pyinstaller --clean quickice-gui.spec`
  - Packages docs/licenses, creates `quickice-v4.5.0-windows-x86_64.zip` via 7z (NOTE: zip name is pinned to v4.5.0 and drifts from canonical `__version__ = "4.7.0"`)
  - Uses `actions/upload-artifact@v7` for artifact storage (artifact name: `windows-executable`)

**Build Scripts:**
- `scripts/build-linux.sh` - Linux build (requires `quickice` conda env activated; checks `$CONDA_DEFAULT_ENV`; calls `pyinstaller --clean quickice-gui.spec`; output `dist/quickice-gui/quickice-gui`)
- `scripts/assemble-dist.sh` - Packages `dist/quickice-gui/` into versioned `quickice-{version}-linux-x86_64.tar.gz` with README, README_bin, LICENSE, docs, licenses (takes version as `$1` arg)
- `scripts/run_gui_ssh.sh`, `scripts/run_oc.sh` - GUI launch helpers

**Dependabot:**
- `.github/dependabot.yml` configured for `conda` and `pip` ecosystems (weekly, PRs disabled with `open-pull-requests-limit: 0`)

## Environment Configuration

**Required env vars:**
- `PYTHONPATH` - Must include project root (set by `setup.sh`; also set in CI workflow)

**Optional env vars (Linux display detection — `quickice/entry.py:_has_display()`):**
- `DISPLAY` - X11 display (local displays start with `:`, remote SSH X11 with `localhost:n.n`)
- `WAYLAND_DISPLAY` - Wayland display
- `QT_QPA_PLATFORM` - Qt platform plugin (checked for values `wayland`, `xcb`, `offscreen`)

**Optional env vars (VTK availability in GUI viewers):**
- `QUICKICE_FORCE_VTK` - Set to `true` (case-insensitive) to force-enable VTK rendering when running over SSH X11 forwarding (indirect rendering). Checked in 6 viewer modules: `quickice/gui/view.py:26`, `quickice/gui/solute_viewer.py:25`, `quickice/gui/interface_panel.py:35`, `quickice/gui/hydrate_viewer.py:26`, `quickice/gui/ion_viewer.py:26`, `quickice/gui/custom_molecule_viewer.py:26`
  - Pattern: if `DISPLAY` contains `localhost` (SSH X11 forwarding), VTK is disabled unless `QUICKICE_FORCE_VTK=true`; local displays assume VTK works
  - Default: VTK assumed unavailable over SSH X11 (NVIDIA GLX crashes with indirect rendering)

**Set-at-runtime env var (remote OpenGL fix — `quickice/gui/main_window.py:_configure_opengl_for_remote()`):**
- `__GLX_VENDOR_LIBRARY_NAME` - Set to `mesa` at runtime (line 2139) when `DISPLAY` indicates a remote (non-`:`-prefixed) session, to avoid VTK segfault via NVIDIA GLX over SSH X11. Only applied in `run_app()` before `QApplication` is created.

**Secrets location:**
- Not applicable (no secrets or API keys)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## GROMACS Format Integration

**GROMACS File Export (primary output — `quickice/output/gromacs_writer.py`):**
- `.gro` files - Coordinate files
  - `write_gro_file()` for ice candidates
  - `write_interface_gro_file()` for ice-water interfaces
  - `write_solute_gro_file()` for solute structures
  - `write_ion_gro_file()` for ion structures
  - `write_custom_molecule_gro_file()` for custom molecule systems
  - `write_multi_molecule_gro_file()` for mixed-molecule systems
- `.top` files - Topology files (6 corresponding writers for each structure type)
  - All 6 use `comb-rule=2` (Lorentz-Berthelot, AMBER/GAFF2 convention)
  - All 6 reference `TIP4P_ICE_OW_SIGMA` and `TIP4P_ICE_OW_EPSILON` module-level constants (lines 56-57) via `:.5e` f-strings
  - `[ defaults ]` writer locations: lines 962, 1557, 1959, 2630, 3219, 3929 (one per writer)
- `.itp` files - Include topology files (copied from `quickice/data/`, modified via `comment_out_atomtypes_in_itp()`)
  - `tip4p-ice.itp` - Water model topology (always included)
  - `{guest}_hydrate.itp` - Guest molecule topology (when hydrate guests present; `_H` suffix moleculetype)
  - `{solute}_liquid.itp` - Liquid solute topology (when solutes present; e.g. `ch4_liquid.itp`, `thf_liquid.itp`; `_L` suffix moleculetype)
  - Custom molecule `.itp` files (when custom molecules present; atomtypes commented)
  - Ion topologies: generated dynamically by `quickice/structure_generation/gromacs_ion_export.py` (`generate_ion_itp()`, `write_ion_itp()`, `add_ion_molecules_to_topology()`, `get_ion_molecule_section()`)

**GROMACS ITP Path Resolution:**
- CLI path: `quickice/cli/itp_helpers.py`
  - `get_hydrate_guest_itp_path(guest_type)` - Resolves `{guest}_hydrate.itp` with case normalization
  - `get_solute_liquid_itp_path(solute_type)` - Resolves `{solute}_liquid.itp` with case normalization
  - `get_tip4p_itp_path()` - Delegates to `quickice/output/gromacs_writer.py`
  - `copy_itp_files_for_structure()` - Bundles all required ITP files for a given step type
- GUI path: `quickice/gui/hydrate_export.py`
  - `_get_guest_itp_path()`, `_get_hydrate_guest_itp_path()` - Similar resolution with project-root fallback

**Atomtypes Commenting:**
- `comment_out_atomtypes_in_itp()` in `quickice/output/gromacs_writer.py` - Comments out `[ atomtypes ]` section in ITP files to prevent conflicts with TIP4P-ICE force field
- Used by BOTH GUI exporters (`quickice/gui/export.py`) and CLI pipeline (`quickice/cli/itp_helpers.py`)
- Applied to: custom molecule ITP, solute liquid ITP, hydrate guest ITP

**GROMACS File Parsing (input):**
- `quickice/structure_generation/gro_parser.py` - Parses `.gro` coordinate strings/files
  - `parse_gro_string()` for GenIce output parsing
  - `parse_gro_file()` for custom molecule template reading
- `quickice/structure_generation/itp_parser.py` - Parses `.itp` topology files
  - Extracts moleculetype name, atom count, atom types/names, atomtypes section presence
  - Used for custom molecule integration and moleculetype registry

**PDB File Export:**
- `quickice/output/pdb_writer.py` - PDB format with CRYST1 records
  - `write_pdb_with_cryst1()` for single candidates
  - `write_ranked_candidates()` for batch output

**Image Export:**
- Matplotlib `savefig()` for phase diagram PNG/SVG (`quickice/output/phase_diagram.py`)
- VTK `vtkPNGWriter`/`vtkJPEGWriter` for 3D viewport screenshots (`quickice/gui/export.py:851,854`, imported via `from vtkmodules.all import vtkPNGWriter, vtkJPEGWriter`)

## Physics Integration Details

**Phase Mapping (IAPWS-based — `quickice/phase_mapping/`):**
- `melting_curves.py` - IAPWS R14-08(2011) melting curves for Ih, III, V, VI, VII
- `solid_boundaries.py` - Linear interpolation for solid-solid phase boundaries
- `triple_points.py` - Triple point reference data
- `ice_ih_density.py` - IAPWS R10-06(2009) Ice Ih density via `iapws._iapws._Ice()`
- `water_density.py` - Water density calculations for interface generation via `iapws.IAPWS95`
- `lookup.py` - `lookup_phase(T, P)` entry point used by both CLI and GUI to map (T,P) → phase_id + density

**GenIce2 Structure Generation:**
- `quickice/structure_generation/generator.py` - `IceStructureGenerator` wraps GenIce2 API for ice crystal generation
  - `safe_import('lattice', name).Lattice()` for dynamic lattice loading
  - `safe_import('molecule', 'tip3p').Molecule()` for 3-atom water model (ice generated as TIP3P, normalized to TIP4P-ICE at export)
  - `safe_import('format', 'gromacs').Format()` for GRO output
  - `GenIce(lattice, density=..., reshape=...)` for structure generation
  - `ice.generate_ice(formatter=..., water=..., depol='strict')` for actual generation
  - Saves/restores global `np.random` state per call (NOT thread-safe)
- `quickice/structure_generation/hydrate_generator.py` - `HydrateStructureGenerator` wraps GenIce2 for hydrate generation
  - Lazy import guarded by `_genice_lock = threading.Lock()` (line 39) in `_ensure_genice_import()`
  - Direct imports for named lattices: `from genice2.lattices import sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime`
  - `safe_import('lattice', name)` for numeric-named lattices `16` (Ice XVI), `17` (Ice XVII) at generation time
  - `from genice2.molecules.tip4p import Molecule as TIP4P` for TIP4P water model
  - `from genice2.formats import gromacs` for GRO format

## CLI Pipeline Integration

**Pipeline Orchestrator:**
- `quickice/cli/pipeline.py` - `CLIPipeline` class runs ordered steps (source → interface → custom → solute → ion → export) with fail-fast semantics
- `quickice/cli/parser.py` - `create_parser()` / `get_arguments()` for CLI argument definition with custom validators
- `quickice/entry.py` - `main()` routes between CLI and GUI based on `--cli`/`--gui` flags and implicit pipeline flag detection (`_has_pipeline_flags()`)

**Validator Integration with Parser:**
- `quickice/cli/parser.py` imports all 7 validators from `quickice/validation/validators.py`:
  - `validate_temperature`, `validate_pressure`, `validate_nmolecules`, `validate_positive_float`, `validate_box_dimension` (original 5)
  - `validate_concentration_range` — used by `--custom-concentration`, `--solute-concentration`, `--ion-concentration`
  - `validate_occupancy_range` — used by `--cage-occupancy-small`, `--cage-occupancy-large`
- Each validator is assigned as `type=` to the corresponding `add_argument()` call, so argparse auto-applies validation during parsing

**Error Handling in Pipeline (`quickice/cli/pipeline.py`):**
- Uses structured exception catching (NOT bare `except Exception` per AGENTS.md constraint):
  - `OSError` for directory creation failures
  - `FileNotFoundError` for missing input GRO/ITP/CSV files
  - `ValueError` for invalid configurations and missing prerequisite structures
  - `InsertionError` for custom molecule insertion failures
  - `ImportError` for missing packages in each step (lazy imports)
  - Export step catches `(OSError, ValueError)` — broader but still typed
- Hydrate export wrapper in `_run_export_step()` has atom count assertion: `assert water_atom_count + guest_atom_count == len(hydrate.positions), ...` (catches water_count × 4 mismatch bugs)

## VTK / Qt GUI Integration

**VTK-Qt Widget Embedding:**
- `quickice/gui/molecular_viewer.py` - Base viewer using `from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor` (line 10) + `from vtkmodules.all import ...` (line 11)
- Per-tab viewers (lazy-import VTK inside class bodies): `solute_viewer.py`, `interface_viewer.py`, `hydrate_viewer.py`, `ion_viewer.py`, `custom_molecule_viewer.py`
- Renderers: `hydrate_renderer.py`, `solute_renderer.py`, `custom_molecule_renderer.py`, `ion_renderer.py`, `vtk_utils.py` — all use `from vtkmodules.all import ...`
- `quickice/gui/dual_viewer.py` - Dual-pane viewer using `from vtkmodules.all import vtkCommand`

**VTK Availability Detection Pattern (SSH X11):**
- Each viewer module probes VTK availability at import time:
  - If `os.environ.get('DISPLAY')` contains `localhost` → likely SSH X11 forwarding → VTK disabled unless `QUICKICE_FORCE_VKT=true`
  - Otherwise (local display or no display) → VTK assumed available; `from quickice.gui.dual_viewer import DualViewerWidget` attempted in try/except
- On failure, `_VTK_AVAILABLE = False` and viewer gracefully degrades

## Test Infrastructure Integration

**e2e Export Helpers (`tests/e2e_export_helpers.py`):**
- `StagingResult = namedtuple("StagingResult", ["staged", "missing"])` — result from ITP staging
- `parse_top_includes()`, `parse_top_molecules()`, `parse_gro_residue_names()` — GRO/TOP parsing for assertions
- `_stage_itp_files()` — Copies #include'd ITP files to workspace with atomtypes commented out; returns `StagingResult`
- `assert_itp_completeness()` — Asserts every #include'd ITP file (except ion.itp) exists in workspace (catches "top references ITP but file missing from export" bugs)
- `run_gmx_grompp()` — Runs `gmx grompp` in workspace directory; returns `(exit_code, stderr_text)`
- Chain-building helpers: `_insert_custom_molecules()`, `_insert_solutes()`, `_insert_ions()`, `_insert_ions_from_solute()`, `_solute_to_ion_source()`, `_make_slab_interface()`, `_hydrate_sI_ch4_candidate()`, etc.
- Data paths: `DATA_DIR`, `ETOH_GRO`, `ETOH_ITP` — test molecule templates (points at `quickice/data/custom/etoh.*`)

**GROMACS Availability Skip (`tests/conftest.py`):**
- `_gmx_available()` uses `shutil.which("gmx")` for detection (line 18-20)
- `gmx_skipif = pytest.mark.skipif(not _gmx_available(), reason="GROMACS (gmx) not found on PATH")` (line 24-27)
- Applied to all test classes that call `gmx grompp` via `@gmx_skipif` decorator

**Subprocess Test Helper (`tests/conftest.py:run_quickice()`):**
- `run_quickice(*args, timeout=60)` — Runs `python -m quickice` (canonical invocation, not `quickice.py`); returns `(return_code, stdout, stderr)`

**Module-Scoped Fixtures (`tests/conftest.py`):**
- Ice fixtures: `ice_ih_candidate`, `ice_ic_candidate` (module-scoped, amortize ~3-5s GenIce2 calls)
- Hydrate fixtures: `hydrate_sI_ch4_candidate`, `hydrate_sI_thf_candidate`, `hydrate_sII_ch4_candidate` (+ raw `_structure` variants)
- Interface fixtures: `interface_slab`, `interface_pocket`, `interface_hydrate_slab`
- `PHASE_CONDITIONS` dict — verified (T,P) pairs producing each ice phase (used by fixtures via `lookup_phase()`)
- No `qtbot` or `QApplication` fixture — these tests are API-only, no GUI

**Parameterized grompp Validation:**
- `tests/test_e2e_gmx_param_validation.py` — `pytest.mark.parametrize` with `ChainParams` NamedTuple
- Covers 27 untested hydrate→interface chain combinations
- Uses `gmx_skipif` marker for CI environments without GROMACS

---

*Integration audit: 2026-07-14*
