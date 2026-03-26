---
phase: 04-ranking
plan: 02
subsystem: ranking
tags: [scoring, energy, density, diversity, pbc, candidate-ranking]

# Dependency graph
requires:
  - phase: 03-structure-generation
    provides: Candidate objects with positions, atom_names, cell, metadata
provides:
  - energy_score function for O-O distance deviation
  - density_score function for density deviation
  - diversity_score function for seed-based diversity
affects: [04-03, 04-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Minimum image convention for PBC calculations
    - Heuristic scoring based on O-O distances
    - Seed-based diversity for single-phase generation

key-files:
  created:
    - quickice/ranking/scorer.py
  modified: []

key-decisions:
  - "Manual PBC implementation instead of scipy.spatial.distance.cdist (doesn't handle PBC)"
  - "Energy score scaled by 100 for visibility (typical 0.001-0.01 nm deviations)"
  - "Default density 0.9167 g/cm³ (ice Ih) when not in metadata"

patterns-established:
  - "Lower scores = better structures (energy, density)"
  - "Higher scores = better structures (diversity)"
  - "All scoring functions work with Candidate objects from Phase 3"

# Metrics
duration: 2 min
completed: 2026-03-26
---

# Phase 4 Plan 2: Scoring Functions Summary

**Implemented three heuristic scoring functions for ranking ice structure candidates: energy (O-O distance deviation), density (deviation from expected), and diversity (seed uniqueness)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-26T16:55:00Z
- **Completed:** 2026-03-26T16:57:22Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments
- Implemented energy_score with PBC-aware O-O distance calculation
- Implemented density_score with proper unit conversions (nm³ to cm³)
- Implemented diversity_score using seed-based approach for single-phase generation

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement energy_score function** - `7537a8c` (feat)
2. **Task 2: Implement density_score function** - `fd29d12` (feat)
3. **Task 3: Implement diversity_score function** - `014cd31` (feat)

## Files Created/Modified
- `quickice/ranking/scorer.py` - Three scoring functions with PBC support and docstrings

## Decisions Made
- Used manual minimum image convention for PBC instead of scipy.spatial.distance.cdist (doesn't handle PBC directly)
- Scaled energy score by 100 for visibility (typical deviations are 0.001-0.01 nm)
- Default density of 0.9167 g/cm³ (ice Ih) when not provided in metadata

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - all functions implemented and verified successfully.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Three scoring functions ready for use in ranking integration
- Energy score uses PBC-aware distance calculation
- Density score calculates deviation from expected phase density
- Diversity score uses seed-based approach for single-phase
- Ready for 04-03-PLAN.md (ranking integration)

---
*Phase: 04-ranking*
*Completed: 2026-03-26*
