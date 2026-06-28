# Feature Landscape: Single-Viewport Architecture

**Domain:** VTK-Centric GUI Redesign
**Researched:** 2026-06-28

## Table Stakes

Features users expect from the current multi-viewer architecture. Missing = regression.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Phase-distinct coloring | Ice=cyan, water=cornflower, guests=gray, ions=purple/green — this is the core visual language | Low | Already per-actor; assemblies don't affect color |
| Visibility toggling per phase | Show/hide ice, water, ions, solutes independently | Low | `vtkAssembly.SetVisibility()` — O(1) |
| Ball-and-stick / VDW / Stick representation modes | Current Ice tab cycles 3 modes | Medium | Must propagate to all assemblies of same type |
| H-bond dashed line display | Current Ice + Hydrate tabs have toggle | Low | Already `vtkActor` in assembly |
| Unit cell wireframe | All tabs have toggle | Low | Already `vtkActor` in assembly |
| Auto-rotation | Ice tab has auto-rotate at ~10°/sec | Low | Single QTimer on one camera |
| Zoom-to-fit / Reset camera | All viewers have this button | Low | `renderer.ResetCamera()` |
| Screenshot export | Save current viewport as image | Low | `vtkWindowToImageFilter` on single render window — simpler than current approach |
| Dual-view candidate comparison | Ice tab shows 2 candidates side-by-side | Medium | `SetViewport()` split; see Dual-View section |
| Camera sync in dual-view | Left/right cameras stay synchronized | Medium | Same `DeepCopy` + observer pattern as current `DualViewerWidget` |
| Preview molecule with semi-transparency | Custom molecule tab shows preview at proposed position | Low | Single actor with `SetOpacity(0.6)` |
| Placeholder before generation | Show "No structure generated" message | Low | VTK text or Qt overlay — no need for QStackedWidget |
| VTK availability detection | Handle SSH X11 forwarding gracefully | Low | Same `QUICKICE_FORCE_VTK` pattern |

## Differentiators

Features that the single-viewport architecture enables but the current tab-based design cannot do.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Simultaneous all-phase view** | See ice + water + guests + solutes + ions in ONE viewport | Low (just add assemblies) | This is the core value — currently impossible with tab-separated viewers |
| **Dock-based layout** | Viewport always visible while adjusting controls in dock panels | Medium | QDockWidget panels float/tab; viewport never hidden |
| **Layer toggle UI** | Checkboxes for each phase (Ice ☑, Water ☑, Guests ☐, Ions ☑, ...) | Low | Assembly visibility mapped to checkboxes |
| **Region-selective focus** | Click an assembly to zoom/focus on just that phase | Medium | Requires picking + camera animation |
| **Measurement overlays** | 2D annotations (bond distances, angles, cell parameters) | Medium | Layer-1 renderer with `vtkTextActor` |
| **Phase boundary highlighting** | Highlight ice-water boundary region | Medium | Custom polydata actor for boundary |
| **Single-context GPU efficiency** | 1 OpenGL context vs 8 = ~8x less GPU memory for framebuffers | Low (architectural) | Measurable improvement on low-end GPUs |
| **Smooth phase transitions** | Fade in/out phases with opacity animation | Low | QTimer + `SetOpacity()` step |
| **Viewport split for any phase** | Not just ice candidates — compare any two structures side-by-side | Medium | Split-view API is generic |

## Anti-Features

Features to explicitly NOT build. Common mistakes in VTK GUI redesigns.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Rebuilding all actors on every change** | O(n²) bond detection + full actor rebuild = slow, janky | Incremental updates: only rebuild the changed phase assembly |
| **Per-tab VTK viewer instances** | Current approach; wastes GPU memory on hidden viewers | Single viewer, swap actor groups |
| **2D Qt overlay on VTK widget** | Z-ordering, mouse event capture, paint glitches | Use VTK's layer-1 renderer for 2D overlays |
| **Multiple `QVTKRenderWindowInteractor` in one window** | Each creates its own OpenGL context; performance cost | Single widget with `SetViewport()` for split |
| **Custom OpenGL rendering pipeline** | VTK handles it; custom shaders = maintenance nightmare | Use VTK's built-in mappers (MoleculeMapper, PolyDataMapper) |
| **Real-time actor updates during generation** | VTK rendering blocks while Python processes | Build actors after generation completes (current approach) |
| **vtkGlyph3D for molecular rendering** | Creates 50x more geometry than needed | Use `vtkMoleculeMapper` — designed for molecular visualization |
| **Global actor visibility tracking** | Fragile; assembly visibility semantics are confusing | Track visibility in `ActorGroup` wrapper, not by querying VTK |

## Feature Dependencies

```
Single QVTKRenderWindowInteractor
├── vtkAssembly per phase
│   ├── Visibility toggling (depends on assemblies)
│   ├── Representation modes (depends on actor builder)
│   └── Opacity control (depends on assemblies)
├── StructureActorBuilder
│   ├── Ice actor creation (standalone)
│   ├── Interface actor creation (depends on ice + water splitting)
│   ├── Hydrate actor creation (depends on molecule_index parsing)
│   ├── Solute actor creation (depends on molecule_indices)
│   ├── Ion actor creation (standalone)
│   ├── Custom molecule actor creation (depends on .gro/.itp parsing)
│   └── Unit cell actor creation (standalone)
├── Camera management
│   ├── Reset on base structure change
│   ├── Preserve on downstream addition
│   └── Split-view sync (depends on SetViewport)
├── Split view
│   ├── SetViewport (depends on render window)
│   ├── Dual camera sync (depends on VTK observers)
│   └── Toggle split/single (depends on both modes)
└── 2D overlay
    ├── Layer renderer (depends on NumberOfLayers)
    ├── Text actors (depends on layer renderer)
    └── Interactive annotations (depends on picking)
```

## MVP Recommendation

For MVP (first working single-viewport), prioritize:
1. **UnifiedViewerWidget** — Single VTK widget with `vtkAssembly` groups
2. **StructureActorBuilder** — Consolidated actor creation from any structure type
3. **Visibility toggling** — Phase checkboxes in toolbar
4. **Camera management** — Smart reset vs preserve

Defer to post-MVP:
- **Split view** (SetViewport): Complex interaction routing; implement single-viewport first
- **2D overlay layer**: Polish feature; labels can be in Qt widgets initially
- **Measurement annotations**: Requires picking infrastructure
- **Opacity animation**: Nice-to-have; solid visibility toggle is sufficient

## Dual-View Replacement Decision Matrix

| Criterion | SetViewport Split | QSplitter (2 widgets) | Candidate Cycling |
|-----------|------------------|-----------------------|-------------------|
| OpenGL contexts | 1 | 2 | 1 |
| Code complexity | Medium | Low (current code) | Low |
| Mouse interaction | Needs testing | Works natively | Works natively |
| Camera sync | DeepCopy (same) | DeepCopy (same) | N/A |
| Comparison UX | Side-by-side ✅ | Side-by-side ✅ | Sequential ❌ |
| Memory overhead | Low | Medium | Low |
| **Recommendation** | **✅ Best** | Fallback | Fallback only |

## Sources

- VTK 9.5.2 API verification (direct testing in conda env)
- Current viewer codebase analysis (7 viewer files, ~3500 total lines)
- QuickIce structure type definitions (6 dataclass types with full field introspection)
- VTK rendering performance benchmarks (measured in quickice conda env)
