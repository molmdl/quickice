# Technology Stack

**Analysis Date:** 2026-07-23

## Languages

**Primary:**
- Python 3.14.3 (conda-forge build `h490e9c7_101_cp314`, ABI `cp314`) — entire `quickice/` package and `tests/`. Pinned in `environment.yml` line 25.

**Secondary:**
- Bash — `setup.sh`, `QuickIce.sh`, `scripts/build-linux.sh`, `scripts/assemble-dist.sh`, `scripts/cli-examples.sh`, `scripts/run_gui_ssh.sh`, `scripts/clean-test-output.sh`. GitHub Actions step in `.github/workflows/build-windows.yml` uses `shell: bash -el {0}`.
- Windows Batch — `QuickIce.bat` (double-click launcher for the frozen Windows GUI).

## Runtime

**Environment:**
- Conda environment `quickice` (channels: `conda-forge`, `defaults`). Defined in `environment.yml`.
- Separate build environment `quickice-build` defined in `environment-build.yml` (adds `pyinstaller==6.19.0`).
- Python 3.14.3; `python_abi=3.14=2_cp314`.

**Package Manager:**
- Conda (primary) + pip (secondary, for packages not on conda-forge). `pip=26.0.1` is itself a conda dependency; pip block in `environment.yml` lines 37-57 holds all scientific deps.
- Lockfile: **None**. `environment.yml` pins exact `==` versions per package (effectively a lockfile, but not a generated lock).
- `requirements-dev.txt` lists `pytest>=9.0.0` and `pyinstaller>=6.0` (unpinned dev tools).

**PYTHONPATH:**
- Project root must be on `PYTHONPATH` for `import quickice` to resolve. `setup.sh` exports `PYTHONPATH="${PYTHONPATH}:$(pwd)"` and appends `$(pwd)` to `PATH`. Per AGENTS.md this must be sourced every new shell.

## Frameworks

**Core:**
- PySide6 6.10.2 — Qt6 GUI framework (conda). Used only in `quickice/gui/`. Top-level imports in all `quickice/gui/*.py` panels/viewers/workers; availability checked without importing via `importlib.util.find_spec('PySide6')` in `quickice/entry.py` (`_is_pyside6_available()`).
- VTK 9.5.2 — 3D molecular visualization (conda). Imported via `from vtkmodules.all import ...` and `from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor` in `quickice/gui/*_viewer.py`, `quickice/gui/*_renderer.py`, `quickice/gui/vtk_utils.py`, `quickice/gui/export.py`, `quickice/gui/dual_viewer.py`. Some VTK imports are deferred inside methods (e.g. `vtkMolecule`, `vtkMoleculeMapper` in `quickice/gui/solute_viewer.py` lines 253/306, `quickice/gui/ion_viewer.py` lines 314/367).
- GenIce2 2.2.13.1 + genice-core 1.4.3 — clathrate-hydrate / ice lattice generation (pip). Top-level in `quickice/structure_generation/generator.py` (`from genice2.plugin import safe_import`, `from genice2.genice import GenIce`). Lazy + thread-safe singleton in `quickice/structure_generation/hydrate_generator.py` (`_ensure_genice_import()` guarded by `_genice_lock = threading.Lock()`, imports `genice2.genice`, `genice2.formats.gromacs`, `genice2.lattices.{sI,sII,sH,c0te,c1te,c2te,ice1hte,sTprime}`, `genice2.molecules.tip4p`). Also used in `quickice/structure_generation/custom_guest_bridge.py` (`genice2.plugin.audit_name`).
- argparse — CLI argument parsing (stdlib). `quickice/cli/parser.py::create_parser()`; the unified router `quickice/entry.py::main()` also builds a minimal argparse pre-parser. **Click is NOT used by quickice directly** (it is a transitive dep of GenIce2).

