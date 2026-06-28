# Architecture: Dock Panel System

**Domain:** QDockWidget-based panel organization for VTK-centric GUI
**Researched:** 2025-06-28
**Confidence:** HIGH (verified via live PySide6 6.10.2 testing)

## Recommended Architecture: Hybrid Contextual-Switching Model

```
+----------------------------------------------------------+
|  Menu Bar: File  Edit  View  Tools  Help                 |
+----------------------------------------------------------+
|  Toolbar: [Ice] [Hydrate] [Interface] [Solute] [Ion]    |
+----------+-------------------------------+---------------+
|          |                               |               |
| PARAMS   |                               |   RESULTS     |
| (tabified|      VTK VIEWPORT            |   dock        |
|  left    |      (central widget)         |               |
|  dock)   |      QVTKRenderWindowInter..  |  - Structure  |
|          |                               |    info       |
| Active:  |      Single 3D scene         |  - Density    |
| Ice Params|     showing current           |  - Atom count |
|          |     structure + overlays      |  - Energies   |
|----------+                               |               |
|          |                               +---------------+
| (tab     |                               |
|  stack:  |                               +---------------+
|  Hydrate |                               |   LOG         |
|  Interf. |                               |   dock        |
|  Solute  |                               |               |
|  Ion     |                               |  Status msgs  |
|  Custom) |                               |  Progress bar |
|          |                               +---------------+
+----------+-------------------------------+---------------+
```

### Floating: Phase Diagram Dock

```
+------------------+
| Phase Diagram    |
| (floating or     |
|  docked right)   |
|                  |
| [matplotlib      |
|  canvas with     |
|  shapely poly    |
|  interaction]    |
|                  |
| Click → sets T,P |
+------------------+
```

## Component Boundaries

| Component | Type | Responsibility | Communicates With |
|-----------|------|----------------|-------------------|
| VTK Viewport | Central Widget | Single 3D rendering of current structure | Toolbar, Results dock |
| Params Dock | QDockWidget (Left, tabified) | Contextual parameter panel for active tool | Toolbar (tool selection), MainWindow |
| Results Dock | QDockWidget (Right) | Structure info, density, atom count, energies | MainWindow (result data) |
| Log Dock | QDockWidget (Bottom) | Status messages, progress bar, generation log | All workers |
| Phase Diagram Dock | QDockWidget (Floatable/Right) | Interactive T-P diagram with click selection | Params dock (Ice), MainWindow |
| Toolbar | QToolBar (Top) | Tool selection buttons, generate/apply actions | Params dock (context switch) |

## Dock → Panel Mapping

### Current Tabs → Dock Assignments

| Current Tab | Content | Dock Assignment | Strategy |
|-------------|---------|-----------------|----------|
| Tab 0 (Ice) | InputPanel + ProgressPanel + PhaseDiagramPanel + ViewerPanel + buttons | Params dock (tab: Ice) + Phase Diagram dock (separate) | Split: params go to left dock tab, phase diagram becomes its own dock |
| Tab 1 (Hydrate) | HydratePanel (lattice, guest, occupancy, supercell) + HydrateViewer | Params dock (tab: Hydrate) | Parameters to left dock tab, viewer → central VTK |
| Tab 2 (Interface) | InterfacePanel (candidate, mode, box params) + InterfaceViewer | Params dock (tab: Interface) | Parameters to left dock tab, viewer → central VTK |
| Tab 3 (Custom) | CustomMoleculePanel (upload, position) + CustomMoleculeViewer | Params dock (tab: Custom) | Parameters to left dock tab, viewer → central VTK |
| Tab 4 (Solute) | SolutePanel (type, concentration) + SoluteViewer | Params dock (tab: Solute) | Parameters to left dock tab, viewer → central VTK |
| Tab 5 (Ion) | IonPanel (Na+/Cl- conc) + IonViewer | Params dock (tab: Ion) | Parameters to left dock tab, viewer → central VTK |

### Consolidated: 5 Panels in 4 Dock Positions

