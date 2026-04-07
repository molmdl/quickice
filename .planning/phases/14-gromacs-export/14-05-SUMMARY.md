---
phase: 14-gromacs-export
plan: "05"
subsystem: export
tags: [gromacs, candidate-selection, gui, cli, ranked-candidates]

# Dependency graph
requires:
  - phase: 14-gromacs-export
    provides: GROMACS file writers and basic GUI/CLI export
  - phase: 14-gromacs-export
    provides: RankedCandidate type from ranking system
provides:
  - Candidate selection in GUI for GROMACS export
  - --candidate flag in CLI for selective GROMACS export
  - Filename with rank/T/P information for GROMACS files
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - RankedCandidate pattern for passing candidate + metadata
    - Selective export pattern (filter by rank)
    - Filename pattern with thermodynamic conditions

key-files:
  created: []
  modified:
    - quickice/gui/export.py
    - quickice/gui/main_window.py
    - quickice/cli/parser.py
    - quickice/main.py

key-decisions:
  - "Use RankedCandidate object instead of Candidate for GROMACS export"
  - "Include T and P in filename for thermodynamic context"
  - "Default filename: {phase}_{T}K_{P}bar_c{rank}.gro"
  - "CLI --candidate flag allows selective export, maintains backward compatibility"

patterns-established:
  - "GROMACS export matches PDB export UX pattern"
  - "GUI passes RankedCandidate with T/P for filename generation"
  - "CLI filters candidates based on --candidate flag value"

# Metrics
duration: 5min
completed: 2026-04-07
---
# Phase 14 Plan 05: Candidate Selection for GROMACS Export Summary

**GROMACS export now supports candidate selection via GUI and CLI, matching PDB export UX pattern**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-07T09:05:03Z
- **Completed:** 2026-04-07T09:10:03Z
- **Tasks:** 4
- **Files modified:** 4

## Accomplishments
- Updated GROMACSExporter to accept RankedCandidate with temperature and pressure parameters
- GUI now passes selected candidate's rank and thermodynamic conditions for filename generation
- Added --candidate CLI flag for selective GROMACS export (e.g., --gromacs --candidate 1)
- CLI filters candidates by rank, warns if specified rank not found, maintains backward compatibility

## Task Commits

Each task was committed atomically:

1. **Task 1: Update GROMACSExporter to accept RankedCandidate** - `4ea2842` (feat)
2. **Task 2: Update GUI handler to pass RankedCandidate and T/P** - `e55d8eb` (feat)
3. **Task 3: Add --candidate flag to CLI parser** - `a4949b3` (feat)
4. **Task 4: Add selective GROMACS export to CLI main** - `a1ee3ec` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `quickice/gui/export.py` - GROMACSExporter.export_gromacs signature changed to accept RankedCandidate, T, P
- `quickice/gui/main_window.py` - _on_export_gromacs now passes RankedCandidate and T/P from input panel
- `quickice/cli/parser.py` - Added --candidate/-c argument with documentation
- `quickice/main.py` - Added candidate filtering logic for selective GROMACS export

## Decisions Made
- Use RankedCandidate object (from ranking system) to pass both candidate structure and metadata
- Filename format includes thermodynamic conditions: `{phase}_{T}K_{P}bar_c{rank}.gro`
- CLI maintains backward compatibility: --gromacs alone exports all, --gromacs --candidate N exports specific rank
- GUI uses same selection mechanism as PDB export (left viewer dropdown)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Candidate selection feature complete for both GUI and CLI
- GROMACS export now matches PDB export UX pattern
- Ready for user testing and feedback

---
*Phase: 14-gromacs-export*
*Completed: 2026-04-07*