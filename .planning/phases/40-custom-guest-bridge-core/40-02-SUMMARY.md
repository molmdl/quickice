---
phase: 40-custom-guest-bridge-core
plan: 02
subsystem: itp-transformation
tags: [gromacs, itp, transform_guest_itp, atoms-resname, hydrate-guest, regex]

# Dependency graph
requires:
  - phase: 38-internal-pipeline-refactor
    provides: transform_guest_itp() scaffolded in 38-04 (Steps 1-2: atomtypes comment-out + moleculetype _H rename); [ atoms ] resname rewrite was explicitly deferred to Phase 40
  - phase: 40-custom-guest-bridge-core
    provides: 40-01 established the regex-bounded section-extraction pattern (parse_itp_defaults_comb_rule) reused here for [ atoms ]
provides:
  - transform_guest_itp Step 3 — rewrites the [ atoms ] resname column (4th field) to {guest_name}{suffix} (e.g. MOL -> MOL_H)
  - _rewrite_atoms_section_resname(content, new_name) helper in gromacs_writer.py
  - 7 unit tests in tests/test_transform_guest_itp_atoms.py covering all Step 3 behaviors
affects: [40-04-custom-guest-bridge-validation, 41-01-p3-fix, 41-03-gro-resname-enforcement, 47-01-validation-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "[ atoms ] section rewrite scoped via non-greedy regex r'\\[\\s*atoms\\s*\\](.*?)(?=\\[\\s*\\w+\\s*\\]|$)' with re.DOTALL | re.IGNORECASE (mirrors 40-01 [ defaults ] extraction)"
    - "Section-body rewrite: split body by newlines, preserve comments/blanks verbatim, rewrite data-line field[3], splice back via content[:body_start] + new_body + content[body_end:]"
    - "Leading whitespace preserved; internal spacing normalized to single spaces (GROMACS is whitespace-flexible in ITP)"
    - "Step 3 applies independently of [ moleculetype ] section presence — resname is rewritten whenever an [ atoms ] section is found"

key-files:
  created:
    - tests/test_transform_guest_itp_atoms.py
  modified:
    - quickice/output/gromacs_writer.py
    - tests/test_itp_transformation.py

key-decisions:
  - "Step 3 rewrites [ atoms ] resname to {guest_name}{suffix} regardless of [ moleculetype ] section presence (Step 3 applies independently; a malformed ITP without [ moleculetype ] still gets its [ atoms ] resname rewritten, consistent with the caller's explicit guest_name)"
  - "Comment lines (starting with ; or #) and blank lines preserved verbatim; only data lines with >=4 whitespace-separated fields have field[3] (resname) replaced"
  - "Graceful no-op when no [ atoms ] section is present (returns content unchanged) — some ITPs may lack it"
  - "Updated 2 existing tests in test_itp_transformation.py that encoded the old deferred no-rewrite behavior from Phase 38-04 (test_atoms_section_unchanged, test_no_moleculetype_section)"

patterns-established:
  - "Regex-bounded ITP section rewrite: match header + lazy body up to next [ section ]/EOF, operate only on the body, splice back — reusable for future per-section ITP transformations"

# Metrics
duration: 14min
completed: 2026-06-30
---

# Phase 40 Plan 02: [ atoms ] Resname Rewrite in transform_guest_itp Summary

**transform_guest_itp now rewrites the [ atoms ] resname column to {guest}_H (e.g. MOL→MOL_H) via a new regex-bounded Step 3, completing the deferred Phase 38-04 item so custom guest ITPs are internally consistent; 7 new + 19 updated unit tests pass with no export-path regressions**

## Performance

- **Duration:** 14 min
- **Started:** 2026-06-30T08:42:50Z
- **Completed:** 2026-06-30T08:56:47Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Extended `transform_guest_itp` with **Step 3**: rewrites the resname column (4th field, 0-indexed 3) in the `[ atoms ]` section to `{guest_name}{suffix}` (e.g. `MOL` → `MOL_H`, `CH4` → `CH4_H`), completing the deferred Phase 38-04 item so a custom guest ITP is internally consistent (`[ moleculetype ] etoh_custom_H` ... `[ atoms ] ... MOL_H ...`)
- Added `_rewrite_atoms_section_resname(content, new_name)` helper that scopes the rewrite to the `[ atoms ]` section only (regex-bounded to the next `[ section ]` header or EOF), preserving comment/blank lines verbatim and keeping each data line's leading whitespace (internal spacing normalized to single spaces — GROMACS is whitespace-flexible in ITP)
- Graceful no-op when no `[ atoms ]` section is present (some ITPs may lack it); Step 3 applies independently of `[ moleculetype ]` section presence
- Verified backward compatibility for built-in guests: `CH4` → `CH4_H` in both `[ moleculetype ]` and `[ atoms ]`; existing Steps 1-2 (atomtypes comment-out, moleculetype rename) unchanged
- 7 new unit tests + 19 existing `transform_guest_itp` tests pass; 76 `test_output` export tests + 12 CLI pipeline hydrate/custom/guest tests pass (no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend transform_guest_itp with [ atoms ] resname rewrite** - `6e532e4` (feat)
2. **Task 2: Unit tests for [ atoms ] resname rewrite** - `f5d8d5c` (test)

## Files Created/Modified
- `quickice/output/gromacs_writer.py` - Added `import re`; new `_rewrite_atoms_section_resname()` helper (regex-bounded `[ atoms ]` body rewrite); Step 3 call at the end of `transform_guest_itp`; updated `transform_guest_itp` docstring to describe the 3-step pipeline. Steps 1-2 and `comment_out_atomtypes_in_itp` unchanged.
- `tests/test_itp_transformation.py` - Added `import re`; renamed `test_atoms_section_unchanged` → `test_atoms_section_resname_rewritten` (now asserts `CH4_H` resname on all 5 `[ atoms ]` data lines via regex parse); updated `test_no_moleculetype_section` to assert `[ atoms ]` resname is rewritten to `CH4_H` even without a `[ moleculetype ]` section. These 2 tests previously encoded the old deferred no-rewrite behavior.
- `tests/test_transform_guest_itp_atoms.py` - New 7-test unit suite covering: custom guest resname rewrite, all 9 atom lines rewritten, comment preservation, no-`[ atoms ]` no-crash, CH4 backward compat, atomtypes still commented, and no leakage to other sections.

## Decisions Made
- Step 3 applies independently of `[ moleculetype ]` section presence — the resname rewrite happens whenever an `[ atoms ]` section is found, so a malformed ITP without `[ moleculetype ]` still gets its `[ atoms ]` resname rewritten (consistent with the caller's explicit `guest_name` request; the `new_name = f"{guest_name}{suffix}"` is computed unconditionally at function entry)
- Reused the regex-bounded section-extraction pattern established in 40-01 (`parse_itp_defaults_comb_rule`) for consistency: non-greedy body capture up to the next `[ section ]` header or EOF, with `re.DOTALL | re.IGNORECASE`
- Leading whitespace on each data line is preserved (faithful to the original ITP styling); internal multiple-spaces are normalized to single spaces, which is acceptable because GROMACS is whitespace-flexible in ITP files
- Kept the rewrite to a pure string-processing helper with no try/except (logic is sound; AGENTS.md forbids bare `except` in core pipeline code and none is needed here)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated 2 existing tests that encoded the old deferred no-rewrite behavior**
- **Found during:** Task 1 (extending `transform_guest_itp` with Step 3)
- **Issue:** `tests/test_itp_transformation.py` had 2 tests that asserted the Phase 38-04 deferred behavior where `[ atoms ]` resname was NOT rewritten: `test_atoms_section_unchanged` (asserted `"1      CH4    C"` remained unchanged) and `test_no_moleculetype_section` (asserted `"CH4_H" not in result`). Implementing Step 3 as the plan requires flips both of these, so the plan's verification #2 ("no regressions in existing transform_guest_itp tests") could not pass without updating them.
- **Fix:** Renamed `test_atoms_section_unchanged` → `test_atoms_section_resname_rewritten` (now parses the `[ atoms ]` section via regex and asserts all 5 data lines carry `CH4_H` resname); updated `test_no_moleculetype_section` to assert `[ atoms ]` resname IS rewritten to `CH4_H` even without a `[ moleculetype ]` section (Step 3 applies independently). Added `import re` to the test file.
- **Files modified:** tests/test_itp_transformation.py
- **Verification:** All 19 existing + 7 new transform_guest_itp tests pass; 76 export tests + 12 CLI pipeline tests pass (no regressions)
- **Committed in:** 6e532e4 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The test update was necessary to reconcile the plan's new required behavior with existing tests that encoded the explicitly-deferred Phase 38-04 behavior. No scope creep — the implementation matches the plan's must_haves exactly.

## Issues Encountered
- The first attempt to insert the Step 3 call via the edit tool matched an ambiguous `oldString` (`result_lines.append(line)` + `return '\n'.join(result_lines)`) that appeared in both `comment_out_atomtypes_in_itp` and `transform_guest_itp`; the replacement landed inside `comment_out_atomtypes_in_itp` (where `new_name` is out of scope) and corrupted its `else:` block indentation. Caught immediately by a syntax check (`IndentationError`), `comment_out_atomtypes_in_itp` was reverted to its original form, and Step 3 was re-applied to `transform_guest_itp` using a unique context anchor (the `# Comment line — still in section` branch + `def get_guest_residue_name` boundary). No runtime impact; resolved before any commit.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `transform_guest_itp` now produces internally consistent custom guest ITPs (`[ moleculetype ] X_H` + `[ atoms ] resname X_H`), ready for 40-04 (custom guest bridge validation/transform) and 41-01/41-03 (GROMACS export for custom guests)
- The ITP transformation pipeline scaffolded in 38-04 is now complete (all 3 steps implemented); downstream plans can rely on `transform_guest_itp` producing consistent moleculetype + atoms naming
- No blockers: pure string-processing addition with no threading or I/O concerns; the `_rewrite_atoms_section_resname` helper is a standalone primitive

---
*Phase: 40-custom-guest-bridge-core*
*Completed: 2026-06-30*
