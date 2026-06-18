# External Integrations

**Analysis Date:** 2026-06-18

## APIs & External Services

**GenIce2 Plugin System:**
- GenIce2 2.2.13.1 - Ice lattice generation via plugin architecture
  - SDK/Client: `genice2.plugin.safe_import` for dynamic lattice/molecule/format loading
  - Usage: `safe_import('lattice', 'ice1h').Lattice()` in `quickice/structure_generation/generator.py`
  - Lattice plugins used: `ice1h`, `ice1c`, `ice2`, `ice3`, `ice5`, `ice6`, `ice7`, `ice8`, `sI`, `sII`, `sH`
  - Molecule plugins used: `tip3p` (3-atom water for ice generation), `tip4p` (4-atom water for hydrate generation)
  - Format plugins used: `gromacs` (GRO output format)
  - Auth: None (local computation, no network)

**IAPWS Thermodynamic Properties:**
- iapws 1.5.5 - International Association for the Properties of Water and Steam formulations
  - SDK/Client: `iapws._iapws._Ice` for Ice Ih density (R10-06(2009))
  - Used in: `quickice/phase_mapping/ice_ih_density.py` (density calculation for Ice Ih)
  - Melting curve equations: `quickice/phase_mapping/melting_curves.py` (IAPWS R14-08(2011))
  - Water density: `quickice/phase_mapping/water_density.py` (IAPWS-95 via `iapws.IAPWS95`)
  - Auth: None (local computation, no network)
  - Note: Melting curves are implemented as pure Python math functions, not API calls

**GROMACS Simulation Engine (external binary):**
- GROMACS `gmx` command-line tool
  - Used for: `gmx grompp` validation in e2e tests (NOT used by the application itself at runtime)
  - Availability: Optional; tests use `gmx_skipif` marker from `tests/conftest.py` to skip if `gmx` not on PATH
  - Detection: `shutil.which("gmx")` in `tests/conftest.py:_gmx_available()`
  - Test MDP file: `tests/em.mdp` (energy minimization parameters for grompp validation)
  - Auth: None (local binary, no network)

## Data Storage

**Databases:**
- No database; all data is in-memory or file-based

**File Storage:**
- Local filesystem only
- Output directory (default: `output/`) for generated PDB, GRO, TOP, ITP, PNG, SVG files
- Bundled data in `quickice/data/`:
  - `tip4p-ice.itp` - TIP4P-ICE water model GROMACS topology
  - `tip4p.gro` - TIP4P water molecule coordinate template
  - `ch4.itp`, `thf.itp` - Guest molecule topologies (hydrate)
  - `ch4_hydrate.itp`, `thf_hydrate.itp` - Guest topologies for hydrate cages
  - `ch4_liquid.itp`, `thf_liquid.itp` - Solute topologies for liquid phase (added in Phases 34.5-37)
  - `custom/` - Directory for custom molecule templates (`etoh.gro`, `etoh.itp`, `etoh.chg`, `etoh.top`)
  - `examples/` - Example input files (`custom_positions.csv`)

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
- Errors handled via Python exceptions and `logging` module

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
  - Manual trigger only (`workflow_dispatch`)
  - Runs on `windows-latest`
  - Uses `conda-incubator/setup-miniconda@v3` with `environment-build.yml`
  - Builds Windows executable via `pyinstaller --clean quickice-gui.spec`
  - Packages as `.zip` artifact: `quickice-v4.0.0-windows-x86_64.zip`
  - Uses `actions/upload-artifact@v7` for artifact storage

**Build Scripts:**
- `scripts/build-linux.sh` - Linux build (requires `quickice` conda env activated, calls `pyinstaller --clean quickice-gui.spec`)
- `scripts/assemble-dist.sh` - Packages `dist/quickice-gui/` into versioned `quickice-{version}-linux-x86_64.tar.gz` with README, LICENSE, docs, licenses

**Dependabot:**
- `.github/dependabot.yml` configured for conda and pip ecosystems (weekly, PRs disabled with `open-pull-requests-limit: 0`)

## Environment Configuration

