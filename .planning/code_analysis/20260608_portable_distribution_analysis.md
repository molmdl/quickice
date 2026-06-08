# Portable Distribution Library Analysis

**Analysis Date:** 2026-06-08
**Method:** Static code analysis (READ-ONLY) of imports, PyInstaller spec, and built bundle
**Bundle measured:** `dist/quickice-gui/` (871 MB total)

---

## Section 1: Current Bundle Profile

### 1.1 Overall Size

| Metric | Value |
|--------|-------|
| **Total bundle** | 871 MB |
| **Compressed tarball** | 289 MB |
| **Main executable** | 29 MB |
| **_internal/ directory** | ~842 MB |

### 1.2 Size Breakdown by Component (measured from built bundle)

| Component | Size | Notes |
|-----------|------|-------|
| **VTK shared libs** (`libvtk*.so`) | 38 MB | 150 .so files |
| **VTK Python modules** (`vtkmodules/*.so`) | 29 MB | 132 .so files, ALL collected via `collect_all` |
| **scipy Python** | 83 MB | 1063 submodules collected via `collect_all` |
| **scipy.libs** (OpenBLAS) | 40 MB | `libopenblasp-r0.3.32.so` |
| **PySide6** | 29 MB | Qt Python bindings |
| **libpython3.14** | 35 MB | Python runtime shared lib |
| **numpy** | 28 MB | Python modules |
| **matplotlib** | 20 MB | 162 submodules |
| **Qt6 C++ libs** (`libQt6*.so`) | 4 MB | Gui, Widgets, Core, Pdf |
| **networkx** | 8 MB | 579 submodules |
| **shapely** (`shapely/` + `shapely.libs/`) | 10.5 MB | GEOS + Python |
| **spglib** | 5.9 MB | Space group library |
| **fontTools** | 6 MB | Font processing |
| **genice2** | 3.6 MB | Ice structure generator |
| **genice_core** | included | GenIce core |
| **iapws** | 452 KB | IAPWS water properties |
| **PIL/Pillow** | 784 KB | Image processing |
| **QuickIce data** | 84 KB | ITP, GRO files |
| **dist-info** (metadata) | ~1 MB | Package metadata dirs |

### 1.3 scipy Submodule Breakdown (83 MB total)

| Submodule | Size | Used by QuickIce? |
|-----------|------|--------------------|
| `scipy.special` | 13 MB | **Transitive** (required by scipy.spatial) |
| `scipy.optimize` | 12 MB | **Transitive** (required by scipy.interpolate) |
| `scipy.stats` | 11 MB | **NOT used** — can exclude |
| `scipy.sparse` | 11 MB | **Transitive** (required by scipy.spatial) |
| `scipy.linalg` | 10 MB | **Transitive** (required by scipy.spatial/interpolate) |
| `scipy.io` | 6.3 MB | **NOT used** — can exclude |
| `scipy.spatial` | 6.1 MB | **Directly used** — cKDTree in 6 files |
| `scipy.signal` | 2.7 MB | **NOT used** — can exclude |
| `scipy.interpolate` | 2.6 MB | **Directly used** — UnivariateSpline in `output/phase_diagram.py` |
| `scipy.integrate` | 2.3 MB | **NOT used** — can exclude |
| `scipy._lib` | 1.8 MB | Internal infrastructure |
| `scipy.fft` | 1.5 MB | **Transitive** (required by scipy.interpolate) |
| `scipy.ndimage` | 1.4 MB | **NOT used** — can exclude |
| `scipy.fftpack` | 840 KB | **Transitive** (legacy of fft) |
| `scipy.cluster` | 812 KB | **NOT used** — can exclude |
| `scipy.odr` | 720 KB | **NOT used** — can exclude |
| `scipy.constants` | 248 KB | **Transitive** (required by multiple) |
| Others | < 100 KB | Negligible |

**Unused scipy total: ~36 MB** (stats + io + signal + integrate + ndimage + cluster + odr)

### 1.4 Data Files Bundled

