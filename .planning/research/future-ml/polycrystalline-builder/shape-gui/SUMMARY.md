# Research Summary: Interactive Shape GUI for Polycrystalline Builder

**Domain:** Scientific GUI / Interactive region editor for molecular simulation setup
**Researched:** 2026-06-28
**Overall confidence:** HIGH (for technology choices) / MEDIUM (for UX workflow — needs user validation)

## Executive Summary

Building an interactive shape editor for defining phase regions (liquid, hydrate, ice) in a rectangular simulation box requires a **hybrid 2D drawing + 3D visualization** approach. The recommended architecture is a **QGraphicsView-based 2D shape editor** on the left panel coupled with a **VTK 3D preview** on the right, using **shapely 2.5D polygons** (2D polygon + Z extrusion range) as the internal data model. This leverages QuickIce's existing PySide6, VTK, and shapely dependencies without adding new packages.

The 2D shape editor uses Qt's Graphics View Framework (QGraphicsView/QGraphicsScene/QGraphicsItem) — the gold standard for interactive 2D shape editing in Qt applications. It provides built-in item selection, move/resize, rubber-band selection, zoom/pan, and QUndoStack integration. The 3D VTK viewer renders a translucent preview of the defined regions overlaid on the box wireframe, giving spatial context.

The **2.5D approach** (draw 2D cross-sections on XY plane, extrude along Z) is recommended over full 3D primitive placement because: (1) it maps directly to how scientists think about slab/pocket interfaces, (2) 2D drawing is far more responsive and precise than 3D widget manipulation, (3) it matches QuickIce's existing interface modes (slab = full XY extrusion, pocket = circular region extruded along Z), and (4) it avoids the complexity of VTK 3D widget interaction for arbitrary shapes.

## Key Findings

**Stack:** QGraphicsView (2D drawing) + VTK QVTKRenderWindowInteractor (3D preview) + shapely (geometry model) + QUndoStack (undo/redo). No new dependencies needed.
**Architecture:** Two-panel layout (2D editor | 3D preview) inside a new tab. Shape data model uses shapely Polygon + Z-range. Phase assignment via combo box per region.
**Critical pitfall:** 2D↔3D coordinate synchronization — the 2D editor must stay synchronized with the 3D preview's camera perspective and box dimensions. Getting the coordinate mapping wrong will make regions appear in wrong positions.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Data model + shape primitives** — Build the PhaseRegion dataclass (shapely Polygon + Z-range + phase type), serialization, and the basic shape primitives (rectangle, ellipse, polygon). No GUI yet.
   - Addresses: Need a clean data model before any GUI work
   - Avoids: Building GUI against a half-baked data model (refactoring nightmare)

2. **QGraphicsView 2D shape editor** — Build the 2D drawing canvas with shape creation, selection, move, resize, delete. QUndoStack integration.
   - Addresses: Core editing functionality
   - Avoids: Scope creep from trying to add 3D editing first

3. **VTK 3D region preview** — Render defined regions as translucent VTK actors in the 3D viewer alongside the box wireframe.
   - Addresses: Spatial validation of defined regions
   - Avoids: Users defining regions they can't visualize in context

4. **Phase assignment + region list** — UI for assigning phase types to regions, region list panel, overlap detection (using shapely).
   - Addresses: The actual purpose of the shape editor
   - Avoids: Building assignment UI before regions can be edited

5. **Multi-slice Z editing** — Allow defining shapes at multiple Z heights with interpolation.
   - Addresses: Complex 3D geometries
   - Avoids: Over-engineering the first version

**Phase ordering rationale:**
- Data model first because all GUI components depend on it
- 2D editor before 3D preview because 2D is the primary interaction mode
- Phase assignment after shape editing because assignment needs a stable editor
- Multi-slice is an enhancement, not MVP

**Research flags for phases:**
- Phase 2 (QGraphicsView editor): Standard Qt patterns, unlikely to need deep research
- Phase 3 (VTK 3D preview): May need research on translucent region rendering performance with many overlapping shapes
- Phase 5 (Multi-slice): Needs UX research — how do scientists want to specify Z-varying geometry?

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries verified in environment.yml; PySide6 QGraphicsView, VTK, shapely all proven technology |
| Features | HIGH | Clear table stakes from domain; differentiators are well-understood |
| Architecture | HIGH | Hybrid 2D+3D is a proven pattern (napari, ParaView slice views) |
| Pitfalls | MEDIUM | Some pitfalls are known from domain; 2D↔3D sync complexity is estimated but not yet experienced |
| UX workflow | MEDIUM | 2.5D approach is technically sound but may not match all user mental models — needs validation |

## Gaps to Address

- **User validation:** Do QuickIce users prefer 2D cross-section editing or 3D primitive placement? Research assumes 2D-first but this needs confirmation.
- **Multi-slice UX:** How many Z-slices do users need? Is simple Z-range extrusion sufficient for most cases, or do complex geometries (e.g., tapered pores) require slice interpolation?
- **Performance:** How many regions can shapely handle in real-time overlap detection before it becomes slow? (Likely fine for <100 regions but untested)
- **Phase constraint validation:** Some phase combinations are invalid (e.g., hydrate sI directly touching ice Ih without a liquid layer). Need to define validation rules.
