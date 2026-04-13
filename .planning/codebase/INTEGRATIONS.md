# External Integrations

**Analysis Date:** 2026-04-13

## APIs & External Services

**Scientific Libraries (local computation, no network calls):**

- IAPWS (iapws 1.5.5) - Water/steam/ice thermodynamic properties per IAPWS standards
  - SDK/Client: `iapws` pip package
  - Auth: None (pure computation library)
  - Three formulations used:
    1. IAPWS R10-06(2009) Ice Ih density: `quickice/phase_mapping/ice_ih_density.py`
       - Called as: `_Ice(T_K, P_MPa)` → returns `{"rho": density_kgm3}`
       - Caching: `@lru_cache(maxsize=256)` on `ice_ih_density_kgm3()`
       - Fallback: returns 0.9167 g/cm³ when IAPWS range exceeded (P > 208.566 MPa or T > 273.16 K)
    2. IAPWS-95 supercooled water density: `quickice/phase_mapping/water_density.py`
       - Called as: `IAPWS95(T=T_K, P=P_MPa)` → returns `.rho` attribute (kg/m³)
       - Caching: `@lru_cache(maxsize=256)` on `water_density_kgm3()`
       - Supports T < 273.15 K (supercooled) via extrapolation
       - Fallback: returns 0.9998 g/cm³ when calculation fails
    3. IAPWS-97 liquid-vapor saturation: `quickice/output/phase_diagram.py`
       - Called as: `IAPWS97(T=T, x=0)` for saturated liquid → returns `.P` attribute (MPa)
       - Used for liquid-vapor boundary curve in phase diagram only
       - No fallback; failures logged as `logging.warning()`

- GenIce2 (genice2 2.2.13.1) - Ice crystal structure generation engine
  - SDK/Client: `genice2` pip package
  - Auth: None (pure computation library)
  - Usage: Core ice structure generation (`quickice/structure_generation/generator.py`)
  - Plugin system entry points:
    - `safe_import("lattice", name)` - loads lattice plugins: ice1h, ice1c, ice2, ice3, ice5, ice6, ice7, ice8
    - `safe_import("molecule", "tip3p")` - loads 3-point water model (O, H, H)
    - `safe_import("format", "gromacs")` - loads GRO output formatter
  - Core API: `GenIce(lattice, density=, reshape=supercell_matrix).generate_ice(formatter=, water=, depol="strict")`
  - Returns: GRO format string → parsed by `_parse_gro()` into positions, atom_names, cell
  - Phase mapping: `quickice/structure_generation/mapper.py` maps QuickIce phase IDs to GenIce lattice names
    - e.g., "ice_ih" → "ice1h", "ice_vii" → "ice7"
  - Supercell calculation: `calculate_supercell(target_molecules, molecules_per_unit_cell)` in mapper.py
  - Thread safety: NOT thread-safe (uses global `np.random` state; save/restore around calls)
  - Random state management: `np.random.seed(seed)` before generation, `np.random.set_state(original_state)` after
  - Supported phases for generation: ice_ih, ice_ic, ice_ii, ice_iii, ice_v, ice_vi, ice_vii, ice_viii (8 of 12 detected phases)

- spglib (2.7.0) - Crystal symmetry analysis
  - SDK/Client: `spglib` pip package (`import spglib`)
  - Auth: None
  - Usage: Space group validation in `quickice/output/validator.py`
  - Called as: `spglib.get_symmetry_dataset(cell_tuple, symprec=symprec)`
  - Requires nm→Å conversion (multiply by 10.0) before calling (spglib expects Å)

- NetworkX (3.6.1) - Graph algorithms
  - SDK/Client: `networkx` pip package
  - Auth: None
  - Usage: Internal GenIce dependency for hydrogen bond network analysis
  - Not directly called by QuickIce code

- Shapely (2.1.2) - Geometric operations
  - SDK/Client: `shapely` pip package (`from shapely.geometry import Polygon as ShapelyPolygon`)
  - Auth: None
  - Usage: Polygon centroid calculation for phase diagram label placement
  - Called in `quickice/output/phase_diagram.py` lines 864, 917
  - Called as: `ShapelyPolygon(vertices).centroid` → `.x`, `.y` for label positioning

- SciPy (1.17.1) - Scientific computing
  - `scipy.spatial.cKDTree` - O(n log n) neighbor search with PBC for O-O distance calculation
    - Used in: `quickice/ranking/scorer.py` (energy_score), `quickice/structure_generation/overlap_resolver.py` (overlap detection), `quickice/output/validator.py` (validation)
    - 3x3x3 supercell approach for periodic boundary conditions
  - `scipy.interpolate.UnivariateSpline` - Smooth phase diagram melting curves
    - Used in: `quickice/output/phase_diagram.py` `_sample_melting_curve()`
    - k=3 cubic spline with s=0 (interpolating, not smoothing)

**No network-based APIs or external services.** All computation is local.

## Data Storage