| File | Bundled? | Used? | Notes |
|------|----------|-------|-------|
| `quickice/data/tip4p-ice.itp` | Yes | Yes | TIP4P-ICE water model topology |
| `quickice/data/tip4p.gro` | Yes | Yes | TIP4P water coordinates |
| `quickice/data/ch4.itp` | Yes | Yes | Methane topology for hydrate export |
| `quickice/data/thf.itp` | Yes | Yes | THF topology for hydrate export |
| `quickice/data/tip4p-ice.itp.bak` | Yes | **No** | Backup file — can exclude |
| `quickice/data/ch4_hydrate.itp` | **No** | Yes | Hydrate-specific CH4 topology — **MISSING from bundle** |
| `quickice/data/ch4_liquid.itp` | **No** | Yes | Liquid CH4 topology — **MISSING from bundle** |
| `quickice/data/thf_hydrate.itp` | **No** | Yes | Hydrate-specific THF topology — **MISSING from bundle** |
| `quickice/data/thf_liquid.itp` | **No** | Yes | Liquid THF topology — **MISSING from bundle** |
| `quickice/data/custom/` | **No** | Yes | Custom molecule templates — **MISSING from bundle** |

### 1.5 Current PyInstaller Spec Configuration

**File:** `quickice-gui.spec` (58 lines)

Key characteristics:
- Uses `collect_all()` for 9 packages (iapws, genice2, genice_core, matplotlib, scipy, numpy, shapely, networkx, spglib)
- **VTK/vtkmodules NOT in collect_all loop** — relies on PyInstaller auto-detection
- Excludes only test/doc patterns: `['*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*', '*/.pytest_cache/*', '*/egg-info/*']`
- `optimize=0` (no bytecode optimization)
- `strip=False` (no debug symbol stripping)
- `upx=True` but UPX binary not installed — **effectively disabled**
- `upx_exclude=[]` (empty)
- `console=False` (windowed app)
- **No genice2.plugin hidden imports** — risks missing lattice plugins

---

## Section 2: Required vs Optional Dependencies

### 2.1 Required Dependencies (MUST bundle)

| Package | Version | Used by | Import sites |
|---------|---------|---------|-------------|
| **PySide6** | 6.10.2 | GUI framework | 15+ GUI files (`quickice/gui/*.py`) |
| **VTK/vtkmodules** | 9.5.2 | 3D molecular visualization | 15+ GUI files (`quickice/gui/*.py`) |
| **numpy** | 2.4.3 | Core numerical operations | 20+ files across all modules |
| **scipy.spatial** | 1.17.1 | cKDTree for neighbor search | `custom_molecule_inserter.py`, `ion_inserter.py`, `overlap_resolver.py`, `scorer.py`, `vtk_utils.py`, `solute_inserter.py` |
| **scipy.spatial.transform** | | Rotation for molecule placement | `custom_molecule_inserter.py`, `solute_inserter.py` |
| **scipy.interpolate** | | UnivariateSpline for phase curves | `output/phase_diagram.py` (line 223) |
| **scipy transitive** | | Required by spatial/interpolate | `scipy.constants`, `scipy.fft`, `scipy.linalg`, `scipy.optimize`, `scipy.sparse`, `scipy.special` |
| **matplotlib** | 3.10.8 | Phase diagram canvas | `gui/phase_diagram_widget.py`, `gui/export.py` |
| **shapely.geometry** | 2.1.2 | Point/Polygon for phase detection | `gui/phase_diagram_widget.py` |
| **iapws** | 1.5.5 | Water/ice density calculations | `phase_mapping/water_density.py`, `phase_mapping/ice_ih_density.py`, `gui/phase_diagram_widget.py` |
| **genice2** | 2.2.13.1 | Ice structure generation | `structure_generation/generator.py`, `structure_generation/hydrate_generator.py` |
| **genice-core** | 1.4.3 | GenIce core algorithms | (transitive via genice2) |
| **networkx** | 3.6.1 | Graph algorithms for genice2 | (transitive via genice2, genice-core, graphstat) |
| **spglib** | 2.7.0 | Space group validation | `output/validator.py` |

### 2.2 Required Transitive Dependencies (bundled via genice2)

