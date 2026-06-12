# Portable Distribution Analysis

**Analysis Date:** 2026-06-12
**Current Bundle Size:** 871 MB (dist/quickice-gui/)
**Compressed Tarball:** 302 MB (quickice-v4.0.0-linux-x86_64.tar.gz)

---

## 1. Current PyInstaller Configuration

**Spec file:** `quickice-gui.spec`
**Entry point:** `quickice/gui/__main__.py`
**Mode:** COLLECT (one-folder)

### Current `collect_all` packages:
| Package | Why Collected | Actually Needed? |
|---------|--------------|-----------------|
| `iapws` | Water/ice density calculations | YES |
| `genice2` | Ice/hydrate structure generation | YES (but partially) |
| `genice_core` | Core algorithms for GenIce2 | YES |
| `matplotlib` | Phase diagram rendering | YES (but partially) |
| `scipy` | cKDTree, Rotation | YES (spatial only) |
| `numpy` | Array operations throughout | YES |
| `shapely` | Phase polygon hit-testing | YES |
| `networkx` | GenIce2 dependency | YES (indirect) |
| `spglib` | Space group validation | YES |

### Current excludes:
```python
excludes=['*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*', '*/.pytest_cache/*', '*/egg-info/*']
```

---

## 2. Actually-Used Libraries with Import Locations

### 2.1 Direct imports by QuickIce code

| Library | Specific Usage | Import Location(s) |
|---------|---------------|---------------------|
| `numpy` | Array ops throughout (29 files) | Nearly every module |
| `PySide6.QtWidgets` | QMainWindow, QWidget, QVBoxLayout, QPushButton, QComboBox, QFileDialog, QMessageBox, QSplitter, QMenuBar, QMenu, QTabWidget, QLineEdit, QProgressBar, QTextEdit, QToolButton, QToolTip | `quickice/gui/main_window.py`, `quickice/gui/view.py`, `quickice/gui/phase_diagram_widget.py`, `quickice/gui/export.py`, all panels |
| `PySide6.QtCore` | Qt, Signal, Slot, QThread, QTimer | `quickice/gui/main_window.py`, `quickice/gui/workers.py`, `quickice/gui/dual_viewer.py`, all panels |
| `PySide6.QtGui` | QAction, QShowEvent | `quickice/gui/main_window.py`, `quickice/gui/dual_viewer.py` |
| `vtkmodules.all` | 17 VTK classes (see below) | `quickice/gui/vtk_utils.py`, all viewers/renderers, `quickice/gui/export.py` |
| `vtkmodules.qt.QVTKRenderWindowInteractor` | Qt-VTK bridge widget | 7 viewer files |
| `scipy.spatial.cKDTree` | KD-tree neighbor search | `quickice/ranking/scorer.py`, `quickice/structure_generation/overlap_resolver.py`, `quickice/structure_generation/ion_inserter.py`, `quickice/structure_generation/solute_inserter.py`, `quickice/structure_generation/custom_molecule_inserter.py`, `quickice/gui/vtk_utils.py`, `quickice/output/validator.py` |
| `scipy.spatial.transform.Rotation` | Random rotation for solute placement | `quickice/structure_generation/solute_inserter.py`, `quickice/structure_generation/custom_molecule_inserter.py` |
| `scipy.interpolate.UnivariateSpline` | Melting curve interpolation | `quickice/output/phase_diagram.py` (lazy import) |
| `matplotlib.backends.backend_qtagg` | FigureCanvasQTAgg for phase diagram | `quickice/gui/phase_diagram_widget.py` |
| `matplotlib.figure` | Figure for diagram and export | `quickice/gui/phase_diagram_widget.py`, `quickice/gui/export.py` |
| `matplotlib.patches` | Polygon for phase diagram | `quickice/gui/phase_diagram_widget.py`, `quickice/output/phase_diagram.py` |
| `shapely.geometry` | Point, Polygon for phase hit-testing | `quickice/gui/phase_diagram_widget.py`, `quickice/output/phase_diagram.py` |
| `iapws.IAPWS95` | Water density calculation | `quickice/phase_mapping/water_density.py` |
| `iapws._iapws._Ice` | Ice Ih density calculation | `quickice/phase_mapping/ice_ih_density.py` |
| `spglib` | Space group symmetry detection | `quickice/output/validator.py` |
| `genice2.plugin.safe_import` | Dynamic lattice/molecule loading | `quickice/structure_generation/generator.py`, `quickice/structure_generation/hydrate_generator.py` |
| `genice2.genice.GenIce` | Ice structure generation | `quickice/structure_generation/generator.py`, `quickice/structure_generation/hydrate_generator.py` |

