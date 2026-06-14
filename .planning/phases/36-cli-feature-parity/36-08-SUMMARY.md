---
phase: 36-cli-feature-parity
plan: 08
subsystem: cli
tags: [cli, pipeline, custom-molecule, solute, insertion, seed]

# Dependency graph
requires:
  - phase: 36-03
    provides: _run_custom_step and _run_solute_step stubs with report_progress
  - phase: 36-07
    provides: Full _run_export_step with all 6 structure types
provides:
  - _run_custom_step() with random and custom placement modes
  - _run_solute_step() with --solute-source selection
  - FIX #7: SoluteInserter(config, seed=args.seed)
  - CustomMoleculeInserter created with seed=args.seed
  - CustomMoleculeConfig with gro_path=gro_path (Path, not str)
affects: [36-09, 36-10, 36-11, cli-pipeline-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Concentration-to-count inline calculation in custom step (reuses AVOGADRO constant pattern)"
    - "Source resolution via _get_source_structure for solute step"

key-files:
  created: []
  modified:
    - quickice/cli/pipeline.py

key-decisions:
  - "gro_path=gro_path (Path) NOT str(gro_path) — CustomMoleculeConfig.gro_path typed as Path"
  - "FIX #7: SoluteInserter(config, seed=args.seed) — NOT SoluteInserter(config) for reproducibility"
  - "Inline AVOGADRO calculation for custom_concentration (avoids importing from solute_inserter)"
  - "getattr for solute_source default 'interface' — backward-compatible with pre-v4.5 args"

patterns-established:
  - "Concentration→count inline: C_M × V_L × NA with nm³→L conversion (1e-24)"
  - "Source structure resolution pattern: _get_source_structure(source_name) for solute/ion steps"

# Metrics
duration: 1min
completed: 2026-06-14
---

# Phase 36 Plan 08: Custom and Solute Step Implementation Summary

**_run_custom_step() with random/custom placement + _run_solute_step() with --solute-source selection, FIX #7 (seeded SoluteInserter)**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-06-14T14:42:18Z
- **Completed:** 2026-06-14T14:43:16Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Implemented _run_custom_step() with two modes: random (count from --custom-count or --custom-concentration) and custom (CSV positions/rotations)
- Implemented _run_solute_step() with --solute-source selection (interface or custom)
- FIX #7: SoluteInserter(config, seed=args.seed) — ensures reproducible solute placement
- CustomMoleculeInserter created with seed=args.seed for reproducible custom molecule placement
- CustomMoleculeConfig uses gro_path=gro_path (Path type) — no str() conversion
- Error handling: FileNotFoundError, ValueError, InsertionError for custom; ValueError, FileNotFoundError for solute
- Inline imports for science deps (matches existing step pattern)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement _run_custom_step with random and custom placement modes** - `cf3e620` (feat)
2. **Task 2: Implement _run_solute_step with source selection** - `3a9ee8b` (feat)

## Files Created/Modified
- `quickice/cli/pipeline.py` - _run_custom_step() and _run_solute_step() replacing stubs

## Decisions Made
- gro_path=gro_path (Path) — NOT str(gro_path) — CustomMoleculeConfig.gro_path is typed as Path in types.py
- FIX #7: SoluteInserter(config, seed=args.seed) — previously unseeded, causing non-reproducible solute placement
- Inline AVOGADRO constant for custom_concentration→count calculation — avoids circular dependency on solute_inserter import
- getattr(self.args, 'solute_source', 'interface') — backward-compatible default for args namespaces that lack solute_source
- getattr(self.args, 'custom_concentration', None) — handles pre-v4.5 args without custom_concentration attribute

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Custom and solute steps fully implemented
- Ready for Plan 36-09 (ion step implementation) and Plan 36-10 (integration)
- Pipeline now has: source step, interface step, custom step, solute step, and export step functional

---
*Phase: 36-cli-feature-parity*
*Completed: 2026-06-14*
