# Feature Landscape: Dock Panel System

**Domain:** QDockWidget-based panel organization for VTK-centric GUI
**Researched:** 2025-06-28
**Confidence:** HIGH (verified via live testing + Qt docs + scientific tool analysis)

## Table Stakes

Features users expect from a professional scientific visualization GUI with dockable panels.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Dockable panels | Standard in ParaView, ChimeraX, OVITO, PyMOL | Low | QDockWidget provides this natively |
| Persistent layout | Users expect their custom layout to survive restart | Low | `saveState()`/`restoreState()` + QSettings |
| View menu for panel visibility | Standard in all dock-based apps | Low | `toggleViewAction()` provides this for free |
| Floating windows | Users expect to pop out panels for multi-monitor | Low | `setFloating(True)` natively supported |
| Contextual parameter switching | ParaView Properties panel changes by selected object | Medium | Toolbar → `raise_()` on tabified dock |
| Resize handles | Users expect to drag dock edges | Low | QDockWidget has built-in resize handles |
| Tab switching within dock area | Multiple panels in same dock space | Low | `tabifyDockWidget()` + tab bar |
| Close/restore panels | X button on dock, View menu to restore | Low | `DockWidgetClosable` + toggleViewAction |

## Differentiators

Features that would set QuickIce apart from typical scientific GUIs.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| VTK-based phase diagram | Unified rendering pipeline, no matplotlib dependency | High | Requires 2D VTK rendering of phase regions |
| Tool-aware panel suggestions | When interface is generated, suggest switching to Solute tool | Medium | Context-aware workflow hints |
| Layout presets | "Minimal" (just viewport), "Full" (all panels), "Debug" (max info) | Low | `saveState()` blob per preset |
| Side-by-side comparison dock | Dock the old + new structure side by side | Medium | Dual viewport in a dock (currently DualViewerWidget) |
| Overlay layer controls | Toggle visibility of ice/water/ions/solutes independently | Medium | VTK actor visibility per tool layer |
| Pin/unpin panels | Auto-hide panels that slide out on hover | Medium | QDockWidget doesn't natively support this; need custom animation |
| Session save/restore | Full session state (all inputs, results, layout) | High | Beyond layout state — includes all generation results |

## Features from Scientific Tools

### ParaView Pattern: Pipeline Browser + Properties Panel

| ParaView Feature | Applicable to QuickIce? | How |
|-------------------|------------------------|-----|
| Pipeline Browser (left) | YES — becomes Tool Browser / Toolbar | Toolbar buttons replace pipeline tree |
| Properties Panel (contextual) | YES — parameter docks switch by tool | Tabified left dock, raise_() on tool selection |
| Statistics panel (right) | YES — Results dock | Structure info, density, energies |
| View menu with panel toggles | YES — standard QDockWidget pattern | toggleViewAction() per dock |
| Apply button (deferred execution) | PARTIAL — QuickIce already has Generate buttons | Keep per-tool Generate/Apply in param dock |
| Multiple view layouts | PARTIAL — could support split viewport later | Low priority; single viewport is cleaner |
| Color map editor | YES — for VTK viewport coloring | Future: atom coloring, property-based coloring |
| Find data selector | NO — QuickIce doesn't search data | Not applicable |
| Time animation controls | NO — no trajectory data | Not applicable |
| Python Shell dock | MAYBE — advanced feature | Could add for scripting |

### ChimeraX Pattern: Tool Shelf + Command Line

| ChimeraX Feature | Applicable to QuickIce? | How |
|-------------------|------------------------|-----|
| Tool shelf (left icons) | YES — toolbar with tool icons | Toolbar buttons for Ice/Hydrate/Interface/etc |
| Command line (bottom) | MAYBE — CLI already exists separately | Could embed command panel in Log dock |
| Side view (zoom/clipping) | NO — VTK viewport handles this natively | VTK trackball camera already provides |
| Model panel | YES — could show loaded structures | Results dock could list structure hierarchy |
| Log panel | YES — Log dock | Status messages, generation logs |
| Floating tool windows | YES — Phase Diagram dock | Floating by default |

### OVITO Pattern: Modifier Stack

