# Phase 10: 3D Molecular Viewer - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can view and interact with generated ice structures in a 3D VTK viewport with ball-and-stick/stick representations, hydrogen bond visualization, unit cell box, camera controls, auto-rotation, and side-by-side comparison of multiple candidates with property-based coloring.

</domain>

<decisions>
## Implementation Decisions

### Viewport placement
- Stacked vertical layout: phase diagram remains on left, 3D viewer appears below inputs after generation
- Placeholder text "Click Generate to view structure" shown before first generation
- Viewer area fills available space with flexible sizing (standard Qt behavior)
- Auto-fit and auto-orient on load for best initial view

### Visual defaults
- CPK standard colors: Oxygen = red (#FF0000), Hydrogen = white (#FFFFFF)
- VdW-proportional ball sizes: Oxygen ~1.27× larger than Hydrogen
- Hydrogen bonds: thin dashed lines between molecules (line style at OpenCode discretion)
- Unit cell: wireframe box with subtle gray edges, non-intrusive

### Controls & interaction
- Toolbar directly above 3D viewport (not main toolbar)
- Essential buttons visible: Ball-and-stick/Stick toggle, H-bonds toggle, Zoom-fit
- Other controls in context menu or dropdown: Unit cell toggle, Auto-rotate, Color-by-property
- Auto-rotation: slow & smooth (~10°/sec), presentation quality
- Color-by-property: dropdown selector - 'None (CPK)', 'Energy ranking', 'Density ranking'

### Comparison layout
- Always dual view after generation (1 row, 2 grids)
- Each grid has dropdown to manually select which candidate to display
- Default: Grid 1 shows rank #1, Grid 2 shows rank #2
- Synchronized cameras: rotate/zoom in one mirrors the other for easy comparison

### Info panel
- Collapsible panel below/beside viewports
- Shows full generation log output (like CLI stdout)
- Collapsed by default - user expands when needed

### OpenCode's Discretion
- Exact atom ball radii values (within VdW proportionality)
- Hydrogen bond line thickness and dash pattern
- Default camera orientation angle
- Auto-rotation implementation details
- Info panel exact positioning and sizing
- Colormap for property-based coloring (viridis or similar scientific standard)

</decisions>

<specifics>
## Specific Ideas

- "Simple, 1 row 2 grids, dropdown manual to select which model to display in which grid"
- "Area to display logs/candidate information/state information (e.g. those info displayed in STDOUT in a CLI run)"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

<dependencies>
## Required Dependency

- VTK >= 9.6.0 (BSD-licensed, MIT-compatible) — **added to env.yml**

</dependencies>

---

*Phase: 10-3d-molecular-viewer*
*Context gathered: 2026-04-01*
