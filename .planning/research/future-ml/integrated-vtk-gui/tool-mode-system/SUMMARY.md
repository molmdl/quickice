# Research Summary: Tool/Mode Switching System for Integrated VTK-Centric GUI

**Domain:** VTK interactor style switching, 3D widget integration, and tool mode architecture
**Researched:** 2026-06-28
**Overall confidence:** HIGH (VTK 9.5.2 API verified via live Python testing; QVTKRenderWindowInteractor source inspected; official VTK docs cross-referenced)

## Executive Summary

VTK's interactor style system fully supports runtime tool/mode switching via `iren.SetInteractorStyle(new_style)`. Style objects survive switching (refcount managed by VTK), and the interactor cleanly delegates events to whatever style is active. The recommended architecture for QuickIce is a **ToolModeManager** that owns a registry of pre-built interactor styles and VTK widgets, switching them at runtime when the toolbar selection changes. This avoids the complexity of a single composite "god-class" style and leverages VTK's built-in style classes directly.

For 3D shape drawing (polycrystal region drawing), VTK provides two viable paths: `vtkContourWidget` (constrained to a plane via `vtkBoundedPlanePointPlacer`) for polygon drawing directly in the 3D viewport, and `vtkInteractorStyleDrawPolygon` for freeform screen-space polygon drawing. The `vtkContourWidget` approach is recommended for region drawing because it constrains points to a user-selected plane, which maps naturally to QuickIce's XY/Z slice interaction model. However, for the polycrystal builder's 2D shape workflow, the existing QGraphicsView approach from the polycrystalline builder research remains the better choice — VTK's 3D contour widget is best for single-plane polygon definition, while QGraphicsView excels at multi-region 2D editing with undo/redo.

VTK widgets (vtkDistanceWidget, vtkSeedWidget, vtkContourWidget, etc.) coexist with interactor styles via a priority-based event system. When a widget is **Enabled**, it intercepts events before the interactor style processes them. When **Disabled**, events pass through to the style. This is the correct pattern for tool modes that need overlay geometry (measure lines, placement markers, region outlines).

## Key Findings

**Interactor style switching:** Confirmed safe at runtime. `SetInteractorStyle()` cleanly replaces the current style. Old styles are retained by Python reference counting and can be re-activated. No explicit cleanup needed beyond removing observers added to the old style. (HIGH confidence)

**VTK 3D widgets + interactor style coexistence:** Widgets register with the interactor via `SetInteractor()`. When Enabled (1), they intercept events. When Disabled (0), events pass through. Multiple widgets can exist simultaneously but only enabled ones process events. (HIGH confidence)

**3D shape drawing:** `vtkContourWidget` + `vtkBoundedPlanePointPlacer` provides plane-constrained polygon drawing in 3D. `vtkInteractorStyleDrawPolygon` provides freeform screen-space drawing. For region definition on a specific plane, the contour widget approach is better. For 2D polycrystal editing, QGraphicsView remains superior. (HIGH confidence)

**Picking:** `vtkCellPicker` picks cells/meshes (for molecule placement on existing geometry), `vtkPointPicker` picks individual points (for atom selection), `vtkWorldPointPicker` picks 3D world coordinates from screen coords (for arbitrary position placement). `vtkPropPicker` picks actors (for selecting entire molecules). (HIGH confidence)

**Mode transition architecture:** ToolModeManager class with enum-driven mode switching. No need for QStateMachine — the mode set is small (6 tools), transitions are simple (toolbar click), and VTK already has its own state machine in each interactor style. A plain Python/Qt pattern is cleaner and more debuggable. (MEDIUM-HIGH confidence)

**Cursor management:** VTK maps its cursor enums to Qt cursors via `QVTKRenderWindowInteractor._CURSOR_MAP`. Setting cursor from the tool mode is straightforward: `vtk_widget.setCursor(Qt.CrossCursor)` for pick/place modes, or leverage VTK's `CursorChangedEvent` observer. (HIGH confidence)

