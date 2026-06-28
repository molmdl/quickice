# Domain Pitfalls

**Domain:** Interactive shape editors for scientific molecular simulation setup
**Researched:** 2026-06-28

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: 2D↔3D Coordinate Desynchronization
**What goes wrong:** The 2D editor shows a shape at position (2.5, 3.0) nm but the VTK 3D preview renders it at (3.0, 2.5) nm because Y is flipped or the coordinate mapper has a bug. Or the Z-range displayed in the phase assignment panel doesn't match what VTK is rendering.
**Why it happens:** Qt's Y-axis points down (screen coordinates), VTK's Y-axis points up (world coordinates). The nm-to-scene mapper must flip Y. Forgetting this flip is the #1 coordinate bug.
**Consequences:** Regions appear in wrong positions in 3D preview; generated structure places phases in wrong locations; user loses trust in the tool.
**Prevention:** 
- Write the coordinate mapper ONCE and test it with unit tests (nm → scene → nm round-trip must be identity)
- Add a "coordinate verification" step: render a small marker at (0,0) in both 2D and 3D views and verify alignment
- Use the same `SceneCoordinateMapper` class everywhere; never inline coordinate math
**Detection:** Regions that look correct in 2D appear mirrored or offset in 3D. Regression tests catch this.

### Pitfall 2: shapely Geometry Corruption During Editing
**What goes wrong:** When user moves a polygon vertex, the resulting shapely Polygon becomes invalid (self-intersecting). shapely silently returns empty results for `area`, `intersects`, etc. on invalid geometries.
**Why it happens:** Dragging a vertex through an edge creates a self-intersecting polygon. shapely 2.x handles this better than 1.x but it's still a risk.
**Consequences:** Overlap detection fails silently; volume calculation returns 0; VTK preview shows a broken mesh.
**Prevention:**
- After every edit, validate with `shapely.is_valid`; if invalid, apply `shapely.make_valid()` or `buffer(0)` to repair
- Show a visual warning (red border) on invalid regions
- Restrict vertex movement to prevent self-intersection (snap to valid positions)
**Detection:** `region.shape.is_valid == False` after edit; zero area; VTK mesh artifacts.

### Pitfall 3: VTK Z-Buffer Fighting with Translucent Overlapping Regions
**What goes wrong:** When two or more translucent regions overlap in 3D, VTK's depth buffer causes flickering or incorrect rendering (one region "punches through" another).
**Why it happens:** VTK renders translucent objects back-to-front, but when regions overlap in Z, the sorting fails. This is a well-known VTK limitation.
**Consequences:** 3D preview looks broken; user can't verify region overlaps visually.
**Prevention:**
- Use `vtkTranslucentPass` with `vtkDepthPeelingPass` for correct translucent rendering
- Limit opacity to 0.15-0.3 range (more transparent = less z-fighting)
- Render region outlines (wireframe) in addition to translucent fill
- Alternative: render only the OUTLINE of each region (no fill) and use color to distinguish phases
**Detection:** Flickering or incorrect rendering when regions overlap in 3D.

### Pitfall 4: QUndoStack Command Granularity
**What goes wrong:** Every mouse move during a drag generates a separate undo command. After dragging a shape 100 pixels, the user must undo 100 times. Or conversely, undoing a "draw polygon" operation requires clicking undo for each vertex.
**Why it happens:** QGraphicsItem.itemChange() fires on every pixel move. Connecting this directly to QUndoStack creates micro-commands.
**Consequences:** Undo is unusable; user gets frustrated; accidental undo of unrelated operations.
**Prevention:**
- Use `beginMacro()`/`endMacro()` for multi-step operations (polygon drawing, shape moves)
- Only push undo command on mouse RELEASE (not during drag)
- Store the initial and final positions in MoveRegionCommand, not every intermediate
- For polygon drawing: push a single "Add polygon" command when double-click finishes the polygon
**Detection:** Undo stack grows by 100+ per drag operation; user complaints about undo behavior.

## Moderate Pitfalls

Mistakes that cause delays or technical debt.

### Pitfall 5: Scene Rect Mismatch with Box Dimensions
**What goes wrong:** QGraphicsScene has a fixed sceneRect but the user changes box dimensions (Lx, Ly). Existing shapes don't scale or clip properly.
**Prevention:** When box dimensions change, recalculate the SceneCoordinateMapper and rescale all existing items. Or: fix the sceneRect to a reasonable pixel size and only change the nm-to-px scale factor. Warn the user if changing box dimensions would invalidate existing shapes.

