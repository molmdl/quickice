---
phase: 03-structure-generation
plan: 02
subsystem: structure_generation
tags: [genice, tip3p, gromacs, numpy, md-simulations]

# Dependency graph
requires:
  - phase: 02-phase-mapping
    provides: Phase lookup with density and phase_id
provides:
  - IceStructureGenerator class for GenIce integration
  - generate_candidates() convenience function
  - 10 diverse ice structure candidates per query
affects:
  - ranking (Phase 4)
  - output (Phase 5)

# Tech tracking
tech-stack:
  added: [genice2, genice-core]
  patterns: [GenIce API wrapper, seed-based diversity, GRO parsing]

key-files:
  created:
    - quickice/structure_generation/generator.py
  modified:
    - quickice/structure_generation/__init__.py
    - quickice/structure_generation/mapper.py
    - tests/test_structure_generation.py

key-decisions:
  - "TIP3P water model (standard for MD simulations, 3 atoms per molecule)"
  - "10 candidates with seeds 1000-1009 (deterministic diversity)"
  - "GROMACS format for output (easily parseable, standard in MD)"
  - "Strict depolarization for physical validity"

patterns-established:
  - "Convenience function wraps class instance for single-shot API"
  - "Random seed controls hydrogen bond network diversity"
  - "GenIce unit cell definitions differ from conventional crystallographic cells"

# Metrics
duration: 24min
completed: 2026-03-26
---

# Phase 3 Plan 2: GenIce-Based Structure Generation

**Working IceStructureGenerator class that generates 10 diverse ice structure candidates using GenIce API with TIP3P water model and strict depolarization**

## Performance

- **Duration:** 24 min
- **Started:** 2026-03-26T14:50:32Z
- **Completed:** 2026-03-26T15:14:52Z
- **Tasks:** 2
- **Files modified:** 4 (generator.py, __init__.py, mapper.py, tests)

## Accomplishments
- IceStructureGenerator class wraps GenIce API with fine-grained control
- 10 candidates generated per query with seeds 1000-1009 (deterministic diversity)
- TIP3P water model with strict depolarization for physical validity
- Density from Phase 2 used in cell sizing
- GROMACS format output parsed into numpy arrays
- generate_candidates() provides clean public API

## Task Commits

Each task was committed atomically:

1. **fix(03-01): correct UNIT_CELL_MOLECULES values** - `3719d41` (fix)
   - Fixed ice1h: 4 → 16 molecules per GenIce unit cell
   - Fixed ice8: 16 → 64 molecules per GenIce unit cell

2. **test(03-02): add comprehensive generator tests** - `c0f2d89` (test)
   - Added 20 new tests for IceStructureGenerator and generate_candidates

3. **feat(03-02): create GenIce-based IceStructureGenerator class** - `56203c9` (feat)
   - Implemented IceStructureGenerator with GenIce API integration
   - Added _generate_single(), generate_all(), and _parse_gro() methods

4. **feat(03-02): implement generate_candidates convenience function** - `70c6d88` (feat)
   - Added generate_candidates() function for clean public API
   - Updated __init__.py exports

**Plan metadata:** Will be committed after this summary

## Files Created/Modified
- `quickice/structure_generation/generator.py` - IceStructureGenerator class and generate_candidates function (260 lines)
- `quickice/structure_generation/__init__.py` - Updated exports for generator module
- `quickice/structure_generation/mapper.py` - Fixed UNIT_CELL_MOLECULES values
- `tests/test_structure_generation.py` - Added 20 new tests (54 total)

## Decisions Made
- **TIP3P water model:** Standard for MD simulations, widely supported, 3 atoms per molecule
- **Seeds 1000-1009:** Deterministic diversity, reproducible, easy to track
- **GROMACS format:** Simple text format, easily parseable, standard in MD community
- **Strict depolarization:** Ensures physically valid structures with zero net dipole

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed UNIT_CELL_MOLECULES values**

- **Found during:** Task 1 (IceStructureGenerator implementation)
- **Issue:** UNIT_CELL_MOLECULES had incorrect values - ice1h was 4 (should be 16), ice8 was 16 (should be 64). GenIce uses different unit cell definitions than conventional crystallographic cells.
- **Fix:** Tested all 8 phases by direct GenIce generation and corrected the values:
  - ice1h: 4 → 16 molecules per unit cell
  - ice8: 16 → 64 molecules per unit cell
- **Files modified:** quickice/structure_generation/mapper.py
- **Verification:** All 54 tests pass with correct molecule counts
- **Commit:** 3719d41

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Bug fix was essential for correct molecule counting. No scope creep.

## Issues Encountered
None - GenIce API integration worked as expected after fixing the unit cell molecule counts.

## Next Phase Readiness
- Structure generation complete and tested (54 tests passing)
- Ready for ranking phase (Phase 4)
- Integration with Phase 2 verified (lookup_phase → generate_candidates)
- All 8 ice phases supported and tested
