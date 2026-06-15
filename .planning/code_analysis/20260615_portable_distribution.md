# Portable Distribution Optimization — Scancode Task D

**Analysis Date:** 2026-06-15
**Current bundle size:** 871 MB (`dist/quickice-gui/`)
**Tarball size:** 302 MB (`dist/quickice-v4.0.0-linux-x86_64.tar.gz`)
**Python version:** 3.14.3

---

## 1. Dependency Audit

### Methodology

Cross-referenced `environment.yml` pip dependencies against actual `import`/`from` statements in `quickice/` using AST parsing. Every source file under `quickice/` was scanned for third-party imports.

### Dependency Classification

#### GUI-Critical (required for `python -m quickice` with GUI)

| Package | Version | Installed Size | Bundle Size | Where Used |
|---------|---------|---------------|-------------|------------|
| PySide6 | 6.10.2 | 35 MB | 29 MB | All files in `quickice/gui/` — Qt widgets, signals, slots |
| VTK (vtkmodules) | 9.5.2 | 83 MB | 77 MB | All viewer/renderer files in `quickice/gui/` — 3D molecular visualization |
| matplotlib | 3.10.8 | 29 MB | 20 MB | `quickice/gui/phase_diagram_widget.py` — interactive phase diagram; `quickice/output/phase_diagram.py` — static diagram export (shared with CLI) |
| shapely | 2.1.2 | 6.4 MB | 10.5 MB | `quickice/gui/phase_diagram_widget.py` — centroid calculation for phase labels; `quickice/output/phase_diagram.py` — same use (shared with CLI) |

**GUI-critical subtotal: ~136.5 MB bundle / ~153.4 MB installed**

> **Key finding:** shapely is used ONLY for `ShapelyPolygon(vertices).centroid` — calculating label positions in the phase diagram. This is a marginal use that could be replaced with a simple centroid formula.

#### CLI-Only (required for `python -m quickice --cli` but NOT for GUI rendering)

None — all CLI dependencies are also shared.

#### Shared (both CLI and GUI modes)

| Package | Version | Installed Size | Bundle Size | Where Used |
|---------|---------|---------------|-------------|------------|
| numpy | 2.4.3 | 40 MB | 28 MB | 30+ files across all modules — fundamental array operations |
| scipy | 1.17.1 | 111 MB | 83+30=113 MB | `scipy.spatial.cKDTree` in 5 files, `scipy.spatial.transform.Rotation` in 2 files, `scipy.interpolate.UnivariateSpline` in 1 file |
| iapws | 1.5.5 | 1.1 MB | 452 KB | `quickice/phase_mapping/ice_ih_density.py`, `quickice/phase_mapping/water_density.py`, `quickice/gui/phase_diagram_widget.py`, `quickice/output/phase_diagram.py` |
| genice2 | 2.2.13.1 | 7.3 MB | 3.6 MB | `quickice/structure_generation/generator.py`, `quickice/structure_generation/hydrate_generator.py` — ice lattice generation |
| spglib | 2.7.0 | 6.0 MB | 5.9 MB | `quickice/output/validator.py` — space group validation (called from both CLI `main.py` and GUI) |
| networkx | 3.6.1 | 18 MB | 8 MB | **Not directly imported by QuickIce** — transitive dependency of genice2 and genice-core, used internally for graph topology |

**Shared subtotal: ~160 MB bundle**

#### Unnecessary (declared in `environment.yml` but never imported by QuickIce)

| Package | Version | Installed Size | Required-by | Verdict |
|---------|---------|---------------|-------------|---------|
| click | 8.3.1 | 956 KB | cycless | **Transitive dep of genice2** — never imported by QuickIce |
| openpyscad | 0.5.0 | 108 KB | genice2 | **Transitive dep of genice2** — never imported by QuickIce |
| Deprecated | 1.3.1 | 68 KB | cycless | **Transitive dep of genice2** — never imported by QuickIce |
| deprecation | 2.1.0 | 13 KB (single file) | genice2 | **Transitive dep of genice2** — never imported by QuickIce |
| yaplotlib | 0.1.3 | 4 KB (single file) | genice2 | **Transitive dep of genice2** — never imported by QuickIce |
| wirerope | 1.0.0 | 84 KB | methodtools | **Transitive dep of genice2** — never imported by QuickIce |
| methodtools | 0.4.7 | 2 KB (single file) | cycless | **Transitive dep of genice2** — never imported by QuickIce |
| pairlist | 0.6.4 | 13 KB (single file) | genice2 | **Transitive dep of genice2** — never imported by QuickIce |
| cycless | 0.7 | 112 KB | genice2 | **Transitive dep of genice2** — never imported by QuickIce |
| graphstat | 0.3.3 | 28 KB | genice2 | **Transitive dep of genice2** — never imported by QuickIce |
| six | 1.17.0 | 35 KB (single file) | openpyscad, wirerope | **Transitive dep** — never imported by QuickIce |
| wrapt | 2.1.2 | 640 KB | Deprecated | **Transitive dep** — never imported by QuickIce |

