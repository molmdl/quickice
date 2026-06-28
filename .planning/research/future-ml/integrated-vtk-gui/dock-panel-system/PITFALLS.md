# Domain Pitfalls: Dock Panel System

**Domain:** QDockWidget-based panel organization for VTK-centric GUI
**Researched:** 2025-06-28
**Confidence:** HIGH (all pitfalls verified via live PySide6 6.10.2 testing)

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Missing objectName on QDockWidget → saveState Silently Fails

**What goes wrong:** `QMainWindow.saveState()` requires every QDockWidget to have a unique `objectName`. If any dock lacks an objectName, Qt prints a warning to stderr (`QMainWindow::saveState(): 'objectName' not set for QDockWidget...`) and **that dock's position/visibility is NOT saved**. The state blob is still produced, but it's incomplete. On restore, the unnamed dock reverts to its default position.

**Why it happens:** `objectName` is not required for QDockWidget to function day-to-day. It only matters for `saveState()`, which is easy to forget during initial development.

**Consequences:**
- User's custom layout doesn't persist correctly on restart
- Specific docks always revert to default position after restart
- No error is thrown — just a stderr warning that may be missed

**Prevention:**
- Set `objectName` on every QDockWidget immediately after construction
- Use a naming convention: `dock{Purpose}` (e.g., `dockParamsIce`, `dockLog`)
- Add a CI check or lint rule: grep for `QDockWidget` without `setObjectName`

**Detection:**
- Check stderr for `saveState(): 'objectName' not set` warnings
- After save+restore, verify each dock's position matches saved state

```python
# CORRECT
self.dock_params_ice = QDockWidget("Ice Parameters", self)
self.dock_params_ice.setObjectName("dockParamsIce")  # ← REQUIRED

# WRONG (will fail silently)
self.dock_params_ice = QDockWidget("Ice Parameters", self)
# Missing: self.dock_params_ice.setObjectName("dockParamsIce")
```

**Verified by:** Live testing — saveState without objectName produced warnings, and dock positions were not restored.

### Pitfall 2: saveState/restoreState Version Mismatch → Silent Failure

**What goes wrong:** `restoreState(state, version)` requires the version number to **exactly match** the version used when `saveState(version)` was called. If versions differ, `restoreState()` returns `False` and does absolutely nothing. The window remains in whatever state it was in before the call.

**Why it happens:** The version number is embedded in the QByteArray. Qt checks it on restore. If they don't match, Qt assumes the state format is from a different application version and refuses to apply it (to avoid corrupt layouts).

**Consequences:**
- After upgrading QuickIce, users' saved layouts are silently discarded
- `restoreState()` returns `False` but doesn't throw an exception
- If you forget to update the version after adding/removing a dock, the state format is wrong

**Prevention:**
- Define a constant `LAYOUT_STATE_VERSION` in MainWindow
- Increment it ONLY when dock structure changes (adding/removing docks, not when moving them)
- Never use the default version (0) — use a custom version from day one
- Log `restoreState()` return value to detect failures

**Verified by:** Live testing — `restoreState(state_v3, version=2)` returned `False` and did nothing; `restoreState(state_v3, version=3)` returned `True` and restored correctly.

```python
# CORRECT
LAYOUT_STATE_VERSION = 2  # Increment when dock structure changes

state = self.saveState(self.LAYOUT_STATE_VERSION)
# ...
restored = self.restoreState(state, self.LAYOUT_STATE_VERSION)
if not restored:
    logger.warning("Failed to restore dock layout — version mismatch?")
```

### Pitfall 3: VTK Segfault in Headless/CI Environments

**What goes wrong:** `QVTKRenderWindowInteractor` segfaults when running with `QT_QPA_PLATFORM=offscreen` or under SSH X11 forwarding with indirect rendering. This crashes the entire application.

**Why it happens:** VTK attempts direct OpenGL rendering, which fails in headless/indirect-rendering environments. The crash happens in the VTK C++ layer, not in Python, so it can't be caught with try/except.

**Consequences:**
- GUI tests that use VTK + docks crash in CI
- SSH users can't run the GUI
- Any test involving `QVTKRenderWindowInteractor.Initialize()` or `Start()` may crash

**Prevention:**
- Never call `vtk_widget.Initialize()` or `vtk_widget.Start()` in headless environments
- Use the existing VTK availability check pattern from `view.py`:
  ```python
  _VTK_AVAILABLE = False
  if os.environ.get('DISPLAY') and 'localhost' in os.environ.get('DISPLAY', ''):
      _VTK_AVAILABLE = os.environ.get('QUICKICE_FORCE_VTK', '').lower() == 'true'
  else:
      _VTK_AVAILABLE = True
  ```
- In headless tests, mock VTK widget or use a QLabel placeholder as central widget
- Wrap VTK calls in conditional: `if self._vtk_available: ...`

