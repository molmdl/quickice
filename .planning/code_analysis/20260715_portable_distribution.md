# Portable Distribution Analysis — Scancode Task D

**Analysis Date:** 2026-07-15
**Analyst:** GSD codebase mapper (read-only)
**Subject:** PyInstaller portable distribution sizing & slimming
**Codebase:** quickice v4.7.0 (`quickice/__init__.py`), conda env `quickice`, Python 3.14.3

---

## 0. Executive Summary

The current Linux portable bundle (`dist/quickice-gui/`, built from `quickice-gui.spec`)
is **~872 MB unpacked** and ships as a **~304 MB** tar.gz
(`dist/quickice-v4.5-linux-x86_64.tar.gz`). The dominant costs are VTK (~286 MB,
33%), scipy (~113 MB, 13%), PySide6 (~29 MB), numpy (~28 MB), and matplotlib + deps
(~28 MB).

The single largest, lowest-risk lever is enabling `strip=True` (all bundled `.so`
are currently **not stripped**) plus excluding unused scipy submodules and the
unused Tcl/Tk stack. The single largest *potential* lever is narrowing the
`from vtkmodules.all import (...)` pattern in `quickice/gui/` (13 files) to
targeted submodule imports, which would let PyInstaller collect a fraction of the
150 `libvtk*.so` libraries — but this requires a code change and is flagged as a
follow-up, not a `.spec`-only fix.

No code or `.spec` files were modified. All suggestions below are read-only
recommendations with concrete diffs.

---

## 1. Current Packaging Setup

### 1.1 Spec file

- **Location:** `quickice-gui.spec` (repo root, 59 lines)
- **Build script:** `scripts/build-linux.sh` — runs `pyinstaller --clean quickice-gui.spec`
- **Assemble script:** `scripts/assemble-dist.sh` — tars `dist/quickice-gui/` +
  `QuickIce.sh`, `README.md`, `README_bin.md`, `LICENSE`, `docs/`, `licenses/*.txt`
  into `dist/quickice-${version}-linux-x86_64.tar.gz`
- **Build env definition:** `environment-build.yml` (separate `quickice-build` env,
  pins PyInstaller 6.19.0). Runtime env: `environment.yml`.

### 1.2 Spec structure (Analysis → EXE → COLLECT, one-dir)

```python
# quickice-gui.spec (current)
datas = [('quickice/data', 'quickice/data')]
binaries = []
hiddenimports = []

# collect_all() applied to 8 packages only:
for pkg in ['iapws', 'genice2', 'genice_core', 'matplotlib', 'scipy', 'numpy',
            'shapely', 'networkx', 'spglib']:
    tmp_ret = collect_all(pkg)   # datas + binaries + hiddenimports

a = Analysis(['quickice/__main__.py'], ...,
    excludes=['*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*',
              '*/.pytest_cache/*', '*/egg-info/*'],
    optimize=0, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='quickice-gui',
          strip=False, upx=True, console=True, hide_console='hide-late', ...)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[],
               name='quickice-gui')
```

### 1.3 Key observations about the current spec

1. **`strip=False` in BOTH `EXE` and `COLLECT`.** Every bundled `.so` is
   `not stripped` (verified: `file dist/quickice-gui/_internal/libvtkCommonCore-9.5.so.1`
   → "ELF ... not stripped"). This is a free, low-risk win.
2. **`excludes` uses file-path globs** (`*/tests/*`, `*/test/*`, `*/docs/*`,
   `*/__pycache__/*`, `*/.pytest_cache/*`, `*/egg-info/*`). These filter *data/binaries
   by path* but do **not** exclude Python *modules* by name (e.g. `tkinter`,
   `scipy.stats`). Module exclusion needs bare module names in `excludes`.
3. **`collect_all` is NOT called for `vtkmodules` or `PySide6`.** These are pulled in
   by PyInstaller's built-in hooks. VTK in particular is collected wholesale because
   every GUI renderer/viewer uses `from vtkmodules.all import (...)`, and
   `vtkmodules.all` is an import-everything aggregator → all 150 `libvtk*.so`
   (210 MB) + 132 `vtkmodules/*.so` (77 MB) are bundled.
4. **`upx=True` already enabled** with `upx_exclude=[]` (UPX compresses every
   eligible binary). `strip=True` + UPX are complementary (strip debug symbols,
   then UPX-compress); the current config skips the strip step.
5. **`optimize=0`.** Setting `optimize=2` strips docstrings/asserts from `.pyc`
   (small win, mostly affects pure-Python packages like networkx/genice2).
6. **One-dir (COLLECT) is correct** for this size. Do NOT switch to one-file — an
   ~800 MB single blob would have multi-second startup and high memory use.
7. **`console=True, hide_console='hide-late'`.** A console window flashes on GUI
   launch; acceptable for a scientific tool that also runs CLI diagnostics.

### 1.4 Measured bundle breakdown (`dist/quickice-gui/_internal/`, unpacked)

| Component | Size | % | Notes |
|---|---|---|---|
| `libvtk*.so` (150 files) | 210 MB | 24% | VTK shared libs, **not stripped** |
| `scipy/` | 83 MB | 10% | only `spatial` (+`_lib`, `linalg` glue) used |
| `vtkmodules/` (132 .so) | 77 MB | 9% | Python wrappers for VTK |
| `scipy.libs/` (OpenBLAS) | 30 MB | 3% | only needed by `scipy.linalg` (unused by app) |
| `PySide6/` | 29 MB | 3% | QtWidgets/Gui/Core used; QtNetwork/QtDBus not |
| `numpy/` | 28 MB | 3% | core dep, keep |
| `matplotlib/` | 20 MB | 2% | 8.1 MB of fonts in `mpl-data/fonts` |
| `python3.14/` | 17 MB | 2% | stdlib |
| `networkx/` | 8 MB | 1% | GenIce2 transitive dep |
| `fontTools/` | 6 MB | 1% | matplotlib dep |
| `spglib/` | 5.9 MB | 1% | used by phase_mapping/ranking |
| `shapely.libs/` + `shapely/` | 10.5 MB | 1% | used (geometry) |
| `genice2/` + `genice_core/` | 3.7 MB | <1% | hydrate generation |
| `_tcl_data` + `_tk_data` + `tcl8` + libtcl/libtk | ~4 MB | <1% | **unused** (no `import tkinter`) |
| `PIL/` + `contourpy/` + `kiwisolver/` + `dateutil/` | ~2 MB | <1% | matplotlib deps |
| `certifi` + `charset_normalizer` + `markupsafe` | ~0.3 MB | <1% | **leaked** (see §6) |
| **TOTAL unpacked** | **~843 MB** (`_internal`) + 29 MB exe overhead | | **~872 MB** |

