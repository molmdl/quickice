# Packaging Analysis for QuickIce

**Analysis Date:** 2026-05-02

## Executive Summary

QuickIce GUI bundles approximately **700MB+** of dependencies, with VTK being the largest contributor (~508MB). This analysis identifies opportunities to reduce bundle size and improve PyInstaller configuration.

---

## Required Runtime Dependencies

### Core Dependencies (Directly Used)

| Package | Version | Size | Purpose | Location in Code |
|---------|---------|------|---------|------------------|
| `numpy` | 2.4.3 | ~40MB | Numerical operations, array handling | Throughout codebase |
| `scipy` | 1.17.1 | ~111MB | Spatial queries (cKDTree) | `quickice/ranking/scorer.py`, `quickice/structure_generation/overlap_resolver.py`, `quickice/output/validator.py` |
| `PySide6` | 6.10.2 | ~35MB | Qt GUI framework | All `quickice/gui/*.py` files |
| `vtk` | 9.5.2 | ~508MB | 3D molecular visualization | All viewer files in `quickice/gui/` |
| `matplotlib` | 3.10.8 | ~29MB | Phase diagram rendering | `quickice/output/phase_diagram.py`, `quickice/gui/phase_diagram_widget.py` |
| `shapely` | 2.1.2 | ~6.4MB | Polygon geometry for phase diagram | `quickice/gui/phase_diagram_widget.py`, `quickice/output/phase_diagram.py` |
| `networkx` | 3.6.1 | ~18MB | Molecular graph operations (genice2) | Required by genice2 |
| `genice2` | 2.2.13.1 | ~7.3MB | Ice crystal structure generation | `quickice/structure_generation/generator.py` |
| `genice-core` | 1.4.3 | ~264KB | Core algorithms for genice2 | Required by genice2 |
| `iapws` | 1.5.5 | ~1.1MB | Water density calculations | `quickice/phase_mapping/water_density.py` |
| `spglib` | 2.7.0 | ~6.0MB | Space group validation | `quickice/output/validator.py` |

**Total Estimated Runtime Dependencies:** ~762MB

### Transitive Dependencies (Required)

| Package | Size | Required By |
|---------|------|-------------|
| `pillow` | - | matplotlib |
| `contourpy` | - | matplotlib |
| `cycler` | - | matplotlib |
| `fonttools` | - | matplotlib |
| `kiwisolver` | - | matplotlib |
| `pyparsing` | - | matplotlib |
| `packaging` | - | matplotlib, scipy |
| `python-dateutil` | - | matplotlib |

### genice2 Transitive Dependencies (Required by genice2)

| Package | Purpose | Can Exclude? |
|---------|---------|--------------|
| `cycless` | Cycle detection | Potentially - not directly used |
| `deprecation` | Deprecation warnings | No - used by genice2 |
| `graphstat` | Graph statistics | Potentially - not directly used |
| `openpyscad` | OpenSCAD output | Potentially - not directly used |
| `pairlist` | Pair list generation | Likely required by genice2 |
| `yaplotlib` | Visualization | Potentially - not directly used |
| `methodtools` | Method decorators | Required by some genice2 deps |
| `munkres` | Assignment algorithm | Required by genice2 |
| `wirerope` | Function wrapping | Required by methodtools |
| `wrapt` | Decorator utilities | Required by deprecation |
| `Deprecated` | Deprecation decorators | Required by genice2 |

---

## Development-Only Dependencies

These should **NOT** be bundled in the executable:

| Package | Purpose | Exclusion Method |
|---------|---------|------------------|
| `pytest` | Testing framework | Add to `excludes` |
| `iniconfig` | pytest dependency | Add to `excludes` |
| `pluggy` | pytest dependency | Add to `excludes` |
| `pygments` | Syntax highlighting (pytest) | Add to `excludes` |
| `pyinstaller` | Build tool | Not included by default |
| `altgraph` | pyinstaller dependency | Add to `excludes` |
| `pyinstaller-hooks-contrib` | pyinstaller hooks | Add to `excludes` |

