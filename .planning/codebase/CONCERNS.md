# Codebase Concerns

**Analysis Date:** 2026-03-30

## Tech Debt

### Large File: phase_diagram.py
- **Issue:** Single file with 964 lines containing 12 polygon builder functions and complex rendering logic
- **Files:** `quickice/output/phase_diagram.py`
- **Impact:** Difficult to maintain, test, and understand; modifications to one polygon may affect others
- **Fix approach:** Extract polygon builders into separate module, create polygon_factory.py with individual builder functions

### Duplicate Boundary Data
- **Issue:** Phase boundary coordinates defined in multiple places (`ice_boundaries.py` and hardcoded in `phase_diagram.py` polygon builders)
- **Files:** `quickice/phase_mapping/data/ice_boundaries.py`, `quickice/output/phase_diagram.py`
- **Impact:** Risk of inconsistency between lookup boundaries and diagram rendering
- **Fix approach:** Centralize all boundary data in ice_boundaries.py, import from single source

### Exception Handling Patterns
- **Issue:** Bare except handlers and silent pass statements in error handling
- **Files:** `quickice/output/phase_diagram.py` (lines 148, 150, 229, 786)
- **Impact:** Errors silently ignored during spline interpolation and IAPWS calls, may hide real issues
- **Fix approach:** Add specific exception types with logging, avoid bare `except:` and `except Exception:`

### Global Random State Manipulation
- **Issue:** GenIce generator modifies global numpy random state
- **Files:** `quickice/structure_generation/generator.py` (lines 84-111)
- **Impact:** Potential for race conditions in concurrent execution, reproducibility issues
- **Fix approach:** Use numpy Generator objects throughout, isolate random state changes

## Known Bugs

### Phase Diagram Polygon Gaps
- **Symptoms:** Two triangular gaps exist in rendered phase diagram
- **Files:** `quickice/output/phase_diagram.py` (polygon builder functions)
- **Trigger:** Viewing diagram at specific T,P ranges
- **Workaround:** None documented
- **Details from ISSUES.md:**
  1. II-IX-Ih triangle gap between Ice II, Ice IX, and Ice Ih
  2. VI-XV-II triangle gap between Ice VI, Ice XV, and Ice II

### Empty Returns in Polygon Builders
- **Symptoms:** Unknown phase returns empty list instead of informative error
- **Files:** `quickice/output/phase_diagram.py` (line 206)
- **Trigger:** Passing unknown phase_id to `_build_phase_polygon_from_curves`
- **Workaround:** None
- **Fix approach:** Raise ValueError with list of valid phases

## Security Considerations

### Path Traversal Protection (Good)
- **Risk:** Output path could potentially escape working directory
- **Files:** `quickice/output/orchestrator.py` (lines 48-56)
- **Current mitigation:** Path traversal check ensures output is within CWD
- **Recommendation:** None - implementation is secure

### Input Validation (Good)
- **Risk:** Invalid CLI inputs could cause unexpected behavior
- **Files:** `quickice/validation/validators.py`
- **Current mitigation:** Comprehensive validation with clear error messages
- **Recommendation:** None - implementation is thorough

### Dependency Security
- **Risk:** External dependencies (GenIce2, iapws, scipy) could have vulnerabilities
- **Files:** `env.yml`
- **Current mitigation:** No vulnerability scanning configured
- **Recommendation:** Add pip-audit or safety to CI pipeline for dependency vulnerability checks

## Performance Bottlenecks

### Spline Interpolation Fallback
- **Problem:** scipy dependency is optional but spline interpolation provides smoother curves
- **Files:** `quickice/output/phase_diagram.py` (lines 139-154)
- **Impact:** Falls back to direct sampling if scipy unavailable, curves may appear jagged
- **Improvement path:** Make scipy required dependency or document performance difference

### O(n log n) Neighbor Search
- **Problem:** KD-tree neighbor search in scoring creates 3x3x3 supercell for PBC
- **Files:** `quickice/ranking/scorer.py` (lines 57-67)
- **Impact:** Memory overhead for supercell, may be slow for very large systems
- **Improvement path:** Use minimum image convention directly, avoid supercell for large systems

### Multiple Melting Curve Evaluations
- **Problem:** Each phase diagram regeneration recalculates all melting curves
- **Files:** `quickice/output/phase_diagram.py` (lines 98-167)
- **Impact:** Unnecessary recomputation for static curves
- **Improvement path:** Cache melting curve data or precompute at module load

## Fragile Areas

### Phase Lookup Boundary Logic
- **Files:** `quickice/phase_mapping/lookup.py` (lines 154-358)
- **Why fragile:** Complex conditional logic with many boundary checks; order of checks matters critically
- **Safe modification:** Add new phases at appropriate priority level, never reorder existing checks
- **Test coverage:** Extensive (test_phase_mapping.py has 100+ tests) but boundary edge cases are fragile