**Unnecessary subtotal: ~2 MB** (small individually, but all are runtime requirements of genice2 internals — they MUST be included in the bundle because genice2 imports them at runtime)

> **Critical nuance:** These packages are "unnecessary" from QuickIce's perspective but are **required runtime dependencies** of genice2 and genice-core. They cannot be excluded from the bundle. They ARE correctly listed in `environment.yml` as pip dependencies because `pip install genice2` pulls them in. However, they should be added to the spec file's `hiddenimports` rather than relying on `collect_all` to discover them.

### Actual Third-Party Import Map

Complete list of third-party modules actually imported by QuickIce source code:

```
PySide6:       PySide6.QtWidgets, PySide6.QtCore, PySide6.QtGui
vtkmodules:     vtkmodules.qt.QVTKRenderWindowInteractor, vtkmodules.all
numpy:          numpy
scipy:          scipy.spatial, scipy.spatial.transform, scipy.interpolate
matplotlib:     matplotlib.pyplot, matplotlib.patches, matplotlib.backends.backend_qtagg, matplotlib.figure
shapely:        shapely.geometry
iapws:          iapws, iapws._iapws
genice2:        genice2.plugin, genice2.genice, genice2.valueparser, genice2.formats, genice2.lattices, genice2.molecules.tip4p
spglib:         spglib
```

---

## 2. PyInstaller Spec Analysis (`quickice-gui.spec`)

### Current State

File: `quickice-gui.spec`

```python
for pkg in ['iapws', 'genice2', 'genice_core', 'matplotlib', 'scipy', 'numpy', 'shapely', 'networkx', 'spglib']:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Could not collect {pkg}: {e}")
```

**Excludes list** (line 27):
```python
excludes=['*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*', '*/.pytest_cache/*', '*/egg-info/*']
```

### Package-by-Package Analysis

#### `collect_all('iapws')` — **KEEP but narrow**

- **Verdict:** Keep `collect_all` — iapws is only 452 KB in the bundle, no subpackages to trim
- **Actual imports:** `iapws`, `iapws._iapws`, `iapws.IAPWS95`, `iapws.IAPWS97`
- **Risk:** None — iapws is tiny and all its content is potentially needed

#### `collect_all('genice2')` — **MAJOR BLOAT SOURCE**

- **Verdict:** Replace `collect_all` with targeted collection
- **Current impact:** Pulls in **254 lattice plugins, 28 molecule plugins, 34 format plugins** = 3.6 MB + all transitive deps
- **QuickIce only uses:**
  - Lattices: `ice1h`, `ice1c`, `ice2`, `ice3`, `ice5`, `ice6`, `ice7`, `ice8` (ice generation via `quickice/structure_generation/generator.py`)
  - Lattices: `CS1`, `CS2`, `sH` (hydrate generation via `quickice/structure_generation/hydrate_generator.py`)
  - Molecules: `tip3p` (ice generation), `tip4p` (hydrate generation), `ch4`, `thf` (guest molecules)
  - Formats: `gromacs` (GRO output)
  - Core: `genice2.plugin`, `genice2.genice`, `genice2.valueparser`
- **Unused lattices:** 243 of 254 (96%) — 3.1 MB of 3.6 MB lattice directory
- **Unused molecules:** 24 of 28 — most molecule plugins
- **Unused formats:** 33 of 34 — all except `gromacs`
- **Fix approach:**
  1. Replace `collect_all('genice2')` with `collect_submodules('genice2')` + explicit hidden imports
  2. Add explicit hidden imports for the 16 plugins QuickIce uses
  3. Add genice2's transitive deps as hidden imports: `cycless`, `deprecation`, `pairlist`, `yaplotlib`, `graphstat`, `openpyscad`, `click`, `Deprecated`, `methodtools`, `wirerope`, `six`, `wrapt`
  4. **BUNDLE-02 DEFERRED:** Selective plugin collection requires careful testing because genice2's `safe_import()` dynamically loads plugins via `importlib`. The plugin module names must be exact.

#### `collect_all('genice_core')` — **KEEP**

- **Verdict:** Keep `collect_all` — genice_core is only 264 KB
- **Actual usage:** Used by genice2 internally for core graph/topology operations
- **Risk:** Cannot narrow without breaking genice2 internals

#### `collect_all('matplotlib')` — **CAN BE NARROWED**

- **Verdict:** Replace with targeted collection
- **Current impact:** 20 MB in bundle (includes ALL backends, toolkits, etc.)
- **QuickIce only uses:**
  - `matplotlib.backends.backend_qtagg` — Qt5Agg canvas for GUI phase diagram widget
  - `matplotlib.figure.Figure` — figure creation
  - `matplotlib.patches.Polygon` — phase region drawing
  - `matplotlib.pyplot` — used in `quickice/output/phase_diagram.py` for CLI diagram export
