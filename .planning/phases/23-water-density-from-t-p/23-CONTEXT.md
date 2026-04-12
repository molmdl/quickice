# Phase 23: Water Density from T/P - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Calculate and display water density from temperature and pressure using IAPWS, and apply this density to correctly space water molecules during interface generation in Tab 2. This phase does NOT include triclinic transformation (Phase 24) or CLI interface generation (Phase 25).

</domain>

<decisions>
## Implementation Decisions

### Temperature/Pressure Range Handling

- Use IAPWS for water density calculation with fallback when out-of-range or NaN
- Research required: Determine appropriate fallback value when IAPWS fails (investigate standard condition density, melting point density, linear extrapolation, or simple 1.0 g/cm³)
- Research required: Determine appropriate pressure range to support (investigate fixed 1 atm, user input, or derive from ice phase)
- OpenCode's Discretion: How to inform user when fallback is used (silent logging, UI indicator, or warning dialog)
- Constraint: Fallback must be explicitly documented with scientific justification

### Interface Generation Workflow

- Water density calculated automatically from ice temperature (no separate T/P controls for water)
- If fallback density is used during generation: same fallback behavior as display, but with additional logging in generation output
- OpenCode's Discretion: When to calculate density during Tab 2 workflow (on-demand, pre-calculated with ice, or real-time)
- OpenCode's Discretion: Whether water density is visible/editable in UI or purely internal calculation

### Research Required

- How to generate water coordinates with target density (this is the key implementation question for interface spacing)
- Scientific basis for fallback density value when IAPWS fails
- Valid pressure range for water density calculations

</decisions>

<specifics>
## Specific Ideas

- User noted: "its more challenging for density below melting point to model liquid phase" - this is the core challenge for ice-water interfaces at sub-freezing temperatures
- Water density should use the same temperature as ice generation (unified temperature control)
- Fallback density needs explicit documentation and scientific justification

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope

</deferred>

---

*Phase: 23-water-density-from-t-p*
*Context gathered: 2026-04-12*