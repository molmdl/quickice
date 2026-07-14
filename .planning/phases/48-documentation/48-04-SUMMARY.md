---
phase: 48-documentation
plan: 04
subsystem: docs
tags: [gui-guide, hydrate, custom-guest, mixed-cage-occupancy, depol-mode, v4.7, gaff2]

# Dependency graph
requires:
  - phase: 48-03
    provides: GUI guide Hydrate Tab 1 lattice types table (10 rows) that this plan's Workflow step 1 references
provides:
  - GUI guide Tab 1 Custom Guest Upload subsection (GUI-only for v4.7, 5-step upload→validate→select→generate→export)
  - GUI guide Tab 1 Mixed Cage Occupancy subsection (per-cage-type guest QComboBox + occupancy QDoubleSpinBox)
  - GUI guide Tab 1 Depol Mode subsection (strict default vs optimal)
  - Fixed Workflow steps referencing all 10 lattice types instead of "sI, sII, or sH"
affects: [48-05 (GUI guide header/version sweep v4.5→v4.7), 48-10 (help_dialog content pages mirror these subsections), DOCS-02-ext]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Per-cage-type mixed occupancy documentation: one row per cage_type_map key with independent guest + occupancy", "GUI-only feature flagging via inline '(GUI-only for v4.7)' + blockquote Note"]

key-files:
  created: []
  modified: [docs/gui-guide.md]

key-decisions:
  - "Sourced all subsection content from quickice/gui/hydrate_panel.py actual v4.7 controls (per-cage combos/spins, depol combo) not the plan's paraphrased text — REAL feature names only"
  - "Verified the GRO/ITP guide heading 'Custom Guest ITP Requirements (for Hydrate Cage Guests)' at line 568 exists before linking to its GitHub anchor #custom-guest-itp-requirements-for-hydrate-cage-guests (AGENTS.md: never make up references)"
  - "Did NOT touch the Overview bullet 'Select hydrate lattice type (sI, sII, sH)' at line 233 — belongs to a different cross-cutting sweep plan, not this plan's subsection scope"

patterns-established:
  - "GUI guide Tab 1 subsection ordering: Guest Molecules → Mixed Cage Occupancy → Custom Guest Upload → Depol Mode → Supercell → Workflow"
  - "Custom guest in hydrate documented as GUI-only with CLI limitation note in a blockquote"

# Metrics
duration: 36h 21m (wall-clock; spans continuation pause — active work ~5 min)
completed: 2026-07-14
---

# Phase 48 Plan 04: GUI Guide Subsections Summary

**3 new Hydrate Tab 1 subsections (Custom Guest Upload GUI-only, Mixed Cage Occupancy per-cage-type, Depol Mode strict/optimal) + fixed Workflow steps referencing all 10 lattice types**

## Performance

- **Duration:** 36h 21m (wall-clock spans a continuation pause; active editing work ~5 min)
- **Started:** 2026-07-12T17:41:43Z
- **Completed:** 2026-07-14T06:03:14Z
- **Tasks:** 2
- **Files modified:** 1 (docs/gui-guide.md)

## Accomplishments
- Added Custom Guest Upload subsection within Tab 1, marked GUI-only for v4.7, with the 5-step upload→validate→select→generate→export workflow and a verified link to the GRO/ITP guide's Custom Guest ITP Requirements section
- Replaced the outdated "Small cages / Large cages" Cage Occupancy text with a Mixed Cage Occupancy subsection covering per-cage-type controls, multi-guest systems, per-cage occupancy, and water-only/filled-ice special cases
- Added Depol Mode subsection documenting strict (default) vs optimal, noting GenIce2 2.2.13.1 produces identical atom counts (mode affects H-bond orientation only)
- Fixed the Workflow steps: step 1 now references all 10 lattice types (filled-ice/water-only + Lattice Types table), step 2 covers per-cage guest + occupancy, step 3 covers depol mode

## Task Commits

Each task was committed atomically:

1. **Task 1: Add 3 new subsections (Custom Guest Upload, Mixed Cage Occupancy, Depol Mode)** - `6c16dad` (docs)
2. **Task 2: Fix outdated Workflow steps (sI, sII, sH → all 10 lattice types)** - `3a5bef0` (docs)

**Plan metadata:** (pending — final docs commit after this SUMMARY)

## Files Created/Modified
- `docs/gui-guide.md` — Tab 1 (Hydrate Generation): added Custom Guest Upload note in Guest Molecules, replaced Cage Occupancy with Mixed Cage Occupancy, added Custom Guest Upload + Depol Mode subsections, fixed Workflow steps

## Decisions Made
- Sourced all subsection content from `quickice/gui/hydrate_panel.py` actual v4.7 controls (per-cage `QComboBox`/`QDoubleSpinBox` rows built in `_rebuild_cage_rows`, depol `QComboBox` in `_create_depol_group`) rather than the plan's paraphrased text — AGENTS.md forbids fabricating feature names. Confirmed the `_H` suffix, comb-rule=2, and ≤3-char residue rules match the engine validator in `custom_guest_bridge.py` and the GRO/ITP guide.
- Verified the GRO/ITP guide target heading `## Custom Guest ITP Requirements (for Hydrate Cage Guests)` exists at line 568 before writing the link `gro-itp-guide.md#custom-guest-itp-requirements-for-hydrate-cage-guests` (AGENTS.md: never make up references). The GitHub-style anchor derived from the lowercase-hyphenated heading matches the link exactly.
- Did NOT modify the Overview bullet at line 233 (`- Select hydrate lattice type (sI, sII, sH)`) — that line is outside this plan's subsection scope and belongs to a cross-cutting version-sweep plan (48-05). Only the Workflow steps (this plan's explicit target) and the three new subsections were changed.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 48-04 complete; closes the GUI guide subsection portion of DOCS-02-ext (Custom Guest Upload, Mixed Cage Occupancy, Depol Mode, fixed Workflow steps).
- The remaining Overview bullet "sI, sII, sH" at line 233 is intentionally left for the cross-cutting version-sweep plan 48-05 (GUI guide header/version sweep v4.5→v4.7).
- Plan 48-10 (help_dialog content pages) can mirror these three new subsections into the in-app help Quick Reference dialog's Hydrate section.
- No blockers.

---
*Phase: 48-documentation*
*Completed: 2026-07-14*
