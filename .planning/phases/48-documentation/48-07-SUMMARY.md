---
phase: 48-documentation
plan: 07
subsystem: docs
tags: [cli-reference, version-sweep, hydrate-examples, lattice-type, cage-guest, depol]

# Dependency graph
requires:
  - phase: 48-06
    provides: "Hydrate flags rewrite (--cage-guest + --depol subsections) that shifted cli-reference.md line numbers"
  - phase: 48-13
    provides: "Version bump 4.5.0 -> 4.7.0 in quickice/__init__.py + parser.py --version action"
provides:
  - "CLI reference --version example shows 4.7.0 (truthful vs actual binary)"
  - "Version-history sentence documenting v4.0/v4.5/v4.7 feature timeline"
  - "v4.7 Hydrate Examples subsection covering extended --lattice-type, mixed --cage-guest, --depol"
affects: [48-documentation, future-release-docs]

# Tech tracking
tech-stack:
  added: []
  patterns: ["docs version strings must track quickice/__version__ after each release bump"]

key-files:
  created: []
  modified: [docs/cli-reference.md]

key-decisions:
  - "Placed version-history sentence under --version section (natural contextual home) because research's cited line 182 had shifted after 48-06 — plan explicitly anticipated this"
  - "Kept the v4.5 mention as HISTORICAL in the version-history timeline (plan allows clearly-historical mentions); swept only stale CURRENT-version references"

patterns-established:
  - "Version sweeps: grep for the OLD version string, confirm zero CURRENT-version matches, allow historical mentions in timelines"

# Metrics
duration: ~3 min active (wall span 2026-07-12 -> 2026-07-14 includes continuation gap)
completed: 2026-07-14
---

# Phase 48 Plan 07: CLI Reference Version Sweep + v4.7 Hydrate Examples Summary

**Swept the --version example 4.5.0 -> 4.7.0, added a v4.0/v4.5/v4.7 version-history sentence, and a v4.7 Hydrate Examples subsection covering extended --lattice-type (c0te/sTprime/16), mixed --cage-guest occupancy, and --depol optimal**

## Performance

- **Duration:** ~3 min active execution (wall-clock span 2026-07-12T17:42Z -> 2026-07-14T06:03Z includes the continuation gap between initial prompt and resumed execution)
- **Started:** 2026-07-12T17:42:19Z
- **Completed:** 2026-07-14T06:03:27Z
- **Tasks:** 1
- **Files modified:** 1 (docs/cli-reference.md, +34/-1)

## Accomplishments
- --version example output updated 4.5.0 -> 4.7.0 (line 169), now truthful against `python -m quickice --version` which prints `python -m quickice 4.7.0` after plan 48-13's bump in parser.py
- Added a version-history sentence under the --version section documenting the feature timeline: v4.0 (interface), v4.5 (solute/custom molecule), v4.7 (extended hydrate: filled ices, custom guests, mixed cage occupancy, depol)
- Added a "v4.7 Hydrate Examples" subsection (after the --depol subsection, before Custom Molecule Insertion Flags) with 6 example commands covering: filled ice C0 (--lattice-type c0te --cage-guest small=CH4:100), water-only sTprime (no guests), mixed cage occupancy sI (CH4 small + THF large), sH with 3 cage types, depol optimal, and Ice XVI (empty sII framework, lattice-type 16)
- All examples use REAL flag names only (verified against quickice/cli/parser.py:199-280): --lattice-type (10 choices), --cage-guest (append, KEY=GUEST:OCC), --depol (strict|optimal). No invented flags.
- Included a cross-reference to the existing --cage-guest filled-ice gotcha to avoid duplicating the caveat

## Task Commits

Each task was committed atomically:

1. **Task 1: Sweep version strings + add v4.7 hydrate examples** - `25626dd` (docs)

**Plan metadata:** pending — SUMMARY + STATE commit follows this file's creation.

## Files Created/Modified
- `docs/cli-reference.md` --version example 4.5.0 -> 4.7.0; added version-history sentence; added "v4.7 Hydrate Examples" subsection (+34/-1 lines)

## Decisions Made
- **Placement of version-history sentence:** The research's cited line 182 ("v4.5 adds solute and custom molecule insertion") had shifted after plan 48-06's hydrate-flags rewrite added the --cage-guest + --depol subsections; `grep` confirmed NO `v4.5` text existed anywhere in the file at execution time. Per the plan's explicit instruction ("Read the actual line first and make the minimal appropriate edit"), placed the version-history sentence directly under the --version section (the natural, contextual home for a version timeline) rather than forcing it into a now-nonexistent line 182.
- **Kept v4.5 as historical:** The one remaining `v4.5` mention (line 172) is inside the version-history timeline sentence ("v4.5 added solute and custom molecule insertion") — clearly historical, not a current-version reference. The plan's verification explicitly allows "historical mentions OK if clearly historical." Only stale CURRENT-version references were swept.

## Deviations from Plan

### Line-number shift (anticipated, not a deviation)

- **Found during:** Task 1 (Edit 2)
- **Issue:** Plan referenced "line 182 contains v4.5 adds solute and custom molecule insertion" but 48-06's hydrate-flags rewrite shifted line numbers; the actual line 182 is a code fence, and `grep` confirmed no `v4.5` text exists anywhere in the file.
- **Handling:** The plan explicitly anticipated this ("READ the file first to find exact line numbers — they shifted after 48-06" and "Read the actual line first and make the minimal appropriate edit"). Placed the version-history sentence under the --version section. No deviation from plan intent — plan's anticipated-research-outdated clause was followed exactly.

**Total deviations:** 0 (the line-number shift was anticipated by the plan's own instructions, not an unplanned deviation)
**Impact on plan:** None — plan executed as written, including its anticipated-research-outdated clause.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 48-07 (version + examples sweep) is complete and non-overlapping with 48-06 (hydrate flags rewrite). Together they close the cli-reference.md v4.7 update.
- Remaining Phase 48 plans (48-02, 48-04, 48-05, 48-10, 48-11, 48-14) touch other docs/help_dialog files and do not depend on 48-07.
- Note: an uncommitted `quickice/gui/help_dialog.py` modification exists in the working tree (belongs to a different parallel plan, likely 48-10) — left untouched and unstaged by this plan's atomic commit.

---
*Phase: 48-documentation*
*Completed: 2026-07-14*
