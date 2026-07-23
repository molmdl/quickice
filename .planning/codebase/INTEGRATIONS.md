# External Integrations

**Analysis Date:** 2026-07-23

## APIs & External Services

**Network APIs:**
- **None.** QuickIce is a fully offline scientific desktop/CLI tool. Verified by searching `quickice/` source for `import requests`, `import urllib`, `import http`, `import socket`, `import asyncio`, `aiohttp`, `httpx`, `sqlite`, `sqlalchemy`, `psycopg`, `mysql` — **no matches**. There are no HTTP clients, REST consumers, or remote service calls anywhere in `quickice/`.

**Scientific formulation libraries (bundled, offline — NOT network APIs):**
- **iapws 1.5.5** — pure-Python implementation of IAPWS thermodynamic standards (no network I/O). Used for water/ice density:
  - `from iapws import IAPWS95` — `quickice/phase_mapping/water_density.py` (IAPWS-95 formulation, supports supercooled water via extrapolation).
  - `from iapws._iapws import _Ice` — `quickice/phase_mapping/ice_ih_density.py` (IAPWS R10-06(2009) Ice Ih equation of state).
  - `from iapws import IAPWS97` (lazy, inside method) — `quickice/gui/phase_diagram_widget.py` lines 64, 473.
  - All wrapped with `lru_cache(maxsize=256)` and `warnings` suppression; fallback densities (e.g. `FALLBACK_DENSITY_GCM3 = 0.9167` for ice, `0.9998` for water) returned when out of range.

**External CLI tool (test-time only):**
- **GROMACS `gmx`** — molecular dynamics engine CLI. **Not invoked by production code** (grep for `subprocess`/`shutil.which` in `quickice/` returns no matches). Production only *writes* GROMACS-compatible `.gro`/`.top`/`.itp` files (see Data Storage below). The `gmx` binary is used exclusively in tests:
  - Availability marker: `gmx_skipif = pytest.mark.skipif(not shutil.which("gmx"), ...)` defined in `tests/conftest.py` line 24 (`_gmx_available()` uses `shutil.which("gmx")`).
  - Tests run `gmx grompp` to validate that exported topologies are simulation-ready (exit 0). Pattern (e.g. `tests/test_e2e_filled_ice_cli_hydrate_grompp.py` line 232, `tests/test_e2e_custom_guest_lattices_cli.py` line 259, `tests/test_e2e_gmx_validation.py`):
    ```python
    if shutil.which("gmx"):
        result = subprocess.run(["gmx", "grompp", "-f", em_mdp, "-c", gro, "-p", top, "-o", ...], capture_output=True, text=True)
        assert result.returncode == 0, f"gmx grompp failed ...:\n{result.stderr}"
    ```
  - `@gmx_skipif` skips the whole test when `gmx` is absent; the `shutil.which("gmx")` guard is a belt-and-suspenders check inside marked tests.
  - The actual "integration contract" is the **GROMACS file format** produced by `quickice/output/gromacs_writer.py`, `quickice/output/*_writer.py`, and `quickice/output/orchestrator.py` — these files must be parseable by `gmx grompp` (comb-rule=2 Lorentz-Berthelot, TIP4P-ICE params from `quickice/output/_constants.py`, `#include "tip4p-ice.itp"`).

## Data Storage

**Databases:**
- **None.** No SQL/NoSQL/document store. No ORM. All state is in-memory Python objects or files on disk.

**File Storage:**
- **Local filesystem only.** QuickIce reads input files and writes export artifacts to user-chosen paths.
- **Outputs written** (by `quickice/output/gromacs_writer.py`, `quickice/output/{ice,interface,ion,solute,custom,multi_molecule}_writer.py`, `quickice/output/pdb_writer.py`, `quickice/output/orchestrator.py`):
  - GROMACS: `*.gro` (coordinates + box), `*.top` (topology), `*.itp` (molecule topology includes — `tip4p-ice.itp` always copied beside `.top` via `get_tip4p_itp_path()`, plus guest/custom/solute/ion ITPs).
  - PDB: `*.pdb` (alternative coordinate export via `quickice/output/pdb_writer.py`).
  - CSV: positions CSV (read with a `MAX_CSV_ROWS = 10000` safety limit in `quickice/cli/pipeline.py` line 21).
- **Inputs read:**
  - User-provided custom molecule files: `--custom-gro` / `--custom-itp` (parsed by `quickice/structure_generation/gro_parser.py` and `quickice/structure_generation/itp_parser.py`).
  - Bundled data assets (committed in repo): `quickice/data/*.itp`, `quickice/data/tip4p.gro`, `quickice/phase_mapping/data/ice_phases.json` (loaded by `quickice/phase_mapping/data/ice_boundaries.py`).
