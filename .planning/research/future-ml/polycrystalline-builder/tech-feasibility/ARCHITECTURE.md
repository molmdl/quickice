# Architecture Patterns — Polycrystalline Builder

**Domain:** Molecular simulation GUI — polycrystalline ice/hydrate builder
**Researched:** 2026-06-28

## Recommended Architecture

### Overall Architecture: 2D Editor + 3D Preview + Generate-Clip-Resolve Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PolyBuilderTab (new tab in MainWindow)          │
│                                                                     │
│  ┌──────────────────────┐  ┌──────────────────────┐                │
│  │   ShapeEditorPanel   │  │   PreviewPanel       │                │
│  │   (QGraphicsView)    │  │   (VTK render window)│                │
│  │                       │  │                       │                │
│  │  ┌─────────────────┐ │  │  ┌─────────────────┐ │                │
│  │  │ QGraphicsScene  │ │  │  │ vtkRenderer     │ │                │
│  │  │ - RegionItems    │ │  │  │ - Prism actors  │ │                │
│  │  │ - Selection      │ │  │  │ - Atom actors   │ │                │
│  │  │ - Move/Resize    │ │  │  │ - Text overlay  │ │                │
│  │  └─────────────────┘ │  │  └─────────────────┘ │                │
│  └──────────────────────┘  └──────────────────────┘                │
│                                                                     │
│  ┌──────────────────────┐  ┌──────────────────────┐                │
│  │   RegionTableModel   │  │   PhaseConfigPanel    │                │
│  │   (QTableView)       │  │   (phase, orient,    │                │
│  │                       │  │    z-range, color)    │                │
│  └──────────────────────┘  └──────────────────────┘                │
│                                                                     │
│  ┌──────────────────────────────────────────────────┐              │
│  │   Generate Button → PolyBuilderWorker (QThread)  │              │
│  └──────────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Model: 2.5D Region (shapely Polygon + Z-range)

```python
@dataclass
class PhaseRegion:
    """A single crystalline region in the polycrystalline box.
    
    2.5D model: shapely Polygon for XY projection + Z-range for extrusion.
    The resulting 3D region is a prism (polygon extruded along Z).
    """
    polygon: Polygon          # shapely 2D polygon (XY projection)
    z_min: float              # bottom of Z extrusion (nm)
    z_max: float              # top of Z extrusion (nm)
    phase_id: str             # e.g., "ice_ih", "hydrate_sI"
    orientation: Rotation     # scipy Rotation for crystal orientation
    seed: int                 # GenIce2 random seed for H-bond network
    name: str                 # Display name (e.g., "Grain 1")
    color: tuple              # RGB for rendering
    
    @property
    def volume_nm3(self) -> float:
        """Volume in nm³ = polygon area × Z height."""
        return self.polygon.area * (self.z_max - self.z_min)
    
    def to_vtk_implicit(self) -> vtkImplicitBoolean:
        """Convert to VTK implicit function for point-in-region testing."""
        # Prism = Intersection(polygon_loop, z_min_plane, z_max_plane)
        ...
    
    def to_vtk_actor(self) -> vtkActor:
        """Convert to translucent VTK prism actor for 3D preview."""
        ...


@dataclass  
class PolycrystalConfig:
    """Full polycrystalline box configuration."""
    box_x: float              # nm
    box_y: float              # nm
    box_z: float              # nm
    regions: list[PhaseRegion]
    
    def validate(self) -> list[str]:
        """Check for overlapping regions, undersized grains, PBC violations."""
        ...
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **ShapeEditorPanel** | 2D shape editing via QGraphicsView | RegionTableModel (CRUD), QUndoStack (undo/redo) |
| **RegionTableModel** | Region data CRUD, validation, serialization | ShapeEditorPanel, PhaseConfigPanel, PolyBuilderWorker |
| **PhaseConfigPanel** | Per-region phase/orientation/Z/color settings | RegionTableModel |
| **PreviewPanel** | VTK 3D preview of region layout + generated atoms | RegionTableModel (region data), MainWindow (result) |
| **PolyBuilderWorker** | Background generation thread (QThread) | RegionTableModel (config), PreviewPanel (atoms result) |
| **GenerateClipResolve** | Core algorithm: generate supercells → clip → resolve overlaps | PolyBuilderWorker (orchestrator), IceGenerator, cKDTree |
| **VoronoiGrainGenerator** | Auto-generate Voronoi grain layout from seed count | RegionTableModel (populates regions), shapely, scipy.Voronoi |
| **CrossSectionView** | matplotlib 2D Z-slice preview (optional) | RegionTableModel (region data at Z-height) |

### Data Flow

```
User Interaction Flow:
1. User draws/edits regions in ShapeEditorPanel (2D polygons)
2. Each edit → QUndoStack push → RegionTableModel update
3. RegionTableModel emits signal → PreviewPanel updates VTK actors
4. User configures phase/orientation per region in PhaseConfigPanel

