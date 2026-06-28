# Synthesis: Integrated VTK-Centric GUI for QuickIce

**Date:** 2026-06-28
**Sources:** 5 research agents (22 files total)
**Verdict:** GO WITH CONDITIONS

---

## Executive Summary

All five research agents converge on the same conclusion: replacing QuickIce's 6-tab layout with a single VTK viewport surrounded by dockable panels is technically feasible, architecturally sound, and requires zero new dependencies. VTK 9.5.2 provides every API needed (`vtkAssembly` for phase grouping, `SetViewport()` for split-view, `SetLayer()` for 2D overlays, `vtkContourWidget` for 3D region drawing, and full interactor style switching). PySide6 6.10.2's `QDockWidget` system provides tabification, state serialization, and contextual panel switching — all verified by live testing. The comparative analysis confirms this pattern is universal across every major scientific visualization tool (ParaView, ChimeraX, OVITO, VMD, PyMOL): single viewport + docked panels + toolbar-driven modes.

The key architectural decision is the data model. The current 2126-line `MainWindow` stores pipeline state as 9 `_current_*` attributes — a god-object that makes decomposition impossible. The data-flow-migration agent proved that a `PipelineSession` dataclass implementing an OVITO-style linear modifier stack (Source → Interface → Custom → Solute → Ion → Export) maps 1:1 to the existing physical pipeline and cleanly replaces all 9 attributes with typed step outputs. This is the **prerequisite for everything else**: without centralized state, decomposing MainWindow just distributes the god-object across 4 files. With PipelineSession, the decomposition is clean and the dock migration becomes straightforward.

The conditions for GO are: (1) PipelineSession extraction MUST happen before any other architectural change, (2) GUI integration tests must be written before MainWindow decomposition begins (there are currently zero), and (3) a coexistence period with `--layout tabs` vs `--layout integrated` is required for one release cycle to ensure no regressions. The polycrystalline builder (v8.0) is the primary scientific motivation for this redesign — it requires interactive 3D region drawing, multi-phase visualization, and a 2D shape editor alongside the 3D viewport, none of which fit in the current tab model. The integrated GUI enables the polycrystal builder as a natural tool mode rather than an awkward tab appendage.

---

## Unified Architecture

The architecture merges findings from all five agents into a single coherent design:

```
┌──────────────────────────────────────────────────────────────────┐
│  Menu Bar: File  Edit  View  Tools  Help                        │
├──────────────────────────────────────────────────────────────────┤
│  Toolbar: [Ice|Hydrate|Interface|Custom|Solute|Ion] [Tools ▾]  │
├────────────┬─────────────────────────────────┬───────────────────┤
│            │                                 │                   │
│ PIPELINE   │    VTK VIEWPORT                 │ PROPERTIES        │
│ NAVIGATOR  │    (QVTKRenderWindowInteractor) │ (contextual)      │
│ (left dock)│                                 │                   │
│            │    vtkAssembly groups:           │ Active step       │
│ ◉ Source   │    ├─ ice (cyan bonds)          │ parameters        │
│ │ Ice/Hyd  │    ├─ water (blue bonds)        │ here              │
│ ◉ Modify   │    ├─ guests (gray B&S)         │                   │
│ │ Interface│    ├─ solute (orange B&S)       │ ┌───────────────┐│
│ │ Custom   │    ├─ ions (gold/green spheres) │ │ T: 250 K      ││
│ │ Solute   │    ├─ custom (purple B&S)       │ │ P: 0.1 MPa    ││
│ │ Ion      │    └─ unit_cell (wireframe)     │ │ n: 768         ││
│ ◉ Export   │                                 │ │ [Generate]     ││
│ │ GROMACS  │    Layer 1 overlay:             │ └───────────────┘│
│            │    ├─ Phase labels (vtkTextActor)│                   │
│            │    └─ Status annotations         │                   │
│            │                                 │                   │
│ STRUCTURE  │                                 │ RESULTS           │
│ MANAGER    │                                 │ (info, density,   │
│ (sub-dock) │                                 │  atom count)     │
│ [ice☑][wat☑][ion☑]                          │                   │
├────────────┴─────────────────────────────────┴───────────────────┤
│  LOG / STATUS BAR                               [Navigate ▾]    │
└──────────────────────────────────────────────────────────────────┘

  Floating: Phase Diagram Dock (matplotlib, always-available reference)
```

### Component Boundaries (Consolidated)

