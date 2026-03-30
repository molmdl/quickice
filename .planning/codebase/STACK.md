# Technology Stack

**Analysis Date:** 2026-03-30

## Languages

**Primary:**
- Python 3.14.3 - Main application code, CLI, all modules

**Secondary:**
- Shell (bash) - Setup scripts (`setup.sh`, `run_oc.sh`)

## Runtime

**Environment:**
- Conda (Miniconda/Anaconda) - Environment management via `env.yml`

**Package Manager:**
- pip (within conda environment)
- Lockfile: Not present (uses conda environment specification)

## Frameworks

**Core:**
- Click 8.3.1 - CLI argument parsing (`quickice/cli/parser.py`)
- GenIce2 2.2.13.1 - Ice structure generation engine
- GenIce-core 1.4.3 - Core lattice algorithms for GenIce

**Testing:**
- pytest >= 9.0.0 - Unit testing framework

**Visualization:**
- matplotlib >= 3.5 - Phase diagram generation (PNG/SVG output)

## Key Dependencies

**Scientific Computing:**
- numpy 2.4.3 - Array operations, coordinate transformations, distance calculations
- scipy >= 1.8 - KDTree for neighbor search, spline interpolation for curves
- shapely >= 2.0 - Polygon geometry for phase diagram regions

**Domain-Specific:**
- iapws >= 1.5.4 - IAPWS-95/97 water property standards (melting curves, saturation curves)
- spglib 2.7.0 - Space group analysis for structure validation
- networkx 3.6.1 - Graph operations (used by GenIce for hydrogen bond networks)
- pairlist 0.6.4 - Neighbor list calculations
- cycless 0.7 - Cycle detection in molecular structures

**Utilities:**
- methodtools 0.4.7 - Method decorators
- deprecated 1.3.1 / deprecation 2.1.0 - Deprecation warnings
- six 1.17.0 - Python 2/3 compatibility
- wrapt 2.1.2 / wirerope 1.0.0 - Wrapper utilities
- openpyscad 0.5.0 - OpenSCAD integration (potential 3D output)
- yaplotlib 0.1.3 - Visualization library
- graphstat 0.3.3 - Graph statistics

## Configuration

**Environment:**
- Conda environment defined in `env.yml`
- Environment name: `quickice`
- No `.env` files - configuration via CLI arguments
- Setup via `source setup.sh` which activates conda and exports PYTHONPATH

**Build:**
- No build step required (pure Python)
- Entry point: `quickice.py` (wrapper) or `quickice.main:main` (module)

## Platform Requirements

**Development:**
- Python 3.14+ required
- Conda environment for dependency management
- pytest for running tests

**Production:**
- Pure Python application - portable to any platform with Python 3.14+
- No database or external service dependencies
- File-based output (PDB files, PNG/SVG diagrams)
- Can run as standalone CLI tool

## External File Formats

**Input:**
- None (all inputs via CLI arguments)

**Output:**
- PDB (Protein Data Bank format) - Crystal structure files
- PNG - Phase diagram raster images
- SVG - Phase diagram vector images
- TXT - Phase diagram data files

**Intermediate:**
- GRO (GROMACS format) - Internal GenIce format, parsed and converted to PDB

## Code Organization

**Package Structure:**
- `quickice.py` - CLI entry point
- `quickice/` - Main package directory
  - `main.py` - Workflow orchestration
  - `cli/` - Command-line argument parsing
  - `validation/` - Input validation
  - `phase_mapping/` - T,P to ice polymorph lookup
  - `structure_generation/` - GenIce2 integration
  - `ranking/` - Candidate scoring
  - `output/` - PDB writing and phase diagrams

---

*Stack analysis: 2026-03-30*