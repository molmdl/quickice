# Portable Distribution Library Analysis

**Analysis Date:** 2026-05-12
**Current Bundle Size:** 871 MB (dist/quickice-gui/)
**Compressed Tarball:** 289 MB

---

## Executive Summary

The QuickIce portable distribution is 871 MB, which is large for a desktop application. The primary contributors are:
- **VTK (3D visualization):** ~150 MB (17%)
- **SciPy (scientific computing):** ~113 MB (13%)
- **PySide6 (Qt GUI):** ~35 MB (4%)
- **NumPy + OpenBLAS:** ~68 MB (8%)
- **FFmpeg/libav (video codecs):** ~24 MB (3%)
- **Other dependencies:** ~50 MB (6%)
- **Application code + data:** ~1 MB (<1%)

**Estimated achievable reduction:** 200-300 MB (23-34%) with the optimizations below.

---

## Required Dependencies (Must Bundle)

### Core Runtime Dependencies

| Package | Version | Size | Purpose | Usage Location |
|---------|---------|------|---------|----------------|
| `numpy` | 2.4.3 | 40 MB + 28 MB libs | Array operations | Throughout codebase |
| `PySide6` | 6.10.2 | 35 MB | Qt GUI framework | `quickice/gui/*.py` |
| `vtk` | 9.5.2 | 77 MB + 54 MB libs | 3D molecular visualization | `quickice/gui/vtk_utils.py`, `quickice/gui/molecular_viewer.py` |
| `scipy` | 1.17.1 | 83 MB + 30 MB libs | KDTree for spatial queries | `quickice/ranking/scorer.py`, `quickice/structure_generation/solute_inserter.py` |
| `matplotlib` | 3.10.8 | 29 MB | Phase diagram rendering | `quickice/gui/phase_diagram_widget.py` |
| `genice2` | 2.2.13.1 | 7.3 MB | Ice/hydrate structure generation | `quickice/structure_generation/generator.py`, `quickice/structure_generation/hydrate_generator.py` |
| `genice-core` | 1.4.3 | 264 KB | Core GenIce algorithms | Dependency of genice2 |
| `iapws` | 1.5.5 | 1.1 MB | Water thermodynamic properties | `quickice/phase_mapping/water_density.py` |
| `shapely` | 2.1.2 | 6.4 MB + 5.6 MB libs | Polygon operations for phase diagram | `quickice/gui/phase_diagram_widget.py` |

### GenIce2 Transitive Dependencies (Required by genice2)

| Package | Version | Size | Purpose | Notes |
|---------|---------|------|---------|-------|
| `networkx` | 3.6.1 | 18 MB | Graph algorithms | Used by genice2 internally |
| `cycless` | 0.7 | 112 KB | Cycle detection | Required by genice2 |
| `pairlist` | 0.6.4 | 16 KB | Pair list generation | Required by genice2 |
| `graphstat` | 0.3.3 | 28 KB | Graph statistics | Required by genice2 |
| `yaplotlib` | 0.1.3 | 8 KB | Yaplot output | Required by genice2 |
| `openpyscad` | 0.5.0 | 108 KB | OpenSCAD output | Required by genice2 |
| `methodtools` | 0.4.7 | - | Method decorators | Required by genice2 |
| `wirerope` | 1.0.0 | - | Method binding | Required by genice2 |
| `deprecated` | 1.3.1 | - | Deprecation warnings | Required by genice2 |
| `deprecation` | 2.1.0 | - | Deprecation utilities | Required by genice2 |
| `wrapt` | 2.1.2 | - | Decorator utilities | Required by genice2 |
| `six` | 1.17.0 | - | Python 2/3 compatibility | Required by genice2 |

### Application Data Files

| File | Size | Purpose |
|------|------|---------|
| `quickice/data/tip4p-ice.itp` | 1.4 KB | TIP4P ice force field |
| `quickice/data/tip4p.gro` | 60 KB | TIP4P water coordinates |
| `quickice/data/thf.itp` | 11 KB | THF force field |
| `quickice/data/thf_liquid.itp` | 11 KB | Liquid THF force field |
| `quickice/data/ch4.itp` | 2.2 KB | Methane force field |
| `quickice/data/ch4_liquid.itp` | 2.2 KB | Liquid methane force field |
| `quickice/data/custom/*` | ~1 KB | Custom molecule templates |

**Total data files:** ~90 KB

---

## Optional/Removable Dependencies

