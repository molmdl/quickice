# Feature Landscape: Tool Mode System

**Domain:** VTK interactor tool modes for integrated GUI
**Researched:** 2026-06-28

## Table Stakes

Features users expect from a molecular visualization tool. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Navigate (3D camera control) | Every 3D viewer has this | Low | Already implemented as default `vtkInteractorStyleTrackballCamera` |
| Click-to-select atoms/molecules | Standard in PyMOL, VMD, OVITO | Medium | Need custom style + picker; highlight selected |
| Click-to-pick (atom info) | Standard in molecular viewers | Medium | Point picker + property display panel |
| Distance measurement | Standard in all molecular viewers | Low | `vtkDistanceWidget` provides this out of the box |
| Visual feedback on tool selection | Cursor change, status hint | Low | Qt cursor API + status bar |
| Keyboard shortcut for mode switch | Standard UX expectation | Low | QShortcut or QAction with key binding |

## Differentiators

Features that set QuickIce apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Draw Region in 3D viewport | Polycrystal regions defined directly on the structure (no separate 2D editor needed for simple cases) | High | `vtkContourWidget` + `vtkBoundedPlanePointPlacer`; plane must be user-settable |
| Place Molecule on structure surface | WYSIWYG molecule placement — see the 3D context while placing | Medium | Custom style with `vtkCellPicker` + plane projection |
| Plane-constrained placement | Place molecules on a specific crystallographic plane (XY, XZ, YZ, or arbitrary) | Medium | `vtkBoundedPlanePointPlacer` with `SetProjectionNormalToZAxis()` etc. |
| Multi-tool undo/redo | Undo across mode switches (place molecule → navigate → undo placement) | Medium | Shared `QUndoStack` on MainWindow |
| Contextual dock panel switching | Tool parameters appear contextually in the dock panel when the tool is selected | Medium | Requires dock panel system (from dock-panel-system research) |
| Rubber band region selection | Rectangle-select multiple atoms/molecules in 3D | Medium | `vtkInteractorStyleRubberBandPick` + `vtkRenderedAreaPicker` |
| Box widget for cell editing | Visual box widget for adjusting unit cell parameters | Medium | `vtkBoxWidget2` — interactive cell size/orientation editing |
| Implicit plane widget | Interactive plane for defining cross-sections or slice views | Medium | `vtkImplicitPlaneWidget2` — visual plane handle |

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Single "god-class" interactor style with mode switching inside | Becomes unmaintainable with 6+ modes; every `OnLeftButtonDown` has a switch/case | One style class per mode, swapped via `SetInteractorStyle()` |
| QStateMachine for mode transitions | Over-engineered for 6 simple states; VTK has its own state machine in each style; adds Qt dependency to VTK layer | Simple ToolModeManager with enum + switch logic |
| Qt event filtering for tool modes | Qt event filters intercept before VTK, breaking the VTK event pipeline; fragile | Use VTK's own observer system and interactor style overrides |
| 2D overlay (QPainter) for tool feedback | Fighting with VTK's rendering pipeline; Z-order issues; ugly | Use VTK 3D widgets (DistanceWidget, ContourWidget) or VTK overlay actors |
| Custom OpenGL rendering for tool visuals | Extreme complexity; VTK already provides 3D widgets for this | Use VTK's widget/representation classes |
| Persistent multi-widget enabling | Event conflicts between competing widgets; undefined behavior | Only one widget enabled at a time per mode |
| Full 3D polygon drawing for polycrystal regions | 3D polygon drawing on arbitrary surfaces is extremely complex; no good VTK support | Use `vtkContourWidget` on a bounded plane, or delegate to QGraphicsView for complex 2D editing |

## Feature Dependencies

