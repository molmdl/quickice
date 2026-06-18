# Portable Distribution Delta Analysis — Scancode D

**Analysis Date:** 2026-06-18
**Delta from:** 2026-06-15 scan (`.planning/code_analysis/20260615_portable_distribution.md`, 816 lines)
**Current bundle size:** 871 MB (`dist/quickice-gui/`) — UNCHANGED
**Tarball size:** 302 MB (`dist/quickice-v4.0.0-linux-x86_64.tar.gz`) — UNCHANGED (289 MB measured)
**Python version:** 3.14.3

---

## Delta Summary

| Category | Status | Detail |
|----------|--------|--------|
| New runtime dependencies | **NONE** | Phase 34.9/37.1 added no new third-party imports |
| `quickice-gui.spec` changes | **NONE** | Last modified 2026-06-15 (same day as previous scan) |
| `scripts/assemble-dist.sh` changes | **NONE** | Last modified 2026-04-07 |
| `environment.yml` changes | **NONE** | Last modified 2026-04-04 |
| `quickice/data/` changes | **NONE** | No new data files since June 15 |
| Bundle size | **UNCHANGED** | 871 MB directory, 842 MB `_internal/` |

---

## 1. New Dependencies Since 2026-06-15

### Finding: NO new runtime dependencies

Phase 34.9 (comb-rule revert, TIP4P-ICE LJ constants) and Phase 37.1 (validators, error handling, PBC wrapping, cKDTree rebuild) introduced only stdlib imports.

**New files added by 34.9/37.1:**

| File | Phase | New third-party imports |
|------|-------|------------------------|
| `quickice/validation/validators.py` | 37.1-11 | `argparse` only (stdlib) |
| `quickice/validation/__init__.py` | 37.1-11 | None |

**Modified files with import changes:**

| File | Change | New third-party imports |
|------|--------|------------------------|
| `quickice/structure_generation/types.py` | 37.1-10 | Added `WATER_VOLUME_NM3`, `detect_atoms_per_molecule` — no new packages |
| `quickice/structure_generation/ion_inserter.py` | 37.1-10 | Moved `AVOGADRO` definition — no new packages |
| `quickice/structure_generation/solute_inserter.py` | 37.1-15 | Conditional cKDTree rebuild — no new packages |

**Complete third-party import set (unchanged from June 15):**

```
PySide6, vtkmodules, numpy, scipy, matplotlib, shapely, iapws, genice2, spglib
```

---

## 2. June 15 Report Savings — CORRECTIONS

### CRITICAL CORRECTION 1: scipy savings overestimated

**June 15 estimate:** 60-70 MB savings from narrowing scipy
**Corrected estimate:** ~26 MB savings from narrowing scipy

**Why the correction:** The June 15 report proposed excluding `scipy.special` (13.7 MB), `scipy.linalg` (11.2 MB), and `scipy.sparse` (12.9 MB) from the bundle. However, runtime dependency tracing shows that `scipy.spatial.cKDTree` **loads all three at import time**:

```python
from scipy.spatial import cKDTree
# Automatically loads: scipy.linalg, scipy.sparse, scipy.special, scipy.constants
```

These are **hard runtime dependencies** of cKDTree — they cannot be excluded without breaking the application.

**Verified runtime dependency chain:**

```
cKDTree → scipy.linalg (BLAS/LAPACK), scipy.sparse, scipy.special, scipy.constants
Rotation → (same as cKDTree, part of scipy.spatial)
UnivariateSpline → scipy.fft, scipy.optimize (in addition to above)
```

**Required scipy subpackages (cannot exclude):**
- `scipy.spatial` (7.0 MB) — cKDTree, Rotation
- `scipy.interpolate` (3.9 MB) — UnivariateSpline
- `scipy.linalg` (11.2 MB) — required by cKDTree
- `scipy.sparse` (12.9 MB) — required by cKDTree
- `scipy.special` (13.7 MB) — required by cKDTree
- `scipy.constants` (0.5 MB) — required by cKDTree
- `scipy.fft` (1.8 MB) — required by UnivariateSpline
- `scipy.optimize` (14.7 MB) — required by UnivariateSpline
- `scipy._lib` (2.8 MB) — core infrastructure
- `scipy.libs/` (30 MB) — BLAS/LAPACK shared libraries

**Excludable scipy subpackages (safe to exclude):**

