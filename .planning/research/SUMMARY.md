# Project Research Summary

**Project:** QuickIce v2.0 — Adding GUI with interactive phase diagram and 3D molecular viewer  
**Domain:** Cross-platform desktop GUI application for scientific visualization  
**Researched:** 2026-03-31  
**Confidence:** HIGH

---

## Executive Summary

QuickIce v2.0 transforms the existing CLI tool into a cross-platform desktop GUI application with interactive phase diagram and 3D molecular visualization. Research confirms that scientific GUI applications in this domain consistently use Qt-based frameworks (PyQt6/PySide6) paired with VTK for 3D rendering. The recommended approach is **PySide6 (LGPL)** with **VTK 9.6.x** — this maintains MIT license compatibility while providing mature, well-documented libraries that support Python 3.14.

The critical insight from architecture research is that the GUI must call existing Python modules directly (not invoke the CLI as subprocess), preserving the existing CLI business logic while adding a presentation layer using MVVM pattern. The biggest risks are UI freezing during computation (must use QThread workers), 3D rendering performance at scale (VTK handles 216 molecules well), and cross-platform path handling (use pathlib throughout).

---

## Key Findings

### Recommended Stack

**Core technologies:**
- **PySide6 6.11.0** — Primary GUI framework (LGPL, MIT-compatible) — industry standard for cross-platform desktop apps with Python 3.14 support
- **VTK 9.6.1** — 3D rendering engine (BSD-licensed) — proven in scientific visualization, excellent Qt integration via `vtkQt`
- **Matplotlib Qt backend** — Existing library reused for interactive phase diagram via `matplotlib.backends.backend_qtagg`
- **GenIce2** — Preserved (MIT licensed, fully compatible)

**License note:** Using PyQt6 would require QuickIce to become GPL-compatible or purchase a commercial license. PySide6 with LGPL is recommended to maintain MIT licensing.

### Expected Features

**Must have (table stakes):**
- Temperature/pressure/molecule count inputs with validation — core parameters
- Generate button with progress bar — primary action trigger
- Phase diagram display (static image initially) — visual T,P→phase mapping
- Click-to-select on phase diagram — intuitive input method
- Basic 3D viewer with ball-and-stick representation — display generated structures
- Zoom/pan/rotate controls — explore 3D structures
- Save PDB file — export generated structure

**Should have (competitive):**
- Phase info window with citations — scientific credibility
- Stick representation mode — alternative visualization
- Hydrogen bond visualization — shows ice hydrogen network
- Help tooltips — reduces learning curve

**Defer (v2+):**
- Markdown manual viewer — nice to have, not essential
- Recent calculations history — session-based is fine for MVP
- Multiple structure comparison — requires multiple viewports

### Architecture Approach

The recommended architecture is **Model-View-ViewModel (MVVM)** with a dedicated backend service layer wrapping existing CLI modules. The GUI calls existing Python modules directly (phase_mapping, structure_generation, ranking) rather than invoking the CLI as a subprocess — this preserves typed objects and avoids fragile output parsing.

Key components:
1. **View Layer (PySide6)** — Main window, input panel, phase diagram widget, 3D viewer widget
2. **ViewModel Layer** — MainViewModel, DiagramViewModel, ViewerViewModel for UI state and commands
3. **PipelineService** — Async wrapper for generation pipeline with progress callbacks
4. **DiagramService** — Interactive phase diagram with click selection
5. **ViewerService** — 3D molecular structure rendering with VTK

### Critical Pitfalls

1. **UI Freezing During Computation** — GenIce generation blocks the main thread; must use QThread with worker objects for background processing
2. **3D Rendering Performance** — 216 water molecules (648 atoms) can stress naive rendering; use VTK's batch rendering with sphere/cylinder impostors
3. **Cross-Platform File Path Handling** — Hardcoded paths fail on Windows; use `pathlib.Path` for all file operations
4. **State Synchronization** — Interactive phase diagram and 3D viewer must stay synchronized; implement proper signal/slot mechanisms
5. **Progress Feedback Errors** — Progress callbacks must be thread-safe; use Qt signals, update every 100-500ms

