---
phase: 07-audit-correctness
plan: 01
subsystem: documentation
tags: [doi, citations, verification, genice2, spglib]

# Dependency graph
requires:
  - phase: 06-documentation
    provides: README.md and docs/ with existing citations
provides:
  - Verified DOIs for GenIce2 and spglib
  - Correct GenIce2 repository URL
  - Complete citation sections in both files
affects: [documentation, citations]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - README.md
    - docs/principles.md

key-decisions:
  - "Always verify DOI resolves correctly before adding to documentation"
  - "IAPWS releases are web documents, not journal papers - use official URL only"

patterns-established:
  - "Use webfetch https://doi.org/{doi} to verify DOIs before citing"

# Metrics
duration: 15 min
completed: 2026-03-28
---

# Phase 7 Plan 1: Citation Audit and Fix Summary

**Verified and corrected all DOIs in project documentation with explicit verification.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-28T15:09:47Z
- **Completed:** 2026-03-28T15:15:00Z
- **Tasks:** 5
- **Files modified:** 2

## Accomplishments
- Discovered GenIce2 DOI was incorrect (10.1002/jcc.25179 pointed to wrong paper)
- Found correct GenIce2 DOI (10.1002/jcc.25077) from official CITATION.cff
- Verified spglib DOI is correct (10.1080/27660400.2024.2384822)
- Fixed GenIce2 repository URL from vitroid/GenIce to genice-dev/GenIce2
- Added spglib citation section to docs/principles.md

## Task Commits

Each task was committed atomically:

1. **Task 1: Verify GenIce2 DOI** - No code changes (verification only)
2. **Task 2: Verify spglib DOI** - No code changes (verification only)
3. **Task 3: Fix GenIce2 URL** - `0eaabd4` (fix)
4. **Task 4: Fix GenIce2 DOI in README.md** - `35eb0f7` (fix)
5. **Task 5: Add verified citations to docs/principles.md** - `eefe15d` (fix)

## Files Created/Modified
- `README.md` - Corrected GenIce2 DOI from wrong paper to correct one
- `docs/principles.md` - Fixed URL, added verified DOI, added spglib citation

## Decisions Made
- **Always verify DOIs before adding** - The previous fake DOI issue taught us to verify first
- **IAPWS uses URL only** - IAPWS releases are official documents, not journal papers; no DOI needed

## Deviations from Plan

None - plan executed exactly as written. All DOIs verified before adding.

## Issues Encountered

**Critical Discovery:** The GenIce2 DOI in README.md (10.1002/jcc.25179) was incorrect. It resolved to a different paper:
- **Wrong paper:** "Pressure tensor for electrostatic interaction calculated by fast multipole method" by Yoshii et al. (2018)
- **Correct paper:** "GenIce: Hydrogen-disordered ice structures by combinatorial generation" by Matsumoto et al. (2017)

This was caught by explicitly verifying the DOI via webfetch before accepting it.

## Authentication Gates

None - no authentication required for this plan.

## Next Phase Readiness
- Citations are now verified and correct
- Ready for next audit plan (07-02: Documentation consistency)

---
*Phase: 07-audit-correctness*
*Completed: 2026-03-28*
