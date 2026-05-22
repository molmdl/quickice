# Technology Stack

**Analysis Date:** 2026-05-22

## Languages

**Primary:**
- Python 3.14.3 - All application logic (CLI, GUI, scientific computation, export)

**Secondary:**
- GROMACS topology language (.itp/.top files) - Molecular force field definitions in `quickice/data/`
- GROMACS coordinate format (.gro files) - Molecular structure files in `quickice/data/`

## Runtime

**Environment:**
- CPython 3.14.3 (conda-forge build, cp314 ABI)

**Package Manager:**
- conda (conda-forge channel) - Primary environment management
- pip - Secondary package installation within conda environment
- Lockfile: `environment.yml` (conda lock equivalent); `environment-build.yml` for build environments

**Environment Setup:**
```bash
conda env create -f environment.yml    # Development environment
source setup.sh                         # Activate + set PYTHONPATH
```

## Frameworks

**Core:**
- PySide6 6.10.2 - Qt6 GUI framework for desktop application (MVVM architecture)
- VTK 9.5.2 - 3D molecular visualization with Qt integration via `vtkmodules.qt.QVTKRenderWindowInteractor`
- GenIce2 2.2.13.1 - Ice crystal structure generation engine (lattice generation + hydrogen bond networks)

**Testing:**
- pytest >=9.0.0 - Test runner (no pytest.ini or conftest.py at project root; per-directory conftest in `tests/test_output/`)

**Build/Dev:**
- PyInstaller >=6.0 (pinned 6.19.0 in build env) - Standalone executable packaging
- GitHub Actions - CI/CD for Windows executable builds

## Key Dependencies

**Critical:**

| Package | Version | Purpose | Used In |
|---------|---------|---------|---------|
| genice2 | 2.2.13.1 | Ice lattice generation (sI/sII/sH hydrates + 8 ice phases) | `quickice/structure_generation/generator.py`, `quickice/structure_generation/hydrate_generator.py` |
| genice-core | 1.4.3 | Core lattice computation library | Transitive dependency of genice2 |
| iapws | 1.5.5 | IAPWS thermodynamic formulations (Ice Ih density via R10-06, water density via IAPWS-95, steam tables via IAPWS-97) | `quickice/phase_mapping/ice_ih_density.py`, `quickice/phase_mapping/water_density.py`, `quickice/gui/phase_diagram_widget.py` |
| numpy | 2.4.3 | Array operations for all molecular coordinates and cell matrices | Everywhere |
| scipy | 1.17.1 | cKDTree for PBC-aware overlap detection, Rotation for molecule orientation | `quickice/structure_generation/overlap_resolver.py`, `quickice/structure_generation/solute_inserter.py`, `quickice/structure_generation/custom_molecule_inserter.py`, `quickice/gui/vtk_utils.py`, `quickice/ranking/scorer.py` |
| matplotlib | 3.10.8 | Phase diagram rendering (PNG/SVG) with Qt embedding (FigureCanvasQTAgg) | `quickice/output/phase_diagram.py`, `quickice/gui/phase_diagram_widget.py`, `quickice/gui/export.py` |
| shapely | 2.1.2 | Phase polygon geometry for point-in-polygon detection | `quickice/gui/phase_diagram_widget.py` |
| networkx | 3.6.1 | Graph algorithms (transitive dep of genice2) | GenIce2 internal |
| spglib | 2.7.0 | Space group detection (transitive dep of genice2) | GenIce2 internal |

**Infrastructure:**

| Package | Version | Purpose |
|---------|---------|---------|
| click | 8.3.1 | CLI framework (transitive dep of genice2) |
| pairlist | 0.6.4 | Pair list computation (transitive dep of genice2) |
| cycless | 0.7 | Cycle detection in molecular networks (transitive dep of genice2) |
| graphstat | 0.3.3 | Graph statistics (transitive dep of genice2) |
| openpyscad | 0.5.0 | OpenSCAD output (transitive dep of genice2) |
| methodtools | 0.4.7 | Method decorators (transitive dep of genice2) |
| wirerope | 1.0.0 | Function wrapping (transitive dep of genice2) |
| deprecated | 1.3.1 | Deprecation decorators (transitive dep of genice2) |
| deprecation | 2.1.0 | Deprecation support (transitive dep of genice2) |
| wrapt | 2.1.2 | Decorator utilities (transitive dep of genice2) |
| six | 1.17.0 | Python 2/3 compatibility (transitive dep) |
| yaplotlib | 0.1.3 | Visualization (transitive dep of genice2) |

## Configuration

**Environment:**
- Conda environment defined in `environment.yml` (development) and `environment-build.yml` (build)
- `PYTHONPATH` must include project root (set by `setup.sh`)
- No `.env` files or environment variables required at runtime
- Optional: `QUICKICE_FORCE_VTK=true` to force VTK initialization in SSH X11 forwarding

**Build:**
- `quickice-gui.spec` - PyInstaller configuration
  - Entry point: `quickice/gui/__main__.py`
  - Data files: `quickice/data` (ITP/GRO templates)
  - Excludes: `*/tests/*`, `*/docs/*`, `*/__pycache__/*` (security hardening)
  - Collect-all hooks for: iapws, genice2, genice_core, matplotlib, scipy, numpy, shapely, networkx, spglib
  - Output: `dist/quickice-gui/` (COLLECT mode, not onefile)

## Platform Requirements

**Development:**
- Linux (primary development platform per environment.yml)
- Windows (supported via GitHub Actions CI)
- Conda with conda-forge channel access
- Display server for VTK (X11 on Linux; `QUICKICE_FORCE_VTK=true` for SSH forwarding)

**Production:**
- Windows executable (primary distribution target, built via GitHub Actions)
- Linux: Run from source with conda environment
- No server/cloud deployment (desktop application)

## Physical Constants & Scientific References

**Hardcoded in codebase:**
- `AVOGADRO = 6.02214076e23` (CODATA 2017) - in `quickice/structure_generation/ion_inserter.py` and `quickice/structure_generation/solute_inserter.py`
- `TIP4P_ICE_ALPHA = 0.13458335` (TIP4P-ICE dummy atom position) - in `quickice/output/gromacs_writer.py`
- IAPWS R14-08(2011) melting curve equations - in `quickice/phase_mapping/melting_curves.py`
- IAPWS R10-06(2009) Ice Ih equation of state - via `iapws._iapws._Ice` in `quickice/phase_mapping/ice_ih_density.py`
- IAPWS-95 formulation for liquid water density - via `iapws.IAPWS95` in `quickice/phase_mapping/water_density.py`
- Madrid2019 ion parameters (Zeron et al., J. Chem. Phys. 2019) - in `quickice/structure_generation/gromacs_ion_export.py`

## Force Field Data Files

**Located in `quickice/data/`:**
- `tip4p-ice.itp` - TIP4P-ICE water model topology (primary water model)
- `tip4p.gro` - TIP4P water template coordinates (used for water filling)
- `ch4.itp` - Methane (all-atom, GAFF)
- `ch4_hydrate.itp` - Methane in hydrate cage topology
- `ch4_liquid.itp` - Methane in liquid topology
- `thf.itp` - Tetrahydrofuran (all-atom, GAFF)
- `thf_hydrate.itp` - THF in hydrate cage topology
- `thf_liquid.itp` - THF in liquid topology
- `custom/etoh.itp` - Ethanol custom molecule example

---

*Stack analysis: 2026-05-22*
