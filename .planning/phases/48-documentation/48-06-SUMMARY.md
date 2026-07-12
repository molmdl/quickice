---
phase: 48-documentation
plan: 06
subsystem: docs
tags: [cli-reference, hydrate, lattice-types, cage-guest, depol, deprecated, v4.7, filled-ice, documentation]

# Dependency graph
requires:
  - phase: 39-extended-hydrate-lattices
    provides: 10 hydrate lattice types in HYDRATE_LATTICES (sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime, 16, 17) with cage_type_map/is_triclinic/is_water_only metadata
  - phase: 42-mixed-cage-occupancy
    provides: --cage-guest CLI flag (repeatable KEY=GUEST:OCC) + HydrateConfig.cage_guest_assignments
  - phase: 43-depol-mode
    provides: --depol CLI flag (strict|optimal, default strict)
  - phase: 47-testing-validation
    provides: triclinic blocking confirmed for c0te/c1te (interface_builder.py:121 TRICLINIC_HYDRATE_PHASES)
provides:
  - CLI reference --lattice-type subsection documenting all 10 choices with per-type properties table + behavior notes (triclinic, water-only, filled-ice gotcha)
  - CLI reference --cage-guest subsection (repeatable KEY=GUEST:OCC format, examples, filled-ice gotcha, GUI-only note)
  - CLI reference --depol subsection (strict|optimal, default strict)
  - DEPRECATED banners on --guest, --cage-occupancy-small, --cage-occupancy-large (kept for backward compat, no behavior change)
  - GUI-only note for custom guest in hydrate (no CLI flag for v4.7)
affects: [48-RESEARCH D2 final verification sweep, future docs phases referencing CLI hydrate flag coverage, end users reading CLI reference for v4.7 hydrate flags]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CLI reference flag docs sourced verbatim from parser.py add_argument help text (lines 206-280) — the parser is the single source of truth for flag wording"
    - "Per-type properties table sourced from HYDRATE_LATTICES (types.py:84-199) — code is the source of truth, not hand-maintained counts"
    - "Deprecated flags kept with DEPRECATED banners (no removal) — backward compatibility preserved with no behavior change"

key-files:
  created: []
  modified:
    - docs/cli-reference.md

key-decisions:
  - "Sourced all 10 table rows from HYDRATE_LATTICES (types.py:84-199) — verified each cage_type_map, is_triclinic, and is_water_only value against the code before finalizing"
  - "Sourced --cage-guest and --depol help text verbatim from parser.py:260-280 (the add_argument calls) — used the EXACT wording including 'built-in only on CLI for v4.7'"
  - "Verified triclinic blocking against interface_builder.py:121 (TRICLINIC_HYDRATE_PHASES = {hydrate_c0te, hydrate_c1te}) — documented that sH is triclinic but NOT blocked"
  - "Kept --guest/--cage-occupancy-small/--cage-occupancy-large documentation intact with DEPRECATED banners (matches parser.py help text which already says 'deprecated; use --cage-guest for mixed occupancy')"
  - "Documented the filled-ice cage-key gotcha in both --lattice-type (forward reference) and --cage-guest (detailed: use 'small' not 'guest'; guest=CH4:100 produces 0 guests)"
  - "Explicitly noted custom guest in hydrate is GUI-only for v4.7 — no CLI flag exists for custom guest upload"

patterns-established:
  - "Pattern: CLI reference hydrate flag docs sourced from parser.py add_argument calls (help text) + types.py HYDRATE_LATTICES (per-type properties) — keeps docs in sync with code"
  - "Pattern: DEPRECATED flags are marked with banner but NOT removed — backward compat with no behavior change is the QuickIce convention"

# Metrics
duration: 2 min
completed: 2026-07-12
---

# Phase 48 Plan 06: CLI Reference Hydrate Flags Rewrite Summary

**Rewrote docs/cli-reference.md hydrate flags section: 10-row --lattice-type table, new --cage-guest + --depol subsections, DEPRECATED banners on 3 legacy flags, filled-ice + GUI-only notes**

## Performance

