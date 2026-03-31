# Codebase Concerns

**Analysis Date:** 2026-03-31

## Tech Debt

### Phase Diagram Polygon Complexity
- **Issue:** Large monolithic file with intricate polygon calculations and hardcoded boundary values
- **Files:** `quickice/output/phase_diagram.py` (965 lines)
- **Impact:** Difficult to maintain, debug, and extend. Each phase polygon has unique boundary logic with hardcoded coordinates
- **Fix approach:** 
  - Extract polygon builders into separate functions per phase
  - Consider configuration-driven boundary definitions
  - Add unit tests for each polygon function

### Unsupported Phases
- **Issue:** GenIce2 doesn't support Ice IX, XI, X, XV (proton-ordered and symmetric phases)
- **Files:** `quickice/structure_generation/mapper.py` (lines 10-19)
- **Impact:** Users requesting these phases get `UnsupportedPhaseError`
- **Fix approach:** 
  - Document limitation clearly in CLI help
  - Consider alternative structure generation methods for these phases
  - Return informative error with suggestions

### Input Range Limitations
- **Issue:** Pressure validator limits to 10000 MPa, but phase diagram extends to 100000 MPa
- **Files:** `quickice/validation/validators.py` (lines 56-58)
- **Impact:** Users cannot use CLI for Ice X phase (>30000 MPa)
- **Fix approach:** Update `validate_pressure()` to accept 0-100000 MPa range

## Known Bugs

### Phase Diagram Gaps
- **Issue:** Minor triangular gaps exist in phase diagram polygon rendering
- **Files:** `quickice/output/phase_diagram.py`
- **Symptoms:** Small white gaps at II-IX-Ih and VI-XV-II triangle regions
- **Trigger:** Rendering phase diagram with log scale pressure
- **Workaround:** None documented
- **Location:** Documented in `ISSUES.md` as remaining minor issues

### Empty Return on Unknown Phase
- **Issue:** `_build_phase_polygon_from_curves()` returns empty list for unknown phase IDs
- **Files:** `quickice/output/phase_diagram.py` (line 207)
- **Symptoms:** Silent failure - phase not rendered without warning
- **Trigger:** Passing unsupported phase ID to polygon builder
- **Fix approach:** Log warning or raise exception for unknown phases

## Security Considerations

### Input Validation
- **Status:** ✓ PASS
- **Current mitigation:** Temperature, pressure, and molecule count validated in `quickice/validation/validators.py`
- **Coverage:** Numeric bounds checking, type validation, helpful error messages
- **Risk:** Low - inputs sanitized before use

### File Operations
- **Status:** ✓ PASS
- **Current mitigation:** Uses `pathlib.Path` for file operations, no shell command injection
- **Risk:** Low - no arbitrary file paths from user input

### External Dependencies
- **Risk:** GenIce2, spglib, scipy, shapely are trusted scientific computing libraries
- **Impact:** Supply chain vulnerability if dependencies compromised
- **Current mitigation:** None
- **Recommendations:** Pin exact versions, use dependency scanning tools

## Performance Bottlenecks

### Supercell Neighbor Search
- **Issue:** O(n log n) neighbor search for O-O distance calculations with 3x3x3 supercell
- **Files:** `quickice/ranking/scorer.py` (lines 26-84), `quickice/output/validator.py` (lines 109-135)
- **Problem:** For large systems (>1000 molecules), creates 27x larger supercell array
- **Cause:** PBC handling requires supercell expansion
- **Improvement path:** Use neighbor lists or cell lists for large systems

### Structure Generation Sequential Loop
- **Issue:** Candidates generated sequentially in `_generate_single()` loop
- **Files:** `quickice/structure_generation/generator.py` (lines 199-219)
- **Problem:** Generating 10 candidates calls GenIce2 10 times sequentially
- **Cause:** No parallelization in `generate_all()` method
- **Improvement path:** Use multiprocessing or joblib for parallel generation

## Fragile Areas

### Phase Boundary Calculations
- **Issue:** Complex hierarchical boundary checking with many edge cases
- **Files:** `quickice/phase_mapping/lookup.py` (lines 154-358)
- **Why fragile:** 
  - 8 different phase regions with unique boundary conditions
  - Hardcoded temperature/pressure thresholds throughout
  - Order-dependent evaluation (first match wins)
- **Safe modification:** 
  - Add comprehensive unit tests for boundary conditions
  - Document decision tree logic explicitly
  - Consider decision table refactoring

