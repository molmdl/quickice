# Portable Distribution / PyInstaller Analysis — QuickIce

**Task:** D — READ-ONLY portable distribution / PyInstaller analysis
**Analysis Date:** 2026-07-23
**Working Directory:** `/share/home/nglokwan/quickice`
**Status:** READ-ONLY. Bias-free (no prior scancode/verification results consulted). Nothing was executed — no `pyinstaller`, no build, no conda changes. Conclusions are formed from reading the spec, scripts, `environment.yml`, and `quickice/` source imports only.
**Scope:** Identify the libraries that must be packaged into a portable distribution, and suggest concrete changes to `quickice-gui.spec` (and the build scripts) to reduce bundled size. All code snippets are **SUGGESTED — NOT APPLIED**.

---

## 1. Current packaging setup

### 1.1 PyInstaller spec — `quickice-gui.spec`

Full file: `quickice-gui.spec` (59 lines). Section-by-section:

- **`datas` (line 5):** Initialized to `[('quickice/data', 'quickice/data')]` — bundles the entire `quickice/data/` tree verbatim into `_internal/quickice/data/`.
- **`binaries` (line 6):** Starts empty `[]`; populated by the `collect_all` loop.
- **`hiddenimports` (line 7):** Starts empty `[]`; populated by the `collect_all` loop.
- **`collect_all` loop (lines 9–16):** Iterates over `['iapws', 'genice2', 'genice_core', 'matplotlib', 'scipy', 'numpy', 'shapely', 'networkx', 'spglib']` and, for each, calls `PyInstaller.utils.hooks.collect_all(pkg)`, merging `[datas, binaries, hiddenimports]`. Failures are swallowed with a warning print.
  - **Notable OMISSIONS from this list:** `PySide6` and `vtk`/`vtkmodules` are **NOT** in the `collect_all` list. They are pulled in only via PyInstaller's built-in hooks (`hook-PySide6.py`, `hook-vtkmodules.py`) when they appear in the import graph (see §5).
- **`Analysis` (lines 18–30):**
  - Entry script: `['quickice/__main__.py']`.
  - `pathex=[]`, `hookspath=[]`, `hooksconfig={}` — no custom hooks.
  - `runtime_hooks=[]` — no runtime hooks (no early `sys.path`/`_MEIPASS` patching; relevant to the data-file resolution risk in §7).
  - `excludes=['*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*', '*/.pytest_cache/*', '*/egg-info/*']` — glob-style path patterns. These target test/doc/cache directories inside collected packages.
  - `noarchive=False`, `optimize=0` — modules go into the PYZ archive; no bytecode optimization.
- **`PYZ` (line 31):** `PYZ(a.pure)` — standard compressed archive of pure-Python modules.
- **`EXE` (lines 33–50):** `name='quickice-gui'`; `exclude_binaries=True` (onedir — binaries go to COLLECT, not into the EXE); `strip=False` (debug symbols **kept** — size opportunity, §4.1); `upx=True` (UPX compression enabled); `console=True` with `hide_console='hide-late'` (console shows during startup, then hides — useful for diagnosing launch failures); `debug=False`; `argv_emulation=False`.
- **`COLLECT` (lines 51–59):** `name='quickice-gui'`; `strip=False`; `upx=True`; `upx_exclude=[]` (nothing excluded from UPX). This is the **onedir** layout — produces `dist/quickice-gui/quickice-gui` (exe) + `dist/quickice-gui/_internal/` (libs/data).

### 1.2 Build script — `scripts/build-linux.sh`

