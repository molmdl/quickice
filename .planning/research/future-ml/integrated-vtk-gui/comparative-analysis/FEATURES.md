# Feature Comparison: Scientific Visualization GUI Tools

**Domain:** Scientific Visualization GUI Architecture
**Researched:** 2026-06-28

## Comparison Matrix

| Dimension | ParaView | VMD | OVITO | ChimeraX | PyMOL | QuickIce Target |
|-----------|----------|-----|-------|----------|-------|-----------------|
| **Viewport** | Multi-view (split) | Single OpenGL | Multi-view (2×2 default) | Single | Single | **Single** |
| **Panel Org** | QDockWidget (left+bottom) | Floating Tk windows | Fixed panels (left+right) | QDockWidget (left+right+bottom) | Fixed sidebar (right) | **QDockWidget (left+right)** |
| **Tool Modes** | Implicit (via toolbar) | Explicit (Mouse menu) | Implicit (viewport toolbar) | Explicit (Right Mouse toolbar) | Implicit (internal GUI) | **Explicit (toolbar + mode)** |
| **Pipeline Model** | DAG pipeline browser | Linear representation list | Modifier stack | Tool-based (no pipeline viz) | Object list (no pipeline) | **Linear modifier stack** |
| **Undo/Redo** | Full pipeline undo | None | Modifier toggle | Limited command undo | Limited (set undo) | **Pipeline-step undo + command undo** |
| **Export** | Per-pipeline-step save | Per-representation | Per-pipeline-step export | Per-model save | Per-object save | **Single final export (GROMACS)** |
| **Structure Visibility** | Eyeball per pipeline module | Per-molecule checkbox | Per-pipeline checkbox | Model Panel (show/hide/select) | Per-object eye icon | **Per-structure-layer checkbox** |
| **Scripting/CLI** | Python (pvpython) | Tcl + Python | Python module | Command-line interface | Python API + CLI | **Future: CLI + Python API** |
| **Plugin System** | Plugin manager + shared libs | Plugin registration at startup | Python modifiers | Bundle system (Toolshed) | C plugins + Python | **Tool registration (not full plugin)** |
| **Learning Curve** | High (pipeline concept) | High (Tcl, scattered UI) | Medium (modifier stack) | Low-Medium (toolbar + CLI) | Medium (command language) | **Target: Low-Medium** |

## Detailed Analysis by Dimension

### Viewport Management

| Tool | Pattern | Details | QuickIce Relevance |
|------|---------|---------|-------------------|
| ParaView | Split views | Tabbed/split viewport layout. Can have multiple view types (3D, 2D chart, etc.). Views share data but have independent cameras. | **Overkill.** QuickIce needs one 3D viewport. Multi-view adds complexity without benefit for structure setup. |
| VMD | Single OpenGL | One large OpenGL window. All molecules rendered in same space. Camera is global. | **Good model.** Single viewport is correct. VMD's simple approach works well. |
| OVITO | 2×2 grid (default) | Default 4 viewports (perspective + 3 orthographic). Can maximize any viewport. Per-viewport pipeline visibility. | **Use single default, keep multi-view as future option.** The 2×2 grid is useful for polycrystalline inspection but not needed at MVP. |
| ChimeraX | Single | One main graphics window. Panels dock around it. Clean and focused. | **Best model.** Single viewport + dockable panels is the exact target architecture. |
| PyMOL | Single | One viewport with internal GUI sidebar. External GUI is separate window. | **Good viewport model, bad panel model.** The single viewport is right; the sidebar is too constrained. |

**Recommendation:** Single VTK viewport (ChimeraX pattern). Add multi-view toggle later for advanced users (OVITO pattern as future option).

### Panel Organization

| Tool | Pattern | Dockable? | Contextual? | QuickIce Relevance |
|------|---------|-----------|-------------|-------------------|
| ParaView | Pipeline Browser (left) + Properties (left/bottom) | Yes (QDockWidget) | Yes (Properties changes per pipeline selection) | **Contextual properties panel is excellent.** Pipeline browser pattern is too complex for QuickIce's linear flow. |
| VMD | Separate floating windows (Graphics, Labels, Colors, Materials, etc.) | No (floating Tk) | Partial (Graphics window has tabs for rep/selection/trajectory) | **Anti-pattern to avoid.** Floating windows scatter the UI and make it hard to find controls. |
| OVITO | Pipeline editor (left) + Properties (right) | No (fixed layout) | Yes (Properties changes per pipeline selection) | **Good reference for panel layout.** Left=stack, right=properties is intuitive. But fixed layout is too rigid. |
| ChimeraX | Dockable panels on all sides + Toolbar (top) + Command Line (bottom) | Yes (QDockWidget) | Yes (panels open based on tool selection) | **Best model.** Dockable panels + toolbar + optional command line. Exactly what QuickIce needs. |
| PyMOL | Internal GUI (right sidebar, fixed) + External GUI (separate window) | No (fixed sidebar) | Partial (sections expand/collapse) | **Anti-pattern.** Dual-GUI is confusing. Fixed sidebar is too cramped. |

