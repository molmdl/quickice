# Phase 17: Configuration Controls - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can configure interface generation parameters through intuitive UI controls on Tab 2 (Interface Construction). Controls include: mode selection (slab/pocket/piece), box size inputs, mode-specific parameter inputs, and random seed. This phase delivers the control panel only — structure generation, visualization, and export are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Box size inputs
- Three separate X/Y/Z dimension inputs (not single cubic value)
- All modes (slab, pocket, piece) use X/Y/Z box inputs — consistent across modes
- Slab interfaces commonly use long rectangular boxes (not cubic), but cubic must still be possible
- OpenCode's discretion on default X/Y/Z values

### Tab 2 layout
- Controls on top, full-width VTK viewer below (no phase diagram like Tab 1)
- Full-width viewer shows the long rectangular box clearly
- VTK viewer is blank until user generates a structure
- Only one tab's viewport active at a time — disable inactive tab's VTK to save resources (Tab 2 rendering can be heavy)

### Mode-dependent layout switching
- OpenCode's discretion on how controls swap when switching modes (instant, show/hide, etc.)
- OpenCode's discretion on control placement and grouping of mode-specific vs shared inputs
- OpenCode's discretion on whether previously entered values persist when switching modes
- OpenCode's discretion on mode selector widget type (dropdown, radio buttons, segmented button)

### Input validation & feedback
- OpenCode's discretion on validation timing (live, on focus loss, on generate)
- OpenCode's discretion on error display style (red border+tooltip, inline text)
- OpenCode's discretion on whether Generate button disables on invalid input
- OpenCode's discretion on range limits (hard spin box limits, soft warnings, or no limits)

### Default values & ranges
- OpenCode's discretion on whether recommended ranges are shown (tooltips, inline labels, or none)
- OpenCode's discretion on default slab mode ice/water thickness values
- OpenCode's discretion on whether box size auto-calculates from layer thicknesses
- OpenCode's discretion on slab stacking direction (Z-axis convention vs user choice)

### Control density & grouping
- OpenCode's discretion on grouping (shared top + mode-specific below, single form, etc.)
- OpenCode's discretion on form style (label-left or stacked label-above)
- OpenCode's discretion on visual separation between shared and mode-specific params
- OpenCode's discretion on control panel compactness vs standard form height
- Match Tab 1's general widget/spacing style but adapt layout for Tab 2's different inputs and full-width viewer

</decisions>

<specifics>
## Specific Ideas

- "Slab interface usually uses a long rectangular box, not cubic — but cubic should still be possible"
- "Make the whole bottom panel the viewport since Tab 2 has no phase diagram — show the long rectangular box clearly"
- "Only enable viewports in one tab at a time to save resources"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 17-configuration-controls*
*Context gathered: 2026-04-08*
