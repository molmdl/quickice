# Technology Stack

**Analysis Date:** 2026-06-08

## Languages

**Primary:**
- Python 3.14.3 - All application logic (CLI, GUI, scientific computation, export pipeline)

**Secondary:**
- GROMACS topology language (.itp/.top files) - Molecular force field definitions in `quickice/data/`
- GROMACS coordinate format (.gro files) - Molecular structure templates in `quickice/data/`

## Runtime

**Environment:**
- CPython 3.14.3 (conda-forge build, cp314 ABI)
- ABI tag: `cp314`

**Package Manager:**
- conda (conda-forge channel) - Primary environment management with `environment.yml`
- pip - Secondary package installation within conda environment (pinned in `environment.yml` pip section)
- Lockfile: `environment.yml` (conda lock equivalent); `environment-build.yml` for build environments

**Environment Setup:**
```bash
conda env create -f environment.yml    # Development environment
source setup.sh                         # Activate + set PYTHONPATH
```

## Frameworks

**Core:**
- PySide6 6.10.2 - Qt6 GUI framework for desktop application (MVVM architecture with `QMainWindow`, `QTabWidget`, signals/slots)
- VTK 9.5.2 - 3D molecular visualization with Qt integration via `vtkmodules.qt.QVTKRenderWindowInteractor`
- GenIce2 2.2.13.1 - Ice crystal structure generation engine (lattice generation + hydrogen bond networks + hydrate lattices)

**Testing:**
- pytest >=9.0.0 - Test runner (no root conftest.py; per-directory conftest in `tests/` and `tests/test_output/`)
- Module-scoped fixtures amortize expensive GenIce2 calls (~3-5s each)

**Build/Dev:**
- PyInstaller 6.19.0 - Standalone executable packaging (COLLECT mode, not onefile)
- GitHub Actions - CI/CD for Windows executable builds (manual trigger only)

## Key Dependencies

**Critical:**

| Package | Version | Purpose | Used In |
|---------|---------|---------|---------|
| genice2 | 2.2.13.1 | Ice lattice generation (8 ice phases + sI/sII/sH hydrates) | `quickice/structure_generation/generator.py`, `quickice/structure_generation/hydrate_generator.py` |
| genice-core | 1.4.3 | Core lattice computation library | Transitive dependency of genice2 |
| iapws | 1.5.5 | IAPWS thermodynamic formulations (Ice Ih density via R10-06, water density via IAPWS-95, steam tables via IAPWS-97) | `quickice/phase_mapping/ice_ih_density.py`, `quickice/phase_mapping/water_density.py`, `quickice/gui/phase_diagram_widget.py` |
| numpy | 2.4.3 | Array operations for all molecular coordinates and cell matrices | Everywhere — positions, cells, supercell, density |
| scipy | 1.17.1 | cKDTree for PBC-aware overlap/neighbor detection; Rotation for molecule orientation | `quickice/structure_generation/overlap_resolver.py`, `quickice/structure_generation/solute_inserter.py`, `quickice/structure_generation/custom_molecule_inserter.py`, `quickice/structure_generation/ion_inserter.py`, `quickice/gui/vtk_utils.py`, `quickice/ranking/scorer.py`, `quickice/output/validator.py` |
| matplotlib | 3.10.8 | Phase diagram rendering (PNG/SVG) with Qt embedding (`FigureCanvasQTAgg`) | `quickice/output/phase_diagram.py`, `quickice/gui/phase_diagram_widget.py`, `quickice/gui/export.py` |
| shapely | 2.1.2 | Phase polygon geometry for point-in-polygon detection | `quickice/gui/phase_diagram_widget.py` |
| spglib | 2.7.0 | Space group symmetry detection for crystal structure validation | `quickice/output/validator.py` (direct import); also transitive dep of genice2 |

**Infrastructure:**

| Package | Version | Purpose |
|---------|---------|---------|
| click | 8.3.1 | CLI framework (transitive dep of genice2) |
| pairlist | 0.6.4 | Pair list computation (transitive dep of genice2) |
| cycless | 0.7 | Cycle detection in molecular networks (transitive dep of genice2) |
| graphstat | 0.3.3 | Graph statistics (transitive dep of genice2) |
| openpyscad | 0.5.0 | OpenSCAD output (transitive dep of genice2) |
| networkx | 3.6.1 | Graph algorithms (transitive dep of genice2, used internally for hydrogen bond networks) |
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
- Optional: `QUICKICE_FORCE_VTK=true` to force VTK initialization in SSH X11 forwarding environments
- Optional: `DISPLAY` - X11 display variable (checked by VTK availability detection in viewer modules)