**Testing:**
- pytest >=9.0.0 (`requirements-dev.txt`). Default discovery — no `pytest.ini` / `pyproject.toml`. Root `conftest.py` registers the `slow` marker; `tests/conftest.py` defines `gmx_skipif` (skips when `gmx` not on PATH) and module-scoped GenIce2 fixtures.
- pytest-timeout 2.4.0 — present in env (per `lib-to-add.yml`), used via `pytest --timeout=120`.

**Build/Dev:**
- PyInstaller 6.19.0 — GUI executable packaging (`environment-build.yml`, `quickice-gui.spec`, Analysis entry `quickice/__main__.py`).
- GitHub Actions — `.github/workflows/build-windows.yml` (manual `workflow_dispatch`, `windows-latest`, builds frozen exe + 7z zip artifact).
- Dependabot — `.github/dependabot.yml` (weekly conda + pip; `open-pull-requests-limit: 0`).

## Key Dependencies

**Critical (directly imported by quickice, verified):**
- numpy 2.4.3 — array operations, pervasive. Top-level `import numpy as np` across `quickice/structure_generation/` (types, mapper, cell_utils, overlap_resolver, water_filler, ion_inserter, solute_inserter, custom_molecule_inserter, hydrate_generator, generator, gro_parser, modes/*), `quickice/ranking/scorer.py`, `quickice/output/...`, `quickice/gui/...`, `quickice/utils/molecule_utils.py`.
- scipy 1.17.1 — `scipy.spatial.cKDTree` (PBC overlap checks, conditional rebuild per AGENTS.md) and `scipy.spatial.transform.Rotation`. Used in `quickice/structure_generation/overlap_resolver.py`, `quickice/structure_generation/ion_inserter.py`, `quickice/structure_generation/solute_inserter.py`, `quickice/structure_generation/custom_molecule_inserter.py`, `quickice/ranking/scorer.py`, `quickice/gui/vtk_utils.py`.
- genice2 2.2.13.1 / genice-core 1.4.3 — hydrate + ice lattice generation (see Frameworks).
- iapws 1.5.5 — IAPWS-95 / IAPWS97 / R10-06(2009) water & ice Ih density. `from iapws import IAPWS95` in `quickice/phase_mapping/water_density.py`; `from iapws._iapws import _Ice` in `quickice/phase_mapping/ice_ih_density.py`; `from iapws import IAPWS97` (lazy) in `quickice/gui/phase_diagram_widget.py`. Pure-Python formulation library, **no network calls**.
- matplotlib 3.10.8 — phase diagram. `FigureCanvasQTAgg`, `Figure`, `Polygon` in `quickice/gui/phase_diagram_widget.py`; `from matplotlib.figure import Figure` in `quickice/gui/export.py`.
- shapely 2.1.2 — point-in-polygon phase hit-testing. `from shapely.geometry import Point, Polygon as ShapelyPolygon` in `quickice/gui/phase_diagram_widget.py`.

**Transitive (GenIce2 ecosystem — in `environment.yml` & collected by `quickice-gui.spec`, but NOT imported by quickice source):**
- click 8.3.1, cycless 0.7, deprecated 1.3.1, deprecation 2.1.0, graphstat 0.3.3, methodtools 0.4.7, networkx 3.6.1, openpyscad 0.5.0, pairlist 0.6.4, six 1.17.0, spglib 2.7.0, wirerope 1.0.0, wrapt 2.1.2, yaplotlib 0.1.3. (`quickice-gui.spec` line 9 collects `iapws, genice2, genice_core, matplotlib, scipy, numpy, shapely, networkx, spglib` into the frozen bundle.)

**Unsanctioned installs (tracked in `lib-to-add.yml`, NOT in `environment.yml`):**
- MDAnalysis 2.10.0, genice2-cif 2.2.1, gsw 3.6.21, pytest-timeout 2.4.0, git-filter-repo 2.47.0. Installed by agents without approval; pending decision to add to `environment.yml` or remove.

## Configuration

**Environment:**
- Conda env `quickice` created via `conda env create -f environment.yml`. Activate per shell with `source setup.sh` (runs `conda activate quickice` + sets `PYTHONPATH`/`PATH`).
- No `.env` files, no runtime config files. All configuration is via CLI args (`quickice/cli/parser.py`) or GUI controls.
- GUI display detection in `quickice/entry.py::_has_display()`: checks `DISPLAY`, `WAYLAND_DISPLAY`, `QT_QPA_PLATFORM` on Linux; always True on macOS/Windows. Set `QT_QPA_PLATFORM=offscreen` for headless GUI tests (per AGENTS.md).
- OpenGL for remote X displays: `quickice/gui/main_window.py::_configure_opengl_for_remote()` sets `__GLX_VENDOR_LIBRARY_NAME=mesa`.

**Build:**
- `quickice-gui.spec` — PyInstaller spec. Bundles `quickice/data` and `collect_all()` for `iapws, genice2, genice_core, matplotlib, scipy, numpy, shapely, networkx, spglib`. Excludes `*/tests/*`, `*/docs/*`, `*/__pycache__/*`, `*/.pytest_cache/*`.
- `environment-build.yml` — build env adding `pyinstaller==6.19.0`.
- No linter / formatter configured (no black, ruff, flake8, mypy). No `pyproject.toml`, no `setup.py`, no `setup.cfg`. Confirmed per AGENTS.md and by directory listing.

**Data assets (bundled, committed):**
- `quickice/data/tip4p-ice.itp` — TIP4P-ICE water topology (referenced by `get_tip4p_itp_path()` in `quickice/output/gromacs_writer.py` / `quickice/cli/itp_helpers.py`, copied beside every exported `.top`).
- `quickice/data/ch4.itp`, `ch4_hydrate.itp`, `ch4_liquid.itp`, `thf.itp`, `thf_hydrate.itp`, `thf_liquid.itp`, `tip4p.gro` — guest/water topology & coordinate templates.
- `quickice/data/custom/`, `quickice/data/examples/custom_positions.csv` — custom molecule samples.
- `quickice/phase_mapping/data/ice_phases.json` — ice phase boundary data (loaded by `quickice/phase_mapping/data/ice_boundaries.py`).

## Platform Requirements

**Development:**
- Linux (primary dev platform) with conda. Python 3.14.3 in `quickice` env. `source setup.sh` every new shell.
- GROMACS `gmx` on PATH is **optional** — required only for `@gmx_skipif`-marked tests that run `gmx grompp` validation (see `tests/conftest.py` line 24). Production code never invokes `gmx`.
- Headless GUI tests need `QT_QPA_PLATFORM=offscreen`; VTK rendering may still crash in some headless environments (mock/skip per AGENTS.md ROADMAP TEST-06).

**Production:**
- **Desktop application** — not a service. Two distribution forms:
  - Windows frozen executable (`quickice-gui.exe`) built by `.github/workflows/build-windows.yml` → `quickice-v4.5.0-windows-x86_64.zip` artifact, launched via `QuickIce.bat` (`%SCRIPT_DIR%\quickice-gui\quickice-gui.exe --gui`).
  - Linux from source: `python -m quickice` (CLI) or `python -m quickice --gui` (GUI); `QuickIce.sh` launches the frozen Linux build (`quickice-gui/quickice-gui --gui`).
- Entry router: `quickice/entry.py::main()` — routing priority: no-args→help; `--help`/`--version`→argparse; `--gui`→PySide6+display check then `quickice/gui/main_window.py::run_app()`; `--cli` or pipeline flags→`quickice/main.py::main()`. Both `quickice/__main__.py` and root `quickice.py` delegate to `quickice.entry.main`.
- Package version: `quickice/__init__.py::__version__ = "4.7.0"` (CI zip is still named `v4.5.0` — binary build predates the version bump).

---

*Stack analysis: 2026-07-23*