| Component | From Agent | Responsibility | Communicates With |
|-----------|-----------|-----------------|-------------------|
| **PipelineSession** | data-flow-migration | Central state: typed step outputs, source type, ranking | All managers (receives, never reads MainWindow) |
| **PipelineManager** | data-flow-migration | Step execution, worker lifecycle, progress | PipelineSession, all workers |
| **ViewerManager** | data-flow-migration + single-viewport-arch | UnifiedViewerWidget lifecycle, actor group updates, camera | PipelineSession, PipelineManager |
| **ExportManager** | data-flow-migration | Export routing per step, filename conventions, file dialogs | PipelineSession |
| **DockManager** | dock-panel-system + data-flow-migration | QDockWidget creation, tabification, contextual `raise_()`, saveState | PipelineSession, ToolModeManager |
| **ToolModeManager** | tool-mode-system | Interactor style switching, widget lifecycle, cursor, status hints | VTK viewport, DockManager, Toolbar |
| **UnifiedViewerWidget** | single-viewport-arch | Single `QVTKRenderWindowInteractor`, `vtkAssembly` groups, camera | ViewerManager |
| **StructureActorBuilder** | single-viewport-arch | Any structure type → `dict[str, vtkAssembly]` | UnifiedViewerWidget |
| **ActorGroup** | single-viewport-arch | `vtkAssembly` wrapper with visibility/opacity/representation API | UnifiedViewerWidget |
| **PipelineNavigator** | comparative-analysis + dock-panel-system | Visual modifier stack, step selection, toggle checkboxes | DockManager, Properties panel |
| **StructureManager** | comparative-analysis | Per-layer visibility, color, opacity checkboxes | UnifiedViewerWidget |
| **VTKSceneManager** | dock-panel-system | Actor add/remove lifecycle, incremental updates | UnifiedViewerWidget |

### Data Flow (Unified)

```
User edits parameter in Properties panel
    │
    ▼
PipelineManager.run_step(kind, **params)
    │
    ▼
Worker executes on QThread
    │
    ▼
PipelineSession.steps[kind].output = result
    │
    ├──► ViewerManager.update_from_step(kind)
    │       StructureActorBuilder.build(result) → dict[str, vtkAssembly]
    │       UnifiedViewerWidget.update_actors(assemblies)
    │       Incremental: only replace changed phase assembly
    │       Camera: reset only on base structure change
    │
    ├──► DockManager.on_step_completed(kind)
    │       PipelineNavigator: mark step as completed
    │       Results dock: update structure info
    │
    └──► StructureManager.on_step_completed(kind)
            Update layer visibility checkboxes
```

---

## Migration Plan

### Phase 0: PipelineSession Extraction — NO GUI CHANGE
**Source:** data-flow-migration/ARCHITECTURE.md §7
**Rationale:** Every subsequent phase depends on centralized state. Without PipelineSession, decomposition creates distributed coupling.
**Delivers:** PipelineSession dataclass alongside existing `_current_*` attributes, with bridge properties.
**LOC:** ~230 (200 PipelineSession + 30 bridge lines)
**Features:** None visible — internal only
**Pitfalls avoided:** Distributed coupling during decomposition (Pitfall 1), broken attribute propagation chain (Pitfall 2)
**Effort:** 2-3 days

### Phase 1: MainWindow Decomposition — NO VISIBLE GUI CHANGE
**Source:** data-flow-migration/ARCHITECTURE.md §7
**Rationale:** 2126-line MainWindow must be decomposed before VTK viewer or layout changes. Managers need PipelineSession as shared state.
**Delivers:** 4 concern-managers (PipelineManager, ViewerManager, ExportManager, DockManager), MainWindow shrinks from 2126 to ~200 lines.
**LOC:** ~1100 (managers) net, -1800 from MainWindow
**Features:** None visible — all existing functionality preserved
**Pitfalls avoided:** God-object distribution (Pitfall 1), circular manager dependencies (Pitfall 8), signal wiring explosion (Pitfall 5)
**Critical prerequisite:** GUI integration tests must exist before Phase 1 starts
**Effort:** 5-8 days

### Phase 2: UnifiedViewerWidget — VISIBLE CHANGE (viewport only)
**Source:** single-viewport-arch/ARCHITECTURE.md, single-viewport-arch/FEATURES.md
**Rationale:** Replace 6 separate VTK viewers with 1 central widget using vtkAssembly groups. Still in tab containers.
**Delivers:** Single render window, consolidated actor builder, visibility toggling, smart camera management.
**LOC:** ~500 (unified_viewer + actor_group + structure_actor_builder)
**Features:** Simultaneous all-phase view, phase-distinct coloring, visibility toggling, incremental actor updates
**Pitfalls avoided:** Assembly visibility semantics mismatch (single-viewport-arch Pitfall 1), camera reset on downstream addition (Pitfall 5), memory leak from stale refs (Pitfall 4), O(n²) bond detection (Pitfall 6), duplicate `_extract_bonds()` (Pitfall 12-13), triclinic PBC bug in bond extraction (Pitfall 14)
**Effort:** 5-7 days

