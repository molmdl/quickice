# Phase 26: Integration & Polish - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Ensure all v3.5 features work together correctly: piece.py validation allows transformed triclinic cells, GROMACS export produces valid files for all interface types, GUI displays density values correctly, and integration tests pass for end-to-end workflows. This is a cross-cutting validation phase — no new features, only verification and fixes.

</domain>

<decisions>
## Implementation Decisions

### Test Coverage Scope

**Rationale:** Test the critical paths that involve new v3.5 features, not every possible combination. Focus on triclinic phases (the main new capability) plus one baseline orthogonal phase.

- **Ice phases to test:** Ice II, Ice V, Ice VI (triclinic — primary new capability) + Ice Ih (baseline orthogonal)
- **Interface modes to test:** All 3 modes (slab, pocket, piece) — piece is critical since it had orthogonal-only validation
- **Workflows to test:** CLI generation, GUI display verification (both tabs), GROMACS export
- **Not testing:** Every temperature/pressure combination — density modules already have unit tests

### Verification Approach

**Rationale:** Automate what can be programatically verified; human verification for visual/GUI elements. Keep test count low but meaningful.

- **Automated tests:** GROMACS file validity (atom count, box dimensions, coordinate ranges), CLI parameter validation, transformation detection logic
- **Human verification:** GUI density display correctness, visual inspection of generated structures, end-to-end workflow sanity check
- **No automated GUI tests:** Not worth the complexity for a desktop app — manual verification is sufficient

### Edge Cases to Test

**Rationale:** Test the failure modes that users might actually encounter, not hypothetical edge cases.

- **Out-of-range temperature:** IAPWS fallback returns 0.9167 g/cm³ (already implemented, verify it works)
- **Invalid CLI parameters:** Missing required params for interface mode, invalid pocket shape
- **File overwrite:** CLI prompt behavior (already implemented in 25-02)
- **Transformation failure:** Non-orthogonal cell that can't be transformed (should not happen with supported phases, but test graceful error handling)

### Integration Test Structure

**Rationale:** Follow existing patterns. Don't create new test structure unless necessary.

- **Add to existing test files:** Test interface generation in existing `test_*.py` files where appropriate
- **New integration test file:** `tests/test_integration_v35.py` for end-to-end workflows that span multiple components
- **Test naming:** `test_integration_<feature>_<scenario>` (e.g., `test_integration_triclinic_ice2_slab`)

### OpenCode's Discretion

- Exact test assertion tolerances (coordinate precision, density decimal places)
- Test fixture organization (inline vs separate files)
- Whether to parametrize tests or write separate test functions
- Error message wording in test failures

</decisions>

<specifics>
## Specific Ideas

- "Integration tests should catch what unit tests miss" — focus on component interactions, not isolated functions
- Run tests on real GenIce2-generated structures, not mock data
- Each integration test should exercise a complete user workflow from start to finish

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope (validation and testing only)

</deferred>

---

## Human Verification Required

After automated tests pass, verify manually:

| # | Verification | How |
|---|--------------|-----|
| 1 | Ice Ih density displays correctly in Tab 1 | Generate Ice Ih, check density value in info panel (should be ~0.92 g/cm³ at 250K) |
| 2 | Water density displays correctly in Tab 1 | Select Liquid phase, check density value (should be ~1.0 g/cm³ at 273K) |
| 3 | CLI interface generation produces valid GROMACS files | Run `quickice --interface --mode slab --ice-phase Ih --nmolecules 100`, open .gro file, verify structure |
| 4 | Triclinic phases (Ice II, V, VI) generate without errors | Generate interface with each triclinic phase, verify no transformation errors |
| 5 | Piece mode accepts triclinic cells | Generate Ice II piece mode interface, verify it works (was previously rejected) |

---

*Phase: 26-integration-polish*
*Context gathered: 2026-04-12*