### Currently Bundled but NOT Directly Used

| Package | Bundled Size | Reason for Removal |
|---------|-------------|-------------------|
| `spglib` | 5.9 MB | **Not imported anywhere in codebase** - listed in environment.yml but unused |
| `networkx` | 8 MB | Only used as transitive dependency of genice2 - could be tree-shaken if genice2 APIs allow |

### Excessively Large Components

| Component | Size | Issue | Recommendation |
|-----------|------|-------|----------------|
| FFmpeg libs (`libavcodec`, `libavformat`, `libavutil`) | 24 MB | Pulled by matplotlib for video export | Not needed - application only uses static image export |
| PIL/Pillow | 15 MB | Pulled as matplotlib dependency | Matplotlib can work without PIL for basic backends |
| Extra matplotlib backends | 1.6 MB | Bundles GTK, PDF, PGF backends | Only need QtAgg backend |
| VTK unused modules | ~50 MB | VTK bundles 150 shared libraries | Application only uses molecule rendering subset |

---

## Data Files to Bundle

### Required (MUST include)

```
quickice/data/
├── tip4p-ice.itp      # TIP4P ice ITP template
├── tip4p.gro          # TIP4P water coordinates
├── thf.itp            # THF hydrate guest
├── thf_liquid.itp     # THF liquid phase
├── ch4.itp            # Methane hydrate guest
├── ch4_liquid.itp     # Methane liquid phase
└── custom/            # Custom molecule templates
    ├── etoh.top
    ├── etoh.itp
    ├── etoh.gro
    └── etoh.chg
```

### GenIce2 Data (auto-collected by spec file)

GenIce2 includes lattice definitions and molecule templates that are required:
- `genice2/lattices/` - Ice lattice definitions
- `genice2/molecules/` - Water molecule definitions
- `genice2/formats/` - Output format handlers

---

## Current Bundle Size Issues

### Issue 1: VTK Over-Bundling (77 MB Python + 54 MB shared libs)

**Problem:** VTK is a massive library with 150+ shared libraries. QuickIce only uses:
- `vtkMolecule`, `vtkMoleculeMapper` - molecular rendering
- `vtkRenderer`, `vtkRenderWindow` - basic rendering
- `vtkActor`, `vtkPolyData` - geometry handling
- Basic interactor styles

**Unused VTK modules bundled:**
- `vtkFiltersParallel*` - parallel processing
- `vtkFiltersAMR` - adaptive mesh refinement
- `vtkFiltersFlowPaths` - flow visualization
- `vtkDomainsChemistry*` - chemistry extensions
- `vtkRenderingVolume` - volume rendering
- Many others

### Issue 2: SciPy Full Bundle (83 MB)

**Problem:** SciPy bundles all submodules, but QuickIce only uses:
- `scipy.spatial.cKDTree` - nearest neighbor search
- `scipy.spatial.transform.Rotation` - rotation operations

**Unused scipy modules:**
- `scipy.special` (13 MB) - special functions
- `scipy.optimize` (12 MB) - optimization
- `scipy.stats` (11 MB) - statistics
- `scipy.sparse` (11 MB) - sparse matrices
- `scipy.io` (6.3 MB) - file I/O
- `scipy.signal` (2.7 MB) - signal processing
- And more...

### Issue 3: Unnecessary FFmpeg Libraries (24 MB)

**Problem:** Matplotlib pulls FFmpeg libraries for video export, but QuickIce only exports static images (PNG, PDF).

**Libraries:**
- `libavcodec.so.62` - 20 MB
- `libavformat.so.62` - 2.9 MB
- `libavutil.so.60` - 1.1 MB

### Issue 4: spglib Unused (5.9 MB)

**Problem:** `spglib` is listed in dependencies but never imported. It's bundled for no reason.

### Issue 5: Matplotlib Backend Bloat (1.6 MB)

**Problem:** Bundles multiple backends (GTK, PDF, PGF, MacOSX, etc.) but only uses `backend_qtagg`.

---

## PyInstaller Script Modifications

### Current Spec File Analysis

**File:** `quickice-gui.spec`

```python
# Current configuration uses collect_all() which bundles EVERYTHING
for pkg in ['iapws', 'genice2', 'genice_core', 'matplotlib', 'scipy', 
            'numpy', 'shapely', 'networkx', 'spglib']:
    tmp_ret = collect_all(pkg)
    # This pulls ALL data files, binaries, and hidden imports
```

