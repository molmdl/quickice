# Codebase Concerns

**Analysis Date:** 2026-03-28

## Tech Debt

**Phase Diagram Polygon Definitions:**
- Issue: Phase polygons defined with hardcoded vertices instead of dynamically computed from boundary curves
- Files: `quickice/output/phase_diagram.py`, `quickice/phase_mapping/solid_boundaries.py`
- Impact: Gaps and overlaps in phase diagram visualization; potential incorrect phase lookup
- Fix approach: Use boundary curve functions dynamically to compute polygon vertices at render time

**Large Monolithic File:**
- Issue: `quickice/output/phase_diagram.py` contains 847 lines with multiple responsibilities
- Files: `quickice/output/phase_diagram.py`
- Impact: Hard to maintain, test, and modify; mixed concerns (polygon building, matplotlib rendering, data)
- Fix approach: Split into separate modules: polygon_builder.py, renderer.py, constants.py

**Legacy PhaseLookup Class:**
- Issue: `PhaseLookup` class in `quickice/phase_mapping/lookup.py` has empty `__init__` with `pass`
- Files: `quickice/phase_mapping/lookup.py:302-310`
- Impact: Dead code path maintained for backward compatibility
- Fix approach: Deprecate class or remove if not used externally

**Duplicate Triple Point Definitions:**
- Issue: Triple points defined in both `quickice/phase_mapping/triple_points.py` and `quickice/phase_mapping/data/ice_boundaries.py`
- Files: `quickice/phase_mapping/triple_points.py:16-30`, `quickice/phase_mapping/data/ice_boundaries.py:26-76`
- Impact: Potential for inconsistency; two sources of truth
- Fix approach: Consolidate to single source, import from one location

## Known Bugs

**Phase Polygon Gaps and Overlaps (Open Issue):**
- Symptoms: Gaps between Ih-XI, IX-II, IX-VI, IX-Ih boundaries; XV overlaps VI region
- Files: `quickice/output/phase_diagram.py:201-400` (polygon builder functions)
- Trigger: Polygon vertices don't properly meet at triple points
- Workaround: None - affects visualization accuracy
- Status: Documented in `ISSUES.md`

**Bare Except Clause Swallowing Exceptions:**
- Symptoms: All exceptions caught and silently ignored during IAPWS97 liquid-vapor curve plotting
- Files: `quickice/output/phase_diagram.py:667-671`
- Trigger: Any exception during saturation curve calculation
- Workaround: None - errors go unreported
- Fix: Replace `except:` with `except Exception:` and log the error

## Security Considerations

**No Critical Security Issues Detected:**
- No `eval()`, `exec()`, or shell command execution
- No SQL injection vectors (no database)
- No file path injection (paths are user-provided but validated as directories)

**Input Validation:**
- Risk: User-provided temperature, pressure, molecule count
- Files: `quickice/validation/validators.py:10-98`
- Current mitigation: Range validation (T: 0-500K, P: 0-10000 MPa, N: 4-100000)
- Recommendations: Consider additional bounds for extreme conditions (e.g., negative absolute values already handled)

## Performance Bottlenecks

**O(n²) Pairwise Distance Calculations:**
- Problem: Atomic overlap check uses nested loops for all atom pairs
- Files: `quickice/output/validator.py:111-127`, `quickice/ranking/scorer.py:60-74`
- Cause: Brute-force pairwise distance calculation without spatial hashing
- Improvement path: Use KD-tree or cell-list algorithm for O(n log n) scaling

**Large Molecule Count Scaling:**
- Problem: Structure generation with 100,000 molecules may be slow
- Files: `quickice/structure_generation/generator.py:69-120`
- Cause: GenIce internal processing plus O(n²) scoring
- Improvement path: Consider limiting max molecules or adding progress feedback

## Fragile Areas

**Solid Boundary Approximations:**
- Files: `quickice/phase_mapping/solid_boundaries.py:33-176`
- Why fragile: Linear interpolation between triple points is MEDIUM confidence (not IAPWS-certified)
- Safe modification: Add new boundaries by following existing pattern; verify against literature
- Test coverage: Limited - boundaries tested only indirectly through phase mapping tests

