# Technology Stack

**Analysis Date:** 2026-04-07

## Languages

**Primary:**
- Python 3.14.3 - All application code, CLI, GUI, and scientific computation

**Secondary:**
- None - Pure Python project

## Runtime

**Environment:**
- Conda (Miniconda/Anaconda)
- Environment name: `quickice`
- Build environment: `quickice-build`

**Package Manager:**
- Conda (conda-forge channel) for core dependencies
- pip for additional Python packages
- Lockfile: `environment.yml`, `environment-build.yml`

## Frameworks

**Core:**
- PySide6 6.10.2 - Qt6-based GUI framework for desktop application
- VTK 9.5.2 - 3D visualization toolkit for molecular rendering

**CLI:**
- argparse - Built-in argument parsing (custom validators)
- click 8.3.1 - Additional CLI utilities

**Testing:**
- pytest >=9.0.0 - Test runner and framework

**Build/Dev:**
- PyInstaller 6.19.0 - Creates standalone executables
- Conda - Environment management

## Key Dependencies

**Scientific Computing:**
- NumPy 2.4.3 - Array operations, numerical computation
- SciPy 1.17.1 - Spatial algorithms (cKDTree for neighbor search)
- Matplotlib 3.10.8 - Phase diagram visualization, plotting

**Ice Structure Generation:**
- genice2 2.2.13.1 - Ice crystal structure generation
- genice-core 1.4.3 - Core GenIce functionality
- pairlist 0.6.4 - Neighbor list calculations
- cycless 0.7 - Cycle detection in molecular networks
- graphstat 0.3.3 - Graph statistics
- yaplotlib 0.1.3 - Visualization utilities

**Thermodynamics:**
- iapws 1.5.5 - Water/steam thermodynamic properties (IAPWS standards)

**Molecular/Structural:**
- spglib 2.7.0 - Space group analysis
- networkx 3.6.1 - Graph algorithms
- shapely 2.1.2 - Geometry operations
- openpyscad 0.5.0 - OpenSCAD integration (3D geometry)

**Utilities:**
- deprecated 1.3.1 / deprecation 2.1.0 - Deprecation warnings
- methodtools 0.4.7 - Method decorators
- wirerope 1.0.0 - Utility decorators
- wrapt 2.1.2 - Decorator utilities
- six 1.17.0 - Python 2/3 compatibility

## Configuration

**Environment:**
- Conda environment files:
  - `environment.yml` - Runtime dependencies
  - `environment-build.yml` - Build-time dependencies (includes PyInstaller)
- Development dependencies: `requirements-dev.txt`
- Shell setup: `setup.sh` (activates conda, exports PYTHONPATH)

**Build:**
- PyInstaller spec: `quickice-gui.spec`
- Collects all data files from: iapws, genice2, matplotlib, scipy, numpy, shapely, networkx, spglib

**GitHub Actions:**
- `.github/workflows/build-windows.yml` - Manual Windows executable build
- `.github/dependabot.yml` - Weekly conda/pip dependency updates

## Platform Requirements

**Development:**
- Conda (Miniconda or Anaconda)
- OpenGL support for VTK 3D visualization
- Linux: GLIBC 2.28+ (Ubuntu 20.04+, Debian 10+, Rocky/RHEL 8+)
- 64-bit architecture

**Production:**
- Standalone executable (Windows): Built via PyInstaller
- No runtime dependencies when using executable
- Output formats: PDB, GRO, TOP, ITP, PNG, SVG

## File Format Support

**Input:**
- None (generates structures from parameters)

**Output:**
- PDB - Protein Data Bank format (molecular coordinates)
- GRO - GROMACS coordinate format
- TOP - GROMACS topology format
- ITP - GROMACS molecule topology (TIP4P-ICE water model)
- PNG/SVG - Phase diagram images

---

*Stack analysis: 2026-04-07*
