# Stack Research: QuickIce v2.0 GUI Application

**Project:** QuickIce v2.0 - Adding GUI with interactive phase diagram and 3D molecular viewer  
**Researched:** 2026-03-31  
**Domain:** Cross-platform desktop GUI with 3D molecular visualization  
**Confidence:** HIGH

---

## Executive Summary

For QuickIce v2.0 GUI application, we recommend adding:

1. **PyQt6 6.11.0** for cross-platform desktop GUI (or PySide6 if commercial licensing needed)
2. **VTK 9.6.x** with Qt rendering for 3D molecular visualization
3. **Matplotlib Qt backend** for interactive phase diagram
4. **Keep existing GenIce2** (MIT licensed, fully compatible with all options)

---

## Recommended Stack

### Core GUI Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **PyQt6** | 6.11.0 | Primary GUI framework | Mature, feature-rich, excellent documentation. Supports Windows, Linux, macOS. Active development with Python 3.10-3.14 support. |

**Alternative: PySide6** - Same Qt framework but with LGPL license. Use if:
- You want to keep QuickIce MIT-licensed without GPL obligations
- Commercial license for PyQt6 is not an option

### 3D Molecular Visualization

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **VTK** | 9.6.1 | 3D rendering engine | BSD licensed (permissive), excellent Qt integration via `vtkQt`, proven in scientific visualization, handles 216 water molecules easily |
| **PyQt6** | (above) | GUI container | Hosts VTK widget for 3D viewer |

**Alternative: py3Dmol 2.5.4** - MIT licensed but requires web browser/Jupyter. Not suitable for standalone desktop app.

### Phase Diagram (Interactive)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Matplotlib** | >=3.5 | Existing (already in stack) | Reuse existing phase_diagram.py logic with Qt backend for interactivity |
| **PyQt6** | (above) | Qt widget hosting | Embed matplotlib figure in Qt for click events |

The existing `quickice/output/phase_diagram.py` uses matplotlib. For interactivity, use `matplotlib.backends.backend_qtagg` (for PyQt6).

### Installation

```bash
# Core GUI dependencies
pip install PyQt6>=6.11.0

# 3D visualization with Qt support
pip install "vtk[qt]>=9.6.1"

# Verify matplotlib Qt backend (included with matplotlib)
pip install "matplotlib>=3.5"
```

---

## Existing Stack (Preserve)

These are already in use and work well:

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| Python | 3.14.3 | Runtime | ✓ Working |
| numpy | 2.4.3 | Array computing | ✓ Working |
| scipy | >=1.8 | Scientific computing | ✓ Working |
| matplotlib | >=3.5 | Phase diagram visualization | ✓ Working |
| genice2 | 2.2.13.1 | Ice structure generation | ✓ Working |
| spglib | 2.7.0 | Crystal validation | ✓ Working |

---

## License Compatibility Matrix

| Library | License | Compatible with QuickIce (MIT) | Notes |
|---------|---------|-------------------------------|-------|
| **GenIce2** | MIT | YES | Already in use |
| **PyQt6** | GPL-3.0 | YES* | Requires QuickIce to be GPL-compatible OR purchase commercial license |
| **PySide6** | LGPL | YES | More permissive, recommended if commercial license needed |
| **VTK** | BSD-3-Clause | YES | Permissive, no restrictions |
| **py3Dmol** | MIT | YES | MIT but web-based (not suitable for desktop) |
| **Matplotlib** | PSF | YES | Permissive, no restrictions |

*\*QuickIce is currently MIT licensed. Using PyQt6 would require QuickIce to become GPL-compatible or purchase a commercial license from Riverbank Computing.*

---

## Architecture Integration

### Component Boundaries

