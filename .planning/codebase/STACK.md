# Technology Stack

**Analysis Date:** 2026-03-31

## Languages

**Primary:**
- Python 3.14.3 - Main application language (all source code in `quickice/` package)

**Secondary:**
- Shell (Bash) - Setup script (`setup.sh`) and run script (`run_oc.sh`)

## Runtime

**Environment:**
- Conda (Miniconda/Anaconda) - Environment management
- Environment name: `quickice`

**Package Manager:**
- pip (via conda) - Python package installation
- Lockfile: Not present (env.yml specifies exact versions)

## Frameworks

**Core:**
- None (pure Python scientific application)

**Testing:**
- pytest >= 9.0.0 - Unit testing framework (`requirements-dev.txt`)

**Build/Dev:**
- No build system (source installation via PYTHONPATH)
- No linter/formatter configuration detected

## Key Dependencies

**Scientific Computing:**
- `numpy` 2.4.3 - Numerical arrays, matrix operations, coordinate handling
- `scipy` >= 1.8 - Spatial algorithms (`cKDTree` for neighbor search), interpolation (`UnivariateSpline`)
- `matplotlib` >= 3.5 - Phase diagram visualization (PNG/SVG output)

**Molecular Structure Generation:**
- `genice2` 2.2.13.1 - Ice structure generation with hydrogen bond networks
- `genice-core` 1.4.3 - Core algorithms for GenIce
- `pairlist` 0.6.4 - Pair list calculations
- `cycless` 0.7 - Cycle detection for hydrogen bond networks
- `graphstat` 0.3.3 - Graph statistics

**Crystallography:**
- `spglib` 2.7.0 - Space group analysis and crystal symmetry

**Thermodynamics:**
- `iapws` >= 1.5.4 - IAPWS-95 water/ice thermodynamic properties

**Geometry/Graph:**
- `shapely` >= 2.0 - Polygon geometry for phase diagram regions
- `networkx` 3.6.1 - Graph algorithms

**CLI:**
- `click` 8.3.1 - Listed in dependencies (but `argparse` used directly in code)
- `argparse` (stdlib) - Actual CLI argument parsing

## Configuration

**Environment:**
- Conda environment file: `env.yml` - Defines all dependencies with versions
- PYTHONPATH setup: `setup.sh` adds project root to Python path
- No `.env` file required - pure Python application

**Build:**
- No build configuration (install via conda env create)
- Development installation: `source setup.sh` after conda env create

## Platform Requirements

**Development:**
- Linux (tested on Linux with libgcc, OpenMP support)
- Conda (Miniconda or Anaconda)
- Python 3.14 compatible environment

**Production:**
- Platform-independent Python application
- Dependencies installable via pip (through conda)
- No database or external service required
- Output files written to local filesystem

## Dependency Groups

**Core Runtime (from env.yml pip section):**
```
click==8.3.1
cycless==0.7
deprecated==1.3.1
deprecation==2.1.0
genice-core==1.4.3
genice2==2.2.13.1
graphstat==0.3.3
iapws>=1.5.4
matplotlib>=3.5
methodtools==0.4.7
networkx==3.6.1
numpy==2.4.3
openpyscad==0.5.0
pairlist==0.6.4
scipy>=1.8
shapely>=2.0
six==1.17.0
spglib==2.7.0
wirerope==1.0.0
wrapt==2.1.2
yaplotlib==0.1.3
```

**Development Only (from requirements-dev.txt):**
```
pytest>=9.0.0
```

## Version Constraints

**Pinned Versions:**
- Most packages use exact versions (e.g., `numpy==2.4.3`)
- Scientific packages use minimum versions (`scipy>=1.8`, `matplotlib>=3.5`, `iapws>=1.5.4`)

**Python Version:**
- Python 3.14.3 (specific version in env.yml)

---

*Stack analysis: 2026-03-31*