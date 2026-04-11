# Phase 22: Ice Ih IAPWS Density - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Display temperature-dependent Ice Ih density calculated via IAPWS equation of state, replacing the hardcoded 0.9167 g/cm³ value. Users can view accurate density that varies with temperature. Other ice phases continue using fixed density values.

</domain>

<decisions>
## Implementation Decisions

### Display Location
- Density appears in the existing info panel density line (no new UI elements)
- No change to phase diagram bottom box
- Tab 1 only (Ice Generation tab)

### Temperature Source
- Use existing temperature flow: phase diagram click → synced with temperature input
- Do not alter current information sync mechanism
- Temperature already flows correctly through existing system

### Display Format
- Match existing density line format in info panel
- Match existing decimal precision
- No IAPWS source indicator needed (clean, minimal)
- Units: g/cm³ (existing)

### Warning Update
- Update existing warning about "same density for whole Ih"
- New message: Only Ice Ih allows temperature-dependent density
- Clarifies that other ice phases use fixed density values

### Edge Case Handling
- If IAPWS fails (temperature within Ice Ih region but outside IAPWS valid range): use fallback value
- Fallback approximately 0.917 g/cm³ (the old hardcoded value)
- Prevents NaN/invalid display while maintaining usability

### Scope
- Ice Ih only: Only Ice Ih uses IAPWS-calculated density
- Other ice phases continue with fixed density values
- Future phases may add IAPWS for other phases if data becomes available

### OpenCode's Discretion
- Exact fallback value (~0.917 g/cm³)
- Exact warning message wording
- IAPWS range validation implementation details

</decisions>

<specifics>
## Specific Ideas

- "Match existing format" — follow current info panel density display style
- "All currently synced, don't alter current info" — preserve existing temperature flow
- Fallback only when IAPWS fails within Ice Ih region, not for user errors

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 22-ice-ih-iapws-density*
*Context gathered: 2026-04-12*
