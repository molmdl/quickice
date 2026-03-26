# Technology Stack

**Analysis Date:** 2026-03-26

## Languages

**Primary:**
- Python 3.9+ - Main implementation language

**Secondary:**
- None - Pure Python implementation

## Runtime

**Environment:**
- Python 3.9+ (specified in pyproject.toml)

**Package Manager:**
- Poetry (poetry.toml present)
- pip/setuptools fallback (setup.py alternative)
- Lockfile: Not present in repo (would be poetry.lock)

## Frameworks

**Core:**
- genice-core >=0.9 - Core algorithm for ice rule satisfaction and depolarization

**Testing:**
- pytest ^8.1.1 - Unit testing framework

**Build/Dev:**
- Poetry - Dependency management and build
- setuptools - Alternative build backend

## Key Dependencies

**Critical:**
- numpy >=1.26.2 - Array operations, coordinate transformations
- networkx >=2.0 - Graph representation and manipulation
- pairlist >=0.5.1.2 - Neighbor pair detection for periodic systems
- cycless >=0.4.2 - Cycle detection for ring analysis
- graphstat >=0.2.1 - Graph statistics and comparison
- yaplotlib >=0.1.2 - Visualization output
- openpyscad >=0.5.0 - OpenSCAD output format

**Infrastructure:**
- importlib_metadata - Entry point discovery (Python <3.10)
- Python standard library: logging, argparse, itertools, collections

## Configuration

**Environment:**
- No environment variables required
- Plugins can be loaded from local `lattices/`, `formats/`, `molecules/` directories

**Build:**
- pyproject.toml - Main configuration
- poetry.toml - Poetry-specific settings

**Package Entry Points:**
- `genice2_lattice` - Lattice plugins
- `genice2_format` - Format plugins  
- `genice2_molecule` - Molecule plugins
- `genice2_loader` - Input file loaders
- `genice2_group` - Functional group plugins

## Platform Requirements

**Development:**
- Python 3.9+
- For M1 Mac: Additional scipy dependencies may be needed

**Production:**
- Any Python 3.9+ environment
- No compiled extensions (pure Python)

**Optional Dependencies:**
- Jupyter/IPython notebooks for interactive use (ipykernel ^6.27.1)
- py3dmol for 3D visualization (^2.0.4)
- matplotlib for plotting (^3.8.2)
- genice2-cage for cage analysis (^2.2)
- genice2-svg for SVG output (^2.2)
- genice2-mdanalysis for MDAnalysis integration (^0.6.5)

---

## Dependency Graph

```
genice2
├── genice-core (external) ─── ice_graph algorithm
├── numpy ─────────────────── array operations
├── networkx ──────────────── graph data structure
├── pairlist ──────────────── neighbor detection
├── cycless ───────────────── cycle/polyhedra detection
├── graphstat ─────────────── graph comparison
├── yaplotlib ─────────────── YaPlot visualization
└── openpyscad ───────────── OpenSCAD output
```

## Installation Methods

**From PyPI:**
```bash
pip install genice2
```

**From Source:**
```bash
git clone https://github.com/vitroid/GenIce
cd GenIce
pip install .
```

**Development:**
```bash
pip install -e .
./genice.x  # Uses local source
```

---

*Stack analysis: 2026-03-26*