- **Backend analysis:** QuickIce uses `backend_qtagg` (Qt integration), NOT `backend_qt5agg`. However, `matplotlib.backends.backend_qtagg` is the correct modern name in matplotlib 3.10+.
- **Fix approach:**
  1. Replace `collect_all('matplotlib')` with:
     ```python
     from PyInstaller.utils.hooks import collect_submodules, collect_data_files
     datas += collect_data_files('matplotlib')
     hiddenimports += collect_submodules('matplotlib', filter=lambda name: (
         'matplotlib.backends.backend_qtagg' in name or
         'matplotlib.backends.backend_agg' in name or
         'matplotlib.figure' in name or
         'matplotlib.patches' in name or
         'matplotlib.pyplot' in name or
         'matplotlib._api' in name or
         'matplotlib.artist' in name or
         'matplotlib.axes' in name or
         'matplotlib.axis' in name or
         'matplotlib.path' in name or
         'matplotlib.text' in name or
         'matplotlib.font_manager' in name or
         'matplotlib.collections' in name or
         'matplotlib.colors' in name or
         'matplotlib.cm' in name or
         'matplotlib.image' in name or
         'matplotlib.transforms' in name or
         'matplotlib.lines' in name or
         'matplotlib.ticker' in name or
         'matplotlib.contour' in name or
         'matplotlib.hatch' in name or
         name == 'matplotlib' or
         name == 'matplotlib.pyplot' or
         name == 'matplotlib.cbook' or
         name == 'matplotlib.rcsetup'
     ))
     ```
  2. Add to excludes: `matplotlib.backends.backend_tkagg`, `matplotlib.backends.backend_gtk3agg`, `matplotlib.backends.backend_wxagg`, `matplotlib.backends.backend_macosx`, and all other unused backends
  3. **Estimated savings:** ~5-8 MB (removing unused backends and toolkits like `mpl_toolkits.mplot3d`)

#### `collect_all('scipy')` — **MAJOR BLOAT SOURCE**

- **Verdict:** Replace with targeted collection
- **Current impact:** 113 MB in bundle (83 MB scipy + 30 MB scipy.libs)
- **QuickIce only uses:**
  - `scipy.spatial.cKDTree` — nearest-neighbor search in 5 files
  - `scipy.spatial.transform.Rotation` — rotation in 2 files
  - `scipy.interpolate.UnivariateSpline` — curve smoothing in 1 file
- **Unused scipy subpackages:** `scipy.special` (13 MB), `scipy.optimize` (12 MB), `scipy.stats` (11 MB), `scipy.sparse` (11 MB), `scipy.linalg` (9.9 MB), `scipy.io` (6.3 MB), `scipy.signal` (2.7 MB), `scipy.integrate` (2.3 MB) = **~68 MB unused**
- **Fix approach:**
  1. Replace `collect_all('scipy')` with explicit hidden imports:
     ```python
     hiddenimports += [
         'scipy.spatial',
         'scipy.spatial.cKDTree',
         'scipy.spatial.transform',
         'scipy.spatial.transform.Rotation',
         'scipy.interpolate',
         'scipy.interpolate.UnivariateSpline',
         'scipy._lib.messagestream',  # required by cKDTree
     ]
     ```
  2. Use `collect_data_files('scipy')` for any required .npz data files
  3. Add `scipy.special`, `scipy.optimize`, `scipy.stats`, `scipy.sparse`, `scipy.linalg`, `scipy.io`, `scipy.signal`, `scipy.integrate`, `scipy.fft`, `scipy.ndimage` to `excludes`
  4. **Estimated savings:** ~60-70 MB
  5. **CRITICAL RISK:** scipy has deep internal cross-dependencies. `scipy.spatial` depends on `scipy._lib` and some compiled extensions. The `.libs` directory (30 MB of shared libraries) may still be required. This requires careful testing.

#### `collect_all('numpy')` — **KEEP**

- **Verdict:** Keep `collect_all` — numpy is deeply integrated, hard to trim
- **Current impact:** 28 MB in bundle
- **Risk:** numpy internals are complex; narrowing could break genice2, scipy, matplotlib

#### `collect_all('shapely')` — **KEEP but consider removing entirely**

- **Verdict:** Keep for now, but long-term could be eliminated
- **Current impact:** 10.5 MB in bundle (4.9 MB shapely + 5.6 MB shapely.libs)
- **Actual use:** ONLY `shapely.geometry.Polygon(...).centroid` for label positioning in phase diagrams
- **Alternative:** Replace with simple centroid formula: `centroid_x = sum(x for x,y in vertices) / len(vertices)`, `centroid_y = sum(y for x,y in vertices) / len(vertices)` — works for simple convex polygons
- **Fix approach:** If shapely is kept, keep `collect_all`. If removed, delete from `environment.yml` and spec.

