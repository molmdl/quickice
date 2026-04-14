# Phase 28: Pre-requisite Fixes - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 4 pre-existing bugs that block v4.0 development:
- Pitfall #7: GenIce2 numpy random state restoration
- Pitfall #15: Temperature/Pressure metadata storage
- Pitfall #16: GRO parser deduplication
- Pitfall #21: is_cell_orthogonal() unification

</domain>

<decisions>
## Implementation Decisions

### Fix Philosophy
- All fixes must be internal-only, no changes to any existing API contracts
- No changes to output format, error messages, or any user-facing behavior
- Existing functions must continue to work exactly as before

### OpenCode's Discretion
- Test approach (unit vs integration vs both)
- Specific implementation patterns to avoid regressions
- Whether to add regression tests

</decisions>

<specifics>
## Specific Ideas

- "Just do without affecting any current functions" — user emphasized zero user-facing changes

</specifics>

<deferred>
## Deferred Ideas

None — Phase 28 scope is pure internal fixes, no user-facing features

</deferred>

---

*Phase: 28-pre-requisite-fixes*
*Context gathered: 2026-04-14*