---

## Potentially Excludable Dependencies

### Confirmed Not Used

| Package | Reason | Action |
|---------|--------|--------|
| `gsw` (Gibbs Sea Water) | Not imported anywhere in codebase | Add to `excludes` |
| `git-filter-repo` | Git tool, unrelated to QuickIce | Add to `excludes` |

### genice2 Dependencies (Investigate Further)

These are pulled in by genice2 but may not be needed for ice structure generation:

| Package | Risk Level | Recommendation |
|---------|------------|----------------|
| `openpyscad` | Low | Try excluding, test thoroughly |
| `yaplotlib` | Low | Try excluding, test thoroughly |
| `graphstat` | Low | Try excluding, test thoroughly |
| `cycless` | Medium | May be needed for cycle detection in ice structures |

---

## Current PyInstaller Configuration

**Spec File:** `quickice-gui.spec`

```python
# Current configuration
excludes=[]  # EMPTY - no exclusions!
```

**Current `collect_all` packages:**
- iapws, genice2, genice_core, matplotlib, scipy, numpy, shapely, networkx, spglib

**Issues Identified:**

1. **No exclusions** - Development dependencies bundled unnecessarily
2. **Missing VTK in collect_all** - VTK not explicitly collected, may miss plugins
3. **No UPX optimization** - UPX is enabled but no exclusions
4. **`vtkmodules.all` imports everything** - Code imports all VTK modules

---

## Specific PyInstaller Script Changes

### 1. Add Exclusions List

Update `quickice-gui.spec`:

```python
# Packages to exclude (development-only)
EXCLUDES = [
    # Testing
    'pytest', 'iniconfig', 'pluggy', 'pygments', '_pytest',
    
    # PyInstaller (build-time only)
    'pyinstaller', 'altgraph', 'pyinstaller_hooks_contrib',
    
    # Unused packages
    'gsw',  # Gibbs Sea Water - not used
    'git_filter_repo',  # Git tool - not used
    
    # Optional: investigate these genice2 dependencies
    # 'openpyscad',  # Uncomment to test exclusion
    # 'yaplotlib',   # Uncomment to test exclusion
    # 'graphstat',   # Uncomment to test exclusion
]
```

### 2. Add VTK to collect_all

```python
for pkg in ['vtk', 'vtkmodules', 'iapws', 'genice2', 'genice_core', 
            'matplotlib', 'scipy', 'numpy', 'shapely', 'networkx', 'spglib']:
```

### 3. Optimize VTK Imports in Code

Replace `from vtkmodules.all import ...` with specific imports:

**Before** (`quickice/gui/vtk_utils.py`):
```python
from vtkmodules.all import (
    vtkMolecule,
    vtkMoleculeMapper,
    # ... all imports
)
```

**After**:
```python
from vtkmodules.vtkCommonDataModel import vtkMolecule
from vtkmodules.vtkRenderingCore import vtkMoleculeMapper
from vtkmodules.vtkFiltersSources import vtkMoleculeSource
# ... specific imports only
```

This allows PyInstaller to tree-shake unused VTK modules.

### 4. Add matplotlib Backend Optimization

```python
# In spec file, after collect_all for matplotlib
import matplotlib
matplotlib.use('QtAgg')  # Force Qt backend only
```

### 5. Enable UPX Exclusions for Large Libraries

```python
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        # VTK binaries may have issues with UPX
        'vtk*.so',
        '*.pyd',
    ],
    name='quickice-gui',
)
```

---

## Optimized Spec File