```
Navigate (standalone — no dependencies)
    │
    ├── Select
    │       ├── Requires: picker (vtkPropPicker)
    │       └── Enables: atom highlighting, info display
    │
    ├── Pick
    │       ├── Requires: picker (vtkPointPicker)
    │       └── Enables: atom property display
    │
    ├── Place Molecule
    │       ├── Requires: picker (vtkCellPicker), placement plane config
    │       ├── Enables: molecule insertion workflow
    │       └── Depends on: solute/ion pipeline (existing)
    │
    ├── Measure
    │       ├── Requires: vtkDistanceWidget (no custom code)
    │       └── Enables: distance display
    │
    └── Draw Region
            ├── Requires: vtkContourWidget + point placer
            ├── Enables: polycrystal region definition
            └── Depends on: polycrystal builder (future-ml research)
```

## Tool Mode Inventory

### Mode 1: Navigate

| Property | Value |
|----------|-------|
| VTK Style | `vtkInteractorStyleTrackballCamera` |
| VTK Widgets | None |
| Picker | None |
| Cursor | Arrow |
| Status Hint | "Rotate: Left-drag \| Pan: Middle-drag \| Zoom: Right-drag or scroll" |
| Context Panel | None (or general display settings) |
| Left Button | Rotate |
| Middle Button | Pan |
| Right Button | Zoom |
| Keyboard | R=reset camera, F=fly to point, P=pick (legacy) |
| Complexity | **Low** — uses built-in style, no custom code |

### Mode 2: Select

| Property | Value |
|----------|-------|
| VTK Style | `SelectInteractorStyle` (custom, extends TrackballCamera) |
| VTK Widgets | None |
| Picker | `vtkPropPicker` (picks actors) |
| Cursor | Crosshair |
| Status Hint | "Click an atom or molecule to select it" |
| Context Panel | Selection info (atom type, residue, coordinates) |
| Left Button | Select (pick + highlight) |
| Middle Button | Pan (inherited from TrackballCamera) |
| Right Button | Zoom (inherited from TrackballCamera) |
| Keyboard | Esc=deselect, Ctrl+A=select all (future) |
| Complexity | **Medium** — custom style with observer management |

### Mode 3: Draw Region

| Property | Value |
|----------|-------|
| VTK Style | `vtkInteractorStyleTrackballCamera` (navigation while drawing) |
| VTK Widgets | `vtkContourWidget` (with `vtkBoundedPlanePointPlacer`) |
| Picker | BoundedPlanePointPlacer (not a traditional picker) |
| Cursor | Crosshair |
| Status Hint | "Click to add vertices \| Double-click to close region \| Middle-drag to pan" |
| Context Panel | Plane selector (XY/XZ/YZ/custom), region list |
| Left Button | Add contour node (via ContourWidget) |
| Middle Button | Pan (via TrackballCamera — conflicts with widget!) |
| Right Button | Zoom (via TrackballCamera) |
| Keyboard | Enter=close loop, Delete=delete last node, Esc=cancel |
| Complexity | **High** — widget+style interaction, plane configuration |

**Note on Middle/Right button conflict:** When `vtkContourWidget` is enabled, it may intercept mouse events. Need to verify that middle/right buttons still pass through to the trackball style for camera manipulation. If not, the ContourWidget must be configured to only process left-button events via its `vtkWidgetEventTranslator`.

### Mode 4: Place Molecule

| Property | Value |
|----------|-------|
| VTK Style | `PlaceMoleculeInteractorStyle` (custom, extends TrackballCamera) |
| VTK Widgets | `vtkSeedWidget` (alternative approach) or None (click-only) |
| Picker | `vtkCellPicker` + fallback `vtkWorldPointPicker` |
| Cursor | Crosshair |
| Status Hint | "Click to place molecule \| Use plane selector for constrained placement" |
| Context Panel | Molecule selector, placement plane config, preview |
| Left Button | Place molecule at picked position |
| Middle Button | Pan (inherited from TrackballCamera) |
| Right Button | Zoom (inherited from TrackballCamera) |
| Keyboard | Delete=remove last placed molecule, Esc=cancel |
| Complexity | **Medium** — custom style with picking and plane projection |

### Mode 5: Measure

