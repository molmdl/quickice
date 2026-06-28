# Domain Pitfalls: VTK Interactor Style & Tool Mode System

**Domain:** VTK interactor style switching, 3D widget lifecycle, event routing
**Researched:** 2026-06-28

## Critical Pitfalls

Mistakes that cause crashes, broken interaction, or require architectural rewrites.

### Pitfall 1: Segfault from VTK Render Window in Headless Environments

**What goes wrong:** Creating `vtkRenderWindow` + `vtkRenderWindowInteractor` without a display causes segfaults. This was confirmed during our research — a minimal `iren = vtkRenderWindowInteractor(); iren.SetRenderWindow(rw)` caused a core dump on this headless system.

**Why it happens:** VTK's OpenGL2 backend requires a valid GL context, which doesn't exist without a display or with `QT_QPA_PLATFORM=offscreen` on some systems.

**Consequences:** Any tool mode code that creates or manipulates VTK rendering objects in test code will crash CI.

**Prevention:** 
- Never create `vtkRenderWindow` or `vtkRenderWindowInteractor` in test code
- Mock VTK objects in unit tests (test logic, not rendering)
- Use `QT_QPA_PLATFORM=offscreen` for GUI tests that need VTK but skip if VTK crashes
- Test interactor style switching logic by testing the `ToolModeManager` state machine, not by actually rendering

**Detection:** CI segfaults in VTK-dependent tests. The AGENTS.md already documents this: "VTK rendering may still crash in some headless environments — mock or skip VTK-dependent tests if needed."

### Pitfall 2: Widget Events Conflict with Interactor Style

**What goes wrong:** When a VTK 3D widget (e.g., `vtkDistanceWidget`) is Enabled and an interactor style is also active, the widget intercepts events that the style needs. For example, in Measure mode, the DistanceWidget may eat the middle-button event, preventing TrackballCamera's pan behavior.

**Why it happens:** VTK widgets have higher event priority than interactor styles. When Enabled, the widget processes events first via `vtkWidgetEventTranslator`. If the widget handles the event, the interactor style never sees it.

**Consequences:** Users can't pan/zoom while using Measure or Draw Region tools. This breaks the fundamental expectation that camera manipulation always works.

**Prevention:**
- Configure widget event translators to only intercept left-button events
- Ensure middle and right button events pass through to the interactor style
- Test every widget+style combination explicitly
- Use `vtkWidgetEventTranslator` to remap events:
  ```python
  translator = widget.GetEventTranslator()
  # Remove middle/right button mappings so they pass to the style
  translator.RemoveEventMapping(vtk.vtkWidgetEvent.Translate, 
                                vtk.vtkEvent.MiddleButton)
  ```

**Detection:** Middle/right drag does nothing in a tool mode that uses widgets.

### Pitfall 3: Observer Leak on Style Switching

**What goes wrong:** Custom interactor styles add observers to the style object (e.g., `self.AddObserver(vtkCommand.LeftButtonPressEvent, callback)`). When the style is switched out via `SetInteractorStyle()`, these observers remain on the style object. If the same style is re-activated later, observers are added again, causing duplicate callbacks.

**Why it happens:** VTK's `AddObserver()` returns a tag, but if you don't store and remove the tag, the observer persists. Style switching doesn't automatically remove observers.

**Consequences:** Double-firing callbacks, incorrect pick results, memory growth.

**Prevention:**
- Every custom style has `activate()` / `deactivate()` methods
- `activate()` adds observers and stores tags in `self._observer_tags`
- `deactivate()` removes all observers by tag
- ToolModeManager always calls `deactivate()` on old style before `activate()` on new style

**Detection:** Click in Select mode fires the selection callback twice after switching away and back.

### Pitfall 4: Picker State Corruption

**What goes wrong:** The interactor's `SetPicker()` method sets a global picker. If ToolModeManager switches pickers (PropPicker for Select, CellPicker for Place, PointPicker for Pick), the old picker's state may leak into the new mode.

