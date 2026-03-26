# Phase 4: Ranking - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Rank 10 ice structure candidates by relevance to user's T,P conditions. Candidates come from Phase 3 (GenIce output). Ranking produces ordered list with scores for use in Phase 5 output.

</domain>

<decisions>
## Implementation Decisions

### OpenCode's Discretion

User delegated all ranking decisions to OpenCode with reasoning:

1. **Scoring methodology** — How energy, density, and diversity combine
   - Recommendation: Weighted sum approach with documented weights
   - Consider: Equal weights as baseline, or density-weighted given T,P input context

2. **Energy calculation** — How to estimate or calculate energy
   - Options: Skip energy, estimate from H-bond geometry, or investigate GenIce output
   - Recommendation: Investigate GenIce capabilities first; if unavailable, estimate from H-bond network quality

3. **Diversity definition** — What counts as diverse
   - Options: Different polymorphs only, structural variety within phase, or ignore diversity
   - Recommendation: Different polymorphs as primary diversity metric

4. **Score presentation** — How to display ranking to user
   - Options: Full breakdown, rank only, or combined score only
   - Recommendation: Combined score + individual components for transparency

### Locked Constraints

From ROADMAP.md success criteria:
- Candidates ranked by energy (lower preferred)
- Candidates scored by density match to expected density at T,P
- Diversity scoring rewards different polymorphs
- Combined ranking score available for each candidate

</decisions>

<specifics>
## Specific Ideas

- "Pure vibe coding" project — ranking doesn't need physics simulation precision
- Pragmatic approach acceptable: reasonable heuristics over scientific accuracy
- Scores should be interpretable for debugging/understanding

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-ranking*
*Context gathered: 2026-03-27*
