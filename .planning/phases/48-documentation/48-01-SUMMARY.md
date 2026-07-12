---
phase: 48-documentation
plan: 01
subsystem: docs
tags: [readme, hydrate, lattice-types, custom-guest, mixed-occupancy, depol, documentation, v4.7]

# Dependency graph
requires:
  - phase: 39-extended-hydrate-lattices
    provides: 10 hydrate lattice types in HYDRATE_LATTICES (sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime, 16, 17) with cage_type_map/is_triclinic/is_water_only metadata
  - phase: 40-custom-guest-hydrate
    provides: Custom guest upload (.gro + .itp) for hydrate cages with comb-rule=2 + <=3-char residue validation (GUI-only for v4.7)
  - phase: 42-mixed-cage-occupancy
    provides: Per-cage-type guest assignment (CageGuestAssignment) + repeatable --cage-guest CLI flag
  - phase: 43-depol-mode
    provides: depol_mode field (strict|optimal, default strict) validated in HydrateConfig.__post_init__
provides:
  - README Tab 1 bullet list listing all 10 v4.7 hydrate lattice types (not just sI, sII, sH)
  - README "Custom Guest in Hydrate Workflow" subsection with the 4-step upload->validate->generate->export workflow (DOCS-01 success criterion)
  - README mentions of mixed cage occupancy and depol mode as hydrate features
affects: [48-RESEARCH D2 final verification sweep, future docs phases referencing README Tab 1 hydrate coverage]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "README Tab 1 lattice list sourced from HYDRATE_LATTICES keys in types.py (sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime, 16, 17) — code is the source of truth"
    - "Custom guest workflow rules stated verbatim from engine: comb-rule=2, <=3 char residue base name, _H suffix (sourced from types.py:591-615 + 48-RESEARCH DOCS-04)"

key-files:
  created: []
  modified:
    - README.md

key-decisions:
  - "Sourced the 10 lattice keys verbatim from quickice/structure_generation/types.py HYDRATE_LATTICES (verified against code) — did not invent flag names"
  - "Marked custom guest in hydrate as GUI-only for v4.7 (no CLI flag); CLI uses --cage-guest for built-in CH4/THF per STATE.md line 183 + 48-RESEARCH Pitfall 1"
  - "Used exact rule language from research: comb-rule=2 (not AMBER-compatible), <=3 chars (not short), _H suffix (not renamed)"
  - "Kept README overview line 17 (Features TOC bullet 'sI, sII, sH') untouched — out of scope for this plan; belongs to the version-sweep plan (RESEARCH A2: lines 14, 296-297, 413-414)"

patterns-established:
  - "Pattern: README Tab 1 feature bullets sourced from code constants (HYDRATE_LATTICES) and engine validation rules (types.py), not hand-maintained prose"

# Metrics
duration: 1 min
completed: 2026-07-12
---

# Phase 48 Plan 01: README Tab 1 Hydrate Rewrite Summary

**README Tab 1 rewritten to list all 10 v4.7 hydrate lattice types plus a new Custom Guest in Hydrate Workflow subsection (upload->validate->generate->export) with mixed cage occupancy and depol mode bullets**

## Performance

- **Duration:** ~1 min (76 sec)
- **Started:** 2026-07-12T07:55:22Z
- **Completed:** 2026-07-12T07:56:38Z
- **Tasks:** 2
- **Files modified:** 1 (README.md, two edits)

## Accomplishments
- Replaced the outdated 5-bullet Tab 1 list (which named only sI, sII, sH + CH4/THF) with a 7-bullet list covering all 10 v4.7 lattice types, custom guest upload, mixed cage occupancy, depol mode, and per-type rendering
- Added a new "Custom Guest in Hydrate Workflow" subsection with the 4-step upload -> validate -> generate -> export workflow, explicitly marking the feature GUI-only for v4.7 and documenting the exact ITP rules (comb-rule=2, residue base name <=3 chars, _H suffix)
- Preserved the Tab 1 heading, intro line, and the "Export includes bundled GAFF2 parameters" note unchanged; the subsection is inserted between Tab 1 and Tab 2

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite Tab 1 bullet list with 10 lattices + custom guest + mixed occupancy + depol** - `52381f7` (docs)
2. **Task 2: Add "Custom Guest in Hydrate Workflow" subsection** - `a034349` (docs)

**Plan metadata:** (pending final commit)

## Files Created/Modified
- `README.md` - Tab 1: Hydrate Generation section (lines 124-147): replaced 5-bullet list with 7-bullet list (10 lattices + custom guest + mixed occupancy + depol) and inserted new "Custom Guest in Hydrate Workflow" subsection with 4-step workflow + GUI-only note

## Decisions Made
- Sourced the 10 lattice keys verbatim from `quickice/structure_generation/types.py` `HYDRATE_LATTICES` (sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime, 16, 17) — verified the keys and the custom-guest validation rules (types.py:591-615) against the code before writing the prose. Did not invent CLI flag names (`--custom-guest`/`--hydrate-lattice`/`--guest-small`/`--guest-large` do NOT exist per 48-RESEARCH Pitfall 1).
- Marked custom guest in hydrate as GUI-only for v4.7 with no CLI flag; the CLI supports built-in CH4/THF guests via `--cage-guest` (per STATE.md line 183 and 48-RESEARCH §3).
- Used the exact rule language from the research: "comb-rule=2" (not "AMBER-compatible"), "<=3 chars" (not "short"), "`_H` suffix" (not "renamed") — sourced from types.py:591-615 and 48-RESEARCH §DOCS-04.
- Kept README.md line 17 (the Features overview TOC bullet "Clathrate structures (sI, sII, sH)") untouched. It is outside the Tab 1 section (lines 124-147) and belongs to the separate version-sweep plan (48-RESEARCH §6 plan A2: lines 14, 296-297, 413-414). The plan's verification check "the lone 3-lattice list in Tab 1 must be GONE" is satisfied: Tab 1 (line 128) now lists all 10.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- 48-01 (README Tab 1 hydrate rewrite + custom guest workflow subsection) is complete. DOCS-01 success criterion #1 (README documents the custom-guest-in-hydrate upload->validate->generate->export workflow) is satisfied.
- Ready for the remaining 48-documentation plans per the RESEARCH split strategy (e.g. 48-02 in-app help restructure, plus the version/known-issues sweep that owns README lines 14/17/296-297/413-414).
- No blockers or concerns. Note: other 48-documentation plans (48-03, 48-06) were executed in parallel by sibling agents; their artifacts (docs/gui-guide.md, docs/cli-reference.md, 48-03-SUMMARY.md) were intentionally left untouched by this plan.

---
*Phase: 48-documentation*
*Completed: 2026-07-12*