| Property | Value |
|----------|-------|
| VTK Style | `vtkInteractorStyleTrackballCamera` (navigation) |
| VTK Widgets | `vtkDistanceWidget` (with `vtkDistanceRepresentation3D`) |
| Picker | (handled by DistanceWidget internally) |
| Cursor | Crosshair |
| Status Hint | "Click two points to measure distance \| Middle-drag to pan" |
| Context Panel | Measurement results list |
| Left Button | Place measure endpoint (via DistanceWidget) |
| Middle Button | Pan (via TrackballCamera) |
| Right Button | Zoom (via TrackballCamera) |
| Keyboard | N=new measurement, Delete=remove selected measurement |
| Complexity | **Low** — uses built-in VTK widget, minimal custom code |

### Mode 6: Pick (Atom Properties)

| Property | Value |
|----------|-------|
| VTK Style | `PickInteractorStyle` (custom, extends TrackballCamera) |
| VTK Widgets | None |
| Picker | `vtkPointPicker` (picks individual points/atoms) |
| Cursor | WhatsThis (question mark) |
| Status Hint | "Click an atom to display its properties" |
| Context Panel | Atom info: element, residue, coordinates, velocity (if available) |
| Left Button | Pick atom and display info |
| Middle Button | Pan (inherited from TrackballCamera) |
| Right Button | Zoom (inherited from TrackballCamera) |
| Keyboard | Esc=clear pick info |
| Complexity | **Medium** — custom style with point picker and info display |

## MVP Recommendation

For MVP of the tool mode system, prioritize:

1. **Navigate** — Already exists, zero new code
2. **Select** — Most requested feature, validates architecture
3. **Measure** — `vtkDistanceWidget` is trivially simple, great demo of 3D widget pattern

Defer to post-MVP:
- **Draw Region**: Complex widget interaction, needs polycrystal builder context
- **Place Molecule**: Needs solute/ion pipeline integration
- **Pick**: Similar to Select but with different picker; can derive from Select pattern

## 3D Shape Drawing Comparison

### VTK 3D Drawing (vtkContourWidget)

**Pros:**
- Draws directly in the 3D viewport — no separate editor window
- Plane-constrained via `vtkBoundedPlanePointPlacer` — ensures all points lie on the same plane
- Node editing — click to add, drag to move, delete to remove
- Close loop support — `CloseLoop()` method
- `GetNodePolyData()` — direct access to the drawn polygon as VTK polydata
- Works with any projection normal (X, Y, Z, or arbitrary plane)

**Cons:**
- Only works on a single plane — cannot draw multi-planar regions
- No built-in rectangle/circle tools — only freeform polygon
- Contour widget event handling may conflict with TrackballCamera for middle/right buttons
- Visual style is basic (lines and dots) — no fancy region fill
- Undo is manual — need to track node additions and provide `DeleteNthNode()`

### QGraphicsView 2D Drawing (from polycrystalline builder research)

**Pros:**
- Full 2D editing tools: rectangle, ellipse, freeform polygon, line
- `QUndoStack` integration — natural undo/redo for shape operations
- `QGraphicsScene` — rich item model with selection, grouping, z-ordering
- Familiar 2D interaction model — no 3D depth confusion
- Separate from VTK — no event handling conflicts

**Cons:**
- Requires a separate 2D editor panel — not "in the viewport"
- Coordinate mapping between 2D editor and 3D viewport needs explicit mapping
- Less immersive — cannot see the 3D structure while drawing

**Recommendation:** Use **VTK vtkContourWidget for simple single-plane region definition** (e.g., drawing a region on the XY plane of the ice structure). Use **QGraphicsView for the polycrystal builder's multi-region 2D editing** (where users need to define multiple named regions with undo/redo). Both approaches are valid for different use cases.

## Sources

- VTK 9.5.2 API testing (live Python)
- QVTKRenderWindowInteractor.py source code
- VTK official class documentation (vtk.org/doc/nightly)
- Polycrystalline builder architecture integration research (`.planning/research/future-ml/polycrystalline-builder/arch-integration/SUMMARY.md`)
- Dock panel system research (`.planning/research/future-ml/integrated-vtk-gui/dock-panel-system/SUMMARY.md`)