### Recommended Modified Spec File

```python
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# === Data files - ONLY what's needed ===
datas = [
    ('quickice/data', 'quickice/data'),  # Application data files
]

# === Binaries ===
binaries = []

# === Hidden imports - explicit, not auto-collected ===
hiddenimports = [
    # Core
    'numpy',
    'numpy.core',
    'numpy.core._multiarray_umath',
    
    # SciPy - ONLY what's used
    'scipy',
    'scipy.spatial',
    'scipy.spatial.cKDTree',
    'scipy.spatial.transform',
    'scipy.spatial.transform.Rotation',
    'scipy.lib',
    'scipy.lib.blas',
    'scipy.lib.lapack',
    
    # GenIce2
    'genice2',
    'genice2.genice',
    'genice2.plugin',
    'genice2.valueparser',
    'genice2.formats',
    'genice2.formats.gromacs',
    'genice2.lattices',
    'genice2.lattices.sI',
    'genice2.lattices.sII',
    'genice2.lattices.sH',
    'genice2.molecules.tip4p',
    'genice_core',
    
    # IAPWS
    'iapws',
    'iapws.IAPWS95',
    'iapws._iapws',
    
    # Shapely
    'shapely',
    'shapely.geometry',
    'shapely.geometry.point',
    'shapely.geometry.polygon',
    
    # Matplotlib - Qt backend only
    'matplotlib',
    'matplotlib.backends',
    'matplotlib.backends.backend_qtagg',
    'matplotlib.backends.backend_agg',
    'matplotlib.figure',
    'matplotlib.patches',
    
    # PySide6
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    
    # VTK - minimal
    'vtkmodules',
    'vtkmodules.all',
    'vtkmodules.qt.QVTKRenderWindowInteractor',
    
    # GenIce2 dependencies
    'networkx',
    'pairlist',
    'cycless',
    'graphstat',
    'openpyscad',
    'yaplotlib',
    'methodtools',
    'wirerope',
    'deprecated',
    'deprecation',
    'wrapt',
    'six',
]

# === Packages to fully collect (data files needed) ===
packages_with_data = ['genice2', 'genice_core']
for pkg in packages_with_data:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        # Don't add all hiddenimports - we're explicit above
    except Exception as e:
        print(f"Warning: Could not collect {pkg}: {e}")

# === Excludes - REMOVE unused modules ===
excludes = [
    # spglib - not used at all
    'spglib',
    
    # Matplotlib backends we don't need
    'matplotlib.backends.backend_gtk3',
    'matplotlib.backends.backend_gtk3agg',
    'matplotlib.backends.backend_gtk3cairo',
    'matplotlib.backends.backend_gtk4',
    'matplotlib.backends.backend_gtk4agg',
    'matplotlib.backends.backend_gtk4cairo',
    'matplotlib.backends.backend_macosx',
    'matplotlib.backends.backend_pdf',
    'matplotlib.backends.backend_pgf',
    'matplotlib.backends.backend_webagg',
    'matplotlib.backends.backend_nbagg',
    'matplotlib.backends._backend_pdf_ps',
    
    # Tkinter - not used
    'tkinter',
    'tkinter.filedialog',
    'tkinter.messagebox',
    
    # PIL/Pillow - not needed for QtAgg backend
    'PIL',
    'pillow',
    
    # Email/HTML - not used
    'email',
    'html',
    'xml',
    'xml.etree',
    
    # Testing frameworks
    'pytest',
    'unittest',
    
    # Development tools
    'pydoc',
    'doctest',
    
    # IPython/Jupyter
    'IPython',
    'jupyter',
    
    # Unused scipy modules
    'scipy.fft',
    'scipy.fftpack',
    'scipy.integrate',
    'scipy.interpolate',
    'scipy.io',
    'scipy.linalg',
    'scipy.misc',
    'scipy.ndimage',
    'scipy.odr',
    'scipy.optimize',
    'scipy.signal',
    'scipy.sparse',
    'scipy.sparse.linalg',
    'scipy.special',
    'scipy.stats',
    'scipy.weave',
    
    # NumPy testing
    'numpy.testing',
    'numpy.distutils',
    'numpy.f2py',
]

a = Analysis(
    ['quickice/gui/__main__.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,  # Enable Python optimizations (remove docstrings)
)

# Remove duplicate imports and optimize
a.scripts = [s for s in a.scripts if s[0] not in ['site', 'sitecustomize']]

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,  # Encryption adds minimal security but slows startup
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='quickice-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Strip debug symbols from binaries
    upx=True,    # Enable UPX compression (if available)
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
    strip=True,  # Strip debug symbols
    upx=True,    # Enable UPX compression
    upx_exclude=[
        # Exclude large binaries that don't compress well
        'libopenblasp-r0.3.32.so',  # OpenBLAS - already optimized
        'libpython3.14.so.1.0',      # Python runtime
    ],
    name='quickice-gui',
)
```

