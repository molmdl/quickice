# Architecture Patterns: Single-Viewport VTK Design

**Domain:** VTK-Centric GUI — Unified 3D Viewport
**Researched:** 2026-06-28

## Recommended Architecture

### Overall Structure

```
QMainWindow
├── Central Widget: QVTKRenderWindowInteractor (single shared viewport)
│   └── vtkRenderWindow (1)
│       ├── vtkRenderer[0] — Main 3D scene (layer 0)
│       │   ├── vtkAssembly "ice" — Ice framework actors
│       │   ├── vtkAssembly "water" — Water box actors
│       │   ├── vtkAssembly "guests" — Guest molecule actors
│       │   ├── vtkAssembly "solute" — Solute molecule actors
│       │   ├── vtkAssembly "ions" — Ion actors (Na+, Cl-)
│       │   ├── vtkAssembly "custom" — Custom molecule actors
│       │   ├── vtkAssembly "unit_cell" — Unit cell wireframe
│       │   ├── vtkAssembly "hbonds" — Hydrogen bond dashed lines
│       │   └── vtkActor "preview" — Preview molecule (semi-transparent)
│       ├── vtkRenderer[1] — 2D HUD overlay (layer 1, SetViewport=full)
│       │   ├── vtkTextActor — Phase labels, measurement text
│       │   └── vtkCornerAnnotation — Status info
│       └── [Split-view mode] vtkRenderer[2] — Right half (SetViewport)
├── QDockWidget LEFT — Control panels (tabbed)
│   ├── Ice Generation panel
│   ├── Interface Construction panel
│   ├── Solute/Custom/Ion panels
│   └── Phase Diagram
├── QDockWidget RIGHT — Export & Info panels
│   ├── Export panel
│   └── Info/Log panel
└── QToolBar — Viewport controls (representation, H-bonds, zoom, auto-rotate)
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `UnifiedViewerWidget` | Owns the single `QVTKRenderWindowInteractor`, manages renderer, assemblies, camera | `StructureActorBuilder`, `MainWindow` |
| `StructureActorBuilder` | Converts any structure type → `list[vtkAssembly]` | `UnifiedViewerWidget`, all renderer modules |
| `ActorGroup` (vtkAssembly wrapper) | Manages one phase's actors, visibility toggle, representation mode | `UnifiedViewerWidget` |
| `CameraManager` | Single camera state, reset-on-new-structure, view presets | `UnifiedViewerWidget` |
| `SplitViewController` | Manages `SetViewport()` split, dual-candidate display | `UnifiedViewerWidget` |
| `OverlayManager` | 2D text labels, annotations on layer-1 renderer | `UnifiedViewerWidget` |

### Data Flow

```
Structure generation result (any type)
    ↓
StructureActorBuilder.build(result) → dict[str, vtkAssembly]
    ↓
UnifiedViewerWidget.update_actors(assemblies_dict)
    ├── Remove previous assemblies for changed phases
    ├── Add new assemblies to renderer
    ├── Preserve camera if partial update (e.g., add ions to existing interface)
    ├── ResetCamera if full update (e.g., new ice candidate)
    └── render_window.Render()
```

## Patterns to Follow

### Pattern 1: vtkAssembly for Phase Grouping

**What:** Each structure phase (ice, water, guests, solutes, ions, custom, unit_cell, hbonds) is wrapped in a `vtkAssembly`. The assembly contains all actors for that phase.

**When:** Always — this is the core architectural pattern.

**Why:** 
- `assembly.SetVisibility(0/1)` toggles the entire phase in one call
- Adding/removing an assembly from the renderer is O(1) vs iterating over many actors
- Nested assemblies are supported (assembly can contain sub-assemblies)
- VTK's rendering pipeline correctly skips invisible assemblies

**Example:**
```python
import vtkmodules.all as vtk