| Dock Position | ObjectName | Content | Initial Visibility |
|---------------|-----------|---------|--------------------|
| Left (tabified) | `dockParamsIce` | IceInputPanel: T, P, nmolecules, Generate button | Visible (default tool) |
| Left (tabified) | `dockParamsHydrate` | HydratePanel params section | Hidden |
| Left (tabified) | `dockParamsInterface` | InterfacePanel params section | Hidden |
| Left (tabified) | `dockParamsModifiers` | QStackedWidget: SolutePanel OR IonPanel OR CustomMoleculePanel | Hidden |
| Right | `dockResults` | Structure info, density, ranked candidates | Visible |
| Bottom | `dockLog` | Log text + progress bar + status | Visible |
| Floatable | `dockPhaseDiagram` | PhaseDiagramPanel (matplotlib) | Visible (floating by default) |

**Why merge Solute/Ion/Custom into "Modifiers" tab?** These three panels are always applied *after* the base structure (Ice/Hydrate/Interface) and are logically "modifier" steps. They share the same workflow pattern: select source → set concentration → insert. Tabifying them saves left-dock space while preserving all controls.

### Alternative Considered: 1:1 Mapping (6 Left-Dock Tabs)

Rejected because:
- 6 tabified docks create crowded tab bar on left dock
- Tab bar text becomes unreadable at narrow widths
- Solute/Ion/Custom are logically grouped as "modifiers"
- Better to have 4 meaningful tabs than 6 tiny ones

### Alternative Considered: Single Params Dock with QStackedWidget

Rejected because:
- `saveState()` cannot save/restore QStackedWidget index
- QStackedWidget hides widget state from Qt's layout system
- Tabified docks preserve individual panel visibility in state serialization
- Users can see all available tools in the tab bar (discoverable)

## Contextual Panel Switching

### Mechanism: Tabified Docks with raise_()

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ... setup central VTK widget ...
        
        # Create parameter docks
        self.dock_params_ice = QDockWidget("Ice Parameters", self)
        self.dock_params_ice.setObjectName("dockParamsIce")
        self.dock_params_ice.setWidget(IceInputPanel())
        
        self.dock_params_hydrate = QDockWidget("Hydrate Parameters", self)
        self.dock_params_hydrate.setObjectName("dockParamsHydrate")
        self.dock_params_hydrate.setWidget(HydrateParamsPanel())
        
        # ... more docks ...
        
        # Add all to left area
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_params_ice)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_params_hydrate)
        
        # Tabify: all param docks share the same left-dock space
        self.tabifyDockWidget(self.dock_params_ice, self.dock_params_hydrate)
        self.tabifyDockWidget(self.dock_params_ice, self.dock_params_interface)
        self.tabifyDockWidget(self.dock_params_ice, self.dock_params_modifiers)
        
        # Set Ice as default visible tab
        self.dock_params_ice.raise_()
    
    def _on_tool_selected(self, tool_name: str):
        """Toolbar button clicked → switch parameter panel."""
        tool_to_dock = {
            "ice": self.dock_params_ice,
            "hydrate": self.dock_params_hydrate,
            "interface": self.dock_params_interface,
            "modifiers": self.dock_params_modifiers,
        }
        target_dock = tool_to_dock.get(tool_name)
        if target_dock:
            target_dock.raise_()  # Brings this tab to front in tabified stack