### 2.2 Indirect imports (via GenIce2)

GenIce2 `genice2/genice.py` imports at top level:
- `genice2.cage` → requires `cycless`, `graphstat` (for hydrate cage detection)
- `pairlist` → neighbor list (C extension `cpairlist.so` + Python)
- `networkx` → graph algorithms
- `genice_core` → core ice graph algorithm

GenIce2 lattice modules used by QuickIce:
| Lattice | File | Extra Dependencies |
|---------|------|------------------|
| ice1h | `genice2/lattices/ice1h.py` | None (only genice2.cell) |
| ice1c | `genice2/lattices/ice1c.py` | None |
| ice2 | `genice2/lattices/ice2.py` | `genice2.CIF` (uses pairlist, networkx) |
| ice3 | `genice2/lattices/ice3.py` | None |
| ice5 | `genice2/lattices/ice5.py` | None |
| ice6 | `genice2/lattices/ice6.py` | None |
| ice7 | `genice2/lattices/ice7.py` | None |
| ice8 | `genice2/lattices/ice8.py` | `genice2.CIF` (uses pairlist, networkx) |
| sI/CS1 | `genice2/lattices/CS1.py` | `genice2.valueparser.parse_cages` |
| sII/CS2 | `genice2/lattices/CS2.py` | `genice2.valueparser`, `genice2.cage` |
| sH/DOH | `genice2/lattices/DOH.py` | None |

GenIce2 molecule/format modules used by QuickIce:
| Module | File | Dependencies |
|--------|------|-------------|
| tip3p | `genice2/molecules/tip3p.py` | numpy |
| tip4p | `genice2/molecules/tip4p.py` | numpy |
| ch4 | `genice2/molecules/ch4.py` | numpy |
| thf | `genice2/molecules/thf.py` | numpy |
| me | `genice2/molecules/me.py` | logging |
| gromacs | `genice2/formats/gromacs.py` | numpy, genice2.cell |

---

## 3. VTK Classes Actually Used

QuickIce imports `from vtkmodules.all import (...)` in 10+ files, but the actual VTK classes used are only **17**:

| VTK Class | Used In |
|-----------|---------|
| `vtkMolecule` | `vtk_utils.py`, all viewer files |
| `vtkMoleculeMapper` | all viewer files, all renderer files |
| `vtkActor` | `vtk_utils.py`, all renderer files, `export.py` |
| `vtkPolyData` | `vtk_utils.py` |
| `vtkPoints` | `vtk_utils.py` |
| `vtkCellArray` | `vtk_utils.py` |
| `vtkPolyDataMapper` | `vtk_utils.py` |
| `vtkOutlineSource` | `vtk_utils.py` |
| `vtkMatrix3x3` | `vtk_utils.py` |
| `vtkRenderer` | all viewer files |
| `vtkSphereSource` | ion/solute/custom/hydrate renderers |
| `vtkFloatArray` | some renderers |
| `vtkColorTransferFunction` | some renderers |
| `vtkInteractorStyleTrackballCamera` | all viewer files |
| `vtkCommand` | `dual_viewer.py` |
| `vtkWindowToImageFilter` | `export.py` |
| `vtkPNGWriter` / `vtkJPEGWriter` | `export.py` |

**Problem:** `from vtkmodules.all import (...)` triggers import of ALL 132 VTK .so modules (77 MB total).