```python
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Packages to exclude
EXCLUDES = [
    'pytest', 'iniconfig', 'pluggy', 'pygments', '_pytest',
    'pyinstaller', 'altgraph', 'pyinstaller_hooks_contrib',
    'gsw', 'git_filter_repo',
]

# Collect all data files, binaries, and hidden imports from packages
datas = [('quickice/data', 'quickice/data')]
binaries = []
hiddenimports = []

# Collect runtime dependencies
RUNTIME_PACKAGES = [
    'vtk', 'vtkmodules',
    'iapws', 'genice2', 'genice_core',
    'matplotlib', 'scipy', 'numpy', 
    'shapely', 'networkx', 'spglib',
    'PySide6', 'shiboken6',
]

for pkg in RUNTIME_PACKAGES:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Could not collect {pkg}: {e}")

# Add genice2 plugin hidden imports
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
    excludes=EXCLUDES,
    noarchive=False,
    optimize=2,  # Enable Python optimization
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
    strip=False,
    upx=True,
    upx_exclude=[
        'vtk*.so',  # VTK may have UPX issues
        'libpython*.so',  # Don't compress Python lib
    ],
    name='quickice-gui',
)
```

---

## Estimated Size Reduction

| Optimization | Estimated Savings | Risk |
|--------------|-------------------|------|
| Exclude dev dependencies | ~5-10MB | None |
| Exclude gsw, git-filter-repo | ~10-15MB | None |
| Optimize VTK imports (tree-shaking) | ~100-200MB | Low-Medium |
| UPX compression | ~50-100MB | Low |
| Exclude unused genice2 deps | ~2-5MB | Medium |

**Total Potential Savings:** 167-330MB (22-43% reduction)

**Realistic Target:** Reduce from ~700MB to ~500-550MB

---

## Hidden Dependencies to Verify

These may be missed by PyInstaller's static analysis:

### 1. genice2 Entry Points
genice2 uses `entry_points` for lattice plugins. The `collect_submodules('genice2.plugin')` should catch this, but verify:

```bash
# After build, test with:
./dist/quickice-gui/quickice-gui
# Generate each ice phase to verify all lattices work
```

### 2. matplotlib Qt Backend
The QtAgg backend requires:
- `matplotlib.backends.backend_qtagg`
- `matplotlib.backends.qt_compat`

These should be caught by `collect_all('matplotlib')`.

### 3. VTK Qt Integration
Requires `vtkmodules.qt.QVTKRenderWindowInteractor` - verify this is included.

### 4. shapely GEOS Library
shapely requires `libgeos` - verify binary is bundled.

### 5. spglib C Extension
spglib uses C extensions - verify `.so` files are included.

---

## Recommendations

### Immediate Actions (Low Risk)

1. Add `EXCLUDES` list with dev dependencies
2. Add `vtk` and `vtkmodules` to `collect_all`
3. Add `collect_submodules('genice2.plugin')` for hidden imports
4. Set `optimize=2` in Analysis

### Medium-Term Actions (Medium Risk)

1. Test exclusion of `openpyscad`, `yaplotlib`, `graphstat`
2. Replace `vtkmodules.all` imports with specific module imports
3. Test VTK UPX exclusions

### Long-Term Actions (Higher Risk)

1. Consider lazy-loading VTK modules only when needed
2. Investigate if scipy cKDTree can be replaced with numpy-only solution
3. Consider offering CLI-only build without GUI/VTK

---

## Testing Checklist

After building optimized executable:

- [ ] Launch GUI successfully
- [ ] Generate ice structure for each supported phase
- [ ] Generate interface structures (slab, pocket, piece modes)
- [ ] Generate hydrate structures
- [ ] Insert ions into structure
- [ ] Export to GROMACS format (.gro, .top, .itp)
- [ ] Export to PDB format
- [ ] Generate phase diagram
- [ ] Use 3D molecular viewer (rotate, zoom, pan)
- [ ] Test hydrogen bond visualization
- [ ] Save screenshot from viewer
- [ ] Run CLI mode with all options

---

## File References

| File | Purpose |
|------|---------|
| `quickice-gui.spec` | PyInstaller spec file |
| `scripts/build-linux.sh` | Build script |
| `scripts/assemble-dist.sh` | Distribution assembly |
| `quickice/gui/__main__.py` | GUI entry point |
| `quickice/main.py` | CLI entry point |
| `quickice/data/` | Data files to bundle (.gro, .itp templates) |

---

*Analysis complete: 2026-05-02*