```
┌─────────────────────────────────────────────────────┐
│              QuickIce GUI Application               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────┐     ┌───────────────────┐   │
│  │  Input Panel     │     │  Phase Diagram    │   │
│  │  (T, P, N_mol)   │────▶│  Widget           │   │
│  │  [PyQt6]         │     │  (Matplotlib+Qt)  │   │
│  └──────────────────┘     └───────────────────┘   │
│           │                         │              │
│           ▼                         ▼              │
│  ┌─────────────────────────────────────────────┐  │
│  │           Core CLI Logic (existing)         │  │
│  │  • phase_mapping                           │  │
│  │  • structure_generation (GenIce2)          │  │
│  │  • ranking                                  │  │
│  │  • output                                   │  │
│  └─────────────────────────────────────────────┘  │
│           │                                        │
│           ▼                                        │
│  ┌──────────────────┐     ┌───────────────────┐   │
│  │  Results Panel   │     │  3D Viewer        │   │
│  │  (Ranked list)   │────▶│  (VTK + Qt)       │   │
│  │  [PyQt6]         │     │  Ball+stick + HB  │   │
│  └──────────────────┘     └───────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Data Flow

1. User enters T, P, N_molecules in Input Panel (PyQt6)
2. Click "Generate" triggers existing CLI logic
3. PDB files created in temp directory
4. Phase Diagram updates to show user point (Matplotlib+Qt)
5. Results Panel shows ranked candidates (PyQt6)
6. User clicks candidate → VTK renders 3D structure

---

## Version Compatibility

| Component | Python Version | Status |
|-----------|---------------|--------|
| QuickIce (existing) | Python 3.14 | ✓ Working |
| PyQt6 | >=3.10 | ✓ Compatible |
| VTK | 9.6.1 (Python 3.10-3.14) | ✓ Compatible |
| Matplotlib | >=3.5 | ✓ Already installed |
| GenIce2 | 2.2.13.1 | ✓ Already installed |

**Note:** VTK 9.6.1 supports Python 3.10-3.14. QuickIce uses Python 3.14.3 (from env.yml).

---

## Alternative Approaches Considered

### Option 1: Web-Based GUI (Flask + 3Dmol.js)

| Pros | Cons |
|------|------|
| py3Dmol is native | Requires browser runtime |
| Modern UI | More complex deployment |
| Cross-platform by default | Not a traditional desktop app |

**Verdict:** Not recommended for v2.0 - adds deployment complexity without significant benefit.

### Option 2: Tkinter + Matplotlib

| Pros | Cons |
|------|------|
| Built into Python | Limited 3D capabilities |
| No extra dependencies | Ugly on Linux, dated look |
| Simpler licensing | Poor scaling for complex UIs |

**Verdict:** Not recommended - inadequate for 3D molecular visualization.

### Option 3: Kivy

| Pros | Cons |
|------|------|
| Great mobile support | Not ideal for desktop scientific apps |
| Cross-platform | Less mature than Qt |

**Verdict:** Not recommended - Qt is better suited for desktop scientific applications.

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **PyQt5** | Older, use PyQt6 for new development | PyQt6 |
| **py3Dmol for desktop** | Designed for Jupyter, not standalone apps | VTK + Qt |
| **Mayavi** | Less maintained than VTK, more complex installation | VTK |
| **wxPython** | Good but less suited for scientific visualization than Qt | PyQt6 |
| **TensorFlow** | Heavy (~500MB), complex for inference | NumPy (not needed for this project) |

---

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| GUI Framework | HIGH | PyQt6 is industry standard, verified current version 6.11.0 (2026-03-30) |
| 3D Visualization | HIGH | VTK is proven, verified Python 3.14 support with version 9.6.1 (2026-03-26) |
| Licensing | HIGH | Verified all licenses, checked compatibility with MIT |
| Integration | MEDIUM | Qt+VTK integration pattern is standard but needs phase-specific implementation |

---

## Sources

- PyQt6: https://pypi.org/project/PyQt6/ (Version 6.11.0, released 2026-03-30)
- VTK: https://pypi.org/project/vtk/ (Version 9.6.1, released 2026-03-26)
- py3Dmol: https://pypi.org/project/py3Dmol/ (Version 2.5.4, MIT licensed)
- GenIce2: https://github.com/genice-dev/GenIce2 (MIT licensed)
- VTK Qt integration: https://docs.vtk.org/en/latest/interfaces/python.html
- Matplotlib Qt backend: https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html
- PySide6 (alternative): https://pypi.org/project/PySide6/

---

*Stack research for: QuickIce v2.0 GUI Application*  
*Researched: 2026-03-31*