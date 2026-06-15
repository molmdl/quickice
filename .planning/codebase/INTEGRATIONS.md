# External Integrations

**Analysis Date:** 2026-06-15

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
  - `write_hydrate_gro_file()` for hydrate structures
  - `write_solute_gro_file()` for solute structures
  - `write_ion_gro_file()` for ion structures
  - `write_custom_molecule_gro_file()` for custom molecule systems
  - `write_multi_molecule_gro_file()` for mixed-molecule systems
- `.top` files - Topology files (corresponding writers for each structure type)
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

**CLI Pipeline Orchestrator:**
- `quickice/cli/pipeline.py` - `CLIPipeline` class runs ordered steps (source → interface → custom → solute → ion → export) with fail-fast semantics
- `quickice/cli/parser.py` - `create_parser()` / `get_arguments()` for CLI argument definition with custom validators
- `quickice/entry.py` - `main()` routes between CLI and GUI based on `--cli`/`--gui` flags and implicit pipeline flag detection

---

*Integration audit: 2026-06-15*
