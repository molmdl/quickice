---
phase: 32-architecture-preparation
plan: 01
subsystem: architecture
tags: [enum, registry, parser, gromacs, type-safety]

# Dependency graph
requires: []
provides:
  - TabIndex enum for type-safe tab references
  - MoleculetypeRegistry for unique GROMACS moleculetype naming
  - ITP parser for GROMACS topology file parsing
affects: [solute-insertion, custom-molecule, gromacs-export]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "IntEnum for type-safe constants"
    - "Registry pattern for unique naming"
    - "Regex-based file parsing"

key-files:
  created:
    - quickice/gui/constants.py
    - quickice/structure_generation/moleculetype_registry.py
    - quickice/structure_generation/itp_parser.py
  modified: []

key-decisions:
  - "Use IntEnum (not plain Enum) for automatic int conversion in tab indices"
  - "Registry uses source keys (hydrate_CH4, liquid_CH4) to track molecule origins"
  - "ITP parser uses regex-based parsing instead of third-party library"

patterns-established:
  - "Type-safe constants: Use IntEnum for index values to prevent hardcoded integer bugs"
  - "Registry pattern: Track molecule sources with unique naming for GROMACS export"
  - "Parser design: Use stdlib regex for simple file formats, avoid dependencies"

# Metrics
duration: 1 min
completed: 2026-05-04
---

# Phase 32 Plan 01: Architecture Foundation Summary

**Three foundational modules: TabIndex enum for type-safe tab references, MoleculetypeRegistry for unique GROMACS moleculetype naming, and ITP parser for topology file parsing**

## Performance

- **Duration:** 1 min
- **Started:** 2026-05-04T22:21:03Z
- **Completed:** 2026-05-04T22:22:20Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- TabIndex IntEnum provides type-safe tab references matching current v4.0 positions (ICE=0, HYDRATE=1, INTERFACE=2, ION=3)
- MoleculetypeRegistry tracks molecule types from different sources with unique GROMACS names (CH4_HYD vs CH4_LIQ)
- ITP parser extracts molecule information (name, atom count, atom types) from GROMACS .itp files

## Task Commits

Each task was committed atomically:

1. **Task 1: Create TabIndex enum** - `c975f8f` (feat)
2. **Task 2: Create MoleculetypeRegistry module** - `ffd66e6` (feat)
3. **Task 3: Create ITP parser module** - `0a61ebc` (feat)

## Files Created/Modified

- `quickice/gui/constants.py` - TabIndex IntEnum with 4 tab positions for type-safe tab references
- `quickice/structure_generation/moleculetype_registry.py` - Registry for unique GROMACS moleculetype naming with reserved name protection
- `quickice/structure_generation/itp_parser.py` - GROMACS ITP file parser extracting molecule name, atom count, and atom types

## Decisions Made

- **IntEnum for tab indices**: Use IntEnum (not plain Enum) for automatic integer conversion, enabling direct use with QTabWidget indices
- **Source key pattern in registry**: Registry uses source keys like "hydrate_CH4" and "liquid_CH4" to track molecule origins, allowing same molecule from different sources to have distinct GROMACS names
- **Regex-based ITP parsing**: Use stdlib regex instead of third-party parser to minimize dependencies and handle GROMACS format variations

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all modules created successfully on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

All three foundational modules are ready for integration:
- **TabIndex** can replace hardcoded tab indices in main_window.py
- **MoleculetypeRegistry** ready for use in gromacs_writer.py to generate unique moleculetype names
- **ITP parser** ready for use in solute/custom molecule validation

Next plan should integrate these modules into existing codebase and add solute insertion tab functionality.

---
*Phase: 32-architecture-preparation*
*Completed: 2026-05-04*
