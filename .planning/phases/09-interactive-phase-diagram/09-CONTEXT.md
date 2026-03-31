# Phase 9: Interactive Phase Diagram - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can visually select thermodynamic conditions by clicking on an interactive phase diagram. The diagram displays the 12 ice phases with labeled regions. Clicking sets temperature and pressure coordinates, shows a marker, and displays the phase name. This phase delivers the interactive visualization component — structure generation and 3D viewing are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Diagram Layout & Positioning
- Split view (fixed): Diagram always visible alongside input panel in main window
- Temperature on X-axis (0-500 K), Pressure on Y-axis (0-10000 bar)
- Fixed minimum size (~400x300px) that fits all 12 phases legibly
- Full labels: axis labels (T, P), units (K, bar), and title "Ice Phase Diagram"

### Interaction Mechanics
- Single click to set position: click places marker, click again repositions
- Crosshair cursor appears when hovering over entire diagram area
- Boundary clicks show indicator: "Multiple phases possible" when clicking on phase boundary lines
- Live tooltip showing T, P coordinates while hovering (before click)

### Visual Rendering Style
- Filled regions with subtle color palette: light pastel fills with clear boundary lines (publication-style)
- Phase labels: short names (Ih, II, III, etc.) as in current diagram implementation
- Grid/ticks: follow current diagram style (ticks only, no grid lines)
- Color scheme: scientific publication style — distinguishable for colorblind users, grayscale-printable

### Selection Feedback
- Marker style: crosshair cursor while hovering, small circle marker (5-8px) when clicked
- Phase name display: status bar or dedicated info panel below diagram (not tooltip)
- No region highlighting: only the marker indicates selection point
- Single marker: clicking moves marker to new position (one marker at a time)

### OpenCode's Discretion
- Exact marker circle size and color
- Precise pastel color values for each phase
- Info panel layout and formatting
- Tooltip styling and delay timing

</decisions>

<specifics>
## Specific Ideas

- Match existing phase diagram rendering from v1.x CLI where applicable
- Labels use short form (Ih, II, III, etc.) not full names (Ice Ih, Ice II, etc.)
- Coordinates should populate the existing temperature/pressure input fields from Phase 8

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-interactive-phase-diagram*
*Context gathered: 2026-03-31*