Generation Flow:
1. User clicks "Generate" → PolyBuilderWorker.spawn()
2. Worker reads PolycrystalConfig from RegionTableModel
3. For each region: GenIce2 generates supercell with seed+orientation
4. GenerateClipResolve clips atoms by region (contains_xy for XY, Z-range check)
5. Overlap detection: cKDTree between all grains (staged, pairwise)
6. Overlap resolution: remove overlapping molecules (whole-molecule, per existing pattern)
7. Boundary treatment: apply three-tier strategy per phase-boundary research
8. Worker emits result → PreviewPanel renders atoms → MainWindow stores result
```

## Patterns to Follow

### Pattern 1: Dual-Sync (2D Editor ↔ 3D Preview)
**What:** Region changes in QGraphicsView are immediately reflected in VTK preview
**When:** Every user edit (move, resize, add, delete region)
**Implementation:**
```python
class RegionTableModel(QtCore.QAbstractTableModel):
    regions_changed = QtCore.Signal()  # emitted on any change
    
    def setData(self, index, value, role):
        # ... update region ...
        self.regions_changed.emit()

class PreviewPanel(QtWidgets.QWidget):
    def __init__(self, model):
        self.model = model
        self.model.regions_changed.connect(self._update_actors)
    
    def _update_actors(self):
        for region in self.model.regions:
            actor = region.to_vtk_actor()
            # Replace existing actor or update properties
```

### Pattern 2: Shapely as Geometry Truth, VTK as Rendering Shell
**What:** shapely Polygon is the authoritative geometry; VTK actors are derived views
**When:** All geometry operations (overlap, containment, clipping)
**Rationale:** shapely has robust 2D predicates; VTK's implicit functions are less convenient for 2D operations but essential for 3D preview

### Pattern 3: Staged Overlap Resolution
**What:** Process overlaps in phases, not all-at-once
**When:** Polycrystalline generation with 10+ grains
**Implementation:**
```python
# Stage 1: Build per-grain atom trees
grain_trees = {i: cKDTree(grain.positions, boxsize=box) for i, grain in grains.items()}

# Stage 2: Pairwise overlap detection (O(k²) where k = number of grains, not atoms)
for i, j in grain_pairs:
    overlaps = grain_trees[i].query_ball_tree(grain_trees[j], r=threshold)

# Stage 3: Resolve by priority (larger grain wins, or boundary-buffer strategy)
```

### Pattern 4: QUndoStack for Shape Editing
**What:** Every user action creates a QUndoCommand for undo/redo
**When:** Shape add, delete, move, resize, property change
**Example:**
```python
class AddRegionCommand(QUndoCommand):
    def __init__(self, model, region):
        super().__init__("Add region")
        self.model = model
        self.region = region
    
    def undo(self):
        self.model.remove_region(self.region)
    
    def redo(self):
        self.model.add_region(self.region)
