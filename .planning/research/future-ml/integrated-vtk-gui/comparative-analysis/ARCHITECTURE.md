# Architecture Patterns: Scientific Visualization GUIs → QuickIce

**Domain:** Scientific Visualization GUI Architecture
**Researched:** 2026-06-28

## Common Architectural Pattern (All 5 Tools)

Every tool follows the same high-level architecture:

```
┌──────────────────────────────────────────────────┐
│  Menu Bar / Toolbar                               │
├──────────┬───────────────────────┬────────────────┤
│          │                      │                │
│  Left    │    Viewport          │  Right Panel   │
│  Panel   │    (3D Scene)        │  (Properties) │
│  (Nav/   │                      │                │
│   List/   │                      │                │
│   Stack) │                      │                │
│          │                      │                │
├──────────┴───────────────────────┴────────────────┤
│  Bottom Panel (Log / Command Line / Timeline)      │
└──────────────────────────────────────────────────┘
```

Variations:
- **ParaView:** Left = Pipeline Browser + Properties. No right panel. Bottom = Animation.
- **VMD:** Viewport is main window. Panels are floating. Left/right panels don't exist in main window.
- **OVITO:** Left = Pipeline Editor. Right = Properties. No bottom panel by default.
- **ChimeraX:** Left/Right = Dockable panels. Top = Toolbar. Bottom = Command Line + Status.
- **PyMOL:** Right sidebar = Internal GUI (fixed). No left panel. No bottom panel.

## Recommended Architecture for QuickIce

```
┌─────────────────────────────────────────────────────────┐
│  Toolbar: [Home] [Structure] [Interface] [Tools] [...]  │
├────────────┬────────────────────────────┬───────────────┤
│            │                            │               │
│ Pipeline   │   VTK Viewport             │ Properties    │
│ Navigator  │   (QVTKRenderWindow        │ Panel         │
│            │    Interactor)             │ (contextual)  │
│ ○ Source   │                            │               │
│ ├ GenIce   │   [ice lattice +           │ ┌───────────┐ │
│ ○ Modify   │    interface +             │ │ Step      │ │
│ ├ Interface│    solutes +               │ │ params    │ │
│ ├ Solute   │    ions]                   │ │ here      │ │
│ ├ Ion      │                            │ └───────────┘ │
│ ○ Export   │                            │               │
│ ├ GROMACS  │                            │               │
│            │                            │               │
├────────────┴────────────────────────────┴───────────────┤
│  Structure Manager  │  Log / Output                      │
│  [ice✓][iface✓][solv✓][ions✓]  │                      │
└─────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Qt Class | Communicates With |
|-----------|---------------|----------|-------------------|
| **VTKViewport** | 3D rendering, camera, mouse interaction | QWidget + QVTKRenderWindowInteractor | ToolModeManager, StructureManager |
| **PipelineNavigator** | Display pipeline steps, track active step | QDockWidget (left) | PipelineController |
| **PropertiesPanel** | Context-sensitive parameter editing | QDockWidget (right) | PipelineController |
| **Toolbar** | Tool mode selection, quick actions | QToolBar | ToolModeManager |
| **StructureManager** | Per-layer visibility, color, selection | QDockWidget (bottom-left) | VTKViewport |
| **LogPanel** | Console output, command history | QDockWidget (bottom) | All components |
| **ToolModeManager** | Mouse mode dispatch, cursor changes | Internal (no widget) | VTKViewport, Toolbar |
| **PipelineController** | Pipeline step execution, data flow | Internal (no widget) | PipelineNavigator, PropertiesPanel, VTKViewport |

### Data Flow

```
User edits parameter in PropertiesPanel
    │
    ▼
PipelineController receives parameter change
    │
    ▼
PipelineController re-executes affected step(s)
    │
    ├─► If "generate" step changed: re-run GenIce2 → new base structure
    ├─► If "interface" step changed: rebuild interface on current base
    ├─► If "solute" step changed: re-insert solutes on current interface
    └─► If "ion" step changed: re-insert ions on current solute structure
    │
    ▼
