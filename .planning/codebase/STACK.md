# Technology Stack

**Analysis Date:** 2026-05-12

## Languages

**Primary:**
- Python 3.14.3 - Main application language, used throughout the entire codebase

**Secondary:**
- Shell (Bash) - Setup script and build automation
- YAML - Conda environment configuration

## Runtime

**Environment:**
- Conda (Miniconda/Anaconda) - Environment management
- Python 3.14.3 with CPython interpreter

**Package Manager:**
- pip (via Conda) - Python package installation
- Conda - Binary dependency management (VTK, PySide6, NumPy)
- Lockfile: Not present (environment.yml pins versions)

## Frameworks

**Core:**
- PySide6 6.10.2 - Qt6-based GUI framework for cross-platform desktop application
- VTK 9.5.2 - 3D visualization toolkit for molecular rendering

**Testing:**
- pytest >=9.0.0 - Test framework

**Build/Dev:**
- PyInstaller 6.19.0 - Build standalone executables from Python application
- GitHub Actions - CI/CD for Windows builds

## Key Dependencies

**Critical:**
- `genice2` 2.2.13.1 - Ice crystal structure generation library
- `genice-core` 1.4.3 - Core algorithms for GenIce
- `iapws` 1.5.5 - IAPWS-95 water/ice thermodynamic properties
- `numpy` 2.4.3 - Numerical operations, array handling
- `scipy` 1.17.1 - Scientific computing, spatial algorithms

**Visualization:**
- `vtk` 9.5.2 - 3D molecular rendering (ball-and-stick, stick, VDW styles)
- `matplotlib` 3.10.8 - Phase diagram plotting, 2D visualization
- `PySide6` 6.10.2 - Qt GUI components

**Structure Analysis:**
- `networkx` 3.6.1 - Graph algorithms for molecular networks
- `spglib` 2.7.0 - Space group analysis and crystal symmetry
- `shapely` 2.1.2 - Computational geometry for boundary detection
- `cycless` 0.7 - Cycle detection in molecular graphs

**File I/O:**
- `openpyscad` 0.5.0 - OpenSCAD file generation (used for structural exports)

**Utility:**
- `click` 8.3.1 - CLI argument parsing (alternative to argparse)
- `methodtools` 0.4.7 - Method decorators
- `deprecated` 1.3.1, `deprecation` 2.1.0 - Deprecation warnings
- `pairlist` 0.6.4 - Pair-wise distance calculations
- `graphstat` 0.3.3 - Graph statistics
- `yaplotlib` 0.1.3 - Yet Another Plot Library

## Configuration

**Environment:**
- Conda environment: `quickice` (development) or `quickice-build` (build)
- Environment files: `environment.yml`, `environment-build.yml`
- Setup script: `setup.sh` (sets PYTHONPATH, activates conda env)
- No `.env` files - application uses bundled data files

**Build:**
- PyInstaller spec file: `quickice-gui.spec`
- Entry point: `quickice/gui/__main__.py`
- Bundled data: `quickice/data/` (force field files)

**Key Configurations Required:**
- PYTHONPATH must include project root for package imports
- OpenGL support for 3D visualization

## Platform Requirements

**Development:**
- Linux 64-bit with GLIBC 2.28+ (Ubuntu 20.04+, Debian 10+, Rocky/RHEL 8+)
- Conda (Miniconda or Anaconda)
- OpenGL support for VTK rendering

**Production:**
- Linux 64-bit or Windows 64-bit
- OpenGL support for 3D visualization
- Pre-built executables distributed via GitHub releases

**Binary Distribution:**
- Linux: `quickice-gui` executable
- Windows: `quickice-gui.exe` executable
- No Python/Conda required for end users

---

*Stack analysis: 2026-05-12*
