# Technology Stack

**Project:** QuickIce — Interactive Polycrystalline Builder (Shape GUI)
**Researched:** 2026-06-28

## Recommended Stack

### Core Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PySide6 | 6.10.2 | GUI framework | Already in env.yml; provides QGraphicsView, QUndoStack, signals/slots |
| VTK | 9.5.2 | 3D region preview | Already in env.yml; QVTKRenderWindowInteractor for Qt integration |
| shapely | 2.1.2 | Geometry model + overlap detection | Already in env.yml; 2.5D polygon operations, intersection/union/difference |
| numpy | 2.4.3 | Coordinate transforms | Already in env.yml; nm ↔ pixel mapping, Z-range math |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| matplotlib | 3.10.8 | NOT recommended for drawing | Use FigureCanvasQTAgg only if static region visualization is needed in a report; NOT for interactive editing |
| scipy | 1.17.1 | cKDTree for overlap checking | When shapely operations are too slow for many regions (>50); shapely is preferred for most cases |

### Qt Graphics View Components
| Class | Purpose | Why |
|-------|---------|-----|
| QGraphicsView | 2D canvas widget | Scroll, zoom, pan; event translation to scene coordinates |
| QGraphicsScene | Shape container | Manages items, selection, z-ordering |
| QGraphicsRectItem | Rectangle regions | Built-in resize handles, selection |
| QGraphicsPolygonItem | Polygon/ellipse regions | Arbitrary shape drawing |
| QGraphicsPathItem | Freehand/lasso regions | Complex curved boundaries |
| QUndoStack | Undo/redo | Standard Qt undo framework; push/pop commands for shape edits |

### VTK Components (3D Preview)
| Class | Purpose | Why |
|-------|---------|-----|
| QVTKRenderWindowInteractor | VTK widget in Qt | Already used in InterfaceViewerWidget, proven pattern |
| vtkRenderer | 3D scene | Region rendering, box wireframe |
| vtkOutlineSource | Box wireframe | Already used in vtk_utils.py for unit cell |
| vtkPolyData + vtkPolyDataMapper | Region surface rendering | Translucent colored surfaces for each phase region |
| vtkImplicitBoolean | Combine regions for spatial queries | UNION for aggregate region; used in backend, not GUI |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| 2D Drawing | QGraphicsView | VTK vtkActor2D overlay | Actor2D is for annotation/labels, not interactive shape editing; no move/resize handles; viewport coords only |
| 2D Drawing | QGraphicsView | matplotlib embedded canvas | Already used for phase diagram; but no interactive shape creation/editing; mouse events are limited; no item-level selection/move |
| 2D Drawing | QGraphicsView | Custom QPainter widget | Maximum control but huge boilerplate; must implement selection, resize handles, undo, z-ordering from scratch; QGraphicsView already provides all of this |
| 2D Drawing | QGraphicsView | napari shapes layer | Excellent shape editing but **requires napari dependency** (not in env.yml); napari's Qt event loop can conflict with standalone PySide6 apps; massive dependency for one feature |
| 3D Region Definition | 2.5D (shapely + Z extrusion) | VTK 3D widgets (vtkBoxWidget2) | BoxWidget2 only defines axis-aligned boxes, not arbitrary polygons; no ellipse/sphere/polygon primitives; complex event handling conflicts with VTK trackball camera |
| 3D Region Definition | 2.5D (shapely + Z extrusion) | Full 3D CSG (vtkImplicitBoolean) | Computationally expensive for real-time; no intuitive GUI for defining 3D CSG trees; overkill for most polycrystalline setups |
| Data Model | shapely Polygon + Z-range | VTK implicit functions | VTK implicit functions are great for spatial queries but poor as a serializable data model; shapely provides both geometry operations AND WKT serialization |

## NOT Recommended: Additional Dependencies

The following libraries were evaluated but are NOT recommended because they would require adding to environment.yml:

| Library | License | What it adds | Why NOT add |
|---------|---------|--------------|-------------|
| napari | BSD-3 | Shapes layer with full editing | 200+ MB dependency; conflicts with standalone PySide6 event loop; QGraphicsView provides equivalent functionality |
| pyqtgraph | MIT | Fast 2D plotting | Doesn't add shape editing capability; matplotlib + QGraphicsView cover the needs |
| opencv-python | Apache-2 | Image-based ROI selection | Overkill; we're not selecting from images; QGraphicsView is purpose-built for this |

## Installation

No new installations needed. All required libraries are already in `environment.yml`:

```bash
# Already installed in quickice conda env:
# PySide6 6.10.2 (conda)
# VTK 9.5.2 (conda)
# shapely 2.1.2 (pip)
# numpy 2.4.3 (pip)
# scipy 1.17.1 (pip)
```

## Sources

- PySide6 QGraphicsView docs: https://doc.qt.io/qt-6/qgraphicsview.html (HIGH confidence)
- VTK vtkBoxWidget2 docs: https://vtk.org/doc/nightly/html/classvtkBoxWidget2.html (HIGH confidence)
- VTK vtkImplicitBoolean docs: https://vtk.org/doc/nightly/html/classvtkImplicitBoolean.html (HIGH confidence)
- VTK vtkActor2D docs: https://vtk.org/doc/nightly/html/classvtkActor2D.html (HIGH confidence)
- Qt QUndoStack docs: https://doc.qt.io/qt-6/qundostack.html (HIGH confidence)
- napari shapes layer: https://napari.org/stable/howtos/layers/shapes.html (MEDIUM confidence — used for evaluation only, not adoption)
- shapely MultiPolygon: https://shapely.readthedocs.io/en/stable/reference/shapely.MultiPolygon.html (HIGH confidence)
- QuickIce codebase: interface_panel.py, interface_viewer.py, vtk_utils.py, phase_diagram_widget.py (HIGH confidence — first-party)