51 lines. Responsibilities:
- Verifies `CONDA_DEFAULT_ENV == quickice` (exits if not).
- Verifies `pyinstaller` is on PATH (else points to `requirements-dev.txt`).
- `rm -rf build/ dist/` (clean).
- Runs `pyinstaller --clean quickice-gui.spec`.
- Verifies `dist/quickice-gui/quickice-gui` exists and prints `du -sh dist/quickice-gui/`.
- **Does NOT** pass any `--exclude-module` flags (relies entirely on the spec's `excludes`). **Does NOT** strip, prune datas, or post-clean `_internal/`. **Does NOT** smoke-test the GUI or a CLI export — only checks the executable bit exists (so a broken GUI would not be caught here).

### 1.3 Assembly script — `scripts/assemble-dist.sh`

19 lines. Called as `assemble-dist.sh <version>`. Responsibilities:
- `cd dist/`, removes prior `quickice-<version>-linux-x86_64.tar.gz`.
- Builds a `package/` staging dir: copies `dist/quickice-gui/` (the onedir bundle), plus `QuickIce.sh` (launcher), `README.md`, `README_bin.md`, `LICENSE`, `docs/{gui-guide.md,principles.md,ranking.md,images/}`, and `licenses/*.txt`.
- `tar -czf` the package and removes staging.
- **Does NOT** prune `_internal/` before tarring (any test fixtures / `.bak` files bundled by the spec are shipped as-is). A post-build prune hook could be added here (§4.6).

### 1.4 Environment — `environment.yml`

Conda env `quickice`, Python `3.14.3` (line 25). Key conda libs: `pyside6=6.10.2` (line 35), `vtk=9.5.2` (line 36). Pip section (lines 37–57) pins: `click`, `cycless`, `deprecated`, `deprecation`, `genice-core==1.4.3` (import name `genice_core`), `genice2==2.2.13.1`, `graphstat`, `iapws==1.5.5`, `methodtools`, `matplotlib==3.10.8`, `networkx==3.6.1`, `numpy==2.4.3`, `openpyscad`, `pairlist`, `scipy==1.17.1`, `shapely==2.1.2`, `six`, `spglib==2.7.0`, `wirerope`, `wrapt`, `yaplotlib`. Dev deps (`requirements-dev.txt`): `pytest>=9.0.0`, `pyinstaller>=6.0` (NOT in `environment.yml`; must NOT be bundled).

---

## 2. Required libs (runtime import analysis)

Import analysis was performed by grepping `quickice/` for `import`/`from` statements. "Top-level" = module-top import; "lazy" = inside a function/method body (PyInstaller's static AST analysis still detects plain `from X import Y` lazy statements, but `importlib`/`find_spec`/generated-code loading is NOT statically detectable — see §5).

| Library (import name) | Required by | Imported how | Must bundle? | Reason |
|---|---|---|---|---|
| `PySide6` (QtWidgets/QtCore/QtGui) | GUI only | **Top-level** in every `quickice/gui/*.py` (e.g. `quickice/gui/main_window.py:18,23,24`). **NOT** imported by `quickice/cli/*` (verified — AGENTS.md constraint holds). | **YES** (GUI) | Entire GUI layer. Only QtWidgets/QtCore/QtGui used — no QtWebEngine/Multimedia/Network/Sql/Pdf/Quick/Qml/Charts/etc. (verified by grep, §4.2). |
| `vtk` / `vtkmodules` | GUI only | **Top-level** `from vtkmodules.all import (...)` in `quickice/gui/{vtk_utils,export,hydrate_renderer,solute_renderer,custom_molecule_renderer,ion_renderer,molecular_viewer,interface_viewer,dual_viewer}.py`; `from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor` in viewers. **Lazy** `from vtkmodules.all import vtkMolecule/vtkMoleculeMapper/vtkActor` inside methods (`solute_viewer.py:253,306`, `custom_molecule_viewer.py:256,309`, `ion_viewer.py:314,367`, `interface_viewer.py:200`). | **YES** (GUI) | All 3D rendering. `vtkmodules.all` wildcard import pulls essentially the whole VTK — largest single size contributor (§7). NOT used by CLI. |
| `numpy` | Both (CLI+GUI) | **Top-level** across `quickice/structure_generation/*`, `quickice/output/*`, `quickice/ranking/scorer.py`, `quickice/utils/molecule_utils.py`, and `quickice/gui/*`. | **YES** | Core array math for the entire physics engine. |
| `scipy` (`scipy.spatial.cKDTree`, `scipy.spatial.transform.Rotation`) | Both | **Top-level** in `quickice/structure_generation/{solute_inserter,custom_molecule_inserter,ion_inserter,overlap_resolver}.py`, `quickice/ranking/scorer.py`, `quickice/output/validator.py:12`, `quickice/gui/vtk_utils.py:19`. | **YES** | cKDTree for overlap/insertion, Rotation for solute orientation, scorer neighbor distances. |
| `genice2` | Both | **Top-level** `quickice/structure_generation/generator.py:11-12` (`from genice2.plugin import safe_import`, `from genice2.genice import GenIce`). **Lazy** in `quickice/structure_generation/hydrate_generator.py:78-81,253-255` (`genice2.genice`, `genice2.formats.gromacs`, `genice2.lattices.{sI,sII,sH,c0te,c1te,c2te,ice1hte,sTprime}`, `genice2.molecules.tip4p`) and `custom_guest_bridge.py:131,297` (`genice2.plugin.audit_name`). | **YES** | Hydrate lattice generation (sI/sII/sH + test lattices), TIP4P molecule, GROMACS format export. Used by CLI pipeline (`cli/pipeline.py` → structure_generation) and GUI. |
| `genice_core` | Both (transitive) | **NOT directly imported** by `quickice/` (grep: no matches). | **YES** | Runtime dependency of `genice2` (`genice-core==1.4.3` in `environment.yml`). Must be present for genice2 to function. Kept in `collect_all` correctly. |
| `spglib` | Both | **Top-level** `quickice/output/validator.py:11` (`import spglib`). | **YES** | Space-group validation in shared `quickice/output/validator.py` (called by `quickice/output/orchestrator.py:12`, used by CLI `main.py` and GUI). |
| `iapws` (incl. private `iapws._iapws`) | Both | **Top-level** `quickice/phase_mapping/water_density.py:31` (`from iapws import IAPWS95`), `quickice/phase_mapping/ice_ih_density.py:27` (`from iapws._iapws import _Ice` — **private submodule**). **Lazy** `quickice/gui/phase_diagram_widget.py:64,473` (`from iapws import IAPWS97`). | **YES** | Water/ice density for phase lookup (`quickice.phase_mapping` is imported by CLI `main.py:9` and GUI). Note the `_iapws` private submodule (§5). |
| `matplotlib` | Both | **Top-level** `quickice/output/phase_diagram.py:13,15` (`import matplotlib.pyplot as plt`, `from matplotlib.patches import Polygon`) — **shared output, used by CLI** via `output_ranked_candidates` (`main.py:159`). GUI: `quickice/gui/phase_diagram_widget.py:17-19` (`backend_qtagg.FigureCanvasQTAgg`, `matplotlib.figure.Figure`), `quickice/gui/export.py:12` (`matplotlib.figure.Figure`). | **YES** | CLI phase-diagram PNG/SVG generation AND GUI interactive phase diagram + export. **Cannot be excluded** without breaking CLI `output_ranked_candidates` (unless `--no-diagram` is always passed). |
| `shapely` | **GUI only** | **Top-level** `quickice/gui/phase_diagram_widget.py:20` (`from shapely.geometry import Point, Polygon as ShapelyPolygon`). NOT used by CLI `output/phase_diagram.py` (it uses `matplotlib.patches.Polygon`). | **YES** (GUI) — optional | Only for interactive phase-diagram hover hit-testing. Small. Could be excluded only if that hover feature is sacrificed (§4.8). |
| `networkx` | Both (transitive) | **NOT directly imported** by `quickice/` (grep: no matches). | **YES** | Transitive dep of `genice2` (ring/cage perception). Must be present for genice2. Kept in `collect_all` correctly. |
| `genice2` transitive deps: `cycless`, `graphstat`, `pairlist`, `wirerope`, `yaplotlib`, `methodtools`, `deprecated`, `deprecation`, `six`, `wrapt`, `click`, `openpyscad` | Both (transitive) | **NOT directly imported** by `quickice/`. | **YES (defensive)** | `environment.yml` pins them; `genice2` may import them (some dynamically). They are pure-Python and small. NOT currently in `collect_all` → potential runtime `ImportError` if genice2 imports them via `importlib` (§5). |
| `pytest`, `pytest-cov`, `pytest-timeout` | **Test only** | NOT imported by `quickice/` (only in `tests/`). | **NO — must NOT bundle** | Dev/test only. `requirements-dev.txt`, not `environment.yml`. Strip from bundle (§4.5). |
| `tkinter` | Neither | NOT imported by `quickice/`. May be pulled by matplotlib's Tk backend. | **NO — exclude** | GUI uses `backend_qtagg` (Qt), never Tk. Safe to exclude (§4.4). |

**CLI/GUI import isolation (AGENTS.md constraint):** Verified — `quickice/cli/` has **zero** `import`/`from` of `vtk`, `PySide6`, `matplotlib`, or `shapely` (grep returned no matches). The shared core (`quickice/structure_generation/`, `quickice/output/`, `quickice/phase_mapping/`, `quickice/ranking/`) uses only `numpy`/`scipy`/`spglib`/`iapws`/`genice2`/`matplotlib`. So a CLI-only build would not need PySide6/VTK/shapely, but the current spec builds the **GUI** bundle (entry `quickice/__main__.py` → `quickice.entry.main()` routes to GUI when `--gui`), so all GUI deps must be bundled.

---

## 3. Entry-point / lazy-import reality check (why the spec's omissions matter)

`quickice/__main__.py` → `from quickice.entry import main`. `quickice/entry.py` has **only stdlib top-level imports** (`importlib.util`, `platform`, `sys`); all heavy imports are inside `main()` branches:
- `from quickice.cli.parser import create_parser` (help/version branches)
- `from quickice.main import main as cli_main` (CLI branches) → pulls `numpy`, `scipy`, `spglib`, `iapws`, `genice2`, `matplotlib` via the shared core.
- `from quickice.gui.main_window import run_app` (GUI branch, `entry.py:176`) → pulls `PySide6`, `vtkmodules`, `numpy`, `matplotlib`, `shapely`.

PyInstaller's modulegraph parses the AST of every reachable module, so it **does** follow these function-body `from X import Y` statements (they are not `importlib.import_module`). Therefore `PySide6` and `vtk` **are** in the import graph via `quickice.gui.main_window` and DO trigger PyInstaller's built-in hooks — they are bundled despite being absent from the `collect_all` list. The genuine, non-statically-detectable risks are the `importlib`/plugin/generated-code paths (§5) and the `find_spec`-only check in `entry.py:37` (`importlib.util.find_spec('PySide6')` — `find_spec` does NOT import, so it does not add PySide6 to the graph; it is only present because `main_window` imports it).

---

## 4. Bundled-size reduction opportunities

Ordered roughly by expected size savings (largest first). All snippets are **SUGGESTED — NOT APPLIED**.

### 4.1 Enable `strip=True` (debug symbols) — LARGE win, low risk

The spec sets `strip=False` in both `EXE` (line 41) and `COLLECT` (line 55). VTK, PySide6, numpy, scipy, and Qt `.so` files ship substantial debug/symbol tables. Stripping typically saves 50–150 MB across a VTK+Qt+scipy bundle. This is the single highest-leverage, lowest-risk change.

**SUGGESTED — NOT APPLIED** (in `quickice-gui.spec`):
```python
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='quickice-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,          # <-- was False
    upx=True,
    ...
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,          # <-- was False
    upx=True,
    upx_exclude=[],
    name='quickice-gui',
)
```
Risk: stack traces from native crashes become less informative. Acceptable for a distribution build (keep an unstripped dev build for debugging).

### 4.2 Exclude unused Qt modules — LARGE win (esp. QtWebEngine = Chromium)

Grep confirms `quickice/` imports **only** `PySide6.QtWidgets`, `PySide6.QtCore`, `PySide6.QtGui`. No usage of `QtWebEngine*`, `QtMultimedia`, `QtNetwork`, `QtSql`, `QtPdf`, `QtQuick`, `QtQml`, `QtCharts`, `QtDataVisualization`, `QtWebSockets`, `QtBluetooth`, `QtNfc`, `QtPositioning`, `QtLocation`, `QtSensors`, `QtSerialPort`, `QtSvg`, `QtXml`, `QtPrintSupport`, `QtTest`, `QtDBus`, `QtDesigner`, `QtHelp`, `QtRemoteObjects`, `QtQuick3D`, `QtQuickWidgets`, `QtShaderTools`, `QtSpeech`, `QtUiTools`, `QtWebChannel`, `QtConcurrent`. PySide6's PyInstaller hook tends to pull many of these (QtWebEngine alone is ~150–300 MB — it embeds Chromium). Excluding them is the biggest Qt-side saving.

⚠️ **Keep** `PySide6.QtOpenGL` and `PySide6.QtOpenGLWidgets` — VTK's `QVTKRenderWindowInteractor` renders via OpenGL; excluding OpenGL Qt modules can break the 3D view. They are not imported by name in `quickice/` (VTK pulls them internally), so do NOT add them to excludes.

**SUGGESTED — NOT APPLIED** (extend the `excludes` list in `Analysis`):
```python
a = Analysis(
    ['quickice/__main__.py'],
    ...
    excludes=[
        # existing path-style prunes
        '*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*',
        '*/.pytest_cache/*', '*/egg-info/*',
        # --- unused Qt modules (NOT imported anywhere in quickice/) ---
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineQuick',  'PySide6.QtWebChannel',
        'PySide6.QtMultimedia',     'PySide6.QtMultimediaWidgets',
        'PySide6.QtNetwork',        'PySide6.QtSql',
        'PySide6.QtPdf',            'PySide6.QtPdfWidgets',
        'PySide6.QtQuick',          'PySide6.QtQuickWidgets',
        'PySide6.QtQuick3D',        'PySide6.QtQml',
        'PySide6.QtCharts',         'PySide6.QtDataVisualization',
        'PySide6.QtWebSockets',     'PySide6.QtBluetooth',
        'PySide6.QtNfc',            'PySide6.QtPositioning',
        'PySide6.QtLocation',       'PySide6.QtSensors',
        'PySide6.QtSerialPort',     'PySide6.QtSerialBus',
        'PySide6.QtSvg',            'PySide6.QtSvgWidgets',
        'PySide6.QtXml',            'PySide6.QtPrintSupport',
        'PySide6.QtTest',           'PySide6.QtDBus',
        'PySide6.QtDesigner',       'PySide6.QtHelp',
        'PySide6.QtRemoteObjects',  'PySide6.QtShaderTools',
        'PySide6.QtSpeech',         'PySide6.QtUiTools',
        'PySide6.QtConcurrent',
        # NOTE: do NOT exclude PySide6.QtOpenGL / PySide6.QtOpenGLWidgets (VTK needs them)
    ],
    ...
)
```
Risk: if any future feature uses one of these (e.g., QtSvg for icons, QtPrintSupport for printing), it would need re-adding. Current code uses none. Verify the GUI launches and renders after this change.

### 4.3 Exclude `tkinter` — small-medium win, low risk

`quickice/` never imports `tkinter`; matplotlib uses `backend_qtagg` (Qt). But matplotlib/PyInstaller may pull the Tk backend + `tkinter` (and `libtk`/`Tcl` libs). Excluding `tkinter` removes Tcl/Tk runtime from the bundle.

**SUGGESTED — NOT APPLIED** (add to the `excludes` list above):
```python
        'tkinter', '_tkinter',
```
Risk: if matplotlib falls back to a Tk backend at runtime (it should not — `backend_qtagg` is imported explicitly in `phase_diagram_widget.py:17`), a non-Qt plot would fail. Current code is safe.

### 4.4 Exclude stdlib test/debug modules — small win, low risk

PyInstaller usually omits most of these, but adding them explicitly belt-and-suspenders the bundle and prevents `numpy`/`scipy` test subpackages from sneaking in.

**SUGGESTED — NOT APPLIED** (add to `excludes`):
```python
        # stdlib / test infrastructure not needed at runtime
        'pytest', '_pytest', 'pytest_cov', 'pytest_timeout', 'pytest_xdist',
        'unittest', 'doctest', 'pydoc', 'lib2to3', 'distutils',
        'curses', 'pdb', 'profile', 'pstats', 'test',
        # IPython/Jupyter (not used, but matplotlib may reference)
        'IPython', 'jupyter', 'notebook', 'ipykernel', 'ipywidgets',
```

### 4.5 Prune `datas` — small win, good hygiene

`datas = [('quickice/data', 'quickice/data')]` (line 5) bundles the **entire** `quickice/data/` tree, including non-runtime files:
- `quickice/data/tip4p-ice.itp.bak` — a backup file, never read at runtime.
- `quickice/data/custom/test_invalid/` — test fixtures (`not_a_gro.txt`, `na_single.itp`, `na_single.gro`, `etoh_no_atomtypes.itp`, `etoh_mismatch.gro`, `etoh_combrule1.itp`, `README.md`) used by the `tests/` suite, not by runtime code.
- `quickice/data/examples/custom_positions.csv` — a sample file for the `--custom-positions-file` option; not auto-loaded at runtime (grep found no code reading it by name), but small and useful to ship for users.

Runtime-loaded data files (must remain bundled) — resolved via `Path(quickice.__file__).parent / "data"` / `Path(__file__).parent.parent / "data"`:
- `tip4p-ice.itp` — `quickice/output/_tip4p.py:25,30` (`get_tip4p_itp_path`), copied by `cli/itp_helpers.py:313`, `gui/export.py:216/392/538/944/1120`, `main.py:142`.
- `tip4p.gro` — `quickice/structure_generation/water_filler.py:236`.
- `ch4.itp`, `thf.itp` — `gui/hydrate_export.py:44`, `gui/export.py:976`.
- `ch4_hydrate.itp`, `thf_hydrate.itp` — `gui/hydrate_export.py:71`, `gui/export.py:1003`, `cli/itp_helpers.py:34`.
- `ch4_liquid.itp`, `thf_liquid.itp` — `cli/itp_helpers.py:57`, `gui/export.py:235,558`.
- `custom/etoh.{itp,gro,top,chg}` — custom-molecule example set.

**Option A — narrow the datas tuple (preferred, single source of truth):** list only the runtime-needed files. **SUGGESTED — NOT APPLIED** (replace line 5):
```python
datas = [
    ('quickice/data/tip4p-ice.itp',          'quickice/data'),
    ('quickice/data/tip4p.gro',             'quickice/data'),
    ('quickice/data/ch4.itp',               'quickice/data'),
    ('quickice/data/thf.itp',               'quickice/data'),
    ('quickice/data/ch4_hydrate.itp',       'quickice/data'),
    ('quickice/data/thf_hydrate.itp',      'quickice/data'),
    ('quickice/data/ch4_liquid.itp',       'quickice/data'),
    ('quickice/data/thf_liquid.itp',       'quickice/data'),
    ('quickice/data/custom',               'quickice/data/custom'),  # etoh.* examples (no test_invalid)
    ('quickice/data/examples',             'quickice/data/examples'),
]
```
Then explicitly drop `test_invalid/` from the `custom` copy. Because PyInstaller `datas` tuples copy whole directories, the cleanest way to omit `test_invalid/` is to either (a) move `test_invalid/` out of `quickice/data/custom/` into `tests/fixtures/` (repo change, out of scope here), or (b) add a post-build prune (Option B).

**Option B — post-build prune in `scripts/assemble-dist.sh`** (keeps the spec simple). **SUGGESTED — NOT APPLIED** (insert after `cp -r quickice-gui package/`, before tarring):
```bash
# Remove non-runtime data shipped by collect_all/datas
rm -f  package/quickice-gui/_internal/quickice/data/tip4p-ice.itp.bak
rm -rf package/quickice-gui/_internal/quickice/data/custom/test_invalid
```
Risk: tiny. Confirm no runtime code reads `test_invalid/` (grep confirms none) or `.bak` (no references).

### 4.6 Drop redundant `collect_all('numpy')` / `collect_all('scipy')` — medium win, **tradeoff**

`numpy` and `scipy` are already reachable via the import graph (top-level imports throughout `quickice/structure_generation/` and `quickice/output/`), so PyInstaller's built-in `hook-numpy.py` / `hook-scipy.py` hooks fire and include the needed binaries. The explicit `collect_all('numpy')` / `collect_all('scipy')` re-collects **all** numpy/scipy submodules + data (including test data, examples, `numpy.f2py`, `numpy.distutils`, `scipy._lib` docs), which over-bundles. Removing them typically saves 20–60 MB.

**SUGGESTED — NOT APPLIED** (edit line 9):
```python
for pkg in ['iapws', 'genice2', 'genice_core', 'matplotlib', 'shapely', 'networkx', 'spglib']:
    # NOTE: numpy and scipy are reachable via the import graph; PyInstaller's
    # built-in hooks include them. collect_all('numpy'/'scipy') over-bundles
    # (test data, f2py, distutils). Only re-add if a runtime ImportError appears.
```
Risk: **medium** — if a numpy/scipy data file or compiled extension is missed by the built-in hook (rare but possible on some platforms), a runtime `ImportError` occurs. Mitigation: test the frozen binary end-to-end (ice generation + GROMACS export + ion insertion, which exercise cKDTree/Rotation). If anything fails, restore `collect_all` for the failing package. **Recommend keeping this as the LAST optimization to try**, after verifying the build works without it.

### 4.7 Optional: exclude `shapely` (GUI-only, small) — **feature loss**

`shapely` is used **only** in `quickice/gui/phase_diagram_widget.py:20` for interactive hover hit-testing on the phase diagram. It is small (~5–10 MB), so the saving is minor. Excluding it requires dropping the hover feature (the CLI path already uses `matplotlib.patches.Polygon` without shapely, so CLI is unaffected).

**SUGGESTED — NOT APPLIED** (only if the hover feature is intentionally dropped):
```python
        'shapely', 'shapely.geometry',
# and remove 'shapely' from the collect_all list on line 9
```
Recommendation: **do NOT exclude** — the size saving is negligible vs. VTK/Qt and the feature loss is user-visible. Listed only for completeness.

### 4.8 UPX: keep enabled, consider `upx_exclude` for fragile libs

`upx=True` is already set (lines 42, 56) with `upx_exclude=[]`. UPX compresses shared libs (good). However, UPX can break certain Qt/VTK `.so` files or trigger antivirus false positives. If the frozen binary crashes on launch or renders incorrectly, exclude the offending libs.

**SUGGESTED — NOT APPLIED** (only if UPX-related runtime issues appear):
```python
coll = COLLECT(
    ...,
    upx=True,
    upx_exclude=[
        # VTK and Qt rendering libs sometimes break under UPX
        'vtk*.so', 'libQt*.so.*', 'libvtk*.so',
    ],
    ...
)
```
No change recommended unless a problem is observed — UPX is currently a net win.

### 4.9 Keep onedir (do NOT switch to onefile) — confirm, not a saving

The spec uses `COLLECT` (onedir). Onedir is already more size-efficient than onefile (onefile embeds + decompresses to a temp dir at every launch, and duplicates the bootloader). For a portable distribution launched via `QuickIce.sh`, onedir is correct. **No change.** (Documenting this so it is not "optimized" into onefile by mistake.)

### 4.10 `console=True` + `hide_console='hide-late'` — keep

Not a size issue. `hide-late` is useful: the console surfaces startup/import errors (e.g., missing hidden imports) before hiding. For diagnosing the very hidden-import risks in §5, keep `console=True` during validation; consider `console=False` only for a final polished release.

---

## 5. Hidden imports to add

PyInstaller's static analysis follows plain `from X import Y` (even inside functions), so most lazy imports are already detected. The genuine gaps are `importlib`/plugin/generated-code loading and private submodules. Recommendations for `hiddenimports` (additive to what `collect_all` already populates):

### 5.1 `vtkmodules.qt.QVTKRenderWindowInteractor` and `vtkmodules.all`

VTK is imported via the wildcard `from vtkmodules.all import (...)`. PyInstaller's vtk hook bundles `vtkmodules`, but the `vtkmodules.qt` submodule (the Qt interactor) is a less-common path. Add it explicitly to guarantee the Qt–VTK bridge is present.

**SUGGESTED — NOT APPLIED** (after the `collect_all` loop, before `Analysis`):
```python
hiddenimports += [
    'vtkmodules', 'vtkmodules.all', 'vtkmodules.qt',
    'vtkmodules.qt.QVTKRenderWindowInteractor',
]
```

### 5.2 `iapws._iapws` (private submodule)

`quickice/phase_mapping/ice_ih_density.py:27` does `from iapws._iapws import _Ice` — a **private/underscore** submodule. `collect_all('iapws')` should already include it, but underscore-prefixed modules are occasionally filtered. Add defensively:

**SUGGESTED — NOT APPLIED**:
```python
hiddenimports += ['iapws._iapws']
```

### 5.3 `genice2` plugin modules (generated-code / plugin loader path)

`quickice/structure_generation/custom_guest_bridge.py:154` writes the literal string `"import genice2.molecules\n"` into a generated module that genice2's plugin loader then `exec`s. PyInstaller cannot statically see a string literal as an import. The specific genice2 plugins used are also imported normally in `hydrate_generator.py:80-81` (`genice2.lattices.{sI,sII,sH,c0te,c1te,c2te,ice1hte,sTprime}`, `genice2.molecules.tip4p`, `genice2.formats.gromacs`), so they are detected — but the generated-code path makes `collect_all('genice2')` (already present) essential, and adding the plugin submodules as explicit hiddenimports is cheap insurance:

**SUGGESTED — NOT APPLIED**:
```python
hiddenimports += [
    'genice2.molecules', 'genice2.molecules.tip4p',
    'genice2.lattices', 'genice2.lattices.sI', 'genice2.lattices.sII',
    'genice2.lattices.sH', 'genice2.lattices.c0te', 'genice2.lattices.c1te',
    'genice2.lattices.c2te', 'genice2.lattices.ice1hte', 'genice2.lattices.sTprime',
    'genice2.formats', 'genice2.formats.gromacs',
    'genice2.genice', 'genice2.plugin', 'genice2.valueparser',
]
```

### 5.4 `genice2` transitive dependencies (not in `collect_all`)

`environment.yml` pins `cycless`, `graphstat`, `pairlist`, `wirerope`, `yaplotlib`, `methodtools`, `deprecated`, `deprecation`, `six`, `wrapt`, `click`, `openpyscad` — none are imported by `quickice/` directly, but `genice2` may import them (some via `importlib`). They are **not** in the `collect_all` list, so if genice2 imports them dynamically they will be missing at runtime. They are small (pure Python). Add as hiddenimports defensively, or add them to the `collect_all` loop:

**SUGGESTED — NOT APPLIED** (option 1 — hiddenimports):
```python
hiddenimports += [
    'cycless', 'graphstat', 'pairlist', 'wirerope', 'yaplotlib',
    'methodtools', 'deprecated', 'deprecation', 'six', 'wrapt', 'click',
    'openpyscad',
]
```
**SUGGESTED — NOT APPLIED** (option 2 — add to the `collect_all` loop on line 9):
```python
for pkg in ['iapws', 'genice2', 'genice_core', 'matplotlib', 'scipy', 'numpy',
            'shapely', 'networkx', 'spglib',
            'cycless', 'graphstat', 'pairlist', 'wirerope', 'yaplotlib',
            'methodtools', 'deprecated', 'deprecation', 'six', 'wrapt', 'openpyscad']:
```
(Use option 2 only if option 1 still leaves missing-module errors; it over-collects slightly.)

### 5.5 `PySide6` — defensive (the only path is a lazy import)

`PySide6` reaches the graph only via `quickice/entry.py:176` (`from quickice.gui.main_window import run_app`, inside the `if known.gui:` branch) → `quickice/gui/main_window.py:18-24`. PyInstaller parses this regardless of the `if` condition, so PySide6 IS bundled via its built-in hook. Adding the three used submodules as explicit hiddenimports is cheap insurance against any future refactor that moves the import behind `importlib`:

**SUGGESTED — NOT APPLIED**:
```python
hiddenimports += ['PySide6.QtCore', 'PySide6.QtWidgets', 'PySide6.QtGui']
```

---

## 6. Datas to bundle (summary)

**Must bundle (runtime-loaded from `quickice/data/`):**
| File | Loaded by | Loader pattern |
|---|---|---|
| `quickice/data/tip4p-ice.itp` | All GROMACS exports (CLI+GUI) | `quickice/output/_tip4p.py:25,30` (`Path(quickice.__file__).parent / "data" / "tip4p-ice.itp"`) |
| `quickice/data/tip4p.gro` | Water filling | `quickice/structure_generation/water_filler.py:236` (`Path(__file__).parent.parent / "data" / "tip4p.gro"`) |
| `quickice/data/ch4.itp`, `thf.itp` | Hydrate guest topology | `quickice/gui/hydrate_export.py:44`, `quickice/gui/export.py:976` |
| `quickice/data/ch4_hydrate.itp`, `thf_hydrate.itp` | Hydrate guest topology | `quickice/gui/hydrate_export.py:71`, `quickice/gui/export.py:1003`, `quickice/cli/itp_helpers.py:34` |
| `quickice/data/ch4_liquid.itp`, `thf_liquid.itp` | Solute liquid topology | `quickice/cli/itp_helpers.py:57`, `quickice/gui/export.py:235,558` |
| `quickice/data/custom/etoh.{itp,gro,top,chg}` | Custom-molecule example | `quickice/structure_generation/solute_inserter.py:261` (`data_dir = Path(__file__).parent.parent / "data"`) + GUI custom panel |
| `quickice/data/examples/custom_positions.csv` | Sample for `--custom-positions-file` | Not auto-loaded; keep for user convenience (optional) |

**Must NOT bundle (test/backup cruft):**
- `quickice/data/tip4p-ice.itp.bak`
- `quickice/data/custom/test_invalid/` (all contents — `not_a_gro.txt`, `na_single.*`, `etoh_no_atomtypes.itp`, `etoh_mismatch.gro`, `etoh_combrule1.itp`, `README.md`)

See §4.5 for the pruning snippet.

---

## 7. Risk / tradeoffs

- **Data-file resolution via `__file__` under PyInstaller (HIGHEST RISK — verify).** All runtime data lookups use `Path(quickice.__file__).parent / "data"` or `Path(__file__).parent.parent / "data"` (e.g. `quickice/output/_tip4p.py:23-30`, `quickice/structure_generation/water_filler.py:236`, `quickice/structure_generation/solute_inserter.py:261`, `quickice/gui/hydrate_export.py:37,64`, `quickice/gui/export.py:969,996`). In a **onedir** build these usually resolve because `__file__` points to a real path under `_MEIPASS` and `datas` places files at `_internal/quickice/data/`. However, this is fragile: if a module is kept only in the PYZ (no on-disk `.pyc`), or if `optimize>0` is later set, `__file__` may become a PYZ-internal virtual path and the lookup can fail silently — breaking GROMACS export (no `tip4p-ice.itp`) and water filling (no `tip4p.gro`). The robust fix is `importlib.resources.files('quickice') / 'data' / '<file>'` (or `sys._MEIPASS`-aware helper). **Recommendation: do NOT change code in this task**, but the maintainer should smoke-test the frozen binary's GROMACS export and water-filling paths; if they fail, migrate the loaders to `importlib.resources`. This is orthogonal to the size-reduction suggestions but is the most likely correctness risk of the current setup.

- **Excluding Qt modules too aggressively.** §4.2 excludes many Qt modules. The three modules NOT to exclude are `PySide6.QtOpenGL` and `PySide6.QtOpenGLWidgets` (VTK's `QVTKRenderWindowInteractor` needs OpenGL for rendering) and the three actually-used modules (`QtCore/QtWidgets/QtGui`). If the 3D viewers render as blank/black windows after applying §4.2, re-add `PySide6.QtOpenGL` and `PySide6.QtOpenGLWidgets` (or remove the whole Qt exclude block and bisect).

- **VTK size is largely irreducible.** `from vtkmodules.all import (...)` (in every renderer) imports the VTK wildcard, so PyInstaller must bundle essentially all of VTK (~300–500 MB). Excluding individual `vtkmodules.*` submodules is unsafe (renderers use many vtk classes via `all`). The realistic VTK savings are: `strip=True` (§4.1) and UPX (§4.8). A deeper reduction would require refactoring `from vtkmodules.all import (...)` to `from vtkmodules.vtkCommonDataModel import vtkPolyData`-style narrow imports — a **source change**, out of scope for a spec-only suggestion and risky (many call sites: `quickice/gui/{vtk_utils,export,hydrate_renderer,solute_renderer,custom_molecule_renderer,ion_renderer,molecular_viewer,interface_viewer,dual_viewer}.py`). Flagged for awareness only.

- **`collect_all('numpy'/'scipy')` removal (§4.6) is a tradeoff.** Saves 20–60 MB but risks a missed numpy/scipy data/extension file. Apply last, with full end-to-end testing (ice gen → ranking → GROMACS export → ion insertion). Keep a rollback ready.

- **`excludes` glob patterns may be unreliable.** The existing `excludes=['*/tests/*', ...]` (line 27) use path-style globs. PyInstaller's `excludes` is documented to accept module-name patterns; the canonical form is module names (`numpy.tests`, `pytest`, `tkinter`, `PySide6.QtWebEngineCore`). The existing globs may or may not prune test data pulled by `collect_all`. The §4.2–§4.4 additions use canonical module names and are reliable; the existing globs should be considered best-effort.

- **`pytest`/test frameworks.** §4.4 explicitly excludes `pytest`/`_pytest`/`pytest_cov`/`unittest`. These are not in `quickice/` imports, so they should not be in the graph anyway — but `collect_all` of a package that (transitively) imports pytest could pull them. The explicit excludes are belt-and-suspenders; no downside.

- **UPX + antivirus.** UPX-compressed binaries (`upx=True`) sometimes trigger false positives in enterprise antivirus on Windows; on Linux this is rarely an issue. If the portable tarball is flagged, set `upx=False` or use `upx_exclude` (§4.8).

- **No runtime smoke test in the build pipeline.** `scripts/build-linux.sh` only checks that `dist/quickice-gui/quickice-gui` is executable — it does NOT launch the GUI or run a CLI export. Any of the hidden-import gaps in §5 or the data-resolution risk above would **not** be caught by the build script. **Recommendation (out of scope to implement):** add a post-build smoke test that runs `./dist/quickice-gui/quickice-gui --cli -T 270 -P 0.1 --interface --mode slab ...` and a GUI launch under `QT_QPA_PLATFORM=offscreen` to catch missing-import and data-file failures before tarring.

---

*End of analysis. READ-ONLY; nothing was modified or executed.*
