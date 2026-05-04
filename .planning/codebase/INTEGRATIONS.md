# External Integrations

**Analysis Date:** 2026-05-05

## APIs & External Services

**None Detected**

QuickIce is a desktop application with no external API integrations. All functionality is self-contained:

- No HTTP requests (no `requests`, `httpx`, `aiohttp`, or `urllib` imports)
- No cloud services
- No external microservices
- No API keys or authentication tokens

## Data Storage

**Databases:**
- None

**File Storage:**
- Local filesystem only
- Output directory: `output/` (configurable via `--output` flag)
- Sample data: `sample_output/`, `quickice/data/`
- Build artifacts: `build/`, `dist/`

**Caching:**
- None (stateless operations)

## Authentication & Identity

**Auth Provider:**
- None required (desktop application)

**Implementation:**
- No authentication
- No user identity management
- No access control

## Monitoring & Observability

**Error Tracking:**
- None

**Logs:**
- Console output via `print()` statements
- No structured logging framework
- No log file persistence

## CI/CD & Deployment

**Hosting:**
- GitHub repository (source code hosting)
- No runtime hosting (desktop application)

**CI Pipeline:**
- GitHub Actions (`.github/workflows/build-windows.yml`)
  - Trigger: Manual (`workflow_dispatch`)
  - Platform: `windows-latest`
  - Steps:
    1. Checkout code
    2. Setup Miniconda with `environment-build.yml`
    3. Build executable with PyInstaller
    4. Package distribution with documentation
    5. Upload artifact: `quickice-v4.0.0-windows-x86_64.zip`

**Dependency Management:**
- GitHub Dependabot (`.github/dependabot.yml`)
  - Conda ecosystem: weekly updates
  - Pip ecosystem: weekly updates
  - Pull request limit: 0 (security updates only)

## Environment Configuration

**Required env vars:**
- None required for core functionality

**Optional env vars:**
- `DISPLAY` - X11 display for GUI (Linux)
- `QUICKICE_FORCE_VTK` - Override VTK availability check (set to 'true')
- `__GLX_VENDOR_LIBRARY_NAME` - Force software rendering (set to 'mesa')

**Secrets location:**
- None (no secrets in codebase)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Third-Party Libraries (Key Integrations)

**GenIce2 Integration:**
- Purpose: Ice crystal structure generation
- Usage: Core engine for generating ice polymorph structures
- Entry points:
  - `quickice/structure_generation/generator.py` - Ice structure generation
  - `quickice/structure_generation/hydrate_generator.py` - Hydrate structure generation
- Supported lattices: Ice Ih, Ic, II, III, V, VI, VII, VIII, XI, IX, XV, X
- Supported hydrates: sI, sII, sH

**IAPWS Integration:**
- Purpose: Water and ice thermophysical properties
- Usage: Phase boundary calculations and density predictions
- Entry points:
  - `quickice/phase_mapping/water_density.py` - Water density via IAPWS95
  - `quickice/phase_mapping/ice_ih_density.py` - Ice Ih density via IAPWS R10-06(2009)
  - `quickice/phase_mapping/melting_curves.py` - IAPWS R14-08(2011) melting curves
  - `quickice/output/phase_diagram.py` - Phase diagram plotting (IAPWS97)
  - `quickice/gui/phase_diagram_widget.py` - GUI phase diagram (IAPWS97)

**VTK Integration:**
- Purpose: 3D molecular visualization in GUI
- Usage: Interactive 3D rendering of ice structures
- Entry points:
  - `quickice/gui/molecular_viewer.py` - Base viewer
  - `quickice/gui/interface_viewer.py` - Interface visualization
  - `quickice/gui/hydrate_viewer.py` - Hydrate visualization
  - `quickice/gui/ion_viewer.py` - Ion visualization
  - `quickice/gui/vtk_utils.py` - VTK utilities
- Qt integration: `vtkmodules.qt.QVTKRenderWindowInteractor`

**Matplotlib Integration:**
- Purpose: Phase diagram plotting and figure generation
- Usage: 2D plots for phase diagrams
- Entry points:
  - `quickice/output/phase_diagram.py` - Phase diagram generation
  - `quickice/gui/phase_diagram_widget.py` - Embedded GUI plots
  - `quickice/gui/export.py` - Figure export
- Qt integration: `matplotlib.backends.backend_qtagg.FigureCanvasQTAgg`

**PySide6 Integration:**
- Purpose: Qt6 GUI framework
- Usage: Desktop GUI application
- Entry points:
  - `quickice/gui/main_window.py` - Main application window
  - `quickice/gui/view.py` - Main view (MVVM pattern)
  - `quickice/gui/viewmodel.py` - View model (MVVM pattern)
  - All GUI panels and widgets

## Data File Dependencies

**Bundled Data Files:**
- `quickice/data/tip4p.gro` - TIP4P water structure template (59KB)
- `quickice/data/tip4p-ice.itp` - GROMACS topology for TIP4P ice
- `quickice/data/ch4.itp` - Methane topology for hydrates
- `quickice/data/thf.itp` - THF topology for hydrates

**Output Formats:**
- PDB files - Molecular structure visualization
- GROMACS files (`.gro`, `.top`, `.itp`) - MD simulation input
- Phase diagram PNG - Visual phase mapping

---

*Integration audit: 2026-05-05*
