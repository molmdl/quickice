# Technology Stack

**Analysis Date:** 2026-06-18

## Languages

**Primary:**
- Python 3.14.3 - All application logic, GUI, CLI, structure generation, export

**Secondary:**
- YAML - Conda environment definitions (`environment.yml`, `environment-build.yml`)
- GROMACS topology format (.itp, .top, .gro) - Molecular simulation file I/O
- Shell (bash) - Setup scripts (`setup.sh`), build scripts (`scripts/build-linux.sh`, `scripts/assemble-dist.sh`), workflow scripts (`scripts/hydrate-interface-custom-ion.sh`), CLI examples (`scripts/cli-examples.sh`)

## Runtime

**Environment:**
- CPython 3.14.3 (conda-forge build `h490e9c7_101_cp314`)
- Conda for environment management (Miniconda/Anaconda)
- Environment name: `quickice` (development), `quickice-build` (build)

**Package Manager:**
- Conda (conda-forge + defaults channels) for binary dependencies (PySide6, VTK, NumPy)
- pip (via conda's pip) for PyPI-only dependencies
- Lockfile: Not present (no `conda-lock` or `pip freeze` lockfile committed)

## Frameworks

**Core:**
- PySide6 6.10.2 - Qt6 GUI framework (cross-platform desktop application)
- VTK 9.5.2 - 3D molecular visualization and rendering
- argparse (stdlib) - CLI argument parsing and validation (`quickice/cli/parser.py`)

**Scientific Computing:**
- NumPy 2.4.3 - Array operations, matrix calculations, coordinate handling
- SciPy 1.17.1 - Spatial data structures (`cKDTree` for neighbor search), rotations (`scipy.spatial.transform.Rotation`)
- Matplotlib 3.10.8 - Phase diagram generation and embedded plotting
- Shapely 2.1.2 - Geometric operations for phase polygon detection in diagram widget
- NetworkX 3.6.1 - Graph algorithms (used by GenIce for ice topology analysis)
- spglib 2.7.0 - Space group validation for crystal structures

**Physics/Thermodynamics:**
- GenIce2 2.2.13.1 - Ice crystal structure generation (core physics engine)
- genice-core 1.4.3 - GenIce shared library/ABI
- iapws 1.5.5 - IAPWS steam tables and ice Ih thermodynamic properties (R10-06, R14-08)
- cycless 0.7 - Ring perception algorithms for ice network topology
- graphstat 0.3.3 - Graph statistics for ice structure analysis

**Testing:**
- pytest >=9.0.0 - Test runner and assertion framework
- Custom marker: `slow` (registered in `conftest.py`)

**Build/Dev:**
- PyInstaller 6.19.0 - Cross-platform executable packaging (`quickice-gui.spec`)
- setuptools 80.10.2 - Python packaging (via conda)

## Key Dependencies

**Critical (application would not function):**
- `genice2` 2.2.13.1 - Generates physically valid ice crystal structures; core physics engine
- `pyside6` 6.10.2 - GUI framework; entire UI is PySide6-based (lazy-imported in CLI path via `importlib.util.find_spec`)
- `vtk` 9.5.2 - 3D molecular visualization in all viewer widgets
- `numpy` 2.4.3 - Foundation for all coordinate/array operations
- `scipy` 1.17.1 - `cKDTree` used in ranking scorer, overlap detection, and all inserters; `Rotation` for solute/custom molecule placement
- `iapws` 1.5.5 - IAPWS R14-08 melting curves and R10-06 Ice Ih density; no alternative
- `matplotlib` 3.10.8 - Phase diagram rendering and embedded canvas widget
- `argparse` (stdlib) - CLI definition and validation in `quickice/cli/parser.py`

**Infrastructure:**
- `shapely` 2.1.2 - Phase polygon detection in `quickice/gui/phase_diagram_widget.py`
- `networkx` 3.6.1 - Graph topology analysis (GenIce dependency)
- `spglib` 2.7.0 - Space group validation in `quickice/output/validator.py`
- `click` 8.3.1 - Declared in environment but NOT used; argparse is the sole CLI framework
- `pairlist` 0.6.4 - Pair list computation (GenIce dependency)
- `openpyscad` 0.5.0 - OpenSCAD interface (declared dependency, used for 3D model export)

**File Format Support:**
- `yaplotlib` 0.1.3 - Yaplot visualization format output
- `wirerope` 1.0.0 - Wire/rope data structure utilities
- `methodtools` 0.4.7 - Method decorators (lru_cache for methods)
- `deprecated` 1.3.1 / `deprecation` 2.1.0 - Deprecation warning decorators

## Force Field Constants (Single Source of Truth)

**TIP4P-ICE LJ Parameters:**
- `TIP4P_ICE_OW_SIGMA = 3.16680e-1` nm — defined in `quickice/output/gromacs_writer.py` (lines 27-28)
- `TIP4P_ICE_OW_EPSILON = 8.82110e-1` kJ/mol — defined in `quickice/output/gromacs_writer.py` (lines 27-28)
- Reference: Abascal et al. 2005, DOI: 10.1063/1.1931662
- These module-level constants replace all inline LJ parameter values in the 6 TOP-writing functions
- `write_top_file()`, `write_interface_top_file()`, `write_multi_molecule_top_file()`, `write_ion_top_file()`, `write_custom_molecule_top_file()`, `write_solute_top_file()` all reference `TIP4P_ICE_OW_SIGMA` and `TIP4P_ICE_OW_EPSILON` via f-strings with `:.5e` formatting

**Combination Rule:**
- `comb-rule=2` (Lorentz-Berthelot) in all 6 TOP-writing functions
- `sigma_ij = (sigma_i + sigma_j) / 2`, `epsilon_ij = sqrt(eps_i * eps_j)`
- Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields
- `[ defaults ]` line: `1  2  yes  0.5  0.8333`
- Present in: `write_top_file()` (line 553), `write_interface_top_file()` (line 1006), `write_multi_molecule_top_file()` (line 1284), `write_ion_top_file()` (line 1789), `write_custom_molecule_top_file()` (line 2194), `write_solute_top_file()` (line 2706)

**Physical Constants:**
- `AVOGADRO = 6.02214076e23` mol⁻¹ (CODATA 2017) — single definition in `quickice/structure_generation/ion_inserter.py` (line 29)
- Previously duplicated in `pipeline.py`; now imported from `ion_inserter.py` in: `quickice/cli/pipeline.py`, `quickice/structure_generation/solute_inserter.py`, `quickice/structure_generation/custom_molecule_inserter.py`, `quickice/ranking/scorer.py`
- `WATER_VOLUME_NM3 = 0.0299` — defined in `quickice/structure_generation/types.py` (line 25)
- Previously hardcoded as `0.0299` in multiple locations; now the single source of truth
- `WATER_ATOMS_PER_MOLECULE = 4` — defined in `quickice/structure_generation/types.py` (line 22)
- `TIP4P_ICE_ALPHA = 0.13458335` — defined in `quickice/output/gromacs_writer.py` (line 23, also line 143)

## Input Validation

**CLI Validators (in `quickice/validation/validators.py`, 206 lines):**
- `validate_temperature(value)` → float in [0, 500] K (CP-01)
- `validate_pressure(value)` → float in [0, 10000] MPa (CP-02)
- `validate_nmolecules(value)` → int in [4, 100000] (CP-02)
- `validate_positive_float(value)` → float > 0 (CP-02)
- `validate_box_dimension(value)` → float >= 1.0 nm (CP-02)
- `validate_concentration_range(value)` → float in [0.0, 5.0] mol/L (CP-03) — covers seawater ~0.6 to saturated ~5 mol/L
- `validate_occupancy_range(value)` → float in [0.0, 100.0] % (CP-03) — cage occupancy percentage

**File Extension Validation (SEC-02):**
- `--custom-gro` file must have `.gro` extension (case-insensitive) — enforced in `quickice/cli/pipeline.py:370-375`
- `--custom-itp` file must have `.itp` extension (case-insensitive) — enforced in `quickice/cli/pipeline.py:376-381`

**Cross-Flag Validation (in `quickice/cli/parser.py:validate_pipeline_args()`):**
- `--hydrate + --nmolecules` mutually exclusive
- `--custom-gro` requires `--custom-itp` and vice versa
- `--custom-gro` requires `--interface`
- `--custom-placement custom` requires `--custom-positions-file`
- `--custom-placement random` requires `--custom-count` or `--custom-concentration` (not both)
- `--solute-type` requires `--solute-concentration` and `--interface`
- `--ion-concentration` requires `--interface`

## Test Infrastructure

**Key Regression Test Files (added in Phases 34.9 / 37.1):**
- `tests/test_tip4p_ice_lj_values.py` (288 lines) — Prevents P16 regression: sigma/epsilon magnitude errors in TOP [atomtypes]
- `tests/test_pbc_wrapping.py` (224 lines) — Verifies all atom coordinates in exported GRO files fall within [0, box_size)
- `tests/test_scancode_bugs_solute.py` (174 lines) — Prevents V-03 regression: solute inserter cKDTree rebuild optimization
- `tests/test_e2e_gmx_param_validation.py` (311 lines) — Parameterized grompp validation for 27 untested chain combinations
- `tests/test_e2e_gmx_validation.py` (1231 lines) — 18 class-based grompp tests covering deepest chains F1-F7 + sII + hydrate/custom/solute standalone

## Configuration

**Environment:**
- Conda environment from `environment.yml` (development) or `environment-build.yml` (build)
- `setup.sh` activates conda env and sets `PYTHONPATH` to project root
- No `.env` files required; application has no environment variable dependencies
- No configuration files needed at runtime; all parameters via CLI args or GUI inputs
- Display environment variables checked by `quickice/entry.py` on Linux: `DISPLAY`, `WAYLAND_DISPLAY`, `QT_QPA_PLATFORM`

**Build:**
- `quickice-gui.spec` - PyInstaller spec for executable build
  - Entry point: `quickice/__main__.py` (unified, supports both CLI and GUI)
  - `console=True` + `hide_console='hide-late'` — console allocated then hidden after GUI launches
  - Data collection: `quickice/data` + all packages via `collect_all()`
  - Excludes: tests, docs, `__pycache__`, `.pytest_cache`, egg-info
- `environment-build.yml` - Conda environment for build (same deps + PyInstaller 6.19.0)
- `scripts/build-linux.sh` - Linux build script (requires `quickice` conda env)
- `scripts/assemble-dist.sh` - Packages dist into versioned `.tar.gz`
- `.github/workflows/build-windows.yml` - Windows build via GitHub Actions

## Entry Points

**Unified entry (primary):**
- `python -m quickice` → `quickice/__main__.py` → `quickice/entry.py:main()`
- Routes to CLI or GUI based on `--cli`/`--gui` flags and argument detection
- GUI: `quickice/gui/main_window.py:run_app()`
- CLI: `quickice/main.py:main()` → `quickice/cli/parser.py:get_arguments()` → `quickice/cli/pipeline.py:CLIPipeline.execute()`

**Legacy entry (still works):**
- `python quickice.py` at project root — delegates to `quickice.entry.main()`

**PyInstaller entry:**
- `quickice-gui` binary → `quickice/__main__.py` (same unified entry)

## Platform Requirements

**Development:**
- Linux (primary development platform per current environment)
- Conda with conda-forge channel
- Python 3.14.3 (bleeding edge; requires conda-forge build)
- X11 display or Wayland for GUI testing (PySide6 + VTK rendering)
- `PYTHONPATH` must include project root (set via `setup.sh`)
- GROMACS `gmx` binary on PATH for e2e grompp validation tests (skipped via `gmx_skipif` if absent)

**Production:**
- Cross-platform desktop: Windows (primary target, has PyInstaller build + GitHub Actions)
- Linux (runs from source or PyInstaller build)
- macOS (supported by PySide6/VTK but no dedicated build pipeline)
- Distribution: PyInstaller-built executable with `console=True` + `hide_console='hide-late'`
- No server/cloud deployment; purely desktop application

---

*Stack analysis: 2026-06-18*
