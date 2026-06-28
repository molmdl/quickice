# Research Summary: Dock Panel System

**Domain:** QDockWidget-based panel organization for VTK-centric GUI redesign
**Researched:** 2025-06-28
**Overall confidence:** HIGH (API verified via live PySide6 6.10.2 testing + Qt 6.11 official docs)

## Executive Summary

Replacing QuickIce's QTabWidget with a QDockWidget-based dockable panel system is technically sound and well-supported by PySide6 6.10.2. The QDockWidget API provides all necessary capabilities: contextual panel show/hide, tabification of docked panels, state serialization via `saveState()`/`restoreState()`, and floating windows for independent panels like the phase diagram.

The recommended approach is a **hybrid panel-switching model**: tool-specific parameter panels are tabified on the left dock area (one visible at a time, switched by toolbar selection), while shared utility panels (Log, Phase Diagram) occupy persistent dock positions. This mirrors ParaView's proven pattern of a contextual Properties panel that changes based on the active pipeline object, adapted for QuickIce's sequential tool workflow.

The central widget becomes the single VTK viewport — a `QVTKRenderWindowInteractor` — maximized by removing competing per-tab viewers. All six current tab panels map to four left-dock parameter panels (Ice, Hydrate, Interface, Modifiers) and one right-dock results panel, with the phase diagram and log as separate dockable panels.

Key risk: `saveState()` requires unique `objectName` on every QDockWidget, and the binary state format is Qt-internal (not forward-compatible across major Qt upgrades). VTK resize handling is confirmed smooth — Qt's layout engine automatically resizes the central widget when dock areas change, and VTK's `QVTKRenderWindowInteractor` responds to Qt resize events natively.

## Key Findings

**Stack:** PySide6 6.10.2 QDockWidget API is complete — `setDockLocation()` (new 6.9), `tabifyDockWidget()`, `saveState()`/`restoreState()`, `toggleViewAction()` for menu integration, `AllowNestedDocks` + `AllowTabbedDocks` for flexible layout.

**Architecture:** Hybrid contextual-switching model: tabified left dock for parameter panels (show one at a time by tool selection), persistent right/bottom docks for shared panels, floating-capable phase diagram dock. Central widget = single VTK viewport.

**Critical pitfall:** `saveState()`/`restoreState()` version numbers must match exactly — version mismatch causes silent failure (returns `False`). All QDockWidgets must have unique `objectName` set, or state saving silently fails (warnings printed to stderr). Also, `toggleViewAction.setChecked()` does NOT reliably show/hide the dock in offscreen mode — must use `dock.show()`/`dock.hide()` directly.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Dock skeleton** — Replace QTabWidget central widget with dock layout. Central VTK widget + empty dock containers. `objectName` on every dock from day one.
   - Addresses: foundational architecture change
   - Avoids: saveState failures from missing objectNames

2. **Panel migration** — Move each tab's content widget into its corresponding dock. Wire toolbar buttons to show/hide docks. Implement tabified left-dock switching.
   - Addresses: all 6 panels → 4+ docks mapping
   - Avoids: breaking existing signal connections (panels preserved as-is initially)

3. **Contextual switching** — Toolbar-driven panel context. When tool changes, parameter dock switches content, shared docks update, VTK viewport updates.
   - Addresses: ParaView-style contextual Properties panel
   - Avoids: user confusion from seeing irrelevant parameters

4. **State serialization** — `saveState()`/`restoreState()` + QSettings for per-panel content state. Layout persistence across sessions.
   - Addresses: user customization, layout restoration
   - Avoids: losing user's preferred dock arrangement on restart

5. **Phase diagram dock** — Extract PhaseDiagramPanel from Ice tab, make it a standalone floating/dockable panel. Optionally port to VTK-based rendering.
   - Addresses: phase diagram as always-available reference, not trapped in one tab
   - Avoids: forcing users to switch tabs to see phase diagram

**Phase ordering rationale:**
- Dock skeleton must come first (all subsequent work depends on it)
- Panel migration before contextual switching (need panels in docks before switching logic)
- State serialization after panel migration (need stable layout before saving it)
- Phase diagram dock can be parallelized with state serialization

**Research flags for phases:**
- Phase 2 (Panel migration): Need to audit every signal connection in MainWindow — 2126 lines of connection code
- Phase 3 (Contextual switching): Need research on toolbar design (tool-mode-system research subtask)
- Phase 5 (Phase diagram): LOW confidence on VTK-based phase diagram feasibility — needs dedicated feasibility study

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All APIs verified via live PySide6 6.10.2 testing + Qt 6.11 official docs |
| Features | HIGH | Based on ParaView/ChimeraX pattern analysis + Qt docs |
| Architecture | HIGH | Hybrid model validated by API testing, state save/restore confirmed working |
| Pitfalls | HIGH | All pitfalls discovered via live testing (saveState requirements, version mismatch, toggleViewAction behavior) |

## Gaps to Address

- VTK-based phase diagram rendering feasibility (matplotlib → VTK migration)
- Toolbar UX design for tool switching (overlaps with tool-mode-system research)
- Per-panel content state serialization strategy (QSettings schema design)
- Accessibility: keyboard navigation between docks (Tab order, shortcuts)
- Dual-viewer support: how the existing DualViewerWidget maps to a single-viewport model