### Polygon Boundary Overlap Detection
- **Issue:** Manual polygon construction to avoid overlaps requires precise coordinate calculation
- **Files:** `quickice/output/phase_diagram.py` (lines 210-668)
- **Why fragile:**
  - Phase regions defined by boundary curves that must meet exactly
  - Rendering order matters (sub-phases rendered after parent phases)
  - Hardcoded offsets like `P_vi - 5.0` (line 300) are fragile
- **Safe modification:**
  - Add polygon overlap validation tests
  - Use shapely operations for automatic boundary calculation
  - Document all hardcoded offsets with comments

### GenIce Integration
- **Issue:** Global random state manipulation for reproducibility
- **Files:** `quickice/structure_generation/generator.py` (lines 83-111)
- **Why fragile:**
  - `np.random.seed()` affects global state
  - Must save/restore state to avoid side effects
- **Safe modification:**
  - Isolate random state in local generator
  - Consider context manager for state management

## Scaling Limits

### Molecule Count
- **Current capacity:** 4 to 100,000 molecules
- **Limit:** Validated in `quickice/validation/validators.py` (line 93)
- **Scaling path:** Increase upper bound for larger systems (requires memory testing)

### Temperature Range
- **Current capacity:** 0 to 500 K
- **Limit:** Phase diagram extends to 500 K, but some phases exist at higher T
- **Scaling path:** Extend IAPWS melting curves for higher temperatures

### Pressure Range
- **Current capacity:** 0 to 10,000 MPa in CLI (but phase diagram supports 0-100,000 MPa)
- **Limit:** Input validator restricts to 10,000 MPa
- **Scaling path:** Update validator to match phase diagram range

## Dependencies at Risk

### GenIce2
- **Risk:** Core functionality depends on GenIce2 library
- **Impact:** Structure generation would fail without it
- **Location:** `quickice/structure_generation/generator.py` (lines 9-10)
- **Alternative:** None identified - GenIce2 is specialized for ice structures

### IAPWS Library
- **Risk:** Phase mapping depends on IAPWS R14-08 melting curves
- **Impact:** Melting curve calculations would fail
- **Location:** `quickice/phase_mapping/melting_curves.py`, `quickice/output/phase_diagram.py` (line 779)
- **Alternative:** Implement IAPWS equations directly

### Shapely
- **Risk:** Phase diagram rendering uses shapely for polygon operations
- **Impact:** Polygon centroid calculation would fail
- **Location:** `quickice/output/phase_diagram.py` (lines 698, 727)
- **Alternative:** Implement centroid calculation manually

## Missing Critical Features

### Test Coverage for Phase Diagram
- **Problem:** No unit tests for `quickice/output/phase_diagram.py` (complex 965-line module)
- **Files:** `quickice/output/phase_diagram.py`
- **Risk:** Polygon boundary changes could introduce undetected overlaps or gaps
- **Priority:** High

### Output Orchestrator Tests
- **Problem:** No unit tests for `quickice/output/orchestrator.py`
- **Files:** `quickice/output/orchestrator.py`
- **Risk:** Output workflow changes could break end-to-end functionality
- **Priority:** Medium

### Ice X, IX, XI, XV Structure Generation
- **Problem:** Cannot generate structures for proton-ordered and symmetric phases
- **Files:** `quickice/structure_generation/mapper.py`
- **Risk:** Users requesting these phases receive error
- **Priority:** Medium (depends on GenIce2 support)

## Test Coverage Gaps

### Phase Diagram Polygon Tests
- **What's not tested:** Polygon vertex calculations for all 12 phases
- **Files:** `quickice/output/phase_diagram.py`
- **Risk:** Boundary changes could create undetected polygon overlaps/gaps
- **Priority:** High
- **Test files needed:** `tests/test_output/test_phase_diagram.py`

### Phase Lookup Boundary Cases
- **What's not tested:** Edge cases at triple points, extreme pressures (>10 GPa)
- **Files:** `quickice/phase_mapping/lookup.py`
- **Risk:** Incorrect phase identification near boundaries
- **Priority:** Medium
- **Test locations:** `tests/test_phase_mapping.py` exists but needs edge case expansion

### Scoring Validation
- **What's not tested:** Energy score calculation correctness, density score accuracy
- **Files:** `quickice/ranking/scorer.py`
- **Risk:** Incorrect ranking could produce non-optimal structures
- **Priority:** Medium
- **Test locations:** `tests/test_ranking.py` exists

### Output Validator Edge Cases
- **What's not tested:** Space group validation failures, overlap detection edge cases
- **Files:** `quickice/output/validator.py`
- **Risk:** Invalid structures could pass validation
- **Priority:** Medium
- **Test locations:** `tests/test_output/test_validator.py` exists

---

*Concerns audit: 2026-03-31*