class ActorGroup:
    """Wraps a vtkAssembly for one structure phase."""
    
    def __init__(self, name: str, actors: list[vtk.vtkActor]):
        self.name = name
        self.assembly = vtk.vtkAssembly()
        for actor in actors:
            self.assembly.AddPart(actor)
    
    def set_visible(self, visible: bool) -> None:
        self.assembly.SetVisibility(1 if visible else 0)
    
    def is_visible(self) -> bool:
        return bool(self.assembly.GetVisibility())
    
    def set_opacity(self, opacity: float) -> None:
        """Set opacity on all parts."""
        self.assembly.GetParts().InitTraversal()
        part = self.assembly.GetParts().GetNextProp()
        while part:
            part.GetProperty().SetOpacity(opacity)
            part = self.assembly.GetParts().GetNextProp()
```

### Pattern 2: Incremental Actor Update

**What:** When a downstream phase adds actors (e.g., ions added to existing interface), only add the new assembly — don't rebuild existing ones.

**When:** Partial pipeline updates (adding ions/solutes to existing interface).

**Example:**
```python
class UnifiedViewerWidget(QWidget):
    def __init__(self):
        ...
        self._groups: dict[str, ActorGroup] = {}  # phase_name → ActorGroup
    
    def update_phase(self, phase_name: str, actors: list[vtk.vtkActor]) -> None:
        """Replace actors for one phase, preserving all others."""
        # Remove old group if exists
        if phase_name in self._groups:
            self.renderer.RemoveActor(self._groups[phase_name].assembly)
        
        # Create and add new group
        group = ActorGroup(phase_name, actors)
        self._groups[phase_name] = group
        self.renderer.AddActor(group.assembly)
        
        # Camera: reset only on full structure change
        if phase_name in ("ice", "interface"):
            self._reset_camera()
        
        self.render_window.Render()
```

### Pattern 3: Camera Preservation

**What:** Preserve camera orientation when adding downstream phases (ions, solutes). Reset camera only when the base structure changes (new ice candidate, new interface).

**When:** All downstream phase additions.

**Example:**
```python
def _should_reset_camera(self, phase_name: str) -> bool:
    """Only reset camera for base structure changes."""
    return phase_name in ("ice", "interface", "hydrate")
```

### Pattern 4: Split View via SetViewport

**What:** For candidate comparison, use `vtkRenderer.SetViewport()` to divide the single render window into left/right regions. Each renderer has its own actors and camera but shares the same OpenGL context.

**When:** Ice Generation tab's dual-view candidate comparison.

**Example:**
```python
def enable_split_view(self) -> None:
    """Split viewport into left/right for candidate comparison."""
    self._renderer_left = vtk.vtkRenderer()
    self._renderer_right = vtk.vtkRenderer()
    
    self._renderer_left.SetViewport(0.0, 0.0, 0.5, 1.0)  # Left half
    self._renderer_right.SetViewport(0.5, 0.0, 1.0, 1.0)  # Right half
    
    self.render_window.AddRenderer(self._renderer_left)
    self.render_window.AddRenderer(self._renderer_right)
    
    # Synchronize cameras (same pattern as current DualViewerWidget)
    self._setup_camera_sync()

def disable_split_view(self) -> None:
    """Return to single-viewport mode."""
    self.render_window.RemoveRenderer(self._renderer_left)
    self.render_window.RemoveRenderer(self._renderer_right)
    # Re-add single renderer
    self.render_window.AddRenderer(self._renderer_main)
