---
phase: 48-documentation
plan: 08
subsystem: docs
tags: [gro-itp-guide, hydrate-custom-guest, comb-rule, residue-name, moleculetype-registry, itp-validation]

# Dependency graph
requires:
  - phase: 38-04
    provides: transform_guest_itp unified ITP transformation (atomtypes comment-out + _H suffix + GRO name validation)
  - phase: 44.1-08
    provides: _stage_hydrate_guest_itps shared helper reusing transform_guest_itp for custom guest export
provides:
  - "Custom Guest ITP Requirements section in docs/gro-itp-guide.md documenting the 5 validation rules for hydrate cage guests"
  - "Footer version bump v4.5 -> v4.7 in docs/gro-itp-guide.md"
affects: [48-documentation, final-verification-sweep, v4.7-release-docs]

# Tech tracking
tech-stack:
  added: []
  patterns: ["DOCS-04 validation rules sourced from actual codebase (custom_guest_bridge.py + gromacs_writer.py + itp_parser.py) — no fabricated error strings"]

key-files:
  created: []
  modified: ["docs/gro-itp-guide.md"]

key-decisions:
  - "Used EXACT error strings from custom_guest_bridge.py:278-280 (comb-rule) and :257-260 (residue name) rather than the plan's paraphrased versions — AGENTS.md forbids fabricating references/data"
  - "Corrected plan's inaccurate file locations: validate_gro_residue_name is in quickice/output/gromacs_writer.py:26 (NOT types.py); transform_guest_itp is in quickice/output/gromacs_writer.py:677 (NOT cli/itp_helpers.py:170 which is a caller)"
  - "Documented comb-rule=2 as 'mandatory if [ defaults ] present' (absent OK — main .top supplies comb-rule=2), matching parse_itp_defaults_comb_rule semantics"

patterns-established:
  - "DOCS-04 pattern: source validation error strings verbatim from the codebase, never paraphrase or fabricate"

# Metrics
duration: 6min
completed: 2026-07-12
---

# Phase 48 Plan 08: GRO/ITP Guide Custom Guest Requirements Summary

**Custom Guest ITP Requirements section added to docs/gro-itp-guide.md with exact comb-rule=2, ≤3-char residue, _H suffix, [atomtypes] merge, and Tab-3 distinction rules sourced from the codebase; footer bumped v4.5 → v4.7**

## Performance

- **Duration:** ~6 min (actual execution; wall-clock longer due to rate-limit waits in prior attempts)
- **Started:** 2026-07-12T07:58:42Z
- **Completed:** 2026-07-12T12:04:07Z
- **Tasks:** 2
- **Files modified:** 1 (docs/gro-itp-guide.md)

## Accomplishments
- Added "Custom Guest ITP Requirements (for Hydrate Cage Guests)" section (49 lines) after the Validation section, covering all 5 rules with exact error strings sourced from the actual codebase
- Documented comb-rule=2 as mandatory (rejected if `[ defaults ]` has comb-rule=1; absent `[ defaults ]` accepted because main `.top` supplies comb-rule=2)
- Documented residue base name ≤3 chars with GRO 5-char limit explanation and the `_H` suffix convention (hydrate `_H`, liquid `_L`)
- Documented `[ atomtypes ]` comment-out + merge into main `.top` via `_merge_custom_atomtypes`
- Distinguished hydrate custom guest (Tab 1, GUI-only for v4.7) from Tab-3 liquid custom molecule with a comparison table
- Updated footer version strings from v4.5 to v4.7 with today's date (2026-07-12)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Custom Guest ITP Requirements section** - `b7f6ad9` (docs)
2. **Task 2: Update footer version strings v4.5 → v4.7** - `b4b85a9` (docs)

## Files Created/Modified
- `docs/gro-itp-guide.md` - Added Custom Guest ITP Requirements section (49 lines) after Validation; updated footer v4.5 → v4.7

## Decisions Made
- **Used exact error strings from the codebase, not the plan's paraphrased versions.** The plan's `<action>` suggested error messages ("comb-rule must be 2 (Lorentz-Berthelot), got comb-rule=1" and "residue name exceeds 3 chars") did not match the actual strings in `custom_guest_bridge.py`. Per AGENTS.md ("Never make up references or data. Always verify sources"), I read `custom_guest_bridge.py:257-280` and `gromacs_writer.py:26-49` and used the verbatim error strings.
- **Corrected the plan's file-location references.** The plan claimed `validate_gro_residue_name` is in `types.py` and `transform_guest_itp` may be in `cli/itp_helpers.py:170`. Grep verification showed `validate_gro_residue_name` is in `quickice/output/gromacs_writer.py:26` and `transform_guest_itp` is in `quickice/output/gromacs_writer.py:677` (the `cli/itp_helpers.py:170` reference is a caller, not the definition). The docs cite the correct module paths.
- **Documented comb-rule semantics precisely.** `parse_itp_defaults_comb_rule()` returns `None` when `[ defaults ]` is absent (valid — main `.top` supplies comb-rule=2) and rejects only when non-None and `!= 2`. The docs state "mandatory (if `[ defaults ]` present)" to capture this nuance exactly.

## Deviations from Plan

None — plan executed as written, with error strings and file locations corrected to match the actual codebase (per AGENTS.md "Never make up references or data").

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DOCS-04 requirement satisfied: GRO/ITP guide now documents custom guest ITP requirements for hydrate cage guests
- Remaining Phase 48 plans (48-01..07, 48-09..14) cover other doc files (README, gui-guide, cli-reference, help_dialog restructure, tooltip audit, version bump)
- The exact error strings documented here can be cross-referenced by other Phase 48 plans that mention custom guest validation (e.g., help_dialog custom guest page)

---
*Phase: 48-documentation*
*Completed: 2026-07-12*
