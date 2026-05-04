# Technology Stack

**Analysis Date:** 2026-05-05

## Languages

**Primary:**
- Python 3.14.3 - Core application logic (entire codebase)

**Secondary:**
- None detected

## Runtime

**Environment:**
- Conda (Miniconda/Anaconda)
- Environment name: `quickice`

**Package Manager:**
- Conda (primary) - `environment.yml`, `environment-build.yml`
- Pip (secondary) - pip dependencies specified in conda environment files
- Lockfile: Present (conda environment files with pinned versions)

## Frameworks

**Core:**
- PySide6 6.10.2 - Qt6-based GUI framework
- VTK 9.5.2 - 3D molecular visualization

**Testing:**
- pytest 9.0.0+ - Test framework and runner

**Build/Dev:**
- PyInstaller 6.19.0 - Executable bundling for distribution
- setuptools 80.10.2 - Package management

## Key Dependencies

**Critical:**

**Scientific Computing:**
- numpy 2.4.3 - Array operations, numerical computing
- scipy 1.17.1 - Spatial algorithms (cKDTree for neighbor search), scientific computing
- networkx 3.6.1 - Graph algorithms for molecular networks

**Ice/Hydrate Generation:**
- genice2 2.2.13.1 - Ice structure generation engine
- genice-core 1.4.3 - Core GenIce functionality
- cycless 0.7 - Cyclic structure detection
- pairlist 0.6.4 - Pair interaction handling

**Thermodynamics & Physics:**
- iapws 1.5.5 - IAPWS water/steam properties (IAPWS-95, IAPWS-97 formulations)
- iapws._iapws._Ice - Ice-specific IAPWS calculations

**Structure Analysis:**
- spglib 2.7.0 - Space group analysis for crystal structures
- shapely 2.1.2 - Geometric operations (polygon containment for phase diagrams)

**Visualization:**
- matplotlib 3.10.8 - Phase diagram plotting, figure generation
- vtkmodules - VTK Python bindings for 3D rendering

**Utility:**
- click 8.3.1 - CLI framework (currently using argparse instead)
- openpyscad 0.5.0 - OpenSCAD format support
- deprecated 1.3.1, deprecation 2.1.0 - Deprecation warnings
- methodtools 0.4.7 - Method decorators
- wirerope 1.0.0, wrapt 2.1.2 - Function wrapping utilities
- six 1.17.0 - Python 2/3 compatibility (legacy)
- yaplotlib 0.1.3 - Yet Another Plot Library
- graphstat 0.3.3 - Graph statistics

**Infrastructure:**
- None (desktop application, no server infrastructure)

## Configuration

**Environment:**
- Conda environment managed via `environment.yml`
- Setup script: `setup.sh` (activates conda env, sets PYTHONPATH)
- Environment variables:
  - `PYTHONPATH` - Project root added for package imports
  - `DISPLAY` - X11 display for GUI (Linux)
  - `QUICKICE_FORCE_VTK` - Override VTK availability check
  - `__GLX_VENDOR_LIBRARY_NAME` - Set to 'mesa' for software rendering

**Build:**
- `environment-build.yml` - Build environment with PyInstaller
- `quickice-gui.spec` - PyInstaller configuration
- Bundles data files from `quickice/data/`
- Collects all dependencies: iapws, genice2, matplotlib, scipy, numpy, shapely, networkx, spglib

## Platform Requirements

**Development:**
- Python 3.14.3
- Conda (Miniconda or Anaconda)
- OpenGL support (for VTK 3D visualization)
- X11 display (Linux GUI)

**Production:**
- **Linux:** GLIBC 2.28+ (Ubuntu 20.04+, Debian 10+, Rocky/RHEL 8+)
- **Windows:** Windows executable via PyInstaller
- OpenGL support required for GUI visualization
- 64-bit architecture

**Deployment:**
- Built as standalone executable using PyInstaller
- Distribution: `quickice-v4.0.0-windows-x86_64.zip` (Windows)
- Linux: Source distribution with conda environment

---

*Stack analysis: 2026-05-05*