**Databases:**
- None. The application is stateless and does not use any database.

**File Storage:**
- Local filesystem only
- Bundled data files in `quickice/data/`:
  - `quickice/data/tip4p-ice.itp` - GROMACS TIP4P-ICE topology include file (force field parameters for Amber-compatible water model)
  - `quickice/data/tip4p.gro` - TIP4P water template structure (864-atom equilibrated water box, 216 molecules, 1.86824 nm³ box)
- Legacy data files in `quickice/phase_mapping/data/`:
  - `quickice/phase_mapping/data/ice_phases.json` - Phase boundary data (legacy; now computed from IAPWS equations)
  - `quickice/phase_mapping/data/ice_boundaries.py` - Legacy boundary data (now using `melting_curves.py` + `solid_boundaries.py`)
- Output files written to user-specified directory (default: `output/`):
  - PDB files (`*.pdb`) - Crystal structure coordinates with CRYST1 records
  - GROMACS files (`*.gro`, `*.top`, `*.itp`) - Molecular dynamics input files
  - Phase diagram images (`phase_diagram.png` at 300dpi, `phase_diagram.svg`)
  - Phase diagram data (`phase_diagram_data.txt`) - Text file with triple points and curve data
  - Viewport screenshots (PNG/JPEG) via GUI export

**Caching:**
- In-memory caching only (no persistent cache):
  - Water template: `quickice/structure_generation/water_filler.py` (`_water_template_cache` module-level global)
  - Ice Ih density: `quickice/phase_mapping/ice_ih_density.py` (`@lru_cache(maxsize=256)` on `ice_ih_density_kgm3()`)
  - Water density: `quickice/phase_mapping/water_density.py` (`@lru_cache(maxsize=256)` on `water_density_kgm3()`)
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
  - `quickice/output/phase_diagram.py` - `logging.debug()` for spline failures, `logging.warning()` for IAPWS97 calculation failures
  - `quickice/output/orchestrator.py` - `logging.warning()` for validation/output failures
- GUI log panel: `quickice/gui/view.py` `InfoPanel` widget displays generation progress, rankings, and phase info in-app
- CLI: progress printed to stdout via `print()` statements in `quickice/main.py`
- No centralized log collection; logs go to stderr/console only

## CI/CD & Deployment

**Hosting:**
- Desktop application - not hosted/deployed to servers
- Distributed as standalone executables bundled with PyInstaller

**CI Pipeline:**
- GitHub Actions (`.github/workflows/build-windows.yml`)
  - Trigger: Manual (`workflow_dispatch`) only
  - Job: Build Windows executable using `environment-build.yml` conda env
  - Steps: checkout → setup miniconda (`conda-incubator/setup-miniconda@v3`) → pyinstaller build → package docs/licenses → 7z archive → upload artifact (`actions/upload-artifact@v7`)
  - No automated testing in CI
  - No Linux CI workflow (Linux build is manual via `scripts/build-linux.sh`)

**Dependabot:**
- `.github/dependabot.yml` - Weekly checks for conda and pip updates
- `open-pull-requests-limit: 0` (PRs created but limited to 0 open at a time)

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
  - Water template file: `load_water_template()` in `quickice/structure_generation/water_filler.py` (lines 243-299)
  - GRO format: title line → atom count → atom records (resnr 5c, resname 5c, atomname 5c, atomnum 5c, x 8.3f, y 8.3f, z 8.3f) → box vectors
  - Supports orthogonal boxes (3-element box vector) and triclinic boxes (9-element box vector: v1x v2y v3z v1y v1z v2x v2z v3x v3y)

**Output Formats:**
- PDB (Protein Data Bank) - Crystal structure with CRYST1 records
  - Writer: `quickice/output/pdb_writer.py` → `write_pdb_with_cryst1()`, `write_interface_pdb_file()`
  - Unit conversion: nm → Å (multiply positions by 10.0, cell by 10.0)
  - Uses HETATM records for water molecules, residue name HOH, chain A
  - CRYST1 record: a, b, c (Å), alpha, beta, gamma (degrees)
- GRO (GROMACS coordinate format) - Molecular dynamics coordinates
  - Writer: `quickice/output/gromacs_writer.py` → `write_gro_file()`, `write_interface_gro_file()`
  - TIP4P-ICE conversion: adds MW virtual site from O, H1, H2 positions
  - Virtual site formula: `MW = O + α*(H1-O) + α*(H2-O)` where α = 0.13458335 (`TIP4P_ICE_ALPHA`)
  - 3-atom ice molecules → 4-atom TIP4P-ICE molecules at export time
  - Atom/residue number wrapping at 100000 (GROMACS convention for large systems)
  - Triclinic box format: 9-element box vector line