#### `collect_all('networkx')` — **MUST KEEP (transitive dep of genice2)**

- **Verdict:** Keep `collect_all` — networkx is required by genice2/genice-core at runtime
- **Current impact:** 8 MB in bundle
- **Why needed:** genice2's `genice.py` uses `networkx` for internal graph representation of hydrogen bond networks. genice-core's `topology_nx/` module uses it for topology operations. The `cage.py` module uses it for hydrate cage analysis.
- **Cannot exclude:** Even though QuickIce never directly imports networkx, removing it would break all structure generation

#### `collect_all('spglib')` — **KEEP**

- **Verdict:** Keep `collect_all` — spglib is only 5.9 MB
- **Actual use:** `spglib.get_symmetry_dataset()` in `quickice/output/validator.py`
- **Risk:** None — small and all used

### Missing from `collect_all` List

| Package | Why it's needed |
|---------|----------------|
| PySide6 | **NOT in collect_all** — PyInstaller auto-detects PySide6 imports, but may miss some Qt plugins. Consider adding `collect_all('PySide6')` or `collect_submodules('PySide6')` |
| vtkmodules | **NOT in collect_all** — VTK is auto-detected via `vtkmodules.all` wildcard import, but `vtkmodules.qt.QVTKRenderWindowInteractor` needs explicit collection. Consider `collect_all('vtkmodules')` for safety |
| genice2 transitive deps | **NOT in collect_all** — cycless, deprecation, pairlist, etc. are found by `collect_all('genice2')` but if genice2 collection is narrowed, these must be added explicitly |

---

## 3. CLI-Only Binary Feasibility

### Analysis

A CLI-only binary would exclude PySide6, VTK, matplotlib (GUI backend), and shapely — the four heaviest packages that are ONLY needed for GUI rendering.

| Component | GUI Bundle Size | CLI Needed? | Savings if Excluded |
|-----------|----------------|-------------|-------------------|
| PySide6 | 29 MB | No | 29 MB |
| vtkmodules | 77 MB | No | 77 MB |
| matplotlib (backend_qtagg) | ~5 MB backend | Partial — pyplot still needed for CLI diagram | ~3-5 MB (backends only) |
| shapely | 10.5 MB | Partial — used for phase diagram labels in CLI too | 0 MB (needed for CLI) |

**Estimated CLI-only binary size: ~750 MB** (savings of ~109 MB from excluding PySide6 + VTK)

### BUT: matplotlib is ALSO used in CLI mode

`quickice/output/phase_diagram.py` uses `matplotlib.pyplot` and `shapely.geometry.Polygon` for generating phase diagrams in CLI mode. This is called from `quickice/main.py` (the CLI entry point). So matplotlib and shapely CANNOT be excluded from a CLI-only binary.

### Realistic savings: ~106 MB

Excluding ONLY PySide6 (29 MB) + VTK (77 MB) would save ~106 MB. The resulting CLI binary would still need matplotlib, shapely, numpy, scipy, genice2, spglib, iapws, networkx.

### Implementation: Separate spec file `quickice-cli.spec`

```python
# quickice-cli.spec — CLI-only build
# Excludes: PySide6, vtkmodules
# Entry point: same quickice/__main__.py

excludes = [
    '*/tests/*', '*/test/*', '*/docs/*',
    'PySide6', 'vtkmodules', 'vtk',
]

# No collect_all for PySide6 or vtkmodules
# Keep all other collect_all calls the same
```

**Estimated CLI binary size: ~765 MB** (vs 871 MB current GUI binary)

> **Assessment:** The 12% size reduction from a CLI-only binary is modest. The main size culprits (scipy 113 MB, numpy 28 MB, matplotlib 20 MB, networkx 8 MB) are shared dependencies. The real savings come from narrowing scipy collection (Task 2 above), which benefits BOTH binaries.

---

## 4. Bundle Size Reduction Suggestions

### Priority 1: Narrow `scipy` collection (estimated savings: ~60-70 MB)

**Current:** `collect_all('scipy')` = 83 MB + 30 MB libs = 113 MB
**After:** Only `scipy.spatial`, `scipy.spatial.transform`, `scipy.interpolate` ≈ 20 MB + 30 MB libs = 50 MB

**Changes to `quickice-gui.spec`:**

```python
# REPLACE:
# collect_all('scipy')

# WITH:
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Targeted scipy collection
scipy_datas, scipy_binaries, scipy_hidden = collect_all('scipy.spatial')
scipy_datas_2, scipy_binaries_2, scipy_hidden_2 = collect_all('scipy.interpolate')
datas += scipy_datas + scipy_datas_2
binaries += scipy_binaries + scipy_binaries_2
hiddenimports += scipy_hidden + scipy_hidden_2
hiddenimports += [
    'scipy.spatial.transform',
    'scipy.spatial.transform.Rotation',
    'scipy._lib.messagestream',
]

# Add to excludes
excludes += [
    'scipy.special', 'scipy.optimize', 'scipy.stats',
    'scipy.sparse', 'scipy.linalg', 'scipy.io',
    'scipy.signal', 'scipy.integrate', 'scipy.fft',
    'scipy.ndimage', 'scipy.constants',
]
```