---

## Expected Size Reduction

### Summary of Reductions

| Component | Current | Target | Reduction | Method |
|-----------|---------|--------|-----------|--------|
| spglib | 5.9 MB | 0 MB | 5.9 MB | Exclude from bundle |
| FFmpeg libs | 24 MB | 0 MB | 24 MB | Exclude from bundle |
| PIL/Pillow | 15 MB | 0 MB | 15 MB | Exclude from bundle |
| Unused SciPy modules | ~40 MB | 0 MB | 40 MB | Explicit imports only |
| Unused matplotlib backends | 1.6 MB | 0.1 MB | 1.5 MB | Exclude backends |
| VTK unused modules | ~50 MB | ~30 MB | 20 MB | VTK excludes (partial) |
| UPX compression | 0 | -30% | ~80 MB | Enable UPX |
| Strip debug symbols | 0 | -10% | ~50 MB | Enable strip |
| Python optimize=2 | 0 | -5% | ~5 MB | Remove docstrings |

**Total estimated reduction:** ~240 MB (from 871 MB to ~630 MB)

### Conservative Estimate

Even with partial optimization:
- Excluding spglib, FFmpeg, PIL, unused backends: ~45 MB
- UPX compression on shared libs: ~50-80 MB
- Stripping debug symbols: ~30-50 MB

**Minimum achievable:** 700-750 MB

---

## Step-by-Step Implementation Guide

### Phase 1: Quick Wins (Low Risk, High Impact)

1. **Remove spglib dependency**
   ```bash
   # Edit environment.yml
   # Remove: - spglib==2.7.0
   
   # Edit quickice-gui.spec
   # Remove 'spglib' from collect_all loop
   # Add to excludes: 'spglib'
   ```

2. **Exclude matplotlib backends**
   ```python
   # In spec file, add to excludes:
   'matplotlib.backends.backend_gtk3',
   'matplotlib.backends.backend_gtk4',
   'matplotlib.backends.backend_macosx',
   'matplotlib.backends.backend_pdf',
   'matplotlib.backends.backend_pgf',
   ```

3. **Enable strip and UPX**
   ```python
   # In spec file EXE and COLLECT:
   strip=True,
   upx=True,
   ```

