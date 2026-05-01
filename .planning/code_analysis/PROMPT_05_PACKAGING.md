# Prompt 5: Packaging Optimization

**Workflow:** `/gsd-plan-phase`
**Priority:** LOW
**Estimated time:** 4-8 hours (including testing)

---

## Instructions

Start a new session, then run:
```
/gsd-plan-phase
```

Paste this prompt when asked:

---

## Prompt

Phase: Optimize PyInstaller Bundle Size

### Goal

Reduce QuickIce GUI bundle size from ~700MB to ~500-550MB (22-43% reduction)

---

### Task 1: Add Exclusions List to quickice-gui.spec

**Current state:** No exclusions - all dependencies bundled
**Target:** Exclude development and unused packages

**Update `quickice-gui.spec`:**
```python
# Packages to exclude (development-only and unused)
EXCLUDES = [
    # Testing frameworks
    'pytest', 'iniconfig', 'pluggy', 'pygments', '_pytest',
    
    # PyInstaller (build-time only)
    'pyinstaller', 'altgraph', 'pyinstaller_hooks_contrib',
    
    # Unused packages
    'gsw',           # Gibbs Sea Water - not used
    'git_filter_repo',  # Git tool - not used
    
    # Optional: investigate these genice2 dependencies
    # 'openpyscad',   # Uncomment to test exclusion
    # 'yaplotlib',    # Uncomment to test exclusion
    # 'graphstat',    # Uncomment to test exclusion
]
```

**Estimated savings:** 15-25MB

---

### Task 2: Add VTK to collect_all Packages

**Current state:** VTK not explicitly collected, may miss plugins
**Target:** Ensure all VTK modules are bundled

**Update `quickice-gui.spec`:**
```python
RUNTIME_PACKAGES = [
    'vtk', 'vtkmodules',  # Add VTK explicitly
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
```

---

### Task 3: Add genice2 Plugin Hidden Imports

**Current state:** genice2 plugins may not be detected by static analysis
**Target:** Ensure all lattice plugins are bundled

**Update `quickice-gui.spec`:**
```python
from PyInstaller.utils.hooks import collect_submodules

# Add genice2 plugin hidden imports
hiddenimports += collect_submodules('genice2.plugin')
```

---

### Task 4: Enable Python Optimization

**Current state:** No optimization
**Target:** Enable bytecode optimization

**Update `quickice-gui.spec`:**
```python
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
    optimize=2,  # Enable Python optimization (remove docstrings, assertions)
)
```

**Estimated savings:** 5-10MB

---

### Task 5: Add UPX Exclusions for Large Libraries

**Current state:** UPX enabled but no exclusions
**Target:** Prevent UPX issues with VTK binaries

**Update `quickice-gui.spec`:**
```python
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'vtk*.so',       # VTK may have UPX issues
        'libpython*.so', # Don't compress Python lib
        '*.pyd',         # Windows Python extensions
    ],
    name='quickice-gui',
)
```

---

### Task 6: Investigate genice2 Dependency Exclusions

**Packages to test:**
- `openpyscad` - OpenSCAD output (may not be used)
- `yaplotlib` - Visualization (may not be used)
- `graphstat` - Graph statistics (may not be used)
- `cycless` - Cycle detection (may be needed)

**Approach:**
1. Comment out one package at a time in EXCLUDES
2. Build and test
3. If all features work, keep exclusion

**Estimated savings:** 2-5MB

---

### Task 7: Complete Spec File Template

**Full optimized `quickice-gui.spec`:**
```python
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Packages to exclude
EXCLUDES = [
    'pytest', 'iniconfig', 'pluggy', 'pygments', '_pytest',
    'pyinstaller', 'altgraph', 'pyinstaller_hooks_contrib',
    'gsw', 'git_filter_repo',
]

# Collect all data files, binaries, and hidden imports
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
    optimize=2,
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
        'vtk*.so',
        'libpython*.so',
    ],
    name='quickice-gui',
)
```

---

## Testing Checklist

After building, test ALL features:

```bash
# Build
pyinstaller quickice-gui.spec

# Run executable
./dist/quickice-gui/quickice-gui
```

**Test each feature:**
- [ ] Launch GUI successfully
- [ ] Generate ice structure for EACH supported phase (Ih, Ic, II, III, V, VI, VII, VIII)
- [ ] Generate interface structures (slab mode)
- [ ] Generate interface structures (pocket mode)
- [ ] Generate interface structures (piece mode)
- [ ] Generate hydrate structures (sI, sII, sH)
- [ ] Insert ions into structure
- [ ] Export to GROMACS format (.gro, .top, .itp)
- [ ] Export to PDB format
- [ ] Generate phase diagram
- [ ] Use 3D molecular viewer (rotate, zoom, pan)
- [ ] Test hydrogen bond visualization
- [ ] Save screenshot from viewer
- [ ] Run CLI mode with all options

---

## References

- `.planning/code_analysis/PACKAGING_2026-05-02.md` - Full analysis
- `quickice-gui.spec` - Current spec file
- `scripts/build-linux.sh` - Build script

---

## Success Criteria

- [ ] Bundle size reduced by 22-43% (target: 500-550MB)
- [ ] All ice phases generate correctly
- [ ] All interface modes work
- [ ] Hydrate generation works
- [ ] Ion insertion works
- [ ] All export formats work
- [ ] 3D viewer works
- [ ] CLI mode works
- [ ] No runtime errors or warnings
