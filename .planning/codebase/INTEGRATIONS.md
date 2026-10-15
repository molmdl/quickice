# External Integrations

**Analysis Date:** 2026-10-15

## APIs & External Services

**Network APIs:**
- **None.** QuickIce is a fully offline scientific desktop/CLI tool. Verified by grepping `quickice/` for `import requests|urllib|http|socket|asyncio|aiohttp|httpx|sqlite|sqlalchemy|psycopg|mysql` — no matches. No HTTP clients, REST consumers, or remote service calls anywhere in the package. (The env's only `requests` copy is a transitive dep of the unsanctioned genice2-cif install — never imported by quickice.)

**GenIce2 Python API (primary library integration):**
- **genice2 2.2.13.1 / genice-core 1.4.3** (pip, pinned in `environment.yml`) — ice & clathrate-hydrate lattice generation. Called as a Python API, never via the GenIce2 CLI.
  - Ice lattices: `quickice/structure_generation/generator.py` lines 11-12 (`from genice2.plugin import safe_import`, `from genice2.genice import GenIce`) — top-level, but only reached on demand via the PEP 562 lazy re-export in `quickice/structure_generation/__init__.py`.
  - Hydrate lattices: `quickice/structure_generation/hydrate_generator.py::_ensure_genice_import()` (line 67, guarded by `_genice_lock = threading.Lock()` line 40) — thread-safe double-checked-locking singleton loading `genice2.genice`, `genice2.formats.gromacs`, `genice2.lattices.{sI,sII,sH,c0te,c1te,c2te,ice1hte,sTprime}`, `genice2.molecules.tip4p`.
  - Guest-module plugin contract: `quickice/structure_generation/custom_guest_bridge.py` registers synthetic modules named `genice2.molecules.<guest_type>` in `sys.modules` so GenIce2's plugin loader picks up custom guests; `audit_name` imported lazily at line 131. `hydrate_generator.py` line 254-256 lazily uses `genice2.valueparser.parse_guest`.
  - Integration contract: whatever GenIce2 emits in `genice2.formats.gromacs` must be round-trippable through `quickice/structure_generation/types.py` structures and re-exportable as valid GROMACS files.
- **iapws 1.5.5** — pure-Python IAPWS thermodynamic standards (no network I/O). Water/ice density:
  - `from iapws import IAPWS95` — `quickice/phase_mapping/water_density.py` (IAPWS-95, supports supercooled water via extrapolation; `lru_cache(maxsize=256)`, fallback `FALLBACK_DENSITY_GCM3 = 0.9998`).
  - `from iapws._iapws import _Ice` — `quickice/phase_mapping/ice_ih_density.py` (IAPWS R10-06(2009) Ice Ih; `lru_cache(maxsize=256)`, fallback `0.9167` g/cm³, `warnings` suppression for metastable states).
  - `from iapws import IAPWS97` (lazy, inside methods) — `quickice/gui/phase_diagram_canvas.py` lines 63, 472 and `quickice/output/phase_diagram.py` line 949.

**VTK rendering (GUI-only, environment-gated):**
- **VTK 9.5.2** (conda) — 3D molecular visualization via `vtkmodules.all` + `vtkmodules.qt.QVTKRenderWindowInteractor`. Not an external service, but an integration surface with strict environment gating:
  - Availability heuristic: `quickice/gui/vtk_utils.py::is_vtk_available()` — returns False when `DISPLAY` contains `'localhost'` (SSH X11 indirect rendering usually crashes VTK) unless `QUICKICE_FORCE_VTK=true`; result cached in `_vtk_available_cache` (env vars don't change during process lifetime; tests use `reset_vtk_available_cache()`).
  - Every viewer guards VTK imports behind `if is_vtk_available():` (e.g. `quickice/gui/view.py` line 25, `solute_viewer.py` line 25, `interface_panel.py` line 34); renderers (`*_renderer.py`) import lazily inside render methods.
  - All VTK usage is deferred off the startup path (slow-gui-startup fix; `quickice/gui/vtk_utils.py` heavy imports are function-local only).

**Qt/PySide6 (GUI-only):**
- **PySide6 6.10.2** (conda) — GUI framework. Detected without import via `importlib.util.find_spec('PySide6')` in `quickice/entry.py::_is_pyside6_available()` (line 26) so the CLI path never loads Qt. Headless tests run under `QT_QPA_PLATFORM=offscreen` (enforced at session start by `tests/conftest.py` line 18). Remote X sessions get Mesa GLX fallback via `__GLX_VENDOR_LIBRARY_NAME=mesa` set in `quickice/gui/main_window.py::_configure_opengl_for_remote()` (line 2260).

**External CLI tool (test-time only):**
- **GROMACS `gmx`** — molecular dynamics engine CLI. **Not invoked by production code** (no `subprocess`/`shutil.which` in `quickice/`). Production only *writes* GROMACS-compatible `.gro`/`.top`/`.itp` files. The `gmx` binary is used exclusively in tests (~124 test files use `gmx_skipif`):
  - Availability marker: `gmx_skipif = pytest.mark.skipif(not shutil.which("gmx"), ...)` in `tests/conftest.py` line 44.
  - E2E Grompp validation runs through one shared helper: `run_gmx_grompp()` in `tests/e2e_export_helpers.py` (line 593) — subprocess `gmx grompp -f <em.mdp> -c <gro> -p <top> -o <tpr>` with stale-tpr cleanup, returns `(exit_code, stderr)`. MDP template: `tests/em.mdp` (`MDP_PATH` at line 397).
  - e2e grompp tests live in `tests/e2e/<feature>/` (per AGENTS.md): `tests/e2e/export_validation/test_e2e_gmx_validation.py`, `tests/e2e/export_validation/test_e2e_gmx_param_validation.py`, `tests/e2e/hydrate/test_e2e_filled_ice_cli_hydrate_grompp.py`, `tests/e2e/chains/test_e2e_builtin_cross_tab_regression.py`, `tests/e2e/hydrate/test_e2e_sH_cross_tab.py`, `tests/e2e/hydrate/test_e2e_triclinic_hydrate_export.py`, etc.
  - The actual production integration contract is the **GROMACS file format** produced by `quickice/output/gromacs_writer.py`, `quickice/output/{ice,interface,ion,solute,custom,multi_molecule}_writer.py`, `quickice/output/orchestrator.py` — outputs must pass `gmx grompp` (exit 0). Enforced conventions: comb-rule=2 Lorentz-Berthelot, TIP4P-ICE parameters from `quickice/output/_constants.py` (never hardcoded), `#include "tip4p-ice.itp"` staged beside every `.top`.

## Data Storage

**Databases:**
- **None.** No SQL/NoSQL/document store. No ORM. All state is in-memory Python objects or files on disk.

**File Storage:**
- **Local filesystem only.** QuickIce reads input files and writes export artifacts to user-chosen paths.
- **Outputs written** (by `quickice/output/gromacs_writer.py`, `quickice/output/{ice,interface,ion,solute,custom,multi_molecule}_writer.py`, `quickice/output/pdb_writer.py`, `quickice/output/orchestrator.py`):
  - GROMACS: `*.gro` (coordinates + box), `*.top` (topology), `*.itp` (molecule topology includes — `tip4p-ice.itp` always copied beside `.top` via `get_tip4p_itp_path()`, plus guest/custom/solute/ion ITPs). Moleculetype names managed by `quickice/structure_generation/moleculetype_registry.py` (guests `_H` suffix, liquid solutes `_L` — never hardcode).
  - PDB: `*.pdb` (`quickice/output/pdb_writer.py`, with CRYST1).
  - PNG: phase diagram + viewport screenshots via lazy matplotlib (`quickice/output/phase_diagram.py`, `quickice/gui/export.py::ViewportExporter.capture_viewport` line 908).
  - CSV input limit: `MAX_CSV_ROWS = 10000` in `quickice/cli/pipeline.py` line 21.
- **Inputs read:**
  - User-provided custom molecule files: `--custom-gro` / `--custom-itp` (parsed by `quickice/structure_generation/gro_parser.py` and `quickice/structure_generation/itp_parser.py`).
  - Bundled data assets (committed in repo): `quickice/data/*.itp` (tip4p-ice, ch4, thf, hydrate/liquid variants), `quickice/data/tip4p.gro`, `quickice/data/custom/` (etoh sample set), `quickice/phase_mapping/data/ice_phases.json` (loaded by `quickice/phase_mapping/data/ice_boundaries.py`).
- **Temp files:** tests use pytest's `tmp_path` (auto-cleaned) for export outputs; a persistent workspace under `tmp/e2e-gmx-validation/` for GROMACS debugging.

**Caching:**
- **In-process only — no external cache service.**
  - `functools.lru_cache(maxsize=256)` on density functions: `quickice/phase_mapping/water_density.py::water_density_kgm3`, `quickice/phase_mapping/ice_ih_density.py::ice_ih_density_kgm3`.
  - GenIce2 library cached as a thread-locked singleton: `HydrateStructureGenerator._genice_lib` / `_gromacs_format` / `_lattice_modules` populated by `_ensure_genice_import()` in `quickice/structure_generation/hydrate_generator.py`.
  - VTK availability cached after first call: `_vtk_available_cache` in `quickice/gui/vtk_utils.py` (reset only by tests via `reset_vtk_available_cache()`).
  - cKDTree instances are conditionally rebuilt only after successful placement (per AGENTS.md) in `quickice/structure_generation/ion_inserter.py` and `quickice/structure_generation/solute_inserter.py`.
  - PEP 562 lazy re-export results cached in package `globals()` (`quickice/gui/__init__.py`, `quickice/structure_generation/__init__.py`).

## Authentication & Identity

**Auth Provider:**
- **None.** No authentication, no user identity, no login. Local scientific tool; no multi-tenancy or access control.

## Monitoring & Observability

**Error Tracking:**
- **None.** No Sentry, Rollbar, Bugsnag, or other error-reporting service.

**Logs:**
- Python stdlib `logging` — `logger = logging.getLogger(__name__)` pattern (e.g. `quickice/cli/pipeline.py` line 19, `quickice/output/gromacs_writer.py` line 24, `quickice/structure_generation/hydrate_generator.py` line 12, `quickice/phase_mapping/water_density.py` line 33). Logs to stderr; no aggregation, no structured-logging framework.
- CLI progress reporting: `quickice/cli/pipeline.py::report_progress()` (line 24) writes `[PROGRESS] {message}` to stderr.
- Warnings: stdlib `warnings` module suppresses noisy iapws metastable-state warnings (`quickice/phase_mapping/ice_ih_density.py` line 64).

## CI/CD & Deployment

**Hosting:**
- **Desktop application** (not hosted as a service). Two distribution forms:
  1. Frozen Windows exe built by GitHub Actions → zip artifact (see CI Pipeline).
  2. Linux from source: conda env `quickice` + `source setup.sh`, then `python -m quickice` (CLI) or `python -m quickice --gui` (GUI).

**CI Pipeline:**
- **GitHub Actions** — `.github/workflows/build-windows.yml`:
  - Trigger: **manual only** (`workflow_dispatch`); no automated CI on push/PR.
  - Runner: `windows-latest`; `conda-incubator/setup-miniconda@v3` with `environment-build.yml` → env `quickice-build`.
  - Steps: `pyinstaller --clean quickice-gui.spec` (PYTHONPATH set inline) → copy docs/licenses (`README.md`, `README_bin.md`, `LICENSE`, `docs/`, `licenses/`) → `7z` zip as `quickice-v4.5.0-windows-x86_64.zip` → `actions/upload-artifact@v7`.
- **Dependabot** — `.github/dependabot.yml`: weekly conda + pip; `open-pull-requests-limit: 0` (security-only, no auto PRs).
- **No test CI** — the ~1846-test suite runs locally via `pytest` (~4-5 min headless with external `timeout` guard; see AGENTS.md). No workflow runs tests.

## Environment Configuration

**Required env vars:**
- **None strictly required at runtime.** `source setup.sh` sets for the dev tree:
  - `PYTHONPATH` — appends project root so `import quickice` resolves.
  - `PATH` — appends project root.
- The frozen PyInstaller bundle needs neither.

**Optional / conditional env vars (read by code):**
- `DISPLAY` / `WAYLAND_DISPLAY` / `QT_QPA_PLATFORM` — checked by `quickice/entry.py::_has_display()` (lines 42-69) to permit `--gui` launch; `QT_QPA_PLATFORM=offscreen` is required for headless GUI tests and enforced by `tests/conftest.py`.
- `QUICKICE_FORCE_VTK` — set to `true` to force VTK rendering even when `DISPLAY` contains `'localhost'` (SSH X11 heuristic in `quickice/gui/vtk_utils.py::is_vtk_available()`); user-facing messages in `view.py` (line 401) and viewer fallbacks suggest it.
- `__GLX_VENDOR_LIBRARY_NAME` — set to `mesa` by `quickice/gui/main_window.py::_configure_opengl_for_remote()` (line 2260) for remote X displays.
- `sys.frozen` — checked by `quickice/entry.py::_get_install_hint()` (line 100) to tailor the "PySide6 missing" message for PyInstaller binaries vs source.

**Secrets location:**
- **None.** QuickIce has no secrets, API keys, tokens, or credentials. Fully offline and unauthenticated.

## Webhooks & Callbacks

**Incoming:**
- **None.** No HTTP server, no webhook endpoints, no callback URLs.

**Outgoing:**
- **None.** No outbound webhooks, no notification services, no telemetry/analytics callbacks.

## Lazy-Import Strategy Impact (integration-relevant rules)

The resolved slow-gui-startup fix (see `.planning/debug/resolved/slow-gui-startup.md`) is now an integration contract for all new code:

- PySide6, VTK, matplotlib, scipy, shapely, and GenIce2 must NOT load at import time of `quickice.gui.main_window` or of any `quickice.structure_generation.*` submodule. Import cost sits ~100% on first use; startup measured at ~0.33s warm (was 1.57s).
- Package re-exports in `quickice/gui/__init__.py` and `quickice/structure_generation/__init__.py` stay PEP 562 `__getattr__`-lazy — new exports must be added to their `_EXPORT_TO_MODULE` maps, not eagerly imported.
- Any new VTK-touching module goes behind `is_vtk_available()` guards; new matplotlib/shapely GUI code belongs in (or is deferred like) `quickice/gui/phase_diagram_canvas.py` — never top-level in `phase_diagram_widget.py`.
- Known PEP 562 caveat for test authors: module `__getattr__` does not fire on same-module LOAD_GLOBAL, so `mock.patch` of lazily imported names needs the sentinel+prologue pattern used in `quickice/structure_generation/{ion,solute}_inserter.py`.

---

*Integration audit: 2026-10-15*