**Recommendation:** ChimeraX-style QDockWidget panels. Left side: pipeline/modifier stack. Right side: contextual properties. Top: toolbar. Bottom: optional log/command panel.

### Tool Mode System

| Tool | Pattern | Mode Switching | Cursor Change | QuickIce Relevance |
|------|---------|---------------|---------------|-------------------|
| ParaView | Implicit (toolbar buttons) | Click toolbar → mode changes | Minimal cursor change | **Too implicit.** Users don't know what mode they're in. |
| VMD | Explicit (Mouse menu) | Menu → Rotate/Translate/Scale/Pick/Light/Bond | Yes (distinct cursors per mode) | **Good model.** Clear mode enumeration. Hot keys (r/t/s). But the Mouse menu is buried. |
| OVITO | Implicit (viewport toolbar) | Click toolbar icons for navigation modes | Minimal | **Too focused on navigation.** No pick/query modes. |
| ChimeraX | Explicit (Right Mouse toolbar) | Toolbar tab → pick mode icon. Left mouse always rotates. | Yes | **Best model.** Separation of left (always rotate) vs right (mode-dependent) is intuitive. Toolbar makes modes discoverable. |
| PyMOL | Implicit (internal GUI) | Selection mode toggles in sidebar | Minimal | **Too buried.** Hard to discover modes. |

**Recommendation:** ChimeraX-style explicit tool modes. Left mouse = always navigate (rotate/pan/zoom). Right mouse = context-dependent mode (pick, query, draw, measure). Toolbar icons for mode selection. Hot keys for common modes.

### Data/Pipeline Model

| Tool | Model | Visual Representation | Reorder? | Toggle Steps? | QuickIce Relevance |
|------|-------|----------------------|----------|---------------|-------------------|
| ParaView | DAG pipeline | Tree browser (expandable) | No (connections are explicit) | Yes (disable modules) | **Too complex.** QuickIce has a linear 5-step flow, not an arbitrary DAG. |
| VMD | Representation list | Per-molecule rep list (Draw Style tab) | Yes (drag reps) | Yes (hide reps) | **Partial model.** VMD's rep list is for display, not data processing. |
| OVITO | Modifier stack | Linear list (bottom-up) with visual elements at top | Yes (drag reorder) | Yes (checkbox per modifier) | **Best model.** Linear, reorderable, toggleable. Matches QuickIce's generate→interface→solute→ion→export flow. |
| ChimeraX | Tool-based (no pipeline viz) | No pipeline visualization | N/A | N/A | **Not applicable.** ChimeraX is for viewing, not constructing. |
| PyMOL | Object list | Per-object list with show/hide | No | Yes (hide objects) | **Partial model.** Object management is good, but no pipeline concept. |

