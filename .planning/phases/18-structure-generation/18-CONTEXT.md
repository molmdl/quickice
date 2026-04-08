# Phase 18: Structure Generation - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Interface structures are correctly generated with ice and water phases assembled according to mode (slab, pocket, piece). Ice comes from GenIce2 via selected candidate (Tab 1), water from bundled tip4p.gro. Overlap resolution and periodic boundary conditions are handled. This phase delivers the generation logic, not the UI or visualization.

</domain>

<decisions>
## Implementation Decisions

### Piece mode shape
- Shape decision deferred to research: investigate what shapes (box, sphere, cylinder) are common in scientific ice-in-water simulation literature before deciding
- MVP ships with box/cube shape; non-box shapes (sphere, cylinder) considered based on research findings
- If research shows box-only is standard practice, ship box-only for v3.0
- Ice piece dimensions: derived from selected candidate by default (OpenCode discretion on exact derivation logic)

### Overlap resolution
- Detection: Distance-based — flag any O-O pair closer than threshold
- Resolution: Remove overlapping water atoms only; ice structure is always preserved intact
- Threshold: Default 2.5 Å (O-O distance), user can override — careful about unit consistency (use angstroms)
- Feedback: OpenCode discretion — report final atom counts after generation (analogous to gmx solvate reporting molecules added, not removed)

### Generation failure behavior
- Validation timing: Pre-generation validation — check all constraints before starting generation. Fail fast with clear error.
- Error display: OpenCode discretion
- Partial results: OpenCode discretion
- Error detail: OpenCode discretion

### Slab mode orientation
- Layer order: Ice-water-ice sandwich (ice above and below water layer). Symmetric, standard in MD simulations, prevents water-vacuum interface.
- Symmetry: User can set different ice thickness for top and bottom layers (allow asymmetric configurations)
- Water density: Fill middle region from bundled tip4p.gro structure, then trim overlapping molecules (gmx solvate-like approach)
- Boundary plane: OpenCode discretion (Z-axis stacking is standard for MD)

</decisions>

<specifics>
## Specific Ideas

- gmx solvate behavior as reference: investigate how gmx solvate works in liquid phase generation — its fill-and-trim approach should inform our water placement logic
- gmx solvate reports molecules added, not removed — follow similar reporting pattern for our overlap resolution feedback
- Pocket and piece mode water filling should use the same tip4p.gro fill-and-trim approach as slab mode

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 18-structure-generation*
*Context gathered: 2026-04-08*