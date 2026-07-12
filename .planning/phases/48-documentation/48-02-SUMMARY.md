---
phase: 48-documentation
plan: 02
subsystem: docs
tags: [readme, version-sweep, v4.7, known-issues, footer, documentation]

# Dependency graph
requires:
  - phase: 48-01
    provides: README Tab 1 hydrate rewrite (added Custom Guest in Hydrate Workflow subsection) — shifted line numbers so this plan READ README first to find current positions
  - phase: 48-13
    provides: Version bump 4.5.0 → 4.7.0 in quickice/__init__.py + quickice/cli/parser.py (makes the v4.7 README strings truthful)
provides:
  - README subtitle (line 14) now says QuickIce v4.7 (was v4.5)
  - README footer subtitle (line 425) now says "QuickIce v4.7 — Extended Hydrate Generation" (was "v4.5 — Solute & Custom Molecule Insertion")
  - README footer last-updated date (line 426) bumped 2026-06-15 → 2026-07-12
  - README Known Issues no longer falsely claims "Only pure water ice systems supported" (removed — QuickIce v4.7 supports hydrates, filled ices, and custom guests)
  - README Known Issues CLI support line references v4.7 (was v4.5 features)
affects: [48-RESEARCH D2 final verification sweep, future docs phases that re-verify README version strings, any plan referencing README Known Issues]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "README version strings (subtitle, footer, Known Issues CLI line) swept in lockstep with the code __version__ bump (48-13) — docs and code version must match"
    - "False Known Issues claim removed entirely (NOT replaced with a watered-down caveat) when the underlying capability shipped — keeps limitations list honest"

key-files:
  created: []
  modified:
    - README.md

key-decisions:
  - "Removed the 'Only pure water ice systems supported' line ENTIRELY rather than rewriting it as a caveat — QuickIce v4.7 supports hydrate systems, filled-ice systems, and custom guest molecules, so any residual caveat would still be misleading"
  - "Footer subtitle changed from 'Solute & Custom Molecule Insertion' to 'Extended Hydrate Generation' to reflect the v4.7 feature focus (per plan)"
  - "Bumped last-updated date to 2026-07-12 (plan-specified; matches the 48-13 version bump + 48-01 Tab 1 rewrite completion date)"
  - "Did NOT touch body-text v4.7 references added by 48-01 (lines 129, 140, 147 — Custom Guest Workflow subsection) — those are intentional v4.7 references, not stale v4.5 strings"

patterns-established:
  - "Pattern: version-string sweep covers three locations — subtitle (line 14), Known Issues CLI line, footer (subtitle + date) — all three must move in lockstep with code __version__"
  - "Pattern: when a Known Issues claim becomes false due to shipped capability, delete it; do not replace with a weaker caveat (a weaker caveat still misrepresents the capability)"

# Metrics
duration: < 1 min
completed: 2026-07-12
---

# Phase 48 Plan 02: README Version Sweep Summary

**Swept README version strings v4.5 → v4.7 (subtitle, footer subtitle, last-updated date) and removed the false "Only pure water ice systems supported" Known Issues claim, updating the CLI support line to v4.7**

## Performance

- **Duration:** < 1 min (~56 sec)
- **Started:** 2026-07-12T17:40:52Z
- **Completed:** 2026-07-12T17:41:48Z
- **Tasks:** 2
- **Files modified:** 1 (README.md, 5 line-level edits across 2 tasks)

## Accomplishments
- README subtitle now reads "QuickIce v4.7 provides a 6-tab GUI workflow..." (was v4.5) — aligns with the code __version__ bump in 48-13
- README footer subtitle now reads "QuickIce v4.7 — Extended Hydrate Generation" (was "v4.5 — Solute & Custom Molecule Insertion") — reflects the v4.7 feature focus
- README footer last-updated date bumped 2026-06-15 → 2026-07-12
- Removed the false "Only pure water ice systems supported" Known Issues line entirely — QuickIce v4.7 supports hydrate systems, filled-ice systems, and custom guest molecules; no watered-down caveat added
- Updated Known Issues CLI support line from "v4.5 features (Tabs 3-5)" to "v4.7 features" — the (Tabs 3-5) qualifier dropped per plan (the CLI now covers the v4.7 feature set)
- Three valid Known Issues retained unchanged: ranking uses distance-based energy estimates, some phase boundaries have limited experimental data, high-pressure phases (> 30 GPa) have larger uncertainties

## Task Commits

Each task was committed atomically:

1. **Task 1: Sweep version strings v4.5 → v4.7 (subtitle, footer subtitle + date)** - `796ba2c` (docs)
2. **Task 2: Remove "Only pure water" lie + update CLI support line (Known Issues)** - `db4374e` (docs)

## Files Created/Modified
- `README.md` — line 14 (subtitle v4.5→v4.7), line 309 (removed "Only pure water" lie, updated CLI line v4.5→v4.7), line 425 (footer subtitle v4.5→v4.7 + subtitle text), line 426 (last-updated date 2026-06-15→2026-07-12)

## Decisions Made
- Removed the false "Only pure water" claim entirely rather than rewriting it as a caveat — per plan instruction "do NOT replace it with a watered-down caveat" (QuickIce v4.7 supports hydrates, filled ices, and custom guests)
- Footer subtitle text changed from "Solute & Custom Molecule Insertion" to "Extended Hydrate Generation" per plan (reflects v4.7 feature focus)
- Updated CLI support line to drop the "(Tabs 3-5)" qualifier per plan's exact target text ("CLI support for v4.7 features is available via `python -m quickice`")

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- README version strings now consistent with the code __version__ (4.7.0 per 48-13) and the Tab 1 hydrate rewrite (48-01)
- The false "pure water only" claim is gone, so the README no longer misrepresents v4.7 hydrate/filled-ice/custom-guest capabilities
- Line numbers shifted from the plan's references (14→14, 296→309, 297→310, 413→425, 414→426) due to the 48-01 Custom Guest subsection insertion — handled by reading README.md first and locating the actual current positions; no impact on correctness
- Ready for the remaining 48-documentation plans (48-04/05/07/10/11/14) and the 48-RESEARCH D2 final verification sweep

---
*Phase: 48-documentation*
*Completed: 2026-07-12*
