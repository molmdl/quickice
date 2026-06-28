# Architecture Patterns

**Domain:** Interactive shape editor for molecular simulation region definition
**Researched:** 2026-06-28

## Recommended Architecture

### Overall Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Polycrystalline Builder Tab                                │
│                                                              │
│  ┌──────────────┐  ┌──────────────────────────────────────┐ │
│  │ Left Panel   │  │ Right Panel (QSplitter)             │ │
│  │              │  │                                      │ │
│  │ Box Dims:    │  │ ┌──────────────┐┌─────────────────┐ │ │
│  │ Lx: [5.0]   │  │ │ 2D Editor    ││ 3D Preview      │ │ │
│  │ Ly: [5.0]   │  │ │ QGraphicsView││ VTK RenderWindow │ │ │
│  │ Lz: [10.0]  │  │ │              ││                  │ │ │
│  │              │  │ │ ┌───┐        ││  ┌─────────┐    │ │ │
│  │ Z-Slice:    │  │ │ │   │ Rect   ││  │ translucent│  │ │ │
│  │ [====] 5.0  │  │ │ │   └───┘    ││  │  regions   │  │ │ │
│  │              │  │ │   ○ Ellipse ││  │  + box     │  │ │ │
│  │ Tool:        │  │ │              ││  │  wireframe │  │ │ │
│  │ ○ Select     │  │ └──────────────┘└─────────────────┘ │ │
│  │ ● Rectangle │  │                                      │ │
│  │ ○ Ellipse   │  │                                      │ │
│  │ ○ Polygon   │  └──────────────────────────────────────┘ │
│  │ ○ Freehand  │                                         │
│  │              │  ┌──────────────────────────────────────┐ │
│  │ Region List: │  │ Phase Assignment                     │ │
│  │ □ R1: Ice Ih │  │ Region 1: [Ice Ih ▼]  Z: 0-3 nm    │ │
│  │ □ R2: Liquid │  │ Region 2: [Liquid ▼]  Z: 3-7 nm    │ │
│  │ □ R3: Hyd sI │  │ Region 3: [Hyd sI ▼]  Z: 7-10 nm  │ │
│  │              │  │                                      │ │
│  │ [Generate]   │  │ Overlap: ✓ None detected            │ │
│  └──────────────┘  └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `BoxConfigPanel` | Box dimensions (Lx, Ly, Lz), Z-slice slider | ShapeEditor (scene rect), VTKPreview (box actor) |
| `ShapeEditor` (QGraphicsView) | 2D shape drawing, selection, editing | RegionModel (shape data), VTKPreview (region update) |
| `ShapeScene` (QGraphicsScene) | Item management, selection, z-order | ShapeEditor (item access), QUndoStack (commands) |
| `RegionModel` | shapely geometry + Z-range + phase type data | ShapeEditor (visual ↔ data sync), VTKPreview (3D actors) |
| `VTKPreview` (QVTKRenderWindowInteractor) | 3D translucent region rendering, box wireframe | RegionModel (region data), BoxConfigPanel (dimensions) |
| `PhaseAssignPanel` | Phase type dropdowns, Z-range spinboxes, overlap status | RegionModel (phase assignment), ShapeEditor (region highlighting) |
| `RegionUndoStack` (QUndoStack) | Undo/redo for all shape operations | ShapeScene (command push), MainWindow (menu actions) |

### Data Flow

```
User draws shape on QGraphicsView
    ↓
ShapeScene creates QGraphicsItem subclass (e.g., PhaseRectItem)
    ↓
QUndoCommand pushed to QUndoStack (e.g., AddShapeCommand)
    ↓
PhaseRectItem updates → emits signal with its shapely geometry
    ↓
RegionModel stores: shapely.Polygon + z_min + z_max + phase_type
    ↓
VTKPreview receives region update → creates/replaces translucent vtkActor
    ↓
PhaseAssignPanel updates region list + overlap check (shapely.intersects)
    ↓
User clicks "Generate" → RegionModel produces PhaseRegionConfig list
    ↓
PolycrystallineBuilder generates structure from PhaseRegionConfig
```

## Patterns to Follow

### Pattern 1: 2.5D Shape Data Model
**What:** Each region is a 2D shapely Polygon extruded along Z from `z_min` to `z_max`.
**When:** Always — this is the core data representation.
**Example:**
```python
from dataclasses import dataclass
from shapely.geometry import Polygon

@dataclass
class PhaseRegion:
    """A 2.5D phase region: 2D polygon extruded along Z."""
    shape: Polygon          # 2D footprint in XY plane (units: nm)
    z_min: float            # Bottom of extrusion (nm)
    z_max: float            # Top of extrusion (nm)
    phase_type: str         # "liquid", "hydrate_sI", "ice_Ih", etc.
    region_id: int          # Unique ID for this region
    
    @property
    def volume_nm3(self) -> float:
        """Volume = 2D area × Z height."""
        return self.shape.area * (self.z_max - self.z_min)
    
    def contains_point(self, x: float, y: float, z: float) -> bool:
        """Check if a 3D point is inside this region."""
        return (self.shape.contains(Point(x, y)) 
                and self.z_min <= z <= self.z_max)
    
    def overlaps(self, other: 'PhaseRegion') -> bool:
        """Check 2D overlap AND Z-range overlap."""
        z_overlap = not (self.z_max <= other.z_min or other.z_max <= self.z_min)
        if not z_overlap:
            return False
        return self.shape.intersects(other.shape)
```