## Implications for Roadmap

Based on research, suggested phase structure for tool mode system:

1. **Phase 1: Navigate + Select tool modes** — Implement ToolModeManager with Navigate (TrackballCamera) and Select (custom style with vtkCellPicker/vtkPropPicker for atom/molecule selection). Two modes validate the switching architecture, cursor management, and status bar hints.
   - Addresses: core switching architecture, ToolModeManager, mode registry
   - Avoids: widget lifecycle complexity (Select uses simple observers, no 3D widgets)

2. **Phase 2: Place Molecule + Measure tools** — Add Place Molecule (custom style with vtkCellPicker for 3D position) and Measure (vtkDistanceWidget with 3D representation). Introduces 3D widget lifecycle management.
   - Addresses: widget Enable/Disable lifecycle, contextual dock panels for tool parameters
   - Avoids: shape drawing complexity

3. **Phase 3: Draw Region tool** — Add region drawing mode. Two sub-approaches: (a) vtkContourWidget for 3D plane-constrained polygon drawing, (b) integration with polycrystal builder's QGraphicsView for 2D region editing. This is the most complex tool mode.
   - Addresses: vtkContourWidget + point placer integration, or QGraphicsView overlay
   - Avoids: multi-widget interference issues

4. **Phase 4: Pick + advanced tools** — Add Pick tool (atom property display) and any additional tools (box widget for cell editing, implicit plane widget for plane selection). Polish all mode transitions.
   - Addresses: information display on pick, widget+style coexistence for multiple widgets

**Phase ordering rationale:**
- Phase 1 establishes the architectural foundation with minimal VTK complexity
- Phase 2 introduces 3D widget lifecycle (the critical pattern to get right)
- Phase 3 adds the hardest tool (drawing) which depends on Phase 2's widget patterns
- Phase 4 is polish and advanced features

**Research flags for phases:**
- Phase 1: Straightforward — TrackballCamera switching + custom Select style are well-understood patterns
- Phase 2: Widget Enable/Disable ordering when multiple widgets exist needs careful testing
- Phase 3: vtkContourWidget interaction with interactor style may have edge cases; needs prototyping
- Phase 4: Box widget + implicit plane widget may conflict with each other; test coexistence

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Interactor style switching | HIGH | Verified via live VTK 9.5.2 API testing; confirmed clean switching |
| VTK widget lifecycle | HIGH | VTK docs + QVTKRenderWindowInteractor source confirm Enable/Disable pattern |
| 3D shape drawing | MEDIUM-HIGH | vtkContourWidget API tested; plane constraint works; but interaction edge cases need prototyping |
| Picking architecture | HIGH | All 4 picker types tested; methods documented; well-known VTK pattern |
| Mode transition design | MEDIUM-HIGH | ToolModeManager is a standard pattern; VTK-specific concerns are well-characterized |
| Cursor management | HIGH | QVTKRenderWindowInteractor._CURSOR_MAP verified in source; Qt cursor API straightforward |
| Qt-VTK event flow | HIGH | QVTKRenderWindowInteractor source read in full; Qt→VTK mapping confirmed |

## Gaps to Address

- **vtkContourWidget + BoundedPlanePointPlacer interaction with style switching:** Need to test whether the contour widget properly releases events when disabled, and whether style switching interferes with the widget's internal state machine.
- **Multiple enabled widgets:** What happens when two widgets are enabled simultaneously? VTK uses priority-based processing, but the exact behavior when two widgets compete for the same event needs testing.
- **Undo/redo across mode switches:** If a user draws a region, switches to Navigate to rotate, then switches back — should the region drawing resume where it left off? vtkContourWidget retains its nodes, but the UX needs specification.
- **Headless VTK testing:** As documented in AGENTS.md, VTK rendering crashes in some headless environments. Tool mode code must be testable without a display. Mock-based testing strategy needed for CI.