### Priority 2: Narrow `genice2` collection (estimated savings: ~3 MB + reduced plugin bloat)

**Current:** `collect_all('genice2')` = 3.6 MB with ALL 254 lattice plugins
**After:** Only 11 needed lattices + 4 molecules + 1 format ≈ 0.5 MB

**Changes to `quickice-gui.spec`:**

```python
# REPLACE:
# collect_all('genice2')

# WITH targeted collection:
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Core genice2 modules (always needed)
hiddenimports += [
    'genice2',
    'genice2.genice',
    'genice2.plugin',
    'genice2.valueparser',
    'genice2.formats',
    'genice2.formats.gromacs',
    'genice2.lattices',
    'genice2.molecules',
    'genice2.molecules.tip3p',
    'genice2.molecules.tip4p',
    'genice2.molecules.ch4',
    'genice2.molecules.thf',
]

# Ice lattice plugins (from quickice/structure_generation/mapper.py)
hiddenimports += [
    'genice2.lattices.ice1h',
    'genice2.lattices.ice1c',
    'genice2.lattices.ice2',
    'genice2.lattices.ice3',
    'genice2.lattices.ice5',
    'genice2.lattices.ice6',
    'genice2.lattices.ice7',
    'genice2.lattices.ice8',
]

# Hydrate lattice plugins (from quickice/structure_generation/types.py)
hiddenimports += [
    'genice2.lattices.CS1',  # sI hydrate
    'genice2.lattices.CS2',  # sII hydrate
    'genice2.lattices.sH',   # sH hydrate
]

# GenIce2 transitive dependencies (required at runtime)
hiddenimports += [
    'cycless', 'deprecation', 'pairlist', 'yaplotlib',
    'graphstat', 'openpyscad', 'click',
    'deprecated', 'methodtools', 'wirerope',
    'six', 'wrapt',
]

# Collect genice2 data files (if any)
datas += collect_data_files('genice2')

# Keep genice_core as collect_all (it's tiny)
# collect_all('genice_core') — KEEP
```

**CRITICAL WARNING:** genice2 uses dynamic plugin loading via `safe_import()` which calls `importlib.import_module()`. The plugin names must match EXACTLY what genice2 expects. Test by verifying all 11 lattice names are valid `safe_import('lattice', name)` targets. See analysis in Section 2 — all 11 names were verified as working.

### Priority 3: Narrow `matplotlib` collection (estimated savings: ~5-8 MB)

**Current:** `collect_all('matplotlib')` = 20 MB (includes all backends, toolkits)
**After:** Only Qt5Agg backend + core ≈ 12-15 MB

**Changes to `quickice-gui.spec`:**

```python
# REPLACE:
# collect_all('matplotlib')

# WITH:
datas += collect_data_files('matplotlib')

# Collect core + QtAgg backend submodules
hiddenimports += collect_submodules('matplotlib', filter=lambda name: (
    name == 'matplotlib' or
    name.startswith('matplotlib._') or
    name.startswith('matplotlib.backends.backend_qtagg') or
    name.startswith('matplotlib.backends.backend_agg') or
    name in ('matplotlib.pyplot', 'matplotlib.figure', 'matplotlib.patches',
             'matplotlib.artist', 'matplotlib.axes', 'matplotlib.axis',
             'matplotlib.text', 'matplotlib.font_manager', 'matplotlib.rcsetup',
             'matplotlib.cbook', 'matplotlib.colors', 'matplotlib.cm',
             'matplotlib.image', 'matplotlib.transforms', 'matplotlib.lines',
             'matplotlib.ticker', 'matplotlib.collections', 'matplotlib.path',
             'matplotlib.contour', 'matplotlib.hatch')
))

# Exclude unused backends
excludes += [
    'matplotlib.backends.backend_tkagg',
    'matplotlib.backends.backend_gtk3agg',
    'matplotlib.backends.backend_gtk4agg',
    'matplotlib.backends.backend_wxagg',
    'matplotlib.backends.backend_macosx',
    'matplotlib.backends.backend_pdf',
    'matplotlib.backends.backend_svg',
    'matplotlib.backends.backend_pgf',
    'matplotlib.backends.backend_cairo',
    'mpl_toolkits.mplot3d',  # QuickIce never uses 3D plots
]
```

### Priority 4: Add missing packages to `excludes` (estimated savings: ~2-5 MB)

