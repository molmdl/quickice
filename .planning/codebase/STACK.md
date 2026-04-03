# Technology Stack

**Analysis Date:** 2026-04-04

## Languages

**Primary:**
- Python 3.14.3 - Main application language (from conda-forge)

**Secondary:**
- Shell (Bash) - Environment setup scripts (`setup.sh`, `run_oc.sh`)

## Runtime

**Environment:**
- Conda (Miniconda/Anaconda) - Package and environment management
- Environment name: `quickice`

**Package Manager:**
- Conda - Primary dependency management via `environment.yml`
- pip - Secondary for pip-only packages
- Lockfile: Not present (uses conda environment export)

## Frameworks

**Core:**
- PySide6 >= 6.9.3 - Qt-based GUI framework for desktop application
- VTK >= 9.5.2 - 3D visualization and molecular rendering engine

**Testing:**
- pytest >= 9.0.0 - Test runner and assertion framework

**Build/Dev:**
- PyInstaller >= 6.0 - Standalone executable packaging for distribution

## Key Dependencies

**Scientific Computing:**
- numpy 2.4.3 - Array operations and numerical computing
- scipy >= 1.8 - Scientific algorithms (cKDTree, interpolation, spline fitting)
- matplotlib >= 3.5 - Phase diagram visualization and plotting
- networkx 3.6.1 - Graph algorithms (for GenIce internal use)

**Domain-Specific:**
- genice2 2.2.13.1 - Ice crystal structure generation engine
- genice-core 1.4.3 - Core algorithms for GenIce
- iapws >= 1.5.4 - IAPWS-95 validated water/ice thermophysical properties
- spglib 2.7.0 - Crystal symmetry analysis and space group operations
- shapely >= 2.0 - Geometry operations for phase diagram polygons

**Molecular Simulation Utilities:**
- pairlist 0.6.4 - Neighbor list calculations
- cycless 0.7 - Cycle detection in molecular networks
- graphstat 0.3.3 - Graph statistics utilities
- openpyscad 0.5.0 - OpenSCAD integration (for potential 3D model export)
- yaplotlib 0.1.3 - Yet another plotting library

**Standard Library Extensions:**
- click 8.3.1 - CLI argument parsing (used alongside argparse)
- deprecated 1.3.1 / deprecation 2.1.0 - Deprecation warnings for API evolution

## Configuration

**Environment:**
- Conda environment defined in `environment.yml`
- Activation required via `source setup.sh` for each new shell
- PYTHONPATH must include project root for package imports

**Build:**
- PyInstaller spec: `quickice-gui.spec`
- GitHub Actions: `.github/workflows/build-windows.yml`

**Development Dependencies:**
- Defined in `requirements-dev.txt`:
  - pytest >= 9.0.0
  - pyinstaller >= 6.0

## Platform Requirements

**Development:**
- Linux: GLIBC 2.28+ (Ubuntu 20.04+, Debian 10+, Rocky/RHEL 8+)
- 64-bit architecture
- OpenGL support for VTK 3D rendering
- Qt 6.10.2 requires modern GLIBC

**Production:**
- Desktop application (CLI and GUI modes)
- Standalone Windows executable via PyInstaller packaging
- Cross-platform Python source distribution

---

*Stack analysis: 2026-04-04*
