# Technology Stack

**Analysis Date:** 2026-04-10

## Languages

**Primary:**
- Python 3.14.3 - All application code (CLI, GUI, generation, output)

**Secondary:**
- Shell (Bash) - Build scripts (`scripts/build-linux.sh`, `scripts/assemble-dist.sh`, `setup.sh`)

## Runtime

**Environment:**
- Python 3.14.3 (CPython, conda-forge build `h490e9c7_101_cp314`)
- Conda environment name: `quickice` (runtime), `quickice-build` (build)

**Package Manager:**
- Conda (channels: conda-forge, defaults) - Primary package manager
- Pip (26.0.1) - Secondary for packages not available via conda
- Lockfile: None (environment.yml pins versions, no conda lock)

## Frameworks

**Core:**
- PySide6 6.10.2 - Qt6 GUI framework (cross-platform desktop application)
- VTK 9.5.2 - 3D molecular visualization and rendering

**Scientific Computing:**
- NumPy 2.4.3 - Array operations, linear algebra, coordinate manipulation
- SciPy 1.17.1 - cKDTree neighbor search, spline interpolation, spatial algorithms
- Matplotlib 3.10.8 - Phase diagram generation (PNG, SVG output)

**Domain-Specific:**
- GenIce2 2.2.13.1 + GenIce-core 1.4.3 - Ice crystal structure generation engine
- IAPWS 1.5.5 - IAPWS water/steam thermodynamic property calculations
- spglib 2.7.0 - Crystal space group symmetry detection and validation
- NetworkX 3.6.1 - Graph algorithms (used by GenIce for hydrogen bond networks)
- Shapely 2.1.2 - Geometric operations (polygon centroids for phase diagram labels)

**CLI:**
- Click 8.3.1 - (transitive dependency; CLI uses argparse directly)
- argparse (stdlib) - Actual CLI argument parsing in `quickice/cli/parser.py`

**Testing:**
- pytest >=9.0.0 - Test runner

**Build/Dev:**
- PyInstaller 6.19.0 - Standalone executable bundling (spec: `quickice-gui.spec`)
- setuptools 80.10.2 - Python package tooling
- wheel 0.46.3 - Wheel packaging

## Key Dependencies

**Critical (application would fail without these):**
- `genice2` 2.2.13.1 - Core ice structure generation; no replacement available
- `genice-core` 1.4.3 - GenIce internals (plugin loading, GenIce class)
- `numpy` 2.4.3 - Every module uses NumPy arrays for positions, cells, calculations
- `pyside6` 6.10.2 - GUI framework; the entire `quickice/gui/` module depends on it
- `vtk` 9.5.2 - 3D molecular rendering via QVTKRenderWindowInteractor

**Infrastructure (important but replaceable):**
- `scipy` 1.17.1 - cKDTree used in `quickice/ranking/scorer.py`, `quickice/structure_generation/overlap_resolver.py`, `quickice/output/validator.py`; UnivariateSpline in `quickice/output/phase_diagram.py`
- `matplotlib` 3.10.8 - Phase diagram generation only (`quickice/output/phase_diagram.py`)
- `spglib` 2.7.0 - Structure validation only (`quickice/output/validator.py`)
- `shapely` 2.1.2 - Phase diagram polygon centroids only (`quickice/output/phase_diagram.py`)
- `iapws` 1.5.5 - Liquid-vapor boundary curve in phase diagram only
- `networkx` 3.6.1 - Used by GenIce internally for hydrogen bond network analysis

**Supporting:**
- `cycless` 0.7 - GenIce dependency (cycle detection in hydrogen bond networks)
- `graphstat` 0.3.3 - GenIce dependency (graph statistics)
- `pairlist` 0.6.4 - GenIce dependency (pair distance calculations)
- `methodtools` 0.4.7 - LRU cache for class methods
- `openpyscad` 0.5.0 - OpenSCAD format output (GenIce dependency)
- `wirerope` 1.0.0 - GenIce dependency (wire/rope data structures)
- `yaplotlib` 0.1.3 - GenIce dependency (yet another plot library)
- `deprecated` 1.3.1 / `deprecation` 2.1.0 - Deprecation decorators (GenIce deps)
- `six` 1.17.0 - Python 2/3 compatibility (GenIce dependency)
- `wrapt` 2.1.2 - Decorator utilities (transitive dependency)

## Configuration

**Environment:**
- Conda environment defined in `environment.yml` (runtime) and `environment-build.yml` (build)
- `setup.sh` activates conda env and sets `PYTHONPATH`/`PATH`
- No `.env` file; no environment variables required for core operation

**Build:**
- `quickice-gui.spec` - PyInstaller spec for GUI executable
- `scripts/build-linux.sh` - Linux build script
- `scripts/assemble-dist.sh` - Distribution tarball assembly
- `.github/workflows/build-windows.yml` - Windows CI build (manual trigger)

**Package:**
- No `setup.py`, `pyproject.toml`, or `setup.cfg` - package is imported via `PYTHONPATH`
- Version defined in `quickice/__init__.py`: `__version__ = "3.0.0"`

## Platform Requirements

**Development:**
- Linux (primary development platform)
- Windows (supported via CI build)
- Conda environment with Python 3.14.3
- Display server for GUI (X11/Wayland on Linux, native on Windows/macOS)
- VTK rendering requires OpenGL support

**Production:**
- PyInstaller bundles standalone executable for Linux and Windows
- Output: `dist/quickice-gui/quickice-gui` (Linux), `.zip` (Windows)
- Distribution tarballs: `quickice-{version}-linux-x86_64.tar.gz`, `quickice-{version}-windows-x86_64.zip`
- No server deployment; desktop application only

---

*Stack analysis: 2026-04-10*
