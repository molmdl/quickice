---
phase: 32-architecture-preparation
plan: 02
subsystem: architecture
tags: [validation, refactoring, gromacs, registry]

# Dependency graph
requires:
  - phase: 32-01
    provides: TabIndex enum, MoleculetypeRegistry, ITP parser
provides:
  - Molecule validator for GRO/ITP consistency
  - Refactored main_window.py with TabIndex constants
  - GROMACS export with registry integration
affects: [33-solute-insertion, 34-custom-molecule, 35-tab-reordering]

# Tech tracking
tech-stack:
  added: []
  patterns: [validation, enum refactoring, registry pattern]

key-files:
  created:
    - quickice/structure_generation/molecule_validator.py
  modified:
    - quickice/gui/main_window.py
    - quickice/output/gromacs_writer.py
    - quickice/gui/hydrate_export.py

key-decisions:
  - "Validator uses existing gro_parser for GRO parsing"
  - "TabIndex enum replaces all hardcoded tab indices"
  - "Registry parameter is optional for backward compatibility"

patterns-established:
  - "Pattern: ValidationResult dataclass for structured validation results"
  - "Pattern: Enum constants replace magic numbers throughout codebase"
  - "Pattern: Optional registry parameter with module-level default"

# Metrics
duration: 3min
completed: 2026-05-04
---

# Phase 32 Plan 02: Molecule Validator and Integration Summary

**Molecule validator with GRO/ITP consistency checking, main_window.py refactored to use TabIndex enum, and GROMACS export integrated with MoleculetypeRegistry for unique moleculetype naming**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-04T22:24:14Z
- **Completed:** 2026-05-04T22:27:45Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Created molecule validator module with specific error messages for GRO/ITP consistency validation
- Refactored main_window.py to eliminate all hardcoded tab indices, using TabIndex enum throughout
- Updated GROMACS export functions to accept MoleculetypeRegistry for context-specific molecule naming
- Maintained backward compatibility for existing exports while enabling future hydrate vs liquid solute distinction

## Task Commits

Each task was committed atomically:

1. **Task 1: Create molecule validator module** - `e745973` (feat)
2. **Task 2: Refactor main_window.py to use TabIndex enum** - `b866273` (feat)
3. **Task 3: Update GROMACS export to use MoleculetypeRegistry** - `9bd8f0d` (feat)

**Plan metadata:** (pending final commit)

_Note: All commits follow atomic commit pattern with descriptive messages_

## Files Created/Modified

- `quickice/structure_generation/molecule_validator.py` - Validates GRO/ITP consistency with specific error messages
- `quickice/gui/main_window.py` - Refactored to use TabIndex enum, removed all tab numbering from comments
- `quickice/output/gromacs_writer.py` - Added MoleculetypeRegistry parameter, module-level registry instance
- `quickice/gui/hydrate_export.py` - Creates registry instance, registers hydrate guests before export

## Decisions Made

- **Validator uses existing gro_parser**: Reuses parse_gro_file for GRO parsing, maintaining consistency with existing codebase
- **Specific error messages**: Validation errors include file names and atom counts for clear user feedback
- **TabIndex enum for all indices**: Replaced every hardcoded index (0, 1, 2, 3) with named constants (ICE, HYDRATE, INTERFACE, ION)
- **Tab names only in comments**: Removed "Tab 1", "Tab 2" numbering from all comments, using descriptive names only
- **Optional registry parameter**: GROMACS export functions accept optional registry, falling back to module-level instance for backward compatibility
- **Hydrate guest registration**: CH4/THF from hydrate cages registered with _HYD suffix for unique GROMACS naming

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed without blockers.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

All three integration modules are complete and tested:

- **Molecule validator** ready for use in custom molecule upload (Phase 34)
- **TabIndex enum** eliminates hardcoded indices, preparing for tab reordering (Phase 35)
- **MoleculetypeRegistry** integrated into GROMACS export, ready for solute/liquid distinction (Phase 33)

**Next:** Execute 32-03-PLAN.md (final plan in Phase 32)

---
*Phase: 32-architecture-preparation*
*Completed: 2026-05-04*