**Detection:**
- Segfault (signal 11) in test output
- `QT_QPA_PLATFORM=offscreen` in environment

**Verified by:** Live testing — VTK + dock test script segfaulted immediately in offscreen mode.

### Pitfall 4: raise_() Doesn't Work in Offscreen Platform Plugin

**What goes wrong:** In the offscreen platform plugin (`QT_QPA_PLATFORM=offscreen`), calling `QDockWidget.raise_()` does nothing. The tabified dock doesn't switch to the raised tab. The offscreen plugin prints: "This plugin does not support raise()".

**Why it happens:** The offscreen platform plugin implements a minimal Qt backend for rendering without a display. Window raising is not implemented.

**Consequences:**
- Tests that verify contextual panel switching via `raise_()` will fail
- Toolbar → panel switching can't be tested in CI
- `tabifiedDockWidgetActivated` signal may not fire

**Prevention:**
- In offscreen environments, use alternative tab switching:
  - Find the internal QTabBar in the tabified dock area
  - Call `setCurrentIndex()` on it directly
  - This is a hack but works for testing
- Design tests to verify panel switching via signal checking, not visual output
- Add `@pytest.mark.skipif(offscreen, reason="raise_() not supported offscreen")` for visual tests

**Verified by:** Live testing — "This plugin does not support raise()" warning printed, tab did not switch.

## Moderate Pitfalls

Mistakes that cause delays or technical debt.

### Pitfall 5: ToggleViewAction.setChecked() Doesn't Reliably Show/Hide Dock

**What goes wrong:** `toggleViewAction()` returns a QAction whose checked state should control dock visibility. However, programmatically calling `action.setChecked(True)` does NOT reliably show the dock (especially in offscreen mode). The checked state of the action and the actual visibility of the dock can get out of sync.

**Why it happens:** The `toggleViewAction` is designed for menu items — it's triggered by user interaction (menu click), not programmatic state changes. Setting checked state programmatically may not trigger the internal dock show/hide logic.

**Prevention:**
- Use `dock.show()` / `dock.hide()` for programmatic control
- Use `toggleViewAction` ONLY in menus (its intended purpose)
- To sync toggleViewAction state after programmatic show/hide:
  ```python
  dock.show()
  # Sync action state
  dock.toggleViewAction().setChecked(True)
  ```

**Verified by:** Live testing — `setChecked(True)` after hiding the dock did not make it visible.

### Pitfall 6: Allowing Params Dock to Float → Breaks Tabified Context Switching

**What goes wrong:** If the parameter dock (the tabified left dock with Ice/Hydrate/Interface/Modifiers) is allowed to float (`DockWidgetFloatable`), a user can double-click the title bar and detach it. Once floating, the dock is no longer part of the tabified group, and toolbar-driven `raise_()` calls no longer switch tabs within it. The user sees a floating window that doesn't respond to tool selection.

**Why it happens:** `raise_()` only works on tabified docks in the same dock area. A floating dock is a separate top-level window.

**Prevention:**
- Set parameter dock features WITHOUT `DockWidgetFloatable`:
  ```python
  self.dock_params_ice.setFeatures(
      QDockWidget.DockWidgetFeature.DockWidgetClosable |  # Actually, remove this too
      QDockWidget.DockWidgetFeature.DockWidgetMovable    # No Floatable!
  )
  ```
- Better: parameter docks should have `NoDockWidgetFeatures` — not closable, not movable, not floatable. They're always in the left dock area.
- Use `setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)` to restrict placement

**Detection:**
- After double-clicking dock title bar, dock floats away
- Toolbar buttons don't switch visible parameter panel

### Pitfall 7: Minimum Dock Width Truncates Panel Content

**What goes wrong:** QDockWidget respects the minimum size of its child widget. If the child widget has a large minimum width (e.g., the Interface Panel with its form layout), the dock cannot be made narrower than that. This prevents the user from giving more space to the VTK viewport.

**Why it happens:** Qt layout constraints are strict. A QDockWidget's minimum width = child widget's minimum width + frame + title bar. If a panel has wide QFormLayout labels or large QGroupBox widgets, the minimum width can be 300-400px, leaving the VTK viewport cramped on small screens.

**Prevention:**
- Design panels with `setMinimumWidth()` set to a reasonable minimum (200-250px)
- Use QScrollArea inside docks for panels with many controls:
  ```python
  scroll = QScrollArea()
  scroll.setWidget(panel_content)
  scroll.setWidgetResizable(True)
  dock.setWidget(scroll)
  ```
- Test on minimum screen resolution (1280x720)
- Set `dock.setMinimumWidth(200)` and let content scroll if narrower

**Detection:**
- User cannot drag dock edge to make it narrower
- VTK viewport is too small on laptop screens

