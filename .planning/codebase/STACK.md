# Technology Stack

**Analysis Date:** 2026-05-02

## Languages

**Primary:**
- Python 3.14.3 - Core application language (CLI, GUI, structure generation)

**Secondary:**
- Bash - Build scripts and environment setup

## Runtime

**Environment:**
- Conda (Miniconda/Anaconda) - Package and environment management
- Environment name: `quickice`

**Package Manager:**
- Conda (conda-forge channel) - Primary dependency management
- Pip - Python packages not available in conda

**Lockfile:**
- `environment.yml` - Conda environment specification with pinned versions
- `environment-build.yml` - Build environment for PyInstaller

## Frameworks

**Core:**
- GenIce2 2.2.13.1 - Ice crystal structure generation with hydrogen disorder
- genice-core 1.4.3 - Core algorithms for GenIce

**GUI:**
- PySide6 6.10.2 - Qt6 bindings for Python (cross-platform GUI)
- VTK 9.5.2 - 3D visualization toolkit for molecular rendering

**Testing:**
- pytest ≥9.0.0 - Unit testing framework

**Build/Dev:**
- PyInstaller 6.19.0 - Standalone executable packaging for distribution
- setuptools 80.10.2 - Python package building

## Key Dependencies

**Scientific Computing:**
- NumPy 2.4.3 - Numerical operations, array handling
- SciPy 1.17.1 - Spatial algorithms (cKDTree), scientific computing
- NetworkX 3.6.1 - Graph algorithms for molecular topology
- Shapely 2.1.2 - Computational geometry for overlap detection

**Visualization:**
- Matplotlib 3.10.8 - Phase diagram generation

**Water/Ice Physics:**
- iapws 1.5.5 - IAPWS-95 water properties, IAPWS R10-06 ice density
- spglib 2.7.0 - Crystal symmetry analysis

**Molecular Structure:**
- cycless 0.7 - Ring detection for structure analysis
- pairlist 0.6.4 - Neighbor list generation
- graphstat 0.3.3 - Graph statistics for molecular networks

**File Formats:**
- openpyscad 0.5.0 - OpenSCAD format output (future use)
- yaplotlib 0.1.3 - Visualization format utilities

**CLI:**
- Click 8.3.1 - Command-line interface framework

**Utilities:**
- deprecated 1.3.1, deprecation 2.1.0 - Deprecation warnings
- methodtools 0.4.7 - Method decorators
- wirerope 1.0.0, wrapt 2.1.2, six 1.17.0 - Utility libraries

## Configuration

**Environment:**
- Conda environment via `environment.yml` (runtime)
- Conda environment via `environment-build.yml` (build)
- Environment activated via `source setup.sh`

**Key Configuration Files:**
- `environment.yml` - Runtime dependencies
- `environment-build.yml` - Build dependencies for PyInstaller
- `quickice-gui.spec` - PyInstaller configuration for executable packaging
- `setup.sh` - Shell script to activate environment and set PYTHONPATH

**No external configuration files:**
- No `.env` files detected
- Settings are hardcoded in modules

## Platform Requirements

**Development:**
- Linux: GLIBC 2.28+ (Ubuntu 20.04+, Debian 10+, Rocky/RHEL 8+)
- 64-bit architecture
- OpenGL support for VTK 3D visualization
- Conda (Miniconda or Anaconda)

**Production:**
- Same as development for source distribution
- Windows: Supported via PyInstaller executable
- Linux: Supported via PyInstaller executable
- macOS: Not explicitly supported (no build workflow)

**Deployment Targets:**
- Source distribution (cross-platform with conda)
- Windows executable (via GitHub Actions)
- Linux executable (via local build script)

---

*Stack analysis: 2026-05-02*