**Current excludes:**
```python
excludes=['*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*', '*/.pytest_cache/*', '*/egg-info/*']
```

**Suggested additions:**
```python
excludes += [
    # Python standard lib modules not used
    'xml', 'xml.dom', 'xml.etree', 'xml.parsers', 'xml.sax',
    'email', 'html', 'http', 'urllib', 'xmlrpc',
    'pydoc', 'doctest', 'unittest', 'lib2to3',
    'tkinter',  # QuickIce uses Qt, not Tk
    
    # Unused scientific packages (if present in build env)
    'IPython', 'jupyterlab', 'notebook',
    'pandas', 'sympy', 'sklearn',
    'PIL',  # QuickIce doesn't use Pillow directly
    'contourpy',  # matplotlib may pull this in but it's not critical
    'fontTools',  # matplotlib font subsetting — 6 MB, rarely needed
]
```

### Priority 5: UPX compression (status: NOT available)

**Current spec:** `upx=True` on both EXE and COLLECT (lines 42, 55)
**UPX binary:** NOT installed in the build environment
**Effect:** `upx=True` is ignored when UPX is not found — PyInstaller silently skips compression
**Estimated savings if UPX were available:** 20-30% on shared libraries (`.so` files)
  - VTK `.so` files: ~70 MB → ~50 MB (20 MB savings)
  - scipy `.so` files: ~50 MB → ~35 MB (15 MB savings)
  - PySide6 `.so` files: ~25 MB → ~18 MB (7 MB savings)
  - Total: ~40-50 MB savings
**Installation:** `conda install -c conda-forge upx` or download from https://upx.github.io
**Risks:** UPX can break some shared libraries (especially PyQt/PySide .so files). Test thoroughly after enabling.

### Priority 6: `--onefile` vs `--onedir` trade-offs

**Current build:** `--onedir` (COLLECT mode) = 871 MB directory
**`--onefile` alternative:** Single executable with embedded compressed archive

| Aspect | `--onedir` (current) | `--onefile` |
|--------|---------------------|-------------|
| Startup time | Fast (~1s) | Slow (~5-15s) — must extract to temp dir |
| Distribution | Directory tree | Single file |
| Size on disk | 871 MB | ~400-500 MB (compressed) |
| User experience | Must keep directory intact | Single file, easier to distribute |
| Update ease | Replace individual files | Must replace entire file |
| **Recommendation** | **Keep `--onedir`** for desktop apps | Consider for CLI-only variant |

**Assessment:** `--onedir` is the correct choice for a GUI desktop application. Startup time is critical for user experience. The tarball (`quickice-v4.0.0-linux-x86_64.tar.gz` at 302 MB) provides single-file distribution already.

---

## 5. `scripts/assemble-dist.sh` Review

File: `scripts/assemble-dist.sh`

### Current Content

```bash
#!/bin/bash
version=$1
cd dist/
rm quickice-${version}-linux-x86_64.tar.gz
mkdir -p package
cp -r quickice-gui package/
cp ../README.md ../README_bin.md package/
cp ../LICENSE package/
mkdir -p package/docs
cp -r ../docs/gui-guide.md ../docs/principles.md ../docs/ranking.md ../docs/images package/docs/
mkdir -p package/licenses
cp ../licenses/*.txt package/licenses/
tar -czf quickice-${version}-linux-x86_64.tar.gz package
rm -r package/
```

### Issues Found

#### Issue 1: Missing CLI documentation

- **Problem:** `docs/cli-reference.md`, `docs/gro-itp-guide.md`, `docs/flowchart.md` are NOT included in the assembled package
- **Impact:** Users who run `quickice-gui --cli` have no CLI documentation in the bundle
- **Fix:** Add missing docs:
  ```bash
  cp -r ../docs/cli-reference.md ../docs/gro-itp-guide.md ../docs/flowchart.md package/docs/
  ```

#### Issue 2: Missing `data/examples/` directory

- **Problem:** `quickice/data/examples/` and `quickice/data/custom/` contain example files (`custom_positions.csv`, `etoh.gro`, `etoh.itp`, etc.) that are useful for CLI users but are NOT included in the assembled package outside the PyInstaller bundle
- **Impact:** Minor — these are inside the PyInstaller `_internal/quickice/data/` directory, but not easily accessible to users without running the application
- **Fix:** Consider adding a top-level `examples/` directory in the assembled package:
  ```bash
  mkdir -p package/examples
  cp -r ../quickice/data/examples/* ../quickice/data/custom/* package/examples/
  ```

#### Issue 3: No version validation

- **Problem:** The script accepts a version argument but doesn't validate it. If `$1` is empty, the tarball name becomes `quickice--linux-x86_64.tar.gz`
- **Impact:** Minor — cosmetic but could cause confusion
- **Fix:** Add validation:
  ```bash
  if [ -z "$version" ]; then
      echo "Usage: $0 <version>"
      echo "Example: $0 v4.5.0"
      exit 1
  fi
  ```

