---
phase: 14-gromacs-export
plan: "03"
subsystem: cli
tags: [gromacs, cli, export, tip4p, molecular-dynamics]

# Dependency graph
requires: []
provides:
  - CLI --gromacs flag for GROMACS file export
  - TIP4P water model coordinates in .gro format
  - TIP4P-ICE topology in .top format
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - CLI flag pattern for format selection
    - GROMACS file format (gro, top)

key-files:
  created: []
  modified:
    - quickice/cli/parser.py
    - quickice/main.py
    - quickice/output/gromacs_writer.py
    - quickice/structure_generation/generator.py

key-decisions:
  - "Use TIP4P water model for GROMACS export (4 atoms per molecule)"
  - "Write single .top file for first candidate, multiple .gro files for ranked candidates"

patterns-established:
  - "GROMACS export follows same output directory pattern as PDB export"
  - "Filename pattern: {phase_id}_{rank}.gro"

# Metrics
duration: 4min
completed: 2026-04-06
---

# Phase 14 Plan 03: CLI GROMACS Export Summary

**Added --gromacs CLI flag for GROMACS file export with TIP4P-ICE water model topology**

## Performance

- **Duration:** 3m 47s
- **Started:** 2026-04-05T18:51:32Z
- **Completed:** 2026-04-05T18:55:19Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Added --gromacs/-g CLI flag for GROMACS format export
- Integrated GROMACS export into CLI pipeline after candidate ranking
- Fixed water model mismatch (TIP3P → TIP4P) for correct coordinate output
- Added bounds check for positions array in gromacs_writer

## Task Commits

Each task was committed atomically:

1. **Task 1: Add --gromacs flag to CLI parser** - `8ea9d6f` (feat)
2. **Task 2: Add GROMACS export to main.py** - `38b3f5c` (feat)
3. **Task 3: Clean up duplicate code in gromacs_writer.py** - `61818ad` (fix)

**Plan metadata:** (docs commit pending)

## Files Created/Modified
- `quickice/cli/parser.py` - Added --gromacs/-g argument and docstring update
- `quickice/main.py` - Added GROMACS export logic with imports from gromacs_writer
- `quickice/output/gromacs_writer.py` - Removed duplicate code, added bounds check
- `quickice/structure_generation/generator.py` - Changed water model from TIP3P to TIP4P

## Decisions Made
- Use TIP4P water model for GROMACS export (4-point: O, H1, H2, MW virtual site)
- Write .top file only for first-ranked candidate (others share same molecule count)
- Filename pattern: `{phase_id}_{rank}.gro` for coordinates, `{phase_id}_1.top` for topology

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed water model mismatch (TIP3P → TIP4P)**
- **Found during:** Task 3 (Testing GROMACS export)
- **Issue:** Generator used TIP3P water (3 atoms/molecule) but gromacs_writer expected TIP4P (4 atoms/molecule). This caused bounds errors: "positions has 384 atoms but nmolecules=128 needs 512"
- **Fix:** Changed water model in generator.py from `tip3p` to `tip4p` to match gromacs_writer expectations
- **Files modified:** quickice/structure_generation/generator.py
- **Verification:** CLI with --gromacs flag now produces valid .gro and .top files without bounds errors
- **Committed in:** 61818ad (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Fix essential for correct GROMACS output. TIP4P is appropriate for ice simulations.

## Issues Encountered
- Initial test revealed water model mismatch - generator produced 3 atoms/molecule while writer expected 4

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CLI GROMACS export complete and functional
- Users can now generate both PDB and GROMACS files from CLI
- Ready for testing with molecular dynamics simulations

---
*Phase: 14-gromacs-export*
*Completed: 2026-04-06*