**Required VTK module groups:**
- `vtkCommonCore`, `vtkCommonDataModel`, `vtkCommonMath`, `vtkCommonMisc`, `vtkCommonSystem`, `vtkCommonTransforms`, `vtkCommonExecutionModel` (core)
- `vtkRenderingCore`, `vtkRenderingOpenGL2`, `vtkRenderingAnnotation` (rendering)
- `vtkInteractionWidgets`, `vtkInteractionStyle` (mouse interaction)
- `vtkFiltersCore`, `vtkFiltersGeneral`, `vtkFiltersSources` (sphere source, outline)
- `vtkDomainsChemistry`, `vtkDomainsChemistryOpenGL2` (molecule rendering)
- `vtkIOImage` (image export)
- `vtkImagingCore` (support)
- `vtkCommonColor` (support)

Estimated needed VTK .so files: ~30-40 (down from 132)

---

## 4. Data Files That Must Be Bundled

| File | Size | Purpose |
|------|------|---------|
| `quickice/data/tip4p-ice.itp` | 1.4 KB | TIP4P-ice force field parameters |
| `quickice/data/tip4p.gro` | 60 KB | TIP4P water reference structure |
| `quickice/data/ch4.itp` | 2.2 KB | Methane force field |
| `quickice/data/ch4_hydrate.itp` | 2.2 KB | Methane hydrate force field |
| `quickice/data/ch4_liquid.itp` | 2.2 KB | Methane in liquid force field |
| `quickice/data/thf.itp` | 11 KB | THF force field |
| `quickice/data/thf_hydrate.itp` | 11 KB | THF hydrate force field |
| `quickice/data/thf_liquid.itp` | 11 KB | THF in liquid force field |
| `quickice/data/custom/etoh.itp` | 5.7 KB | Ethanol example ITP |
| `quickice/data/custom/etoh.gro` | 508 B | Ethanol example GRO |
| `quickice/data/custom/etoh.chg` | 531 B | Ethanol example charges |
| `quickice/data/custom/etoh.top` | 320 B | Ethanol example topology |
| `quickice/phase_mapping/data/ice_phases.json` | 2.3 KB | Phase boundary data |
| `quickice/data/tip4p-ice.itp.bak` | 1.6 KB | Backup (can be excluded) |

**Total critical data files:** ~110 KB

---

## 5. Current Bundle Size Breakdown