PipelineController emits structure_updated signal
    │
    ▼
VTKViewport receives new VTK actors → re-renders
    │
    ▼
StructureManager updates layer list if layers changed
```

## Patterns to Follow

### Pattern 1: Dockable Panel Architecture (ChimeraX)

**What:** All tool panels are QDockWidget instances that can dock, undock, tab, and rearrange.
**When:** Every panel that is not the viewport or toolbar.
**Why:** ChimeraX proves this works for scientific visualization. Users can customize their workspace. Panels can be hidden/shown per tool mode.

```python
class QuickIceMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setDockOptions(
            QMainWindow.AllowNestedDocks |
            QMainWindow.AllowTabbedDocks |
            QMainWindow.AnimatedDocks
        )
        
        # Central widget = VTK viewport
        self.vtk_viewport = VTKViewport(self)
        self.setCentralWidget(self.vtk_viewport)
        
        # Dockable panels
        self.pipeline_nav = PipelineNavigator(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.pipeline_nav)
        
        self.properties = PropertiesPanel(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties)
        
        self.structure_mgr = StructureManager(self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.structure_mgr)
```

### Pattern 2: Contextual Properties Panel (ParaView + OVITO)

**What:** Properties panel changes content based on selected pipeline step. Selecting "Interface" in the pipeline navigator shows interface parameters. Selecting "Ion" shows ion parameters.
**When:** Pipeline step selection changes.
**Why:** Avoids the "tab nightmare" of the current 6-tab design. One panel, one set of relevant controls.

```python
class PropertiesPanel(QDockWidget):
    def on_pipeline_step_selected(self, step: PipelineStep):
        # Clear current widgets
        self.clear_content()
        # Create step-specific parameter widgets
        widget = step.create_properties_widget()
        self.setWidget(widget)
```

### Pattern 3: Modifier Stack Pipeline (OVITO)

**What:** Pipeline is a linear list of steps, displayed bottom-up. Steps can be toggled, reordered, and edited independently. The viewport always shows the output of the *entire* pipeline.
**When:** User is building a structure.
**Why:** Non-destructive editing. Toggle ion insertion off → viewport shows structure without ions. Toggle back on → ions reappear. No data loss.

```python
class PipelineModel:
    """OVITO-style modifier stack for QuickIce."""
    
    def __init__(self):
        self.steps: list[PipelineStep] = [
            GenerateStep(),      # Data source (GenIce2)
            InterfaceStep(),     # Modifier
            SoluteStep(),        # Modifier
            IonStep(),           # Modifier
            ExportStep(),        # Sink (GROMACS)
        ]
    
    def execute(self) -> StructureData:
        """Execute pipeline from source through all enabled modifiers."""
        data = self.steps[0].execute()  # Source step
        for step in self.steps[1:]:
            if step.enabled:
                data = step.execute(data)
        return data
    
    def execute_up_to(self, step_index: int) -> StructureData:
        """Execute pipeline only up to a given step (for debugging)."""
        data = self.steps[0].execute()
        for step in self.steps[1:step_index + 1]:
            if step.enabled:
                data = step.execute(data)
        return data
```

### Pattern 4: Tool Mode Manager (ChimeraX)

**What:** Mouse interaction mode is explicitly managed. Left mouse always navigates (rotate/pan/zoom). Right mouse behavior depends on active tool mode. Toolbar icons select the mode.
**When:** User switches between inspection, selection, drawing, and measurement tools.
**Why:** ChimeraX's separation of navigation (left) from tool action (right) prevents accidental structure changes during navigation.

```python
class ToolModeManager:
    """ChimeraX-style tool mode management."""
    
    NAVIGATE = "navigate"
    PICK = "pick"
    MEASURE = "measure"
    DRAW_REGION = "draw_region"
    QUERY = "query"
    
    def __init__(self, vtk_viewport: VTKViewport):
        self.vtk_viewport = vtk_viewport
        self.current_mode = self.NAVIGATE
        self._interactors = {
            self.NAVIGATE: vtk_viewport.default_interactor,
            self.PICK: PickInteractor(),
            self.MEASURE: MeasureInteractor(),
            self.DRAW_REGION: DrawRegionInteractor(),
            self.QUERY: QueryInteractor(),
        }
    
    def set_mode(self, mode: str):
        self.current_mode = mode
        interactor = self._interactors[mode]
        self.vtk_viewport.set_interactor_style(interactor)
        self.vtk_viewport.set_cursor(self._cursor_for_mode(mode))
