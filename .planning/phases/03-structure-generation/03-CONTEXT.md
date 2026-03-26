# Phase 3: Structure Generation - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate valid ice structure coordinates via GenIce integration. Takes phase identification from Phase 2 and produces 10 candidate structures for ranking in Phase 4. Core transformation: phase → atomic coordinates.

</domain>

<decisions>
## Implementation Decisions

### Candidate diversity
- OpenCode's discretion with rationale required during planning
- Consider: same-phase variations, seed-based diversity, minimum candidate requirements

### Supercell sizing
- Round up to nearest valid supercell when nmolecules doesn't fit exactly
- User is informed when adjustment occurs (format: OpenCode's discretion)
- Supercell multiplier strategy: OpenCode's discretion
- Lower bound handling (nmolecules < minimum viable): OpenCode's discretion

### GenIce failures
- Fail fast for unsupported phases (no fallback to similar phases)
- Reject and explain for invalid nmolecules/phase combinations
- Error message format: OpenCode's discretion
- Retry logic for transient failures: OpenCode's discretion

### Structure storage
- In-memory only (no temp files or persistent cache)
- Intermediate format: OpenCode's discretion
- Metadata fields to include: OpenCode's discretion
- Organization of 10 candidates: OpenCode's discretion

### Dependencies
- GenIce already in env.yml (genice2==2.2.13.1, genice-core==1.4.3)
- spglib==2.7.0 added to env.yml (needed for Phase 5 space group validation)

</decisions>

<specifics>
## Specific Ideas

- GenIce handles hydrogen bond network generation (ensures exactly 4 H-bonds per molecule)
- 10 candidates per query is fixed requirement from ROADMAP
- No physics simulation — GenIce provides valid coordinates, ML/vibe handles ranking

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-structure-generation*
*Context gathered: 2026-03-26*