**Why it happens:** `vtkRenderWindowInteractor.SetPicker()` increments the new picker's refcount and decrements the old one, but the picker's internal state (last pick position, picked prop list) persists.

**Consequences:** Select mode returns results from Place mode's last pick. False selections.

**Prevention:**
- Always call `picker.Initialize()` or create fresh pickers per mode activation
- Clear pick lists between mode switches
- Don't rely on picker state across mode switches

**Detection:** Select mode shows a molecule as "selected" that was picked in Place mode.

## Moderate Pitfalls

Mistakes that cause delays or annoying bugs.

### Pitfall 5: ContourWidget Node Positions Drift During Camera Rotation

**What goes wrong:** When using `vtkContourWidget` for region drawing, rotating the camera while the contour is visible causes the contour nodes to appear to "drift" away from their original positions. This is because the contour points are in world coordinates, and the visual representation updates with camera changes — but if the `PointPlacer` isn't properly configured, nodes may appear to detach from the structure.

**Why it happens:** The contour representation needs to know what coordinate system it's in. If `vtkBoundedPlanePointPlacer` isn't set up correctly, display-to-world conversion can be inaccurate after camera changes.

**Prevention:** 
- Always use `vtkBoundedPlanePointPlacer` (or `vtkFocalPlanePointPlacer`) with ContourWidget
- Set the projection normal explicitly: `placer.SetProjectionNormalToZAxis()` 
- Test contour drawing after camera rotation

**Detection:** Region polygon appears to shift when camera rotates.

### Pitfall 6: vtkDistanceWidget Label Not Updating

**What goes wrong:** The distance label on the `vtkDistanceRepresentation3D` shows a stale or incorrect value after moving the measure endpoints.

**Why it happens:** The label format string needs to be set explicitly, and the representation may need `SetLabelFormat("%.2f nm")` for proper nm-unit display. Default format may show too many decimals or wrong units.

**Prevention:** 
- Set `rep.SetLabelFormat("%.3f nm")` explicitly
- Verify the distance value is in the correct unit (QuickIce uses nm)
- Test with known distances

**Detection:** Distance label shows "0.000" or a value in wrong units.

### Pitfall 7: QVTKRenderWindowInteractor Cursor Not Respecting Qt Changes

**What goes wrong:** Setting `vtk_widget.setCursor(Qt.CrossCursor)` works initially, but VTK's `CursorChangedEvent` handler may override it back to `ArrowCursor` when the interactor style changes.

**Why it happens:** `QVTKRenderWindowInteractor.ShowCursor()` reads VTK's current cursor enum and maps it via `_CURSOR_MAP`. When VTK internally changes cursor state (e.g., during rotation), it fires `CursorChangedEvent`, which triggers `ShowCursor()`, overriding the Qt-set cursor.

**Prevention:**
- Either: Set cursor via VTK's `iren.GetRenderWindow().SetCurrentCursor(VTK_CURSOR_CROSSHAIR)` and let VTK manage cursor changes
- Or: Disconnect `CursorChangedEvent` observer and manage cursor purely from Qt
- Recommended: Use VTK's cursor system (it maps to Qt cursors correctly)

**Detection:** Cursor changes back to arrow after rotating in a tool mode that should show crosshair.

### Pitfall 8: Multiple Widgets Fighting for the Same Event

**What goes wrong:** If two widgets are accidentally enabled simultaneously (e.g., a DistanceWidget and a ContourWidget), both try to process left-button events, causing undefined behavior.

**Why it happens:** ToolModeManager forgot to disable the previous mode's widgets before enabling the new mode's widgets.

**Prevention:**
- ToolModeManager always disables ALL widgets before enabling new mode's widgets
- Add assertion: `assert sum(1 for w in all_widgets if w.GetEnabled()) <= 1`
- Log widget enable/disable state during mode transitions