Compressed deliverable: `dist/quickice-v4.5-linux-x86_64.tar.gz` = **304 MB**.

---

## 2. Required Libraries (must bundle)

| Library | Bundled size | Why required | Import sites |
|---|---|---|---|
| **numpy** | 28 MB | Core numeric array type used everywhere | all of `quickice/structure_generation/`, `gui/`, `output/` |
| **scipy.spatial** | 6.1 MB (`scipy/spatial`) | `cKDTree` for neighbor search, `Rotation` for orientation | `quickice/ranking/scorer.py`, `quickice/structure_generation/{ion_inserter,solute_inserter,custom_molecule_inserter,overlap_resolver}.py`, `quickice/gui/vtk_utils.py` (uses `scipy.spatial.cKDTree` + `scipy.spatial.transform.Rotation`) |
| **VTK** (subset) | see §5 | 3D molecular rendering, PNG/JPEG export | `quickice/gui/vtk_utils.py`, `quickice/gui/*_renderer.py`, `quickice/gui/*_viewer.py`, `quickice/gui/export.py`, `quickice/gui/dual_viewer.py` |
| **PySide6** (QtWidgets/Gui/Core) | ~15 MB of the 29 MB | GUI framework (MVVM) | `quickice/gui/*.py` (24 files) |
| **matplotlib** (QtAgg backend) | 20 MB + deps | Phase diagram widget + figure export | `quickice/gui/phase_diagram_widget.py` (`backend_qtagg.FigureCanvasQTAgg`, `figure.Figure`, `patches.Polygon`), `quickice/gui/export.py` (`figure.Figure`) |
| **genice2** + **genice_core** | 3.7 MB | Hydrate lattice generation (sI/sII/sH/c0te/c1te/c2te/ice1hte/sTprime) | `quickice/structure_generation/hydrate_generator.py` (lazy import), `quickice/structure_generation/generator.py`, `quickice/structure_generation/custom_guest_bridge.py` (`genice2.plugin.safe_import`, `audit_name`) |
| **networkx** | 8 MB | GenIce2 transitive dep (cage/topology analysis) | pulled by `genice2` |
| **spglib** | 5.9 MB | Space-group symmetry for phase mapping/ranking | `quickice/phase_mapping/`, `quickice/ranking/` |
| **shapely** | 10.5 MB | Geometry ops (interface/pocket modes) | `quickice/structure_generation/` |
| **iapws** | 452 KB | Water thermophysical properties (density) | `quickice/structure_generation/types.py` (WATER_VOLUME), water filling |
| **pairlist** | small | GenIce2 transitive dep | via `genice2` |
| **cycless / graphstat / methodtools / wirerope / wrapt / deprecated / deprecation / six / openpyscad / yaplotlib / click** | small | GenIce2 transitive deps + CLI (`click`) + SCAD export | `quickice/entry.py`→`cli`, `quickice/output/` |

### 2.1 Data files that must bundle (`quickice/data/`, 184 KB total)

```
quickice/data/
├── tip4p-ice.itp          # 1.4 KB  — TIP4P-ICE water topology (REQUIRED, see AGENTS.md)
├── tip4p.gro              # 60 KB   — reference water coordinates
├── ch4.itp / ch4_hydrate.itp / ch4_liquid.itp   # ~7 KB — methane templates
├── thf.itp / thf_hydrate.itp / thf_liquid.itp   # ~33 KB — THF templates
├── custom/                # 60 KB   — custom guest residue templates
└── examples/              # 4 KB
```

- Bundled via `datas = [('quickice/data', 'quickice/data')]` in `quickice-gui.spec` — **correct, keep**.
- Per AGENTS.md: `tip4p-ice.itp` is the authoritative source for TIP4P-ICE params;
  `gromacs_writer.py` reads it via `get_tip4p_itp_path()`. Must remain bundled.
- `tip4p-ice.itp.bak` (1.6 KB backup) is **not needed** at runtime — can be dropped
  from the data tree or excluded, but it is tiny.

---

## 3. Libraries Safe to EXCLUDE

### 3.1 Tcl/Tk stack (~4 MB) — SAFE, no code uses tkinter

- **Evidence:** `grep -rn "import tkinter\|from tkinter\|import _tkinter" quickice/`
  returns **no matches**. Tk is pulled in only by matplotlib's `_tkagg` /
  `backend_tk*.py` backends and Python's stdlib Tk detection.
- **Bundled:** `_tcl_data/` (2.6 MB), `_tk_data/` (1.0 MB), `tcl8/` (296 KB),
  `libtcl8.6.so`, `libtk8.6.so`.
- **Action:** add to `excludes`: `'tkinter'`, `'_tkinter'`. Also drop matplotlib's
  Tk backends (see §3.4).
- **Risk:** None — matplotlib is configured to use the **QtAgg** backend
  (`backend_qtagg`), never TkAgg.

### 3.2 scipy unused submodules (~77 MB of the 83 MB `scipy/`) + scipy.libs (~30 MB) — SAFE WITH TESTING

- **Evidence:** `grep "from scipy\|import scipy" quickice/` shows ONLY:
  - `scipy.spatial.cKDTree` (6 files)
  - `scipy.spatial.transform.Rotation` (2 files: `solute_inserter.py`,
    `custom_molecule_inserter.py`)
- **Bundled but unused** (with measured sizes):
  - `scipy/special` 13 MB, `scipy/optimize` 12 MB, `scipy/sparse` 11 MB,
    `scipy/stats` 11 MB, `scipy/linalg` 9.9 MB, `scipy/io` 6.3 MB,
    `scipy/signal` 2.7 MB, `scipy/interpolate` 2.6 MB, `scipy/integrate` 2.3 MB,
    `scipy/fft` 1.5 MB, `scipy/ndimage` 1.4 MB, `scipy/cluster` 812 KB,
    `scipy/odr` 720 KB, `scipy/datasets`, `scipy/differentiate`, `scipy/constants`,
    `scipy/fftpack`, `scipy/misc`
- **`scipy.libs/` (30 MB)** is the OpenBLAS shared lib, loaded only by
  `scipy.linalg`. Since the app does not use `scipy.linalg`, this can be excluded
  *if* `scipy.linalg` is also excluded.