### Polygon Vertex Calculations
- **Files:** `quickice/output/phase_diagram.py` (lines 209-667)
- **Why fragile:** Hardcoded coordinates mixed with calculated boundaries; small changes can create gaps/overlaps
- **Safe modification:** Test polygon rendering after any change to vertex coordinates
- **Test coverage:** Limited - polygon visual verification requires manual inspection

### Triple Point Data
- **Files:** `quickice/phase_mapping/triple_points.py`, `quickice/phase_mapping/__init__.py`
- **Why fragile:** Scientific data from literature; coordinate values must match boundary functions exactly
- **Safe modification:** Update triple points only with verified scientific data, update all dependent boundaries
- **Test coverage:** Implicit via phase lookup tests

## Scaling Limits

### Molecule Count Validation
- **Current capacity:** 4 to 100,000 molecules
- **Limit:** Upper limit from `validate_nmolecules` in `validators.py`
- **Scaling path:** Increase upper bound for larger systems, consider memory implications

### Pressure Range Extension
- **Current capacity:** 0 to 10,000 MPa (10 GPa)
- **Limit:** Pressure validator caps at 10 GPa, but Ice X boundary extends to 100 GPa
- **Scaling path:** Extend `validate_pressure` to support Ice X conditions (0-100,000 MPa)

### Temperature Range
- **Current capacity:** 0 to 500 K
- **Limit:** Temperature validator caps at 500K
- **Scaling path:** Extend if supporting supercritical water or very high temperature phases

## Dependencies at Risk

### GenIce2 (Critical)
- **Risk:** External library for ice structure generation, actively maintained
- **Impact:** Core functionality - cannot generate structures without it
- **Mitigation:** Pin version in env.yml, monitor for updates

### iapws (Critical)
- **Risk:** External library for IAPWS water properties, mature and stable
- **Impact:** Melting curve calculations depend on it
- **Mitigation:** Pin version, IAPWS equations could be reimplemented if needed

### scipy (Optional but Important)
- **Risk:** Large dependency, optional for spline interpolation
- **Impact:** Smoother phase diagram curves when available
- **Mitigation:** Graceful fallback exists, consider making required for consistent output

### matplotlib (Required for Diagrams)
- **Risk:** Standard scientific plotting library, stable
- **Impact:** Phase diagram generation requires it
- **Mitigation:** Pin version, output generation should gracefully handle missing matplotlib

### shapely (Required for Diagrams)
- **Risk:** Geometry library used for polygon centroid calculation
- **Impact:** Label placement on phase diagrams
- **Mitigation:** Pin version

## Missing Critical Features

### No Configuration File Support
- **Problem:** All parameters hardcoded or passed via CLI
- **Blocks:** User-defined settings persistence, batch processing configurations
- **Files:** `quickice/cli/parser.py`
- **Recommendation:** Add YAML/JSON config file support for reproducible runs

### No Logging Configuration
- **Problem:** Only warnings logged, no debug/info levels configurable
- **Blocks:** Troubleshooting production issues, performance monitoring
- **Files:** `quickice/main.py`, `quickice/output/orchestrator.py`
- **Recommendation:** Add structured logging with configurable levels

### No Caching Mechanism
- **Problem:** Each run regenerates all structures, no persistence
- **Blocks:** Large molecule counts, iterative workflows
- **Files:** `quickice/structure_generation/generator.py`
- **Recommendation:** Add optional caching with hash-based file storage

## Test Coverage Gaps

### CLI Module Untested
- **What's not tested:** `quickice/cli/parser.py` argument parsing logic
- **Files:** `quickice/cli/parser.py`
- **Risk:** Argument parsing bugs may not be caught
- **Priority:** Low - parser is simple, integration tests cover happy paths

### Output Module Partially Tested
- **What's not tested:** `quickice/output/orchestrator.py` error handling paths
- **Files:** `quickice/output/orchestrator.py`, `tests/test_output/`
- **Risk:** Error paths untested, may fail silently in production
- **Priority:** Medium - add tests for error scenarios

### Phase Diagram Visual Verification
- **What's not tested:** Polygon rendering correctness, gap/overlap detection
- **Files:** `quickice/output/phase_diagram.py`
- **Risk:** Visual bugs may go undetected until user inspection
- **Priority:** Low - requires manual verification, polygon logic tested indirectly

### Performance Testing Absent
- **What's not tested:** Large molecule counts, concurrent execution
- **Files:** All modules
- **Risk:** Performance regressions may go undetected
- **Priority:** Medium - add benchmark tests for critical paths

---

*Concerns audit: 2026-03-30*