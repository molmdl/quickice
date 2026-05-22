# Technology Stack

**Analysis Date:** 2026-05-22

## Languages

**Primary:**
- Python 3.14.3 - All application code (GUI, CLI, structure generation, phase mapping, ranking, export)

**Secondary:**
- Shell (Bash) - Build scripts and environment setup (`scripts/build-linux.sh`, `scripts/assemble-dist.sh`, `scripts/run_gui_ssh.sh`, `scripts/run_oc.sh`)
- GROMACS topology language - Molecular force field parameter files (`.itp`, `.top`, `.gro` in `quickice/data/`)

## Runtime

**Environment:**
- CPython 3.14.3 (conda-forge build)
- Conda for environment management (environment name: `quickice`)

**Package Manager:**
- Conda (primary) + pip (secondary for PyPI-only packages)
- Lockfile: `environment.yml` (conda), no pip lockfile (no `requirements.txt` for runtime deps, only `requirements-dev.txt` for dev deps)

## Frameworks

**Core:**
- PySide6 6.10.2 - Qt6 GUI framework (cross-platform desktop UI)
- VTK 9.5.2 - 3D molecular visualization (via `vtkmodules` Python bindings)
- GenIce2 2.2.13.1 - Ice crystal structure generation engine
- genice-core 1.4.3 - Core GenIce library

**Testing:**
- pytest >= 9.0.0 - Unit and integration testing

**Build/Dev:**
- PyInstaller 6.19.0 - Standalone executable packaging (spec: `quickice-gui.spec`)

## Key Dependencies

**Critical:**
- numpy 2.4.3 - Array operations for all coordinate manipulation, cell matrices, supercell calculations. Used in every module.
- scipy 1.17.1 - `scipy.spatial.cKDTree` for neighbor search (H-bond detection, overlap detection, ion/solute placement), `scipy.spatial.transform.Rotation` for molecule orientation
- iapws 1.5.5 - IAPWS water/ice thermodynamic property formulations: `IAPWS95` for liquid water density, `_Ice` for Ice Ih density, `IAPWS97` for saturation curve in phase diagram
- matplotlib 3.10.8 - Phase diagram rendering (`FigureCanvasQTAgg` for Qt embedding, `Figure`, `Polygon` patches)
- shapely 2.1.2 - Geometric polygon operations for phase diagram click detection (`Point`, `Polygon` containment)
- click 8.3.1 - CLI framework (imported but argparse is actually used; click may be a GenIce2 transitive dep)

**Infrastructure:**
- networkx 3.6.1 - Graph operations (GenIce2 dependency for hydrogen bond network analysis)
- spglib 2.7.0 - Space group symmetry analysis (installed but not directly imported in QuickIce code; GenIce2 dependency)
- pairlist 0.6.4 - Pair list computation (GenIce2 dependency)
- cycless 0.7 - Cycle detection in molecular networks (GenIce2 dependency)
- graphstat 0.3.3 - Graph statistics (GenIce2 dependency)
- openpyscad 0.5.0 - OpenSCAD model generation (installed but not directly imported in QuickIce; GenIce2 utility)
- yaplotlib 0.1.3 - Yaplot visualization format (installed but not directly imported in QuickIce; GenIce2 utility)
- deprecated 1.3.1 / deprecation 2.1.0 - Deprecation decorators (GenIce2 dependencies)
- methodtools 0.4.7 - Method decorator utilities (GenIce2 dependency)
- wirerope 1.0.0 - Decorator utilities (GenIce2 dependency)
- wrapt 2.1.2 - Wrapper utilities (GenIce2 dependency)
- six 1.17.0 - Python 2/3 compatibility (GenIce2 dependency)

## Configuration

**Environment:**
- Conda environment defined in `environment.yml` (runtime) and `environment-build.yml` (build)
- Environment activation: `source setup.sh` (activates conda env, sets PYTHONPATH)
- No `.env` files or environment variable configuration

**Build:**
- PyInstaller spec: `quickice-gui.spec`
- Build script: `scripts/build-linux.sh` (uses `pyinstaller --clean quickice-gui.spec`)
- Data files bundled: `quickice/data/` directory (ITP, GRO topology files)

## Platform Requirements

**Development:**
- Conda (Miniconda/Anaconda) for environment management
- Linux (primary development platform; build script targets Linux)
- X11 display server (for GUI rendering; SSH X-forwarding supported via `scripts/run_gui_ssh.sh`)
- Python >= 3.14 (pinned in environment.yml)