- **Action:** add to `excludes` (keep `scipy.spatial`, `scipy._lib`, `scipy.constants`):
  `scipy.linalg`, `scipy.special`, `scipy.optimize`, `scipy.sparse`, `scipy.stats`,
  `scipy.signal`, `scipy.interpolate`, `scipy.integrate`, `scipy.fft`, `scipy.fftpack`,
  `scipy.ndimage`, `scipy.io`, `scipy.cluster`, `scipy.odr`, `scipy.datasets`,
  `scipy.differentiate`, `scipy.misc`.
- **Risk:** MEDIUM — scipy's import machinery sometimes lazy-imports submodules.
  Must verify `from scipy.spatial import cKDTree` still works post-exclude
  (it should — `scipy.spatial.ckdtree` is a self-contained C++ extension). If
  `scipy.spatial` import fails, keep `scipy.linalg` and `scipy.libs` (the safe
  fallback keeps ~40 MB but still saves ~70 MB).
- **hiddenimports to add** (belt-and-suspenders for the survivors):
  `'scipy.spatial.ckdtree'`, `'scipy.spatial.transform._rotation'`,
  `'scipy._lib'`.

### 3.3 VTK unused modules (~30–50 MB excludable without code change) — PARTIAL

- **Evidence:** The app uses a small set of VTK classes (see §5.1). Many bundled
  VTK I/O and rendering modules are for formats/features the app never touches:
  Exodus, AMR, CGNS, Cesium3D, CityGML, FFMPEG, OggTheora, NetCDF, SegY, SQL,
  HDF, Xdmf, WebGL/VtkJS web export, parallel, geovis, etc.
- **Safe to exclude (no app import path reaches them):**
  `vtkIOExodus`, `vtkIOAMR`, `vtkIOCGNSReader`, `vtkIOCONVERGECFD`,
  `vtkIOCesium3DTiles`, `vtkIOCityGML`, `vtkIOERF`, `vtkIOEnSight`,
  `vtkIOEngys`, `vtkIOFDS`, `vtkIOFFMPEG`, `vtkIOFLUENTCFF`, `vtkIOHDF`,
  `vtkIOIOSS`, `vtkIOLANLX3D`, `vtkIOLSDyna`, `vtkIOMINC`,
  `vtkIOMotionFX`, `vtkIOMovie`, `vtkIONetCDF`, `vtkIOOggTheora`,
  `vtkIOParallel`, `vtkIOParallelXML`, `vtkIOSQL`, `vtkIOSegY`,
  `vtkIOTecplotTable`, `vtkIOVeraOut`, `vtkIOVideo`, `vtkIOXdmf2`,
  `vtkIOXdmf3`, `vtkGeovisCore`, `vtkWebCore`, `vtkWebGLExporter`,
  `vtkRenderingVtkJS`, `vtkRenderingSceneGraph`, `vtkParallelDIY`,
  `vtkFiltersParallel`, `vtkFiltersParallelDIY2`, `vtkFiltersParallelImaging`,
  `vtkFiltersHyperTree`, `vtkFiltersCellGrid`, `vtkFiltersTopology`,
  `vtkFiltersTensor`, `vtkFiltersVerdict`, `vtkFiltersStatistics`,
  `vtkFiltersTemporal`, `vtkFiltersProgrammable`, `vtkFiltersAMR`,
  `vtkRenderingVolumeOpenGL2` (volume rendering unused), `vtkRenderingLICOpenGL2`
  (line integral convolution unused), `vtkRenderingGL2PSOpenGL2` (vector
  export unused), `vtkIOExportGL2PS`, `vtkIOExportPDF`, `vtkRenderingFreeType`
  (test cautiously — text rendering).
- **Action:** add these to `excludes`. Note: PyInstaller `excludes` works on
  *Python module* names; VTK `.so` are pulled by the built-in `vtkmodules` hook
  based on `vtkmodules.all`. Excluding the Python wrapper names
  (`vtkmodules.vtkIOExodus`, etc.) **may** drop the corresponding `.so` if nothing
  else references them, but VTK cross-dependencies are dense. **Verify by
  diffing `du -sh dist/quickice-gui/_internal/vtkmodules` before/after.** Realistic
  `.so`-only-exclude savings: 20–40 MB unpacked.
- **Risk:** LOW for the I/O/web/parallel list above (clearly unused formats).
  Test that PNG/JPEG export (`vtkWindowToImageFilter`, `vtkPNGWriter`,
  `vtkJPEGWriter` in `quickice/gui/export.py`) still works — these live in
  `vtkIOImage` and `vtkRenderingCore`/`vtkRenderingOpenGL2`, which are KEPT.

### 3.4 matplotlib unused backends (~1 MB) — SAFE, minor

- **Evidence:** Only `backend_qtagg` (QtAgg) is imported
  (`quickice/gui/phase_diagram_widget.py`). All other backends are dead weight:
  `backend_gtk3*`, `backend_gtk4*`, `backend_macosx`, `backend_pdf`, `backend_ps`,
  `backend_pgf`, `backend_svg`, `backend_tkagg`, `backend_tkcairo`, `backend_webagg*`,
  `backend_wx*`, `backend_cairo`, `backend_nbagg`, `backend_template`, `_tkagg`.
- **Action:** exclude via `excludes`: `'matplotlib.backends.backend_tkagg'`,
  `'matplotlib.backends.backend_tkcairo'`, `'_tkagg'`, and the gtk/wx/mac/web/pdf/ps/svg/pgf/cairo/nbagg backends. Easiest: rely on the `tkinter` exclusion (§3.1) to kill `_tkagg`, and add the rest by name.
- **Risk:** None — only QtAgg is used. Keep `backend_agg` (Agg is the rasterizing
  core QtAgg depends on).

### 3.5 PySide6 unused Qt modules (~1.5 MB) — SAFE, minor

- **Evidence:** `grep "from PySide6\." quickice/` shows only `QtWidgets`,
  `QtGui`, `QtCore`. `QtNetwork` (1.2 MB) and `QtDBus` (324 KB) are bundled but
  **never imported** by the app.
- **Action:** add to `excludes`: `'PySide6.QtNetwork'`, `'PySide6.QtDBus'`,
  `'PySide6.QtWebEngineCore'`, `'PySide6.QtWebEngineWidgets'`,
  `'PySide6.QtWebEngineQuick'`, `'PySide6.QtQuick3D'`, `'PySide6.QtQml'`,
  `'PySide6.QtQuick'`, `'PySide6.QtMultimedia'`, `'PySide6.QtSql'`,
  `'PySide6.QtTest'`, `'PySide6.QtDesigner'`, `'PySide6.QtHelp'`,
  `'PySide6.QtCharts'`, `'PySide6.QtDataVisualization'`,
  `'PySide6.QtPdf'`, `'PySide6.QtPrintSupport'` (test — Qt print dialog may be
  reached via QFileDialog; keep if unsure).