### Phase 3: QDockWidget Migration — ARCHITECTURAL TRANSFORMATION
**Source:** dock-panel-system/ARCHITECTURE.md, dock-panel-system/FEATURES.md
**Rationale:** Replace QTabWidget with dock panel layout. This is the primary UX change.
**Delivers:** Central VTK viewport, tabified left-dock parameter panels, right-dock results, bottom-dock log, floating phase diagram.
**LOC:** ~400 (DockManager expansion + toolbar)
**Features:** Contextual panel switching, layout persistence via saveState/restoreState, View menu for dock visibility, toolbar-driven panel context
**Pitfalls avoided:** Missing objectName on QDockWidget (dock Pitfall 1), saveState version mismatch (Pitfall 2), floating params dock breaking tab switching (Pitfall 6), minimum dock width truncation (Pitfall 7), tabify ordering (Pitfall 8), render storms on dock resize (single-viewport Pitfall 8)
**Coexistence:** `--layout tabs` vs `--layout integrated` feature flag. Timebox to 1 release.
**Effort:** 5-8 days

### Phase 4: Pipeline Navigator + Modifier Stack — UX POLISH
**Source:** comparative-analysis/ARCHITECTURE.md §3, data-flow-migration/ARCHITECTURE.md §3
**Rationale:** Visual representation of the pipeline as an OVITO-style linear modifier stack. Enables step toggling, per-step export, and non-destructive editing.
**Delivers:** Pipeline step list in left dock, step toggle checkboxes, per-step export via menu, contextual properties panel per selected step.
**LOC:** ~350
**Features:** Modifier toggle (disable ion insertion → ions disappear, re-enable → reappear), per-step export, pipeline progress visualization
**Pitfalls avoided:** DAG pipeline engine (comparative-analysis Pitfall 1), full pipeline undo (Pitfall 6), export filename convention change (data-flow Pitfall 6)
**Effort:** 3-5 days

### Phase 5: Tool Mode System — INTERACTIVE TOOLS
**Source:** tool-mode-system/ARCHITECTURE.md, tool-mode-system/FEATURES.md
**Rationale:** Add toolbar-driven tool modes with VTK interactor style switching. Enables Navigate, Select, Measure, Place Molecule, Draw Region, Pick.
**Delivers:** ToolModeManager with pre-built interactor styles and VTK widgets. Toolbar mode buttons. Contextual dock panels per tool.
**LOC:** ~500 (tool_mode_manager + custom styles + widget integration)
**Features:** Navigate (TrackballCamera), Select (atom/molecule picking with vtkPropPicker), Measure (vtkDistanceWidget), Place Molecule (vtkCellPicker + plane projection), Pick (vtkPointPicker + atom info), Draw Region (vtkContourWidget + BoundedPlanePointPlacer)
**Pitfalls avoided:** God-class interactor style (tool-mode Pitfall Anti-1), observer leak on style switching (Pitfall 3), widget event conflict (Pitfall 2), cursor overridden by VTK (Pitfall 7), picker state corruption (Pitfall 4), picker tolerance too low (Pitfall 12), multiple widgets fighting (Pitfall 8)
**Effort:** 5-7 days

### Phase 6: 2D Overlay + Polish — FINISHING TOUCHES
**Source:** single-viewport-arch/ARCHITECTURE.md §5, single-viewport-arch/FEATURES.md
**Rationale:** HUD overlays, opacity animation, measurement annotations, region labels.
**Delivers:** Layer-1 renderer with vtkTextActor labels, vtkCornerAnnotation status, smooth opacity transitions.
**LOC:** ~200
**Features:** Phase labels, measurement annotations, smooth phase fade in/out
**Pitfalls avoided:** 2D Qt overlay on VTK (anti-pattern), 3D text rotation (use 2D overlay instead)
**Effort:** 2-3 days

### Parallelization and Dependencies

```
Phase 0 (PipelineSession) ────────────────────── must be first
    │
    ▼
Phase 1 (Decomposition) ──────────────────────── depends on Phase 0
    │
    ├──► Phase 2 (UnifiedViewer) ── depends on Phase 1
    │         │
    │         ├──► Phase 3 (Docks) ── can partially parallel with Phase 4
    │         │         │
    │         │         └──► Phase 4 (Pipeline Nav) ── depends on Phase 3
    │         │                   │
    │         │                   └──► Phase 5 (Tool Modes) ── depends on Phase 4
    │         │                             │
    │         │                             └──► Phase 6 (Overlay/Polish)
    │         │
    │         └──► Phase 3 and Phase 4 can overlap if split between team members
    │
    └──► Phase 2 must complete before Phase 3 (VTK widget must exist before docks surround it)
```

**Total estimated effort:** 27-41 days (5-8 weeks of focused work)

**Polycrystal builder enablement:** The integrated GUI directly enables v8.0's polycrystal builder by providing:
- **Single viewport** with simultaneous multi-phase visualization (ice, water, hydrate regions rendered as separate vtkAssembly groups with distinct colors)
- **Draw Region tool mode** using `vtkContourWidget` + `vtkBoundedPlanePointPlacer` for 3D plane-constrained polygon drawing directly on the structure
- **QGraphicsView 2D shape editor** as a dock panel for complex multi-region editing with undo/redo (the tool-mode-system research confirmed both approaches are valid for different use cases)
- **PipelineNavigator** extension with a "Polycrystal" step between Interface and Custom/Solute/Ion
- **StructureManager** with per-phase visibility toggling (ice grain 1, ice grain 2, hydrate region, liquid, buffer zones)

