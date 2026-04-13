# Technology Stack

**Analysis Date:** 2026-04-13

## Languages

**Primary:**
- Python 3.14.3 - All application code (CLI, GUI, core physics, output generation, ranking, validation)

**Secondary:**
- Shell (Bash) - Build scripts (`scripts/build-linux.sh`, `scripts/assemble-dist.sh`, `setup.sh`)
- GRO format (GROMACS) - Molecular coordinate output (read/written)
- PDB format - Molecular coordinate output (written)
- ITP/TOP format (GROMACS topology) - Force field topology output (written)

## Runtime

**Environment:**
- CPython 3.14.3 (conda-forge build `h490e9c7_101_cp314`, `python_abi=3.14=2_cp314`)
- Conda environment name: `quickice` (runtime), `quickice-build` (build)

**Package Manager:**
- Conda (channels: conda-forge, defaults) - Primary package manager for Python runtime + C libraries
- Pip 26.0.1 - Secondary for Python-only packages not in conda
- Lockfile: `environment.yml` (pinned versions serve as de-facto lock; no conda-lock file)

**Environment Setup:**
- One-time: `conda env create -f environment.yml`
- Every new shell: `source setup.sh` (activates conda env, sets PYTHONPATH and PATH)

## Frameworks

**Core:**
- PySide6 6.10.2 - Qt6 GUI framework (cross-platform desktop application)
  - MVVM pattern: View (`quickice/gui/view.py`, `quickice/gui/main_window.py`) → ViewModel (`quickice/gui/viewmodel.py`) → Model (business logic in `quickice/` subpackages)
  - QThread workers: `quickice/gui/workers.py` (`GenerationWorker`, `InterfaceGenerationWorker`)
  - Signal/slot architecture for async UI updates and generation progress
- VTK 9.5.2 - 3D molecular visualization and rendering
  - Qt integration: `vtkmodules.qt.QVTKRenderWindowInteractor` embedded as QWidget
  - Rendering: `vtkMoleculeMapper` for ball-and-stick/VDW/stick display modes
  - Export: `vtkWindowToImageFilter`, `vtkPNGWriter`, `vtkJPEGWriter` for viewport screenshots
  - H-bond visualization: `vtkPolyData` + `vtkPolyDataMapper` for dashed-line actors
  - Unit cell wireframe: `vtkOutlineSource` for simulation box boundaries
- GenIce2 2.2.13.1 + GenIce-core 1.4.3 - Ice crystal structure generation engine
  - Plugin loading: `genice2.plugin.safe_import(category, name)`
  - Core class: `genice2.genice.GenIce(lattice, density=, reshape=)`
  - Generates 8 ice phases via lattice plugins (ice1h, ice1c, ice2, ice3, ice5, ice6, ice7, ice8)
  - Molecule: `safe_import("molecule", "tip3p")` → 3-atom O, H, H format
  - Formatter: `safe_import("format", "gromacs")` → GRO format output string
  - Thread safety: NOT thread-safe (uses global `np.random` state; save/restore around calls)

**Scientific Computing:**
- NumPy 2.4.3 - Array operations, linear algebra, coordinate manipulation, cell matrices
  - Positions stored as `(N_atoms, 3)` float64 arrays in nm
  - Cell matrices stored as `(3, 3)` row-vector format: `new_pos = pos @ cell`
- SciPy 1.17.1 - `scipy.spatial.cKDTree` for neighbor search with PBC; `scipy.interpolate.UnivariateSpline` for smooth phase diagram curves
- Matplotlib 3.10.8 - Phase diagram generation (PNG at 300dpi, SVG output)

**Domain-Specific:**
- IAPWS 1.5.5 - IAPWS-97 and IAPWS-95 thermodynamic property calculations
  - IAPWS-97: Liquid-vapor saturation curve in `quickice/output/phase_diagram.py` (called as `IAPWS97(T=T, x=0)`)
  - IAPWS-95: Supercooled water density in `quickice/phase_mapping/water_density.py` (called as `IAPWS95(T=T_K, P=P_MPa)`)
  - IAPWS Ice: Ice Ih density in `quickice/phase_mapping/ice_ih_density.py` (called as `_Ice(T_K, P_MPa)`)
- spglib 2.7.0 - Crystal space group symmetry detection and validation
  - Used in `quickice/output/validator.py` for `validate_space_group()`
  - Called as: `spglib.get_symmetry_dataset(cell_tuple, symprec=symprec)`
  - Requires nm→Å conversion (multiply by 10.0) before calling
- NetworkX 3.6.1 - Graph algorithms (used internally by GenIce for hydrogen bond networks)
- Shapely 2.1.2 - Geometric operations (polygon centroids for phase diagram label placement)

**CLI:**
- argparse (stdlib) - Actual CLI argument parsing in `quickice/cli/parser.py`
- Click 8.3.1 - Listed in dependencies but NOT used for CLI (transitive dependency of GenIce)

**Testing:**
- pytest >=9.0.0 - Test runner and assertion library

**Build/Dev:**
- PyInstaller 6.19.0 - Standalone executable bundling (spec: `quickice-gui.spec`)
- setuptools 80.10.2 - Python package tooling
- wheel 0.46.3 - Wheel packaging

## Key Dependencies