- **Good news:** Qt **WebEngine is already absent** (no `QtWebEngine*.so` in
  `dist/quickice-gui/_internal/PySide6/`). The Qt plugin tree is already lean
  (4.3 MB total). The `generic` (660 KB) and `wayland-*` plugins can be dropped if
  the target is X11-only, but they are small.
- **Risk:** LOW. `QtNetwork` is sometimes a Qt-internal dep for
  `QNetworkAccessManager`; only exclude if no network access is needed (the app
  is offline/scientific — safe).

### 3.6 Leaked packages from unapproved installs (~0.3 MB + cleanliness risk) — SAFE, recommended

- **Evidence:** `lib-to-add.yml` documents that `genice2-cif`, `MDAnalysis`, and
  `gsw` were `pip install`ed by research agents **without permission** into the
  `quickice` conda env. Their transitive deps leaked into the bundle:
  - `certifi/` (232 KB), `charset_normalizer/` (32 KB), `markupsafe/` (44 KB)
    are present in `dist/quickice-gui/_internal/`. These are transitive deps of
    `genice2-cif → cif2ice → jinja2 → markupsafe` and
    `genice2-cif → requests → certifi/charset_normalizer`.
  - `jinja2`, `requests`, `urllib3`, `idna` are NOT in the bundle (nothing
    imports them), but their leaf deps lingered.
- **MDAnalysis / gsw** are not in the bundle (good), but their presence in the
  build env is a latent risk — if any future code path imports them, they'd be
  pulled in (MDAnalysis alone is ~50 MB).
- **Action (two-part):**
  1. **Spec:** add to `excludes`: `'certifi'`, `'charset_normalizer'`,
     `'markupsafe'`, `'jinja2'`, `'requests'`, `'urllib3'`, `'idna'`,
     `'MDAnalysis'`, `'gsw'`, `'mdanalysis'`, `'cif2ice'`, `'genice2_cif'`,
     `'genice2-cif'`, `'pycifrw'`, `'ply'`, `'validators'`, `'prettytable'`,
     `'wcwidth'`, `'toml'`, `'mmtf'`, `'mda_xdrlib'`, `'griddataformats'`,
     `'mrcfile'`, `'msgpack'`, `'threadpoolctl'`, `'tqdm'`, `'joblib'`,
     `'filelock'`.
  2. **Process (outside spec):** build in a **clean** env matching exactly
     `environment.yml` / `environment-build.yml`. Run
     `pip uninstall -y genice2-cif MDAnalysis gsw` (and their deps) before
     building, or recreate the env from scratch. This is both a size fix and a
     correctness/license-cleanliness fix.
- **Risk:** None — none of these are imported by `quickice/` (verified by grep).

### 3.7 `.dist-info` metadata dirs (~2 MB) — SAFE, trivial

- All `*-dist-info/` dirs (scipy, numpy, networkx, genice2, shapely, spglib,
  iapws, matplotlib, markupsafe) are metadata-only. PyInstaller keeps them for
  `importlib.metadata` lookups. Most apps don't need them at runtime.
- **Action:** the existing `excludes` already has `'*/egg-info/*'`; extend with
  `'*/dist-info/*'` **only if** no runtime code calls `importlib.metadata.version()`
  on these. quickice uses its own `quickice/__init__.py::__version__` (hardcoded
  "4.7.0"), not `importlib.metadata`, so this is safe. Savings small (~2 MB).

---

## 4. Data Files to Bundle

See §2.1. Only `quickice/data/` (184 KB) is required and already correctly wired
via `datas = [('quickice/data', 'quickice/data')]`. No changes needed to `datas`.

The `assemble-dist.sh` script additionally bundles `docs/` (3.8 MB incl. images),
`README.md`, `README_bin.md`, `LICENSE`, and `licenses/*.txt` (44 KB) into the
tarball — these are user-facing docs, not runtime deps. `docs/images/` is the bulk
of the docs cost; if the tarball size matters, ship docs as a separate download
or compress images more aggressively. (Out of scope for the `.spec`.)

---

## 5. Suggested `.spec` Changes (concrete)

### 5.1 Patched `excludes` and `hiddenimports` block