**Phase Lookup Decision Tree:**
- Files: `quickice/phase_mapping/lookup.py:61-287`
- Why fragile: Complex hierarchical if/elif logic for phase determination; easy to miss edge cases
- Safe modification: Add new phases carefully; ensure all boundary conditions are checked
- Test coverage: Good coverage in `tests/test_phase_mapping.py`

**GenIce Lattice Mapping:**
- Files: `quickice/structure_generation/mapper.py:10-31`
- Why fragile: Hardcoded mapping from phase_id to GenIce lattice names
- Safe modification: Add new phase support by extending `PHASE_TO_GENICE` and `UNIT_CELL_MOLECULES` dicts
- Test coverage: Covered in `tests/test_structure_generation.py`

**Unsupported Proton-Ordered Phases:**
- Files: `quickice/structure_generation/mapper.py:10-19`
- Why fragile: Ice XI, IX, X, XV not in `PHASE_TO_GENICE` mapping
- Safe modification: These phases will raise `UnsupportedPhaseError` if lookup returns them
- Test coverage: Not explicitly tested - should add test for unsupported phase handling

## Scaling Limits

**Molecule Count Limits:**
- Current capacity: 4-100,000 molecules (validator enforced)
- Limit: O(n²) scoring becomes slow beyond ~10,000 molecules
- Scaling path: Implement spatial hashing in distance calculations

**Pressure Range Limits:**
- Current capacity: 0-10,000 MPa (1-10 GPa)
- Limit: Ice X exists at P > 30 GPa (30,000 MPa) - outside validated range
- Scaling path: Extend validator range if Ice X support is needed

## Dependencies at Risk

**GenIce2:**
- Risk: External library for structure generation; API changes could break generation
- Impact: All structure generation would fail
- Mitigation: Pin version in requirements; monitor for updates

**IAPWS:**
- Risk: External library for thermodynamic calculations
- Impact: Melting curve calculations and liquid-vapor boundary in diagrams
- Mitigation: Already has fallback handling with try/except; pin version

**spglib:**
- Risk: External library for space group validation
- Impact: Structure validation would fail; PDB writing continues
- Mitigation: Graceful error handling in orchestrator

## Missing Critical Features

**Proton-Ordered Phase Generation:**
- Problem: Ice XI, IX, X, XV cannot generate structures (not in GenIce mapping)
- Files: `quickice/structure_generation/mapper.py:10-19`
- Blocks: Users cannot generate these proton-ordered ice polymorphs
- Workaround: Raises `UnsupportedPhaseError` with clear message

**Phase Diagram Validation:**
- Problem: No automated checking that phase polygons are gapless and non-overlapping
- Files: `quickice/output/phase_diagram.py`
- Blocks: Cannot detect geometry errors before user sees incorrect diagram
- Fix approach: Add polygon validation function using Shapely or similar geometry library

## Test Coverage Gaps

**Phase Diagram Generation:**
- What's not tested: `quickice/output/phase_diagram.py` has no dedicated test file
- Files: `quickice/output/phase_diagram.py` (847 lines, 0 direct tests)
- Risk: Polygon geometry errors, matplotlib rendering failures, incorrect boundary rendering
- Priority: Medium (visualization only, not core logic)

**Output Orchestrator:**
- What's not tested: `quickice/output/orchestrator.py` has no dedicated test file
- Files: `quickice/output/orchestrator.py` (132 lines, 0 direct tests)
- Risk: Integration failures between PDB writing, validation, and diagram generation
- Priority: Medium (integration layer)

**Ice Boundaries Data:**
- What's not tested: `quickice/phase_mapping/data/ice_boundaries.py` tested only indirectly
- Files: `quickice/phase_mapping/data/ice_boundaries.py` (404 lines)
- Risk: Incorrect melting curve coefficients or triple point values
- Priority: Low (data file, hard to test without reference values)

**Error Path Testing:**
- What's not tested: Error handling paths in `quickice/structure_generation/errors.py`
- Files: `quickice/structure_generation/errors.py` (pass-only class)
- Risk: Error messages may not be clear or useful
- Priority: Low (simple pass-through)

---

*Concerns audit: 2026-03-28*