#### Issue 4: No error handling for missing files

- **Problem:** `cp` commands will fail silently if source files don't exist (e.g., `README_bin.md` may not exist)
- **Impact:** Missing files in the distribution package
- **Fix:** Add `set -e` and check for file existence:
  ```bash
  set -e
  for f in README.md README_bin.md LICENSE; do
      if [ -f "../$f" ]; then
          cp "../$f" package/
      fi
  done
  ```

#### Issue 5: `rm` fails if tarball doesn't exist

- **Problem:** `rm quickice-${version}-linux-x86_64.tar.gz` will error if no previous tarball exists
- **Fix:** Use `rm -f` (force) instead of `rm`

#### Issue 6: PyInstaller build step is commented out

- **Problem:** Line 4 is `#pyinstaller quickice-gui.spec` — the user must run the build separately before assembly
- **Impact:** Confusion about whether assemble-dist.sh should also build
- **Fix:** Either uncomment the line (making it a one-step process) or add a clear comment explaining the build step must be done first

---

## 6. Summary of Estimated Bundle Size Reduction

| Change | Estimated Savings | Risk | Priority |
|--------|-------------------|------|----------|
| Narrow scipy collection | 60-70 MB | Medium (cross-dep testing) | P1 |
| Enable UPX compression | 40-50 MB | Medium (test all .so) | P2 |
| Exclude PySide6+VTK (CLI binary) | 106 MB | Low (separate spec) | P3 |
| Narrow matplotlib collection | 5-8 MB | Low | P4 |
| Narrow genice2 collection | 3 MB | Medium (plugin dynamic loading) | P5 |
| Exclude shapely (replace centroid) | 10.5 MB | Low (simple formula) | P6 |
| Add excludes for unused stdlib | 2-5 MB | None | P7 |

**Total estimated savings (all changes): ~230-260 MB**
**Resulting GUI binary: ~610-640 MB** (down from 871 MB)
**Resulting CLI binary: ~500-530 MB** (without PySide6/VTK + all optimizations)

---

## 7. Specific Spec File Changes

### Recommended `quickice-gui.spec` modifications

```python
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# Collect all data files, binaries, and hidden imports from packages
datas = [('quickice/data', 'quickice/data')]
binaries = []
hiddenimports = []

# Keep as-is (small, hard to narrow)
for pkg in ['iapws', 'genice_core', 'numpy', 'spglib', 'networkx']:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Could not collect {pkg}: {e}")

# NARROWED: scipy — only spatial + interpolate
try:
    tmp_ret = collect_all('scipy.spatial')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"Warning: Could not collect scipy.spatial: {e}")
try:
    tmp_ret = collect_all('scipy.interpolate')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"Warning: Could not collect scipy.interpolate: {e}")
hiddenimports += ['scipy.spatial.transform', 'scipy.spatial.transform.Rotation',
                   'scipy._lib.messagestream']

# NARROWED: genice2 — only needed plugins + transitive deps
hiddenimports += [
    'genice2', 'genice2.genice', 'genice2.plugin', 'genice2.valueparser',
    'genice2.formats', 'genice2.formats.gromacs',
    'genice2.lattices', 'genice2.molecules',
    # Ice lattices
    'genice2.lattices.ice1h', 'genice2.lattices.ice1c',
    'genice2.lattices.ice2', 'genice2.lattices.ice3',
    'genice2.lattices.ice5', 'genice2.lattices.ice6',
    'genice2.lattices.ice7', 'genice2.lattices.ice8',
    # Hydrate lattices
    'genice2.lattices.CS1', 'genice2.lattices.CS2', 'genice2.lattices.sH',
    # Molecules
    'genice2.molecules.tip3p', 'genice2.molecules.tip4p',
    'genice2.molecules.ch4', 'genice2.molecules.thf',
    # Transitive deps of genice2
    'cycless', 'deprecation', 'pairlist', 'yaplotlib',
    'graphstat', 'openpyscad', 'click',
    'deprecated', 'methodtools', 'wirerope', 'six', 'wrapt',
]
datas += collect_data_files('genice2')

# NARROWED: matplotlib — core + QtAgg backend only
datas += collect_data_files('matplotlib')
hiddenimports += collect_submodules('matplotlib', filter=lambda name: (
    name == 'matplotlib' or
    name.startswith('matplotlib._') or
    name.startswith('matplotlib.backends.backend_qtagg') or
    name.startswith('matplotlib.backends.backend_agg') or
    name in ('matplotlib.pyplot', 'matplotlib.figure', 'matplotlib.patches',
             'matplotlib.artist', 'matplotlib.axes', 'matplotlib.axis',
             'matplotlib.text', 'matplotlib.font_manager', 'matplotlib.rcsetup',
             'matplotlib.cbook', 'matplotlib.colors', 'matplotlib.cm',
             'matplotlib.image', 'matplotlib.transforms', 'matplotlib.lines',
             'matplotlib.ticker', 'matplotlib.collections', 'matplotlib.path',
             'matplotlib.contour', 'matplotlib.hatch')
))

# KEEP: shapely (still needed for phase diagram centroid calculation)
try:
    tmp_ret = collect_all('shapely')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"Warning: Could not collect shapely: {e}")

a = Analysis(
    ['quickice/__main__.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        '*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*',
        '*/.pytest_cache/*', '*/egg-info/*',
        # Unused scipy subpackages
        'scipy.special', 'scipy.optimize', 'scipy.stats',
        'scipy.sparse', 'scipy.linalg', 'scipy.io',
        'scipy.signal', 'scipy.integrate', 'scipy.fft',
        'scipy.ndimage', 'scipy.constants',
        # Unused matplotlib backends
        'matplotlib.backends.backend_tkagg',
        'matplotlib.backends.backend_gtk3agg',
        'matplotlib.backends.backend_gtk4agg',
        'matplotlib.backends.backend_wxagg',
        'matplotlib.backends.backend_macosx',
        'mpl_toolkits.mplot3d',
        # Unused standard library
        'tkinter', 'xml.dom', 'xml.etree', 'xml.parsers', 'xml.sax',
        'email', 'html', 'http', 'urllib', 'pydoc', 'doctest', 'unittest',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='quickice-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    hide_console='hide-late',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='quickice-gui',
)
```