```python
# quickice-gui.spec — PROPOSED additions (drop-in, no code changes needed)

# Tcl/Tk (unused — no `import tkinter` in quickice/)
_tk_excludes = ['tkinter', '_tkinter']

# scipy (only scipy.spatial.{cKDTree,Rotation} are used)
_scipy_excludes = [
    'scipy.linalg', 'scipy.special', 'scipy.optimize', 'scipy.sparse',
    'scipy.stats', 'scipy.signal', 'scipy.interpolate', 'scipy.integrate',
    'scipy.fft', 'scipy.fftpack', 'scipy.ndimage', 'scipy.io', 'scipy.cluster',
    'scipy.odr', 'scipy.datasets', 'scipy.differentiate', 'scipy.misc',
    # NOTE: keep scipy.spatial, scipy._lib, scipy.constants
]

# matplotlib unused backends (only backend_qtagg / backend_agg used)
_mpl_excludes = [
    'matplotlib.backends.backend_tkagg', 'matplotlib.backends.backend_tkcairo',
    'matplotlib.backends.backend_gtk3', 'matplotlib.backends.backend_gtk3agg',
    'matplotlib.backends.backend_gtk3cairo', 'matplotlib.backends.backend_gtk4',
    'matplotlib.backends.backend_gtk4agg', 'matplotlib.backends.backend_gtk4cairo',
    'matplotlib.backends.backend_macosx', 'matplotlib.backends.backend_pdf',
    'matplotlib.backends.backend_ps', 'matplotlib.backends.backend_pgf',
    'matplotlib.backends.backend_svg', 'matplotlib.backends.backend_webagg',
    'matplotlib.backends.backend_webagg_core', 'matplotlib.backends.backend_wx',
    'matplotlib.backends.backend_wxagg', 'matplotlib.backends.backend_wxcairo',
    'matplotlib.backends.backend_cairo', 'matplotlib.backends.backend_nbagg',
    'matplotlib.backends.backend_template',
]

# PySide6 unused Qt modules (only QtWidgets/QtGui/QtCore used)
_qt_excludes = [
    'PySide6.QtNetwork', 'PySide6.QtDBus', 'PySide6.QtWebEngineCore',
    'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick', 'PySide6.QtQuick3D',
    'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtMultimedia', 'PySide6.QtSql',
    'PySide6.QtTest', 'PySide6.QtDesigner', 'PySide6.QtHelp', 'PySide6.QtCharts',
    'PySide6.QtDataVisualization', 'PySide6.QtPdf',
    # 'PySide6.QtPrintSupport',  # keep unless you confirm no print dialogs
]

# VTK unused I/O / web / parallel / exotic-filter modules
_vtk_excludes = [
    'vtkmodules.vtkIOExodus', 'vtkmodules.vtkIOAMR', 'vtkmodules.vtkIOCGNSReader',
    'vtkmodules.vtkIOCONVERGECFD', 'vtkmodules.vtkIOCesium3DTiles',
    'vtkmodules.vtkIOCityGML', 'vtkmodules.vtkIOERF', 'vtkmodules.vtkIOEnSight',
    'vtkmodules.vtkIOEngys', 'vtkmodules.vtkIOFDS', 'vtkmodules.vtkIOFFMPEG',
    'vtkmodules.vtkIOFLUENTCFF', 'vtkmodules.vtkIOHDF', 'vtkmodules.vtkIOIOSS',
    'vtkmodules.vtkIOLANLX3D', 'vtkmodules.vtkIOLSDyna', 'vtkmodules.vtkIOMINC',
    'vtkmodules.vtkIOMotionFX', 'vtkmodules.vtkIOMovie', 'vtkmodules.vtkIONetCDF',
    'vtkmodules.vtkIOOggTheora', 'vtkmodules.vtkIOParallel',
    'vtkmodules.vtkIOParallelXML', 'vtkmodules.vtkIOSQL', 'vtkmodules.vtkIOSegY',
    'vtkmodules.vtkIOTecplotTable', 'vtkmodules.vtkIOVeraOut',
    'vtkmodules.vtkIOVideo', 'vtkmodules.vtkIOXdmf2', 'vtkmodules.vtkIOXdmf3',
    'vtkmodules.vtkGeovisCore', 'vtkmodules.vtkWebCore',
    'vtkmodules.vtkWebGLExporter', 'vtkmodules.vtkRenderingVtkJS',
    'vtkmodules.vtkRenderingSceneGraph', 'vtkmodules.vtkParallelDIY',
    'vtkmodules.vtkFiltersParallel', 'vtkmodules.vtkFiltersParallelDIY2',
    'vtkmodules.vtkFiltersParallelImaging', 'vtkmodules.vtkFiltersHyperTree',
    'vtkmodules.vtkFiltersCellGrid', 'vtkmodules.vtkFiltersTopology',
    'vtkmodules.vtkFiltersTensor', 'vtkmodules.vtkFiltersVerdict',
    'vtkmodules.vtkFiltersStatistics', 'vtkmodules.vtkFiltersTemporal',
    'vtkmodules.vtkFiltersProgrammable', 'vtkmodules.vtkFiltersAMR',
    'vtkmodules.vtkRenderingVolumeOpenGL2', 'vtkmodules.vtkRenderingLICOpenGL2',
    'vtkmodules.vtkRenderingGL2PSOpenGL2', 'vtkmodules.vtkIOExportGL2PS',
    'vtkmodules.vtkIOExportPDF',
]

# Leaked deps from unapproved genice2-cif / MDAnalysis / gsw installs (lib-to-add.yml)
_leak_excludes = [
    'certifi', 'charset_normalizer', 'markupsafe', 'jinja2', 'requests',
    'urllib3', 'idna', 'MDAnalysis', 'mdanalysis', 'gsw', 'cif2ice',
    'genice2_cif', 'genice2-cif', 'pycifrw', 'ply', 'validators',
    'prettytable', 'wcwidth', 'toml', 'mmtf', 'mda_xdrlib',
    'griddataformats', 'mrcfile', 'msgpack', 'threadpoolctl', 'tqdm', 'joblib',
    'filelock',
]

# hiddenimports to guarantee the surviving lazy/dynamic imports are found
_extra_hiddenimports = [
    # scipy survivors
    'scipy.spatial.ckdtree', 'scipy.spatial.transform._rotation', 'scipy._lib',
    # genice2 lazy imports (loaded inside function bodies — see §7)
    'genice2.genice', 'genice2.formats', 'genice2.formats.gromacs',
    'genice2.lattices', 'genice2.lattices.sI', 'genice2.lattices.sII',
    'genice2.lattices.sH', 'genice2.lattices.c0te', 'genice2.lattices.c1te',
    'genice2.lattices.c2te', 'genice2.lattices.ice1hte',
    'genice2.lattices.sTprime', 'genice2.molecules', 'genice2.molecules.tip4p',
    'genice2.plugin', 'genice2.valueparser',
    # matplotlib backend actually used
    'matplotlib.backends.backend_qtagg',
    # VTK Qt interactor (imported lazily inside __init__ of viewers)
    'vtkmodules.qt.QVTKRenderWindowInteractor',
]
```

### 5.2 Apply to Analysis / EXE / COLLECT

```python
a = Analysis(
    ['quickice/__main__.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + _extra_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # existing path-glob data excludes (keep)
        '*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*',
        '*/.pytest_cache/*', '*/egg-info/*',
        # NEW module-name excludes
        *_tk_excludes, *_scipy_excludes, *_mpl_excludes, *_qt_excludes,
        *_vtk_excludes, *_leak_excludes,
    ],
    noarchive=False,
    optimize=2,          # was 0 — strip docstrings/asserts from .pyc
)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='quickice-gui',
    strip=True,          # was False — strip debug symbols from .so  ★ biggest easy win
    upx=True,
    console=True,
    hide_console='hide-late',
    # ... rest unchanged ...
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=True,          # was False — strip the collected .so too  ★
    upx=True,
    upx_exclude=[
        # Do NOT UPX these (avoid AV false-positives / ASLR issues on system libs):
        'libvtk*', 'libQt*', 'libpython*', 'libstdc*', 'libgcc*',
    ],
    name='quickice-gui',
)
```

### 5.3 Notes on `strip` / `upx` interaction

- All bundled `libvtk*.so` and `scipy`/`numpy` `.so` are currently **not stripped**
  (verified with `file`). `strip=True` removes DWARF debug symbols (typically
  20–40% of an unstripped `.so`). PyInstaller strips *before* UPX, so the two
  compose. Because UPX is already on, the *unpacked* dir shrinks a lot but the
  *tar.gz* (already compressed) shrinks less — still worth it for the unpacked
  experience and AV-scan reduction.
