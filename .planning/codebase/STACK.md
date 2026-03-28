# Technology Stack

**Analysis Date:** 2026-03-28

## Languages

**Primary:**
- Python 3.14.3 - Core implementation language for all modules

**Secondary:**
- None detected - Pure Python codebase

## Runtime

**Environment:**
- Conda environment named `quickice`
- Python 3.14.3 with CPython implementation

**Package Manager:**
- Conda (primary) - Environment management via `env.yml`
- pip - Python package installation within conda environment
- Lockfile: Not present (no pip lockfile)

**Setup:**
- Run `conda env create -f env.yml` once to create environment
- Run `source setup.sh` in each new shell to activate and set PYTHONPATH

## Frameworks

**Core:**
- argparse - CLI argument parsing (standard library)
- dataclasses - Data structures (standard library)

**Testing:**
- pytest >=9.0.0 - Test framework

**Build/Dev:**
- No build system detected - direct Python execution
- No type checking tools configured
- No linting/formatting tools configured

## Key Dependencies

**Scientific Computing:**
- numpy 2.4.3 - Array operations, numerical computing
- scipy >=1.8 - Scientific algorithms, spline interpolation (`scipy.interpolate.UnivariateSpline`)
- networkx 3.6.1 - Graph algorithms for molecular networks

**Visualization:**
- matplotlib >=3.5 - Phase diagram plotting, publication-quality figures

**Molecular Simulation:**
- genice2 2.2.13.1 - Ice structure generation (core library)
- genice-core 1.4.3 - GenIce core functionality
- spglib 2.7.0 - Space group detection, crystal symmetry analysis
- pairlist 0.6.4 - Pair detection for molecular structures
- cycless 0.7 - Cycle detection in molecular networks

**Geometry:**
- shapely >=2.0 - Geometric operations, polygon handling for phase diagrams

**Water Properties:**
- iapws >=1.5.4 - IAPWS water/steam thermodynamic properties
  - Used for: `IAPWS97` class to compute liquid-vapor saturation curves

**Utilities:**
- click 8.3.1 - Present in dependencies but argparse used in implementation
- packaging 25.0 - Version parsing (standard library extension)

## Configuration

**Environment:**
- Conda environment defined in `env.yml`
- PYTHONPATH must include project root (set via `setup.sh`)
- No `.env` files or environment variables required

**Build:**
- No build configuration files (setup.py, pyproject.toml, etc.)
- Direct execution via `python quickice.py`

**Entry Point:**
- `quickice.py` - CLI entry point that imports from `quickice/` package

## Platform Requirements

**Development:**
- Linux/x86_64 platform (conda packages are platform-specific)
- Conda or Miniconda installed
- Python 3.14 compatible environment

**Production:**
- Any platform supporting Python 3.14 and listed dependencies
- No deployment infrastructure configured
- Output files written to local `output/` directory

## Dependency Graph

```
quickice.py
    └── quickice/main.py
            ├── quickice/cli/parser.py (argparse)
            ├── quickice/phase_mapping/
            │       ├── lookup.py (custom logic)
            │       ├── melting_curves.py (custom IAPWS equations)
            │       ├── solid_boundaries.py (linear interpolation)
            │       └── triple_points.py (data tables)
            ├── quickice/structure_generation/
            │       ├── generator.py (genice2, numpy)
            │       └── mapper.py (numpy)
            ├── quickice/ranking/
            │       └── scorer.py (numpy)
            └── quickice/output/
                    ├── orchestrator.py
                    ├── pdb_writer.py (numpy)
                    ├── validator.py (spglib, numpy)
                    └── phase_diagram.py (matplotlib, shapely, scipy, iapws)
```

---

*Stack analysis: 2026-03-28*