### Pitfall 6: Phase Assignment Without Overlap Resolution
**What goes wrong:** User assigns overlapping regions with different phase types. The generator doesn't know which phase takes priority.
**Prevention:** Run shapely overlap detection after every region edit/phase change. If overlaps exist, show a warning and disable "Generate" until resolved. Provide a "resolve overlaps" tool that uses shapely.difference() to split overlapping regions.

### Pitfall 7: VTK Preview Stale State
**What goes wrong:** User edits a shape in 2D but the 3D preview doesn't update (or updates with a delay). This happens if the signal chain from 2D editor → RegionModel → VTK preview is broken or rate-limited incorrectly.
**Prevention:** Use direct signal connection: shapeChanged → updateVTKPreview. For performance, batch updates with a QTimer (e.g., 50ms debounce). Always call `render_window.Render()` after updating VTK actors.

### Pitfall 8: Z-Slice Cross-Section Confusion
**What goes wrong:** User draws a shape at Z=5nm but the shape actually spans Z=0-10nm. They think they're defining a thin slice but they've defined a full-column region.
**Prevention:** Make Z-range (z_min, z_max) prominently visible for each region. When drawing a new shape, default z_min/z_max to the current Z-slice slider position with a small extent, NOT the full box height. Show a Z-axis indicator in the 2D editor sidebar.

### Pitfall 9: Non-Convex Polygon Triangulation Failures
**What goes wrong:** A user draws a concave (non-convex) polygon. When rendering it in VTK, the triangulation produces artifacts or inverted faces.
**Prevention:** Use `vtkTriangleFilter` which handles non-convex polygons. If that fails, use `vtkStripper` to clean the mesh. Alternatively, decompose non-convex polygons into convex parts using shapely's `convex_hull` or a convex decomposition algorithm.

### Pitfall 10: Save/Load Format Without Versioning
**What goes wrong:** Region configuration is saved to a JSON/YAML file. Later, the format changes (e.g., adding a `rotation` field). Old files can't be loaded.
**Prevention:** Include a `format_version` field in the save file. Write a loader that can handle version N-1 → N migration. Use shapely's WKT (Well-Known Text) format for polygon serialization — it's standard, version-stable, and human-readable.

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 11: Small Shape Handles on High-DPI Displays
**What goes wrong:** Resize handles are too small on 4K displays. Users can't grab them.
**Prevention:** Scale handle size by device pixel ratio. Use `QStyle` pixel metrics for handle size.

### Pitfall 12: Slow Shapely Operations for Many Vertices
**What goes wrong:** A freehand-drawn polygon has 500+ vertices. shapely operations (intersects, difference) become slow for such complex shapes.
**Prevention:** Apply `shapely.simplify()` with a tolerance after freehand drawing (like napari's Ramer-Douglas-Peucker approach). Default tolerance: 0.1 nm.

### Pitfall 13: Lost Selection After Undo
**What goes wrong:** User selects a region, performs an operation, undoes it, and the selection is lost.
**Prevention:** Store selection state in QUndoCommand. On undo, restore the previous selection.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Data model design | Pitfall 10: No versioning in save format | Add format_version from day 1 |
| QGraphicsView editor | Pitfall 4: Undo granularity | Design undo commands before implementing editor |
| VTK 3D preview | Pitfall 3: Z-buffer fighting | Use depth peeling or wireframe-only rendering |
| Phase assignment | Pitfall 6: Unresolved overlaps | Real-time overlap detection with "Generate" guard |
| Coordinate mapping | Pitfall 1: Y-axis flip | Unit tests for coordinate round-trip |
| Z-slice editing | Pitfall 8: Z-range confusion | Default Z-range to slice extent, not full box |

## Sources

- VTK translucent rendering issues: VTK documentation + community forums (MEDIUM confidence — known VTK limitation)
- shapely invalid geometry behavior: shapely 2.1.2 documentation (HIGH confidence)
- Qt undo granularity: Qt QUndoStack documentation (HIGH confidence)
- QGraphicsView Y-axis convention: Qt documentation (HIGH confidence — Y-down in screen, Y-up in scene)
- napari shape simplification: napari shapes layer documentation (MEDIUM confidence — adapted for our use case)
- QuickIce codebase analysis: interface_panel.py, interface_viewer.py patterns (HIGH confidence)
