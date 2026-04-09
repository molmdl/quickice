# External Integrations

**Analysis Date:** 2026-04-10

## APIs & External Services

**Scientific Libraries (local computation, no network calls):**
- IAPWS (iapws 1.5.5) - Water/steam thermodynamic properties per IAPWS standards
  - SDK/Client: `iapws` pip package (`from iapws import IAPWS97`)
  - Auth: None (pure computation library)
  - Usage: Liquid-vapor saturation curve in phase diagram (`quickice/output/phase_diagram.py`)
  - Called as: `IAPWS97(T=T, x=0)` for saturated liquid properties

- GenIce2 (genice2 2.2.13.1) - Ice crystal structure generation
  - SDK/Client: `genice2` pip package (`from genice2.plugin import safe_import`, `from genice2.genice import GenIce`)
  - Auth: None (pure computation library)
  - Usage: Core ice structure generation (`quickice/structure_generation/generator.py`)
  - Plugin system: `safe_import("lattice", name)` loads lattice plugins, `safe_import("molecule", "tip3p")` loads water models, `safe_import("format", "gromacs")` loads formatters
  - Note: Uses global `np.random` state (not thread-safe)

- spglib (2.7.0) - Crystal symmetry analysis
  - SDK/Client: `spglib` pip package (`import spglib`)
  - Auth: None
  - Usage: Space group validation (`quickice/output/validator.py`)
  - Called as: `spglib.get_symmetry_dataset(cell_tuple, symprec=symprec)`

- NetworkX (3.6.1) - Graph algorithms
  - SDK/Client: `networkx` pip package (imported by GenIce internally)
  - Auth: None
  - Usage: Hydrogen bond network analysis within GenIce

- Shapely (2.1.2) - Geometric operations
  - SDK/Client: `shapely` pip package (`from shapely.geometry import Polygon as ShapelyPolygon`)
  - Auth: None
  - Usage: Polygon centroid calculation for phase diagram labels (`quickice/output/phase_diagram.py`)

**No network-based APIs or external services.** All computation is local.

## Data Storage

**Databases:**
- None. The application is stateless and does not use any database.

**File Storage:**
- Local filesystem only
- Bundled data files in `quickice/data/`:
  - `quickice/data/tip4p-ice.itp` - GROMACS TIP4P-ICE topology include file
  - `quickice/data/tip4p.gro` - TIP4P water template structure (864 atoms)
- Output files written to user-specified directory (default: `output/`):
  - PDB files (`*.pdb`) - Crystal structure coordinates
  - GROMACS files (`*.gro`, `*.top`, `*.itp`) - Molecular dynamics input
  - Phase diagram images (`phase_diagram.png`, `phase_diagram.svg`)
  - Phase diagram data (`phase_diagram_data.txt`)

**Caching:**
- In-memory caching only:
  - Water template cache in `quickice/structure_generation/water_filler.py` (`_water_template_cache`)
  - Boundary sampling cache in `quickice/output/phase_diagram.py` (`_SHARED_BOUNDARY_CACHE`)
- No persistent cache, no Redis, no memcached

## Authentication & Identity

**Auth Provider:**
- None. Desktop application with no user authentication or identity management.

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry, Bugsnag, or similar service.

**Logs:**
- Python stdlib `logging` module used sparingly:
  - `quickice/output/phase_diagram.py` - Debug/warning logs for melting curve failures
  - `quickice/output/orchestrator.py` - Warning logs for validation/output failures
- No centralized log collection; logs go to stderr/console only

## CI/CD & Deployment

**Hosting:**
- Desktop application - not hosted/deployed to servers
- Distributed as standalone executables bundled with PyInstaller

**CI Pipeline:**
- GitHub Actions (`.github/workflows/build-windows.yml`)
  - Trigger: Manual (`workflow_dispatch`) only
  - Job: Build Windows executable using `environment-build.yml` conda env
  - Steps: checkout → setup miniconda → pyinstaller build → package docs/licenses → upload artifact
  - No automated testing in CI
  - No Linux CI workflow (Linux build is manual via `scripts/build-linux.sh`)

**Dependabot:**
- `.github/dependabot.yml` - Weekly checks for conda and pip updates
  - `open-pull-requests-limit: 0` (auto-merge disabled, PRs created but limited)

## Environment Configuration

**Required env vars:**
- `PYTHONPATH` - Must include project root for `quickice` package import (set by `setup.sh`)
- `PATH` - Must include project root for CLI entry point (set by `setup.sh`)
- `CONDA_DEFAULT_ENV` - Checked by build scripts to verify `quickice` env is active

**Secrets location:**
- None. No secrets, API keys, or credentials required.

## Webhooks & Callbacks

**Incoming:**
- None. Desktop application with no server component.

**Outgoing:**
- None. No network requests made by the application.

## File Format Integrations

**Input Formats:**
- GRO (GROMACS coordinate format) - Parsed from GenIce output strings and from `quickice/data/tip4p.gro`
  - Parser: `IceStructureGenerator._parse_gro()` in `quickice/structure_generation/generator.py`
  - Parser: `load_water_template()` in `quickice/structure_generation/water_filler.py`

**Output Formats:**
- PDB (Protein Data Bank) - Crystal structure with CRYST1 records
  - Writer: `quickice/output/pdb_writer.py` (`write_pdb_with_cryst1()`)
- GRO (GROMACS coordinate format) - Molecular dynamics coordinates
  - Writer: `quickice/output/gromacs_writer.py` (`write_gro_file()`, `write_interface_gro_file()`)
- TOP (GROMACS topology) - Force field and molecule definitions
  - Writer: `quickice/output/gromacs_writer.py` (`write_top_file()`, `write_interface_top_file()`)
- ITP (GROMACS topology include) - Copied from `quickice/data/tip4p-ice.itp`
  - Copied via `shutil.copy()` in CLI main and GUI exporters
- PNG/SVG - Phase diagram and viewport screenshots
  - Writer: matplotlib `savefig()` in `quickice/output/phase_diagram.py`
  - Writer: VTK `vtkPNGWriter`/`vtkJPEGWriter` in `quickice/gui/export.py`
- TXT - Phase diagram data file
  - Writer: direct file write in `quickice/output/phase_diagram.py`

## Scientific Data References

**IAPWS Standards (embedded as equations, not API calls):**
- IAPWS R14-08(2011) - Melting curves for ice phases Ih, III, V, VI, VII
  - Implemented in: `quickice/phase_mapping/melting_curves.py`
- IAPWS R10-06(2009) - Equation of state for H2O Ice Ih (referenced in metadata)
- Triple point data from Journaux et al. (2019, 2020) and LSBU Water Phase Data
  - Implemented in: `quickice/phase_mapping/triple_points.py`

**Water Models (bundled data):**
- TIP3P - 3-point water model (O, H, H) used for GenIce internal generation
  - Loaded via: `safe_import("molecule", "tip3p")` in `quickice/structure_generation/generator.py`
- TIP4P-ICE - 4-point water model (OW, HW1, HW2, MW) used for GROMACS export
  - Template: `quickice/data/tip4p.gro` (864-atom equilibrated water box)
  - Topology: `quickice/data/tip4p-ice.itp` (GROMACS molecule definition)
  - Virtual site parameter α = 0.13458335 (defined in `quickice/output/gromacs_writer.py`)

---

*Integration audit: 2026-04-10*