| Package | Version | Required by | Direct use in QuickIce? |
|---------|---------|-------------|------------------------|
| **cycless** | 0.7 | genice2 | No |
| **deprecation** | 2.1.0 | genice2 | No |
| **graphstat** | 0.3.3 | genice2 | No |
| **pairlist** | 0.6.4 | genice2 | No |
| **openpyscad** | 0.5.0 | genice2 | No |
| **yaplotlib** | 0.1.3 | genice2 | No |
| **methodtools** | 0.4.7 | cycless | No |
| **Deprecated** | 1.3.1 | cycless | No |
| **wrapt** | 2.1.2 | Deprecated | No |
| **wirerope** | 1.0.0 | methodtools | No |
| **six** | 1.17.0 | openpyscad, python-dateutil | No |

**These are all required** — genice2's `safe_import()` dynamically loads lattice/molecule/format plugins at runtime. Removing any transitive dep risks breaking ice or hydrate generation.

### 2.3 Optional/Excludable Dependencies

| Package | Size in bundle | Reason for exclusion | Risk |
|---------|---------------|---------------------|------|
| **scipy.stats** | 11 MB | Not imported anywhere in QuickIce | LOW — but transitive dep analysis needed |
| **scipy.io** | 6.3 MB | Not imported anywhere | LOW |
| **scipy.signal** | 2.7 MB | Not imported anywhere | LOW |
| **scipy.integrate** | 2.3 MB | Not imported anywhere | LOW |
| **scipy.ndimage** | 1.4 MB | Not imported anywhere | LOW |
| **scipy.cluster** | 812 KB | Not imported anywhere | LOW |
| **scipy.odr** | 720 KB | Not imported anywhere | LOW |
| **matplotlib.animation** | ~1 MB | Not used (no animation) | LOW-MEDIUM |
| **tip4p-ice.itp.bak** | negligible | Backup file | NONE |
| **dist-info dirs** | ~1 MB | Package metadata not needed at runtime | NONE |
| **gsw** (Gibbs Sea Water) | ~5 MB | Not imported anywhere | NONE — already excluded in environment |

---

## Section 3: Safe Optimization Suggestions

### 3.1 Install UPX and Rebuild (HIGHEST IMPACT, SAFEST)

**Estimated savings:** 80–130 MB
**Risk:** LOW (QT-023 confirmed spec already has `upx=True`)
**Action:** Install UPX binary on build machine, rebuild

```bash
# Download and install UPX
wget https://github.com/upx/upx/releases/download/v4.2.2/upx-4.2.2-amd64_linux.tar.xz
tar -xf upx-4.2.2-amd64_linux.tar.xz
cp upx-4.2.2-amd64_linux/upx ~/bin/
# Rebuild
./scripts/build-linux.sh
```

**Caveats:**
- Antivirus false positives on UPX-packed binaries
- ~1 second startup increase for decompression
- Keep `upx_exclude` for VTK `.so` files and `libpython*.so` (already in old spec)

### 3.2 Strip Debug Symbols (LOW RISK, EASY)

**Estimated savings:** 10–30 MB (from .so files)
**Risk:** LOW — standard practice for release builds
**Action:** Change `strip=False` to `strip=True` in `quickice-gui.spec`

```python
# BEFORE (line 52):
    strip=False,

# AFTER:
    strip=True,
```

**Also in COLLECT (line 54):**
```python
# BEFORE:
    strip=False,

# AFTER:
    strip=True,
```

### 3.3 Enable Bytecode Optimization (LOW RISK)

**Estimated savings:** 3–5 MB (smaller .pyc files)
**Risk:** LOW — `optimize=2` was used successfully in QT-008
**Action:** Change `optimize=0` to `optimize=2`

```python
# BEFORE (line 29):
    optimize=0,

# AFTER:
    optimize=2,
```

### 3.4 Restore QT-008 Exclusions (LOW RISK)

**Estimated savings:** ~10 MB
**Risk:** LOW — these were proven safe in QT-008, only QT-016's scipy exclusions broke things
**Action:** Add back the development/unused package exclusions from QT-008