- TOP (GROMACS topology) - Force field and molecule definitions
  - Writer: `quickice/output/gromacs_writer.py` → `write_top_file()`, `write_interface_top_file()`
  - Atom types: OW_ice, HW_ice, MW (TIP4P-ICE parameters)
  - Defaults: Amber-compatible (nbfunc=1, comb-rule=2, fudgeLJ=0.5, fudgeQQ=0.8333)
  - Includes: `[atomtypes]`, `[moleculetype]`, `[atoms]`, `[settles]`, `[virtual_sites3]`, `[exclusions]`, `[system]`, `[molecules]`
- ITP (GROMACS topology include) - Copied from bundled `quickice/data/tip4p-ice.itp`
  - Copied via `shutil.copy()` in CLI (`quickice/main.py`) and GUI exporters (`quickice/gui/export.py`)
- PNG/SVG - Phase diagram and viewport screenshots
  - Phase diagram: matplotlib `savefig()` in `quickice/output/phase_diagram.py` (300dpi PNG, SVG)
  - Viewport: VTK `vtkWindowToImageFilter` → `vtkPNGWriter`/`vtkJPEGWriter` in `quickice/gui/export.py`
- TXT - Phase diagram data file
  - Writer: direct file write in `quickice/output/phase_diagram.py`
  - Contains: triple points, melting curve samples, user conditions

## Scientific Data References

**IAPWS Standards (embedded as equations, not API calls):**
- IAPWS R14-08(2011) - Melting curves for ice phases Ih, III, V, VI, VII
  - Implemented in: `quickice/phase_mapping/melting_curves.py`
  - Ice Ih: Simon-Glatzel equation with Tt=273.16K, Pt=0.000611657 MPa
  - Ice III: Tref=251.165K, Pref=208.566 MPa
  - Ice V: Tref=256.164K, Pref=350.100 MPa
  - Ice VI: Tref=273.31K, Pref=632.400 MPa
  - Ice VII: Tref=355K, Pref=2216.000 MPa (exponential form)
- IAPWS R10-06(2009) - Equation of state for H2O Ice Ih
  - Implemented via: `iapws._iapws._Ice()` wrapped in `quickice/phase_mapping/ice_ih_density.py`
  - Valid range: T ≤ 273.16K, P ≤ 208.566 MPa
  - Temperature-dependent density (unique among ice phases; others use fixed reference values)
- IAPWS-95 - Water thermodynamic properties (supports supercooled water)
  - Implemented via: `iapws.IAPWS95()` wrapped in `quickice/phase_mapping/water_density.py`
  - Essential for ice-water interface generation at sub-freezing temperatures
- Triple point data from Journaux et al. (2019, 2020) and LSBU Water Phase Data
  - Implemented in: `quickice/phase_mapping/triple_points.py`
  - Key triple points: Ih-II-III (238.45K, 213.5 MPa), Ih-III-Liquid (251.165K, 208.566 MPa), etc.
  - 15+ triple points defined covering all phase boundaries

**Water Models (bundled data):**
- TIP3P - 3-point water model (O, H, H) used for GenIce internal generation
  - Loaded via: `safe_import("molecule", "tip3p")` in `quickice/structure_generation/generator.py` line 111
  - Internal only; never written to output files directly
  - At export time, 3-atom TIP3P molecules are converted to 4-atom TIP4P-ICE format
- TIP4P-ICE - 4-point water model (OW, HW1, HW2, MW) used for GROMACS export
  - Reference: Abascal et al. 2005, DOI: 10.1063/1.1931662
  - Template: `quickice/data/tip4p.gro` (864-atom equilibrated water box, 216 molecules)
  - Topology: `quickice/data/tip4p-ice.itp` (GROMACS molecule definition)
  - Virtual site parameter: α = 0.13458335 (defined in `quickice/output/gromacs_writer.py` line 15)
  - MW computation: `MW = O + α*(H1-O) + α*(H2-O)` (`compute_mw_position()` in gromacs_writer.py)
  - Charges: OW=0.0, HW1=0.5897, HW2=0.5897, MW=-1.1794
  - Settles (rigid water geometry): doh=0.09572 nm, dhh=0.15139 nm
  - Template density: ~0.991 g/cm³ (216 molecules in 1.86824³ nm³ box)

## Physical Constants Used

- Avogadro's number: 6.022e23 molecules/mol (`quickice/ranking/scorer.py` line 168)
- Water molecular mass: 18.01528 g/mol (`quickice/ranking/scorer.py` line 169)
- Unit conversion: 1 nm³ = 1e-21 cm³ (`quickice/ranking/scorer.py`)
- Unit conversion: 1 nm = 10 Å (used throughout VTK, PDB, and spglib code)
- Ideal O-O distance in ice: 0.276 nm (`quickice/ranking/types.py` ScoringConfig default)
- O-O cutoff for ranking: 0.35 nm (`quickice/ranking/types.py` ScoringConfig default)
- Water molecule diameter: ~0.28 nm (used for validation in `quickice/structure_generation/interface_builder.py`)
- VII-VIII ordering temperature: 278K (fixed boundary in `quickice/phase_mapping/solid_boundaries.py`)

---

*Integration audit: 2026-04-13*