| Subpackage | Bundle Size | Risk |
|-----------|-------------|------|
| `scipy.stats` | 11.0 MB | None — not loaded by any QuickIce code path |
| `scipy.io` | 6.3 MB | None |
| `scipy.signal` | 2.7 MB | None |
| `scipy.integrate` | 2.3 MB | None |
| `scipy.ndimage` | 1.4 MB | None |
| `scipy.fftpack` | 0.8 MB | None (legacy, replaced by scipy.fft) |
| `scipy.cluster` | 0.8 MB | None |
| `scipy.odr` | 0.7 MB | None |
| `scipy.datasets` | 0.1 MB | None |
| `scipy.differentiate` | 0.1 MB | None |
| **Total excludable** | **26.2 MB** | |

### CRITICAL CORRECTION 2: Hydrate lattice hiddenimports incomplete

**June 15 report listed:** `genice2.lattices.CS1`, `genice2.lattices.CS2`, `genice2.lattices.sH`

**Missing from June 15:** `genice2.lattices.sI`, `genice2.lattices.sII`

**Why this matters:** `quickice/structure_generation/hydrate_generator.py` line 64 has:
```python
from genice2.lattices import sI, sII, sH
```

These are **separate .py files** from CS1/CS2:
- `sI.py` = `from .CS1 import *` (re-export wrapper)
- `sII.py` = `from .CS2 import *` (re-export wrapper)

While `sI.Lattice` and `CS1.Lattice` produce the same object, the **import statement** `from genice2.lattices import sI` would fail at runtime if `sI.py` is not in the bundle.

**Correct hiddenimports for hydrate lattices:**
```python
# Both re-export modules AND implementation modules needed
'genice2.lattices.sI',    # from genice2.lattices import sI (line 64)
'genice2.lattices.sII',   # from genice2.lattices import sII (line 64)
'genice2.lattices.sH',    # from genice2.lattices import sH (line 64) + safe_import
'genice2.lattices.CS1',   # safe_import('lattice', 'CS1') via get_genice_lattice_name()
'genice2.lattices.CS2',   # safe_import('lattice', 'CS2') via get_genice_lattice_name()
```

### NEW FINDING 1: 27.2 MB of test data leaking into bundle