---

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: GUI Infrastructure + Core Input
**Rationale:** Establishes the foundation all other phases depend on. Without the main window, input handling, and basic service layer, nothing else works.
**Delivers:** PySide6 main window with input fields, validation, Generate button, basic progress display
**Addresses:** Temperature/pressure/N inputs, input validation, Generate button
**Avoids:** UI freezing (threading infrastructure built from start)

### Phase 2: Phase Diagram Integration
**Rationale:** The phase diagram is the primary visual interface and depends on having the input system working
**Delivers:** Interactive phase diagram widget with click-to-select, T,P field updates from clicks
**Addresses:** Phase diagram display, click to select T,P, current selection indicator
**Avoids:** Coordinate mapping pitfalls by using matplotlib's built-in transforms

### Phase 3: 3D Molecular Viewer
**Rationale:** The main differentiator — users need to visualize generated ice structures. Requires VTK integration and threading working correctly.
**Delivers:** VTK-based 3D viewer with ball-and-stick, zoom/pan/rotate, hydrogen bond visualization
**Addresses:** 3D viewport, ball-and-stick, zoom/pan/rotate, H-bond visualization
**Avoids:** Rendering performance issues by using VTK batch rendering

### Phase 4: Save/Export + Polish
**Rationale:** Users need to export results; also addresses minor UI polish items
**Delivers:** Save PDB dialog, export phase diagram, theme toggle, help tooltips
**Addresses:** Save PDB, Save phase diagram, Dark/light theme
**Avoids:** Cross-platform path issues (pathlib used throughout), export mismatch (same render settings for display and export)

### Phase Ordering Rationale

- Phase 1 first: All other phases build on GUI infrastructure and threading
- Phase 2 before 3: Phase diagram is the input method; 3D viewer is output visualization
- Phase 3 complexity: 3D rendering is the most technically challenging — handled after simpler features work
- Phase 4 last: Export is a "nice to have" that completes the workflow

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (3D Viewer):** VTK + PySide6 integration has standard patterns but needs phase-specific implementation for molecular rendering; may need to research ball-and-stick actor construction
- **Phase 1 (Threading):** GenIce progress callbacks may need wrapper implementation to report granular progress

Phases with standard patterns (skip research-phase):
- **Phase 1:** PySide6 basic window + form is well-documented
- **Phase 2:** Matplotlib Qt integration is standard pattern

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages verified for Python 3.14; PySide6/VTK versions confirmed from PyPI (2026-03-30/26) |
| Features | MEDIUM-HIGH | Based on scientific visualization tool patterns (OVITO, Avogadro); some features inferred |
| Architecture | HIGH | MVVM + threading patterns well-documented; direct module import recommended |
| Pitfalls | MEDIUM-HIGH | Common patterns for CLI-to-GUI transition; some pitfalls are preventive |

**Overall confidence:** HIGH

### Gaps to Address

- **GenIce progress callbacks:** Not confirmed if GenIce exposes progress hooks; may need to wrap and estimate progress based on known generation steps
- **VTK molecular rendering specifics:** Need to verify exact API for ball-and-stick with colors (O=red, H=white) at implementation time
- **Phase diagram boundary data:** Need to confirm existing `quickice/phase_mapping` exports boundary data in structured format for interactive plotting

---

## Sources

### Primary (HIGH confidence)
- PySide6: https://pypi.org/project/PySide6/ — Version 6.11.0 (2026-03-23), Python 3.14 explicit support
- VTK: https://pypi.org/project/vtk/ — Version 9.6.1 (2026-03-26), cp314 wheels available
- PyQt Threading Documentation: https://doc.qt.io/qtforpython-6/overviews/qthread.html — Official Qt threading patterns

### Secondary (MEDIUM confidence)
- OVITO (https://www.ovito.org/) — Scientific visualization tool patterns
- Avogadro (https://github.com/avogadro/avogadro) — Molecular editor reference
- Matplotlib Qt backend: https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html

### Tertiary (LOW confidence)
- GenIce2: https://github.com/genice-dev/GenIce2 — Verified MIT license, but progress callback API not deeply researched

---

*Research completed: 2026-03-31*
*Ready for roadmap: yes*