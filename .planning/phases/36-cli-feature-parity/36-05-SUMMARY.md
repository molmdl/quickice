---
phase: 36-cli-feature-parity
plan: 05
subsystem: cli-pipeline
tags: [cli, pipeline, ice-candidate, interface, generate_candidates, InterfaceConfig]

# Dependency graph
requires:
  - phase: 36-03
    provides: CLIPipeline scaffold with step stubs, report_progress()
provides:
  - _run_source_step() ice candidate generation (base_seed, nmolecules=256 default)
  - _run_interface_step() with InterfaceConfig including seed parameter
  - Hydrate branch placeholder structure for Plan 06
affects: [36-06, 36-07, 36-08, 36-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inline imports in step methods: avoid top-level GUI/science deps in pipeline.py"
    - "getattr(self.args, attr, default) for backward-compatible optional CLI args"
    - "if self._ice_candidate is None guard for hydrate branch insertion point"

key-files:
  created: []
  modified:
    - quickice/cli/pipeline.py

key-decisions:
  - "nmolecules default 256 via getattr for backward compatibility"
  - "seed=self.args.seed in InterfaceConfig (FIX #3 from project history)"
  - "Hydrate branch placeholder: if self._ice_candidate is None guard before ice candidate code"

patterns-established:
  - "Inline try/except ImportError for science package imports in step methods"
  - "report_progress() on both success and error paths"
  - "logger.error() + report_progress() + return 1 error pattern"

# Metrics
duration: 1min
completed: 2026-06-14
---

# Phase 36 Plan 05: Source & Interface Step Implementation Summary

**Ice candidate generation via generate_candidates(base_seed=) and interface generation via InterfaceConfig(seed=) in CLIPipeline**

## Performance

- **Duration:** 1 min
- **Started:** 2026-06-14T14:32:53Z
- **Completed:** 2026-06-14T14:33:42Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- _run_source_step() generates ice candidate via generate_candidates() with base_seed and nmolecules=256 default
- _run_interface_step() creates InterfaceConfig with seed parameter and calls generate_interface()
- Both methods use report_progress() and return 1 on error with proper exception handling
- Method structure allows Plan 06 to add hydrate branch (if self._ice_candidate is None guard)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement _run_source_step for ice candidate generation** - `2148edd` (feat)
2. **Task 2: Implement _run_interface_step with InterfaceConfig** - `b60efcd` (feat)

## Files Created/Modified
- `quickice/cli/pipeline.py` - Added ice candidate generation in _run_source_step() and interface generation in _run_interface_step()

## Decisions Made
- nmolecules defaults to 256 via getattr(self.args, 'nmolecules', 256) for backward compatibility with args namespaces that lack the attribute
- seed=self.args.seed passed to InterfaceConfig (project history FIX #3: InterfaceConfig requires seed= parameter)
- Hydrate branch insertion point uses `if self._ice_candidate is None` guard so Plan 06 can add hydrate generation that sets self._ice_candidate before the ice candidate branch
- pocket_diameter uses getattr with None default since it's optional (only for pocket mode)
- pocket_shape uses getattr with 'sphere' default matching InterfaceConfig default
- gmx solvate-like report printed to stderr if self._interface_result.report exists

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- _run_source_step() ready for hydrate branch addition in Plan 06 (if self._ice_candidate is None guard)
- _run_interface_step() fully implemented and ready for custom/solute/ion downstream steps
- Remaining stubs (_run_custom_step, _run_solute_step, _run_ion_step, _run_export_step) return exit code 1 as planned

---
*Phase: 36-cli-feature-parity*
*Completed: 2026-06-14*