- `upx_exclude` for `libvtk*` / `libQt*` / `libpython*` / `libstdc*` / `libgcc*` is
  a defensive choice: UPX on large rendering/system libraries occasionally
  triggers antivirus false-positives and can break ASLR/`dlopen`-based plugin
  loading (Qt plugins, VTK). If UPX is already working fine in the field, keep
  `upx_exclude=[]` and just add `strip=True`; only widen `upx_exclude` if you hit
  runtime `dlopen` errors.

### 5.4 One-file vs one-dir

- **Keep one-dir (COLLECT).** Switching to one-file would create an ~700+ MB
  single executable with multi-second startup (self-extraction to a temp dir on
  every launch) and high RAM use. One-dir is correct for a scientific tool of
  this size. No change.

---

## 6. Dynamic Import Risks (lazy imports PyInstaller may miss)

PyInstaller's static analyzer follows `import` statements but can miss imports
inside function bodies / `try/except` / `importlib`. The codebase deliberately
lazy-imports the three heaviest deps (per AGENTS.md "Lazy Imports"). Each is a
risk that the built binary fails at runtime with `ModuleNotFoundError`.

### 6.1 GenIce2 (lazy, inside `_ensure_genice_import`) — HIGH risk, already partially mitigated

- **Site:** `quickice/structure_generation/hydrate_generator.py:78-81`
  ```python
  import genice2.genice as genice_lib
  from genice2.formats import gromacs
  from genice2.lattices import sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime
  from genice2.molecules.tip4p import Molecule as TIP4P
  ```
  Also `quickice/structure_generation/generator.py:11-12`
  (`genice2.plugin.safe_import`, `genice2.genice.GenIce`) and
  `quickice/structure_generation/custom_guest_bridge.py:131,297`
  (`genice2.plugin.audit_name`), and a **generated string** module
  `genice2.molecules.<guest_type>` registered via `sys.modules` (line 320) —
  this is a *synthetic* module created at runtime; PyInstaller cannot see it.
