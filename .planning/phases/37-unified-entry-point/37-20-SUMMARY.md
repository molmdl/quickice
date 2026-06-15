---
phase: 37
plan: 20
subsystem: cli-workflow-scripts
tags: [bash, workflow, hydrate, interface, custom-molecule, ion, gromacs, cli, documentation]
---

# Phase 37 Plan 20: Hydrate-Interface-Custom-Ion Workflow Script Summary

**One-liner:** Runnable bash workflow script chaining hydrate→interface→custom molecule→ion pipeline with CLI option parsing and doc cross-references

## Dependency Graph

- **requires:** Phase 36 (CLI pipeline), Phase 37 Plans 01-18 (unified entry point)
- **provides:** Executable workflow script for full pipeline, doc references in gro-itp-guide and README
- **affects:** Phase 35+ (documentation), future workflow scripts

## Tech Stack

- **added:** None (bash script using existing python -m quickice)
- **patterns:** Bash while/shift flag parsing with value-taking options, single-command pipeline chaining

## Key Files

### Created

- `scripts/hydrate-interface-custom-ion.sh` — Runnable workflow script with 10 CLI options, validation, and summary output

### Modified

- `docs/gro-itp-guide.md` — Added "Workflow Example" section before References
- `README.md` — Added "Example Scripts" bullet in Documentation section

## Tasks Completed

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | Create workflow script | f0e3e40 | scripts/hydrate-interface-custom-ion.sh (192 lines) |
| 2 | Add doc references | 72ae538 | Workflow Example section + Example Scripts bullet |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| while/shift instead of for/$@ for flag parsing | Plan specified `for arg in "$@"` pattern (from clean-test-output.sh), but that script only has boolean flags. Value-taking flags with `shift` inside `for` loop break because shift modifies `$@` but `for` iterates the original list. Changed to `while [ $# -gt 0 ]; do case "$1" in ... shift; done` pattern — the correct bash idiom for flags with values. |
| Missing-value guards for all flag-taking options | Added `if [ -z "$1" ]` check after each `shift` to catch `--flag` without a value (e.g., `--custom-gro` at end of command line). Prevents silent empty-string assignment and confusing downstream errors. |
| Script prints full command before running | Users can copy the printed `python -m quickice` command for learning, debugging, or manual customization. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed flag parsing pattern for value-taking options**

- **Found during:** Task 1 verification
- **Issue:** Plan specified `for arg in "$@"; do case` with `shift` for value-taking flags. The `shift` inside a `for` loop iterates the original `$@`, causing value arguments to be treated as unknown options (e.g., `--custom-gro /path/file.gro` fails with "Unknown option: /path/file.gro").
- **Fix:** Changed to `while [ $# -gt 0 ]; do case "$1" in` pattern with `shift` at end of each case block. This is the standard bash idiom for parsing flags that take values.
- **Files modified:** scripts/hydrate-interface-custom-ion.sh
- **Commit:** f0e3e40

**2. [Rule 2 - Missing Critical] Added missing-value guards for flag options**

- **Found during:** Task 1 (while fixing the parsing bug)
- **Issue:** No validation that a value follows a flag-taking option. Running `--custom-gro` at end of command line would silently set CUSTOM_GRO="" and fail later with "required" error instead of pointing to the actual problem.
- **Fix:** Added `if [ -z "$1" ]; then echo "ERROR: --flag requires an argument"; exit 1; fi` after each shift for all 9 flag-taking options.
- **Files modified:** scripts/hydrate-interface-custom-ion.sh
- **Commit:** f0e3e40

## Verification Results

1. ✅ `bash -n scripts/hydrate-interface-custom-ion.sh` — Syntax OK
2. ✅ `--help` flag works, shows usage and exits 0
3. ✅ No-args invocation exits 1 with "ERROR: --custom-gro is required"
4. ✅ `--custom-gro /nonexistent` exits 1 with "Custom GRO file not found"
5. ✅ `grep -c "hydrate-interface-custom-ion" docs/gro-itp-guide.md` → 3
6. ✅ `grep -c "Example Scripts" README.md` → 1
7. ✅ Full pipeline test with valid files completes successfully (exit 0)
8. ✅ Script prints the `python -m quickice` command before running
9. ✅ Script prints summary with output directory listing after completion

## Next Phase Readiness

- No blockers introduced
- Workflow script is fully functional and tested
- Documentation cross-references are in place
- All 20 plans in Phase 37 now complete
