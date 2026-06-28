# Technology Stack — Polycrystalline Builder

**Project:** QuickIce Interactive Polycrystalline Builder
**Researched:** 2026-06-28

## Recommended Stack

### Core Framework (ALL EXISTING — no new dependencies for V1)

| Technology | Version | Purpose | Why | Status |
|------------|---------|---------|-----|--------|
| PySide6 | 6.10.2 | GUI framework | QGraphicsView for 2D shape editor, QUndoStack for undo/redo | EXISTING |
| VTK | 9.5.2 | 3D preview rendering | Translucent prism rendering, vtkImplicitBoolean for point-in-region | EXISTING |
| numpy | 2.4.3 | Array operations | Rotation of atom positions (0.003s/100k atoms), coordinate transforms | EXISTING |
| scipy | 1.17.1 | Spatial algorithms | cKDTree overlap detection (0.17s/100k atoms), Voronoi grain generation | EXISTING |
| shapely | 2.1.2 | 2D geometry model | Polygon operations, vectorized point-in-polygon (0.005s/100k pts), overlap detection | EXISTING |
| matplotlib | 3.10.8 | 2D cross-section preview | FigureCanvasQTAgg for embedded Z-slice view | EXISTING |
| genice2 | 2.2.13.1 | Ice structure generation | All ice phases + hydrate lattices (~0.08s/1k mols) | EXISTING |
| networkx | 3.6.1 | Graph algorithms | Hydrogen bond network topology (existing usage) | EXISTING |
| spglib | 2.7.0 | Space group analysis | Symmetry verification of generated crystals | EXISTING |

### Supporting Libraries (EXISTING — specific roles)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shapely.contains_xy | 2.1.2 | Vectorized point-in-polygon | Atom clipping during Generate-Clip-Resolve |
| shapely.affinity | 2.1.2 | Coordinate transforms | Y-flip between Qt (Y-down) and VTK (Y-up) |
| shapely.ops.unary_union | 2.1.2 | Merge overlapping regions | Region overlap detection and resolution |
| scipy.spatial.Voronoi | 1.17.1 | 2D/3D Voronoi tessellation | Auto grain generation (2D Voronoi + mirror-point) |
| scipy.spatial.cKDTree | 1.17.1 | Fast overlap detection | Atom-level overlap detection with PBC |
| scipy.spatial.transform.Rotation | 1.17.1 | Crystal rotation | Grain orientation application |
| vtk.vtkImplicitBoolean | 9.5.2 | 3D CSG operations | Point-in-prism testing for atom clipping |
| vtk.vtkImplicitSelectionLoop | 9.5.2 | Polygon region in 3D | XY polygon boundary for prism regions |
| vtk.vtkBoxWidget2 | 9.5.2 | Interactive box widget | Region placement and resizing in 3D |
| PySide6.QtGui.QUndoStack | 6.10.2 | Undo/redo support | Shape editing operations |

## Additional Dependencies (NOT needed for V1, only for Full 3D)

| Library | Version | License | Size | Purpose | Why Needed | Can Existing Substitute? |
|---------|---------|---------|------|---------|-------------|--------------------------|
| trimesh | ≥4.5 | MIT | ~15MB | 3D mesh CSG, point-in-mesh | Arbitrary 3D shape definition (spherical inclusions, tapered pores) | NO — shapely is strictly 2D, VTK's implicit functions only handle simple primitives and extruded polygons |