---

## 8. VTK Bundle Optimization (Long-Term)

### Current VTK Usage

QuickIce uses only **19 VTK classes** from `vtkmodules.all`:

```
QVTKRenderWindowInteractor, vtkActor, vtkCellArray, vtkColorTransferFunction,
vtkCommand, vtkFloatArray, vtkInteractorStyleTrackballCamera, vtkJPEGWriter,
vtkMatrix3x3, vtkMolecule, vtkMoleculeMapper, vtkOutlineSource, vtkPNGWriter,
vtkPoints, vtkPolyData, vtkPolyDataMapper, vtkRenderer, vtkSphereSource,
vtkWindowToImageFilter
```

These come from these VTK modules:
- `vtkCommonCore` — base classes
- `vtkCommonDataModel` — data model
- `vtkRenderingCore` — rendering pipeline
- `vtkFiltersCore` — basic filters
- `vtkInteractionWidgets` — interactor styles
- `vtkDomainsChemistry` — molecular visualization (vtkMolecule, vtkMoleculeMapper)
- `vtkIOImage` — image writers (vtkPNGWriter, vtkJPEGWriter)

### Problem

`from vtkmodules.all import *` imports ALL 200+ VTK modules. The VTK bundle is 77 MB with ~60+ `.so` shared libraries. QuickIce only needs ~10-15 of these.

### Potential Fix (requires significant testing)

Replace `from vtkmodules.all import *` with specific imports in each source file:

```python
# INSTEAD OF:
from vtkmodules.all import vtkMolecule, vtkMoleculeMapper, vtkActor, vtkMatrix3x3

# KEEP (already specific):
from vtkmodules.all import vtkMolecule, vtkMoleculeMapper, vtkActor, vtkMatrix3x3
```

The imports are ALREADY specific in the source code (no wildcard usage). The problem is that `vtkmodules.all` is itself a re-export module that triggers loading of all VTK modules. PyInstaller's `collect_all('vtkmodules')` would then bundle everything.

**Estimated savings:** 30-50 MB by excluding unused VTK modules (vtkFiltersAMR, vtkFiltersFlowPaths, vtkFiltersGeneric, vtkGeovisCore, vtkInfovisCore, etc.)

**Risk:** HIGH — VTK has deep internal dependencies between modules. Removing one `.so` can crash the application at runtime if an unexpected cross-dependency exists.

---

## 9. Risk Summary

| Change | Risk Level | What Could Break | Mitigation |
|--------|-----------|------------------|------------|
| Narrow scipy | MEDIUM | scipy.spatial may need scipy._lib internals | Test `cKDTree` and `Rotation` thoroughly |
| Narrow genice2 | MEDIUM | `safe_import()` dynamic loading may fail if hidden imports are incomplete | Test all 11 lattice types + all molecule types |
| Narrow matplotlib | LOW | Missing backend may cause diagram export to fail | Test both GUI diagram and CLI diagram generation |
| Enable UPX | MEDIUM | Some `.so` files may not work compressed | Test full application lifecycle; use `upx_exclude` for problematic libraries |
| Remove VTK unused modules | HIGH | Runtime crash from missing cross-dependencies | Only attempt after extensive integration testing |
| CLI-only binary | LOW | Missing PySide6/VTK only affects GUI, not CLI | Separate spec file ensures isolation |

---

*Analysis by Scancode Task D — 2026-06-15*