The current spec's `excludes=['*/tests/*']` does NOT prevent test files from being bundled. `collect_all()` pulls in package data (including test directories) before `Analysis` excludes can filter them.

**Test data in bundle by package:**

| Package | Test Data Size |
|---------|---------------|
| `scipy` (excludable subpackages) | 15.6 MB total (included in 26.2 MB above) |
| `scipy` (required subpackages) | 8.0 MB |
| `numpy` | 6.4 MB |
| `networkx` | 3.0 MB |
| `matplotlib` | 1.9 MB |
| `shapely` | 0.5 MB |
| **Total test data** | **27.2 MB** |

Of this 27.2 MB, ~11.8 MB is in packages that will remain in the bundle (numpy, matplotlib, networkx, shapely, and required scipy subpackages). The other ~15.6 MB is in excludable scipy subpackages and would be removed by narrowing scipy.

**Fix approach:** Use `collect_submodules()` with a filter that excludes `*/tests/*` submodules, or explicitly add test directories to `excludes` list in `Analysis()`.

### NEW FINDING 2: scipy.optimize._highspy (6.9 MB) — unnecessary in bundle

The HiGHS linear programming solver (`scipy.optimize._highspy/`) is 6.9 MB in the bundle. It is loaded as a transitive dependency of `scipy.optimize` (which is required by `UnivariateSpline`), but QuickIce **never calls** `scipy.optimize.linprog` or any LP solver.

```python
# In bundle: dist/quickice-gui/_internal/scipy/optimize/_highspy/
# Contains: _core.cpython-314-x86_64-linux-gnu.so (6.43 MB) + _highs_options.so (0.38 MB)
```

**Fix approach:** Add `'scipy.optimize._highspy'` to `excludes` list. This should safely prevent bundling of the HiGHS .so files since no code path imports it directly.

### NEW FINDING 3: genice2 bundle size grew from 3.6 MB to 5.1 MB

The June 15 report measured genice2 at 3.6 MB in the bundle. Current installed size is 5.1 MB (lattices = 4.6 MB of 5.1 MB). The bundle still shows 3.6 MB (dist hasn't been rebuilt). But on next build, the bundle will be ~5.1 MB for genice2.

**Lattice count:** 243 .py files + 2 subdirectories (engel, preparing) = 245 entries in installed lattices directory. Bundle has 254 entries (includes `__init__.py` and other structural files).

---

## 3. Verified Savings from June 15 Report

### scipy collect_all bloat — STILL #1 target, but savings revised DOWN

| Metric | June 15 Estimate | Revised Estimate | Reason |
|--------|------------------|-------------------|--------|
| scipy savings | 60-70 MB | 26 MB | cKDTree loads linalg+sparse+special |
| scipy in bundle after | ~50 MB | ~87 MB | Must keep 68.5 MB required + 30 MB libs |

### GenIce2 collect_all pulls 254 lattice plugins — STILL VALID

- **Bundle count:** 254 entries in lattices directory (confirmed from `dist/quickice-gui/_internal/genice2/lattices/`)
- **Needed:** 13 lattice modules (8 ice + 5 hydrate: sI, sII, sH, CS1, CS2)
- **Unused:** 241 of 254 (95%)
- **Estimated savings:** ~4.3 MB (lattice directory is 4.6 MB; keeping 13 files ≈ 0.25 MB)

### CLI-only binary savings — STILL VALID (~106 MB)

Excluding PySide6 (29 MB) + VTK (77 MB) = 106 MB. matplotlib and shapely are still needed for CLI mode (phase diagram export).

### Total savings — REVISED DOWNWARD

| Change | June 15 Estimate | Revised Estimate | Delta |
|--------|------------------|-------------------|-------|
| Narrow scipy collection | 60-70 MB | 26 MB | -34 to -44 MB |
| Remove test data from bundle | — | 11.8 MB | NEW |
| Exclude scipy._highspy | — | 6.9 MB | NEW |
| Enable UPX compression | 40-50 MB | 40 MB | unchanged |
| CLI-only binary (separate spec) | 106 MB | 106 MB | unchanged |
| Narrow matplotlib | 5-8 MB | 7 MB | unchanged |
| Narrow genice2 | 3 MB | 4.3 MB | +1.3 MB |
| Remove shapely (replace centroid) | 10.5 MB | 10.5 MB | unchanged |
| Exclude unused stdlib | 2-5 MB | 3 MB | unchanged |
| **GUI total** | **230-260 MB** | **~118 MB** | -112 to -142 MB |
| **CLI total** | **—** | **~224 MB** | — |

**Resulting bundle sizes:**

| Variant | June 15 Estimate | Revised Estimate |
|---------|------------------|-------------------|
| GUI bundle | 610-640 MB | ~753 MB |
| CLI bundle | 500-530 MB | ~647 MB |

---

## 4. Actionable Spec File Changes — PRECISE Recommendations

### 4.1 scipy: Specific `collect_submodules()` replacement

Replace `collect_all('scipy')` with targeted collection that respects the cKDTree→linalg/sparse/special dependency chain:

```python
# REPLACE: collect_all('scipy')
# WITH:
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# Collect required scipy subpackages as wholes
# (cKDTree loads linalg, sparse, special, constants at runtime — cannot narrow further)
for pkg in ['scipy.spatial', 'scipy.interpolate', 'scipy.linalg',
            'scipy.sparse', 'scipy.special', 'scipy.fft', 'scipy.optimize',
            'scipy.constants', 'scipy._lib']:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Could not collect {pkg}: {e}")

# Additional hidden imports not auto-discovered
hiddenimports += [
    'scipy._cyutility',
    'scipy._distributor_init',
    'scipy._lib.messagestream',
    'scipy.version',
]

# EXCLUDE entire subpackages QuickIce never uses
# These are safe to exclude because no QuickIce code path loads them
excludes += [
    'scipy.stats',
    'scipy.io',
    'scipy.signal',
    'scipy.integrate',
    'scipy.ndimage',
    'scipy.fftpack',
    'scipy.cluster',
    'scipy.odr',
    'scipy.datasets',
    'scipy.differentiate',
    # Exclude HiGHS LP solver (6.9 MB) — never called by QuickIce
    'scipy.optimize._highspy',
]

# Also exclude test directories from required subpackages
excludes += [
    'scipy.spatial.tests',
    'scipy.interpolate.tests',
    'scipy.linalg.tests',
    'scipy.sparse.tests',
    'scipy.special.tests',
    'scipy.optimize.tests',
    'scipy.fft.tests',
    'scipy._lib.tests',
    'scipy.constants.tests',
]
```

### 4.2 genice2: Corrected hiddenimports list

```python
# REPLACE: collect_all('genice2')
# WITH:
from PyInstaller.utils.hooks import collect_data_files

# Core genice2 modules
hiddenimports += [
    'genice2',
    'genice2.genice',
    'genice2.plugin',
    'genice2.valueparser',
    'genice2.formats',
    'genice2.formats.gromacs',
    'genice2.lattices',
    'genice2.molecules',
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

# Hydrate lattice plugins — CORRECTED from June 15 report
# Both re-export wrappers (sI, sII, sH) AND implementations (CS1, CS2) needed:
#   Line 64: from genice2.lattices import sI, sII, sH
#   Line 151: safe_import('lattice', 'CS1'/'CS2'/'sH')
# sI.py = "from .CS1 import *", sII.py = "from .CS2 import *"
hiddenimports += [
    'genice2.lattices.sI',     # Re-export wrapper (MISSED in June 15 report)
    'genice2.lattices.sII',    # Re-export wrapper (MISSED in June 15 report)
    'genice2.lattices.sH',     # Direct module (both import and safe_import)
    'genice2.lattices.CS1',    # Implementation (sI hydrate)
    'genice2.lattices.CS2',    # Implementation (sII hydrate)
]

# Molecule plugins
hiddenimports += [
    'genice2.molecules.tip3p',  # Ice generation (generator.py safe_import)
    'genice2.molecules.tip4p',  # Hydrate generation (direct import + safe_import)
    'genice2.molecules.ch4',   # Hydrate guest (safe_import via GenIce internally)
    'genice2.molecules.thf',   # Hydrate guest (safe_import via GenIce internally)
]

# Transitive dependencies of genice2 (required at runtime)
hiddenimports += [
    'cycless', 'deprecation', 'pairlist', 'yaplotlib',
    'graphstat', 'openpyscad', 'click',
    'deprecated', 'methodtools', 'wirerope',
    'six', 'wrapt',
]

# Collect genice2 data files (if any)
datas += collect_data_files('genice2')
```

### 4.3 Test data exclusion — cross-package

Add to the `excludes` list in `Analysis()`:

```python
excludes += [
    # Cross-package test exclusions (collect_all pulls these in despite '*/tests/*' pattern)
    'numpy.tests',
    'numpy.distutils.tests',
    'matplotlib.tests',
    'networkx.tests',
    'shapely.tests',
]
```

### 4.4 Complete recommended `quickice-gui.spec`

```python
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# ============================================================
# Data files, binaries, and hidden imports
# ============================================================
datas = [('quickice/data', 'quickice/data')]
binaries = []
hiddenimports = []

# Keep collect_all for small/critical packages
for pkg in ['iapws', 'genice_core', 'numpy', 'spglib', 'networkx']:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Could not collect {pkg}: {e}")

# ---- NARROWED: scipy ----
# cKDTree loads linalg, sparse, special at runtime — cannot exclude those
for pkg in ['scipy.spatial', 'scipy.interpolate', 'scipy.linalg',
            'scipy.sparse', 'scipy.special', 'scipy.fft', 'scipy.optimize',
            'scipy.constants', 'scipy._lib']:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Could not collect {pkg}: {e}")
hiddenimports += [
    'scipy._cyutility',
    'scipy._distributor_init',
    'scipy._lib.messagestream',
    'scipy.version',
]

# ---- NARROWED: genice2 ----
# Only needed plugins + transitive deps
hiddenimports += [
    'genice2', 'genice2.genice', 'genice2.plugin', 'genice2.valueparser',
    'genice2.formats', 'genice2.formats.gromacs',
    'genice2.lattices', 'genice2.molecules',
    # Ice lattices (8)
    'genice2.lattices.ice1h', 'genice2.lattices.ice1c',
    'genice2.lattices.ice2', 'genice2.lattices.ice3',
    'genice2.lattices.ice5', 'genice2.lattices.ice6',
    'genice2.lattices.ice7', 'genice2.lattices.ice8',
    # Hydrate lattices (5: 3 re-export wrappers + 2 implementations)
    'genice2.lattices.sI', 'genice2.lattices.sII', 'genice2.lattices.sH',
    'genice2.lattices.CS1', 'genice2.lattices.CS2',
    # Molecules (4)
    'genice2.molecules.tip3p', 'genice2.molecules.tip4p',
    'genice2.molecules.ch4', 'genice2.molecules.thf',
    # Transitive deps
    'cycless', 'deprecation', 'pairlist', 'yaplotlib',
    'graphstat', 'openpyscad', 'click',
    'deprecated', 'methodtools', 'wirerope', 'six', 'wrapt',
]
datas += collect_data_files('genice2')

# ---- NARROWED: matplotlib ----
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

# ---- KEEP: shapely ----
try:
    tmp_ret = collect_all('shapely')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"Warning: Could not collect shapely: {e}")

# ============================================================
# Analysis with excludes
# ============================================================
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
        # Original excludes
        '*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*',
        '*/.pytest_cache/*', '*/egg-info/*',
        # Unused scipy subpackages (safe to exclude)
        'scipy.stats', 'scipy.io', 'scipy.signal',
        'scipy.integrate', 'scipy.ndimage', 'scipy.fftpack',
        'scipy.cluster', 'scipy.odr', 'scipy.datasets', 'scipy.differentiate',
        # scipy.optimize._highspy (6.9 MB LP solver — never used)
        'scipy.optimize._highspy',
        # Test directories in required scipy subpackages
        'scipy.spatial.tests', 'scipy.interpolate.tests',
        'scipy.linalg.tests', 'scipy.sparse.tests',
        'scipy.special.tests', 'scipy.optimize.tests',
        'scipy.fft.tests', 'scipy._lib.tests', 'scipy.constants.tests',
        # Unused matplotlib backends
        'matplotlib.backends.backend_tkagg',
        'matplotlib.backends.backend_gtk3agg',
        'matplotlib.backends.backend_gtk4agg',
        'matplotlib.backends.backend_wxagg',
        'matplotlib.backends.backend_macosx',
        'matplotlib.backends.backend_pdf',
        'matplotlib.backends.backend_svg',
        'matplotlib.backends.backend_pgf',
        'matplotlib.backends.backend_cairo',
        'mpl_toolkits.mplot3d',
        # Test directories in other packages
        'numpy.tests', 'numpy.distutils.tests',
        'matplotlib.tests', 'networkx.tests', 'shapely.tests',
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

## 5. `scripts/assemble-dist.sh` — UNCHANGED

Last modified 2026-04-07. All 6 issues from the June 15 report remain unresolved:

| Issue | Status |
|-------|--------|
| Missing CLI documentation (`cli-reference.md`, etc.) | **UNFIXED** |
| Missing `data/examples/` directory | **UNFIXED** |
| No version validation | **UNFIXED** |
| No error handling for missing files | **UNFIXED** |
| `rm` fails if tarball doesn't exist | **UNFIXED** |
| PyInstaller build step commented out | **UNFIXED** |

---

## 6. UnivariateSpline as scipy.optimize Gateway — Optional Elimination

`scipy.optimize` (14.7 MB in bundle) is loaded **only** because `scipy.interpolate.UnivariateSpline` transitively depends on it. UnivariateSpline is used in exactly **one place**:

- `quickice/output/phase_diagram.py` line 223: `from scipy.interpolate import UnivariateSpline`
- Used for smooth curve fitting of melting boundary lines
- **Already has a fallback** (lines 229-238): if UnivariateSpline fails, it falls back to direct point sampling

If UnivariateSpline were replaced with `numpy.interp` or a simple cubic interpolation, `scipy.optimize` could be excluded entirely, saving an additional **14.7 MB** from the bundle.

**Implementation approach:**

```python
# IN quickice/output/phase_diagram.py, REPLACE:
#     from scipy.interpolate import UnivariateSpline
#     spline = UnivariateSpline(T_sample, P_sample, k=3, s=0)
# WITH:
#     from numpy.polynomial.polynomial import polyfit, polyval
#     coeffs = polyfit(T_sample, P_sample, deg=3)
#     P_smooth = polyval(T_smooth, coeffs)
#     # Or simply: P_smooth = np.interp(T_smooth, T_sample, P_sample)
```

**Estimated additional savings if implemented:** ~14.7 MB (scipy.optimize no longer needed)
**Risk:** LOW — the fallback path already exists, and numpy interpolation is well-tested
**Combined scipy savings if implemented:** ~26 + 14.7 + 6.9 (highspy) ≈ **48 MB**

---

## 7. Priority-Ordered Action Items

| Priority | Action | Savings | Risk | Effort |
|----------|--------|---------|------|--------|
| **P1** | Exclude 10 unused scipy subpackages | 26 MB | None | Low — add to excludes |
| **P1** | Exclude scipy test directories | 8 MB | None | Low — add to excludes |
| **P1** | Exclude scipy._highspy | 6.9 MB | Low | Low — add to excludes |
| **P1** | Exclude test dirs from numpy/matplotlib/networkx/shapely | 11.8 MB | None | Low — add to excludes |
| **P2** | Narrow genice2 (fix hiddenimports + remove unused lattices) | 4.3 MB | Medium | Medium — test all lattice types |
| **P2** | Narrow matplotlib | 7 MB | Low | Medium — test diagram export |
| **P3** | Install UPX and enable compression | 40 MB | Medium | Medium — test all .so files |
| **P3** | Replace UnivariateSpline with numpy interpolation | 14.7 MB | Low | Medium — code change + test |
| **P4** | Remove shapely (replace centroid formula) | 10.5 MB | Low | Low — simple formula change |
| **P4** | CLI-only binary (separate spec) | 106 MB | Low | Low — new spec file |
| **P5** | Exclude unused stdlib | 3 MB | None | Low — add to excludes |
| **P5** | Fix assemble-dist.sh (6 issues) | 0 MB | None | Low — shell script fixes |

**Total addressable savings (all actions):** ~132 MB GUI / ~238 MB CLI

---

## 8. Risk Summary — UPDATED

| Change | Risk Level | What Could Break | Mitigation |
|--------|-----------|------------------|------------|
| Exclude 10 scipy subpackages | **NONE** | Nothing — no QuickIce code loads them | Verify with `python -c "from scipy.spatial import cKDTree; from scipy.spatial.transform import Rotation; from scipy.interpolate import UnivariateSpline"` |
| Exclude scipy test dirs | **NONE** | Tests not needed at runtime | Already excluded by pattern (but pattern doesn't work) |
| Exclude scipy._highspy | **LOW** | HiGHS LP solver not used | Verify no linprog calls anywhere |
| Exclude other pkg test dirs | **NONE** | Tests not needed at runtime | Standard practice |
| Narrow genice2 | **MEDIUM** | `safe_import()` may fail if hidden imports incomplete | Test all 11 ice + 5 hydrate lattices |
| Narrow matplotlib | **LOW** | Missing backend may fail | Test GUI diagram + CLI export |
| Replace UnivariateSpline | **LOW** | Curve smoothing quality may differ | Fallback already exists; compare visually |
| Remove shapely | **LOW** | Centroid formula only works for convex polygons | Phase diagrams use convex regions |
| Enable UPX | **MEDIUM** | Some .so may break compressed | Use `upx_exclude` for VTK/PySide6 |
| CLI-only binary | **LOW** | Missing PySide6/VTK | Separate spec ensures isolation |

---

## 9. Files Referenced

| File | Relevance |
|------|-----------|
| `quickice-gui.spec` | PyInstaller spec — UNCHANGED since June 15, all optimizations apply here |
| `scripts/assemble-dist.sh` | Distribution packaging — UNCHANGED since April, 6 known issues |
| `environment.yml` | Dependency manifest — UNCHANGED since April |
| `environment-build.yml` | Build environment — includes `pyinstaller==6.19.0` |
| `quickice/structure_generation/hydrate_generator.py` | Lines 64, 151 — hydrate lattice imports (sI/sII/sH + CS1/CS2/sH) |
| `quickice/structure_generation/mapper.py` | Lines 10-18 — ice lattice name mapping |
| `quickice/structure_generation/types.py` | Lines 70-98 — hydrate lattice config (HYDRATE_LATTICES dict) |
| `quickice/structure_generation/generator.py` | Lines 108, 119, 122 — safe_import calls for lattice, molecule, format |
| `quickice/output/phase_diagram.py` | Line 223 — UnivariateSpline (only scipy.interpolate usage) |
| `quickice/output/validator.py` | Line 12 — `scipy.spatial.cKDTree` |
| `quickice/gui/vtk_utils.py` | Line 9 — `scipy.spatial.cKDTree` |
| `quickice/structure_generation/ion_inserter.py` | Line 14 — `scipy.spatial.cKDTree` |
| `quickice/structure_generation/solute_inserter.py` | Lines 15-16 — `cKDTree` + `Rotation` |
| `quickice/structure_generation/custom_molecule_inserter.py` | Lines 15-16 — `cKDTree` + `Rotation` |
| `quickice/structure_generation/overlap_resolver.py` | Line 11 — `scipy.spatial.cKDTree` |
| `quickice/ranking/scorer.py` | Line 15 — `scipy.spatial.cKDTree` |
| `quickice/validation/validators.py` | New in 37.1-11 — `argparse` only (no bundle impact) |

---

*Delta analysis by Scancode Task D — 2026-06-18*
*Reference: `.planning/code_analysis/20260615_portable_distribution.md` (full baseline)*