The current spec only excludes test patterns (`*/tests/*`). QT-008 added specific package exclusions that were safe:

```python
EXCLUDES = [
    # Testing frameworks (not needed at runtime)
    'pytest', 'iniconfig', 'pluggy', 'pygments', '_pytest',
    
    # PyInstaller (build-time only)
    'pyinstaller', 'altgraph', 'pyinstaller_hooks_contrib',
    
    # Unused packages
    'gsw',  # Gibbs Sea Water - not used
    'git_filter_repo',  # Git tool - not used
]
```

### 3.5 Restore genice2.plugin Hidden Imports (SAFETY FIX)

**Estimated savings:** 0 MB (may increase slightly)
**Risk:** NONE — this prevents runtime failures from missing lattice plugins
**Action:** Add back `collect_submodules('genice2.plugin')` which was lost in QT-016 revert

```python
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Add after collect_all loop:
hiddenimports += collect_submodules('genice2.plugin')
```

This is important because genice2 uses `safe_import()` to dynamically discover lattice modules. Without the hidden imports, PyInstaller may miss them.

### 3.6 Add VTK/vtkmodules to collect_all Loop (SAFETY FIX)

**Estimated savings:** 0 MB (may increase slightly)
**Risk:** NONE — ensures all VTK modules are properly collected
**Action:** Add VTK to the collect_all loop

```python
for pkg in ['vtk', 'vtkmodules', 'iapws', 'genice2', 'genice_core', 'matplotlib', 'scipy', 'numpy', 'shapely', 'networkx', 'spglib']:
```

The current spec does NOT explicitly collect VTK — it relies on PyInstaller's auto-detection, which may miss modules.

### 3.7 Exclude scipy Unused Submodules (MEDIUM RISK, HIGHEST PYTHON SAVINGS)

**Estimated savings:** ~36 MB (from scipy Python modules)
**Risk:** MEDIUM — QT-016 attempted this and broke the executable

**Key lesson from QT-016 failure:** The approach of replacing `collect_all('scipy')` with selective `collect_submodules` was too aggressive. It excluded scipy itself from the collection loop AND tried to use explicit hiddenimports, which missed transitive dependencies loaded internally by scipy.

**Safer approach:** Keep `collect_all('scipy')` in the loop but add the unused modules to the `excludes` list. This lets PyInstaller's dependency tracker find all needed submodules, then strips the ones we know are unused:

```python
excludes=[
    '*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*', '*/.pytest_cache/*', '*/egg-info/*',
    # Unused scipy submodules (NOT transitive deps of spatial/interpolate)
    'scipy.stats', 'scipy.io', 'scipy.signal', 'scipy.integrate',
    'scipy.ndimage', 'scipy.cluster', 'scipy.odr',
]
```

**CRITICAL: Do NOT remove `scipy` from the collect_all loop.** The QT-016 mistake was removing scipy from `RUNTIME_PACKAGES` and replacing with `collect_submodules('scipy.spatial')`. This broke because:
1. `collect_submodules` only finds Python modules, not compiled extensions or data files
2. scipy's internal imports may load submodules dynamically
3. The `excludes` approach preserves PyInstaller's full dependency analysis

### 3.8 Exclude matplotlib.animation (LOW RISK)

**Estimated savings:** ~1–2 MB
**Risk:** LOW — animation not used anywhere

```python
excludes=[
    # ... existing ...
    'matplotlib.animation',
]
```

### 3.9 Exclude Backup Data File (NO RISK)

**Estimated savings:** negligible
**Risk:** NONE
**Action:** Remove `tip4p-ice.itp.bak` from data collection, or exclude it in spec

```python
datas = [('quickice/data', 'quickice/data')]
# After collection, filter out .bak files (or use Tree with excludes)
```

### 3.10 Include Missing Data Files (BUG FIX, NO RISK)

**Estimated savings:** 0 MB (adds files)
**Risk:** NONE — fixes missing files in bundle
**Action:** The bundle is missing `ch4_hydrate.itp`, `ch4_liquid.itp`, `thf_hydrate.itp`, `thf_liquid.itp`, and `custom/` directory. These are needed for hydrate and custom molecule GROMACS export.

