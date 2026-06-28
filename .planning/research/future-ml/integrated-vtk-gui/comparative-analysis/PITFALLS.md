# Domain Pitfalls: Scientific Visualization GUI Architecture

**Domain:** Scientific Visualization GUI Architecture
**Researched:** 2026-06-28

## Critical Pitfalls

Mistakes that cause rewrites or major architectural issues.

### Pitfall 1: Building a General DAG Pipeline Engine (ParaView Trap)

**What goes wrong:** You implement a fully general pipeline where any step can connect to any other step, with type checking at connections, multi-output handling, cycle detection, and dynamic reconnection. This is what ParaView does — it's appropriate for ParaView (arbitrary data analysis pipelines) but catastrophic for QuickIce (fixed 5-step linear flow).

**Why it happens:** The pipeline metaphor is powerful and seductive. "What if users want to branch?" "What if they want to compare two different solute insertions?" The DAG seems like the "right" architecture.

**Consequences:**
- 3-6 months of extra development time building the pipeline engine
- Type system complexity (what can connect to what?)
- Pipeline validation logic (cycle detection, type compatibility)
- UI complexity (how to visually represent arbitrary DAGs?)
- Performance issues (demand-driven execution is hard to implement correctly)
- Users never use the branching — they always build linear pipelines

**Prevention:** Use OVITO's model instead — a fixed-sequence modifier stack. QuickIce's flow is **always**: generate → interface → solute → ion → export. This is a linear sequence, not a DAG. Model it as a list of steps that execute in order.

**Detection:** If you find yourself writing `PipelineConnection`, `PipelineNode`, or `validate_pipeline_dag()` classes, you've fallen into this trap.

### Pitfall 2: Per-Tab VTK Render Windows (Current QuickIce Anti-Pattern)

**What goes wrong:** Each pipeline step gets its own VTK render window embedded in a separate tab. When the user switches tabs, they see a different 3D view with different camera state and different structure.

**Why it happens:** The current QuickIce architecture started as a tab-based wizard. Each tab is self-contained, so each gets its own viewer. It's the "obvious" approach.

**Consequences:**
- 5+ VTK render windows consuming memory and GPU resources
- Camera inconsistency (each tab has its own camera — users lose their viewing angle)
- Structure inconsistency (each tab shows a snapshot of its step, not the current pipeline state)
- Duplicated rendering code across tabs
- Tab switching latency (VTK renderer initialization)
- Users can't see the whole pipeline at once

**Prevention:** Single VTK render window, shared by all pipeline steps. Structure layers are separate VTK actors in one scene. The viewport always shows the complete pipeline output.

**Detection:** If you have more than one `QVTKRenderWindowInteractor` instance, you've fallen into this trap.

### Pitfall 3: Floating Tool Windows Without Docking (VMD Trap)

**What goes wrong:** Tool panels open as independent floating windows that must be manually positioned and managed by the user. VMD has 20+ such windows (Graphics, Labels, Colors, Materials, Render, Tool, etc.).

**Why it happens:** It's the simplest implementation — just `QWidget` with `show()`. No need to think about layout or docking. Each tool "owns" its window.

**Consequences:**
- Windows get lost behind other applications
- No spatial consistency between sessions
- Screen clutter on smaller monitors
- Users spend time managing windows instead of doing science
- New users are overwhelmed by the number of windows

**Prevention:** Use QDockWidget for all panels. Panels default to docked positions. Users can undock if they want (advanced users with multi-monitor setups). ChimeraX proves this pattern works.

**Detection:** If your tools create `QWidget` or `QDialog` instances that float independently of the main window, you've fallen into this trap.

### Pitfall 4: Dual Internal/External GUI (PyMOL Trap)

**What goes wrong:** One window has the 3D viewport with a minimal "internal GUI" sidebar, and a completely separate "external GUI" window has all the detailed controls, settings, and file operations.

**Why it happens:** PyMOL's historical architecture. The internal GUI was for quick display controls; the external GUI was for everything else. This made sense in 2000 when dual-monitor setups were rare.

**Consequences:**
- Users must manage two windows
- Context switching between windows disrupts workflow
- Controls in the external GUI don't clearly map to viewport state
- New users don't know where to find controls

**Prevention:** Single QMainWindow with dockable panels. All controls visible in one window.

**Detection:** If your application has two top-level windows that the user must interact with simultaneously, you've fallen into this trap.

