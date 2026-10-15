# Technology Stack

**Analysis Date:** 2026-10-15

## Languages

**Primary:**
- Python 3.14.3 (conda-forge build `h490e9c7_101_cp314`, ABI `cp314`) — entire `quickice/` package and `tests/`. Pinned in `environment.yml` line 25.

**Secondary:**
- Bash — `setup.sh`, `QuickIce.sh`, `scripts/build-linux.sh`, `scripts/assemble-dist.sh`, `scripts/cli-examples.sh`, `scripts/run_gui_ssh.sh`, `scripts/clean-test-output.sh`, `scripts/hydrate-interface-custom-ion.sh`, `scripts/run_oc.sh`. GitHub Actions steps use `shell: bash -el {0}`.
- Windows Batch — `QuickIce.bat` (double-click launcher for the frozen Windows GUI).

## Runtime

**Environment:**
- Conda environment `quickice` (channels: `conda-forge`, `defaults`). Defined in `environment.yml`.
- Separate build environment `quickice-build` defined in `environment-build.yml` (adds `pyinstaller==6.19.0` on top of the same pinned runtime deps).
- Python 3.14.3; `python_abi=3.14=2_cp314`.

**Package Manager:**
- Conda (primary) + pip (secondary, for packages not on conda-forge). `pip=26.0.1` is itself a conda dependency; pip block in `environment.yml` lines 37-58 holds all scientific deps.
- Lockfile: **None**. `environment.yml` pins exact `==` versions per package (effectively a lockfile, but not a generated lock).
- `requirements-dev.txt` lists `pytest>=9.0.0` and `pyinstaller>=6.0` (unpinned dev tools).

**PYTHONPATH:**
- Project root must be on `PYTHONPATH` for `import quickice` to resolve. `setup.sh` exports `PYTHONPATH="${PYTHONPATH}:$(pwd)"` and appends `$(pwd)` to `PATH`. Per `AGENTS.md`, source it every new shell. The CI workflow sets the same variable manually (`.github/workflows/build-windows.yml` line 26).

## Frameworks

**Core:**
- PySide6 6.10.2 — Qt6 GUI framework (conda). Top-level imports in `quickice/gui/*.py` panels/viewers/workers (fine: those modules only load on the GUI path). The CLI/entry path checks availability WITHOUT importing via `importlib.util.find_spec('PySide6')` in `quickice/entry.py::_is_pyside6_available()` (line 26).
- VTK 9.5.2 — 3D molecular visualization (conda). All VTK imports are **lazy or guarded** (slow-gui-startup fix, resolved — see `.planning/debug/resolved/slow-gui-startup.md`):
  - `quickice/gui/vtk_utils.py` — heavy `vtkmodules.all`/`scipy.spatial` imports live INSIDE function bodies; module top level only imports numpy + `TYPE_CHECKING` blocks. Hosts `is_vtk_available()` env detection (no VTK import), cached in `_vtk_available_cache`.
  - Viewer modules (`quickice/gui/view.py` line 25, `solute_viewer.py`, `ion_viewer.py`, `hydrate_viewer.py`, `custom_molecule_viewer.py`, `interface_panel.py` line 34) import VTK-dependent modules ONLY inside `if is_vtk_available():` guards.
  - Renderer modules (`hydrate_renderer.py`, `ion_renderer.py`, `solute_renderer.py`, `custom_molecule_renderer.py`) keep top-level `from vtkmodules.all import ...` but are imported lazily INSIDE viewer render methods (e.g. `solute_viewer.py` line 421, `hydrate_viewer.py` line 250, `ion_viewer.py` line 413, `custom_molecule_viewer.py` line 489).
  - `quickice/gui/dual_viewer.py`, `molecular_viewer.py`, `interface_viewer.py` import `vtkmodules` at top level but are only imported under the same guard.
  - `quickice/gui/export.py` — `matplotlib.figure` only under `TYPE_CHECKING` (line 19); VTK imported inside `capture_viewport` (line 908).
- GenIce2 2.2.13.1 + genice-core 1.4.3 — clathrate-hydrate / ice lattice generation (pip). Three consumption styles:
  - Top-level (but on-demand) in `quickice/structure_generation/generator.py` lines 11-12 (`from genice2.plugin import safe_import`, `from genice2.genice import GenIce`) — reach-able only via the PEP 562 lazy re-export in `quickice/structure_generation/__init__.py` ("IceStructureGenerator", "generator").
  - Lazy + thread-safe singleton in `quickice/structure_generation/hydrate_generator.py::_ensure_genice_import()` (guarded by `_genice_lock = threading.Lock()` at line 40; imports `genice2.genice`, `genice2.formats.gromacs`, `genice2.lattices.{sI,sII,sH,c0te,c1te,c2te,ice1hte,sTprime}`, `genice2.molecules.tip4p`).
  - Function-body imports in `quickice/structure_generation/custom_guest_bridge.py` line 131 (`from genice2.plugin import audit_name`) and `hydrate_generator.py` line 254-256 (`genice2.genice.GenIce`, `genice2.plugin.safe_import`, `genice2.valueparser.parse_guest`).
