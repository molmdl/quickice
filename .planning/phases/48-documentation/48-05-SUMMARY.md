---
phase: 48-documentation
plan: 05
subsystem: docs
tags: [gui-guide, version-sweep, v4.7, v4.5, cross-cutting]

# Dependency graph
requires:
  - phase: 48-04
    provides: GUI guide Tab 1 subsections (Custom Guest Upload, Mixed Cage Occupancy, Depol Mode) + fixed Workflow steps whose insertion shifted line numbers for this plan's targets
  - phase: 48-13
    provides: Code __version__ bump 4.5.0 → 4.7.0 making the v4.7 documentation strings truthful
provides:
  - GUI guide header (line 3) swept v4.5 → v4.7 (describes the CURRENT version)
  - GUI guide image caption (line 39) swept v4.5 → v4.7 (describes the CURRENT version)
  - GUI guide version note (line 40) rephrased to keep v4.5 as clearly historical ("v4.5 added") + add v4.7 as the current version ("v4.7 adds Extended Hydrate Generation")
  - GUI guide body reference (line 182) rephrased to keep v4.5 as clearly historical ("v4.5 added") + add v4.7 as the current version ("v4.7 adds extended hydrate generation")
affects: [48-14 (final verification sweep — confirms no stale v4.5 current-version strings remain across all docs), DOCS-02-ext]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Version-sweep rephrase pattern: historical 'vX.Y adds' → 'vX.Y added' (past tense) + append 'vCURRENT adds ...' so the current version is named while prior versions stay clearly historical"]

key-files:
  created: []
  modified: [docs/gui-guide.md]

key-decisions:
  - "Rephrased historical 'v4.5 adds' → 'v4.5 added' (past tense) on lines 40 and 182 to clearly mark v4.5 as historical, then appended 'v4.7 adds ...' for the current version — per plan guidance that historical references are acceptable if clearly historical but the current version must be v4.7"
  - "Matched line 182 version-history sentence phrasing to cli-reference.md (plan 48-07) for cross-doc consistency: 'v4.0 added interface construction; v4.5 added solute and custom molecule insertion; v4.7 adds extended hydrate generation with filled ices, custom guests, mixed cage occupancy, and depol mode'"
  - "Read the file with the Read tool first to get exact line text before editing — line numbers shifted after 48-03 (lattice table) and 48-04 (subsections) added content, per project_context instruction"

patterns-established:
  - "Cross-cutting version sweep: current-version strings (header, caption) get a straight vX.Y → vCURRENT bump; historical 'adds' mentions get rephrased to past-tense 'added' + a new 'vCURRENT adds ...' clause appended"

# Metrics
duration: 1 min
completed: 2026-07-14
---

# Phase 48 Plan 05: GUI Guide Version Sweep Summary

**Swept v4.5 → v4.7 version strings at the GUI guide header (line 3), image caption (line 39), version note (line 40), and body reference (line 182), rephrasing historical v4.5 mentions to past tense while naming v4.7 as the current version**

## Performance

- **Duration:** 1 min
- **Started:** 2026-07-14T06:08:25Z
- **Completed:** 2026-07-14T06:09:53Z
- **Tasks:** 1
- **Files modified:** 1 (docs/gui-guide.md)

## Accomplishments
- Swept the GUI guide header (line 3) and image caption (line 39) from v4.5 → v4.7 — these describe the CURRENT version shown in the screenshot and must not be stale
- Rephrased the version note (line 40): "v4.5 adds Custom Molecule..." → "v4.5 added Custom Molecule..., moving Ion to Tab 5; v4.7 adds Extended Hydrate Generation (filled ices, custom guests, mixed cage occupancy, depol mode)" — v4.5 kept as clearly historical, v4.7 named as the current version
- Rephrased the body reference (line 182): "v4.5 adds solute and custom molecule insertion..." → "v4.5 added solute and custom molecule insertion; v4.7 adds extended hydrate generation with filled ices, custom guests, mixed cage occupancy, and depol mode, with direct GROMACS export..." — matches the cli-reference.md (48-07) version-history sentence for cross-doc consistency
- Verified: only clearly-historical "v4.5 added" references remain (past tense); no stale v4.5 as the current version

## Task Commits

Each task was committed atomically:

1. **Task 1: Sweep v4.5 → v4.7 at lines 3, 39-40, 182** - `367a5be` (docs)

**Plan metadata:** (pending — final docs commit after this SUMMARY)

## Files Created/Modified
- `docs/gui-guide.md` — Header line 3 (v4.5→v4.7), image caption line 39 (v4.5→v4.7), version note line 40 (v4.5 adds→v4.5 added + v4.7 adds Extended Hydrate Generation), body reference line 182 (v4.5 adds→v4.5 added + v4.7 adds extended hydrate generation)

## Decisions Made
- Rephrased historical "v4.5 adds" → "v4.5 added" (past tense) on lines 40 and 182, then appended "v4.7 adds ..." clauses — per plan guidance that historical references are acceptable if clearly historical, but the header/caption (describing the CURRENT version) MUST say v4.7. A straight version bump on the historical notes would have been inaccurate (v4.7 did not add Custom Molecule; v4.5 did), so the rephrase preserves historical accuracy while naming v4.7 as the current version.
- Matched line 182's version-history sentence to the phrasing already established in `docs/cli-reference.md` (plan 48-07): "v4.0 added interface construction; v4.5 added solute and custom molecule insertion; v4.7 adds extended hydrate generation with filled ices, custom guests, mixed cage occupancy, and depol mode" — ensures cross-document consistency for the v4.7 feature narrative.
- Read the file with the Read tool first to get exact line text before editing (line numbers shifted after 48-03 added the lattice table and 48-04 added the subsections), per the project_context instruction. Confirmed lines 3, 39, 40, 182 matched the plan's expected content before editing.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 48-05 complete; closes the GUI guide cross-cutting version-sweep portion of the documentation work (header + caption + body references all name v4.7 as the current version).
- Only clearly-historical "v4.5 added" references remain in docs/gui-guide.md (lines 40, 182), which is acceptable per the plan's verification criteria.
- Plan 48-14 (final verification sweep) can confirm no stale v4.5 current-version strings remain across all docs (README swept by 48-02, CLI ref swept by 48-07, GUI guide swept by this plan, GRO/ITP guide swept by 48-08).
- No blockers.

---
*Phase: 48-documentation*
*Completed: 2026-07-14*