The current `datas = [('quickice/data', 'quickice/data')]` should include all of `quickice/data/`, but the built bundle is missing several files. This suggests the build was done before these files were added, or there's a filtering issue.

### 3.11 Summary of Safe Optimizations by Impact

| Optimization | Est. Savings | Risk | Effort |
|-------------|-------------|------|--------|
| Install UPX + rebuild | 80–130 MB | LOW | Manual install |
| Strip debug symbols | 10–30 MB | LOW | 2-line change |
| Exclude unused scipy submodules | ~36 MB | MEDIUM | Add to excludes list |
| Enable optimize=2 | 3–5 MB | LOW | 1-line change |
| Restore QT-008 exclusions | ~10 MB | LOW | Add EXCLUDES list |
| Exclude matplotlib.animation | ~1–2 MB | LOW | Add to excludes |
| **TOTAL (excluding UPX)** | **~60–83 MB** | | |

---

## Section 4: Unsafe Optimizations to Avoid

### 4.1 Replacing `collect_all('scipy')` with Selective Imports (BROKE QT-016)

**What was tried:** Replace `collect_all('scipy')` with:
```python
hiddenimports += collect_submodules('scipy.spatial')
hiddenimports += collect_submodules('scipy.interpolate')
# Remove 'scipy' from RUNTIME_PACKAGES
```

**Why it failed:**
- `collect_submodules` only discovers Python `.py` modules, not compiled `.so` extensions
- scipy's `__init__.py` dynamically imports subpackages at import time
- Removing `scipy` from collect_all broke the package's internal initialization
- Runtime `ImportError` resulted when the executable tried to load scipy

**Lesson:** Never remove a package from `collect_all` and replace with `collect_submodules`. Instead, keep `collect_all` and add unwanted submodules to `excludes`.

### 4.2 Excluding scipy Transitive Dependencies

**What to avoid:** Excluding `scipy.constants`, `scipy.fft`, `scipy.linalg`, `scipy.optimize`, `scipy.sparse`, `scipy.special`

**Why it's unsafe:**
- `scipy.spatial.cKDTree` imports from `scipy.sparse`, `scipy.special` internally
- `scipy.interpolate.UnivariateSpline` imports from `scipy.linalg`, `scipy.optimize`, `scipy.fft`
- These are compile-time/import-time dependencies, not just optional features
- Excluding them causes `ImportError` at runtime when scipy.spatial tries to load

**From QT-016 research:** scipy.spatial requires: constants, linalg, sparse, special. scipy.interpolate requires: constants, fft, linalg, optimize, sparse, spatial, special.

### 4.3 Excluding shapely.ops or shapely.prepared via collect_submodules

**What to avoid:** Replacing `collect_all('shapely')` with `collect_submodules('shapely.geometry')`

**Why it's unsafe:**
- shapely's C extension (`shapely.libs/`) is loaded as a unit
- `shapely.geometry` may internally reference `shapely.ops` or `shapely.prepared`
- Similar pattern to scipy: internal imports break with selective collection
- QT-016 attempted this and it contributed to the revert

**Safer approach:** If excluding shapely submodules, use `excludes` list, not selective collection.

### 4.4 VTK Selective Imports (Replacing `from vtkmodules.all import *`)

**What was researched:** Replace `from vtkmodules.all import (vtkMolecule, vtkActor, ...)` with specific module imports:
```python
from vtkmodules.vtkCommonDataModel import vtkMolecule, vtkPolyData
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper
```

**Why it's risky:**
- VTK has complex inter-module dependencies (rendering depends on data model, etc.)
- `from vtkmodules.all import *` is used in 15+ files across the codebase
- Changing all imports is a large refactoring effort with high regression risk
- VTK's `vtkmodules.all` module handles circular imports and lazy loading internally
- Missing a dependency could cause segfaults, not just ImportErrors

**Recommendation:** Do NOT attempt VTK selective imports unless you can thoroughly test every viewer (ice, hydrate, ion, solute, custom molecule, interface, dual) on the built executable.

### 4.5 Excluding networkx