### Pitfall 5: Syncing Multiple VTK Viewers

**What goes wrong:** You have multiple VTK render windows and try to keep their cameras, actors, and state synchronized. When the user rotates the view in one tab, all other tabs should update too.

**Why it happens:** A "compromise" approach between per-tab viewers and single viewer. "Let's keep tabs but sync the cameras!"

**Consequences:**
- Complex synchronization code
- Race conditions (which tab's camera is authoritative?)
- Performance overhead (rendering the same scene N times)
- Inevitable sync bugs (one tab drifts out of sync)
- The sync code is harder to maintain than a single viewer would be

**Prevention:** Don't have multiple viewers. One VTK render window, one set of actors, one camera. If you need different views, use VTK's multi-viewport capability within a single render window (like OVITO's 2×2 layout).

**Detection:** If you have camera synchronization code (`sync_cameras()`, `on_camera_changed` signal forwarding between viewers), you've fallen into this trap.

## Moderate Pitfalls

Mistakes that cause delays or significant technical debt.

### Pitfall 6: Implementing Full Undo for Pipeline Execution

**What goes wrong:** You implement comprehensive undo/redo that can reverse pipeline step execution, parameter changes, and structure modifications. This requires storing snapshots of the entire data pipeline state at each operation.

**Why it happens:** "Users expect undo" → "Let's make everything undoable" → massive state management system.

**Prevention:** Use OVITO's approach: pipeline steps are toggleable (non-destructive by design). Use ChimeraX's approach: limited command-based undo for parameter changes (max 10 actions, specific categories only). Don't try to undo pipeline execution — that's what the modifier stack toggle is for.

**Detection:** If you're storing full `StructureData` snapshots in an undo stack, you've over-engineered this.

### Pitfall 7: Premature Plugin API

**What goes wrong:** You design a comprehensive plugin API (like ParaView's or ChimeraX's bundle system) before the internal API is stable. Plugins break with every internal change. The plugin API constrains internal refactoring.

**Why it happens:** "Let's make it extensible!" sounds good in design documents. ChimeraX's bundle system is elegant, and it's tempting to copy it.

**Prevention:** Design for *future* plugin support by using clean internal interfaces (tool registration, pipeline step registration), but don't expose a public plugin API until the internal API has been stable for at least 2 releases. Use a simple tool registration mechanism internally:

```python
class ToolRegistry:
    _tools: dict[str, ToolDescriptor] = {}
    
    @classmethod
    def register(cls, tool: ToolDescriptor):
        cls._tools[tool.name] = tool
    
    @classmethod
    def get_tools(cls) -> list[ToolDescriptor]:
        return list(cls._tools.values())
```

**Detection:** If you're writing plugin discovery, plugin loading, or plugin versioning code before v1.0, you've fallen into this trap.

### Pitfall 8: Representation System Before Basic Rendering Works

**What goes wrong:** You spend time building a multi-representation system (cartoon, stick, sphere, surface, etc.) before the basic VTK rendering pipeline works correctly. Representations in molecular visualization tools like PyMOL and VMD are complex (cartoon requires backbone tracing, surface requires MSMS/SES computation, etc.).

**Why it happens:** "Users will want to see proteins in cartoon form" → but QuickIce builds ice crystals, not proteins. Ice crystals are just atoms on a lattice. The appropriate representation is VDW spheres and bonds — that's it.

**Prevention:** Start with simple VTK rendering (VDW spheres via `vtkSphereSource` + `vtkGlyph3D`, bonds via `vtkTubeFilter` on lines). Add fancy representations only if users request them. For QuickIce's domain, simple rendering is sufficient.

**Detection:** If you're implementing backbone tracing, secondary structure assignment, or SES computation, you've gone too far for QuickIce's domain.

### Pitfall 9: Command-Line Interface Before GUI Is Stable

**What goes wrong:** You implement a ChimeraX-style command-line interface (typed commands for all operations) before the GUI operations are well-defined. The command set becomes a maintenance burden, and every GUI operation must have a command equivalent.

**Why it happens:** ChimeraX's command line is elegant and powerful. It enables scripting, undo, and automation. But it requires that *every* GUI operation maps to a command.

**Prevention:** Defer command-line interface to a future phase. Focus on the GUI first. The CLI already exists in QuickIce (the `quickice` command-line tool). The GUI command line (ChimeraX-style in-app CLI) can come later as a polish feature.

**Detection:** If you're spending more time designing command syntax than implementing GUI features, you've fallen into this trap.

### Pitfall 10: VTK Interactor Style Fighting

**What goes wrong:** You try to use a high-level VTK wrapper (PyVista, vedo) that doesn't give you full control over interactor styles. QuickIce needs custom interactors (draw region, pick atom, measure distance) that don't fit the wrapper's assumptions.

**Why it happens:** PyVista and vedo are convenient for quick prototyping. Their `show()` methods handle interactors automatically. But when you need custom interaction modes, you must fight the wrapper's interactor management.

**Prevention:** Use raw VTK with `QVTKRenderWindowInteractor`. Implement custom `vtkInteractorStyle` subclasses for each tool mode. This is what ParaView does internally. Full control, no abstraction fighting.

**Detection:** If you find yourself accessing `plotter.renderer.GetRenderWindow().GetInteractor().SetInteractorStyle()` through PyVista's internals, you've fallen into this trap.

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 11: Fixed Panel Layout (OVITO Anti-Pattern)

**What goes wrong:** Panels are fixed in position and size. Users can't rearrange them. This works for OVITO (which has a focused workflow) but limits power users.

**Prevention:** Use QDockWidget with `AllowNestedDocks | AllowTabbedDocks`. Default positions are defined, but users can rearrange.

### Pitfall 12: No Status Bar Feedback

**What goes wrong:** Operations happen silently. Users don't know if a pipeline step is executing, succeeded, or failed.

**Prevention:** Always show status bar messages for: pipeline step execution, parameter changes, viewport updates, export operations. ChimeraX's status line is a good model.

### Pitfall 13: VTK Actor Memory Leaks

**What goes wrong:** VTK actors, mappers, and filters are created but never properly removed from the renderer. Memory grows with each pipeline re-execution.

**Prevention:** Use VTK's garbage collection (`vtk.vtkObject.GlobalWarningDisplay`). Remove all actors from renderer before adding new ones. Use `RemoveActor()` not just `SetVisibility(False)`. Keep references to actors in the StructureManager and clear them explicitly.

### Pitfall 14: Blocking GUI During Pipeline Execution

**What goes wrong:** Pipeline steps execute synchronously on the main thread. The GUI freezes during GenIce2 execution (~3-5 seconds for large structures).

**Prevention:** Already partially solved — QuickIce has `HydrateWorker` (QThread subclass). Extend this pattern to all pipeline steps. Show progress indicator. Keep viewport interactive (render cached result while new result computes).

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Viewport setup | Per-tab VTK renderers (Pitfall 2) | Enforce single `QVTKRenderWindowInteractor` |
| Panel docking | Floating windows instead of docked (Pitfall 3) | All panels must be QDockWidget |
| Pipeline model | DAG pipeline engine (Pitfall 1) | Fixed linear modifier stack only |
| Tool modes | VTK interactor fighting via wrappers (Pitfall 10) | Raw VTK interactor styles, no PyVista |
| Structure visibility | Actor memory leaks (Pitfall 13) | Explicit actor management with removal |
| Undo/redo | Full pipeline undo (Pitfall 6) | Toggle + limited command undo |
| Export | Over-engineering multi-format export | GROMACS .gro/.top/.itp only (already exists) |
| Future CLI | Premature command interface (Pitfall 9) | Defer to post-MVP |

## Sources

- ParaView User's Guide: https://docs.paraview.org/en/latest/UsersGuide/introduction.html (MEDIUM-HIGH — documents pipeline architecture clearly)
- OVITO Pipeline: https://www.ovito.org/docs/current/usage/pipeline.html (HIGH — explicit modifier stack documentation)
- ChimeraX Window/Undo: https://www.cgl.ucsf.edu/chimerax/docs/user/window.html, /commands/undo.html (HIGH — dockable panel and limited undo documented)
- VMD Windows/Mouse: https://www.ks.uiuc.edu/Research/vmd/current/ug/node38.html, /node32.html (MEDIUM — scattered window architecture is evident from docs)
- PyMOL: https://github.com/schrodinger/pymol-open-source (MEDIUM — layered architecture from repo structure)
- trame: https://kitware.github.io/trame/guide/ (HIGH — confirms web-first architecture)
- vedo: https://vedo.embl.es/ (MEDIUM — confirms scripting-oriented, no Qt integration)
