# External Integrations

**Analysis Date:** 2026-04-11

## APIs & External Services

**Scientific Libraries (local computation, no network calls):**
- IAPWS (iapws 1.5.5) - Water/steam thermodynamic properties per IAPWS standards
  - SDK/Client: `iapws` pip package (`from iapws import IAPWS97`)
  - Auth: None (pure computation library)
  - Usage: Liquid-vapor saturation curve in phase diagram (`quickice/output/phase_diagram.py` line 947-957)
  - Called as: `IAPWS97(T=T, x=0)` for saturated liquid properties at temperature T
  - Output: `.P` attribute gives pressure in MPa

- GenIce2 (genice2 2.2.13.1) - Ice crystal structure generation
  - SDK/Client: `genice2` pip package
  - Auth: None (pure computation library)
  - Usage: Core ice structure generation (`quickice/structure_generation/generator.py` lines 93-119)
  - Plugin system entry points:
    - `safe_import("lattice", name)` - loads lattice plugins (ice_ih, ice_ii, ice_iii, ice_v, ice_vi, ice_vii, ice_viii, ice_ic, ice_ix, ice_xi, ice_xv)
    - `safe_import("molecule", "tip3p")` - loads 3-point water model (O, H, H)
    - `safe_import("format", "gromacs")` - loads GRO output formatter
  - Core API: `GenIce(lattice, density=, reshape=).generate_ice(formatter=, water=, depol="strict")`
  - Returns: GRO format string parsed by `_parse_gro()`
  - Thread safety: NOT thread-safe (uses global `np.random` state; save/restore around calls)

- spglib (2.7.0) - Crystal symmetry analysis
  - SDK/Client: `spglib` pip package (`import spglib`)
  - Auth: None
  - Usage: Space group validation (`quickice/output/validator.py` lines 17-40)
  - Called as: `spglib.get_symmetry_dataset(cell_tuple, symprec=symprec)`
  - Note: Requires nm→Å conversion (multiply by 10.0) before calling spglib

- NetworkX (3.6.1) - Graph algorithms
  - SDK/Client: `networkx` pip package (imported by GenIce internally)
  - Auth: None
  - Usage: Hydrogen bond network analysis within GenIce

- Shapely (2.1.2) - Geometric operations
  - SDK/Client: `shapely` pip package (`from shapely.geometry import Polygon as ShapelyPolygon`)
  - Auth: None
  - Usage: Polygon centroid calculation for phase diagram label placement (`quickice/output/phase_diagram.py` lines 864, 917)
  - Called as: `ShapelyPolygon(vertices).centroid` → `.x`, `.y` for label positioning

**No network-based APIs or external services.** All computation is local.

## Data Storage

**Databases:**
- None. The application is stateless and does not use any database.

**File Storage:**
- Local filesystem only
- Bundled data files in `quickice/data/`:
  - `quickice/data/tip4p-ice.itp` - GROMACS TIP4P-ICE topology include file (force field parameters)
  - `quickice/data/tip4p.gro` - TIP4P water template structure (864-atom equilibrated water box, ~1.868 nm³)
- Output files written to user-specified directory (default: `output/`):
  - PDB files (`*.pdb`) - Crystal structure coordinates with CRYST1 records
  - GROMACS files (`*.gro`, `*.top`, `*.itp`) - Molecular dynamics input files
  - Phase diagram images (`phase_diagram.png` at 300dpi, `phase_diagram.svg`)
  - Phase diagram data (`phase_diagram_data.txt`) - Text file with triple points and curve data

**Caching:**
- In-memory caching only (no persistent cache):
  - Water template: `quickice/structure_generation/water_filler.py` (`_water_template_cache` module-level global)
  - Boundary vertices: `quickice/output/phase_diagram.py` (`_SHARED_BOUNDARY_CACHE` dict keyed by boundary name + range + n_points)
- No Redis, no memcached, no file-based cache

## Authentication & Identity

**Auth Provider:**
- None. Desktop application with no user authentication or identity management.

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry, Bugsnag, or similar service.

**Logs:**
- Python stdlib `logging` module used sparingly:
  - `quickice/output/phase_diagram.py` - `logging.debug()` for spline failures, `logging.warning()` for IAPWS97 failures
  - `quickice/output/orchestrator.py` - `logging.warning()` for validation/output failures
- GUI log panel: `quickice/gui/view.py` InfoPanel displays generation progress and results in-app
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
- GRO (GROMACS coordinate format) - Parsed from two sources:
  - GenIce output strings: `IceStructureGenerator._parse_gro()` in `quickice/structure_generation/generator.py` (lines 149-208)
  - Water template file: `load_water_template()` in `quickice/structure_generation/water_filler.py`
  - GRO format: title line → atom count → atom records (resnr, resname, atomname, atomnum, x, y, z) → box vectors
  - Supports orthogonal and triclinic boxes (9-element box vector format)