```

### Pattern 5: 2D Overlay via Renderer Layers

**What:** Use a second `vtkRenderer` on layer 1 for 2D overlays that don't rotate with the 3D scene. Set `SetBackgroundAlpha(0)` for transparency.

**When:** Phase labels, measurement annotations, tool indicators.

**Example:**
```python
def _setup_overlay_renderer(self) -> None:
    """Create 2D overlay renderer for HUD elements."""
    self.render_window.SetNumberOfLayers(2)
    
    self._overlay_renderer = vtk.vtkRenderer()
    self._overlay_renderer.SetLayer(1)
    self._overlay_renderer.SetViewport(0.0, 0.0, 1.0, 1.0)
    self._overlay_renderer.SetBackgroundAlpha(0)  # Transparent background
    self._overlay_renderer.SetInteractive(0)  # No mouse interaction on overlay
    
    self.render_window.AddRenderer(self._overlay_renderer)
    
    # Add text label
    text = vtk.vtkTextActor()
    text.SetInput("Ice Phase")
    text.SetPosition(10, 10)
    self._overlay_renderer.AddActor(text)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Flat Actor List with Per-Actor Visibility

**What:** Adding all actors via `renderer.AddActor()` and toggling visibility per-actor.

**Why bad:** With 10+ actor groups, tracking which actors belong to which phase becomes error-prone. Adding/removing actors requires iterating the full list. Camera reset logic becomes confused about which actors are visible.

**Instead:** Use `vtkAssembly` for group-level management.

### Anti-Pattern 2: Separate Render Windows per Phase

**What:** Creating a `vtkRenderWindow` for each phase (current approach).

**Why bad:** Each render window creates an independent OpenGL context. 8 contexts = 8x GPU memory for framebuffer objects, 8x render passes, 8x interactor overhead. Tab switching destroys/recreates contexts.

**Instead:** Single render window with one or two renderers.

### Anti-Pattern 3: Duplicating Renderer Logic per Viewer

**What:** Each viewer class has its own `_setup_vtk()`, `_extract_bonds()`, `_create_guest_ball_and_stick_actor()`.

**Why bad:** The current codebase has 4 nearly identical copies of `_extract_bonds()` and `_create_guest_ball_and_stick_actor()` across `InterfaceViewerWidget`, `SoluteViewerWidget`, `IonViewerWidget`, and `CustomMoleculeViewerWidget`.

**Instead:** Extract into `StructureActorBuilder` with phase-specific actor creation methods.

### Anti-Pattern 4: Resetting Camera on Every Actor Addition

**What:** Calling `ResetCamera()` every time a downstream phase is added (ions on interface, solutes on interface).

**Why bad:** Camera jumps to fit new actors, disrupting the user's viewing angle. The base structure (ice/water interface) is much larger than the added ions/solutes.

**Instead:** Only reset camera on base structure changes. For downstream additions, adjust clipping range or do nothing.

### Anti-Pattern 5: QStackedWidget with Hidden VTK Viewers

**What:** Using `QStackedWidget` to swap between placeholder and VTK viewer (current hydrate/ion/solute/custom molecule viewers).

**Why bad:** The hidden VTK viewer still exists in memory with its render window and OpenGL context. With 5+ stacked viewers, GPU resources are consumed even when not visible.

**Instead:** Single VTK widget is always present. Show/hide actors instead of swapping widgets.

## Scalability Considerations

| Concern | At 100 atoms | At 15K atoms (typical) | At 500K atoms (extreme) |
|---------|--------------|------------------------|------------------------|
| Actor build time | <1ms | ~40ms | ~200ms |
| PolyData memory | ~1 KB | ~600 KB | ~14 MB |
| Render time (estimated) | <5ms | ~20ms | ~100-500ms |
| Assembly toggle | O(1) | O(1) | O(1) |
| Camera reset | <1ms | ~2ms | ~10ms |

**Key insight:** Typical QuickIce structures (ice 768 mol + water 4000 mol = ~15K atoms) are well within VTK's comfortable rendering range. Even with all phases simultaneously displayed, total actor count stays under 30 and total polydata under 5 MB. The bottleneck is not rendering but actor construction (the O(n²) bond detection in hydrate_renderer).

## QVTKRenderWindowInteractor + QMainWindow Integration

### Verified: QVTKRenderWindowInteractor as Central Widget

`QVTKRenderWindowInteractor` inherits from `QWidget` (confirmed in VTK 9.5.2). It can be set as `QMainWindow.setCentralWidget()`.