---

## Risk Register

### Critical Risks

| # | Risk | Source | Prevention | Detection |
|---|------|--------|------------|-----------|
| R1 | **VTK segfault in headless/CI** | single-viewport-arch Pitfall 2, dock-panel-system Pitfall 3, tool-mode-system Pitfall 1 | Preserve `_VTK_AVAILABLE` detection; mock VTK in unit tests; `QT_QPA_PLATFORM=offscreen` with skip-if for VTK-dependent tests; never create `vtkRenderWindow` in test code | Segfault (signal 11) in CI |
| R2 | **Distributed coupling from premature decomposition** | data-flow-migration Pitfall 1 | ALWAYS extract PipelineSession before decomposing MainWindow; managers receive PipelineSession, never MainWindow; audit for `self._parent._current_*` | Manager depends on MainWindow internals |
| R3 | **Broken solute→ion attribute propagation chain** | data-flow-migration Pitfall 2 | PipelineManager's `run_step(ION)` must auto-chain from the correct upstream step (Solute > Custom > Interface); integration test: full chain export, verify .top [molecules] section | .top file missing molecule types |
| R4 | **SetViewport split-view mouse routing failure** | single-viewport-arch Pitfall 3 | Test early; implement custom interactor style with `FindPokedRenderer(x, y)` if routing fails; QSplitter fallback with 2 VTK widgets | Mouse events only affect one side |
| R5 | **Assembly visibility semantics mismatch** | single-viewport-arch Pitfall 1 | Use `ActorGroup` wrapper with own visibility state; never query `child.GetVisibility()` for rendering state; bind UI to `ActorGroup.set_visible()` | Checkboxes out of sync with rendering |

### Moderate Risks

| # | Risk | Source | Prevention | Detection |
|---|------|--------|------------|-----------|
| R6 | **Signal wiring breaks during dock migration** | data-flow-migration Pitfall 5, dock-panel-system Pitfall 6 | Create wiring checklist before Phase 3; use PipelineManager signals as central routing; per-panel integration tests | Button click doesn't trigger action |
| R7 | **saveState fails silently from missing objectName** | dock-panel-system Pitfall 1 | Set objectName on every QDockWidget at creation; naming convention; CI grep check | Dock reverts to default position on restart |
| R8 | **HydrateWorker QThread subclass incompatibility** | data-flow-migration Pitfall 3, AGENTS.md | PipelineManager wraps HydrateWorker separately (it IS the thread, no moveToThread); don't "fix" per AGENTS.md | Hydrate generation crashes after refactor |
| R9 | **Widget event conflict with interactor style** | tool-mode-system Pitfall 2 | Configure `vtkWidgetEventTranslator` to only intercept left-button; ensure middle/right pass through to TrackballCamera | Can't pan/zoom while using Measure tool |
| R10 | **Observer leak on style switching** | tool-mode-system Pitfall 3 | Every custom style has `activate()`/`deactivate()`; ToolModeManager always calls deactivate before activate; store observer tags | Double-firing callbacks after mode switch |
| R11 | **Export filename convention change** | data-flow-migration Pitfall 6 | ExportManager preserves exact same filename patterns per structure type | Exported filenames differ from current |
| R12 | **VTK render storms on dock resize** | single-viewport-arch Pitfall 8 | Debounce renders with 50ms QTimer; or `SetDesiredUpdateRate(30.0)` to throttle | Flickering during dock drag |

### Minor Risks

| # | Risk | Source | Prevention | Detection |
|---|------|--------|------------|-----------|
| R13 | raise_() not working in offscreen/CI | dock-panel-system Pitfall 4 | Use `setCurrentIndex()` on internal QTabBar for tests; skip visual tests in CI | Tab doesn't switch in test |
| R14 | ContourWidget nodes drift during camera rotation | tool-mode-system Pitfall 5 | Always use `vtkBoundedPlanePointPlacer` with explicit projection normal | Region polygon shifts on rotation |
| R15 | Picker tolerance too low for nm-scale atoms | tool-mode-system Pitfall 12 | Set `cell_picker.SetTolerance(0.002)` or higher; test at various zoom levels | Click on visible atom doesn't register |
| R16 | Duplicate constants (`ANGSTROM_TO_NM`, `_extract_bonds`) | single-viewport-arch Pitfalls 11-13 | Move to `quickice/gui/constants.py` and `StructureActorBuilder` | Bug fix must be applied N times |

**Overall risk assessment:** MEDIUM. The architecture is sound and well-proven by 5 major scientific tools. The critical risks (R1-R5) have clear prevention strategies. The main risk is not technical but organizational: the migration must follow a strict phase ordering (PipelineSession → Decomposition → UnifiedViewer → Docks → Tools) or it will create distributed coupling. The zero GUI test coverage is the biggest gap — adding integration tests is a hard prerequisite for Phase 1.

