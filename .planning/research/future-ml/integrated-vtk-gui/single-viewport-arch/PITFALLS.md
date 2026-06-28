# Domain Pitfalls: Single-Viewport VTK Architecture

**Domain:** VTK-Centric GUI Redesign
**Researched:** 2026-06-28

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: vtkAssembly Visibility Semantics Mismatch

**What goes wrong:** `child_actor.GetVisibility()` returns `1` even when the parent `vtkAssembly` has `SetVisibility(0)`. Code that checks `actor.GetVisibility()` to determine rendering state gets wrong answers.

**Why it happens:** VTK's `vtkAssembly.SetVisibility(0)` only sets the assembly's own visibility flag. During rendering, VTK evaluates the effective visibility chain (assembly AND part), but `GetVisibility()` on the child still returns the child's own flag.

**Consequences:** 
- UI checkboxes become out of sync with actual rendering state
- Code like `if actor.GetVisibility(): ...` behaves incorrectly when the actor is inside a hidden assembly
- "Toggle all" operations that iterate parts and call `SetVisibility()` create confusing states

**Prevention:** 
- Never query `actor.GetVisibility()` for rendering state — always check the parent assembly
- Create `ActorGroup` wrapper that tracks visibility in its own state variable
- UI binds to `ActorGroup.set_visible()` / `ActorGroup.is_visible()`, not raw VTK API

**Detection:** If checkboxes show "visible" but actors aren't rendering, this is the likely cause.

### Pitfall 2: VTK Render Window Segfault in Headless Environments

**What goes wrong:** Creating a `vtkRenderWindow` or calling `Render()` on it causes a segfault in SSH X11 forwarding or headless environments.

**Why it happens:** VTK tries to create an OpenGL context. Without a proper display server (X11/Wayland), the OpenGL driver crashes. `QT_QPA_PLATFORM=offscreen` does NOT always help — VTK's rendering backend may bypass Qt's offscreen driver.

**Consequences:** Application crash on remote SSH sessions. Current codebase has `_VTK_AVAILABLE` detection but the new architecture must preserve it.

**Prevention:**
- Preserve the existing `_VTK_AVAILABLE` detection pattern from `hydrate_viewer.py`
- Test `QUICKICE_FORCE_VTK=true` override
- Consider `vtkOSPRayRenderWindow` as a software-rendering fallback (but this adds a dependency)
- Always wrap VTK render calls in try/except

**Detection:** Segfault on startup in SSH session. Check `DISPLAY` env var for `localhost` prefix.

### Pitfall 3: SetViewport Split-View Mouse Interaction Failure

**What goes wrong:** When using `vtkRenderer.SetViewport()` to create split view, mouse events (rotation, zoom, pan) may all route to one renderer instead of the renderer under the cursor.

**Why it happens:** `QVTKRenderWindowInteractor` has a single `vtkRenderWindowInteractor`. The interactor may not correctly determine which sub-viewport renderer should receive the event based on mouse position.

**Consequences:** User tries to rotate the right-side candidate but the left side rotates instead. Or, only one viewport responds to mouse input.

**Prevention:**
- Test `SetViewport()` mouse routing early in development
- If routing fails: implement custom `vtkInteractorStyle` that reads mouse position and calls `FindPokedRenderer(x, y)` to route events
- VTK's `vtkRenderWindowInteractor.SetLastEventPosition()` and `FindPokedRenderer()` are the key methods
- Alternative: Use `QSplitter` with two VTK widgets as fallback (two OpenGL contexts, but correct mouse routing)

**Detection:** Mouse events only affect one side of split view.

### Pitfall 4: Memory Leak from Stale Actor References

**What goes wrong:** When replacing an assembly (e.g., new ice candidate), removing the old assembly from the renderer but keeping Python references to it prevents VTK from freeing GPU memory.

**Why it happens:** VTK uses reference counting. Python wrappers hold references. If `self._groups["ice"]` holds the old assembly while a new one is created, the old assembly's GPU resources are not freed until the Python reference is released.

**Consequences:** GPU memory grows with each structure generation. After 10+ generations, framebuffers and vertex buffers accumulate.

**Prevention:**
- Always set `self._groups[phase] = None` or `del self._groups[phase]` before creating a new group
- Call `renderer.RemoveActor(assembly)` before replacing
- Use `assembly.GetParts().RemoveAllItems()` before discarding (forces cleanup of child actors)
- Consider `vtkGarbageCollector.RequestDeferredCollection()` after major actor swaps

**Detection:** Monitor GPU memory usage across multiple generation cycles.

### Pitfall 5: Camera Reset on Downstream Addition Destroys Viewing Angle

**What goes wrong:** Calling `renderer.ResetCamera()` when ions are added to an existing interface jumps the camera to fit the new (slightly different) bounding box, losing the user's carefully positioned view angle.

**Why it happens:** The current `IonViewerWidget._reset_camera()` always resets camera. When ions are tiny compared to the interface (20 ions vs 14,000 water atoms), the camera shift is minimal but still annoying.

**Consequences:** User frustration — they position the view, add ions, and the camera jumps.

**Prevention:**
- Only reset camera on base structure changes (ice candidate, interface, hydrate)
- For downstream additions (ions, solutes, custom molecules): adjust clipping range only
- `renderer.ResetCameraClippingRange()` without `ResetCamera()` preserves the view but ensures near/far planes are correct

**Detection:** Camera position changes when adding ions.

## Moderate Pitfalls

Mistakes that cause delays or technical debt.

