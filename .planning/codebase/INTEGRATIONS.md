# External Integrations

**Analysis Date:** 2026-04-04

## APIs & External Services

**Scientific Libraries (Embedded):**

### GenIce2
- Service: Ice crystal structure generation
  - Purpose: Generates hydrogen-disordered ice structures with valid H-bond networks
  - SDK/Client: `genice2.plugin.safe_import()` + `genice2.genice.GenIce`
  - Integration: Wrapped in `quickice/structure_generation/generator.py`
  - Usage: Called with lattice name, density, supercell matrix, water model (TIP3P), formatter (GROMACS)
  - Repository: https://github.com/genice-dev/GenIce2
  - Paper: "GenIce: Hydrogen-disordered ice structures by combinatorial generation", J. Comput. Chem. 2017

### IAPWS (International Association for Properties of Water and Steam)
- Service: Validated thermophysical property equations
  - Purpose: IAPWS-95 melting curves, saturation curves, triple point data
  - SDK/Client: `iapws.IAPWS97` class
  - Integration: Used in `quickice/phase_mapping/melting_curves.py` and `quickice/output/phase_diagram.py`
  - Auth: None (scientific standard, open equations)
  - Reference: IAPWS R14-08(2011) - Melting and Sublimation Curves

### spglib
- Service: Crystal symmetry analysis
  - Purpose: Space group detection, symmetry operations
  - SDK/Client: `spglib` Python package
  - Integration: Available for structure validation

## Data Storage

**Databases:**
- None - Application is stateless

**File Storage:**
- Local filesystem only
  - Output: PDB molecular structure files
  - Output: PNG/SVG phase diagram images
  - Output: Text data files with boundary curves
  - Location: Configurable via `--output` flag (default: `output/`)

**Caching:**
- None - Each run generates fresh structures

## Authentication & Identity

**Auth Provider:**
- None - Local desktop application
  - No user accounts
  - No network authentication

## Monitoring & Observability

**Error Tracking:**
- None - Console/stderr output only

**Logs:**
- Python logging module (basic usage)
  - Configured per-module with `logging.debug()`, `logging.warning()`
  - No centralized logging infrastructure

## CI/CD & Deployment

**Hosting:**
- GitHub repository: Source distribution
- GitHub Actions: Windows executable builds
  - Workflow: `.github/workflows/build-windows.yml`
  - Trigger: Manual (workflow_dispatch)
  - Artifact: `quickice-gui-windows` (30-day retention)

**CI Pipeline:**
- GitHub Actions for Windows builds
  - Python 3.14 setup
  - Miniconda environment creation from `environment.yml`
  - PyInstaller packaging with `--windowed --onedir`
  - Artifact upload

**Release Distribution:**
- GitHub Releases (manual process)
- Standalone Windows executable with bundled dependencies

## Environment Configuration

**Required env vars:**
- `PYTHONPATH` - Must include project root for package imports
- Set via: `source setup.sh`

**Conda environment:**
- Environment name: `quickice`
- Created from: `environment.yml`

**Secrets location:**
- None - No secrets required for this application

## Webhooks & Callbacks

**Incoming:**
- None - Desktop application

**Outgoing:**
- None - Desktop application

## Plugin Architecture

**GenIce Plugin System:**
- GenIce2 uses a plugin architecture for lattices, water models, and formatters
- QuickIce imports plugins dynamically:
  ```python
  lattice = safe_import("lattice", "ice_ih").Lattice()
  water = safe_import("molecule", "tip3p").Molecule()
  formatter = safe_import("format", "gromacs").Format()
  ```
- Available lattices: ice_ih, ice_ic, ice_ii, ice_iii, ice_v, ice_vi, ice_vii, ice_viii, ice_ix, ice_xi, ice_xv

## Third-Party Licenses

**Bundled in `licenses/` directory:**
- VTK license
- Qt/PySide6 license
- Other dependency licenses (for distribution compliance)

---

*Integration audit: 2026-04-04*
