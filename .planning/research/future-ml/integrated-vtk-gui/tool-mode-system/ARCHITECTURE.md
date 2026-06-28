# Architecture: Tool Mode System for Integrated VTK-Centric GUI

**Domain:** VTK interactor style switching, 3D widget integration, event routing
**Researched:** 2026-06-28

## Recommended Architecture

### Overview: ToolModeManager with Interactor Style Registry

The tool mode system centers on a `ToolModeManager` class that:
1. Owns pre-built interactor style objects (one per tool mode)
2. Owns VTK 3D widget objects (for tool modes that use them)
3. Switches the active style and widget state when the toolbar selection changes
4. Emits Qt signals for UI updates (cursor, status bar, dock panel, toolbar button)

```
┌─────────────────────────────────────────────────────┐
│                    MainWindow                        │
│                                                     │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Toolbar  │  │ VTK Viewport│  │ Context Dock  │  │
│  │ [tools]  │  │ (QVTKRWI)   │  │ (parameters)  │  │
│  └────┬─────┘  └──────┬───────┘  └───────┬───────┘  │
│       │               │                  │          │
│       └───────────────┼──────────────────┘          │
│                       │                              │
│              ┌────────▼────────┐                     │
│              │ ToolModeManager │                     │
│              │                 │                     │
│              │ _mode_registry  │                     │
│              │ _active_style   │                     │
│              │ _active_widgets │                     │
│              │ _pickers        │                     │
│              └────────┬────────┘                     │
│                       │                              │
│        ┌──────────────┼──────────────┐              │
│        │              │              │              │
│   ┌────▼───┐   ┌─────▼────┐   ┌────▼────┐        │
│   │Navigate│   │ Select   │   │ Measure  │  ...    │
│   │Style   │   │ Style    │   │ + Widget │        │
│   └────────┘   └──────────┘   └─────────┘         │
└─────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `ToolModeManager` | Mode registry, style switching, widget lifecycle, cursor | MainWindow, VTK viewport, toolbar, dock panel |
| `ToolMode` (dataclass) | Mode definition: name, style class, widget list, cursor, status hint | ToolModeManager |
| `CustomInteractorStyle*` | Per-mode event handling (Select, Place, Pick) | VTK interactor, ToolModeManager (via observers/signals) |
| VTK 3D Widgets | Measure (DistanceWidget), Region (ContourWidget), Box (BoxWidget2) | VTK interactor, ToolModeManager |
| Context Dock Panel | Tool-specific parameter controls | ToolModeManager (mode_changed signal), MainWindow |
| Status Bar | Tool-specific hint text | ToolModeManager (status_hint_changed signal) |

### Data Flow: Mode Switch

```
User clicks toolbar button "Select"
    │
    ▼
ToolModeManager.set_mode("select")
    │
    ├── Disable active widgets (if any)
    │       widget.SetEnabled(0)
    │
    ├── Switch interactor style
    │       iren.SetInteractorStyle(select_style)
    │
    ├── Update cursor
    │       vtk_widget.setCursor(Qt.CrossCursor)
    │
    ├── Update status bar
    │       status_bar.showMessage("Click an atom to select it")
    │
    ├── Show contextual dock panel
    │       dock_manager.show_panel("select_params")
    │
    └── Emit mode_changed signal
            → Toolbar updates checked state
            → Dock panel switches content
```

### Data Flow: Event Processing

```
Qt Mouse Event (mousePressEvent)
    │
    ▼
QVTKRenderWindowInteractor.mousePressEvent()
    │  Sets event info on _Iren (interactor)
    │  Calls _Iren.LeftButtonPressEvent()
    │
    ▼
vtkRenderWindowInteractor processes event
    │
    ├── Check: Any enabled widgets? 
    │       YES → Widget.ProcessEvents() → Widget handles event
    │       NO  → Pass to interactor style
    │
    ▼