### Pattern 2: QGraphicsItem Subclass with Phase Metadata
**What:** Each visible shape in QGraphicsScene is a custom QGraphicsItem subclass that knows its RegionModel reference.
**When:** For all shape items in the 2D editor.
**Example:**
```python
from PySide6.QtWidgets import QGraphicsRectItem
from PySide6.QtGui import QBrush, QPen

class PhaseRectItem(QGraphicsRectItem):
    """Rectangle shape item linked to a PhaseRegion in the data model."""
    
    PHASE_COLORS = {
        "liquid": QColor(100, 149, 237, 80),     # Cornflower blue, translucent
        "hydrate_sI": QColor(255, 165, 0, 80),   # Orange
        "ice_Ih": QColor(0, 200, 200, 80),       # Cyan
    }
    
    def __init__(self, region: PhaseRegion, parent=None):
        # Convert nm coords to scene coords
        x, y = region.shape.exterior.coords[0]  # Simplified
        super().__init__(x, y, region.shape.bounds[2]-x, region.shape.bounds[3]-y, parent)
        self._region = region
        self._update_appearance()
    
    def _update_appearance(self):
        color = self.PHASE_COLORS.get(self._region.phase_type, QColor(200, 200, 200, 80))
        self.setBrush(QBrush(color))
        self.setPen(QPen(color.darker(150), 2))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setToolTip(f"Region {self._region.region_id}: {self._region.phase_type}")
```

### Pattern 3: QUndoCommand for Shape Operations
**What:** Each shape operation (add, delete, move, resize, change phase) is a QUndoCommand.
**When:** For all user-editable operations.
**Example:**
```python
from PySide6.QtGui import QUndoCommand

class AddRegionCommand(QUndoCommand):
    def __init__(self, scene, region: PhaseRegion, item: PhaseRectItem):
        super().__init__("Add region")
        self._scene = scene
        self._region = region
        self._item = item
    
    def redo(self):
        self._scene.addItem(self._item)
        self._region.model.add_region(self._region)
    
    def undo(self):
        self._scene.removeItem(self._item)
        self._region.model.remove_region(self._region.region_id)

class MoveRegionCommand(QUndoCommand):
    def __init__(self, item: PhaseRectItem, old_pos, new_pos):
        super().__init__("Move region")
        self._item = item
        self._old_pos = old_pos
        self._new_pos = new_pos
    
    def redo(self):
        self._item.setPos(self._new_pos)
    
    def undo(self):
        self._item.setPos(self._old_pos)
```

### Pattern 4: NM ↔ Scene Coordinate Mapping
**What:** QGraphicsScene works in pixel-like coordinates. The simulation box is in nanometers. A coordinate mapper translates between the two.
**When:** For all mouse interactions and shape rendering.
**Example:**
```python
class SceneCoordinateMapper:
    """Bidirectional nm ↔ scene coordinate mapping."""
    
    def __init__(self, box_x_nm: float, box_y_nm: float, 
                 scene_width_px: int, scene_height_px: int):
        self.scale_x = scene_width_px / box_x_nm  # px per nm
        self.scale_y = scene_height_px / box_y_nm
        self.offset_x = 0  # padding
        self.offset_y = 0
    
    def nm_to_scene(self, x_nm: float, y_nm: float) -> tuple[float, float]:
        """Convert nanometer coordinates to scene pixels."""
        return (x_nm * self.scale_x + self.offset_x, 
                y_nm * self.scale_y + self.offset_y)
    
    def scene_to_nm(self, x_px: float, y_px: float) -> tuple[float, float]:
        """Convert scene pixels back to nanometers."""
        return ((x_px - self.offset_x) / self.scale_x, 
                (y_px - self.offset_y) / self.scale_y)
```