### Pitfall 6: O(n²) Bond Detection in Actor Builder

**What goes wrong:** `hydrate_renderer.py` uses O(n²) distance-based bond detection within each molecule (`for i in range(n): for j in range(i+1, n)`). For large guest molecules (THF, 13 atoms), this is fine. But if the builder accidentally runs this on ALL atoms instead of per-molecule, it becomes O(N²) for the full structure.

**Prevention:** Use `molecule_index` to bound bond detection to individual molecules only. The current `_build_vtk_molecule_from_molecule_index()` pattern is correct — preserve it.

### Pitfall 7: VTK Widget Initialization Order

**What goes wrong:** Calling `QVTKRenderWindowInteractor.Initialize()` before the widget is shown (has a valid window handle) causes rendering to fail silently or crash.

**Why it happens:** VTK needs the Qt window handle to create the OpenGL context. If `Initialize()` is called too early, the context is invalid.

**Prevention:** Call `Initialize()` after `showEvent()` or after adding the widget to a visible layout. The current `molecular_viewer.py` calls `Initialize()` in `__init__` which works because Qt defers rendering until the event loop runs.

### Pitfall 8: QDockWidget Resize Causing VTK Render Storms

**What goes wrong:** Dragging a QDockWidget border triggers continuous resize events on the central VTK widget, causing VTK to re-render on every mouse move.

**Why it happens:** Qt sends `resizeEvent` on every pixel of dock drag. VTK responds to each with a full render.

**Prevention:**
- Use `setUpdatesEnabled(False)` during dock drag, `True` on release
- Or: debounce renders with a 50ms QTimer — only render after 50ms of no resize
- Or: VTK may already throttle internally (test before optimizing)

### Pitfall 9: vtkMoleculeMapper and Bond Color Override

**What goes wrong:** Setting `mapper.SetBondColor(r, g, b)` on a `vtkMoleculeMapper` doesn't always apply if `SetColorModeToDefault()` is active — VTK may use element-based colors instead.

**Prevention:** Always call `mapper.ScalarVisibilityOff()` before setting custom bond colors. The current code does this correctly.

### Pitfall 10: Assembly Picking (If Implemented Later)

**What goes wrong:** `vtkAssembly` parts are not individually pickable by default — picking returns the top-level assembly, not the child actor.

**Prevention:** If per-actor picking is needed (e.g., click on an ion to get info), use `vtkPropPicker` with `actor.SetPickable(1)` on child parts, and trace back via `GetPath()` in the pick result.

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 11: ANGSTROM_TO_NM Conversion Scattered Across Files

**What goes wrong:** The constant `0.1` (ANGSTROM_TO_NM) is defined separately in `molecular_viewer.py`, `interface_viewer.py`, `ion_viewer.py`, `solute_viewer.py`, `custom_molecule_viewer.py`, and `hydrate_renderer.py`.

**Prevention:** Define once in `quickice/gui/constants.py` or `quickice/gui/vtk_utils.py` and import everywhere.

### Pitfall 12: Duplicate _extract_bonds() Implementation

**What goes wrong:** `_extract_bonds()` is copy-pasted across 4 viewer files (interface, ion, solute, custom molecule). Any bug fix must be applied 4 times.

**Prevention:** Move to `vtk_utils.py` or the new `StructureActorBuilder`.

### Pitfall 13: Duplicate _create_guest_ball_and_stick_actor() Implementation

**What goes wrong:** Same function duplicated in 4 viewer files. Identical code.

**Prevention:** Move to `vtk_utils.py` or the new `StructureActorBuilder`.

### Pitfall 14: PBC Wrapping Assumptions in Bond Extraction

**What goes wrong:** Current `_extract_bonds()` assumes orthorhombic cells (`np.diag(cell)`) for PBC wrapping. Triclinic cells (ice II, ice V) would have incorrect bond visualization.

**Prevention:** Use the full cell matrix for PBC (same as `vtk_utils._pbc_min_image_position()`). The current `interface_viewer.py._extract_bonds()` uses `cell_dims = np.diag(cell)` which is WRONG for triclinic cells.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| UnifiedViewerWidget init | VTK widget init order (Pitfall 7) | Test Initialize() after showEvent |
| Actor group visibility | Assembly visibility mismatch (Pitfall 1) | Use ActorGroup wrapper with own state tracking |
| Split-view implementation | Mouse routing failure (Pitfall 3) | Test early; have QSplitter fallback |
| Dock-based layout | Render storms on resize (Pitfall 8) | Debounce renders |
| Incremental updates | Memory leak from stale refs (Pitfall 4) | Clear Python references before replacing |
| Camera management | Reset on downstream addition (Pitfall 5) | Only reset on base structure changes |
| Bond extraction refactoring | Triclinic PBC bug (Pitfall 14) | Use full cell matrix, not diag() |
| Actor builder consolidation | O(n²) bond detection (Pitfall 6) | Preserve per-molecule boundary pattern |

## Sources

- VTK 9.5.2 API behavior verified by direct testing
- Segfault in headless environment confirmed (vtkRenderWindow creation crashes with `QT_QPA_PLATFORM=offscreen`)
- Assembly visibility behavior: `parent.SetVisibility(0)` → `child.GetVisibility()` still returns `1` (tested)
- PBC triclinic bug: `np.diag(cell)` is incorrect for non-orthogonal cells (existing code analysis)
- Current codebase: 4x duplicated `_extract_bonds()`, 4x duplicated `_create_guest_ball_and_stick_actor()`
