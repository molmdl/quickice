# Phase 19: Visualization - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Display ice-water interface structures in 3D with clear visual distinction between ice and water phases. Uses the same VTK viewer approach as Tab 1 but adapted for two-phase structures. Visualization confirms structure correctness before export.

</domain>

<decisions>
## Implementation Decisions

### Color scheme
- Ice-phase atoms render in cyan
- Water-phase atoms render in slate blue or cornflower blue — whichever contrasts better with cyan on dark background and is most readable
- O vs H distinction within each phase: OpenCode's discretion
- Bond coloring: OpenCode's discretion

### Rendering style
- Hydrogen bonds are HIDDEN in Tab 2 — too messy with water present. Users view hydrogen bonds in Tab 1's ice visualization instead (overrides VIS-04)
- Atom rendering: OpenCode's discretion — consider that interface structures have many atoms
- Large system simplification: OpenCode's discretion — may simplify rendering above a threshold if needed for performance
- Covalent bonds: OpenCode's discretion — lines per VIS-02, thickness at OpenCode's discretion

### Viewer interaction
- Default camera: side view along Z-axis (slab stacking direction) when structure loads
- Background: dark (VTK default)
- Reset camera: OpenCode's discretion
- Whether Tab 2 shares Tab 1's VTK viewer or has its own: OpenCode's discretion

### Empty & loading states
- Before generation: placeholder text overlay (e.g., "Generate a structure to visualize")
- During generation: OpenCode's discretion
- On generation failure: OpenCode's discretion
- Auto-update on completion: auto-update is fine, no special transition needed — OpenCode's discretion on transition style

### OpenCode's Discretion
- Oxygen vs hydrogen atom visual distinction within phases
- Bond line color and thickness
- Atom rendering approach (spheres vs points) and size
- Performance threshold for rendering simplification
- Reset camera implementation (button, shortcut, or both)
- Whether Tab 2 shares Tab 1's VTK widget or has its own
- Loading/error state visual design
- Smooth transition vs instant update on generation complete

</decisions>

<specifics>
## Specific Ideas

- Water atoms should be slate blue or cornflower blue — whichever contrasts best with cyan ice on a dark background
- Default view should be along Z-axis (side view) so the slab stacking is immediately visible
- Hydrogen bonds deliberately excluded from Tab 2 — water makes them too messy, users can see them in Tab 1

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 19-visualization*
*Context gathered: 2026-04-09*