```

### Why `raise_()` instead of show/hide?

**Tested finding:** In tabified docks, `raise_()` is the correct way to switch the visible tab. `show()`/`hide()` on a tabified dock does NOT reliably change which tab is displayed — it may show/hide the entire tab group. `raise_()` activates the tab within the group.

However, in offscreen/CI environments (`QT_QPA_PLATFORM=offscreen`), `raise_()` does not work (confirmed by testing — "This plugin does not support raise()"). For testing, the `tabifiedDockWidgetActivated` signal can be monitored, or `setCurrentIndex()` on the internal QTabBar can be used as a workaround.

### Why not destroy/recreate panels on switch?

- Panels hold user state (input values, configuration, validation state)
- Destroying and recreating loses all unsaved state
- Memory cost of keeping panels alive is negligible (~100KB per panel)
- `hide()` preserves widget state; `deleteLater()` destroys it

**Decision:** Keep all panels alive. Switch with `raise_()`.

## State Serialization

### Dock Layout State (saveState/restoreState)

```python
class MainWindow(QMainWindow):
    LAYOUT_STATE_VERSION = 2  # Increment when dock structure changes
    
    def closeEvent(self, event):
        """Save layout on close."""
        settings = QSettings("QuickIce", "QuickIceGUI")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState(self.LAYOUT_STATE_VERSION))
        super().closeEvent(event)
    
    def _restore_layout(self):
        """Restore layout on startup."""
        settings = QSettings("QuickIce", "QuickIceGUI")
        geometry = settings.value("geometry")
        state = settings.value("windowState")
        if geometry:
            self.restoreGeometry(geometry)
        if state:
            self.restoreState(state, self.LAYOUT_STATE_VERSION)
```

### Requirements for saveState (verified by testing)

1. **Every QDockWidget must have a unique `objectName`** — otherwise `saveState()` prints warnings and the dock's position is NOT saved. This is the #1 pitfall.

2. **Version number must match exactly** — `restoreState(state, wrong_version)` returns `False` and does nothing. Increment version only when dock structure changes (adding/removing docks).

3. **State is a QByteArray** — binary format, not human-readable. Size is typically 200-400 bytes for 4-7 docks. Cannot be hand-edited.

4. **State saves:** dock positions, sizes (relative), visibility, tab order, floating state. Does NOT save per-panel content (input field values, etc.).

5. **Call `restoreState()` AFTER all docks are added** — docks created after restoreState will need `restoreDockWidget()` called individually.

### Per-Panel Content State (QSettings)

```python
class IceInputPanel(QWidget):
    def save_state(self, settings: QSettings):
        """Save input field values."""
        settings.beginGroup("IceInputPanel")
        settings.setValue("temperature", self.temp_input.text())
        settings.setValue("pressure", self.pressure_input.text())
        settings.setValue("nmolecules", self.nmol_input.text())
        settings.endGroup()
    
    def restore_state(self, settings: QSettings):
        """Restore input field values."""
        settings.beginGroup("IceInputPanel")
        self.temp_input.setText(settings.value("temperature", ""))
        self.pressure_input.setText(settings.value("pressure", ""))
        self.nmol_input.setText(settings.value("nmolecules", ""))
        settings.endGroup()
```

### State Serialization Architecture

| State Type | Mechanism | Scope | When |
|-----------|-----------|-------|------|
| Dock layout | `saveState()`/`restoreState()` | Window close/start | Automatic |
| Window geometry | `saveGeometry()`/`restoreGeometry()` | Window close/start | Automatic |
| Panel content | QSettings per-panel | App close/start | Panel.save_state/restore_state |
| Tool selection | QSettings | App close/start | MainWindow saves active tool name |

## Menu Integration

### View Menu for Dock Visibility

Every QDockWidget provides a `toggleViewAction()` — a checkable QAction that shows/hides the dock. This should be added to the View menu:

```python
def _create_menu_bar(self):
    menubar = self.menuBar()
    
    # View menu — dock visibility toggles
    view_menu = menubar.addMenu("View")
    view_menu.addAction(self.dock_params_ice.toggleViewAction())
    view_menu.addAction(self.dock_params_hydrate.toggleViewAction())
    view_menu.addAction(self.dock_params_interface.toggleViewAction())
    view_menu.addAction(self.dock_params_modifiers.toggleViewAction())
    view_menu.addSeparator()
    view_menu.addAction(self.dock_results.toggleViewAction())
    view_menu.addAction(self.dock_log.toggleViewAction())
    view_menu.addAction(self.dock_phase_diagram.toggleViewAction())
    view_menu.addSeparator()
    
    # Reset layout action
    reset_layout_action = view_menu.addAction("Reset Layout")
    reset_layout_action.triggered.connect(self._reset_layout)