**Required env vars:**
- `PYTHONPATH` - Must include project root (set by `setup.sh`)

**Optional env vars (Linux display detection):**
- `DISPLAY` - X11 display (checked by `quickice/entry.py:_has_display()`)
- `WAYLAND_DISPLAY` - Wayland display (checked by `quickice/entry.py:_has_display()`)
- `QT_QPA_PLATFORM` - Qt platform plugin (checked for `wayland`, `xcb`, `offscreen`)

**Secrets location:**
- Not applicable (no secrets or API keys)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## GROMACS Format Integration

**GROMACS File Export (primary output):**
- `.gro` files - Coordinate files via `quickice/output/gromacs_writer.py`
  - `write_gro_file()` for ice candidates
  - `write_interface_gro_file()` for ice-water interfaces
  - `write_solute_gro_file()` for solute structures
  - `write_ion_gro_file()` for ion structures
  - `write_custom_molecule_gro_file()` for custom molecule systems
  - `write_multi_molecule_gro_file()` for mixed-molecule systems
- `.top` files - Topology files (6 corresponding writers for each structure type)
  - All 6 use `comb-rule=2` (Lorentz-Berthelot, AMBER/GAFF2 convention)
  - All 6 reference `TIP4P_ICE_OW_SIGMA` and `TIP4P_ICE_OW_EPSILON` module-level constants
  - `[ defaults ]` line: `1  2  yes  0.5  0.8333`
- `.itp` files - Include topology files (copied from `quickice/data/`, modified via `comment_out_atomtypes_in_itp()`)
  - `tip4p-ice.itp` - Water model topology (always included)
  - `{guest}_hydrate.itp` - Guest molecule topology (when hydrate guests present)
  - `{solute}_liquid.itp` - Liquid solute topology (when solutes present; e.g. `ch4_liquid.itp`, `thf_liquid.itp`)
  - Custom molecule `.itp` files (when custom molecules present; atomtypes commented)
  - `na.itp`, `cl.itp` - Ion topologies (generated by `quickice/structure_generation/gromacs_ion_export.py`)

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
- Matplotlib `savefig()` for phase diagram PNG/SVG
- VTK `vtkPNGWriter`/`vtkJPEGWriter` for 3D viewport screenshots

## Physics Integration Details

**Phase Mapping (IAPWS-based):**
- `quickice/phase_mapping/melting_curves.py` - IAPWS R14-08(2011) melting curves for Ih, III, V, VI, VII
- `quickice/phase_mapping/solid_boundaries.py` - Linear interpolation for solid-solid phase boundaries
- `quickice/phase_mapping/triple_points.py` - Triple point reference data
- `quickice/phase_mapping/ice_ih_density.py` - IAPWS R10-06(2009) Ice Ih density via `iapws._iapws._Ice()`
- `quickice/phase_mapping/water_density.py` - Water density calculations for interface generation via `iapws.IAPWS95`

**GenIce2 Structure Generation:**
- `quickice/structure_generation/generator.py` - Wraps GenIce2 API for ice crystal generation
  - `safe_import('lattice', ...)` for dynamic lattice loading
  - `safe_import('molecule', 'tip3p')` for water model
  - `safe_import('format', 'gromacs')` for GRO output
  - `GenIce(lattice, density=..., reshape=...)` for structure generation
  - `ice.generate_ice(formatter=..., water=..., depol='strict')` for actual generation
- `quickice/structure_generation/hydrate_generator.py` - Wraps GenIce2 for hydrate generation
  - Lazy import of GenIce2 modules (thread-safe with `_genice_lock`)
  - `safe_import('lattice', 'sI'/'sII'/'sH')` for hydrate lattices
  - `safe_import('molecule', 'tip4p')` for TIP4P water model
  - Uses `genice2.valueparser.parse_guest` for guest molecule configuration

## CLI Pipeline Integration

**Pipeline Orchestrator:**
- `quickice/cli/pipeline.py` - `CLIPipeline` class runs ordered steps (source → interface → custom → solute → ion → export) with fail-fast semantics
- `quickice/cli/parser.py` - `create_parser()` / `get_arguments()` for CLI argument definition with custom validators
- `quickice/entry.py` - `main()` routes between CLI and GUI based on `--cli`/`--gui` flags and implicit pipeline flag detection