**Detection:** Unpredictable click behavior; sometimes a distance measure appears, sometimes a contour node.

### Pitfall 9: InteractorStyle Reference Count Leak

**What goes wrong:** When switching styles via `SetInteractorStyle()`, the interactor increments the new style's refcount. But if you create a NEW style instance every time you switch (instead of reusing pre-built styles), the old style's refcount drops to 1 (held by your dict), but VTK's internal pointer may also hold a reference. Over many mode switches, this can cause subtle memory growth.

**Why it happens:** VTK uses reference counting. `SetInteractorStyle(new)` calls `Register(new)` and `UnRegister(old)`. If you hold your own Python reference to `old`, it won't be freed. But if you DON'T hold a reference (creating anonymous instances), VTK may keep them alive through its observer system.

**Prevention:**
- Pre-create all styles in `_build_mode_registry()` and keep them alive for the app lifetime
- Never create styles on-the-fly in `set_mode()`
- Monitor refcounts in debug mode

**Detection:** Slowly increasing memory usage over many mode switches.

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 10: Status Bar Hint Not Cleared on Mode Switch

**What goes wrong:** Status bar shows "Click to add vertices" after switching from Draw Region to Navigate.

**Why it happens:** Forgot to emit `status_hint_changed` signal in `set_mode()`.

**Prevention:** Always update status hint in `set_mode()`, including for Navigate mode.

### Pitfall 11: ContourWidget CloseLoop Requires Double-Click Timing

**What goes wrong:** `vtkContourWidget.CloseLoop()` works, but the user must double-click or press Enter. The timing for double-click detection in VTK may not match the user's expectation.

**Why it happens:** VTK's double-click detection depends on `OnLeftButtonDoubleClick()` which requires two clicks within a system-defined interval. This may not be intuitive for region closing.

**Prevention:** Support multiple close actions: double-click, Enter key, and a "Close Region" button in the context panel.

### Pitfall 12: vtkCellPicker Tolerance Too Low for Small Atoms

**What goes wrong:** `vtkCellPicker` can't find atoms because its tolerance (in pixels) is too low for small VDW spheres in the nm coordinate system.

**Why it happens:** QuickIce positions are in nm, but picker tolerance is in screen pixels. Small atoms at the current zoom level may occupy <1 pixel.

**Prevention:** 
- Set picker tolerance explicitly: `cell_picker.SetTolerance(0.002)` (or higher)
- Consider using `vtkPointPicker` with a higher tolerance for atom selection
- Test at various zoom levels

**Detection:** Clicking directly on a visible atom does not register as a pick.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Navigate + Select | Observer leak on style switching | activate()/deactivate() pattern |
| Place Molecule | Picker tolerance too low for nm-scale atoms | Increase picker tolerance; test at various zoom levels |
| Place Molecule | Plane projection incorrect for triclinic cells | Test with non-orthogonal cells; use proper plane normal |
| Measure | DistanceWidget steals middle/right button events | Configure widget event translator |
| Draw Region | ContourWidget nodes drift during camera rotation | Use BoundedPlanePointPlacer with explicit projection |
| Draw Region | CloseLoop UX unclear | Support multiple close actions (double-click, Enter, button) |
| Draw Region | ContourWidget + TrackballCamera event conflict | Test event routing; ensure middle/right pass through |
| Pick | PointPicker returns wrong atom index | Validate against known positions; use tolerance testing |
| All modes | Cursor overridden by VTK CursorChangedEvent | Use VTK cursor system instead of Qt setCursor |

## Sources

- VTK 9.5.2 API testing: confirmed segfault in headless (see AGENTS.md)
- QVTKRenderWindowInteractor.py source: cursor management via `_CURSOR_MAP` and `CursorChangedEvent`
- VTK documentation: widget event translator, observer pattern
- Polycrystalline builder research: shape drawing approaches
- QuickIce codebase: existing viewer implementations
