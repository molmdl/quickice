---
phase: 40-custom-guest-bridge-core
plan: 01
subsystem: parsing-validation
tags: [itp-parser, comb-rule, gromacs, lorentz-berthelot, guest-validation]

# Dependency graph
requires:
  - phase: 38-internal-pipeline-refactor
    provides: itp_parser.py (parse_itp_file, ITPMoleculeInfo) extended here
provides:
  - parse_itp_defaults_comb_rule(content) -> int | None in itp_parser.py
  - etoh_combrule1.itp test fixture ([ defaults ] comb-rule=1 reject path)
  - 10 unit tests covering valid/invalid/absent/malformed comb-rule parsing
affects: [40-04-custom-guest-bridge-validation, 40-05-hydrate-generator-integration, 47-01-validation-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "[ defaults ] section extraction via non-greedy regex up to next [ section ] header"
    - Absent [ defaults ] returns None (accept path: main .top supplies comb-rule=2)
    - except (ValueError, IndexError) instead of bare except (AGENTS.md compliance)

key-files:
  created:
    - quickice/data/custom/test_invalid/etoh_combrule1.itp
    - tests/test_itp_parser_combrule.py
  modified:
    - quickice/structure_generation/itp_parser.py
    - quickice/data/custom/test_invalid/README.md

key-decisions:
  - "parse_itp_defaults_comb_rule returns None when [ defaults ] is absent (valid: etoh.itp has none; main .top supplies comb-rule=2)"
  - "Reject comb-rule != 2 ONLY when parser returns non-None; accept when None"
  - "Malformed/non-integer comb-rule returns None (not raise) — callers decide rejection"
  - "re module already imported in itp_parser.py; no new dependency added"

patterns-established:
  - "[ defaults ] comb-rule extraction: 2nd field of first non-comment data line"
  - "Test fixture pattern: prepend [ defaults ] block to valid ITP copy for reject-path testing"

# Metrics
duration: 2min
completed: 2026-06-30
---

# Phase 40 Plan 01: ITP Comb-Rule Parser + Test Fixtures Summary

**parse_itp_defaults_comb_rule() extracts comb-rule from GROMACS [ defaults ] section, returning int or None; with a comb-rule=1 reject-path fixture and 10 passing unit tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-30T08:35:37Z
- **Completed:** 2026-06-30T08:38:14Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Added `parse_itp_defaults_comb_rule(content) -> int | None` to `itp_parser.py` — extracts the comb-rule (2nd field) from a GROMACS `[ defaults ]` section, returning the integer when present and parseable, `None` when the section is absent or the value is malformed
- Created `etoh_combrule1.itp` test fixture — a copy of the valid `etoh.itp` with a `[ defaults ]` block (comb-rule=1) prepended, exercising the GUEST-07 reject path
- Wrote 10 unit tests covering valid comb-rule=2/1, absent `[ defaults ]`, real fixtures (etoh.itp/etoh.top/etoh_combrule1.itp), `;` and `#` comments, malformed values, section boundaries, and empty sections — all passing
- Verified no regressions: 122 existing `itp`-keyword tests still pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add parse_itp_defaults_comb_rule to itp_parser.py** - `5b238da` (feat)
2. **Task 2: Create etoh_combrule1.itp test fixture + update README** - `7306975` (test)
3. **Task 3: Unit tests for comb-rule parser** - `9a62952` (test)

## Files Created/Modified
- `quickice/structure_generation/itp_parser.py` - Added `parse_itp_defaults_comb_rule` function (47 lines) after `parse_itp_file`; reuses existing `re` import
- `quickice/data/custom/test_invalid/etoh_combrule1.itp` - New test fixture: etoh.itp content with `[ defaults ]` comb-rule=1 prepended (reject path for GUEST-07)
- `quickice/data/custom/test_invalid/README.md` - Added fixture table row documenting etoh_combrule1.itp purpose
- `tests/test_itp_parser_combrule.py` - New 10-test unit suite covering all comb-rule parser behaviors

## Decisions Made
- Followed the plan's regex pattern `r'\[\s*defaults\s*\](.*?)(?=\[\s*\w+\s*\]|$)'` with `re.DOTALL | re.IGNORECASE` for section body extraction (stops at next `[ section ]` header or end of content)
- Used `except (ValueError, IndexError)` per AGENTS.md (no bare `except`) — IndexError covers the `fields[1]` access even though `len(fields) >= 2` guards it
- Malformed comb-rule returns `None` rather than raising, so callers (40-04 custom guest validation) decide whether to reject; this keeps the parser a pure extraction primitive
- Verified `re` was already imported at module top (line 8) — no import added

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `parse_itp_defaults_comb_rule` is importable and ready for use by downstream plan 40-04 (custom guest bridge validation), which will call it and reject when the returned value is non-None and != 2
- `etoh_combrule1.itp` fixture is ready for the GUEST-07 reject-path validation test in 40-04 / 47-01
- No blockers: the function is a standalone pure-extraction primitive with no threading or I/O concerns
- The 40-RESEARCH.md validation checklist (step 5) can now reference this function directly: `comb = parse_itp_defaults_comb_rule(itp_content); if comb is not None and comb != 2: raise ValueError(...)`

---
*Phase: 40-custom-guest-bridge-core*
*Completed: 2026-06-30*