**Validator Integration with Parser:**
- `quickice/cli/parser.py` imports all 7 validators from `quickice/validation/validators.py`:
  - `validate_temperature`, `validate_pressure`, `validate_nmolecules`, `validate_positive_float`, `validate_box_dimension` (original 5)
  - `validate_concentration_range` (CP-03) — used by `--custom-concentration`, `--solute-concentration`, `--ion-concentration`
  - `validate_occupancy_range` (CP-03) — used by `--cage-occupancy-small`, `--cage-occupancy-large`
- Each validator is assigned as `type=` to the corresponding `add_argument()` call, so argparse auto-applies validation during parsing

**Error Handling in Pipeline:**
- `quickice/cli/pipeline.py` uses structured exception catching (NOT bare `except Exception`):
  - `OSError` for directory creation failures (line 63)
  - `FileNotFoundError` for missing input GRO/ITP/CSV files (lines 448-450)
  - `ValueError` for invalid configurations and missing prerequisite structures (lines 452-454, 506-512, 642-645)
  - `InsertionError` for custom molecule insertion failures (lines 456-458)
  - `ImportError` for missing packages in each step (lazy imports)
  - Export step catches `(OSError, ValueError)` (line 764) — broader but still typed
- GRO file I/O protected: `parse_gro_string()` / `parse_gro_file()` use try/except with IOError handling
- Hydrate export wrapper in `_run_export_step()` has atom count assertion (line 720-723):
  ```python
  assert water_atom_count + guest_atom_count == len(hydrate.positions), ...
  ```
  Catches bugs where `water_count * 4` does not match actual water atoms in positions

## Test Infrastructure Integration

**e2e Export Helpers (`tests/e2e_export_helpers.py`, 528 lines):**
- `StagingResult = namedtuple("StagingResult", ["staged", "missing"])` — result from ITP staging (line 37)
- `parse_top_includes()`, `parse_top_molecules()`, `parse_gro_residue_names()` — GRO/TOP parsing for assertions
- `_stage_itp_files()` — Copies #include'd ITP files to workspace with atomtypes commented out; returns `StagingResult`
- `assert_itp_completeness()` — Asserts every #include'd ITP file (except ion.itp) exists in workspace (line 455-481)
  - Catches the "top references ITP but file is missing from export" class of bugs
  - This is the test gap that previously allowed the CH4 hydrate guest ITP copy bug to escape detection
- `run_gmx_grompp()` — Runs `gmx grompp` in workspace directory; returns `(exit_code, stderr_text)` (lines 484-528)
- Chain-building helpers: `_insert_custom_molecules()`, `_insert_solutes()`, `_insert_ions()`, `_insert_ions_from_solute()`, `_solute_to_ion_source()`, `_make_slab_interface()`, `_hydrate_sI_ch4_candidate()`, etc.
- Data paths: `DATA_DIR`, `ETOH_GRO`, `ETOH_ITP` — test molecule templates

**GROMACS Availability Skip (`tests/conftest.py`):**
- `gmx_skipif = pytest.mark.skipif(not _gmx_available(), reason="GROMACS (gmx) not found on PATH")` (line 24)
- Applied to all test classes that call `gmx grompp` via `@gmx_skipif` decorator
- `_gmx_available()` uses `shutil.which("gmx")` for detection (line 18)

**Parameterized grompp Validation:**
- `tests/test_e2e_gmx_param_validation.py` (311 lines) — `pytest.mark.parametrize` with `ChainParams` NamedTuple
- Covers 27 untested hydrate→interface chain combinations
- Derivation: 4 hydrate types × {custom:yes/no} × {solute:none/CH4/THF} × {ion:yes/no} = 48 total minus 13 already-tested minus 8 non-hydrate interface-only combos = 27
- Uses `gmx_skipif` marker for CI environments without GROMACS

---

*Integration audit: 2026-06-18*
