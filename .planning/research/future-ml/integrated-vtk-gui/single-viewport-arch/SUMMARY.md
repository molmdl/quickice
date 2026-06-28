# Research Summary: Single-Viewport VTK Architecture

**Domain:** VTK-Centric GUI Redesign — Unified 3D Viewport
**Researched:** 2026-06-28
**Overall confidence:** HIGH

## Executive Summary

The transition from 8 independent VTK viewers to a single shared viewport is **technically feasible and architecturally sound**. VTK 9.5.2 provides all required primitives: `vtkAssembly` for actor grouping with hierarchical visibility toggling, `vtkRenderer.SetViewport()` for split-view rendering, `vtkRenderer.SetLayer()` for 2D overlays, and `vtkTextActor`/`vtkBillboardTextActor3D` for annotations. The current codebase already demonstrates the single-renderer pattern — `IonViewerWidget` and `SoluteViewerWidget` both add interface + overlay actors to a single renderer — proving the approach works at the code level.

The key design decision is choosing between `vtkAssembly` (hierarchical, supports group visibility toggle) vs plain `renderer.AddActor()` (flat, per-actor visibility). **Recommendation: Use `vtkAssembly`** for each structure phase (ice, water, guests, solutes, ions, custom molecules, unit cell) because it provides O(1) visibility toggling, clean actor lifecycle management, and enables the "show/hide phase" UX that the integrated GUI needs.

For the DualViewerWidget replacement, **recommend `vtkRenderer.SetViewport()` for split-view** (left/right halves within one `QVTKRenderWindowInteractor`). This preserves the side-by-side comparison UX while reducing from 2 render windows to 1, cutting OpenGL context overhead in half. The synchronized camera pattern from the existing `DualViewerWidget` carries over directly.

Memory and performance are well within budget. A full interface structure (768 ice + 4000 water = ~14,300 atoms) builds in ~40ms as `vtkMolecule` objects and ~31ms as `vtkPolyData` bond lines. The `vtkPolyData` for 500k points consumes ~14 MB — the expected ~15k atoms per structure is trivially small. Even with all phases rendered simultaneously (ice + water + guests + solutes + ions), the total actor count stays under 30, and total polydata memory under 5 MB.

The main risk is **transparency sorting for overlapping translucent regions** (polycrystal phase boundaries, preview molecules). VTK 9.5.2's `vtkDepthSortPolyData` exists but requires careful camera-relative sorting. For the MVP, make all structure actors opaque (current approach uses opaque bond lines and solid spheres) and reserve transparency for preview molecules only.

## Key Findings

**Stack:** VTK 9.5.2 has all APIs needed — `vtkAssembly`, `vtkRenderer.SetViewport()`, `vtkRenderer.SetLayer()`, `vtkTextActor`, `vtkBillboardTextActor3D`. No new dependencies required.

**Architecture:** Single `QVTKRenderWindowInteractor` as `QMainWindow.setCentralWidget()`, one `vtkRenderer` per scene, `vtkAssembly` per structure phase. `QDockWidget` panels for controls. Split-view via `SetViewport()` on two renderers sharing one render window.

**Critical pitfall:** VTK `vtkRenderWindow` segfaults in headless/offscreen environments (confirmed in our testing). The existing `QUICKICE_FORCE_VTK` + display detection pattern must be preserved. Also: `vtkAssembly.GetVisibility()` returns the assembly's own flag, NOT the effective visibility (which depends on parent chain). During rendering, VTK correctly hides child parts when parent assembly is invisible — but code querying `child_actor.GetVisibility()` will see `1` even when the parent assembly is hidden.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **UnifiedViewerWidget core** — Build single-viewport widget with `vtkAssembly` group management
   - Addresses: Actor consolidation, visibility toggling, camera management
   - Avoids: Pitfall of per-actor visibility management becoming unmanageable

2. **Actor builder consolidation** — Refactor 6+ `render_*()` functions into `StructureActorBuilder`
   - Addresses: DRY principle, unified coloring system, shared PBC bond extraction
   - Avoids: Duplicate `_extract_bonds()`, `_create_guest_ball_and_stick_actor()` across 4 viewers

3. **Dual view via SetViewport()** — Replace `DualViewerWidget` with split-renderer approach
   - Addresses: Side-by-side comparison UX preservation
   - Avoids: 2 OpenGL contexts, 2 render windows, camera sync complexity

4. **QMainWindow + QDockWidget layout** — Replace QTabWidget with dock-based layout
   - Addresses: Single viewport always visible, controls in dock panels
   - Avoids: 8 hidden VTK viewers consuming GPU memory while not displayed

5. **2D overlay layer** — Add `vtkTextActor` labels, region indicators
   - Addresses: Phase labels, measurement annotations
   - Avoids: Inline 3D text that rotates with the scene

**Phase ordering rationale:**
- Phase 1 must come first (core widget)
- Phase 2 must precede Phase 3 (actor builders needed for split-view rendering)
- Phase 3 before Phase 4 (dual-view must work before dismantling tabs)
- Phase 4 is the architectural transformation
- Phase 5 is polish (labels, HUD)

**Research flags for phases:**
- Phase 3: VTK `SetViewport()` interaction between two renderers sharing one interactor — needs testing (does mouse pick work correctly in split view?)
- Phase 4: QDockWidget resize behavior with VTK widget — needs testing (does VTK re-render efficiently on dock resize?)
- Phase 5: `vtkDepthSortPolyData` for transparent preview molecules — needs performance validation

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | VTK 9.5.2 APIs verified against actual install |
| Features | HIGH | Current viewer code analyzed, all 7 viewer classes read |
| Architecture | HIGH | vtkAssembly, SetViewport, SetLayer all tested in VTK 9.5.2 |
| Pitfalls | HIGH | Segfault in headless confirmed, assembly visibility semantics tested |
| Performance | HIGH | Benchmarked: 500k pts = 14 MB, 15k atoms builds in ~40ms |
| Dual-view split | MEDIUM | SetViewport API confirmed; mouse interaction in split view untested |

## Gaps to Address

- **Split-view mouse interaction:** Need to test if `QVTKRenderWindowInteractor` correctly routes mouse events to the renderer under the cursor when using `SetViewport()`. The interactor may need a custom `vtkInteractorStyleSwitch` or event forwarding.
- **Dock widget resize rendering:** Need to verify VTK re-renders without artifacts when QDockWidgets are dragged/resized around the central VTK widget.
- **Large-scale transparent actor sorting:** `vtkDepthSortPolyData` performance with 10k+ translucent cells needs benchmarking.