- argparse — CLI argument parsing (stdlib). `quickice/cli/parser.py::create_parser()`; the unified router `quickice/entry.py::main()` builds a minimal argparse pre-parser (line 134). **Click is NOT used by quickice directly** (transitive dep of GenIce2).

**Testing:**
- pytest >=9.0.0 (`requirements-dev.txt`; env has pytest 9.0.2 per `__pycache__` bytecode names). Default discovery — no `pytest.ini` / `pyproject.toml`. Root `conftest.py` registers the `slow` marker (line 11); `tests/conftest.py` defines `gmx_skipif` (line 44, via `shutil.which("gmx")`), enforces `QT_QPA_PLATFORM=offscreen` at session start (line 18), and defines module-scoped GenIce2 fixtures.
- pytest-timeout 2.4.0 — **unsanctioned install** (tracked in `lib-to-add.yml`), used via `pytest --timeout=120`. SIGALRM-based only — cannot interrupt C-level hangs; use an external `timeout` guard for the full suite (per AGENTS.md).

**Build/Dev:**
- PyInstaller 6.19.0 — GUI executable packaging (`environment-build.yml`, `quickice-gui.spec`, Analysis entry `quickice/__main__.py`).
- GitHub Actions — `.github/workflows/build-windows.yml` (manual `workflow_dispatch`, `windows-latest`, builds frozen exe + 7z zip artifact).
- Dependabot — `.github/dependabot.yml` (weekly conda + pip; `open-pull-requests-limit: 0`).

## Lazy-Import Architecture (slow-gui-startup fix, resolved 2026-09-12)

GUI startup was reduced from ~1.57s warm / 4.15s cold to ~0.33s by making ALL heavy imports lazy. Importing `quickice.gui.main_window` now leaves `sys.modules` free of vtkmodules/scipy/matplotlib/genice2/networkx/iapws/shapely (in SSH-X11 envs where VTK is heuristically unavailable). Verified in `.planning/debug/resolved/slow-gui-startup.md`. Rules the codebase now enforces:

- **PEP 562 lazy re-exports:** `quickice/gui/__init__.py` and `quickice/structure_generation/__init__.py` both define module-level `__getattr__`/`__dir__` mapping names → defining submodules via `_EXPORT_TO_MODULE` dicts; submodules load on first attribute access and results are cached in `globals()`. Do NOT revert to eager imports in these two `__init__.py` files.
- **scipy deferred to first use:** function-body `from scipy.spatial import cKDTree` / `from scipy.spatial.transform import Rotation` in `quickice/structure_generation/{ion,solute,custom_molecule}_inserter.py`, `overlap_resolver.py`, plus TYPE_CHECKING-only annotations at module top. `quickice/ranking/scorer.py` (line 69) and `quickice/output/validator.py` (line 136) use the same function-body pattern.
- **matplotlib/shapely isolated in one module:** `quickice/gui/phase_diagram_canvas.py` (NEW file, split from `phase_diagram_widget.py` in the perf pass) holds the only top-level matplotlib/shapely imports (`FigureCanvasQTAgg`, `Figure`, `patches.Polygon`, `shapely.geometry`) — and is itself imported lazily. `quickice/gui/phase_diagram_widget.py::PhaseDiagramPanel` builds the canvas via `QTimer.singleShot(0)` after window show or on first `diagram_canvas` access (placeholder QLabel until then). `quickice/output/phase_diagram.py` imports matplotlib inside functions (lines 864-867).
- **AGENTS.md rule:** PySide6, VTK, GenIce2 must be imported inside function bodies in shared-core code (never at module top level in `quickice/cli/`, `quickice/structure_generation/`, `quickice/output/`).
- **Gotcha (recorded lesson):** PEP 562 module `__getattr__` does NOT fire for LOAD_GLOBAL within the same module, and function-local imports bypass `mock.patch` on module attributes — hence the sentinel+prologue cKDTree pattern in `ion_inserter.py`/`solute_inserter.py`.

## Key Dependencies

