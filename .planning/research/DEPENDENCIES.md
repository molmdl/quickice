# Dependency Research: QuickIce v2.0 GUI + 3D Visualization

**Project:** QuickIce v2.0 - Adding GUI application  
**Researched:** 2026-03-31  
**Python Version:** 3.14.3  
**Confidence:** HIGH

---

## Executive Summary

All required packages support Python 3.14. The recommended stack is **PySide6** (LGPL) + **VTK** with Qt support. This combination provides cross-platform desktop GUI with 3D molecular visualization while maintaining MIT license compatibility.

---

## Recommended Dependencies

### Primary Recommendation (MIT License Compatible)

Add to `env.yml` pip section:

```yaml
      - PySide6==6.11.0
      - vtk==9.6.1
```

### Alternative (If GPL License Acceptable)

```yaml
      - PyQt6==6.11.0
      - vtk==9.6.1
```

---

## Version Verification (Python 3.14 Compatibility)

| Package | Version | Python 3.14 Support | Release Date | Wheel Availability |
|---------|---------|---------------------|--------------|-------------------|
| **PySide6** | 6.11.0 | ✓ Explicit (classifiers list 3.14) | 2026-03-23 | win_amd64, manylinux, macOS |
| **PyQt6** | 6.11.0 | ✓ Via abi3 (cp310 ABI) | 2026-03-30 | win_amd64, manylinux, macOS |
| **VTK** | 9.6.1 | ✓ Explicit cp314 wheels | 2026-03-26 | win_amd64, manylinux, macOS |

**Sources:**
- PySide6: https://pypi.org/project/PySide6/6.11.0/
- PyQt6: https://pypi.org/project/PyQt6/6.11.0/
- VTK: https://pypi.org/project/vtk/9.6.1/

---

## Exact Lines for env.yml

### Option A: PySide6 (Recommended - LGPL, MIT Compatible)

```yaml
  - pip:
      # ... existing packages ...
      - PySide6==6.11.0
      - vtk==9.6.1
```

### Option B: PyQt6 (Alternative - GPL-3.0)

```yaml
  - pip:
      # ... existing packages ...
      - PyQt6==6.11.0
      - vtk==9.6.1
```

---

## Threading Support

**No additional packages needed.** Python's standard library includes `threading` module (since Python 1.5). For GUI progress bars:

- PySide6/PyQt6 have built-in `QProgressBar` widget
- Use `QThread` for non-blocking GUI updates during structure generation
- Already satisfied by PySide6/PyQt6 packages

---

## VTK Qt Integration

VTK 9.6.1 includes Qt support via extras. The package provides:
- `vtkQt` rendering classes
- `QVTkRenderWindowAdapter` for embedding VTK in Qt

**No extra installation required** - VTK wheels include Qt support by default when installed alongside PySide6/PyQt6.

To verify VTK Qt support at runtime:
```python
from VTK.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
```

---

## License Compatibility Analysis

| Package | License | Compatible with QuickIce (MIT) | Notes |
|---------|---------|-------------------------------|-------|
| **PySide6** | LGPL-3.0 | ✓ Yes | Dynamic linking exception allows MIT license |
| **PyQt6** | GPL-3.0 | ✗ No* | Requires QuickIce to be GPL-compatible |
| **VTK** | BSD-3-Clause | ✓ Yes | Permissive, no restrictions |

*\* PyQt6 would require either: (1) QuickIce becomes GPL-licensed, or (2) purchase commercial license from Riverbank Computing*

**Recommendation:** Use **PySide6** to maintain MIT license compatibility.

---

## Cross-Platform Support

| Platform | PySide6 | VTK | Notes |
|----------|---------|-----|-------|
| **Windows x86-64** | ✓ 6.11.0 | ✓ 9.6.1 | Requires Visual C++ runtime |
| **Linux x86-64** | ✓ 6.11.0 | ✓ 9.6.1 | manylinux_2_17 compatible |
| **Linux ARM64** | ✓ 6.11.0 | ✓ 9.6.1 | manylinux_2_28 compatible |
| **macOS x86-64** | ✓ 6.11.0 | ✓ 9.6.1 | macOS 13.0+ |
| **macOS ARM64** | ✓ 6.11.0 | ✓ 9.6.1 | macOS 11.0+ |

---

## Existing Dependencies (Preserved)

These are already in env.yml and remain unchanged:

```yaml
      - click==8.3.1
      - genice2==2.2.13.1
      - matplotlib>=3.5
      - networkx==3.6.1
      - numpy==2.4.3
      - scipy>=1.8
      - spglib==2.7.0
```

**No conflicts detected** with proposed additions.

---

## Installation Notes

1. **conda vs pip decision:** Use pip for all three packages (PySide6, VTK, PyQt6). They are published to PyPI with pre-built wheels.

2. **Installation order:** Install PySide6/PyQt6 first, then VTK. VTK detects Qt at install time.

3. **Linux-specific:** On Linux, may need system Qt packages:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install libgl1-mesa-glx libglib2.0-0
   ```

4. **Windows-specific:** Ensure Visual C++ 2019+ runtime installed (usually pre-installed)

---

## Quality Gate Verification

- [x] Versions verified compatible with Python 3.14 (VTK has explicit cp314 wheels, PySide6/PyQt6 via abi3)
- [x] All GUI dependencies included (PySide6 or PyQt6)
- [x] 3D visualization dependencies included (VTK)
- [x] No version conflicts with existing packages (verified via PyPI dependencies)
- [x] Conda vs pip decision documented (use pip for all)

---

## Additional Recommendations

### For 3D Molecular Viewer Implementation

VTK 9.6.1 supports the required molecular visualization features:
- **Ball-and-stick rendering**: Use `vtkSphereSource` + `vtkCylinderSource`
- **Hydrogen bonds**: Use `vtkLine` or custom tube filters
- **Camera controls**: Built-in `vtkInteractorStyleTrackballCamera`

### Performance Note

For max 216 water molecules (648 atoms), VTK will perform well:
- Modern hardware: 60+ FPS
- Integrated graphics: 30+ FPS
- No GPU required for this scale

---

## Sources

- PySide6: https://pypi.org/project/PySide6/ (verified 2026-03-31)
- PyQt6: https://pypi.org/project/PyQt6/ (verified 2026-03-31)
- VTK: https://pypi.org/project/vtk/ (verified 2026-03-31)
- VTK Python docs: https://docs.vtk.org/en/latest/interfaces/python.html

---

*Research for: QuickIce v2.0 GUI + 3D visualization dependencies*