**Recommendation:** OVITO-style modifier stack. QuickIce's pipeline steps map directly to modifiers:
1. **Data Source:** GenIce2 crystal generation (equivalent to OVITO's "Data source")
2. **Modifier:** Interface builder
3. **Modifier:** Solute inserter
4. **Modifier:** Ion inserter
5. **Modifier (Sink):** GROMACS export

Key difference from OVITO: QuickIce's "Data Source" step *generates* data from parameters (not loads from file). This is similar to ParaView's "Sources" menu. The modifier stack should accommodate this.

### Undo/Redo

| Tool | Approach | Scope | Limitation | QuickIce Relevance |
|------|----------|-------|------------|-------------------|
| ParaView | Full pipeline undo | Can undo pipeline creation, property changes | Requires re-execution of pipeline | **Good model but heavy.** Undo in a pipeline means re-executing all downstream steps. |
| VMD | None | — | No undo at all | **Anti-pattern.** VMD's lack of undo is a known pain point. |
| OVITO | Modifier toggle | Toggle modifiers on/off (non-destructive) | No explicit undo/redo stack | **Elegant for pipeline, insufficient for interactive editing.** Modifier toggle is "soft undo" but doesn't cover parameter changes. |
| ChimeraX | Limited command undo | Undo stack (max 10 actions) for specific command categories | Only specific actions are undoable (show/hide, color, style, select, view, move) | **Pragmatic model.** Command-based undo with explicit scope. Good balance of capability and implementation effort. |
| PyMOL | Limited set undo | Undo for `set` commands only | Very narrow scope | **Too limited.** |

**Recommendation:** Hybrid approach:
1. **Modifier stack toggle** (OVITO pattern): Pipeline steps can be enabled/disabled without losing configuration. This is "structural undo" — remove ion insertion, see result, re-enable.
2. **Command-based undo** (ChimeraX pattern): For parameter changes within a step (e.g., change ion concentration), maintain a limited undo stack.
3. Don't implement full pipeline undo (ParaView pattern) — it's overkill and expensive.

### Export Workflow

| Tool | Pattern | Details | QuickIce Relevance |
|------|---------|---------|-------------------|
| ParaView | Save Data per pipeline module | Can export at any pipeline step | **Overkill.** QuickIce only needs final GROMACS export. |
| VMD | Save per representation | Coordinate saves per molecule | **Partial.** QuickIce may want to save intermediate structures for debugging. |
| OVITO | Export at any pipeline step | Can export data after any modifier | **Good model.** Being able to export intermediate results is valuable for debugging. |
| ChimeraX | Save per model | `save` command for models | **Simple and right.** |
| PyMOL | Save per object | Multiple format support | **Simple and right.** |

**Recommendation:** Export always produces final GROMACS files (.gro/.top/.itp). But also allow "Export intermediate" at any pipeline step (OVITO pattern) for debugging and validation.

### Structure Visibility

| Tool | Pattern | Multi-structure? | QuickIce Relevance |
|------|---------|-------------------|-------------------|
| ParaView | Eyeball icon per pipeline module | Yes (each source/filter is separate actor) | **Overly granular.** QuickIce has ~5 structural layers, not 50 pipeline modules. |
| VMD | Per-molecule checkbox | Yes (molecule list in main window) | **Good basic model.** But VMD doesn't separate structural layers within a molecule. |
| OVITO | Per-pipeline visibility | Yes (each pipeline can be shown/hidden per viewport) | **Good model.** Pipeline-level visibility maps well to QuickIce's structural layers. |
| ChimeraX | Model Panel (show/hide/select per model) | Yes (hierarchical models with submodels) | **Best model.** Hierarchical model list with show/hide, color wells, selection checkboxes. Very clean. |
| PyMOL | Per-object eye icon | Yes (object list in internal GUI) | **Good but limited.** Flat list, no hierarchy. |

**Recommendation:** ChimeraX-style Model Panel adapted for QuickIce's structural layers:
- **Ice lattice** (show/hide)
- **Interface region** (show/hide, color)
- **Liquid region** (show/hide, color)
- **Solute molecules** (show/hide, color per solute)
- **Ion positions** (show/hide, color by type)

### Scripting/Command Interface

| Tool | Pattern | QuickIce Relevance |
|------|---------|-------------------|
| ParaView | Python scripting (pvpython/pvbatch) + Python Shell in GUI | **Good for future.** CLI is already implemented in QuickIce. GUI should expose Python shell later. |
| VMD | Tcl + Python + console | **Reference only.** Tcl is legacy. Python is better. |
| OVITO | Python module (headless scripting) | **Good future model.** QuickIce's CLI pipeline could be exposed as a Python module. |
| ChimeraX | Command-line interface (typed commands) + Python scripting | **Best model.** Command line in the GUI is powerful. Commands map to all operations. This enables undo, scripting, and automation. |
| PyMOL | Python API + command language | **Good reference.** Command language enables automation. |

**Recommendation:** Defer to future phases. Current QuickIce CLI is sufficient. Long-term, add ChimeraX-style command interface in a bottom panel for power users.

### Plugin/Extension System

| Tool | Pattern | QuickIce Relevance |
|------|---------|-------------------|
| ParaView | Shared library plugins + plugin manager | **Overkill.** QuickIce doesn't need third-party plugin support. |
| VMD | Plugin registration at startup (C-based + Tcl/Python) | **Overkill.** VMD's plugin system is complex and error-prone. |
| OVITO | Python modifiers | **Interesting.** Users can write custom Python modifiers. But OVITO Pro is commercial. |
| ChimeraX | Bundle system + Toolshed repository | **Good future model.** ChimeraX bundles are Python packages with metadata. Toolshed is like a package manager. |
| PyMOL | C plugins + Python | **Too low-level.** |

**Recommendation:** No plugin system for MVP. Design tool registration so future plugins are possible:
- Each "tool" is a class that registers its panel, toolbar actions, and VTK interactors
- Tools are discovered at startup (similar to ChimeraX bundles but simpler)
- Future: external Python packages can register tools

## Table Stakes (Must-Have for QuickIce GUI)

| Feature | Why Expected | Complexity | Source |
|---------|--------------|------------|-------|
| Single 3D viewport with rotate/pan/zoom | Every tool has this | Low | All 5 tools |
| Show/hide structural layers | Users need to inspect sub-systems | Low | ChimeraX Model Panel |
| Toolbar with tool modes | Standard in all modern tools | Medium | ChimeraX, VMD |
| Contextual properties panel | Parameter editing is core workflow | Medium | ParaView, OVITO |
| Pipeline visualization | Users need to see build progress | Medium | OVITO, ParaView |
| Export to GROMACS | Core output requirement | Low (already exists) | QuickIce-specific |
| Camera reset/fit | Standard viewport operation | Low | All 5 tools |
| Background color control | Users expect visual customization | Low | All 5 tools |

## Differentiators (QuickIce-Specific)

| Feature | Value Proposition | Complexity | Source |
|---------|-------------------|------------|-------|
| Pipeline as modifier stack | Non-destructive editing, toggle steps | Medium | OVITO model |
| Polycrystalline region drawing | No other tool offers this | High | QuickIce-specific |
| GROMACS export integration | End-to-end workflow | Medium | QuickIce-specific |
| Real-time pipeline preview | See structure evolve as parameters change | High | OVITO model |
| Tool mode: measure distances/angles | Verify structure before export | Medium | VMD, ChimeraX |
| Tool mode: pick/query atoms | Debug structure construction | Medium | VMD pick modes |

## Anti-Features (Do NOT Build)

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| DAG pipeline builder | QuickIce has linear flow; DAG adds complexity without benefit | Linear modifier stack (OVITO) |
| Multi-view layout (default) | Most users need one viewport; splits add UI complexity | Single viewport, maximize option |
| Floating tool windows | Scattered UI, hard to manage (VMD pain point) | Dockable panels (ChimeraX) |
| Dual GUI (internal + external) | Confusing (PyMOL pain point) | Single integrated window |
| Tcl scripting interface | Legacy, not Pythonic | Python-only (already the case) |
| Representation system (cartoon/stick/sphere) | QuickIce shows atomic positions, not biomolecular representations | Simple VDW/CPK rendering + bonds |
| Animation/trajectory playback | QuickIce builds static structures, not MD trajectories | Future: if analysis suite added |
| Full plugin API (v1) | Premature abstraction; need to stabilize internal API first | Tool registration interface (internal only) |

## Sources

- ParaView User's Guide: https://docs.paraview.org/en/latest/UsersGuide/introduction.html (MEDIUM-HIGH confidence)
- OVITO Pipeline Concept: https://www.ovito.org/docs/current/usage/pipeline.html (HIGH confidence — official docs)
- OVITO Viewport Windows: https://www.ovito.org/docs/current/usage/viewports.html (HIGH confidence — official docs)
- ChimeraX Window: https://www.cgl.ucsf.edu/chimerax/docs/user/window.html (HIGH confidence — official docs)
- ChimeraX Toolbar: https://www.cgl.ucsf.edu/chimerax/docs/user/tools/toolbar.html (HIGH confidence — official docs)
- ChimeraX Model Panel: https://www.cgl.ucsf.edu/chimerax/docs/user/tools/modelpanel.html (HIGH confidence — official docs)
- ChimeraX Undo: https://www.cgl.ucsf.edu/chimerax/docs/user/commands/undo.html (HIGH confidence — official docs)
- VMD User's Guide: https://www.ks.uiuc.edu/Research/vmd/current/ug/ (MEDIUM confidence — docs are for v1.9.3, VMD 2.0 alpha underway)
- VMD Plugins: https://www.ks.uiuc.edu/Research/vmd/plugins/ (MEDIUM confidence)
- VMD Mouse Modes: https://www.ks.uiuc.edu/Research/vmd/current/ug/node32.html (MEDIUM confidence)
- PyMOL Open Source: https://github.com/schrodinger/pymol-open-source (MEDIUM confidence — repo structure reveals layered architecture)
- trame Guide: https://kitware.github.io/trame/guide/ (HIGH confidence — official docs)
- vedo: https://vedo.embl.es/ (MEDIUM confidence — website overview)