### Pattern 5: VTK Translucent Region Rendering
**What:** Each PhaseRegion is rendered as a translucent colored VTK actor showing its 3D extrusion.
**When:** For 3D preview after region definition.
**Example:**
```python
from vtkmodules.all import vtkPolyData, vtkPoints, vtkCellArray, vtkPolyDataMapper, vtkActor

def create_region_actor(region: PhaseRegion, color: tuple) -> vtkActor:
    """Create a translucent VTK actor for a 2.5D phase region."""
    # Get 2D polygon vertices
    coords = list(region.shape.exterior.coords)
    n = len(coords)
    
    # Create top and bottom faces + side walls
    points = vtkPoints()
    # Bottom face (z_min)
    for x, y in coords:
        points.InsertNextPoint(x, y, region.z_min)
    # Top face (z_max)
    for x, y in coords:
        points.InsertNextPoint(x, y, region.z_max)
    
    # Build faces as polygon cells
    # ... (triangulation for non-convex polygons via vtkTriangleFilter)
    
    mapper = vtkPolyDataMapper()
    mapper.SetInputData(polydata)
    
    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    actor.GetProperty().SetOpacity(0.3)  # Translucent
    actor.GetProperty().SetEdgeVisibility(True)
    actor.GetProperty().SetEdgeColor(*color)
    
    return actor
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: VTK 3D Widgets for Shape Definition
**What:** Using vtkBoxWidget2, vtkSphereWidget, etc. to let users place 3D regions.
**Why bad:** VTK 3D widgets only support axis-aligned primitives (box, sphere); no arbitrary polygon support; widget interaction conflicts with VTK camera trackball; users must switch between "draw mode" and "view mode"; extremely poor UX for defining complex shapes.
**Instead:** Use 2D QGraphicsView for shape definition, VTK for preview only.

### Anti-Pattern 2: Matplotlib for Interactive Drawing
**What:** Using matplotlib patches (Rectangle, Polygon) embedded via FigureCanvasQTAgg for interactive shape editing.
**Why bad:** matplotlib is designed for static plots, not interactive editors; no built-in item selection/drag/resize; mouse event handling is cumbersome; no undo framework; redrawing the entire canvas on each mouse move is slow.
**Instead:** Use QGraphicsView for interactive editing; matplotlib only for static phase diagram (existing pattern in QuickIce).

### Anti-Pattern 3: Single-Coordinate-System Coupling
**What:** Tying the 2D editor coordinate system directly to VTK's world coordinates.
**Why bad:** VTK uses different coordinate conventions than Qt; any change in box dimensions would break the 2D editor layout; Z-slice changes require recalculating everything.
**Instead:** Use a SceneCoordinateMapper that decouples nm (data) from scene pixels (view), and a separate Z-slice parameter that controls which 2D cross-section is shown.

### Anti-Pattern 4: Storing Shapes Only in QGraphicsScene
**What:** Relying on QGraphicsItem positions as the source of truth for shape data.
**Why bad:** QGraphicsItems can be in intermediate states during drag; serialization requires extracting geometry from Qt objects; Qt coordinate rounding can introduce nm-scale errors.
**Instead:** Maintain a parallel RegionModel (list of PhaseRegion dataclasses) as the source of truth. QGraphicsItems are views of this model. Changes flow: user → QGraphicsItem → signal → RegionModel update → VTK preview update.

## Scalability Considerations

| Concern | At 5 regions | At 50 regions | At 500 regions |
|---------|--------------|---------------|----------------|
| 2D editor rendering | Instant | Instant | Needs QGraphicsView::NoViewportUpdate for batch operations |
| shapely overlap check | <1ms | ~10ms | ~100ms; batch with prepared geometries |
| VTK translucent rendering | Instant | Instant | May need LOD; reduce opacity to avoid z-buffer fighting |
| QUndoStack depth | Fine | Fine | Set undoLimit to 100 to prevent memory growth |
| Region list UI | Simple QListWidget | Needs scroll | Needs search/filter by phase type |

## Z-Slice Workflow

The recommended approach for Z-axis control:

1. **Single Z-slice (MVP):** One Z-range per region (z_min, z_max). User draws shape on XY plane, then sets Z extent via spinboxes. This covers slab, pocket, and piece geometries.

2. **Multi-slice (enhancement):** User can define shapes at multiple Z heights. A Z-slider on the left panel controls which cross-section is visible in the 2D editor. Regions at different Z heights appear as different layers. Shape interpolation between slices uses shapely's `interpolate()` and `simplify()`.

3. **3D primitive shortcuts:** For common shapes, provide preset buttons: "Add ice slab" (full XY rectangle with Z-range), "Add spherical pocket" (circle with Z-range), "Add cylindrical channel" (rectangle with Z-range = full box height).

## Sources

- PySide6 QGraphicsView: https://doc.qt.io/qt-6/qgraphicsview.html (HIGH confidence)
- VTK vtkBoxWidget2: https://vtk.org/doc/nightly/html/classvtkBoxWidget2.html (HIGH confidence)
- VTK vtkImplicitBoolean: https://vtk.org/doc/nightly/html/classvtkImplicitBoolean.html (HIGH confidence)
- VTK vtkActor2D: https://vtk.org/doc/nightly/html/classvtkActor2D.html (HIGH confidence)
- Qt QUndoStack: https://doc.qt.io/qt-6/qundostack.html (HIGH confidence)
- napari shapes layer: https://napari.org/stable/howtos/layers/shapes.html (MEDIUM confidence — used for design inspiration only)
- QuickIce interface_panel.py: First-party code showing existing two-column layout pattern (HIGH confidence)
- QuickIce interface_viewer.py: First-party code showing VTK integration pattern (HIGH confidence)
- QuickIce phase_diagram_widget.py: First-party code showing matplotlib-in-Qt pattern with shapely usage (HIGH confidence)