- **Duration:** 2 min (1 min 19 sec)
- **Started:** 2026-07-12T07:55:58Z
- **Completed:** 2026-07-12T07:57:17Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Expanded the `--lattice-type` choices list from 3 (`sI`, `sII`, `sH`) to all 10 v4.7 choices with a per-type properties table (Choice, Description, Cage Keys, Water-Only, Triclinic) sourced from `HYDRATE_LATTICES` (types.py:84-199)
- Added three behavior notes to `--lattice-type`: triclinic blocking (c0te/c1te blocked in `--interface`; sH triclinic but not blocked), water-only (sTprime/17 ignore guests), and the filled-ice cage-key gotcha (use `small` not `guest`)
- Added a new `--cage-guest` subsection documenting the repeatable `KEY=GUEST:OCC` format, parameters, mixed-occupancy examples, the filled-ice gotcha, and the GUI-only custom-guest note
- Added a new `--depol` subsection documenting `strict`/`optimal` (default `strict`) with examples and the GenIce2 2.2.13.1 identical-atom-counts note
- Added DEPRECATED banners to `--guest`, `--cage-occupancy-small`, and `--cage-occupancy-large` (kept for backward compatibility, no behavior change)
- Verified no non-existent flags (`--custom-guest`, `--hydrate-lattice`, `--guest-small`, `--guest-large`) were documented

## Task Commits

Each task was committed atomically:

1. **Task 1: Expand --lattice-type to 10 choices with per-type table + notes** - `8a782cb` (docs)
2. **Task 2: Add --cage-guest + --depol subsections; mark deprecated flags; add GUI-only note** - `8536347` (docs)

**Plan metadata:** (pending final commit)

## Files Created/Modified
- `docs/cli-reference.md` - Hydrate Generation Flags section (lines 538-750): expanded `--lattice-type` to 10 choices + per-type table + notes; added `--cage-guest` and `--depol` subsections; added DEPRECATED banners to `--guest`/`--cage-occupancy-small`/`--cage-occupancy-large`; added GUI-only + filled-ice gotcha notes

## Decisions Made
- Sourced all 10 table rows verbatim from `quickice/structure_generation/types.py:84-199` (HYDRATE_LATTICES) — verified each `cage_type_map`, `is_triclinic`, and `is_water_only` value against the code before finalizing. The code is the source of truth, not the research summary.
- Sourced `--cage-guest` and `--depol` help text verbatim from `quickice/cli/parser.py:260-280` (the add_argument calls) — used the EXACT wording including "built-in only on CLI for v4.7" and the strict/optimal descriptions.
- Verified the triclinic-blocking claim against `quickice/structure_generation/interface_builder.py:121` (`TRICLINIC_HYDRATE_PHASES = {"hydrate_c0te", "hydrate_c1te"}`) — confirmed c0te/c1te are blocked in interface generation and sH (also `is_triclinic=True`) is NOT in the blocked set.
- Kept the `--guest`/`--cage-occupancy-small`/`--cage-occupancy-large` documentation intact (choices, defaults, examples) and prepended DEPRECATED banners — matching the parser.py help text which already says "(deprecated; use --cage-guest for mixed occupancy)". No removal, no behavior change.
- Documented the filled-ice cage-key gotcha in two places: a forward reference in the `--lattice-type` notes and the detailed gotcha in the `--cage-guest` subsection ("Using `--cage-guest guest=CH4:100` produces 0 guests").

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- 48-06 (CLI reference hydrate flags rewrite) is complete. The `--lattice-type` (10 choices), `--cage-guest` (new), and `--depol` (new) subsections are in place with all verification greps passing.
- Ready for the remaining 48-documentation plans (48-02, 48-04, 48-05, 48-07 through 48-14 per the RESEARCH split strategy).
- No blockers or concerns. The pre-existing untracked `48-01-SUMMARY.md`/`48-03-SUMMARY.md` and the modified `README.md` are from other plan executions and were intentionally left unstaged — only `docs/cli-reference.md` was committed for the 48-06 task work.

---
*Phase: 48-documentation*
*Completed: 2026-07-12*