```

### Pattern 5: Structure Layer Manager (ChimeraX Model Panel adapted)

**What:** Each structural component (ice, interface, liquid, solutes, ions) is a separate "model" with independent visibility, color, and representation controls.
**When:** User needs to inspect specific parts of the composite structure.
**Why:** ChimeraX's Model Panel is the cleanest implementation of multi-model management. Hierarchical show/hide (hide "All" hides everything; hide "Ice" hides only ice lattice).

```python
class StructureLayer:
    """One visible structural component in the scene."""
    
    def __init__(self, name: str, vtk_actor: vtk.vtkActor):
        self.name = name
        self.actor = vtk_actor
        self.visible = True
        self.color = QColor("white")
        self.opacity = 1.0

class StructureManager(QDockWidget):
    """ChimeraX Model Panel adapted for QuickIce."""
    
    LAYERS = ["Ice Lattice", "Interface", "Liquid", "Solutes", "Ions"]
    
    def set_layer_visibility(self, layer_name: str, visible: bool):
        layer = self._layers[layer_name]
        layer.visible = visible
        layer.actor.SetVisibility(visible)
        self.vtk_viewport.render()
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: DAG Pipeline for Linear Flow (ParaView Trap)

**What:** Building a fully general directed-acyclic-graph pipeline engine where any step can connect to any other step.
**Why bad:** ParaView needs this because its users build arbitrary analysis pipelines. QuickIce has a fixed 5-step linear flow. A DAG engine would add massive complexity (cycle detection, type checking at connections, multi-output handling) for zero benefit.
**Instead:** Fixed-sequence modifier stack (OVITO model). Steps always execute in order. Each step receives the output of the previous step. No branching, no merging.

### Anti-Pattern 2: Floating Tool Windows (VMD Trap)

**What:** Each tool opens in its own floating window that can be placed anywhere on screen.
**Why bad:** Window management becomes the user's burden. Tools get lost behind other windows. No spatial consistency between sessions. Screen clutter. VMD's 20+ floating windows are a known pain point.
**Instead:** QDockWidget panels that dock to the main window. Panels can be undocked for advanced users but default to docked.

### Anti-Pattern 3: Dual GUI (PyMOL Trap)

**What:** One window for the 3D viewport with a minimal sidebar, plus a completely separate window for settings and controls.
**Why bad:** Users must manage two windows. Context switching between windows disrupts workflow. Settings in the external GUI don't clearly map to what's visible in the internal GUI.
**Instead:** Single QMainWindow with dockable panels. All controls visible in one window.

### Anti-Pattern 4: Tab-Heavy UI (Current QuickIce Trap)

**What:** QTabWidget with 6 tabs, each containing an independent VTK viewer and its own parameter panel.
**Why bad:** Tabs hide information. Users can't see the pipeline progress. Each tab's VTK viewer is independent → duplicated rendering code, inconsistent camera states, memory overhead. Tab switching is slow if VTK renderers need to initialize.
**Instead:** Single viewport + pipeline navigator. Selecting a pipeline step changes the properties panel content. The viewport always shows the current state of the entire pipeline.

### Anti-Pattern 5: Per-Tab VTK Renderers

**What:** Each tab (or pipeline step) gets its own QVTKRenderWindowInteractor with its own VTK render window.
**Why bad:** Memory waste (5+ VTK render windows). Camera inconsistency between tabs. Duplicated actor management code. Slow tab switching.
**Instead:** Single VTK render window. All structural layers rendered as separate actors in one scene. Visibility controls determine which layers are shown.