---

## Technology Stack

### Already Available (No New Dependencies)

| Technology | Version | Role | Verified |
|------------|---------|------|----------|
| **PySide6** | 6.10.2 | Qt GUI framework: QDockWidget, QMainWindow, QToolBar, QUndoStack | YES — all APIs tested |
| **VTK** | 9.5.2 | 3D rendering: vtkAssembly, SetViewport, SetLayer, vtkContourWidget, vtkDistanceWidget, interactor styles | YES — all APIs tested against installed version |
| **numpy** | 2.4.3 | Array operations, VTK point data interop | Already in use |
| **shapely** | (in env) | 2D polygon geometry for polycrystal region definitions (enables Draw Region tool) | Already in environment |

### New Internal Modules Required

| Module | LOC (est.) | Purpose |
|--------|-----------|---------|
| `quickice/gui/pipeline_session.py` | ~200 | PipelineSession + PipelineStep dataclasses (Phase 0) |
| `quickice/gui/pipeline_manager.py` | ~350 | Step execution, worker lifecycle, progress signals (Phase 1) |
| `quickice/gui/viewer_manager.py` | ~250 | UnifiedViewerWidget lifecycle, actor group updates (Phase 1) |
| `quickice/gui/export_manager.py` | ~300 | Export routing per step, filename conventions (Phase 1) |
| `quickice/gui/dock_manager.py` | ~200 | QDockWidget creation, tabification, saveState, feature flag (Phase 1+3) |
| `quickice/gui/unified_viewer.py` | ~200 | Single QVTKRenderWindowInteractor with assembly management (Phase 2) |
| `quickice/gui/structure_actor_builder.py` | ~250 | Consolidated actor creation from any structure type (Phase 2) |
| `quickice/gui/actor_group.py` | ~80 | vtkAssembly wrapper with visibility/opacity/representation API (Phase 2) |
| `quickice/gui/tool_mode_manager.py` | ~200 | Mode registry, style switching, widget lifecycle (Phase 5) |
| `quickice/gui/pipeline_navigator.py` | ~200 | Visual modifier stack dock widget (Phase 4) |

### Key VTK 9.5.2 API Findings

| API | Behavior Note | Confidence |
|-----|--------------|------------|
| `vtkAssembly.SetVisibility(0)` | Hides ALL parts during rendering, but `child.GetVisibility()` still returns 1 — track visibility in wrapper | HIGH (tested) |
| `vtkRenderer.SetViewport(xmin,ymin,xmax,ymax)` | Normalized coordinates; each renderer has its own camera; mouse routing may need custom style | MEDIUM (API verified, interaction untested) |
| `vtkRenderWindow.SetNumberOfLayers(2)` | Layer 0 = 3D scene, Layer 1 = 2D HUD; set `overlay_renderer.SetInteractive(0)` | HIGH (tested) |
| `iren.SetInteractorStyle(new_style)` | Cleanly replaces style; old style retained by Python refcount; observers NOT automatically removed | HIGH (tested) |
| VTK widgets (`vtkDistanceWidget`, etc.) | `SetEnabled(1)` intercepts events; `SetEnabled(0)` passes through; configure event translator for button-specific routing | HIGH (source inspected) |
| `QVTKRenderWindowInteractor` | Inherits QWidget; works as `setCentralWidget()`; auto-renders on resize; `_CURSOR_MAP` maps VTK cursors to Qt | HIGH (source read in full) |
| `vtkRenderWindow` in headless | Segfaults on `QT_QPA_PLATFORM=offscreen` or SSH X11 forwarding | HIGH (confirmed by testing) |

### Framework Alternatives — REJECTED

| Framework | Why Not |
|-----------|---------|
| **trame** | Web-first architecture (browser-based); would replace native PySide6 desktop; massive change for no benefit |
| **PyVista** | Opinionated abstraction fights VTK interactor customization; QuickIce needs custom interactors; PyVista hides the interactor layer |
| **vedo** | Scripting-oriented, no Qt integration story; good for prototyping, bad for production GUI |

---

## Key Design Decisions

### 1. vtkAssembly vs vtkActorCollection vs Flat Actor List
**Decision:** Use `vtkAssembly` for every structural phase.
**Rationale:** `vtkAssembly` provides O(1) visibility toggling for entire phase groups (`SetVisibility(0)` hides all parts), supports hierarchical nesting for sub-groups within a phase, and VTK's rendering pipeline correctly skips invisible assemblies. `vtkActorCollection` is just a list with no group-level rendering optimization. A flat `renderer.AddActor()` list requires O(n) iteration for phase visibility changes and makes actor lifecycle management error-prone at scale.
**Source:** single-viewport-arch/ARCHITECTURE.md Pattern 1