- **Temp files:** tests use pytest's `tmp_path` (auto-cleaned) for export outputs; `gmx_workspace` fixture for persistent GROMACS debugging.

**Caching:**
- **In-process only — no external cache service.**
  - `functools.lru_cache(maxsize=256)` on density functions: `quickice/phase_mapping/water_density.py::ice_ih_density_kgm3`, `quickice/phase_mapping/ice_ih_density.py`.
  - GenIce2 library cached as a thread-locked singleton: `HydrateStructureGenerator._genice_lib` / `_gromacs_format` / `_lattice_modules` populated by `_ensure_genice_import()` in `quickice/structure_generation/hydrate_generator.py`, guarded by `_genice_lock = threading.Lock()` (double-checked locking).
  - cKDTree instances are conditionally rebuilt only after successful placement (per AGENTS.md) in `quickice/structure_generation/ion_inserter.py` and `quickice/structure_generation/solute_inserter.py`.

## Authentication & Identity

**Auth Provider:**
- **None.** No authentication, no user identity, no login. This is a local scientific tool with no multi-tenancy or access control.

## Monitoring & Observability

**Error Tracking:**
- **None.** No Sentry, Rollbar, Bugsnag, or other error-reporting service.

**Logs:**
- Python stdlib `logging` module — `logger = logging.getLogger(__name__)` pattern across modules (e.g. `quickice/cli/pipeline.py` line 19, `quickice/output/gromacs_writer.py` line 24, `quickice/structure_generation/hydrate_generator.py` line 12, `quickice/phase_mapping/water_density.py` line 33). Logs go to stderr by default; no centralized log aggregation, no structured logging framework.
- CLI user-facing progress: `quickice/cli/pipeline.py::report_progress()` writes `[PROGRESS] {message}` to stderr (line 30).
- Warnings: `warnings` stdlib module used to suppress noisy iapws metastable-state warnings (`quickice/phase_mapping/ice_ih_density.py`).

## CI/CD & Deployment

**Hosting:**
- **Desktop application** (not hosted as a service). Distributed two ways:
  1. Frozen Windows executable built by GitHub Actions → zip artifact (see CI Pipeline).
  2. Linux from source via conda env `quickice` + `source setup.sh`, then `python -m quickice` (CLI) or `python -m quickice --gui` (GUI).

**CI Pipeline:**
- **GitHub Actions** — `.github/workflows/build-windows.yml`:
  - Trigger: **manual only** (`workflow_dispatch`); no automated CI on push/PR.
  - Runner: `windows-latest`.
  - Steps: `conda-incubator/setup-miniconda@v3` with `environment-file: environment-build.yml` → env `quickice-build` → `pyinstaller --clean quickice-gui.spec` → copy docs/licenses (`README.md`, `README_bin.md`, `LICENSE`, `docs/`, `licenses/`) → `7z` zip as `quickice-v4.5.0-windows-x86_64.zip` → `actions/upload-artifact@v7`.
- **Dependabot** — `.github/dependabot.yml`: weekly conda + pip updates, `open-pull-requests-limit: 0` (security-only, no auto PRs).
- **No test CI** — tests run locally via `pytest` (per AGENTS.md ~1007 tests). No workflow runs the test suite.

## Environment Configuration

**Required env vars:**
- **None strictly required at runtime.** All setup is done by `source setup.sh`:
  - `PYTHONPATH` — appends project root so `import quickice` resolves (line 11).
  - `PATH` — appends project root (line 12).
- Both are convenience for the dev source tree; the frozen PyInstaller bundle does not need them.

**Optional / conditional env vars (read by code):**
- `DISPLAY` / `WAYLAND_DISPLAY` / `QT_QPA_PLATFORM` — checked by `quickice/entry.py::_has_display()` (lines 57-69) to decide whether `--gui` can launch. Set `QT_QPA_PLATFORM=offscreen` for headless GUI tests.
- `__GLX_VENDOR_LIBRARY_NAME` — set to `mesa` by `quickice/gui/main_window.py::_configure_opengl_for_remote()` for remote X displays (Mesa GLX fallback).
- `sys.frozen` — checked by `quickice/entry.py::_get_install_hint()` (line 100) to tailor the "PySide6 missing" error message for PyInstaller binaries vs source.

**Secrets location:**
- **None.** QuickIce has no secrets, API keys, tokens, or credentials. It is fully offline and unauthenticated.

## Webhooks & Callbacks

**Incoming:**
- **None.** No HTTP server, no webhook endpoints, no callback URLs.

**Outgoing:**
- **None.** No outbound webhooks, no notification services, no telemetry/analytics callbacks.

---

*Integration audit: 2026-07-23*