**Build:**
- `quickice-gui.spec` - PyInstaller configuration
  - Entry point: `quickice/gui/__main__.py`
  - Data files: `quickice/data` (ITP/GRO templates)
  - Excludes: `*/tests/*`, `*/docs/*`, `*/__pycache__/*` (security hardening)
  - Collect-all hooks for: iapws, genice2, genice_core, matplotlib, scipy, numpy, shapely, networkx, spglib
  - Output: `dist/quickice-gui/` (COLLECT mode, not onefile)
  - UPX compression: enabled
  - Console mode: disabled (windowed application)

## Platform Requirements

**Development:**
- Linux (primary development platform)
- Windows (supported via GitHub Actions CI)
- Conda with conda-forge channel access
- Display server for VTK (X11 on Linux; `QUICKICE_FORCE_VTK=true` for SSH forwarding)
- Python 3.14.3 (pinned in environment.yml)

**Production:**
- Windows executable (primary distribution target, built via GitHub Actions)
- Linux: Run from source with conda environment + `setup.sh`
- No server/cloud deployment (desktop application)

## Physical Constants & Scientific References

**Hardcoded in codebase:**
- `AVOGADRO = 6.02214076e23` (CODATA 2017) - in `quickice/structure_generation/ion_inserter.py` and `quickice/structure_generation/solute_inserter.py`
- `TIP4P_ICE_ALPHA = 0.13458335` (TIP4P-ICE dummy atom position) - in `quickice/output/gromacs_writer.py`
- IAPWS R14-08(2011) melting curve equations - in `quickice/phase_mapping/melting_curves.py`
- IAPWS R10-06(2009) Ice Ih equation of state - via `iapws._iapws._Ice` in `quickice/phase_mapping/ice_ih_density.py`
- IAPWS-95 formulation for liquid water density - via `iapws.IAPWS95` in `quickice/phase_mapping/water_density.py`
- Madrid2019 ion parameters (Zeron et al., J. Chem. Phys. 2019) - in `quickice/structure_generation/gromacs_ion_export.py`
- Ion VDW radii: NA_VDW_RADIUS=0.190nm, CL_VDW_RADIUS=0.181nm - in `quickice/structure_generation/ion_inserter.py`
- Ion charges: NA_CHARGE=0.85, CL_CHARGE=-0.85 - in `quickice/structure_generation/gromacs_ion_export.py`
- Ion Lennard-Jones: NA_SIGMA=0.22173668nm, CL_SIGMA=0.46990563nm - in `quickice/structure_generation/gromacs_ion_export.py`

## Force Field Data Files

**Located in `quickice/data/`:**
- `tip4p-ice.itp` - TIP4P-ICE water model topology (primary water model for all GROMACS exports)
- `tip4p.gro` - TIP4P water template coordinates (used for water filling in interface generation)
- `ch4.itp` - Methane (all-atom, GAFF force field)
- `ch4_hydrate.itp` - Methane in hydrate cage topology
- `ch4_liquid.itp` - Methane in liquid topology (atomtypes commented out for compatibility)
- `thf.itp` - Tetrahydrofuran (all-atom, GAFF force field)
- `thf_hydrate.itp` - THF in hydrate cage topology
- `thf_liquid.itp` - THF in liquid topology
- `custom/etoh.itp` - Ethanol custom molecule example
- `custom/etoh.gro` - Ethanol custom molecule coordinates
- `custom/etoh.chg` - Ethanol custom molecule charges
- `custom/etoh.top` - Ethanol custom molecule topology

## Version

- Application version: `4.5.0` (defined in `quickice/__init__.py` as `__version__`)
- CLI version flag: `%(prog)s 4.5.0` in `quickice/cli/parser.py`
- GitHub Actions artifact naming: `quickice-v4.0.0-windows-x86_64.zip` (in `.github/workflows/build-windows.yml` — note: may be outdated)

---

*Stack analysis: 2026-06-08*
