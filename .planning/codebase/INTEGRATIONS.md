# External Integrations

**Analysis Date:** 2026-04-07

## APIs & External Services

**None** - QuickIce is a fully local desktop application with no external API calls.

## Data Storage

**Databases:**
- None - No database connections

**File Storage:**
- Local filesystem only
- Output directory configurable via `--output` CLI flag (default: `output/`)
- Bundled data files in `quickice/data/`:
  - `tip4p-ice.itp` - GROMACS TIP4P-ICE water model topology
  - `tip4p.gro` - Reference TIP4P structure

**Caching:**
- None - All computation is performed on-demand

## Third-Party Libraries (Local Integration)

**IAPWS (iapws 1.5.5):**
- Purpose: Water/steam thermodynamic properties
- Usage: Liquid water region calculation in phase diagrams
- Location: `quickice/output/phase_diagram.py`, `quickice/gui/phase_diagram_widget.py`
- Import: `from iapws import IAPWS97`
- No external network calls - uses local IAPWS equations

**GenIce2 (genice2 2.2.13.1):**
- Purpose: Ice crystal structure generation
- Usage: Generate ice polymorph lattices with hydrogen bond networks
- Location: `quickice/structure_generation/generator.py`
- Imports:
  - `from genice2.plugin import safe_import`
  - `from genice2.genice import GenIce`
- Supported phases: Ih, Ic, II, III, V, VI, VII, VIII
- Water models: TIP4P (4-point water with massless virtual site)
- Formatters: GROMACS format output
- No external network calls - pure local computation

## Authentication & Identity

**Auth Provider:**
- None - No authentication required (local desktop application)

## Monitoring & Observability

**Error Tracking:**
- None - Errors printed to stderr/console

**Logs:**
- Console output (print statements)
- No structured logging framework

## CI/CD & Deployment

**Hosting:**
- N/A - Desktop application

**CI Pipeline:**
- GitHub Actions (manual trigger only)
- Workflow: `.github/workflows/build-windows.yml`
- Trigger: `workflow_dispatch` (manual)
- Steps:
  1. Checkout code
  2. Setup Miniconda with `environment-build.yml`
  3. Build executable with PyInstaller
  4. Package documentation and licenses
  5. Create ZIP artifact
- Artifact: `quickice-v2.0.0-windows-x86_64.zip`

**Dependency Updates:**
- Dependabot: Weekly conda/pip updates
- Auto-merge: Disabled (`open-pull-requests-limit: 0`)

## Environment Configuration

**Required env vars:**
- None - No environment variables required for core functionality

**Optional env vars:**
- `DISPLAY` - X11 display (checked for VTK availability)
- `QUICKICE_FORCE_VTK` - Force VTK usage in headless environments

**Secrets location:**
- None - No secrets or credentials

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Molecular Simulation Integration

**GROMACS Compatibility:**
- Output formats: `.gro` (coordinates), `.top` (topology), `.itp` (molecule definition)
- Water model: TIP4P-ICE (4-point water model for ice simulations)
- Force field: Amber-compatible defaults
- Location: `quickice/output/gromacs_writer.py`

**PDB Format:**
- Standard Protein Data Bank format
- Location: `quickice/output/pdb_writer.py`

## Data Files (Bundled)

**Phase Mapping Data:**
- `quickice/phase_mapping/data/ice_phases.json` - Phase metadata
- `quickice/phase_mapping/ice_boundaries.py` - Solid-solid boundary data (embedded)

**Molecular Data:**
- `quickice/data/tip4p-ice.itp` - GROMACS TIP4P-ICE topology
- `quickice/data/tip4p.gro` - Reference structure

## Scientific Standards Used

**IAPWS Standards (local implementation):**
- IAPWS R14-08(2011) - Melting curves for ice phases
- IAPWS R10-06(2009) - Equation of state for Ice Ih
- Location: `quickice/phase_mapping/melting_curves.py`

**Triple Point Data:**
- Embedded in code: `quickice/phase_mapping/triple_points.py`
- Source: IAPWS and scientific literature

---

*Integration audit: 2026-04-07*
