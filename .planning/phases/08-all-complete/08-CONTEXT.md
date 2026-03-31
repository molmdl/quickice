# Phase 8: GUI Infrastructure + Core Input - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can enter temperature, pressure, and molecule count parameters and trigger ice structure generation with progress feedback through a PySide6 GUI. This phase delivers the foundational GUI infrastructure: main window, input panel with validation, generate/cancel controls, and progress feedback. Phase diagram selection and 3D viewer are separate phases (9 and 10).

</domain>

<decisions>
## Implementation Decisions

### Window Layout
- Input fields arranged vertically (stacked form) — temperature, then pressure, then molecule count
- Note: Phase diagram click (Phase 9) will autofill these fields
- Generate and Cancel buttons positioned below inputs (Generate prominent, Cancel secondary)
- Labels above each input field (e.g., "Temperature (K):") — accessible and explicit
- Layout should accommodate future expansion for phase diagram and 3D viewer panels
- OpenCode's discretion: progress area placement (separate panel vs inline), window framing/grouping style, default window size and resizability

### Input Validation UX
- Validation errors appear on submit (when Generate clicked), not real-time
- Inline error messages below each field (red text contextual to invalid input)
- Generate button disabled when inputs are invalid
- OpenCode's discretion: error message style (technical vs friendly tone)

### Progress Feedback
- High-level status stages: "Generating...", "Ranking...", "Complete"
- Progress bar shows percentage only, no time estimates
- Success message appears briefly, then clears to keep UI clean
- OpenCode's discretion: Cancel button responsiveness during generation

### Error Presentation
- Modal dialog for generation failures — ensures user sees error
- No persistent error logging — show error and move on (simplest for MVP)
- OpenCode's discretion: technical detail level in errors, input field state after error (keep values vs highlight problem vs clear invalid)

### OpenCode's Discretion
- Progress area placement (separate panel below, integrated inline, or status bar)
- Input panel framing (subtle border, clean minimal, or titled group box)
- Default window size and resizability policy
- Error message tone (technical vs friendly)
- Cancel button responsiveness behavior
- Technical detail in error dialogs (summary vs full details vs expandable)
- Input field state after error (keep values, highlight problem, or clear invalid)

</decisions>

<specifics>
## Specific Ideas

- Input fields will be autofilled when user clicks on phase diagram (Phase 9 feature)
- Layout should be designed with future panels in mind (phase diagram, 3D viewer)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-gui-infrastructure-core-input*
*Context gathered: 2026-03-31*