**Output Formats:**
- PDB (Protein Data Bank) - Crystal structure with CRYST1 records
  - Writer: `quickice/output/pdb_writer.py` → `write_pdb_with_cryst1()`
  - Unit conversion: nm → Å (multiply positions by 10.0, cell by 10.0)
  - Uses HETATM records for water molecules, residue name HOH, chain A
- GRO (GROMACS coordinate format) - Molecular dynamics coordinates
  - Writer: `quickice/output/gromacs_writer.py` → `write_gro_file()`, `write_interface_gro_file()`
  - TIP4P-ICE conversion: adds MW virtual site from O, H1, H2 positions (α = 0.13458335)
  - 3-atom ice molecules → 4-atom TIP4P-ICE molecules at export time
- TOP (GROMACS topology) - Force field and molecule definitions
  - Writer: `quickice/output/gromacs_writer.py` → `write_top_file()`, `write_interface_top_file()`
  - Atom types: OW_ice, HW_ice, MW (TIP4P-ICE parameters)
  - Defaults: Amber-compatible (nbfunc=1, comb-rule=2, fudgeLJ=0.5, fudgeQQ=0.8333)
- ITP (GROMACS topology include) - Copied from bundled `quickice/data/tip4p-ice.itp`
  - Copied via `shutil.copy()` in CLI main (`quickice/main.py` line 114) and GUI exporters (`quickice/gui/export.py`)
- PNG/SVG - Phase diagram and viewport screenshots
  - Phase diagram: matplotlib `savefig()` in `quickice/output/phase_diagram.py` (300dpi PNG, SVG)
  - Viewport: VTK `vtkWindowToImageFilter` → `vtkPNGWriter`/`vtkJPEGWriter` in `quickice/gui/export.py` (2x scale, quality 95 for JPEG)
- TXT - Phase diagram data file
  - Writer: direct file write in `quickice/output/phase_diagram.py`

## Scientific Data References

**IAPWS Standards (embedded as equations, not API calls):**
- IAPWS R14-08(2011) - Melting curves for ice phases Ih, III, V, VI, VII
  - Implemented in: `quickice/phase_mapping/melting_curves.py`
  - Ice Ih: Simon-Glatzel equation with Tt=273.16K, Pt=0.000611657 MPa
  - Ice III-VII:各自的 Simon-Glatzel 方程 with reference temperatures and pressures
- IAPWS R10-06(2009) - Equation of state for H2O Ice Ih (referenced in metadata in `quickice/phase_mapping/lookup.py`)
- Triple point data from Journaux et al. (2019, 2020) and LSBU Water Phase Data
  - Implemented in: `quickice/phase_mapping/triple_points.py`
  - Key triple points: Ih-II-III (238.45K, 213.5 MPa), Ih-III-Liquid (251.165K, 208.566 MPa), etc.

**Water Models (bundled data):**
- TIP3P - 3-point water model (O, H, H) used for GenIce internal generation
  - Loaded via: `safe_import("molecule", "tip3p")` in `quickice/structure_generation/generator.py` line 111
  - Internal only; never written to output files directly
- TIP4P-ICE - 4-point water model (OW, HW1, HW2, MW) used for GROMACS export
  - Reference: Abascal et al. 2005, DOI: 10.1063/1.1931662
  - Template: `quickice/data/tip4p.gro` (864-atom equilibrated water box, 216 molecules)
  - Topology: `quickice/data/tip4p-ice.itp` (GROMACS molecule definition with settles, virtual_sites3, exclusions)
  - Virtual site parameter: α = 0.13458335 (defined in `quickice/output/gromacs_writer.py` line 15)
  - MW computation: `MW = O + α*(H1-O) + α*(H2-O)` (line 192-209)
  - Charges: OW=0.0, HW1=0.5897, HW2=0.5897, MW=-1.1794
  - Settles: doh=0.09572 nm, dhh=0.15139 nm

## Physical Constants Used

- Avogadro's number: 6.022e23 molecules/mol (in `quickice/ranking/scorer.py` line 168)
- Water molecular mass: 18.01528 g/mol (in `quickice/ranking/scorer.py` line 169)
- Unit conversion: 1 nm³ = 1e-21 cm³ (in `quickice/ranking/scorer.py`)
- Unit conversion: 1 nm = 10 Å (Å→nm factor = 0.1, used throughout VTK and PDB code)
- Ideal O-O distance in ice: 0.276 nm (in `quickice/ranking/types.py` ScoringConfig default)

---

*Integration audit: 2026-04-11*
