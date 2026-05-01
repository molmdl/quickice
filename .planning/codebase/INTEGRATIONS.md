# External Integrations

**Analysis Date:** 2026-05-02

## APIs & External Services

**No external APIs or web services.**

QuickIce is a fully offline desktop application. All calculations are performed locally without network requests.

## Scientific Libraries (Internal Integrations)

**IAPWS (International Association for the Properties of Water and Steam):**
- Package: `iapws` 1.5.5
- Purpose: Validated water and ice thermodynamic properties
- Usage locations:
  - `quickice/phase_mapping/ice_ih_density.py` - Ice Ih density via IAPWS R10-06(2009)
  - `quickice/phase_mapping/water_density.py` - Water density via IAPWS-95 formulation
  - `quickice/phase_mapping/melting_curves.py` - IAPWS R14-08(2011) melting pressure equations
- No API keys required - pure calculation library

**GenIce2:**
- Package: `genice2` 2.2.13.1, `genice-core` 1.4.3
- Purpose: Ice crystal structure generation with hydrogen bond network disorder
- Usage locations:
  - `quickice/structure_generation/generator.py` - Ice structure generation via GenIce API
  - `quickice/structure_generation/hydrate_generator.py` - Hydrate structure generation
- Integration pattern: Plugin-based lattice loading via `safe_import()`
- Supported lattices: ice_ih, ice_ic, ice_ii, ice_iii, ice_v, ice_vi, ice_vii, ice_viii, sI, sII, sH

**spglib:**
- Package: `spglib` 2.7.0
- Purpose: Crystal symmetry analysis and space group detection
- Usage: Validation of generated structures
- No API keys required - pure calculation library

## Data Storage

**Databases:**
- None. QuickIce is stateless and does not persist data between sessions.

**File Storage:**
- Local filesystem only
- Output directory: `output/` (default) or user-specified path
- Sample data: `sample_output/` for demonstration
- Static data files: `quickice/data/` (force field parameters)

**Caching:**
- In-memory LRU cache via `@lru_cache(maxsize=256)` in:
  - `quickice/phase_mapping/ice_ih_density.py` - Cached density calculations
  - `quickice/phase_mapping/water_density.py` - Cached water density calculations
- No persistent cache files

## Authentication & Identity

**Auth Provider:**
- None. QuickIce is a standalone desktop application without user authentication.

## Monitoring & Observability

**Error Tracking:**
- None. Errors are logged to console/stderr.

**Logs:**
- Console output via `print()` statements
- No structured logging framework
- No log file persistence

## CI/CD & Deployment

**Hosting:**
- Source: GitHub repository (version control only)
- Distributable: Standalone executables (Windows, Linux)

**CI Pipeline:**
- GitHub Actions
  - Workflow: `.github/workflows/build-windows.yml`
  - Trigger: Manual (workflow_dispatch)
  - Runner: windows-latest
  - Build tool: PyInstaller 6.19.0
  - Artifact: Windows executable ZIP archive

**Dependabot:**
- Configuration: `.github/dependabot.yml`
- Ecosystems: conda, pip
- Schedule: Weekly
- Open PRs limit: 0 (monitoring only, no auto-PRs)

**Build Scripts:**
- `scripts/build-linux.sh` - Linux executable build
- `scripts/assemble-dist.sh` - Distribution assembly
- `quickice-gui.spec` - PyInstaller configuration

## Environment Configuration

**Required env vars:**
- `PYTHONPATH` - Must include project root for `quickice` package imports
- Set via `source setup.sh` which exports:
  ```bash
  export PYTHONPATH="${PYTHONPATH}:$(pwd)"
  ```

**Conda activation:**
- `conda activate quickice` required before running
- Handled by `setup.sh`

**Secrets location:**
- None. No secrets or credentials required.

## Webhooks & Callbacks

**Incoming:**
- None. QuickIce does not accept incoming network connections.

**Outgoing:**
- None. QuickIce does not make outgoing network requests.

## File Format Integrations

**Input Formats:**
- None (QuickIce generates structures from parameters, not from input files)
- GRO format parsing: `quickice/structure_generation/gro_parser.py` (for internal template loading)

**Output Formats:**
- PDB - Protein Data Bank format for molecular coordinates
  - Writer: `quickice/output/pdb_writer.py`
- GRO - GROMACS coordinate format
  - Writer: `quickice/output/gromacs_writer.py`
- TOP - GROMACS topology format
  - Writer: `quickice/output/gromacs_writer.py`
- ITP - GROMACS include topology format
  - Pre-built files in `quickice/data/`:
    - `tip4p-ice.itp` - TIP4P-ICE water model parameters
    - `ch4.itp` - Methane guest molecule (GAFF2 force field)
    - `thf.itp` - THF guest molecule (GAFF2 force field)
- PNG - Phase diagram visualization
  - Generator: `quickice/output/phase_diagram.py`
  - Library: Matplotlib

**Force Field Data:**
- `quickice/data/tip4p-ice.itp` - TIP4P-ICE water model (bundled)
- `quickice/data/ch4.itp` - Methane parameters (GAFF2, bundled)
- `quickice/data/thf.itp` - THF parameters (GAFF2, bundled)
- `quickice/data/tip4p.gro` - Water template for interface generation

## External Software Integration

**GROMACS:**
- Integration type: Export format only
- QuickIce generates GROMACS-compatible input files (.gro, .top, .itp)
- No direct API integration - users run GROMACS separately with generated files
- Water model: TIP4P-ICE (optimized for ice simulations)
- Ion parameters: Madrid2019 force field (bundled)

**Visualization:**
- VTK 9.5.2 - Embedded 3D viewer in GUI
- Matplotlib 3.10.8 - Phase diagram plots
- No external visualization software integration

---

*Integration audit: 2026-05-02*
