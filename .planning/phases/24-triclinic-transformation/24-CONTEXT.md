# Phase 24: Triclinic Transformation Service - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable interface generation for all ice phases including non-orthogonal phases (Ice II, V, VI) that were previously rejected. The transformation converts triclinic unit cells to orthogonal representation while preserving crystal structure. Detection, transformation, and validation happen automatically within Tab 1 when a triclinic phase is selected. The transformed cells must work seamlessly with Tab 2's interface builder.

</domain>

<decisions>
## Implementation Decisions

### Detection Strategy
- Strict 0.1° tolerance for defining "orthogonal" (cell angles α, β, γ must be 90° ± 0.1°)
- Cells outside this tolerance are considered triclinic and trigger transformation
- Already-orthogonal phases (Ih, Ic, III, VI, VII, VIII) skip transformation without errors

### Validation Rigor
- Full validation with internal consistency checks after transformation:
  - Density preservation (compare before/after)
  - Coordination numbers unchanged
  - Bond lengths and angles within tolerance
- No need to compare against published reference structures — internal consistency is sufficient

### Error Handling & Retry
- On transformation failure, retry with different molecule counts to satisfy new cell type
- Research existing nmol auto-adjustment logic (possibly via spglib) and adapt for transformation
- If retries exhausted, reject with clear error message

### Integration Point
- Transformation happens automatically in Tab 1 (Ice Generation) when a triclinic phase is selected
- User does not manually trigger transformation — it's transparent to the workflow
- Transformed cell is then available for Tab 2 (Interface Construction)

### User Feedback
- Show transformation status in Tab 1 (e.g., "Ice II: Cell transformed from triclinic")
- Include retry count if applicable (e.g., "transformed (3 retries)")
- User knows what happened but doesn't need to intervene

### Key Constraint
- Transformed cells MUST work with Tab 2's interface builder (piece.py validation, slab/pocket/piece modes)
- This is the success criterion: user can generate interfaces for Ice II, V, VI without errors

</decisions>

<specifics>
## Specific Ideas

- Leverage existing nmol auto-adjustment logic (research how this works — possibly via spglib)
- The transformation is a means to an end: enable interface generation for all phases
- User experience should feel seamless — select phase, get working structure

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

<open_questions>
## Research Needed

1. **How does current nmol auto-adjustment work?**
   - Is it via spglib?
   - What's the algorithm for finding valid supercell multipliers?
   - Can this logic be adapted for triclinic-to-orthogonal transformation?

2. **What transformation algorithm should be used?**
   - Standard crystallographic transformation matrices?
   - Supercell approach (multiply cell to approximate orthogonal)?
   - Metric tensor approach?

3. **Where exactly in Tab 1 should transformation trigger?**
   - During ice generation (in the worker thread)?
   - As a post-processing step?
   - Integrated into existing GenIce2 flow?

</open_questions>

---

*Phase: 24-triclinic-transformation*
*Context gathered: 2026-04-12*