## Scalability Considerations

| Concern | At 100 atoms | At 100K atoms | At 10M atoms |
|---------|-------------|---------------|--------------|
| Rendering | VTK handles trivially | VTK handles well (VTK 9.5 has GPU acceleration) | May need level-of-detail, point cloud mode |
| Pipeline re-execution | Instant | <1s (GenIce2 + inserters) | ~5s (large polycrystals) — need async execution |
| Modifier toggle | Instant re-render | Instant re-render | Re-execute from toggle point → render |
| Memory | <10 MB | ~100 MB | ~1-2 GB — may need structure eviction |
| Interactive picking | Fast (kd-tree trivial) | Fast (kd-tree build <1s) | Need spatial indexing acceleration |

**Key insight:** QuickIce's typical structures are 5K-500K atoms. VTK handles this fine. The bottleneck is pipeline re-execution when parameters change, not rendering. This means:
- Rendering: Direct VTK actor management is sufficient. No need for LOD or GPU instancing.
- Pipeline: Use `QThread` worker (already established pattern with `HydrateWorker`) for async execution.
- Interaction: Standard VTK pickers work fine for QuickIce's atom counts.

## Python VTK Framework Assessment

| Framework | Type | Qt Integration | VTK Version | QuickIce Fit | Why |
|-----------|------|-----------------|-------------|--------------|-----|
| **trame** | Web-first framework | Indirect (via browser) | VTK 9.x + ParaView | **Poor** | Web-first architecture doesn't match native desktop. Would replace PySide6 with web stack. Massive architectural change for no benefit. |
| **PyVista** | High-level VTK wrapper | PySide6 via `BackgroundPlotter` | VTK 9.x | **Poor** | Opinionated abstraction layer hides VTK interactor customization. QuickIce needs custom interactors (draw region, pick atom). PyVista fights you on this. |
| **vedo** | Scripting-oriented | Qt via `show()` method | VTK 9.x | **Poor** | Designed for scripts, not applications. No Qt integration story. Good for quick prototyping, bad for production GUI. |
| **Raw VTK + QVTKRenderWindowInteractor** | Direct VTK in Qt | Native PySide6 | VTK 9.5.2 (in env) | **Best** | Full control over interactors, actors, mappers. Already in use. ParaView itself uses this pattern. No new dependencies. |

**Recommendation:** Stick with raw VTK + QVTKRenderWindowInteractor. This is what ParaView uses internally. It gives full control over:
- Custom interactor styles (for tool modes)
- Actor management (for structure layers)
- Pipeline execution (for modifier stack)
- Rendering optimization (for large structures)

No framework fight. No abstraction leak. No new dependencies.

## Sources

- ParaView: https://docs.paraview.org/en/latest/UsersGuide/introduction.html (MEDIUM-HIGH)
- OVITO Pipeline: https://www.ovito.org/docs/current/usage/pipeline.html (HIGH)
- OVITO Viewports: https://www.ovito.org/docs/current/usage/viewports.html (HIGH)
- ChimeraX Window: https://www.cgl.ucsf.edu/chimerax/docs/user/window.html (HIGH)
- ChimeraX Toolbar: https://www.cgl.ucsf.edu/chimerax/docs/user/tools/toolbar.html (HIGH)
- ChimeraX Model Panel: https://www.cgl.ucsf.edu/chimerax/docs/user/tools/modelpanel.html (HIGH)
- VMD Windows: https://www.ks.uiuc.edu/Research/vmd/current/ug/node38.html (MEDIUM)
- VMD Mouse Modes: https://www.ks.uiuc.edu/Research/vmd/current/ug/node32.html (MEDIUM)
- VMD Plugins: https://www.ks.uiuc.edu/Research/vmd/plugins/ (MEDIUM)
- trame: https://kitware.github.io/trame/guide/ (HIGH)
- vedo: https://vedo.embl.es/ (MEDIUM)
- PyMOL: https://github.com/schrodinger/pymol-open-source (MEDIUM)