**Recommendation:** Do NOT add trimesh for V1. The 2.5D prism model (shapely Polygon + Z-range) covers ~90% of scientifically interesting polycrystalline configurations. Flag trimesh as a future enhancement if users request arbitrary 3D shapes.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| 2D Geometry | shapely 2.1.2 (EXISTING) | CGAL Python bindings | Heavy dependency, complex build, overkill for polygon ops |
| 2D Geometry | shapely 2.1.2 (EXISTING) | PyGEOS | Deprecated, merged into shapely 2.0+ |
| 3D CSG | 2.5D model (V1) | trimesh | Additional dependency; 2.5D sufficient for V1 |
| 3D CSG | 2.5D model (V1) | open3d | Heavier than trimesh (~200MB), GPU-dependent, overkill |
| 3D Voronoi | scipy Voronoi + shapely clip (V1) | pyvoro | Additional C++ dependency; scipy + mirror-point sufficient for 2D |
| 3D Voronoi | scipy Voronoi + shapely clip (V1) | Voro++ (pyvoro backend) | Same as above |
| Grain Analysis | Not needed for builder | freud-analysis | Only for post-build analysis, not builder functionality |
| 2D Editor | QGraphicsView (EXISTING) | matplotlib embedded | QGraphicsView supports interactive editing (selection, move, resize); matplotlib is display-only |
| 2D Editor | QGraphicsView (EXISTING) | custom QPainter | QGraphicsView provides scene graph, item interaction, undo framework for free |
| Undo/Redo | QUndoStack (EXISTING) | custom command pattern | QUndoStack is battle-tested, integrates with Qt event loop |

## Key Integration Patterns

### shapely → QGraphicsView (2D Editor)
```python
from shapely.geometry import Polygon
from PySide6.QtGui import QPolygonF, QPointF
from PySide6.QtWidgets import QGraphicsPolygonItem

# Shapely polygon → Qt polygon (with Y-flip for Qt Y-down convention)
shapely_poly = Polygon([(0,0), (2,0), (3,1), (1.5,3), (0,1)])
qt_poly = QPolygonF([QPointF(x, -y) for x, y in shapely_poly.exterior.coords])
item = QGraphicsPolygonItem(qt_poly)
item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
```

### shapely → VTK (3D Preview)
```python
# Shapely polygon → extruded VTK prism
coords = list(shapely_poly.exterior.coords)[:-1]
n_sides = len(coords)
z_min, z_max = 0.0, 5.0

points3d = vtk.vtkPoints()
for x, y in coords:
    points3d.InsertNextPoint(x, y, z_min)
for x, y in coords:
    points3d.InsertNextPoint(x, y, z_max)

# Build side quads + top/bottom polygon faces → vtkPolyData → actor
# Construction takes 0.0004s per prism, 0.003s for 20 prisms (BENCHMARKED)
```

### shapely → VTK Implicit (Point-in-Region)
```python
ib = vtk.vtkImplicitBoolean()
ib.SetOperationTypeToIntersection()

loop = vtk.vtkImplicitSelectionLoop()
loop_pts = vtk.vtkPoints()
for x, y in shapely_poly.exterior.coords:
    loop_pts.InsertNextPoint(x, y, 0)
loop.SetLoop(loop_pts)
loop.SetNormal(0, 0, 1)

plane_bot = vtk.vtkPlane()  # z >= 0
plane_top = vtk.vtkPlane()  # z <= 5
ib.AddFunction(loop)
ib.AddFunction(plane_bot)
ib.AddFunction(plane_top)

# Test: ib.EvaluateFunction(pt) < 0 means INSIDE prism
# Performance: 0.054s for 100k points, 0.28s for 500k points (BENCHMARKED)
```

## Performance Summary (BENCHMARKED on actual hardware)

| Operation | 10k atoms | 100k atoms | 500k atoms | 1M atoms |
|-----------|-----------|------------|------------|----------|
| cKDTree build | 0.003s | 0.03s | 0.18s | 0.47s |
| cKDTree overlap query | 0.02s | 0.14s | 1.33s | 10.8s |
| NumPy rotation | 0.001s | 0.003s | 0.003s | 0.01s |
| shapely contains_xy | — | 0.005s | 0.024s | 0.046s |
| VTK point-in-prism | — | 0.054s | 0.28s | — |

| GenIce2 Generation | ~100 mols | ~1k mols | ~8k mols | ~28k mols |
|---------------------|-----------|----------|----------|-----------|
| Ice Ih timing | 0.02s | 0.08s | 0.69s | 2.58s |

## Sources

- All benchmarks: run on actual hardware (Linux x86_64, Python 3.14.3, conda env quickice)
- VTK API: verified via runtime import and method testing (VTK 9.5.2)
- shapely API: verified via runtime testing (shapely 2.1.2)
- PySide6 API: verified via runtime import (PySide6 6.10.2)
- GenIce2 timing: verified through QuickIce's own `generate_candidates()` pipeline