### 2. OVITO Modifier Stack vs ParaView DAG Pipeline
**Decision:** Linear modifier stack (OVITO model). NOT a DAG.
**Rationale:** QuickIce's pipeline is physically constrained to a strict linear order: Source → Interface → Custom → Solute → Ion → Export. Steps cannot be reordered (you can't insert solutes before building the interface). A DAG engine would add cycle detection, type checking at connections, multi-output handling, and visual DAG representation — all for zero benefit since no user will ever build a branching pipeline. The modifier stack is simpler, maps 1:1 to the existing pipeline, and provides the key UX benefit: non-destructive step toggling (disable Ion insertion, see result, re-enable).
**Source:** comparative-analysis/ARCHITECTURE.md Pattern 3, comparative-analysis/PITFALLS.md Pitfall 1

### 3. QGraphicsView vs VTK 3D Drawing for Region Editing
**Decision:** Both — use each where it excels.
**Rationale:** `vtkContourWidget` + `vtkBoundedPlanePointPlacer` is the right tool for simple single-plane region drawing directly in the 3D viewport (e.g., drawing a polygon on the XY plane of the ice structure). QGraphicsView is the right tool for the polycrystal builder's complex multi-region 2D editing with undo/redo, shape creation tools (rectangle, ellipse, polygon), and multi-region management. The tool-mode-system research confirmed both approaches are valid for different use cases. Use VTK 3D drawing for the Draw Region tool mode; use QGraphicsView as a dock panel for the polycrystal builder's shape editor.
**Source:** tool-mode-system/FEATURES.md §3D Shape Drawing Comparison, polycrystalline-builder/shape-gui/SUMMARY.md

### 4. PipelineSession vs `_current_*` Attributes
**Decision:** PipelineSession dataclass replaces all 9 `_current_*` attributes.
**Rationale:** The current 9 `_current_*` attributes on a 2126-line MainWindow make decomposition impossible — every extracted manager would need to read `parent._current_*`, reproducing the god-object across files. PipelineSession centralizes all state in one typed object that managers receive as a dependency. The backward-compatible properties (`current_result`, `current_interface_result`, etc.) provide a bridge during migration. The CP-01 duck-typing is a non-issue: all runtime-attribute-sets on InterfaceStructure are existing dataclass fields with defaults, not arbitrary new attributes.
**Source:** data-flow-migration/ARCHITECTURE.md §1, data-flow-migration/SUMMARY.md

### 5. Coexistence Period vs Clean Break
**Decision:** Feature flag coexistence (`--layout tabs` vs `--layout integrated`), timeboxed to 1 release.
**Rationale:** A clean break from tabs to docks risks regressions that can't be rolled back. The feature flag costs ~150 extra lines in DockManager, and all other managers are layout-agnostic (they only see PipelineSession). The coexistence period is strictly a rollback safety net — no new features are added to the tabs path. After one release cycle with the integrated layout validated by users, remove the `--layout tabs` flag.
**Source:** data-flow-migration/ARCHITECTURE.md §8

### 6. ChimeraX-Style Dock Layout vs OVITO-Style Fixed Panels
**Decision:** ChimeraX-style QDockWidget panels (dockable, tabifiable, state-persistent).
**Rationale:** OVITO's fixed left+right panels work for its focused workflow but are too rigid for QuickIce, which needs contextual parameter switching (Ice params vs Interface params vs Ion params). ChimeraX's dockable panels provide the same contextual switching with the flexibility of user customization. `saveState()`/`restoreState()` enables layout persistence. The tabified left dock pattern (4 parameter panels sharing one dock area, switched by toolbar) is the best mapping from the current 6 tabs.
**Source:** dock-panel-system/ARCHITECTURE.md, comparative-analysis/FEATURES.md

### 7. One Style Per Mode vs God-Class Style
**Decision:** One interactor style class per mode, swapped via `SetInteractorStyle()`.
**Rationale:** A single style with a `self._mode` enum and a switch/case in every `OnXxx()` method violates SRP, grows unmanageably with each new mode, and makes testing individual modes impossible. Pre-building one style per mode in `_build_mode_registry()` and switching them at runtime is VTK's intended pattern — `SetInteractorStyle()` cleanly replaces the active style, and VTK handles reference counting for old styles.
**Source:** tool-mode-system/ARCHITECTURE.md §1-2, tool-mode-system/PITFALLS.md Anti-Pattern 1

### 8. Split View via SetViewport vs QSplitter
**Decision:** `vtkRenderer.SetViewport()` for split-view candidate comparison.
**Rationale:** Single render window, single OpenGL context, single interactor — all shared between two renderers. Camera sync via `DeepCopy` (same pattern as current DualViewerWidget). QSplitter with two QVTKRenderWindowInteractors creates two OpenGL contexts and two interactors, defeating the single-viewport goal. Fallback to QSplitter only if `SetViewport()` mouse routing proves broken in testing.
**Source:** single-viewport-arch/ARCHITECTURE.md §Dual-View, single-viewport-arch/FEATURES.md §Dual-View Decision Matrix