**Why it's unsafe:**
- Required by genice2 (direct dependency)
- Required by genice-core (direct dependency)
- Required by graphstat (direct dependency)
- genice2 uses `safe_import()` to dynamically load lattice modules that use networkx
- Removing networkx breaks all ice and hydrate structure generation

### 4.6 Removing gsw from Bundle (Already Safe, But Check)

**What:** `gsw` (Gibbs Sea Water, 3.6.21) shows as a numpy dependency but is NOT used by QuickIce

**Status:** Already excluded in QT-008's EXCLUDES list. The current spec lost this exclusion during QT-016 revert. Should be re-added safely.

---

## Section 5: Suggested PyInstaller Spec Changes

### 5.1 Complete Proposed Spec File

Below is the recommended spec with all safe changes applied. Changes are annotated with `# [CHANGE]` markers.

```python
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules  # [CHANGE] add collect_submodules

# Packages to exclude (development-only and unused)
EXCLUDES = [  # [CHANGE] add explicit EXCLUDES list (restored from QT-008 + new scipy exclusions)
    # Testing frameworks
    'pytest', 'iniconfig', 'pluggy', 'pygments', '_pytest',
    
    # PyInstaller (build-time only)
    'pyinstaller', 'altgraph', 'pyinstaller_hooks_contrib',
    
    # Unused packages
    'gsw',  # Gibbs Sea Water - not used
    'git_filter_repo',  # Git tool - not used
    
    # Test/doc patterns
    '*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*', 
    '*/.pytest_cache/*', '*/egg-info/*',
    
    # scipy unused submodules (safe to exclude - not transitive deps of spatial/interpolate)
    # [CHANGE] NEW: exclude unused scipy modules (~36 MB savings)
    # DO NOT exclude: constants, fft, linalg, optimize, sparse, special (transitive deps)
    'scipy.stats', 'scipy.io', 'scipy.signal', 'scipy.integrate',
    'scipy.ndimage', 'scipy.cluster', 'scipy.odr',
    
    # matplotlib unused modules
    # [CHANGE] NEW: exclude animation (~1-2 MB savings)
    'matplotlib.animation',
]

# Collect all data files, binaries, and hidden imports from packages
datas = [('quickice/data', 'quickice/data')]  # Includes custom/ subdirectory
binaries = []
hiddenimports = []

for pkg in ['vtk', 'vtkmodules', 'iapws', 'genice2', 'genice_core', 'matplotlib', 'scipy', 'numpy', 'shapely', 'networkx', 'spglib']:
    # [CHANGE] add 'vtk', 'vtkmodules' to explicit collection
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Could not collect {pkg}: {e}")

# [CHANGE] Add genice2 plugin hidden imports (prevents missing lattice modules)
hiddenimports += collect_submodules('genice2.plugin')

a = Analysis(
    ['quickice/gui/__main__.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,  # [CHANGE] use EXCLUDES list instead of generic pattern
    noarchive=False,
    optimize=2,  # [CHANGE] was 0, now 2 for bytecode optimization
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
    strip=True,  # [CHANGE] was False, now True to strip debug symbols
    upx=True,
    console=False,
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
    strip=True,  # [CHANGE] was False, now True
    upx=True,
    upx_exclude=[
        'vtk*.so',          # [CHANGE] VTK .so files may have issues with UPX
        'libpython*.so',    # [CHANGE] Python runtime lib
    ],
    name='quickice-gui',
)
```

### 5.2 Change-by-Change Summary

| Line(s) | Before | After | Savings | Risk |
|---------|--------|-------|---------|------|
| Import | `collect_all` | `collect_all, collect_submodules` | 0 | NONE |
| New | (no EXCLUDES) | Full EXCLUDES list | ~15 MB | LOW |
| Excludes | `['*/tests/*', ...]` | EXCLUDES variable | — | — |
| 9 (loop) | `['iapws', 'genice2', ...]` | Add `'vtk', 'vtkmodules'` | 0 (safety) | NONE |
| New | — | `collect_submodules('genice2.plugin')` | 0 (safety) | NONE |
| 29 | `optimize=0` | `optimize=2` | 3–5 MB | LOW |
| 41 | `strip=False` | `strip=True` | 10–30 MB | LOW |
| 54 | `strip=False` | `strip=True` | — | — |
| 56 | `upx_exclude=[]` | `['vtk*.so', 'libpython*.so']` | safety | NONE |