4. **Install UPX**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install upx-ucl
   
   # Or download from: https://github.com/upx/upx/releases
   ```

### Phase 2: SciPy Optimization (Medium Risk)

1. **Identify exact SciPy imports**
   ```bash
   grep -r "from scipy" quickice/ --include="*.py"
   # Output shows only: scipy.spatial.cKDTree, scipy.spatial.transform.Rotation
   ```

2. **Modify spec file for explicit imports**
   ```python
   # Replace collect_all('scipy') with explicit hiddenimports
   hiddenimports = [
       'scipy.spatial',
       'scipy.spatial.cKDTree',
       'scipy.spatial.transform',
       'scipy.spatial.transform.Rotation',
   ]
   
   # Add scipy modules to excludes
   excludes = [
       'scipy.special',
       'scipy.optimize',
       'scipy.stats',
       'scipy.sparse',
       'scipy.io',
       'scipy.signal',
       'scipy.integrate',
       'scipy.interpolate',
       'scipy.linalg',
       'scipy.fft',
       'scipy.ndimage',
   ]
   ```

3. **Test thoroughly**
   ```bash
   pyinstaller --clean quickice-gui.spec
   ./dist/quickice-gui/quickice-gui
   
   # Verify:
   # - Ice generation works
   # - Hydrate generation works
   # - Ranking/scoring works (uses cKDTree)
   # - Interface generation works (uses Rotation)
   ```

### Phase 3: FFmpeg/PIL Removal (Medium Risk)

1. **Verify matplotlib doesn't need FFmpeg**
   ```python
   # Check current usage
   grep -r "animation\|video\|ffmpeg" quickice/ --include="*.py"
   # Should return no matches
   ```

2. **Exclude FFmpeg and PIL**
   ```python
   # In spec file excludes:
   excludes = [
       'PIL',
       'pillow',
   ]
   ```

3. **Test image export**
   ```bash
   ./dist/quickice-gui/quickice-gui
   # Test: Save diagram as PNG
   # Test: Save viewport as PNG
   ```

### Phase 4: VTK Optimization (High Risk, High Reward)

1. **Create VTK exclude hook**
   ```python
   # File: hooks/hook-vtkmodules.py
   
   # VTK modules that QuickIce actually uses:
   VTK_USED = [
       'vtkCommonCore',
       'vtkCommonDataModel',
       'vtkCommonMisc',
       'vtkCommonTransforms',
       'vtkCommonExecutionModel',
       'vtkCommonMath',
       'vtkRenderingCore',
       'vtkRenderingOpenGL2',
       'vtkRenderingFreeType',
       'vtkFiltersCore',
       'vtkFiltersGeneral',
       'vtkFiltersSources',
       'vtkInteractionStyle',
       'vtkIOCore',
       'vtkIOLegacy',
       'vtkDomainsChemistry',  # For vtkMolecule
   ]
   
   # Exclude everything else
   # This requires careful testing
   ```

2. **Test with reduced VTK**
   ```bash
   # Build and verify all visualization features work
   # This is the riskiest optimization
   ```

### Phase 5: Final Verification

1. **Full test suite on bundled application**
   ```bash
   # Run all GUI workflows:
   # 1. Ice generation (all phases)
   # 2. Hydrate generation (sI, sII, sH)
   # 3. Interface construction
   # 4. Ion insertion
   # 5. Solute insertion
   # 6. Custom molecule workflow
   # 7. All export functions (PDB, GROMACS, PNG, PDF)
   # 8. Phase diagram interaction
   # 9. 3D visualization (rotation, zoom, representation modes)
   ```

2. **Measure final size**
   ```bash
   du -sh dist/quickice-gui/
   tar -czf test.tar.gz dist/quickice-gui/
   du -sh test.tar.gz
   ```

---

## Additional Recommendations

### 1. Consider Alternative 3D Rendering

If VTK size is unacceptable, consider:
- **PyOpenGL + moderngl**: Much smaller footprint
- **vispy**: Scientific visualization, smaller than VTK
- **pyqtgraph**: Built on PyQt, good for scientific plots

Trade-off: Requires rewriting visualization layer.

### 2. Lazy Loading for GenIce2

GenIce2 is only used for ice/hydrate generation. Consider:
```python
# Lazy import pattern (already used in hydrate_generator.py)
def _ensure_genice_import(self):
    if self._genice_lib is None:
        import genice2.genice as genice_lib
        self._genice_lib = genice_lib
```

This doesn't reduce bundle size but speeds up application startup.

### 3. Separate CLI and GUI Builds

If CLI-only distribution is needed:
- CLI only needs: numpy, scipy, genice2, iapws
- Excludes: PySide6, VTK, matplotlib, shapely
- Estimated CLI bundle: ~150-200 MB

### 4. Use Nuitka Instead of PyInstaller

Nuitka compiles Python to C, producing smaller binaries:
```bash
pip install nuitka
nuitka --standalone --enable-plugin=pyside6 \
       --enable-plugin=numpy \
       quickice/gui/__main__.py
```

Trade-off: Longer build time, but potentially 20-30% smaller bundle.

### 5. Platform-Specific Optimization

For Linux-specific builds:
- Use `patchelf` to optimize RPATH
- Strip all debug symbols from .so files
- Use system libraries where possible (not portable but smaller)

---

## Conclusion

The QuickIce portable distribution can be reduced from **871 MB to approximately 630-700 MB** through:

1. **Immediate wins (low risk):**
   - Remove spglib (5.9 MB)
   - Exclude unused matplotlib backends (1.5 MB)
   - Enable UPX compression (50-80 MB)
   - Strip debug symbols (30-50 MB)

2. **Medium effort (medium risk):**
   - Limit SciPy to used modules (40 MB)
   - Remove FFmpeg/PIL (39 MB)

3. **High effort (high risk):**
   - Optimize VTK bundle (20+ MB)

**Recommended approach:** Start with Phase 1 quick wins, verify functionality, then proceed to Phase 2-3. Phase 4 (VTK optimization) should only be attempted if bundle size is critical and other optimizations are insufficient.

---

*Analysis completed: 2026-05-12*