```

### Pattern 5: Y-Flip Coordinate Convention
**What:** Qt uses Y-down (screen coordinates), VTK/shapely use Y-up (mathematical)
**When:** All conversions between QGraphicsView and shapely/VTK
**Implementation:**
```python
# Qt → shapely: negate Y
shapely_y = -qt_y

# shapely → Qt: negate Y
qt_y = -shapely_y

# Use shapely.affinity.scale(yfact=-1, origin=(0,0)) for polygon flip
# BENCHMARKED: works correctly
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: VTK for 2D Geometry Operations
**What:** Using VTK implicit functions for polygon overlap detection
**Why bad:** VTK's EvaluateFunction is per-point (not vectorized), 10x slower than shapely contains_xy
**Instead:** Use shapely for all 2D geometry; VTK only for 3D rendering and point-in-prism

### Anti-Pattern 2: Monolithic Overlap Resolution
**What:** Building one giant cKDTree with all grains and running query_ball_tree
**Why bad:** query_ball_tree is O(n²) in the worst case; at 500k+ atoms this takes >10s
**Instead:** Pairwise grain overlap detection (O(k²) pairs × O(n log n) per pair), then resolve per-boundary

### Anti-Pattern 3: Real-Time GenIce2 Generation
**What:** Trying to update 3D preview with actual atoms during shape editing
**Why bad:** GenIce2 takes 0.08–2.58s per grain; interactive editing requires <16ms response
**Instead:** Show only region prisms during editing; generate atoms on "Generate" button click (background thread)

### Anti-Pattern 4: 3D Voronoi for Grain Layout
**What:** Using scipy.spatial.Voronoi in 3D for automatic grain generation
**Why bad:** 3D Voronoi produces many unbounded regions (only 922/1001 finite for 1000 seeds); clipping is complex
**Instead:** Use 2D Voronoi + mirror-point technique + Z-range extrusion for 2.5D grains

### Anti-Pattern 5: GraphicsView for 3D Rendering
**What:** Trying to render 3D content in QGraphicsView
**Why bad:** QGraphicsView is strictly 2D; fake 3D via transforms is fragile
**Instead:** Use VTK for 3D, QGraphicsView for 2D editing only

## Scalability Considerations

| Concern | 10 grains (~50k atoms) | 20 grains (~200k atoms) | 100 grains (~1M atoms) |
|---------|------------------------|-------------------------|------------------------|
| GenIce2 generation | ~1.5s total | ~5s total | ~25s total |
| cKDTree overlap detection | 0.05s | 0.2s | 3s (pairwise staged) |
| shapely overlap check | <0.001s | 0.002s | 0.02s |
| VTK prism rendering | <0.01s | 0.01s | 0.05s |
| VTK atom rendering | ~0.1s | ~0.5s | ~2s |
| VTK point-in-prism | 0.01s | 0.05s | 0.3s |
| QGraphicsView region items | instant | instant | <0.01s |

**Key insight:** The bottleneck is GenIce2 generation (~0.3μs/molecule), not spatial operations. For 100+ grains, a progress dialog with per-grain status is essential.

## matplotlib Cross-Section View (Optional Enhancement)

The matplotlib `FigureCanvasQTAgg` embedding works (verified). It can render a 2D Z-slice showing region polygons clipped at a specific Z-height. This adds value as a "plan view" that complements the QGraphicsView shape editor and VTK 3D preview.

**When to add:** V1 if time permits, otherwise V2. The QGraphicsView editor already provides 2D editing capability; the matplotlib view adds a "readonly" scientific cross-section view with axis labels and scale bars.

**Not a replacement for QGraphicsView** — matplotlib's canvas doesn't support interactive item selection, move, resize, or undo/redo. QGraphicsView is essential for the editor.

## Sources

- All architecture decisions based on benchmarked performance data (see STACK.md)
- Wave 1 findings from shape-gui, poly-gen, phase-boundary researchers
- Existing QuickIce architecture from AGENTS.md (dual-path, MVVM, QThread workers)