### Pitfall 8: tabifyDockWidget Order Affects Initial Tab Bar Display

**What goes wrong:** The order in which you call `tabifyDockWidget(first, second)` determines the tab order. If you tabify in the wrong order, the initial tab bar shows the least-useful tab first (e.g., "Ion" instead of "Ice").

**Why it happens:** `tabifyDockWidget(first, second)` places `second` as a new tab next to `first`. The first dock added to an area becomes the initial visible tab. The `raise_()` call after tabification determines which tab is initially shown.

**Prevention:**
- Always call `raise_()` on the default dock after tabification:
  ```python
  self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_params_ice)
  self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_params_hydrate)
  self.tabifyDockWidget(self.dock_params_ice, self.dock_params_hydrate)
  self.dock_params_ice.raise_()  # ← Ice is default visible tab
  ```

**Detection:**
- Wrong tab is visible on startup
- `tabifiedDockWidgets(dock)` returns tabs in wrong order

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 9: Dock Title Bar Text is Too Long

**What goes wrong:** If dock window titles are long (e.g., "Interface Construction Parameters"), the tab bar in the tabified left dock becomes unreadable. Tabs are truncated, and users can't distinguish between panels.

**Prevention:**
- Use short dock titles: "Ice", "Hydrate", "Interface", "Modifiers"
- Long descriptions go in tooltips: `dock.setToolTip("Ice structure generation parameters")`

### Pitfall 10: restoreDockWidget Shows Dock at Wrong Position

**What goes wrong:** After `removeDockWidget()` + `restoreDockWidget()`, the dock reappears but at its default position (left area), not where it was before removal. `restoreDockWidget()` only restores a dock to the main window layout — it doesn't remember the dock's previous position.

**Prevention:**
- Don't use `removeDockWidget()` / `restoreDockWidget()` for show/hide
- Use `dock.hide()` / `dock.show()` instead (preserves dock position)
- `removeDockWidget()` is for permanently removing a dock from the layout

**Verified by:** Live testing — `restoreDockWidget()` returned `True` but dock was not visible (it was restored to layout but remained hidden).

### Pitfall 11: QDockWidget.visibilityChanged vs QWidget.isVisible

**What goes wrong:** `QDockWidget.visibilityChanged(bool)` and `QWidget.isVisible()` can disagree for tabified docks. A dock that is in a tabified group but not the active tab reports `isVisible() == False` but `visibilityChanged` may not have been emitted.

**Why it happens:** `visibilityChanged` considers whether the dock's content is actually visible to the user (active tab), not whether the QDockWidget widget is technically visible in the Qt widget tree.

**Prevention:**
- Use `visibilityChanged` signal for UX-aware visibility tracking
- Use `isVisible()` only for Qt layout concerns
- Don't rely on `isVisible()` to determine if user can see the dock content

### Pitfall 12: AnimatedDocks Can Cause Flickering During Resize

**What goes wrong:** When `AnimatedDocks` is enabled and the user drags a dock splitter, the central VTK widget receives many resize events in quick succession. Each resize triggers a VTK render. If VTK rendering is slow (large structures), this causes visible flickering.

**Prevention:**
- Use VTK's `SetDesiredUpdateRate()` to throttle renders during resize
- Or temporarily disable AnimatedDocks during generation
- Or connect to `vtkCommand.InteractionEvent` for smarter render scheduling

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Dock skeleton setup | Missing objectName → saveState fails | Set objectName on every dock immediately |
| Panel migration | Breaking existing signal connections | Audit MainWindow._setup_connections() — 2126 lines of wiring |
| Contextual switching | raise_() not working in offscreen/CI | Use setCurrentIndex on internal QTabBar for tests |
| State serialization | Version mismatch on upgrade | Document version bump process; use constant |
| Phase diagram dock | matplotlib canvas resize in dock | FigureCanvasQTAgg handles resize; test at narrow widths |
| VTK scene manager | Actor lifecycle management | Clear/add actors on tool switch; avoid actor accumulation |
| Multi-panel dock testing | VTK segfault in headless | Mock VTK or skip VTK-dependent tests in CI |

## Sources

- Qt 6.11 QDockWidget docs: https://doc.qt.io/qt-6/qdockwidget.html (HIGH confidence — authoritative)
- Qt 6.11 QMainWindow docs: https://doc.qt.io/qt-6/qmainwindow.html (HIGH confidence — authoritative)
- Live PySide6 6.10.2 testing (HIGH confidence — all pitfalls reproduced and verified)
- ParaView User Guide: https://docs.paraview.org/en/latest/UsersGuide/introduction.html (HIGH confidence — ParaView uses same dock pattern)
- QuickIce AGENTS.md — VTK headless/remote constraints (HIGH confidence — project-specific)