```

### Important: toggleViewAction Behavior

**Tested finding:** `toggleViewAction` is checkable and its text is the dock's window title. When a user unchecks it, the dock hides. When checked, the dock shows. However, in the offscreen plugin, setting `setChecked(True)` does NOT reliably show the dock — use `dock.show()`/`dock.hide()` for programmatic control, and `toggleViewAction` only for menu items.

### createPopupMenu Override

QMainWindow provides `createPopupMenu()` which returns a context menu with all dock/toolbar toggle actions. This appears on right-click in the dock area. The default implementation is usually sufficient. Can be overridden to customize:

```python
def createPopupMenu(self):
    """Custom context menu for dock area."""
    menu = super().createPopupMenu()  # Default: all dock + toolbar toggle actions
    # Could filter out certain items here
    return menu
```

## Dock Options Configuration

### Recommended Settings

```python
self.setDockOptions(
    QMainWindow.DockOption.AnimatedDocks |      # Smooth resize animations
    QMainWindow.DockOption.AllowNestedDocks |    # Enable splitting within areas
    QMainWindow.DockOption.AllowTabbedDocks      # Enable tabification (required!)
)
```

### Why each option:

- **AnimatedDocks**: Smooth visual feedback when dragging/resizing docks. Negligible performance cost.
- **AllowNestedDocks**: Allows users to split dock areas (e.g., put Log dock in the left area if desired). Gives power users flexibility.
- **AllowTabbedDocks**: Required for `tabifyDockWidget()` to work. Without this, docks cannot be stacked.

### Options NOT recommended:

- **ForceTabbedDocks**: Too restrictive — prevents side-by-side docking. Makes AllowNestedDocks useless.
- **VerticalTabs**: Tab labels on left side. Looks unusual for left dock area (double vertical bars). Can reconsider if tab labels are too long.
- **GroupedDragging**: Dragging one tab drags all tabs in the group. Can cause confusion. Enable later if users request it.

## Corner Configuration

By default, Qt assigns corners to dock areas. For QuickIce:

```python
# Top-left corner → Left dock area (params take priority)
self.setCorner(Qt.Corner.TopLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
# Bottom-left corner → Left dock area  
self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
# Top-right corner → Right dock area (results)
self.setCorner(Qt.Corner.TopRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
# Bottom-right corner → Bottom dock area (log)
self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.BottomDockWidgetArea)
```

This ensures:
- Left dock extends full height when right dock is absent
- Log dock extends full width at bottom when both side docks are narrow

## Phase Diagram as Dockable Panel

### Current State (778 lines in phase_diagram_widget.py)

The PhaseDiagramPanel is a QWidget containing:
- `PhaseDiagramCanvas` (matplotlib `FigureCanvasQTAgg` with shapely polygon interaction)
- `QLabel` for phase info display
- Signals: `coordinates_selected(T, P)`, `phase_info_ready(phase_id, T, P)`

### Migration Strategy

1. **Wrap in QDockWidget** — minimal change:
   ```python
   self.dock_phase_diagram = QDockWidget("Phase Diagram", self)
   self.dock_phase_diagram.setObjectName("dockPhaseDiagram")
   self.dock_phase_diagram.setWidget(self.diagram_panel)
   self.dock_phase_diagram.setAllowedAreas(
       Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
   )
   self.dock_phase_diagram.setFeatures(
       QDockWidget.DockWidgetFeature.DockWidgetClosable |
       QDockWidget.DockWidgetFeature.DockWidgetMovable |
       QDockWidget.DockWidgetFeature.DockWidgetFloatable
   )
   # Start as floating (not docked) for maximum viewport space
   self.dock_phase_diagram.setFloating(True)
   ```

2. **Floating by default** — Phase diagram is a reference panel, not primary interaction. Floating lets users position it freely (over the VTK viewport or on a second monitor).

3. **Connection to Ice params** — When user clicks phase diagram, `coordinates_selected` signal still updates Ice parameter inputs. No change to signal flow.

4. **Future: VTK-based rendering** — Replace matplotlib canvas with VTK 2D actor rendering. Benefits: unified rendering pipeline, avoids matplotlib dependency in GUI, smoother interaction. This is a separate milestone (LOW confidence — needs feasibility study).

### Phase Diagram Dock Features

| Feature | Implementation | Notes |
|---------|---------------|-------|
| Floating by default | `setFloating(True)` after `addDockWidget()` | Can be re-docked by user |
| Dockable left/right | `setAllowedAreas(Left | Right)` | Prevents top/bottom (waste of space) |
| Closeable | `DockWidgetClosable` feature | User can dismiss; View menu to restore |
| Resizable | Default QDockWidget behavior | matplotlib canvas handles resize via FigureCanvasQTAgg |
| Persistent state | `saveState()` tracks position/size/float | Plus QSettings for diagram view state (zoom, marker) |

## VTK Viewport Integration

### Central Widget: Single VTK Render Window

```python
# Replace QTabWidget with VTK viewport
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

self.vtk_widget = QVTKRenderWindowInteractor(self)
self.setCentralWidget(self.vtk_widget)

renderer = vtkRenderer()
renderer.SetBackground(0.1, 0.1, 0.2)  # Dark background
self.vtk_widget.GetRenderWindow().AddRenderer(renderer)
```

### Resize Behavior

**Key finding (from API analysis + Qt docs):** When a dock is resized or shown/hidden, Qt's layout engine automatically adjusts the central widget size. The VTK render window responds to Qt resize events via `QVTKRenderWindowInteractor.resizeEvent()`. No special handling is needed beyond:

```python
# VTK auto-renders on resize via QVTKRenderWindowInteractor
# If flickering is observed, can defer render:
self.vtk_widget.GetRenderWindow().SetDesiredUpdateRate(30.0)  # 30 FPS target
```

### VTK + Dock Resize Gotcha

**Tested finding:** VTK segfaults in headless environments (`QT_QPA_PLATFORM=offscreen`). This is a known limitation per AGENTS.md. For VTK+Dock testing:
- Use `QUICKICE_FORCE_VTK=true` for forced testing
- Otherwise, mock/skip VTK-dependent tests
- In real display environments, VTK handles dock-driven resize correctly

### Structure Rendering Pipeline

Currently, each tab has its own viewer (Ice has DualViewer, Interface has InterfaceViewer, etc.). In the dock model, ALL structures render in the single central VTK viewport. The architecture needs a **VTK scene manager**:

```python
class VTKSceneManager:
    """Manages actors in the central VTK viewport."""
    
    def __init__(self, renderer: vtkRenderer):
        self.renderer = renderer
        self._actors: dict[str, vtkActor] = {}
    
    def clear_all(self):
        """Remove all actors from renderer."""
        self.renderer.RemoveAllViewProps()
        self._actors.clear()
    
    def show_ice_structure(self, candidate):
        """Replace current scene with ice structure."""
        self.clear_all()
        actor = candidate_to_vtk_molecule(candidate)
        self.renderer.AddActor(actor)
        self._actors["ice"] = actor
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()
    
    def show_interface_structure(self, result):
        """Replace scene with interface (ice + water)."""
        self.clear_all()
        # Add ice actors, water actors, bond actors
        # ...
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()
    
    def add_overlay(self, name: str, actor: vtkActor):
        """Add overlay actor (ions, solutes) without clearing base."""
        if name in self._actors:
            self.renderer.RemoveActor(self._actors[name])
        self.renderer.AddActor(actor)
        self._actors[name] = actor
        self.vtk_widget.GetRenderWindow().Render()
```

This replaces the current pattern of 6 separate viewers with a unified scene.

## Panel Lifecycle

### Creation Order (in MainWindow.__init__)

```
1. Central VTK widget → setCentralWidget()
2. Left dock: Params Ice → addDockWidget(Left)
3. Left dock: Params Hydrate → addDockWidget(Left), tabify
4. Left dock: Params Interface → addDockWidget(Left), tabify
5. Left dock: Params Modifiers → addDockWidget(Left), tabify
6. Right dock: Results → addDockWidget(Right)
7. Bottom dock: Log → addDockWidget(Bottom)
8. Phase Diagram dock → addDockWidget(Right), setFloating(True)
9. Toolbar → addToolBar(Top)
10. Menu bar → toggleViewAction for each dock
11. restoreState() → apply saved layout
```

### Dock Feature Configuration

| Dock | Closable | Movable | Floatable | Allowed Areas |
|------|----------|---------|-----------|---------------|
| Params (all 4 tabs) | No | No | No | Left only |
| Results | Yes | Yes | Yes | Left or Right |
| Log | Yes | Yes | Yes | Bottom or Left or Right |
| Phase Diagram | Yes | Yes | Yes | Left or Right |

**Why Params dock is not closable/floatable/movable:**
- Closable: Users should always see parameters for the active tool
- Floatable: Floating params dock disconnects from tab group, breaking tool switching
- Movable: Moving to right/bottom creates confusion with the results/log docks
- Restricting these features reduces user error while keeping utility docks flexible

## Data Flow Changes

### Current (Tab-Based)

```
Tab 0 (Ice) → result stored as _current_result
Tab 1 (Hydrate) → result stored as _current_hydrate_result
Tab 2 (Interface) → reads _current_result / _current_hydrate_result → produces _current_interface_result
Tab 4 (Solute) → reads _current_interface_result → produces _current_solute_result
Tab 5 (Ion) → reads _current_interface_result / _current_solute_result → produces _current_ion_result
```

### New (Dock-Based) — Same Data Flow, Different Navigation

```
Toolbar: [Ice] → Params Ice dock shown → Generate → result → VTK viewport shows ice
Toolbar: [Interface] → Params Interface dock shown → reads ice result → Generate → VTK shows interface
Toolbar: [Solute] → Params Modifiers dock (solute tab) → reads interface result → Insert → VTK adds solute overlay
Toolbar: [Ion] → Params Modifiers dock (ion tab) → reads interface/solute result → Insert → VTK adds ion overlay
```

**Key insight:** The data flow doesn't change — only the navigation changes. MainWindow still stores results as `_current_*_result` attributes. The difference is that panels are always "alive" (not hidden in a different tab), so cross-panel data availability is simpler.

### Progress/Status Feedback

Currently, progress panels are per-tab. In dock model:
- **Log dock** is the single progress/status display (shared across all tools)
- **Results dock** shows structure-specific info
- Progress bar moves to Log dock (or can be in the toolbar)
- Each panel's generate button triggers worker, which sends progress to Log dock

## Migration Strategy: Incremental

### Step 1: Dock Skeleton (non-breaking)

```python
# Keep QTabWidget temporarily, add empty docks alongside
self.tab_widget = QTabWidget()  # Still exists
self.setCentralWidget(self.tab_widget)

# Add docks but they're initially empty/hidden
self.dock_log = QDockWidget("Log", self)
self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_log)
```

This is wrong — can't have both QTabWidget as central and docks around it. Actually, we can — QTabWidget IS the central widget, and docks go around it. But the goal is to remove QTabWidget.

### Step 1 (Revised): Replace Central Widget

```python
# Remove: self.tab_widget = QTabWidget(); self.setCentralWidget(self.tab_widget)
# Replace with:
self.vtk_widget = QVTKRenderWindowInteractor(self)
self.setCentralWidget(self.vtk_widget)

# All tab content → docks
self.dock_params_ice = QDockWidget("Ice Parameters", self)
self.dock_params_ice.setWidget(ice_params_content)
# ... etc
```

This is a **breaking change** — the entire UI changes in one step. There's no incremental path from QTabWidget central to VTK central. The migration must be done in one coordinated step.

### Recommended: Feature Flag

```python
# environment.yml or config
QUICKICE_USE_DOCKS=1  # Set to enable dock layout; unset for tab layout

# In MainWindow.__init__
if os.environ.get('QUICKICE_USE_DOCKS'):
    self._setup_dock_ui()
else:
    self._setup_tab_ui()  # Existing code
```

This allows parallel development and A/B testing without breaking the existing UI.
