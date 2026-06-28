# Technology Stack: Single-Viewport VTK Architecture

**Project:** QuickIce Integrated VTK GUI
**Researched:** 2026-06-28

## Recommended Stack

### Core Framework (No Changes)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PySide6 | 6.10.2 | Qt GUI framework | Already in use; QDockWidget + QMainWindow pattern needed |
| VTK | 9.5.2 | 3D rendering | Already in use; all required APIs available |
| numpy | 2.4.3 | Array operations | Already in use; VTK interop for point data |

### New Internal Modules

| Module | Purpose | Why |
|--------|---------|-----|
| `quickice/gui/unified_viewer.py` | Single-viewport VTK widget replacing 7 viewer classes | Core of the redesign; wraps `QVTKRenderWindowInteractor` with assembly management |
| `quickice/gui/structure_actor_builder.py` | Converts any structure type → `dict[str, vtkAssembly]` | Eliminates 4x duplicated `_extract_bonds()`, `_create_guest_ball_and_stick_actor()` |
| `quickice/gui/actor_group.py` | Thin `vtkAssembly` wrapper with visibility/opacity/representation APIs | Clean API for phase toggling without exposing raw VTK |

### VTK 9.5.2 APIs Used

| API | Purpose | Verified |
|-----|---------|----------|
| `vtkAssembly` | Actor grouping with hierarchical visibility | YES — tested: `AddPart()`, `GetParts()`, `SetVisibility()`, nested assemblies work |
| `vtkRenderer.SetViewport(xmin,ymin,xmax,ymax)` | Split-view candidate comparison | YES — API exists, returns None (setter) |
| `vtkRenderer.SetLayer(int)` | 2D overlay on separate layer | YES — API exists |
| `vtkRenderWindow.SetNumberOfLayers(int)` | Enable multi-layer rendering | YES — API exists, returns None |
| `vtkTextActor` | 2D text labels (screen-space) | YES — `SetInput()`, `SetPosition()` work |
| `vtkBillboardTextActor3D` | 3D-positioned labels that face camera | YES — available in 9.5.2 |
| `vtkCornerAnnotation` | Corner text overlay | YES — available |
| `vtkDepthSortPolyData` | Sort translucent polydata by depth | YES — available for preview molecule sorting |
| `vtkActor.SetVisibility(int)` | Per-actor visibility toggle | YES — `0` hides, `1` shows, rendering skips hidden actors |
| `vtkActor.GetProperty().SetOpacity(float)` | Transparency | YES — 0.0 to 1.0 range |
| `vtkCamera.DeepCopy(other)` | Camera synchronization | YES — used in current `DualViewerWidget` |
| `vtkMoleculeMapper` | Ball-and-stick rendering | YES — already in use across all viewers |
| `vtkGlyph3D` | Efficient multi-instance rendering | YES — alternative for large point sets |
| `vtkPolyDataMapper` | Generic polydata rendering | YES — used for bond lines, unit cell |
| `vtkCommand.ModifiedEvent` | Camera change observer for sync | YES — used in current `DualViewerWidget` |

### Key API Behavior Notes

**`vtkAssembly` visibility:**
- `assembly.SetVisibility(0)` hides ALL parts during rendering
- `part.GetVisibility()` still returns `1` for child parts — this is the assembly's own flag
- Effective visibility = `assembly.GetVisibility() AND part.GetVisibility()`
- **Don't check child visibility to determine rendering state — check parent assembly**

**`vtkRenderer.SetViewport()`:**
- Parameters are normalized coordinates: `(xmin, ymin, xmax, ymax)` in `[0, 1]`
- Viewport defines which region of the render window this renderer draws to
- Multiple renderers can coexist in one render window
- **Each renderer has its own camera** — this is how split-view works

**`vtkRenderWindow.SetNumberOfLayers()`:**
- Default is 1. Set to 2+ for overlay rendering
- Layer 0 = background (3D scene), Layer 1 = foreground (2D HUD)
- Higher-layer renderers draw on top of lower layers
- **Set `overlay_renderer.SetInteractive(0)` to prevent mouse interaction on overlay**

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Actor grouping | `vtkAssembly` | `vtkActorCollection` | ActorCollection is just a list — no hierarchical visibility, no `AddPart` nesting, no group-level rendering optimization |
| Actor grouping | `vtkAssembly` | Plain `renderer.AddActor()` list | No group toggle; must iterate all actors to hide/show a phase; O(n) vs O(1) |
| Split view | `SetViewport()` on 2 renderers | QSplitter + 2 `QVTKRenderWindowInteractor` | Two OpenGL contexts, two interactors; defeats the single-viewport goal |
| Split view | `SetViewport()` | Single viewport + cycling | Loses side-by-side comparison; acceptable as fallback only |
| 2D overlay | Renderer layers (SetLayer) | In-scene text actors | 3D text rotates with scene; can't display fixed UI elements |
| 2D overlay | Renderer layers | PySide6 QLabel overlay | Z-ordering issues; VTK widget captures mouse events; paint overlay doesn't integrate with VTK render pipeline |
| Bond rendering | `vtkMoleculeMapper` | Custom `vtkGlyph3D` pipeline | vtkMoleculeMapper handles atom+bond rendering in one pass; Glyph3D only does points; combining bonds with Glyph3D requires separate polydata |
| Bond rendering | `create_bond_lines_actor()` | `vtkMoleculeMapper` (for interface) | Bond lines are lighter weight (no 3D spheres/cylinders); interface uses lines intentionally to reduce GPU load for large structures |

## Performance Benchmarks (VTK 9.5.2, quickice conda env)

| Benchmark | Result | Notes |
|-----------|--------|-------|
| `vtkPolyData` 500k points creation | 194ms | Using `vtkPoints.InsertNextPoint()` |
| `vtkPolyData` 500k points memory | 6,144 KB (~6 MB) | `GetActualMemorySize()` |
| `vtkGlyph3D` 100k atoms | 657ms, 492 MB output | Glyph3D creates full sphere geometry per point |
| `vtkMolecule` 768 ice mols (2,304 atoms) | 13.3ms | Including bond creation |
| `vtkMolecule` 4,000 water mols (12,000 atoms) | 26.8ms | Including bond creation |
| Bond lines polydata (14,304 pts, 9,536 lines) | 31.2ms | For interface-style rendering |
| Bond lines polydata memory (14k pts) | 576 KB | Very lightweight |
| Ion points (100) | 0.1ms | Trivial |

**Key performance insights:**
1. `vtkMoleculeMapper` is efficient for <20K atoms (covers all QuickIce structures)
2. Bond-line polydata is very lightweight (576 KB for full interface)
3. `vtkGlyph3D` creates much heavier geometry (492 MB for 100k atoms) — avoid for molecular rendering
4. Total memory budget for all phases in one renderer: <5 MB polydata + GPU framebuffer

## Sources

- VTK 9.5.2 API tests run against installed `vtkmodules.all` in quickice conda env
- `vtkAssembly` hierarchical visibility: tested with parent/child, `SetVisibility(0)` confirmed to hide all parts during rendering
- `vtkPolyData` memory benchmarks: measured via `GetActualMemorySize()` on real polydata
- `vtkMoleculeMapper` build time benchmarks: measured with `time.perf_counter()`
- QuickIce structure type definitions verified via `__dataclass_fields__` introspection