**Critical (application would fail without these):**
- `genice2` 2.2.13.1 - Core ice structure generation; no replacement available
  - All 8 supported ice phases generated via GenIce lattice plugins
  - GRO format output parsed by `IceStructureGenerator._parse_gro()` in `quickice/structure_generation/generator.py`
  - Unsupported phases (ice_ix, ice_xi, ice_xv, ice_x) are detected by phase mapping but cannot be generated
- `genice-core` 1.4.3 - GenIce internals (`GenIce` class, `safe_import` plugin loader)
- `numpy` 2.4.3 - Every module uses NumPy arrays for positions, cells, calculations
  - Positions: `(N_atoms, 3)` float arrays in nm
  - Cell matrices: `(3, 3)` row-vector format where `new_position = position @ cell`
  - VTK conversion requires transpose: `cell.T` for `vtkMatrix3x3` (column-vector convention)
- `pyside6` 6.10.2 - Entire `quickice/gui/` module (16 files) depends on it
- `vtk` 9.5.2 - 3D molecular rendering pipeline (`vtkMoleculeMapper`, `vtkRenderer`, `vtkInteractorStyleTrackballCamera`)
- `scipy` 1.17.1 - cKDTree in `quickice/ranking/scorer.py`, `quickice/structure_generation/overlap_resolver.py`, `quickice/output/validator.py`; UnivariateSpline in `quickice/output/phase_diagram.py`

**Infrastructure (important but replaceable):**
- `matplotlib` 3.10.8 - Phase diagram generation only (`quickice/output/phase_diagram.py`)
- `iapws` 1.5.5 - Thermodynamic density and melting curve calculations
  - IAPWS R10-06(2009) Ice Ih density: `quickice/phase_mapping/ice_ih_density.py`
  - IAPWS-95 supercooled water density: `quickice/phase_mapping/water_density.py`
  - IAPWS-97 liquid-vapor saturation: `quickice/output/phase_diagram.py`
- `spglib` 2.7.0 - Structure validation only (`quickice/output/validator.py`)
- `shapely` 2.1.2 - Phase diagram polygon centroids only (`quickice/output/phase_diagram.py`)
- `networkx` 3.6.1 - Used by GenIce internally for hydrogen bond network analysis

**Supporting (GenIce plugin dependencies):**
- `cycless` 0.7 - Cycle detection in hydrogen bond networks
- `graphstat` 0.3.3 - Graph statistics
- `pairlist` 0.6.4 - Pair distance calculations
- `methodtools` 0.4.7 - LRU cache for class methods
- `openpyscad` 0.5.0 - OpenSCAD format output
- `wirerope` 1.0.0 - Wire/rope data structures
- `yaplotlib` 0.1.3 - Yet another plot library
- `deprecated` 1.3.1 / `deprecation` 2.1.0 - Deprecation decorators
- `six` 1.17.0 - Python 2/3 compatibility
- `wrapt` 2.1.2 - Decorator utilities

## Configuration

**Environment:**
- Conda environment defined in `environment.yml` (runtime) and `environment-build.yml` (build)
- `setup.sh` activates conda env and sets `PYTHONPATH`/`PATH`
- No `.env` file; no environment variables required for core operation

**Build:**
- `quickice-gui.spec` - PyInstaller spec for GUI executable
  - Entry point: `quickice/gui/__main__.py`
  - Collects data/binaries/hidden imports from: iapws, genice2, genice_core, matplotlib, scipy, numpy, shapely, networkx, spglib
  - Bundles: `quickice/data` directory (tip4p-ice.itp, tip4p.gro)
  - Output: `dist/quickice-gui/quickice-gui` executable + `_internal/` libraries
- `scripts/build-linux.sh` - Linux build script (requires `quickice` conda env active; takes 5-15 min)
- `scripts/assemble-dist.sh` - Creates distribution tarball with docs, licenses, and executable

**CI:**
- `.github/workflows/build-windows.yml` - Windows CI build (manual trigger via `workflow_dispatch`)
  - Uses `conda-incubator/setup-miniconda@v3` with `environment-build.yml`
  - PyInstaller build → package docs/licenses → 7z archive → upload artifact
- `.github/dependabot.yml` - Weekly conda/pip dependency checks (open-pull-requests-limit: 0)

**Package:**
- No `setup.py`, `pyproject.toml`, or `setup.cfg` - package imported via PYTHONPATH
- Version: `quickice/__init__.py` → `__version__ = "3.0.0"`

## Platform Requirements

**Development:**
- Linux (primary development platform)
- Windows (supported via CI build)
- Conda environment with Python 3.14.3
- Display server for GUI (X11/Wayland on Linux, native on Windows)
- VTK rendering requires OpenGL support
- Minimum ~2GB RAM for conda environment

**Production:**
- PyInstaller bundles standalone executable for Linux and Windows
- Linux output: `dist/quickice-gui/quickice-gui` (executable + `_internal/` libs)
- Windows output: `.zip` archive (built via GitHub Actions)
- Distribution tarballs: `quickice-{version}-linux-x86_64.tar.gz`
- No server deployment; desktop application only
- Display server required for GUI (VTK rendering)
- CLI mode (`python quickice.py`) works without display server

---

*Stack analysis: 2026-04-13*