| Component | Size | % of Total | Necessity |
|-----------|------|-----------|-----------|
| `scipy/` | 83 MB | 9.5% | OVERBUNDLED (only spatial needed, ~8 MB) |
| `vtkmodules/` | 77 MB | 8.8% | OVERBUNDLED (all 132 .so vs ~30 needed) |
| `scipy.libs/` | 30 MB | 3.4% | Includes OpenBLAS (needed for spatial) |
| `PySide6/` | 29 MB | 3.3% | NEEDED (Qt GUI framework) |
| `numpy/` | 28 MB | 3.2% | NEEDED |
| `matplotlib/` | 20 MB | 2.3% | PARTIALLY NEEDED (core + qtagg backend) |
| `python3.14/` | 17 MB | 1.9% | NEEDED (runtime) |
| `networkx/` | 8.0 MB | 0.9% | NEEDED (genice2 dep) |
| `fontTools/` | 6.0 MB | 0.7% | NEEDED (matplotlib dep) |
| `spglib/` | 5.9 MB | 0.7% | NEEDED (validator) |
| `shapely.libs/` + `shapely/` | 10.5 MB | 1.2% | NEEDED (phase diagram) |
| `genice2/` | 3.6 MB | 0.4% | OVERBUNDLED (249 lattice files, need ~14) |
| `_tcl_data/` + `_tk_data/` + `tcl8/` | 3.9 MB | 0.4% | NOT NEEDED (matplotlib qtagg doesn't use Tk) |
| `PIL/` | 920 KB | 0.1% | NOT NEEDED (not directly imported) |
| `contourpy/` | 784 KB | <0.1% | NEEDED (matplotlib dep) |
| `iapws/` | 452 KB | <0.1% | NEEDED |
| Loose `.so` files | 47 MB | 5.4% | MIXED (many xcb libs unnecessary) |
| `.dist-info/` directories | ~1 MB | <0.1% | NOT NEEDED at runtime |
| `setuptools/` | 40 KB | <0.1% | NOT NEEDED |
| **Total** | **~842 MB** | | |

---

## 6. Packages in Requirements NOT Actually Used by QuickIce

These packages appear in `environment.yml` / `environment-build.yml` but are NOT imported by QuickIce code. They are indirect dependencies of GenIce2, only needed for features QuickIce does NOT use:

| Package | Required By | Needed by QuickIce? | Notes |
|---------|------------|---------------------|-------|
| `cycless` | genice2.cage | PARTIAL (hydrate only) | Required for `genice2/cage.py` which is imported by `genice2/genice.py` top-level |
| `pairlist` | genice2.genice, genice2.CIF | YES | Top-level import in genice2/genice.py |
| `openpyscad` | genice2.formats.rings | NO | Only used by `rings` format (not used by QuickIce) |
| `graphstat` | genice2.cage | PARTIAL (hydrate only) | Required for `genice2/cage.py` |
| `yaplotlib` | genice2.formats.yaplot | NO | Only used by `yaplot` format |
| `methodtools` | cycless | NO | Indirect dep of cycless |
| `deprecated` | cycless | NO | Indirect dep of cycless |
| `deprecation` | genice2 | MAYBE | Used by genice2 decorators |
| `wirerope` | methodtools | NO | Indirect dep |
| `wrapt` | deprecated | NO | Indirect dep |
| `six` | openpyscad | NO | Only needed if openpyscad is used |
| `click` | cycless | NO | CLI framework, not needed for GUI |

**Critical finding:** The current bundle does NOT include `cycless`, `graphstat`, `pairlist` (Python), or `click`, but DOES include the `cpairlist.so` C extension. This means the current bundle has a **latent import error**: if GenIce2 hits the `cage.py` code path (hydrate generation with cage assessment), it will crash with `ModuleNotFoundError: No module named 'cycless'`.

---

## 7. Specific PyInstaller Optimization Suggestions

### 7.1 Exclusions (modules that can be safely excluded from the bundle)

**scipy submodules (~70 MB savings):**
```python
excludes += [
    'scipy.special', 'scipy.optimize', 'scipy.stats', 'scipy.sparse',
    'scipy.linalg', 'scipy.io', 'scipy.signal', 'scipy.integrate',
    'scipy.fft', 'scipy.fftpack', 'scipy.cluster', 'scipy.odr',
    'scipy.constants', 'scipy.differentiate', 'scipy.datasets', 'scipy.misc',
]
```

**VTK modules (~40 MB savings):**
Replace `from vtkmodules.all import (...)` with specific imports from individual VTK submodules. The following VTK modules can be excluded:
```python
excludes += [
    'vtkmodules.vtkFiltersAMR', 'vtkmodules.vtkFiltersCellGrid',
    'vtkmodules.vtkFiltersFlowPaths', 'vtkmodules.vtkFiltersGeneric',
    'vtkmodules.vtkFiltersHybrid', 'vtkmodules.vtkFiltersModeling',
    'vtkmodules.vtkFiltersParallel', 'vtkmodules.vtkFiltersSelection',
    'vtkmodules.vtkFiltersTexture', 'vtkmodules.vtkFiltersVerdict',
    'vtkmodules.vtkImagingColor', 'vtkmodules.vtkImagingFourier',
    'vtkmodules.vtkImagingGeneral', 'vtkmodules.vtkImagingMath',
    'vtkmodules.vtkImagingMorphological', 'vtkmodules.vtkImagingStatistics',
    'vtkmodules.vtkImagingStencil', 'vtkmodules.vtkIOAMR',
    'vtkmodules.vtkIOAsynchronous', 'vtkmodules.vtkIOChemistry',
    'vtkmodules.vtkIOCore', 'vtkmodules.vtkIOEnSight', 'vtkmodules.vtkIOExport',
    'vtkmodules.vtkIOGeometry', 'vtkmodules.vtkIOImage',  # needed for export, keep
    'vtkmodules.vtkIOInfovis', 'vtkmodules.vtkIOLegacy',
    'vtkmodules.vtkIOMINC', 'vtkmodules.vtkIOMovie',
    'vtkmodules.vtkIOPLY', 'vtkmodules.vtkIOSQL',
    'vtkmodules.vtkIOXML', 'vtkmodules.vtkWebGLExporter',
    # ... many more
]
```
**NOTE:** A better approach is to stop using `from vtkmodules.all import (...)` and instead import from specific submodules. This allows PyInstaller to only bundle the .so files that are actually referenced.

**Tcl/Tk (~4 MB savings):**
```python
excludes += ['_tkinter', 'tkinter', 'tcl8', '_tcl_data', '_tk_data']
```

**PIL/Pillow (~1 MB savings):**
```python
excludes += ['PIL']
```

**setuptools (~40 KB savings):**
```python
excludes += ['setuptools']
```

**dist-info directories:**
```python
excludes += ['*.dist-info']
```

**GenIce2 unused lattice files (~2.5 MB savings):**
Remove the ~235 lattice .py files that QuickIce does not use from the bundle. This can be done by not using `collect_all('genice2')` and instead specifying only the needed submodules.

**matplotlib tests and unused backends:**
```python
excludes += ['matplotlib.tests', 'matplotlib.testing', 'matplotlib.sphinxext',
             'matplotlib.tri', 'matplotlib.projections',
             'matplotlib.backends.backend_tkagg', 'matplotlib.backends.backend_gtk',
             'matplotlib.backends.backend_wx', 'matplotlib.backends.backend_macosx']
```

**XCB libraries (many unnecessary):**
```python
# Can exclude most libxcb-*.so except libxcb.so, libxcb-render.so, libxcb-shm.so
# The Qt platform plugin only needs a few XCB extensions
```

### 7.2 Replace `from vtkmodules.all import (...)`

**Current code** (in 10+ files):
```python
from vtkmodules.all import (
    vtkMolecule, vtkActor, vtkPolyData, vtkPoints, vtkCellArray, ...
)
```

**Recommended replacement:**
```python
# In vtk_utils.py (centralize all VTK imports)
from vtkmodules.vtkCommonDataModel import vtkMolecule, vtkPolyData
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer
from vtkmodules.vtkFiltersSources import vtkOutlineSource, vtkSphereSource
from vtkmodules.vtkCommonMath import vtkMatrix3x3
from vtkmodules.vtkRenderingCore import vtkColorTransferFunction
from vtkmodules.vtkCommonCore import vtkFloatArray
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkIOImage import vtkPNGWriter, vtkJPEGWriter
from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter
```

This change alone would reduce the VTK bundle from 77 MB (~132 .so files) to approximately **30-35 MB (~35 .so files)** because PyInstaller would only follow the specific import chains.

**Estimated savings: ~40-45 MB**

### 7.3 Replace `collect_all` for scipy and genice2

**Current spec (scipy):**
```python
collect_all('scipy')  # Bundles ALL of scipy: 83 MB + 30 MB libs
```

**Recommended spec:**
```python
# Only collect scipy.spatial and scipy.interpolate
from PyInstaller.utils.hooks import collect_submodules
hiddenimports += collect_submodules('scipy.spatial')
hiddenimports += collect_submodules('scipy.interpolate')
# Add scipy._lib as dependency
hiddenimports += collect_submodules('scipy._lib')
```

**Estimated savings: ~70 MB** (from ~113 MB to ~15 MB for scipy.spatial + interpolate + libs)

**Current spec (genice2):**
```python
collect_all('genice2')  # Bundles ALL 249 lattice files
```

**Recommended spec:**
```python
# Only collect the specific lattice/molecule/format modules QuickIce uses
hiddenimports += [
    'genice2.genice', 'genice2.plugin', 'genice2.cell', 'genice2.cage',
    'genice2.valueparser', 'genice2.decorators', 'genice2.formats',
    'genice2.lattices', 'genice2.molecules', 'genice2.CIF',
    'genice2.lattices.ice1h', 'genice2.lattices.ice1c',
    'genice2.lattices.ice2', 'genice2.lattices.ice3',
    'genice2.lattices.ice5', 'genice2.lattices.ice6',
    'genice2.lattices.ice7', 'genice2.lattices.ice8',
    'genice2.lattices.sI', 'genice2.lattices.sII', 'genice2.lattices.sH',
    'genice2.lattices.CS1', 'genice2.lattices.CS2', 'genice2.lattices.DOH',
    'genice2.molecules.tip3p', 'genice2.molecules.tip4p',
    'genice2.molecules.ch4', 'genice2.molecules.thf', 'genice2.molecules.me',
    'genice2.formats.gromacs',
    'genice2.molecules', 'genice2.molecules.mol',
    'genice2.molecules.one', 'genice2.molecules.ice',
    'genice2.molecules.serialize', 'genice2.molecules.arrange',
]
```

**Estimated savings: ~2.5 MB** (from ~3.6 MB to ~1.1 MB for genice2 lattices)

### 7.4 Hidden Imports (what PyInstaller will miss)

The current spec is missing these critical hidden imports:

```python
hiddenimports += [
    # GenIce2 runtime dependencies (NOT in current bundle!)
    'cycless', 'cycless.cycles', 'cycless.polyhed',
    'graphstat',
    'pairlist',  # Python pairlist module (cpairlist.so alone is not enough)
    'click',     # Required by cycless
    
    # GenIce2 internal modules
    'genice2.cage', 'genice2.valueparser', 'genice2.decorators',
    'genice2.cell', 'genice2.CIF', 'genice2.load',
    'genice2.groups', 'genice2.rigid', 'genice2.FrankKasper',
    
    # iapws internal
    'iapws._iapws',
    
    # Shapely C extension
    'shapely.speedups._speedups',
    
    # spglib C extension
    'spglib._spglib',
    
    # Matplotlib backend dependencies
    'matplotlib.backends.backend_qtagg',
    'matplotlib.backends.qt_compat',
    
    # scipy C extensions
    'scipy.spatial._ckdtree', 'scipy.spatial._qhull',
    'scipy.spatial.transform._rotation',
    'scipy.interpolate._fitpack',
]
```

**CRITICAL:** The current bundle is missing `cycless`, `graphstat`, `pairlist` (Python), and `click`. Hydrate generation may crash on import of `genice2/cage.py`. The `pairlist` Python module is needed by `genice2/genice.py` (top-level import) and `genice2/CIF.py` (used by ice2 and ice8 lattices).

### 7.5 Data File List (what must be bundled)

```python
datas = [
    # QuickIce molecular data files
    ('quickice/data/tip4p-ice.itp', 'quickice/data'),
    ('quickice/data/tip4p.gro', 'quickice/data'),
    ('quickice/data/ch4.itp', 'quickice/data'),
    ('quickice/data/ch4_hydrate.itp', 'quickice/data'),
    ('quickice/data/ch4_liquid.itp', 'quickice/data'),
    ('quickice/data/thf.itp', 'quickice/data'),
    ('quickice/data/thf_hydrate.itp', 'quickice/data'),
    ('quickice/data/thf_liquid.itp', 'quickice/data'),
    ('quickice/data/custom', 'quickice/data/custom'),
    
    # Phase boundary data
    ('quickice/phase_mapping/data/ice_phases.json', 'quickice/phase_mapping/data'),
    
    # Matplotlib data (fonts, etc. - required for rendering)
    ('matplotlib/mpl-data', 'matplotlib/mpl-data'),
]
```

### 7.6 UPX Compression Recommendations

The current spec already enables UPX:
```python
upx=True,
```

**Recommendations:**
- **KEEP UPX enabled** for all .so files except VTK C extensions
- **ADD `upx_exclude`** for VTK .so files that may have issues with UPX compression:
```python
upx_exclude=[
    # VTK .so files can be problematic with UPX
    'vtkmodules/*.so',
    # PySide6 .so files
    'PySide6/*.so',
    # OpenBLAS
    'libopenblas*.so',
    'libscipy_openblas*.so',
]
```
- **Estimated UPX savings:** ~10-15% of total size (80-130 MB) on non-excluded binaries
- **Risk:** UPX-compressed VTK/Qt .so files may crash on some Linux distributions. Excluding them is safer.

### 7.7 One-File vs One-Folder Tradeoff

| Aspect | One-Folder (current) | One-File |
|--------|---------------------|----------|
| Startup time | Fast (~1-2s) | Slow (~10-30s extraction to /tmp) |
| Disk space | 871 MB | ~400 MB compressed |
| User experience | Requires folder distribution | Single file convenience |
| Update granularity | Can replace individual files | Must rebuild entire archive |
| PyInstaller support | Stable, well-tested | Known issues with VTK, C extensions |
| Recommended | **YES** (for scientific app with large C extensions) | NO |

**Recommendation: Stay with one-folder (COLLECT) mode.** The VTK and scipy C extensions are known to have issues in one-file mode (on-extraction to /tmp can cause missing library dependencies). The 302 MB compressed tarball is already reasonable for distribution.

---

## 8. Optimized Spec File Recommendation

```python
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# === DATA FILES ===
datas = [
    ('quickice/data', 'quickice/data'),
    ('quickice/phase_mapping/data/ice_phases.json', 'quickice/phase_mapping/data'),
]

# === BINARIES ===
binaries = []

# === HIDDEN IMPORTS ===
hiddenimports = []

# Collect ONLY what's needed from each package
for pkg in ['iapws', 'genice_core', 'numpy']:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Could not collect {pkg}: {e}")

# GenIce2: collect all (needed for dynamic plugin loading via safe_import)
# but add missing runtime dependencies
try:
    tmp_ret = collect_all('genice2')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"Warning: Could not collect genice2: {e}")

# Add MISSING GenIce2 runtime dependencies
hiddenimports += [
    'cycless', 'cycless.cycles', 'cycless.polyhed',
    'graphstat',
    'pairlist',
    'click',
]

# Scipy: only spatial and interpolate submodules
hiddenimports += collect_submodules('scipy.spatial')
hiddenimports += collect_submodules('scipy.interpolate')
hiddenimports += collect_submodules('scipy._lib')

# NetworkX: needed by genice2
hiddenimports += collect_submodules('networkx')

# Shapely: needed for phase diagram
try:
    tmp_ret = collect_all('shapely')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"Warning: Could not collect shapely: {e}")

# spglib: needed for validator
try:
    tmp_ret = collect_all('spglib')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"Warning: Could not collect spglib: {e}")

# Matplotlib: collect all (needed for Qt embedding and data files)
try:
    tmp_ret = collect_all('matplotlib')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"Warning: Could not collect matplotlib: {e}")

# === EXCLUSIONS ===
excludes = [
    # Test/documentation directories
    '*/tests/*', '*/test/*', '*/docs/*', '*/__pycache__/*',
    '*/.pytest_cache/*', '*/egg-info/*', '*.dist-info',
    
    # scipy submodules NOT needed
    'scipy.special', 'scipy.optimize', 'scipy.stats', 'scipy.sparse',
    'scipy.linalg', 'scipy.io', 'scipy.signal', 'scipy.integrate',
    'scipy.fft', 'scipy.fftpack', 'scipy.cluster', 'scipy.odr',
    'scipy.constants', 'scipy.differentiate', 'scipy.datasets', 'scipy.misc',
    
    # Tkinter (not needed - using Qt backend)
    '_tkinter', 'tkinter', 'tcl8', '_tcl_data', '_tk_data',
    
    # PIL (not directly imported)
    'PIL',
    
    # setuptools (not needed at runtime)
    'setuptools',
    
    # matplotlib unused components
    'matplotlib.tests', 'matplotlib.testing', 'matplotlib.sphinxext',
    'matplotlib.tri', 'matplotlib.projections',
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
    optimize=2,  # Enable Python optimization (strip docstrings)
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
    strip=True,  # Strip debug symbols from binaries
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
    strip=True,  # Strip debug symbols
    upx=True,
    upx_exclude=[
        'vtkmodules/*.so',
        'PySide6/*.so',
        'libopenblas*.so',
        'libscipy_openblas*.so',
    ],
    name='quickice-gui',
)
```

---

## 9. Size Comparison: Current vs Estimated Minimal

| Component | Current Size | Estimated Minimal | Savings |
|-----------|-------------|-------------------|---------|
| scipy (full) | 113 MB | 15 MB | **98 MB** |
| vtkmodules (all 132 .so) | 77 MB | 32 MB | **45 MB** |
| PySide6 | 29 MB | 29 MB | 0 MB |
| numpy | 28 MB | 28 MB | 0 MB |
| matplotlib | 20 MB | 14 MB | **6 MB** |
| python3.14 | 17 MB | 17 MB | 0 MB |
| networkx | 8 MB | 8 MB | 0 MB |
| genice2 lattices | 3.6 MB | 1.1 MB | **2.5 MB** |
| Tcl/Tk | 3.9 MB | 0 MB | **3.9 MB** |
| PIL | 0.9 MB | 0 MB | **0.9 MB** |
| spglib | 5.9 MB | 5.9 MB | 0 MB |
| shapely | 10.5 MB | 10.5 MB | 0 MB |
| Loose .so (libxcb, etc.) | 47 MB | 35 MB | **12 MB** |
| .dist-info + setuptools | 1 MB | 0 MB | **1 MB** |
| genice2 missing deps | 0 MB | ~1 MB | -1 MB (addition) |
| **strip + UPX optimization** | - | - | **~40 MB** |
| **TOTAL** | **~842 MB** | **~175 MB** | **~667 MB (79%)** |

**Compressed tarball estimate:** ~175 MB → ~80-100 MB (vs current 302 MB)

---

## 10. Priority Action Items

### Critical (import correctness):
1. **Add missing hidden imports for genice2 deps** — `cycless`, `graphstat`, `pairlist`, `click`. Without these, hydrate generation may crash.
2. **Add `iapws._iapws`** as hidden import (for `ice_ih_density.py`)

### High impact (size reduction):
3. **Replace `from vtkmodules.all import (...)`** with specific submodule imports (~45 MB savings)
4. **Replace `collect_all('scipy')`** with `collect_submodules('scipy.spatial')` + `collect_submodules('scipy.interpolate')` (~98 MB savings)
5. **Exclude Tcl/Tk** — matplotlib qtagg backend doesn't need Tk (~4 MB savings)
6. **Enable `strip=True`** in both EXE and COLLECT sections
7. **Set `optimize=2`** in Analysis (strips docstrings, smaller .pyc)

### Medium impact:
8. **Trim genice2 lattices** — only bundle the 14 needed lattice files, not all 249 (~2.5 MB savings)
9. **Exclude PIL** — not directly imported (~1 MB savings)
10. **Exclude .dist-info directories** at runtime (~1 MB savings)
11. **Trim libxcb*.so** — only bundle essential XCB extensions (~5-10 MB savings)

### Low impact:
12. **Trim matplotlib** — exclude tests, testing, sphinxext, tri, projections (~6 MB savings)
13. **Exclude `tip4p-ice.itp.bak`** from data files (0.001 MB savings)

---

## 11. GenIce2 Plugin System: Bundling Implications

GenIce2 uses `safe_import()` for dynamic plugin loading:
```python
# In quickice/structure_generation/generator.py:
lattice = safe_import('lattice', self.lattice_name).Lattice()
water = safe_import('molecule', 'tip3p').Molecule()
formatter = safe_import('format', 'gromacs').Format()
```

`safe_import` dynamically imports `genice2.lattices.{name}`, `genice2.molecules.{name}`, `genice2.formats.{name}`. PyInstaller cannot detect these dynamic imports through static analysis. This means:

1. **All used lattice/molecule/format modules must be in `hiddenimports`**
2. **GenIce2's internal dependencies (pairlist, networkx, cage, etc.) must also be in hiddenimports**
3. **Using `collect_all('genice2')` is the safest approach** for the genice2 package itself, but the lattices directory can be trimmed post-build

**Alternative approach:** Post-build cleanup script that removes unused lattice .py files from `dist/quickice-gui/_internal/genice2/lattices/`, keeping only the 14 needed files.

---

*Analysis performed by codebase mapper. All sizes are approximate from the existing v4.0.0 build (Python 3.14, built 2024-05-04).*