**Production:**
- Linux standalone executable via PyInstaller (output: `dist/quickice-gui/quickice-gui`)
- Cross-platform potential (PySide6 and VTK are cross-platform, but build script targets Linux only)
- No server deployment; desktop application

## GenIce2 Integration

**Package ecosystem:**
- `genice2` 2.2.13.1 - Main ice structure generation library
- `genice-core` 1.4.3 - Core lattice algorithms

**GenIce2 modules used by QuickIce:**
- `genice2.genice.GenIce` - Main ice generation class (used in `quickice/structure_generation/generator.py` and `quickice/structure_generation/hydrate_generator.py`)
- `genice2.plugin.safe_import` - Plugin loader for lattices, molecules, and formatters
- `genice2.formats.gromacs` - GROMACS GRO format output
- `genice2.lattices.sI`, `sII`, `sH` - Hydrate lattice modules
- `genice2.molecules.tip3p` - TIP3P water model (3-site: O, H, H) for ice generation
- `genice2.molecules.tip4p` - TIP4P water model (4-site: OW, HW1, HW2, MW) for hydrate generation
- `genice2.valueparser.parse_guest` - Guest molecule specification parser

**Supported ice phases (via GenIce2 lattices):**
- Ice Ih (`ice1h`), Ice Ic (`ice1c`), Ice II (`ice2`), Ice III (`ice3`), Ice V (`ice5`), Ice VI (`ice6`), Ice VII (`ice7`), Ice VIII (`ice8`)
- Hydrate lattices: sI (`CS1`), sII (`CS2`), sH (`sH`)

## Scientific Libraries Usage

**iapws (IAPWS formulations):**
- `iapws.IAPWS95` → `quickice/phase_mapping/water_density.py` - Liquid water density (supports supercooled water)
- `iapws._iapws._Ice` → `quickice/phase_mapping/ice_ih_density.py` - Ice Ih density (IAPWS R10-06)
- `iapws.IAPWS97` → `quickice/gui/phase_diagram_widget.py` - Saturation curve for vapor region

**scipy:**
- `scipy.spatial.cKDTree` → H-bond detection, overlap detection, ion/solute placement (6 modules)
- `scipy.spatial.transform.Rotation` → Solute and custom molecule orientation (2 modules)

**shapely:**
- `shapely.geometry.Point`, `shapely.geometry.Polygon` → Phase diagram point-in-polygon testing (`quickice/gui/phase_diagram_widget.py`)

**matplotlib:**
- `matplotlib.backends.backend_qtagg.FigureCanvasQTAgg` → Qt-embedded phase diagram canvas
- `matplotlib.figure.Figure` → Phase diagram figure and viewport export
- `matplotlib.patches.Polygon` → Phase region rendering

**numpy:**
- Pervasive: coordinate arrays, cell matrices, supercell calculations, density computations, position wrapping

## Water Models

**TIP3P (3-site):** O, H, H — Used internally for ice structure generation via GenIce2. Normalized to TIP4P-ICE at export.

**TIP4P-ICE (4-site):** OW, HW1, HW2, MW — Final export format. MW virtual site computed at export time using α = 0.13458335. Template: `quickice/data/tip4p.gro`, topology: `quickice/data/tip4p-ice.itp`.

## Data Files

**Molecular topology files** (`quickice/data/`):
- `tip4p-ice.itp` - TIP4P-ICE water model topology
- `tip4p.gro` - Single TIP4P water molecule coordinates (template for water filling)
- `ch4.itp` - Methane topology (GAFF2)
- `ch4_hydrate.itp` - Hydrate cage methane topology
- `ch4_liquid.itp` - Liquid-phase methane topology
- `thf.itp` - Tetrahydrofuran topology (GAFF2)
- `thf_hydrate.itp` - Hydrate cage THF topology
- `thf_liquid.itp` - Liquid-phase THF topology

**Custom molecule examples** (`quickice/data/custom/`):
- `etoh.gro`, `etoh.itp`, `etoh.top`, `etoh.chg` - Ethanol example

**Phase data** (`quickice/phase_mapping/data/`):
- `ice_phases.json` - Phase metadata (names, densities, crystal forms)

**Water model parameters used in code:**
- TIP4P-ICE α = 0.13458335 (virtual site parameter, defined in `quickice/output/gromacs_writer.py`)
- Madrid2019 ion parameters (Na+, Cl- VDW sigma, epsilon, charge) defined in `quickice/structure_generation/gromacs_ion_export.py`

---

*Stack analysis: 2026-05-22*