### 9. Solute/Ion/Custom as "Modifiers" Tab vs Separate Tabs
**Decision:** Merge Solute, Ion, and Custom Molecule into one "Modifiers" tabified dock.
**Rationale:** These three panels are always applied *after* the base structure and share the same workflow pattern (select source → set parameters → insert). Six tabified left-dock tabs create a crowded tab bar; four meaningful tabs (Ice, Hydrate, Interface, Modifiers) is cleaner. The Modifiers dock uses a QStackedWidget internally to switch between Solute/Ion/Custom content, controlled by sub-tabs or buttons within the dock.
**Source:** dock-panel-system/ARCHITECTURE.md §Dock → Panel Mapping

### 10. Raw VTK vs High-Level Wrappers
**Decision:** Raw VTK 9.5.2 + QVTKRenderWindowInteractor. No PyVista, vedo, or trame.
**Rationale:** QuickIce needs custom interactor styles (Draw Region, Place Molecule, Select), full actor management (vtkAssembly groups per phase), and direct renderer control (SetViewport, SetLayer). PyVista's abstraction layer fights VTK interactor customization. vedo is scripting-oriented with no Qt integration. trame is web-first. ParaView itself uses raw VTK + QVTKRenderWindowInteractor — this is the battle-tested production pattern.
**Source:** comparative-analysis/ARCHITECTURE.md §Python VTK Framework Assessment

---

## Open Questions

1. **SetViewport mouse interaction routing:** Does `QVTKRenderWindowInteractor` correctly route mouse events to the renderer under the cursor when using `SetViewport()`? Needs a prototype test. If it fails, the custom `vtkInteractorStyle` with `FindPokedRenderer(x, y)` is the fallback.

2. **GUI test strategy:** Zero GUI integration tests exist currently. What test framework? `pytest-qt` for signal verification? Mock-based for VTK-dependent code? Skip strategy for headless CI? This must be resolved before Phase 1.

3. **PipelineSession ↔ CLIPipeline convergence:** The CLI pipeline (`quickice/cli/pipeline.py`) implements the same linear step chain. Should PipelineSession eventually replace CLIPipeline's internal state? Research says yes, but this is a post-migration cleanup — don't attempt during the GUI migration phases.

4. **PolycrystalStructure compatibility:** Should it subclass `InterfaceStructure` or be a separate dataclass with `to_interface_structure()`? The polycrystalline builder research recommends Option B (separate + conversion method) for cleaner design. This decision affects the PipelineSession step type for polycrystal output.

5. **Per-panel content state serialization schema:** `saveState()` handles dock layout. QSettings handles per-panel input values. The QSettings key schema needs design. Should it be per-panel (`IceInputPanel/temperature`) or per-step (`pipeline/steps/0/parameters/temperature`)?

6. **Worker lifecycle for fast steps (< 100ms):** SoluteInserter and IonInserter currently run synchronously. Should PipelineManager wrap them in QThread workers for consistency, or allow synchronous execution with a progress indicator threshold?

7. **Command-line interface in GUI:** ChimeraX-style command panel in the bottom dock? Deferred to post-MVP per comparative-analysis research, but the dock layout should reserve space for it.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Single viewport (vtkAssembly)** | HIGH | All VTK APIs tested against 9.5.2; performance benchmarks measured; existing viewer code analyzed |
| **Dock panel system** | HIGH | All PySide6 6.10.2 APIs verified by live testing; saveState/restoreState confirmed; pitfalls discovered by testing |
| **Tool mode system** | HIGH | VTK interactor switching confirmed; widget lifecycle documented from source; custom style pattern validated |
| **Pipeline data model** | HIGH | 1:1 mapping from existing `_current_*` attributes; CP-01 duck-typing verified as non-issue; modifier stack matches physical constraints |
| **Migration phasing** | MEDIUM | Phase ordering is sound but parallelization estimates may be optimistic; zero GUI tests is a gap |
| **SetViewport split-view interaction** | MEDIUM | API confirmed; mouse routing untested; fallback exists (QSplitter) |
| **Coexistence feasibility** | MEDIUM | Technically straightforward (~150 lines); UX cost/benefit of maintaining two layouts is unclear |
| **Polycrystal builder enablement** | HIGH | 2.5D model + QGraphicsView confirmed; VTK multi-phase rendering straightforward; data flow compatible |
| **No new dependencies** | HIGH | All research agents independently confirmed: PySide6 + VTK + numpy + shapely covers everything |

**Overall confidence:** MEDIUM-HIGH. The architecture is well-proven by 5 major scientific tools. VTK and PySide6 APIs are verified by live testing. The main uncertainty is in the migration execution — specifically, whether the phase ordering holds under real development conditions, and whether the zero GUI test coverage can be addressed quickly enough.

---

## Files Produced by Sub-Agents

