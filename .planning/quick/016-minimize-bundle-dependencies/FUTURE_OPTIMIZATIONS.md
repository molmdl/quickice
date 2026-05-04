# Future Bundle Optimization Opportunities

**Created:** 2026-05-03
**Updated:** 2026-05-04 (Phase 1 reverted)
**Current Bundle:** 863MB

---

## ⚠️ Phase 1 FAILED - DO NOT RETRY

**Phase 1 (scipy/matplotlib/shapely exclusions) was attempted and REVERTED on 2026-05-04.**

**Reason:** Exclusions broke the bundled executable at runtime.

**See:** [016-REVERT-NOTICE.md](./016-REVERT-NOTICE.md)

**Action:** Skip this approach. Do not attempt selective scipy/matplotlib/shapely exclusions in future.

---

## Phase 2: VTK Selective Imports (~50-100MB savings)

### Current State
All files use `from vtkmodules.all import (...)` which loads all 187 VTK modules (~200MB total).

### Required Changes

**Files to update (9 files):**
1. `quickice/gui/vtk_utils.py`
2. `quickice/gui/molecular_viewer.py`
3. `quickice/gui/dual_viewer.py`
4. `quickice/gui/hydrate_viewer.py`
5. `quickice/gui/hydrate_renderer.py`
6. `quickice/gui/ion_viewer.py`
7. `quickice/gui/ion_renderer.py`
8. `quickice/gui/interface_viewer.py`
9. `quickice/gui/export.py`

**VTK Class-to-Module Mapping:**
```python
VTK_CLASS_TO_MODULE = {
    # Core rendering
    'vtkRenderer': 'vtkRenderingCore',
    'vtkActor': 'vtkRenderingCore',
    'vtkPolyDataMapper': 'vtkRenderingCore',
    'vtkMoleculeMapper': 'vtkRenderingCore',
    'vtkRenderWindow': 'vtkRenderingCore',
    'vtkRenderWindowInteractor': 'vtkRenderingCore',

    # Data model
    'vtkPolyData': 'vtkCommonDataModel',
    'vtkMolecule': 'vtkCommonDataModel',
    'vtkPoints': 'vtkCommonDataModel',
    'vtkCellArray': 'vtkCommonDataModel',

    # Filters
    'vtkOutlineSource': 'vtkFiltersSources',
    'vtkSphereSource': 'vtkFiltersSources',

    # Interactor
    'vtkInteractorStyleTrackballCamera': 'vtkInteractionStyle',
    'vtkCommand': 'vtkCommonCore',

    # Qt integration
    'QVTKRenderWindowInteractor': 'vtkmodules.qt.QVTKRenderWindowInteractor',

    # Export
    'vtkPNGWriter': 'vtkIOImage',
    'vtkJPEGWriter': 'vtkIOImage',
    'vtkWindowToImageFilter': 'vtkRenderingCore',

    # Other
    'vtkColorTransferFunction': 'vtkRenderingCore',
    'vtkFloatArray': 'vtkCommonCore',
    'vtkMatrix3x3': 'vtkCommonMath',
}
```

### Risk
- **Medium**: VTK might load modules dynamically at runtime
- **Mitigation**: Test all visualization features thoroughly

### Dependencies to Trace
- VTK rendering pipeline dependencies
- Qt-VTK interactor dependencies
- Molecule mapper dependencies

---

## Phase 3: Networkx Submodule Optimization (Unknown savings)

### Current State
networkx (8MB) loads 579 modules when genice2 is used.

### Potential Optimization
genice2 loads 191 algorithm modules. May be able to exclude:
- `networkx.drawing` (if not used by genice2)
- `networkx.readwrite` (if not used by genice2)

### Risk
- **High**: genice2 may require specific networkx submodules
- **Mitigation**: Test hydrate generation after exclusions

### Dependencies to Trace
- `genice2` → `graphstat` → `networkx.algorithms.*`
- `genice2` → `genice-core` → `networkx.algorithms.*`

---

## Phase 4: Shared Library Optimization (Unknown savings)

### Current State
| Library | Size | Purpose |
|---------|------|---------|
| libopenblasp | 40MB | Linear algebra (numpy/scipy) |
| libvtkCommonCore | 54MB | VTK core |
| libpython3.14 | 35MB | Python runtime |
| libicudata | 31MB | Qt internationalization |
| libavcodec | 20MB | Video encoding (VTK) |

### Potential Optimization
- Investigate if ICU is needed (31MB for Qt internationalization)
- Investigate if avcodec is needed (20MB for VTK video)

### Risk
- **High**: May break Qt or VTK functionality
- **Mitigation**: Thorough testing after changes

---

## Additional Research Needed

1. **VTK dynamic module loading**: Does VTK load plugins at runtime?
2. **scipy internal dependencies**: Does scipy.spatial depend on scipy.sparse?
3. **genice2 networkx usage**: Which specific networkx submodules are used?
4. **Qt ICU usage**: Is ICU required for English-only applications?
5. **VTK avcodec usage**: Is video encoding required for PNG/SVG export?

---

## Summary

| Phase | Savings | Risk | Status |
|-------|---------|------|--------|
| ~~Phase 1 (scipy/matplotlib/shapely)~~ | ~~105MB~~ | ~~Low~~ | **❌ FAILED/REVERTED** |
| Phase 2 (VTK selective imports) | ~50-100MB | Medium | Future (if desired) |
| Phase 3 (networkx submodules) | Unknown | High | Future (if desired) |
| Phase 4 (shared libraries) | Unknown | High | Future (if desired) |

**Current recommendation:** Accept current bundle size (863MB) as reasonable for a scientific application with these dependencies. Further optimizations carry significant risk of breaking functionality.

**If optimization is still desired:** Start with Phase 2 (VTK) - but expect similar complexity and risk.