| OVITO Feature | Applicable to QuickIce? | How |
|----------------|------------------------|-----|
| Modifier stack (left) | PARTIALLY — QuickIce has sequential pipeline | Modifiers dock (Solute/Ion/Custom) as stack |
| Properties panel (right) | YES — Results dock | Per-structure properties |
| Viewport (center) | YES — central VTK widget | Same concept |
| Animation timeline | NO — no trajectory | Not applicable |
| Data inspection overlay | MAYBE — hover info on atoms | Future VTK feature |

### PyMOL Pattern: Internal GUI

| PyMOL Feature | Applicable to QuickIce? | How |
|----------------|------------------------|-----|
| Internal GUI (right sidebar) | NO — too cramped for QuickIce's param panels | QuickIce panels are wider than PyMOL's |
| External GUI (separate window) | YES — Phase Diagram floating | Phase diagram as floating window |
| Object list | PARTIALLY — structure hierarchy | Results dock with expandable structure tree |
| Command line | NO — QuickIce is GUI-first | Not the target UX |

## Anti-Features

Features to explicitly NOT build. Common mistakes in scientific GUI dock systems.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Infinite dock nesting | Creates chaotic layouts, confuses users | Limit nesting with `AllowNestedDocks` but not `ForceTabbedDocks` |
| All panels always visible | Screen clutter, especially on laptops | Contextual switching — show only relevant params |
| Per-tool VTK viewports | Defeats the purpose of single-viewport redesign | Single VTK viewport, swap actors on tool switch |
| Dock-within-dock-within-dock | Nightmare UI, users can't restore layout | Max 2 levels: tabified within a dock area |
| Saving panel state as raw text | Fragile, breaks when panels change | Use QSettings with type-safe keys |
| Custom title bar for every dock | Maintenance burden, inconsistent look | Use native QDockWidget title bar |
| Drag-and-drop panel reordering | QDockWidget handles this natively — don't reinvent | Use built-in drag/dock behavior |
| Tab bar for param panels below left dock | Wastes horizontal space | Use `setTabPosition(LeftDockWidgetArea, QTabWidget.TabPosition.North)` or vertical tabs |

## Feature Dependencies

```
Dock skeleton (central VTK + dock containers)
  ├── Panel migration (move tab content to docks)
  │   ├── Contextual switching (toolbar → raise_())
  │   │   └── Tool-aware suggestions (when interface done, suggest solute)
  │   ├── State serialization (saveState + QSettings)
  │   │   └── Layout presets (named state blobs)
  │   └── VTK scene manager (unified rendering)
  │       └── Overlay layer controls (per-tool actor visibility)
  └── Phase diagram dock (extract from Ice tab)
      └── VTK-based phase diagram (future milestone)
```

## MVP Recommendation

For MVP of the dock panel system, prioritize:

1. **Dock skeleton** — Central VTK + 4 param docks (tabified) + Results dock + Log dock
2. **Contextual switching** — Toolbar → raise_() on tabified param docks
3. **State serialization** — `saveState()`/`restoreState()` for layout persistence
4. **Phase diagram dock** — Floatable, separate from Ice params

Defer to post-MVP:
- **VTK-based phase diagram**: High complexity, marginal UX gain over matplotlib
- **Layout presets**: Nice-to-have, can be added with a few `saveState()` calls
- **Tool-aware suggestions**: Requires workflow state machine, separate research
- **Side-by-side comparison dock**: DualViewerWidget in a dock is doable but needs VTK scene manager first
- **Overlay layer controls**: Needs VTK scene manager first

## Sources

- Qt 6.11 QMainWindow documentation: https://doc.qt.io/qt-6/qmainwindow.html (HIGH confidence)
- Qt 6.11 QDockWidget documentation: https://doc.qt.io/qt-6/qdockwidget.html (HIGH confidence)
- ParaView User Guide: https://docs.paraview.org/en/latest/UsersGuide/introduction.html (HIGH confidence — confirmed ParaView uses dock-based layout with contextual Properties panel)
- ChimeraX User Guide: https://www.cgl.ucsf.edu/chimerax/docs/user/ (MEDIUM confidence — confirmed tool shelf pattern)
- Live PySide6 6.10.2 testing (HIGH confidence — all API behaviors verified)