**Critical (directly imported by quickice, verified):**
- numpy 2.4.3 — array operations, pervasive. Top-level `import numpy as np` is acceptable everywhere (cheap, needed by both paths) across `quickice/structure_generation/` (types, mapper, cell_utils, overlap_resolver, water_filler, inserters, hydrate_generator, generator, gro_parser, modes/*), `quickice/phase_mapping/`, `quickice/output/`, `quickice/ranking/`, `quickice/gui/`, `quickice/utils/molecule_utils.py`.
- scipy 1.17.1 — `scipy.spatial.cKDTree` (PBC overlap checks, conditional rebuild per AGENTS.md) and `scipy.spatial.transform.Rotation` (molecule placement). All imports lazy (see Lazy-Import Architecture). `scipy.interpolate.UnivariateSpline` (lazy, with fallback) in `quickice/output/phase_diagram.py` line 221.
- genice2 2.2.13.1 / genice-core 1.4.3 — hydrate + ice lattice generation (see Frameworks).
- iapws 1.5.5 — IAPWS-95 / IAPWS97 / R10-06(2009) water & ice Ih density. `from iapws import IAPWS95` in `quickice/phase_mapping/water_density.py` (line 31); `from iapws._iapws import _Ice` in `quickice/phase_mapping/ice_ih_density.py` (line 27); `from iapws import IAPWS97` lazily inside methods in `quickice/gui/phase_diagram_canvas.py` (lines 63, 472) and `quickice/output/phase_diagram.py` (line 949). Pure-Python formulation library, **no network calls**.
- matplotlib 3.10.8 — phase diagram rendering. All usage now lazy: `quickice/gui/phase_diagram_canvas.py` (top-level here, but module loaded lazily), `quickice/gui/export.py` (TYPE_CHECKING + method-body), `quickice/output/phase_diagram.py` (method-body).
- shapely 2.1.2 — point-in-polygon phase hit-testing. `quickice/gui/phase_diagram_canvas.py` (top-level in the lazily-loaded module) and function-body imports in `quickice/output/phase_diagram.py` (lines 862, 897).

**Transitive (GenIce2 ecosystem — in `environment.yml` & collected by `quickice-gui.spec`, but NOT imported by quickice source):**
- click 8.3.1, cycless 0.7, deprecated 1.3.1, deprecation 2.1.0, graphstat 0.3.3, methodtools 0.4.7, networkx 3.6.1, openpyscad 0.5.0, pairlist 0.6.4, six 1.17.0, spglib 2.7.0, wirerope 1.0.0, wrapt 2.1.2, yaplotlib 0.1.3. (`quickice-gui.spec` line 9 collects `iapws, genice2, genice_core, matplotlib, scipy, numpy, shapely, networkx, spglib` into the frozen bundle.)

**Unsanctioned installs (tracked in `lib-to-add.yml`, NOT in `environment.yml`):**
- MDAnalysis 2.10.0 (+ 9 deps), genice2-cif 2.2.1 (+ deps incl. requests 2.34.2, jinja2), gsw 3.6.21, pytest-timeout 2.4.0, git-filter-repo 2.47.0. Installed by agents without approval; pending decision to add to `environment.yml` or remove. New deps must NEVER be auto-installed — edit `environment.yml`, seek user approval, wait for `conda env update` (per AGENTS.md).
- Note: genice2-cif pulls in `requests` — the only HTTP-client library in the env, and quickice source never imports it.

## Configuration

**Environment:**
- Conda env `quickice` created via `conda env create -f environment.yml`. Activate per shell with `source setup.sh` (runs `conda activate quickice` + sets `PYTHONPATH`/`PATH`).
- No `.env` files, no runtime config files. All configuration is via CLI args (`quickice/cli/parser.py`) or GUI controls.
- GUI display detection in `quickice/entry.py::_has_display()` (lines 42-69): checks `DISPLAY`, `WAYLAND_DISPLAY`, `QT_QPA_PLATFORM` (accepts `wayland`/`xcb`/`offscreen`) on Linux; always True on macOS/Windows. Set `QT_QPA_PLATFORM=offscreen` for headless GUI tests (enforced at session start by `tests/conftest.py` line 18).
- VTK availability heuristic in `quickice/gui/vtk_utils.py::is_vtk_available()`: if `DISPLAY` contains `'localhost'` (SSH X11 forwarding, indirect rendering), VTK is disabled unless `QUICKICE_FORCE_VTK=true`. Result cached in `_vtk_available_cache`; tests reset via `reset_vtk_available_cache()`.
- OpenGL for remote X displays: `quickice/gui/main_window.py::_configure_opengl_for_remote()` (line 2260) sets `__GLX_VENDOR_LIBRARY_NAME=mesa`.

**Build:**
- `quickice-gui.spec` — PyInstaller spec. Bundles `quickice/data` and `collect_all()` for `iapws, genice2, genice_core, matplotlib, scipy, numpy, shapely, networkx, spglib`. Excludes `*/tests/*`, `*/test/*`, `*/docs/*`, `*/__pycache__/*`, `*/.pytest_cache/*`, `*/egg-info/*`. Entry `quickice/__main__.py`; `console=True` + `hide_console='hide-early'` (same exe serves --cli and --gui).
- `environment-build.yml` — build env adding `pyinstaller==6.19.0`.
- No linter / formatter configured (no black, ruff, flake8, mypy). No `pyproject.toml`, no `setup.py`, no `setup.cfg`. Confirmed per AGENTS.md and by directory listing.
- Project-local AI-tooling config: `opencode.json` (agent model assignments + permissions; opencode-only, not consumed by app code).

**Data assets (bundled, committed):**
- `quickice/data/tip4p-ice.itp` — TIP4P-ICE water topology (referenced by `get_tip4p_itp_path()`; copied beside every exported `.top`; verification source per AGENTS.md — Abascal et al. 2005, DOI: 10.1063/1.1931662).
- `quickice/data/ch4.itp`, `ch4_hydrate.itp`, `ch4_liquid.itp`, `thf.itp`, `thf_hydrate.itp`, `thf_liquid.itp`, `tip4p.gro` — guest/water topology & coordinate templates.
- `quickice/data/custom/` (etoh.chg, etoh.gro, etoh.itp, etoh.top, test_invalid/), `quickice/data/examples/custom_positions.csv` — custom molecule samples/fixtures.
- `quickice/phase_mapping/data/ice_phases.json` — ice phase boundary data (loaded by `quickice/phase_mapping/data/ice_boundaries.py`).
- GROMACS parameter constants live in `quickice/output/_constants.py` (`TIP4P_ICE_ALPHA` line 17, `TIP4P_ICE_OW_SIGMA` line 21, `TIP4P_ICE_OW_EPSILON` line 22) and are re-exported via `quickice/output/gromacs_writer.py` (line 34). Never hardcode them (AGENTS.md).

## Platform Requirements

**Development:**
- Linux (primary dev platform) with conda. Python 3.14.3 in `quickice` env. `source setup.sh` every new shell. SSH X11 (`DISPLAY=localhost:*`) disables VTK by heuristics — set `QUICKICE_FORCE_VTK=true` to override, or expect non-VTK fallback rendering.
- GROMACS `gmx` on PATH is **optional** — required only for `@gmx_skipif`-marked tests that run `gmx grompp` validation (see `tests/conftest.py` line 44). Production code never invokes `gmx` (grep verified: no `subprocess`/`shutil.which` in `quickice/`, only a docstring mention in `hydrate_generator.py` line 244).
- Headless GUI tests need `QT_QPA_PLATFORM=offscreen`; VTK rendering may still crash in some headless environments (mock/skip per AGENTS.md ROADMAP TEST-06, deferred).
- Full suite: ~1846 tests, ~4-5 min headless — `QT_QPA_PLATFORM=offscreen timeout 900 python -m pytest -q`; ALWAYS use the external `timeout` guard (pytest-timeout cannot interrupt C-level hangs).

**Production:**
- **Desktop application** — not a service. Two distribution forms:
  - Windows frozen executable (`quickice-gui.exe`) built by `.github/workflows/build-windows.yml` → `quickice-v4.5.0-windows-x86_64.zip` artifact, launched via `QuickIce.bat`.
  - Linux from source: `python -m quickice` (CLI) or `python -m quickice --gui` (GUI); `QuickIce.sh` launches the frozen Linux build (`quickice-gui/quickice-gui --gui`).
- Entry router: `quickice/entry.py::main()` — routing priority: no-args→help; `--help`/`--version`→argparse; `--gui`→PySide6+display check then `quickice/gui/main_window.py::run_app()` (line 2287); `--cli` or pipeline flags→`quickice/main.py::main()`. Both `quickice/__main__.py` and root `quickice.py` delegate to `quickice.entry.main`. Add routing logic in `entry.py`, never in `__main__.py`/`quickice.py` (per AGENTS.md).
- Package version: `quickice/__init__.py::__version__ = "4.7.0"` (CI zip is still named `v4.5.0` — binary build predates the version bump).

---

*Stack analysis: 2026-10-15*