### single-viewport-arch/ (5 files)
| File | Purpose |
|------|---------|
| SUMMARY.md | Single viewport feasibility, vtkAssembly recommendation, DualViewer replacement |
| ARCHITECTURE.md | Actor group hierarchy, UnifiedViewerWidget, renderer config, camera strategy, split-view |
| STACK.md | VTK 9.5.2 API patterns verified, performance benchmarks |
| FEATURES.md | Table stakes (visibility, coloring, dual-view), differentiators (all-phase view, overlays), anti-features |
| PITFALLS.md | 14 pitfalls: assembly visibility semantics, headless segfault, SetViewport mouse, memory leak, camera reset |

### dock-panel-system/ (4 files)
| File | Purpose |
|------|---------|
| SUMMARY.md | QDockWidget layout, panel↔tool mapping, contextual switching |
| ARCHITECTURE.md | Dock hierarchy, panel lifecycle, state serialization, VTK scene manager, feature flag coexistence |
| FEATURES.md | Features from ParaView/ChimeraX/OVITO/PyMOL, table stakes, differentiators, anti-features |
| PITFALLS.md | 12 pitfalls: missing objectName, version mismatch, raise_() offscreen, floating params dock, resize |

### tool-mode-system/ (4 files)
| File | Purpose |
|------|---------|
| SUMMARY.md | Interactor style switching, ToolModeManager, 3D vs 2D drawing |
| ARCHITECTURE.md | ToolModeManager design, mode registry, style switching, widget lifecycle, event routing, picker strategy |
| FEATURES.md | 6 tool modes (Navigate, Select, Draw, Place, Measure, Pick), 3D drawing comparison |
| PITFALLS.md | 12 pitfalls: headless segfault, widget event conflict, observer leak, picker corruption, cursor override |

### comparative-analysis/ (4 files)
| File | Purpose |
|------|---------|
| SUMMARY.md | OVITO modifier stack + ChimeraX docks hybrid model recommendation |
| FEATURES.md | Feature comparison matrix across 5 tools + 3 Python VTK frameworks |
| ARCHITECTURE.md | 5 patterns to adopt, 5 anti-patterns to avoid, framework assessment |
| PITFALLS.md | 14 pitfalls: DAG trap, per-tab renderers, floating windows, dual GUI, VTK sync, premature plugin API |

### data-flow-migration/ (3 files)
| File | Purpose |
|------|---------|
| SUMMARY.md | PipelineSession model, migration strategy, coexistence verdict |
| ARCHITECTURE.md | PipelineSession dataclass, MainWindow decomposition, modifier stack, CP-01 resolution, export workflow, worker lifecycle |
| PITFALLS.md | 11 pitfalls: decomposition before PipelineSession, broken propagation chain, HydrateWorker incompat, signal wiring |

---

## How This Enables the Polycrystalline Builder (v8.0)

The integrated VTK-centric GUI directly unblocks the polycrystalline builder in several ways that the current tab-based layout cannot:

1. **Simultaneous multi-phase visualization.** The polycrystal builder produces structures with multiple grain types (Ice Ih, Ice III, liquid water, clathrate hydrate) that must be visible simultaneously with distinct colors. The current tab model shows one phase at a time — useless for polycrystals. The `vtkAssembly` per-phase architecture renders all grains in one viewport with per-grain visibility toggling.

2. **Draw Region tool mode.** The `vtkContourWidget` + `vtkBoundedPlanePointPlacer` provides 3D plane-constrained polygon drawing directly on the structure. For simple single-plane region definition (the most common case), this eliminates the need for a separate 2D editor. The `vtkContourWidget` retains nodes across mode switches (draw → navigate → draw), and `GetNodePolyData()` directly produces VTK polydata for the region boundary.

3. **QGraphicsView dock panel for complex editing.** For the polycrystal builder's multi-region 2D editing (rectangles, ellipses, Voronoi tessellations, undo/redo), the QGraphicsView shape editor becomes a dock panel alongside the 3D viewport. This 2D+3D split view is impossible in the tab model (the 2D editor and 3D viewer would be in different tabs). In the dock model, both are visible simultaneously.

4. **PipelineNavigator extension.** The "Polycrystal" step sits naturally in the modifier stack between Interface and Custom/Solute/Ion. Selecting it in the pipeline navigator shows the polycrystal configuration panel in the properties dock. The pipeline's `current_structure` at the polycrystal step is a `PolycrystalStructure` convertible to `InterfaceStructure` for downstream compatibility.

5. **StructureManager per-grain visibility.** The ChimeraX Model Panel pattern adapted for QuickIce provides checkboxes per structural layer. For polycrystals, this extends to per-grain visibility (Ice Grain 1, Ice Grain 2, Hydrate Region, Liquid, Buffer Zone), enabling users to inspect individual grains without hiding the entire structure.

---

*Synthesized: 2026-06-28 | 5 research agents, 22 files, 1 cohesive architecture*
