# Phase 2: Phase Mapping - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Users query with temperature (T) and pressure (P) and receive correct ice polymorph identification (e.g., ice-Ih, ice-VII). This phase delivers the T,P → polymorph lookup functionality. The phase diagram itself is a lookup table, not computed from first principles.

</domain>

<decisions>
## Implementation Decisions

### Boundary handling
- OpenCode's discretion — determine appropriate handling for T,P near phase boundaries
- May include: return primary phase, return multiple, flag as boundary, or hybrid approach

### Output richness
- OpenCode's discretion — determine what metadata to include with phase identification
- Options: phase name only, phase + density, confidence/alternatives if near boundary

### Unknown regions
- OpenCode's discretion — handle T,P outside known phase diagram or mapping to unsupported phases
- Should provide clear error messages explaining the limitation

### Error behavior
- OpenCode's discretion — error types, verbosity, recovery suggestions
- Follow Python best practices for scientific tools

### OpenCode's Discretion
All four discussion areas (boundary handling, output richness, unknown regions, error behavior) delegated to OpenCode. Implementation should follow scientific tool conventions and provide clear, helpful user feedback.

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for phase diagram lookup tools.

</specifics>

<deferred>
## Deferred Ideas

- **Phase diagram visualization** — Output 2D/3D phase diagram plot with user's T,P point marked. Useful for users to visualize where their conditions fall. Belongs in a future phase or as optional output feature.

</deferred>

---

*Phase: 02-phase-mapping*
*Context gathered: 2026-03-26*