### 5.3 Additional scipy Exclusions in EXCLUDES list

| Exclusion | Estimated savings | Risk |
|-----------|-------------------|------|
| `scipy.stats` | 11 MB | LOW |
| `scipy.io` | 6.3 MB | LOW |
| `scipy.signal` | 2.7 MB | LOW |
| `scipy.integrate` | 2.3 MB | LOW |
| `scipy.ndimage` | 1.4 MB | LOW |
| `scipy.cluster` | 812 KB | LOW |
| `scipy.odr` | 720 KB | LOW |
| `matplotlib.animation` | ~1 MB | LOW |
| **Total** | **~36 MB** | |

### 5.4 Verification Checklist (MUST run after applying changes)

After modifying the spec and rebuilding:

1. **Build succeeds:** `./scripts/build-linux.sh`
2. **Bundle size measured:** `du -sh dist/quickice-gui/`
3. **scipy modules still present:** `ls dist/quickice-gui/_internal/scipy/spatial/` and `ls dist/quickice-gui/_internal/scipy/interpolate/`
4. **scipy unused modules absent:** Verify `dist/quickice-gui/_internal/scipy/stats/` does NOT exist
5. **Ice generation works:** Launch GUI, generate Ice Ih structure
6. **Hydrate generation works:** Switch to Hydrate tab, generate sI CH4 hydrate
7. **Interface generation works:** Generate ice-water interface
8. **Ion insertion works:** Insert Na+ and Cl- ions
9. **Solute insertion works:** Insert THF solutes
10. **Custom molecule works:** Upload custom .gro/.itp, generate
11. **Phase diagram works:** Click on diagram to select T/P
12. **GROMACS export works:** Export each tab to .gro/.top/.itp/.mdp
13. **PDB export works:** Save PDB from viewer
14. **Viewport screenshot works:** Save viewport image

### 5.5 What NOT to Change (Lessons from QT-016)

1. **Do NOT remove 'scipy' from collect_all loop** — this broke the executable in QT-016
2. **Do NOT replace `collect_all('scipy')` with `collect_submodules('scipy.spatial')`** — misses compiled extensions
3. **Do NOT exclude `scipy.constants`, `scipy.fft`, `scipy.linalg`, `scipy.optimize`, `scipy.sparse`, `scipy.special`** — these are transitive dependencies of spatial and interpolate
4. **Do NOT replace `from vtkmodules.all import *` with selective imports** — too risky without full regression testing
5. **Do NOT exclude `networkx`** — required by genice2
6. **Do NOT exclude `shapely` from collect_all** — same pattern as scipy, use excludes list instead

---

## Appendix A: Complete Import Map (What QuickIce Actually Uses)

### numpy (used in 20+ files)
- Direct: `import numpy as np` in most modules
- No subpackage imports — uses top-level only

### scipy.spatial (used in 6 files)
- `scipy.spatial.cKDTree`: `ion_inserter.py`, `overlap_resolver.py`, `scorer.py`, `vtk_utils.py`, `solute_inserter.py`, `output/validator.py`
- `scipy.spatial.transform.Rotation`: `custom_molecule_inserter.py`, `solute_inserter.py`

### scipy.interpolate (used in 1 file)
- `scipy.interpolate.UnivariateSpline`: `output/phase_diagram.py` (line 223, conditional import)

### matplotlib (used in 2 files)
- `matplotlib.backends.backend_qtagg.FigureCanvasQTAgg`: `gui/phase_diagram_widget.py`
- `matplotlib.figure.Figure`: `gui/phase_diagram_widget.py`, `gui/export.py`
- `matplotlib.patches.Polygon`: `gui/phase_diagram_widget.py`

### shapely (used in 1 file)
- `shapely.geometry.Point`: `gui/phase_diagram_widget.py`
- `shapely.geometry.Polygon`: `gui/phase_diagram_widget.py`

