# Technology Stack

**Analysis Date:** 2026-04-11

## Languages

**Primary:**
- Python 3.14.3 - All application code (CLI, GUI, generation, ranking, output, validation)

**Secondary:**
- Shell (Bash) - Build scripts (`scripts/build-linux.sh`, `scripts/assemble-dist.sh`, `setup.sh`)

## Runtime

**Environment:**
- Python 3.14.3 (CPython, conda-forge build `h490e9c7_101_cp314`)
- Conda environment name: `quickice` (runtime), `quickice-build` (build)

**Package Manager:**
- Conda (channels: conda-forge, defaults) - Primary package manager
- Pip 26.0.1 - Secondary for packages not available via conda
- Lockfile: None (environment.yml pins versions, no conda lock)

**Environment Setup:**
- `conda env create -f environment.yml` - one-time environment creation
- `source setup.sh` - activates conda env + sets PYTHONPATH/PATH for every new shell

## Frameworks

**Core:**
- PySide6 6.10.2 - Qt6 GUI framework (cross-platform desktop application)
  - MVVM pattern: View (`quickice/gui/view.py`, `main_window.py`) → ViewModel (`quickice/gui/viewmodel.py`) → Model (business logic)
  - QThread workers: `quickice/gui/workers.py` (GenerationWorker, InterfaceGenerationWorker)
  - Signal/slot architecture for async UI updates
- VTK 9.5.2 - 3D molecular visualization and rendering
  - Qt integration: `vtkmodules.qt.QVTKRenderWindowInteractor` embedded as QWidget
  - Rendering: `vtkMoleculeMapper` for ball-and-stick/VDW/stick modes
  - Export: `vtkWindowToImageFilter`, `vtkPNGWriter`, `vtkJPEGWriter` for viewport screenshots

**Scientific Computing:**
- NumPy 2.4.3 - Array operations, linear algebra, coordinate manipulation, cell matrices
- SciPy 1.17.1 - `scipy.spatial.cKDTree` for neighbor search with PBC; `scipy.interpolate.UnivariateSpline` for smooth phase diagram curves
- Matplotlib 3.10.8 - Phase diagram generation (PNG at 300dpi, SVG output)

**Domain-Specific:**
- GenIce2 2.2.13.1 + GenIce-core 1.4.3 - Ice crystal structure generation engine
  - Plugin loading: `genice2.plugin.safe_import(category, name)`
  - Core class: `genice2.genice.GenIce(lattice, density=, reshape=)`
  - Lattice plugins: ice_ih, ice_ic, ice_ii, ice_iii, ice_v, ice_vi, ice_vii, ice_viii, ice_ix, ice_xi, ice_xv
  - Molecule: `safe_import("molecule", "tip3p")` (3-atom generation)
  - Formatter: `safe_import("format", "gromacs")` (GRO output format)
  - Thread safety: NOT thread-safe (uses global `np.random` state internally)
- IAPWS 1.5.5 - IAPWS-97 water/steam thermodynamic property calculations
  - Used in `quickice/output/phase_diagram.py` for liquid-vapor saturation curve
  - Called as: `IAPWS97(T=T, x=0)` for saturated liquid properties
- spglib 2.7.0 - Crystal space group symmetry detection and validation
  - Used in `quickice/output/validator.py` for `validate_space_group()`
  - Called as: `spglib.get_symmetry_dataset(cell_tuple, symprec=symprec)`
- NetworkX 3.6.1 - Graph algorithms (used by GenIce for hydrogen bond networks)
- Shapely 2.1.2 - Geometric operations (polygon centroids for phase diagram labels)

**CLI:**
- argparse (stdlib) - Actual CLI argument parsing in `quickice/cli/parser.py`
- Click 8.3.1 - Listed in dependencies but NOT used for CLI (transitive dependency)

**Testing:**
- pytest >=9.0.0 - Test runner and assertion library

**Build/Dev:**
- PyInstaller 6.19.0 - Standalone executable bundling (spec: `quickice-gui.spec`)
- setuptools 80.10.2 - Python package tooling
- wheel 0.46.3 - Wheel packaging

## Key Dependencies

**Critical (application would fail without these):**
- `genice2` 2.2.13.1 - Core ice structure generation; no replacement available
  - All 12 ice phases generated via GenIce lattice plugins
  - GRO format output parsed by `IceStructureGenerator._parse_gro()`
- `genice-core` 1.4.3 - GenIce internals (`GenIce` class, `safe_import`)
- `numpy` 2.4.3 - Every module uses NumPy arrays for positions, cells, calculations
  - Positions: `(N_atoms, 3)` float arrays in nm
  - Cell matrices: `(3, 3)` row-vector format
- `pyside6` 6.10.2 - Entire `quickice/gui/` module depends on it
  - 16 files in `quickice/gui/`
- `vtk` 9.5.2 - 3D molecular rendering pipeline
  - `vtkMoleculeMapper`, `vtkRenderer`, `vtkInteractorStyleTrackballCamera`
  - `QVTKRenderWindowInteractor` for Qt embedding

**Infrastructure (important but replaceable):**
- `scipy` 1.17.1 - cKDTree in `quickice/ranking/scorer.py`, `quickice/structure_generation/overlap_resolver.py`, `quickice/output/validator.py`; UnivariateSpline in `quickice/output/phase_diagram.py`
- `matplotlib` 3.10.8 - Phase diagram generation only (`quickice/output/phase_diagram.py`)
- `spglib` 2.7.0 - Structure validation only (`quickice/output/validator.py`)
- `shapely` 2.1.2 - Phase diagram polygon centroids only (`quickice/output/phase_diagram.py`)
- `iapws` 1.5.5 - Liquid-vapor boundary curve in phase diagram only (`quickice/output/phase_diagram.py`)
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
  - Collects: iapws, genice2, genice_core, matplotlib, scipy, numpy, shapely, networkx, spglib
  - Bundles: `quickice/data` directory
  - Output: `dist/quickice-gui/quickice-gui` executable + `_internal/` libraries
- `scripts/build-linux.sh` - Linux build script (requires `quickice` conda env, 5-15 min)
- `scripts/assemble-dist.sh` - Distribution tarball assembly

**CI:**
- `.github/workflows/build-windows.yml` - Windows CI build (manual trigger via `workflow_dispatch`)
- `.github/dependabot.yml` - Weekly conda/pip dependency checks

**Package:**
- No `setup.py`, `pyproject.toml`, or `setup.cfg` - package imported via PYTHONPATH
- Version: `quickice/__init__.py` → `__version__ = "3.0.0"`

## Platform Requirements

**Development:**
- Linux (primary development platform)
- Windows (supported via CI build)
- Conda environment with Python 3.14.3
- Display server for GUI (X11/Wayland on Linux, native on Windows/macOS)
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

*Stack analysis: 2026-04-11*