- **Mitigation in spec:** `collect_all('genice2')` and `collect_all('genice_core')`
  are already in the loop (good — pulls all of genice2's submodules + data). The
  `_extra_hiddenimports` list above adds the specific `genice2.lattices.*` and
  `genice2.molecules.tip4p` names explicitly as belt-and-suspenders.
- **Residual risk:** the custom-guest bridge builds a module named
  `genice2.molecules.<guest_type>` at runtime and injects it into
  `sys.modules`. PyInstaller bundles the `genice2.molecules` *package* (via
  `collect_all`), so `safe_import('molecule', <name>)` should resolve through the
  package path. **Verify** a custom-guest hydrate build runs in the frozen binary
  (see §8).

### 6.2 PySide6 (availability checked via `find_spec`, imported inside branches) — LOW risk

- **Site:** `quickice/entry.py:37` uses `importlib.util.find_spec('PySide6')`
  (never imports at module top). Actual imports are inside `entry.main()`
  branches: `from quickice.gui.main_window import run_app` (line 176), which
  transitively imports all `quickice/gui/*.py` with top-level
  `from PySide6.QtWidgets/QtCore/QtGui import ...`.
- **Mitigation:** PyInstaller's built-in PySide6 hook + the top-level
  `from PySide6...` in GUI modules makes these visible. The proposed
  `_qt_excludes` only drop *unused* Qt modules. **Verify** `--gui` launches after
  excluding `QtNetwork`/`QtDBus`.

### 6.3 VTK (imported top-level in GUI modules, but gated by env vars) — MEDIUM risk after excludes

- **Sites:** 13 files use `from vtkmodules.all import (...)`; 8 viewers lazily
  import `from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor`
  *inside `__init__`*. VTK availability is gated at runtime by
  `QUICKICE_FORCE_VTK` (see §7).
- **Mitigation:** `from vtkmodules.all import` forces PyInstaller to bundle all
  of VTK (that's *why* it's 286 MB). The proposed `_vtk_excludes` drop unused
  submodules. **Risk:** `vtkmodules.all` is a generated aggregator that imports
  *every* `vtkmodules.vtk*` module; if a dropped module is referenced by the
  `all` aggregator at import time, `from vtkmodules.all import vtkActor` could
  raise `AttributeError`/`ImportError` on the missing submodule. **This is the
  chief risk of the VTK excludes.** Two safe strategies:
  1. **Conservative (recommended first):** apply only the clearly-unused I/O/web
     excludes (Exodus, AMR, CGNS, Cesium, FFMPEG, OggTheora, NetCDF, SegY, SQL,
     HDF, Xdmf, Web*, Geovis, parallel). Test PNG/JPEG export + 3D render.
     If `vtkmodules.all` import fails, **do not** use VTK module excludes —
     instead pursue §5.5 (code-level import narrowing).
  2. **If `vtkmodules.all` breaks on excludes:** the robust long-term fix is a
     **code change** (out of scope for this read-only task, but documented in
     §5.5) to replace `from vtkmodules.all import X` with targeted imports like
     `from vtkmodules.vtkRenderingCore import vtkActor, vtkRenderer` etc.

### 6.4 matplotlib backend (lazy-ish) — LOW risk

- `quickice/gui/phase_diagram_widget.py:17` imports
  `from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg` at module
  top level of a GUI module. `collect_all('matplotlib')` already runs. Add
  explicit `matplotlib.backends.backend_qtagg` to hiddenimports as a guarantee.

---

## 7. `QUICKICE_FORCE_VTK` & Mesa Offscreen Rendering — Bundling Implications

### 7.1 The `QUICKICE_FORCE_VTK` gate

- Five viewer/panel modules read the env var to decide whether to attempt VTK
  rendering: `quickice/gui/view.py:26`, `solute_viewer.py:25`,
  `ion_viewer.py:26`, `hydrate_viewer.py:26`, `custom_molecule_viewer.py:26`,
  `interface_panel.py:35`.
- Logic (`view.py:20-34`): VTK is auto-enabled unless `DISPLAY` looks like SSH
  X11 forwarding (`localhost` in `DISPLAY`), in which case VTK is disabled
  *unless* `QUICKICE_FORCE_VTK=true`. On failure to import `DualViewerWidget`,
  `_VTK_AVAILABLE` falls to `False` and the panel renders a textual message
  (`view.py:405`: "or use QUICKICE_FORCE_VTK=true to override").
- **Bundling implication:** VTK must be bundled regardless — even headless/SSH
  users can set `QUICKICE_FORCE_VTK=true` to get rendering. **Do NOT exclude VTK
  entirely.** The goal is to exclude *unused VTK modules*, not VTK itself.

### 7.2 Mesa GLX for remote X11

- `quickice/gui/main_window.py:2115-2139` `_configure_opengl_for_remote()` sets
  `os.environ['__GLX_VENDOR_LIBRARY_NAME'] = 'mesa'` when `DISPLAY` indicates a
  remote (non-`:N` local) session, to avoid an NVIDIA-GLX segfault under
  indirect rendering.
- **Bundling implication:** the bundle must include a working software-OpenGL
  path. On conda, `vtk` (conda-forge) ships `libOSMesa` support and the Qt
  `offscreen` platform plugin. PyInstaller's VTK hook should collect the VTK
  OpenGL2 rendering module (`vtkRenderingOpenGL2` — **keep this**, it's in the
  KEPT list). For pure-headless test farms, users set
  `QT_QPA_PLATFORM=offscreen` (per AGENTS.md "Headless/remote VTK").
- **Risk of excludes:** `vtkRenderingOpenGL2` and `vtkRenderingCore` MUST be
  kept (used by every viewer + PNG/JPEG export). They are NOT in the exclude
  list. Do not add them.

### 7.3 `QT_QPA_PLATFORM=offscreen` (testing, not bundling)

- Set in tests (`tests/test_hydrate_panel.py`, `tests/test_e2e_*_gui.py`, etc.)
  and respected by `entry.py:_has_display()` (line 66) as a valid display mode.
- Not a bundling concern, but relevant to §8 verification.

---

## 8. Estimated Size Savings

Two scenarios. "Unpacked" = `dist/quickice-gui/` dir; "tar.gz" = the shipped
`quickice-vX-linux-x86_64.tar.gz`.

### 8.1 Scenario A — `.spec`-only changes (no code edits)

| Change | Unpacked saved | tar.gz saved |
|---|---|---|
| `strip=True` (EXE + COLLET) on all unstripped `.so` | ~80–120 MB | ~15–25 MB |
| Exclude scipy unused submodules (keep `spatial`+`_lib`) | ~77 MB | ~30–40 MB |
| Exclude `scipy.libs` (OpenBLAS, if `scipy.linalg` excluded) | ~30 MB | ~8–12 MB |
| Exclude Tcl/Tk stack | ~4 MB | ~1.5 MB |
| Exclude leaked (certifi/charset_normalizer/markupsafe) + clean env | ~0.3 MB | ~0.1 MB |
| Exclude PySide6 unused Qt modules + some plugins | ~1.5 MB | ~0.5 MB |
| Exclude matplotlib unused backends | ~1 MB | ~0.3 MB |
| Exclude unused VTK I/O/web/parallel modules (conservative list) | ~20–40 MB | ~8–15 MB |
| `optimize=2` (strip docstrings from networkx/genice2 .pyc) | ~1–2 MB | ~0.5 MB |
| **Total (Scenario A)** | **~215–275 MB** | **~65–95 MB** |
| **Resulting bundle** | **~600–660 MB** | **~210–240 MB** |

> The `strip=True` unpacked saving is the most certain. The scipy submodule
> excludes are the biggest *tar.gz* win but carry MEDIUM test risk (verify
> `cKDTree` import). The VTK-module excludes are the most uncertain
> (`vtkmodules.all` may break — test first, fall back to Scenario B for VTK).

### 8.2 Scenario B — add code-level VTK import narrowing (larger, needs code changes)

If the 13 `from vtkmodules.all import (...)` sites in `quickice/gui/` are
rewritten to targeted submodule imports (e.g.
`from vtkmodules.vtkRenderingCore import vtkActor, vtkRenderer`,
`from vtkmodules.vtkCommonDataModel import vtkPolyData, vtkPoints`,
`from vtkmodules.vtkIOImage import vtkPNGWriter, vtkJPEGWriter`,
`from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera`,
`from vtkmodules.vtkRenderingOpenGL2 import ...`), PyInstaller's VTK collection
shrinks to the ~20 modules actually reachable (Common*, RenderingCore,
RenderingOpenGL2, RenderingQt, InteractionStyle, FiltersSources, IOImage,
DomainsChemistry for vtkMolecule/MoleculeMapper, ChartsCore) instead of all 132.

| Change | Unpacked saved | tar.gz saved |
|---|---|---|
| VTK narrowing: 286 MB → ~120–150 MB | ~140–160 MB | ~50–65 MB |
| **Total (Scenario B = A + VTK narrowing)** | **~355–435 MB** | **~115–160 MB** |
| **Resulting bundle** | **~440–520 MB** | **~145–190 MB** |

Scenario B requires editing `quickice/gui/vtk_utils.py`, `*_renderer.py`,
`*_viewer.py`, `export.py`, `dual_viewer.py` — **out of scope for this read-only
task**, but documented as the highest-impact follow-up. The mapping of used
classes → VTK modules (§5.5 below) makes that change mechanical.

### 8.3 VTK class → module map (for the follow-up code change)

| Used class | VTK module (targeted import path) |
|---|---|
| `vtkMolecule`, `vtkMoleculeMapper` | `vtkmodules.vtkDomainsChemistry` (+ `vtkRenderingCore`) |
| `vtkActor`, `vtkRenderer`, `vtkPolyDataMapper` | `vtkmodules.vtkRenderingCore` |
| `vtkPolyData`, `vtkPoints`, `vtkCellArray`, `vtkMatrix3x3` | `vtkmodules.vtkCommonDataModel` (+ `vtkCommonCore`) |
| `vtkOutlineSource`, `vtkSphereSource` | `vtkmodules.vtkFiltersSources` |
| `vtkWindowToImageFilter`, `vtkPNGWriter`, `vtkJPEGWriter` | `vtkmodules.vtkIOImage` |
| `vtkInteractorStyleTrackballCamera` | `vtkmodules.vtkInteractionStyle` |
| `vtkColorTransferFunction`, `vtkFloatArray` | `vtkmodules.vtkCommonDataModel` / `vtkCommonCore` |
| `vtkCommand` | `vtkmodules.vtkCommonCore` (re-exported) |
| `QVTKRenderWindowInteractor` | `vtkmodules.qt.QVTKRenderWindowInteractor` |
| OpenGL backend (`vtkRenderingOpenGL2`) | `vtkmodules.vtkRenderingOpenGL2` (Qt interactor pulls this) |

---

## 9. Verification Steps (confirm slimmed bundle still works)

Run these against the rebuilt `dist/quickice-gui/quickice-gui`. Do NOT modify
source — only validate the frozen binary.

### 9.1 CLI path (must not regress — no Qt/VTK/matplotlib needed at startup)

```bash
# 1. Help / version (exercises entry.py routing, argparse)
./dist/quickice-gui/quickice-gui --help
./dist/quickice-gui/quickice-gui --version

# 2. CLI pipeline end-to-end (exercises scipy.spatial.cKDTree + genice2 + numpy)
#    Use an existing example from scripts/cli-examples.sh
./dist/quickice-gui/quickice-gui --cli -T 270 -P 1 -N 256 --hydrate sI --guest ch4 -o /tmp/qi_out
#    Confirm .gro/.top written and no ModuleNotFoundError for scipy.spatial/genice2.

# 3. scipy exclusion sanity (the riskiest exclude):
./dist/quickice-gui/quickice-gui --cli -T 200 -P 1 -N 128 --interface -o /tmp/qi_iface
#    If this fails with 'No module named scipy.linalg/sparse/etc.', that's expected
#    and FINE — those were excluded. The failure mode to watch for is
#    'No module named scipy.spatial.ckdtree' (must NOT happen).
```

### 9.2 GUI path (Qt + matplotlib)

```bash
# 4. Headless GUI launch (offscreen Qt platform)
QT_QPA_PLATFORM=offscreen ./dist/quickice-gui/quickice-gui --gui &
GUIPID=$!
sleep 5
kill $GUIPID 2>/dev/null
#    Confirm: no 'No module named PySide6.Qt...' for KEPT modules (Widgets/Gui/Core).
#    A crash about QtNetwork/QtDBus being missing is FINE (we excluded them) only
#    if the app does not reach those code paths; watch for hard segfaults instead.

# 5. Phase diagram widget (matplotlib QtAgg backend)
#    Launch GUI, navigate to the phase-diagram tab; confirm the canvas renders.
#    Automated: run tests/test_hydrate_panel.py against the frozen binary's
#    environment if feasible, else manual.
```

### 9.3 VTK headless rendering (the highest-risk exclude area)

```bash
# 6. Force VTK in a no-display environment (simulates SSH X11):
unset DISPLAY
QT_QPA_PLATFORM=offscreen QUICKICE_FORCE_VTK=true \
  ./dist/quickice-gui/quickice-gui --gui &
#    Generate a hydrate (sI + ch4), confirm the 3D viewer populates
#    (no 'No module named vtkmodules.vtk*...' for KEPT modules).
#    If you see 'No module named vtkmodules.vtkIOImage' → you over-excluded;
#    remove vtkIOImage from _vtk_excludes (it's NOT in the proposed list, but
#    double-check no accidental over-exclusion of RenderingCore/OpenGL2).

# 7. PNG/JPEG export (exercises vtkWindowToImageFilter + vtkPNGWriter/vtkJPEGWriter):
#    In the GUI, use Export → PNG. Confirm a valid image is written.
#    This validates that vtkIOImage + vtkRenderingCore survived the excludes.

# 8. Mesa remote-GLX path:
DISPLAY=localhost:12.0 ./dist/quickice-gui/quickice-gui --gui &
#    Confirm __GLX_VENDOR_LIBRARY_NAME=mesa is set (main_window.py:2139) and
#    no NVIDIA-GLX segfault. (Requires an actual SSH -X session to fully test.)
```

### 9.4 Custom-guest hydrate (synthetic genice2.molecules module — §6.1 residual risk)

```bash
# 9. Build a hydrate with a CUSTOM guest (exercises custom_guest_bridge.py which
#    injects a synthetic genice2.molecules.<name> into sys.modules at runtime):
./dist/quickice-gui/quickice-gui --cli -T 270 -P 1 -N 256 --hydrate sI \
  --guest-custom /path/to/guest.gro -o /tmp/qi_custom
#    If this fails with a genice2 module-resolution error, the synthetic-module
#    path was not preserved — ensure collect_all('genice2') remains in the spec
#    and the genice2.molecules package dir is in datas/binaries.
```

### 9.5 Size verification (before/after diff)

```bash
du -sh dist/quickice-gui/ dist/quickice-gui/_internal/
du -sh dist/quickice-gui/_internal/{scipy,scipy.libs,vtkmodules,PySide6,numpy,matplotlib}
ls dist/quickice-gui/_internal/libvtk*.so* | wc -l   # should drop from 150
ls dist/quickice-gui/_internal/vtkmodules/*.so | wc -l  # should drop from 132
test ! -e dist/quickice-gui/_internal/_tk_data && echo "tk excluded OK"
test ! -e dist/quickice-gui/_internal/certifi && echo "leaks excluded OK"
```

---

## 10. Summary of Recommendations (prioritized)

1. **`strip=True` in EXE + COLLECT** (free, low-risk, ~80–120 MB unpacked). ★ easiest win.
2. **Exclude unused scipy submodules + `scipy.libs`** (~107 MB unpacked, biggest
   tar.gz win). Test `cKDTree` import after. Keep `scipy.spatial`, `scipy._lib`.
3. **Exclude Tcl/Tk** (`tkinter`, `_tkinter`) (~4 MB, zero risk — no tkinter use).
4. **Exclude leaked genice2-cif/MDAnalysis/gsw deps** + build in a clean env
   (`certifi`, `charset_normalizer`, `markupsafe`, …). Cleanliness + license fix.
5. **Exclude unused PySide6 Qt modules** (`QtNetwork`, `QtDBus`, WebEngine*, …).
6. **Exclude unused matplotlib backends** (gtk/wx/mac/tk/pdf/ps/svg/web/cairo).
7. **Conservative VTK I/O/web/parallel excludes** (~20–40 MB). Test PNG/JPEG
   export + 3D render; if `vtkmodules.all` breaks, revert VTK excludes and
   pursue §5.5 (code-level import narrowing) instead.
8. **`optimize=2`** (minor, strips docstrings).
9. **(Follow-up, code change) Narrow `from vtkmodules.all import` to targeted
   submodule imports** in `quickice/gui/` (13 files) — the single biggest
   *potential* lever (~140–160 MB unpacked), see §8.2/§8.3.
10. **Keep one-dir (COLLECT)** — do not switch to one-file.

**Projected outcome (Scenario A, spec-only):** ~600–660 MB unpacked /
~210–240 MB tar.gz (from 872 MB / 304 MB).
**Projected outcome (Scenario B, + VTK code narrowing):** ~440–520 MB unpacked /
~145–190 MB tar.gz.

---

*Analysis performed read-only. No code, `.spec`, or build scripts were modified.
All sizes measured against `dist/quickice-gui/` (build dated 2026-06-27) and
`dist/quickice-v4.5-linux-x86_64.tar.gz`. Sizes are approximate; re-measure after
any change.*