vtkInteractorStyle.OnLeftButtonDown()
    │  (calls the active style's override)
    │
    ▼
CustomSelectStyle.OnLeftButtonDown()
    │  Uses picker to find atom/molecule
    │  Emits selection signal
    │
    ▼
ToolModeManager receives selection signal
    │  Updates UI (info panel, highlight)
```

## Detailed Design

### 1. ToolModeManager Class

```python
from enum import Enum, auto
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QCursor

class ToolMode(Enum):
    NAVIGATE = auto()
    SELECT = auto()
    DRAW_REGION = auto()
    PLACE_MOLECULE = auto()
    MEASURE = auto()
    PICK = auto()

class ToolModeManager(QObject):
    """Manages VTK interactor style switching and widget lifecycle
    for the integrated VTK-centric GUI's tool mode system."""
    
    mode_changed = Signal(ToolMode)
    status_hint_changed = Signal(str)
    selection_made = Signal(object)  # Picked prop/atom info
    
    def __init__(self, vtk_widget, renderer, parent=None):
        super().__init__(parent)
        self._vtk_widget = vtk_widget  # QVTKRenderWindowInteractor
        self._renderer = renderer
        self._iren = vtk_widget.GetRenderWindow().GetInteractor()
        self._current_mode = ToolMode.NAVIGATE
        
        # Build style registry (one instance per mode, created once)
        self._styles = {}
        self._widgets = {}  # mode -> list of vtkAbstractWidget
        self._pickers = {}  # mode -> vtkAbstractPicker
        
        self._build_mode_registry()
    
    def _build_mode_registry(self):
        """Pre-create all interactor styles and widgets."""
        # Navigate: standard trackball camera
        self._styles[ToolMode.NAVIGATE] = vtkInteractorStyleTrackballCamera()
        
        # Select: custom style with picking
        self._styles[ToolMode.SELECT] = SelectInteractorStyle()
        self._pickers[ToolMode.SELECT] = vtkPropPicker()
        
        # Place Molecule: custom style with cell picking on plane
        self._styles[ToolMode.PLACE_MOLECULE] = PlaceMoleculeInteractorStyle()
        self._pickers[ToolMode.PLACE_MOLECULE] = vtkCellPicker()
        
        # Measure: navigate style + DistanceWidget
        self._styles[ToolMode.MEASURE] = vtkInteractorStyleTrackballCamera()
        distance_widget = vtkDistanceWidget()
        distance_widget.SetInteractor(self._iren)
        rep = vtkDistanceRepresentation3D()
        distance_widget.SetRepresentation(rep)
        self._widgets[ToolMode.MEASURE] = [distance_widget]
        
        # Draw Region: ContourWidget on a bounded plane
        self._styles[ToolMode.DRAW_REGION] = vtkInteractorStyleTrackballCamera()
        contour_widget = vtkContourWidget()
        contour_widget.SetInteractor(self._iren)
        rep = vtkOrientedGlyphContourRepresentation()
        rep.SetPointPlacer(vtkBoundedPlanePointPlacer())
        contour_widget.SetRepresentation(rep)
        self._widgets[ToolMode.DRAW_REGION] = [contour_widget]
        
        # Pick: custom style with point picking + info display
        self._styles[ToolMode.PICK] = PickInteractorStyle()
        self._pickers[ToolMode.PICK] = vtkPointPicker()
    
    def set_mode(self, mode: ToolMode):
        """Switch to the specified tool mode."""
        if self._current_mode == mode:
            return
        
        # Step 1: Disable widgets from previous mode
        old_widgets = self._widgets.get(self._current_mode, [])
        for widget in old_widgets:
            widget.SetEnabled(0)
        
        # Step 2: Remove observers from previous custom style (if any)
        # (Custom styles clean up their own observers in deactivate())
        old_style = self._styles.get(self._current_mode)
        if hasattr(old_style, 'deactivate'):
            old_style.deactivate()
        
        # Step 3: Switch interactor style
        new_style = self._styles[mode]
        self._iren.SetInteractorStyle(new_style)
        
        # Step 4: Activate new style (set up observers, etc.)
        if hasattr(new_style, 'activate'):
            new_style.activate(self._iren, self._renderer)
        
        # Step 5: Enable widgets for new mode
        new_widgets = self._widgets.get(mode, [])
        for widget in new_widgets:
            widget.SetEnabled(1)
        
        # Step 6: Set picker if mode requires one
        picker = self._pickers.get(mode)
        if picker:
            self._iren.SetPicker(picker)
        
        # Step 7: Update cursor
        self._update_cursor(mode)
        
        # Step 8: Update status hint
        hints = {
            ToolMode.NAVIGATE: "Rotate: Left-drag | Pan: Middle-drag | Zoom: Right-drag or scroll",
            ToolMode.SELECT: "Click an atom or molecule to select it",
            ToolMode.DRAW_REGION: "Click to add region vertices | Double-click to close",
            ToolMode.PLACE_MOLECULE: "Click to place a molecule at the 3D position",
            ToolMode.MEASURE: "Click two points to measure distance",
            ToolMode.PICK: "Click an atom to display its properties",
        }
        self.status_hint_changed.emit(hints.get(mode, ""))
        
        # Step 9: Emit mode changed
        self._current_mode = mode
        self.mode_changed.emit(mode)
    
    def _update_cursor(self, mode: ToolMode):
        """Set the cursor based on the active tool mode."""
        cursor_map = {
            ToolMode.NAVIGATE: Qt.CursorShape.ArrowCursor,
            ToolMode.SELECT: Qt.CursorShape.CrossCursor,
            ToolMode.DRAW_REGION: Qt.CursorShape.CrossCursor,
            ToolMode.PLACE_MOLECULE: Qt.CursorShape.CrossCursor,
            ToolMode.MEASURE: Qt.CursorShape.CrossCursor,
            ToolMode.PICK: Qt.CursorShape.WhatsThisCursor,
        }
        cursor = cursor_map.get(mode, Qt.CursorShape.ArrowCursor)
        self._vtk_widget.setCursor(QCursor(cursor))
```

### 2. Custom Interactor Styles

#### SelectInteractorStyle

```python
class SelectInteractorStyle(vtkInteractorStyleTrackballCamera):
    """Custom interactor style for atom/molecule selection.
    
    Left-click: Pick the atom/molecule under cursor
    Middle-drag: Pan (preserved from TrackballCamera)
    Right-drag: Zoom (preserved from TrackballCamera)
    """
    
    def __init__(self):
        super().__init__()
        self._picker = None
        self._renderer = None
        self._observer_tags = []
    
    def activate(self, iren, renderer):
        """Set up observers when this style becomes active."""
        self._iren = iren
        self._renderer = renderer
        self._picker = iren.GetPicker()
        
        # Add observer for left button press
        tag = self.AddObserver(
            vtkCommand.LeftButtonPressEvent,
            self._on_left_button_down
        )
        self._observer_tags.append(tag)
        
        # Add observer for left button release  
        tag = self.AddObserver(
            vtkCommand.LeftButtonReleaseEvent,
            self._on_left_button_up
        )
        self._observer_tags.append(tag)
    
    def deactivate(self):
        """Remove observers when this style is deactivated."""
        for tag in self._observer_tags:
            self.RemoveObserver(tag)
        self._observer_tags.clear()
    
    def _on_left_button_down(self, obj, event):
        """Handle left click for selection."""
        # Get click position
        click_pos = self._iren.GetEventPosition()
        
        # Perform pick
        self._picker.Pick(click_pos[0], click_pos[1], 0, self._renderer)
        
        picked_actor = self._picker.GetActor()
        if picked_actor:
            # Emit selection via a callback or signal
            # (Bridge to Qt signal via ToolModeManager)
            self._on_picked(picked_actor)
        
        # Forward event to base class for camera manipulation
        # (IMPORTANT: Don't call base OnLeftButtonDown if we want
        #  click-only selection. But if we want drag-to-rotate
        #  when not clicking on an actor, we need conditional forwarding.)
        self.OnLeftButtonDown()
    
    def _on_picked(self, actor):
        """Handle a successful pick."""
        # Highlight the picked actor
        # (This is a callback — connect to ToolModeManager.selection_made)
        pass
```

#### PlaceMoleculeInteractorStyle

```python
class PlaceMoleculeInteractorStyle(vtkInteractorStyleTrackballCamera):
    """Custom interactor style for click-to-place molecule.
    
    Left-click: Place a molecule at the 3D position
    Middle-drag: Pan (preserved)
    Right-drag: Zoom (preserved)
    
    Uses vtkCellPicker to find the 3D world position under cursor.
    Falls back to vtkWorldPointPicker if no geometry is hit.
    """
    
    def __init__(self):
        super().__init__()
        self._cell_picker = vtkCellPicker()
        self._world_picker = vtkWorldPointPicker()
        self._placement_plane = None  # Optional: constrain to plane
        self._observer_tags = []
    
    def activate(self, iren, renderer):
        self._iren = iren
        self._renderer = renderer
        tag = self.AddObserver(
            vtkCommand.LeftButtonPressEvent,
            self._on_left_click
        )
        self._observer_tags.append(tag)
    
    def deactivate(self):
        for tag in self._observer_tags:
            self.RemoveObserver(tag)
        self._observer_tags.clear()
    
    def _on_left_click(self, obj, event):
        """Handle click for molecule placement."""
        click_pos = self._iren.GetEventPosition()
        
        # Try cell picker first (picks on existing geometry)
        self._cell_picker.Pick(click_pos[0], click_pos[1], 0, self._renderer)
        pick_pos = self._cell_picker.GetPickPosition()
        
        # If no geometry hit, use world point picker
        if self._cell_picker.GetCellId() < 0:
            self._world_picker.Pick(click_pos[0], click_pos[1], 0, self._renderer)
            pick_pos = self._world_picker.GetPickPosition()
        
        # If a placement plane is set, project onto the plane
        if self._placement_plane is not None:
            pick_pos = self._project_to_plane(pick_pos, self._placement_plane)
        
        # Place molecule at pick_pos
        # (Emit signal via ToolModeManager)
        pass
    
    def _project_to_plane(self, point, plane):
        """Project a 3D point onto the placement plane.
        
        Args:
            point: (x, y, z) world coordinates
            plane: vtkPlane with origin and normal
        Returns:
            Projected (x, y, z) on the plane
        """
        return plane.ProjectPoint(point)
```

### 3. Widget Lifecycle Management

VTK 3D widgets follow a strict lifecycle:

```python
# Creation (once, during ToolModeManager.__init__)
widget = vtkDistanceWidget()
widget.SetInteractor(iren)         # Register with interactor
rep = vtkDistanceRepresentation3D()
widget.SetRepresentation(rep)      # Set visual representation

# Activation (when mode is entered)
widget.SetEnabled(1)               # Widget starts processing events
widget.SetProcessEvents(1)         # Enable event processing

# Deactivation (when mode is left)
widget.SetEnabled(0)               # Widget stops processing events
# Widget retains its state (e.g., measure line stays visible if we want)

# Destruction (rarely needed — widgets persist for the app lifetime)
widget.SetEnabled(0)
# Python GC handles cleanup when ToolModeManager is destroyed
```

**Key rules:**
1. **One `SetInteractor()` call per widget lifetime** — don't re-register
2. **Enable/Disable toggles event processing** — the widget persists
3. **Widget state persists across mode switches** — measure lines, contour nodes stay
4. **Only ONE widget should be enabled per mode** — multiple enabled widgets cause event conflicts
5. **Disable before switching styles** — enabled widgets intercept events meant for the new style

### 4. Qt-VTK Event Bridge

The event flow from Qt to VTK (verified from `QVTKRenderWindowInteractor.py` source):

```
Qt mousePressEvent(ev)
    │
    ├── Get position: x, y = ev.position().x(), ev.position().y()
    ├── Get modifiers: ctrl, shift = ev.modifiers()
    ├── Set event info on VTK interactor:
    │       self._Iren.SetEventInformation(x, y, ctrl, shift, ...)
    │
    └── Forward to VTK:
            if LeftButton:  self._Iren.LeftButtonPressEvent()
            if RightButton: self._Iren.RightButtonPressEvent()
            if MiddleButton: self._Iren.MiddleButtonPressEvent()

VTK interactor processes:
    │
    ├── Forward to active interactor style
    │       style.OnLeftButtonDown()  (virtual method)
    │
    └── Style-specific handling:
            TrackballCamera: Start rotation
            SelectStyle:     Perform pick
            CustomStyle:     Override OnLeftButtonDown()
```

**Important:** Qt events are fully consumed by the `QVTKRenderWindowInteractor`. There is no Qt event propagation back to parent widgets. To intercept events at the Qt level, use `installEventFilter()` on the VTK widget.

### 5. Picker Selection Strategy

| Tool Mode | Picker | Why |
|-----------|--------|-----|
| Select | `vtkPropPicker` | Picks entire actors (molecules), fast, no cell-level detail needed |
| Pick | `vtkPointPicker` | Picks individual points for atom property display |
| Place Molecule | `vtkCellPicker` + fallback `vtkWorldPointPicker` | Cell picker finds geometry; world picker gives arbitrary 3D position |
| Draw Region | `vtkBoundedPlanePointPlacer` | Constrains placement to a plane (not a traditional picker) |
| Measure | (handled by vtkDistanceWidget internally) | Widget manages its own picking |

### 6. Shared QUndoStack

A single `QUndoStack` on MainWindow serves all modes:

```python
class MainWindow(QMainWindow):
    def __init__(self):
        ...
        self._undo_stack = QUndoStack(self)
        self._undo_action = self._undo_stack.createUndoAction(self, "&Undo")
        self._redo_action = self._undo_stack.createRedoAction(self, "&Redo")
```

Undo commands are mode-specific:
- `PlaceMoleculeCommand` — undo molecule placement
- `DrawRegionCommand` — undo region vertex addition
- `SelectCommand` — undo selection (toggle highlight)

The stack is shared because some actions span modes (e.g., place molecule, then navigate to check, then undo the placement).

## Anti-Patterns to Avoid

### Anti-Pattern 1: God-Class Interactor Style
**What:** One `vtkInteractorStyle` subclass that checks a `self._mode` enum in every `OnXxx()` method.
**Why bad:** Violates SRP, hard to test individual modes, brittle state management, grows with every new mode.
**Instead:** One style class per mode, switched via `SetInteractorStyle()`.

### Anti-Pattern 2: Creating/Destroying Styles on Every Switch
**What:** `style = vtkInteractorStyleTrackballCamera(); iren.SetInteractorStyle(style)` every time.
**Why bad:** Object creation overhead, potential memory leaks if references aren't managed, observer setup repeated.
**Instead:** Pre-create all styles in `_build_mode_registry()`, switch references.

### Anti-Pattern 3: Leaving Widgets Enabled Across Modes
**What:** Forgetting `widget.SetEnabled(0)` when switching away from Measure mode.
**Why bad:** Enabled widget intercepts events meant for the new mode, causing bizarre behavior.
**Instead:** Always disable widgets in `set_mode()` before switching styles.

### Anti-Pattern 4: Observers on the Interactor (Not the Style)
**What:** `iren.AddObserver(vtkCommand.LeftButtonPressEvent, callback)` for mode-specific behavior.
**Why bad:** Interactor observers fire regardless of the active style, making mode switching impossible.
**Instead:** Add observers on the interactor *style* (or use custom style overrides).

## Scalability Considerations

| Concern | At 2 modes | At 6 modes | At 10+ modes |
|---------|-----------|------------|-------------|
| Style registry | Simple dict | Dict with ToolMode enum keys | May need lazy initialization |
| Widget count | 0-2 | 3-5 | 8+ — needs widget pool |
| Observer cleanup | Manual per-style | activate/deactivate pattern | Observer mediator class |
| Mode transition logic | Simple if/else | ToolModeManager handles | May need QStateMachine for complex transitions |
| Memory | ~2 MB VTK objects | ~5 MB | Consider destroying unused styles |

## VTK 9.5.2 Available Interactor Styles (Catalog)

| Style | VTK Class | QuickIce Use | Behavior |
|-------|-----------|--------------|----------|
| Trackball Camera | `vtkInteractorStyleTrackballCamera` | **Navigate mode** (default) | Left-drag=rotate, Middle-drag=pan, Right-drag=zoom |
| Trackball Actor | `vtkInteractorStyleTrackballActor` | Not needed | Left-drag=rotate actor, Middle=pan actor, Right=scale actor |
| Joystick Camera | `vtkInteractorStyleJoystickCamera` | Not needed | Position-sensitive rotation (continuous while held) |
| Joystick Actor | `vtkInteractorStyleJoystickActor` | Not needed | Position-sensitive actor manipulation |
| Image | `vtkInteractorStyleImage` | Not needed | 2D image slice viewing (window/level) |
| Rubber Band 2D | `vtkInteractorStyleRubberBand2D` | Not needed | 2D rectangle selection on image |
| Rubber Band 3D | `vtkInteractorStyleRubberBand3D` | **Possible region select** | Draws 3D rectangle; inherits TrackballCamera |
| Rubber Band Pick | `vtkInteractorStyleRubberBandPick` | **Possible region select** | Draws rectangle, then picks actors inside |
| Rubber Band Zoom | `vtkInteractorStyleRubberBandZoom` | Not needed | Zooms to rectangle selection |
| Draw Polygon | `vtkInteractorStyleDrawPolygon` | **Possible region draw** | Draws freeform polygon on screen |
| Terrain | `vtkInteractorStyleTerrain` | Not needed | Globe/terrain rotation |
| Unicam | `vtkInteractorStyleUnicam` | Not needed | 1-button camera control with click-to-pick |
| Flight | `vtkInteractorStyleFlight` | Not needed | Fly-through camera control |
| User | `vtkInteractorStyleUser` | **Base for custom styles** | Empty style — all On* methods are no-ops |
| Switch | `vtkInteractorStyleSwitch` | Reference only | Switches between joystick/trackball via keypress |
| Multi-Touch | `vtkInteractorStyleMultiTouchCamera` | Not needed | Touch gesture camera control |
| Area Select Hover | `vtkInteractorStyleAreaSelectHover` | Not needed | Tree-map specific hover highlighting |

## VTK 9.5.2 Available 3D Widgets (Catalog)

| Widget | VTK Class | QuickIce Use | Notes |
|--------|-----------|--------------|-------|
| Distance | `vtkDistanceWidget` | **Measure mode** | Two-point distance with 3D label |
| Seed | `vtkSeedWidget` | **Place Molecule mode (alternative)** | Multiple handle placement |
| Contour | `vtkContourWidget` | **Draw Region mode** | Polygon/polyline drawing with node editing |
| Box 2 | `vtkBoxWidget2` | **Future: cell editing** | 3D box with move/rotate/scale handles |
| Implicit Plane 2 | `vtkImplicitPlaneWidget2` | **Future: plane selection** | Movable plane with normal arrow |
| Sphere 2 | `vtkSphereWidget2` | Not needed | Spherical handle widget |
| Line 2 | `vtkLineWidget2` | Not needed | Simple line between two points |
| Spline 2 | `vtkSplineWidget2` | Not needed | Smooth curve through control points |
| Handle | `vtkHandleWidget` | **Part of ContourWidget** | Individual draggable handle point |
| Angle | `vtkAngleWidget` | Not needed | Three-point angle measurement |
| Bi-Dimensional | `vtkBiDimensionalWidget` | Not needed | Two connected distance measurements |
| Border | `vtkBorderWidget` | Not needed | 2D border/rectangle selection |
| Caption | `vtkCaptionWidget` | Not needed | Draggable text caption |
| Camera Orientation | `vtkCameraOrientationWidget` | **Future: navigation aid** | On-screen orientation cube |
| Finite Plane | `vtkFinitePlaneWidget` | **Possible region draw** | Finite plane with handles |
| Image Tracer | `vtkImageTracerWidget` | Not needed | Traces path on image data |
| Logo | `vtkLogoWidget` | Not needed | Overlay logo placement |
| Scalar Bar | `vtkScalarBarWidget` | **Future: color legend** | Draggable scalar bar |

## Sources

- VTK 9.5.2 Python API: verified via live testing (`python -c "import vtkmodules.all as vtk; ..."`)
- QVTKRenderWindowInteractor.py: `/share/home/nglokwan/miniconda3/envs/quickice/lib/python3.14/site-packages/vtkmodules/qt/QVTKRenderWindowInteractor.py` (read in full, 803 lines)
- VTK Class Reference: `https://vtk.org/doc/nightly/html/classvtkInteractorStyle.html` (accessed 2026-06-28)
- VTK Class Reference: `https://vtk.org/doc/nightly/html/classvtkInteractorStyleTrackballCamera.html` (accessed 2026-06-28)
- QuickIce existing code: `quickice/gui/molecular_viewer.py`, `quickice/gui/dual_viewer.py`, `quickice/gui/interface_viewer.py`, `quickice/gui/hydrate_viewer.py`, `quickice/gui/vtk_utils.py` (all read)