### iapws (used in 3 files)
- `iapws.IAPWS95`: `phase_mapping/water_density.py`
- `iapws._iapws._Ice`: `phase_mapping/ice_ih_density.py`
- `iapws.IAPWS97`: `gui/phase_diagram_widget.py`, `output/phase_diagram.py`

### genice2 (used in 2 files)
- `genice2.plugin.safe_import`: `generator.py`, `hydrate_generator.py`
- `genice2.genice.GenIce`: `generator.py`, `hydrate_generator.py`
- `genice2.formats.gromacs`: `hydrate_generator.py`
- `genice2.lattices.sI/sII/sH`: `hydrate_generator.py`
- `genice2.molecules.tip4p.Molecule`: `hydrate_generator.py`
- `genice2.valueparser.parse_guest`: `hydrate_generator.py`

### spglib (used in 1 file)
- `spglib.get_symmetry_dataset`: `output/validator.py`

### VTK (used in 15+ GUI files)
All via `from vtkmodules.all import (...)` — see Section 4.4 for full class list

---

## Appendix B: VTK Classes Actually Used

| VTK Class | Source Module | Used in |
|-----------|--------------|---------|
| `vtkMolecule` | vtkCommonDataModel | vtk_utils, molecular_viewer, ion_viewer, solute_viewer, custom_molecule_viewer, interface_viewer, hydrate_viewer |
| `vtkActor` | vtkRenderingCore | vtk_utils, export, molecular_viewer, ion_renderer, solute_renderer, custom_molecule_renderer, hydrate_renderer |
| `vtkPolyData` | vtkCommonDataModel | vtk_utils |
| `vtkPoints` | vtkCommonDataModel | vtk_utils |
| `vtkCellArray` | vtkCommonDataModel | vtk_utils |
| `vtkPolyDataMapper` | vtkRenderingCore | vtk_utils, molecular_viewer |
| `vtkOutlineSource` | vtkFiltersSources | vtk_utils |
| `vtkMatrix3x3` | vtkCommonMath | vtk_utils |
| `vtkMoleculeMapper` | vtkRenderingChemistry | molecular_viewer, ion_viewer, solute_viewer, custom_molecule_viewer, interface_viewer |
| `vtkRenderer` | vtkRenderingCore | molecular_viewer, ion_viewer, solute_viewer, custom_molecule_viewer, interface_viewer, hydrate_viewer |
| `vtkRenderWindow` | vtkRenderingCore | molecular_viewer, ion_viewer, solute_viewer, custom_molecule_viewer, interface_viewer, hydrate_viewer |
| `vtkRenderWindowInteractor` | vtkRenderingCore | molecular_viewer, ion_viewer, solute_viewer, custom_molecule_viewer, interface_viewer, hydrate_viewer |
| `vtkInteractorStyleTrackballCamera` | vtkInteractionStyle | molecular_viewer, ion_viewer, solute_viewer, custom_molecule_viewer, interface_viewer, hydrate_viewer |
| `vtkCommand` | vtkCommonCore | dual_viewer |
| `QVTKRenderWindowInteractor` | vtk.qt | molecular_viewer, ion_viewer, solute_viewer, custom_molecule_viewer, interface_viewer, hydrate_viewer |
| `vtkPNGWriter` | vtkIOImage | export |
| `vtkJPEGWriter` | vtkIOImage | export |
| `vtkWindowToImageFilter` | vtkRenderingCore | export |
| `vtkColorTransferFunction` | vtkRenderingCore | molecular_viewer |
| `vtkFloatArray` | vtkCommonCore | ion_renderer, solute_renderer, custom_molecule_renderer, hydrate_renderer |
| `vtkSphereSource` | vtkFiltersSources | ion_renderer, solute_renderer, custom_molecule_renderer, hydrate_renderer |

---

*Analysis performed: 2026-06-08*
*Method: Static code analysis of all Python imports, PyInstaller spec, and built bundle filesystem*
*Bundle version: v4.0.0 (built 2026-05-04, 871 MB)*