**Expected layout:**
```
QMainWindow
├── setCentralWidget(QVTKRenderWindowInteractor)  ← fills remaining space
├── addDockWidget(LEFT, control_dock)               ← resizable, floatable
├── addDockWidget(RIGHT, info_dock)                 ← resizable, floatable
└── addToolBar(TOP, viewport_toolbar)               ← dockable toolbar
```

**Resize behavior:** When QDockWidgets resize, the central VTK widget automatically adjusts. VTK will call `Render()` on resize events. This is efficient because VTK only re-renders when the window actually changes size.

**Key constraint:** The VTK widget must call `Initialize()` after it has a parent and is shown. The current codebase does this correctly. In the new architecture, call `Initialize()` in `UnifiedViewerWidget.__init__()` after creating the widget.

## Dual-View Architecture Detail

### Option A: SetViewport Split (RECOMMENDED)

```
┌──────────────────┬──────────────────┐
│   Renderer 0     │   Renderer 1     │
│   (left half)    │   (right half)   │
│                  │                  │
│  Candidate #1   │  Candidate #2   │
│  (Rank 1)       │  (Rank 2)       │
│                  │                  │
│  SetViewport     │  SetViewport     │
│  (0,0,0.5,1)    │  (0.5,0,1,1)    │
└──────────────────┴──────────────────┘
     1 QVTKRenderWindowInteractor
     1 vtkRenderWindow
     2 vtkRenderers
```

**Pros:**
- Single OpenGL context
- Single interactor (mouse events routed to renderer under cursor)
- Camera sync via DeepCopy (same as current DualViewerWidget)
- Easy to toggle between split/single view

**Cons:**
- Mouse interaction routing needs testing (may need custom interactor style)
- Each renderer needs separate actor assemblies (2x actor creation for comparison)

### Option B: QSplitter with Two QVTKRenderWindowInteractors

**Not recommended** — this is essentially the current `DualViewerWidget` approach. Two render windows = two OpenGL contexts. The only advantage is simpler mouse interaction routing.

### Option C: Single Viewport with Candidate Cycling

```
┌────────────────────────────────────┐
│           Single Renderer           │
│                                    │
│   [◀ Prev]  Candidate #1  [Next ▶] │
│   (Rank 1)                         │
│                                    │
└────────────────────────────────────┘
```

**When to use:** As a fallback if `SetViewport()` mouse interaction proves buggy. Also useful for small screens.

## Camera Management Strategy

### Single Camera (Default Mode)

One camera controls the entire scene. All assemblies share this camera.

**When to reset:**
- New ice candidate loaded → `ResetCamera()`
- New interface/hydrate structure → `ResetCamera()`
- Adding ions/solutes to existing → DO NOT reset (preserve viewing angle)

### Dual Camera (Split View Mode)

Two cameras, one per renderer. Synchronized via `DeepCopy` on modification events.

**Camera sync pattern (same as current DualViewerWidget):**
```python
def _on_camera1_modified(self, obj, event):
    if self._syncing:
        return
    self._syncing = True
    cam2.DeepCopy(cam1)
    renderer2.Render()
    self._syncing = False
```

## Sources

- VTK 9.5.2 installed in quickice conda env (verified `vtk.vtkVersion.GetVTKVersion()`)
- `vtkAssembly` API tested: `AddPart()`, `GetParts()`, `SetVisibility()`, nested assemblies
- `vtkRenderer.SetViewport()`, `SetLayer()` API confirmed
- `vtkRenderWindow.SetNumberOfLayers()` confirmed
- `vtkTextActor`, `vtkBillboardTextActor3D`, `vtkCornerAnnotation` availability confirmed
- `vtkDepthSortPolyData` available in VTK 9.5.2
- `vtkActorCollection` available (but `vtkAssembly` is preferred)
- QuickIce viewer codebase fully analyzed (7 viewer files, 4 renderer files, 1 utils file)
