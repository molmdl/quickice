# Research Summary: Integrated VTK-Centric GUI Redesign — Comparative Analysis

**Domain:** Scientific Visualization GUI Architecture
**Researched:** 2026-06-28
**Overall confidence:** MEDIUM-HIGH

## Executive Summary

After deep analysis of five major scientific visualization tools (ParaView, VMD, OVITO, ChimeraX, PyMOL) and three Python VTK frameworks (trame, PyVista, vedo), a clear architectural pattern emerges: **single viewport + contextual side panels + toolbar-driven modes**. Every tool except PyMOL uses this pattern. The key design decision for QuickIce is not *whether* to adopt this pattern, but *how to model the pipeline* — whether as a ParaView-style dataflow pipeline, an OVITO-style modifier stack, or a ChimeraX-style tool-shelf with command-line overlay.

The analysis strongly recommends a **hybrid model** combining OVITO's modifier-stack pipeline representation with ChimeraX's panel docking/toolbar system. ParaView's pipeline browser is architecturally elegant but overly complex for QuickIce's use case (QuickIce has a linear 5-step pipeline, not an arbitrary DAG). VMD's floating-extension pattern is the worst fit — it leads to scattered UI and lacks the cohesion of docked panels. PyMOL's dual-GUI pattern should be explicitly avoided.

For the Python VTK integration layer, QuickIce should **continue using VTK 9.5.2 directly** (already in environment) rather than adopting trame (web-first, not native desktop), PyVista (opinionated abstraction that fights VTK interactor customization), or vedo (scripting-focused, no Qt integration). The existing pattern of `QVTKRenderWindowInteractor` embedded in PySide6 is the correct approach and matches how ParaView itself integrates VTK into Qt.

## Key Findings

**Stack:** PySide6 + VTK (direct), no new framework dependencies needed. Use `QVTKRenderWindowInteractor` with custom interactor styles.
**Architecture:** Single VTK viewport + QDockWidget side panels + toolbar tool modes. Pipeline as linear modifier-stack with visual representation.
**Critical pitfall:** Don't build a general-purpose pipeline engine (ParaView trap). QuickIce's pipeline is 5 fixed steps with limited branching — model it as a fixed-sequence modifier stack, not a configurable DAG.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Viewport + Rendering Foundation** — Single VTK viewport, camera controls, basic structure rendering
   - Addresses: Core 3D visualization (FEATURES.md: viewport management)
   - Avoids: PITFALLS.md: building pipeline before viewport works

2. **Panel Framework + Docking System** — QDockWidget infrastructure, panel registration, panel switching
   - Addresses: ChimeraX-style dockable panels (ARCHITECTURE.md: panel organization)
   - Avoids: PITFALLS.md: VMD's scattered floating windows

3. **Pipeline Visualizer + Modifier Stack** — Linear pipeline display, step toggle/reorder, per-step properties
   - Addresses: OVITO-style pipeline editor (ARCHITECTURE.md: data/pipeline model)
   - Avoids: PITFALLS.md: ParaView's over-engineered DAG pipeline

4. **Tool Modes + Toolbar** — Mouse mode switching, tool registration, cursor changes
   - Addresses: ChimeraX/VMD-style tool modes (FEATURES.md: tool mode system)
   - Avoids: PITFALLS.md: PyMOL's dual-GUI confusion

5. **Structure Manager + Visibility** — Model list, show/hide per-structure, color controls
   - Addresses: ChimeraX Model Panel pattern (FEATURES.md: structure visibility)
   - Avoids: PITFALLS.md: representation explosion

6. **Undo/Redo + Session** — Command-based undo stack, session save/restore
   - Addresses: ChimeraX undo pattern (FEATURES.md: undo/redo)
   - Avoids: PITFALLS.md: VMD's no-undo limitation

**Phase ordering rationale:**
- Viewport must exist before panels can dock to it
- Panels must exist before pipeline can be visualized in them
- Pipeline visualization enables tool mode context (which tool is active depends on which pipeline step is selected)
- Tool modes require structure visibility to show their effects
- Undo/redo is a polish feature that depends on all interactive operations being in place

**Research flags for phases:**
- Phase 3 (Pipeline Visualizer): Needs deeper research on how to represent QuickIce's generate→interface→solute→ion→export flow as a modifier stack. The "generate" step creates new data (not just transforms) — this is different from OVITO.
- Phase 4 (Tool Modes): Needs research on custom VTK interactor styles for polycrystalline region drawing.
- Phase 2 (Panel Framework): Likely standard QDockWidget patterns, minimal risk.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | VTK+PySide6 already in use, no new deps needed. Verified from environment.yml |
| Features | MEDIUM-HIGH | Based on official docs for ParaView, OVITO, ChimeraX. VMD/PyMOL less thoroughly verified |
| Architecture | MEDIUM-HIGH | Common pattern across all 5 tools is clear. Specific QuickIce adaptation needs validation |
| Pitfalls | MEDIUM | Some pitfalls inferred from usage patterns, not from explicit documentation |

## Gaps to Address

- **OVITO modifier-stack + "generate new data" step:** OVITO's model assumes you import data and then transform it. QuickIce's "generate" step *creates* data from parameters. Need to decide if the generate step is a "source" (ParaView model) or a "modifier that replaces data" (OVITO model stretched).
- **VTK interactor style for region drawing:** No existing tool provides a good model for drawing arbitrary 2D/3D regions on a crystal structure. This is QuickIce-specific and needs custom implementation research.
- **Multi-structure compositing in VTK:** How to efficiently render ice lattice + interface + solutes + ions in a single VTK scene with independent visibility controls. Need to research VTK actor/mapper separation patterns.
- **trame vs native desktop:** trame was evaluated for web-first deployment. If future requirements include web/Jupyter access, trame becomes relevant. For now, native desktop is correct.
