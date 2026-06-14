---
phase: 36-cli-feature-parity
plan: 10
subsystem: cli
tags: [cli, pipeline, main, entry-point, delegation, backward-compat]

# Dependency graph
requires:
  - phase: 36-01
    provides: Parser with v4.5 flags + validate_pipeline_args
  - phase: 36-03
    provides: CLIPipeline class with step stubs and report_progress
  - phase: 36-05
    provides: _run_source_step and _run_interface_step
  - phase: 36-07
    provides: Full _run_export_step with all 6 structure types
  - phase: 36-08
    provides: _run_custom_step and _run_solute_step
  - phase: 36-09
    provides: _run_ion_step with 3 source modes
provides:
  - main.py wired to CLIPipeline for pipeline workflows
  - Pipeline flag detection (interface, hydrate, custom_gro, solute_type, ion_concentration)
  - Ice-only backward-compatible path preserved
  - check_output_file() removed (auto-overwrite + --no-overwrite)
  - Exit codes: 0 success, 1 runtime error, 2 argument error
affects: [36-11, cli-integration-testing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pipeline flag detection: has_pipeline_flags branches to CLIPipeline before ice-only path"
    - "Auto-overwrite by default with --no-overwrite safety flag in CLIPipeline"

key-files:
  created: []
  modified:
    - quickice/main.py

key-decisions:
  - id: D1
    choice: "Pipeline flag detection before ice-only path in main()"
    rationale: "Interface/hydrate/custom/solute/ion flags indicate pipeline mode; absent flags fall through to ice-only"
  - id: D2
    choice: "Remove check_output_file() entirely (not conditional)"
    rationale: "CLIPipeline uses --no-overwrite flag for safety; ice-only path already auto-overwrites; no interactive prompts in CLI"
  - id: D3
    choice: "Keep InterfaceGenerationError in except clause"
    rationale: "Even though CLIPipeline handles it internally, defensive exception handling for future code paths"

patterns-established:
  - "Entry-point delegation: main() detects workflow type and delegates to specialized executor"

# Metrics
duration: 1min
completed: 2026-06-14
---

# Phase 36 Plan 10: Wire main.py to CLIPipeline Summary

**Pipeline flag detection in main() delegates to CLIPipeline.execute() for interface/hydrate/custom/solute/ion workflows while preserving ice-only backward compatibility**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-06-14T14:46:25Z
- **Completed:** 2026-06-14T14:48:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- main() now detects pipeline flags and delegates to CLIPipeline.execute()
- check_output_file() removed (replaced by auto-overwrite + --no-overwrite flag in pipeline)
- Interface block removed from main.py (delegated to CLIPipeline which uses interface.gro/interface.top filenames)
- Ice-only path fully preserved (candidate generation + ranking + GROMACS export + PDB output)
- Exit code semantics: 0 success, 1 runtime error, 2 argument error
- No GUI imports in main.py
- All 23 existing CLI integration tests still pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Refactor main.py to delegate to CLIPipeline** - `c6aa97c` (feat)

## Files Created/Modified
- `quickice/main.py` - Added CLIPipeline import + pipeline flag detection, removed check_output_file() + interface block, preserved ice-only path

## Decisions Made
- Pipeline flag detection happens immediately after args parsing, before any ice-only logic — this ensures pipeline workflows (interface, hydrate, custom, solute, ion) are routed to CLIPipeline, while pure ice generation (--temperature, --pressure, --nmolecules only) falls through to the existing path
- check_output_file() removed entirely because (1) CLIPipeline handles --no-overwrite safety, (2) ice-only path already auto-overwrites, (3) interactive prompts don't belong in CLI pipelines
- InterfaceGenerationError kept in except clause for defensive programming even though CLIPipeline handles it internally

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- main.py now fully wired to CLIPipeline
- Pipeline flag detection routes all v4.5 workflows correctly
- Ready for Plan 36-11 (final integration/end-to-end testing)
- All 6 pipeline steps functional: source, interface, custom, solute, ion, export

---
*Phase: 36-cli-feature-parity*
*Completed: 2026-06-14*
