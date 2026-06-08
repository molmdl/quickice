---
phase: e2e-compute-export
plan: 10
type: execute
wave: 7
depends_on: []
files_modified:
  - scripts/clean-test-output.sh
autonomous: true

must_haves:
  truths:
    - "Developer can run script with --dry-run and see exactly what would be deleted without deleting anything"
    - "Developer can run script without flags and reclaim tmp/ space (minus em.mdp and e2e-gmx-validation/)"
    - "em.mdp is preserved across all modes (used by grompp tests)"
    - "Stale GROMACS backup files (#*.# pattern) are reported separately for visibility"
  artifacts:
    - path: "scripts/clean-test-output.sh"
      provides: "Test output cleanup utility"
      contains: "--dry-run"
  key_links:
    - from: "scripts/clean-test-output.sh"
      to: "tmp/"
      via: "rm -rf of contents"
      pattern: "rm.*tmp"
---

<objective>
Create a cleanup script that removes accumulated test output from the tmp/ directory.

Purpose: The e2e-compute-export phase generated 97MB of test output across ~20 directories in tmp/. Developers need a simple way to reclaim this space without manually identifying what's safe to delete. The grompp validation workspace (tmp/e2e-gmx-validation/) is designed to persist for post-test debugging and should only be cleaned explicitly.

Output: scripts/clean-test-output.sh — a standalone bash utility following existing script conventions.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@scripts/build-linux.sh
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create scripts/clean-test-output.sh cleanup utility</name>
  <files>scripts/clean-test-output.sh</files>
  <action>
Create `scripts/clean-test-output.sh` following the existing script conventions (see @scripts/build-linux.sh: shebang, set -e, usage comments, error checking).

Script behavior:
1. Parse CLI flags:
   - `--dry-run`: Show what would be deleted without deleting anything
   - `--include-gmx-validation`: Also clean tmp/e2e-gmx-validation/ (default: preserved for post-test debugging)
   - `--stale-backups-only`: Only remove GROMACS stale backup files matching `#*#` pattern (e.g., `#em.tpr.1#` through `#em.tpr.98#`); useful for quick cleanup before the 99-backup GROMACS limit
   - `-h` / `--help`: Print usage and exit

2. Default cleanup (no flags) removes ALL tmp/ contents EXCEPT:
   - `tmp/em.mdp` — used by grompp tests (MDP parameter file)
   - `tmp/e2e-gmx-validation/` — persistent grompp workspace for post-test debugging

3. With `--include-gmx-validation`, also remove tmp/e2e-gmx-validation/ contents.

4. With `--stale-backups-only`, ONLY remove files matching `#*#` pattern recursively under tmp/. Do NOT remove other files or directories. This is a lightweight mode for the GROMACS 99-backup limit issue.

5. Script must:
   - Run from repo root (check that tmp/ directory exists, exit 1 if not)
   - Print each item being deleted (or would-be-deleted in dry-run)
   - Print summary: count of directories removed, count of files removed, bytes reclaimed (use `du -sh tmp/` before/after for non-dry-run)
   - In --dry-run mode, print "[DRY RUN]" prefix on each line
   - Stale backup files (`#*#`) are counted separately in the summary for visibility

6. Implementation structure:
```bash
#!/bin/bash
# Clean accumulated test output from tmp/ directory
# Usage: ./scripts/clean-test-output.sh [OPTIONS]
#
# Options:
#   --dry-run              Show what would be deleted without deleting
#   --include-gmx-validation  Also clean tmp/e2e-gmx-validation/ (default: preserved)
#   --stale-backups-only  Only remove GROMACS #*# backup files
#   -h, --help             Show this help message
#
# Preserved by default:
#   tmp/em.mdp             Used by grompp tests
#   tmp/e2e-gmx-validation/  Persistent grompp workspace for debugging
```

7. After creating the script, make it executable: `chmod +x scripts/clean-test-output.sh`
  </action>
  <verify>
Run `bash -n scripts/clean-test-output.sh` (syntax check passes) and `scripts/clean-test-output.sh --help` (prints usage). Run `scripts/clean-test-output.sh --dry-run` (shows what would be deleted, does NOT delete anything, exits 0).
  </verify>
  <done>
Script exists at scripts/clean-test-output.sh, is executable, passes bash syntax check, --help prints usage, --dry-run lists items without deleting, em.mdp is always preserved, e2e-gmx-validation/ is preserved by default.
  </done>
</task>

</tasks>

<verification>
1. `bash -n scripts/clean-test-output.sh` — syntax OK
2. `scripts/clean-test-output.sh --help` — prints usage and exits 0
3. `scripts/clean-test-output.sh --dry-run` — lists deletable items, exits 0, nothing actually deleted
4. `scripts/clean-test-output.sh --dry-run --include-gmx-validation` — also lists e2e-gmx-validation/ contents
5. `scripts/clean-test-output.sh --stale-backups-only --dry-run` — only lists #*# files
6. Verify tmp/em.mdp still exists after any non-dry-run test
</verification>

<success_criteria>
scripts/clean-test-output.sh is executable, supports --dry-run / --include-gmx-validation / --stale-backups-only flags, always preserves em.mdp, preserves e2e-gmx-validation/ by default, and follows existing script conventions (shebang, set -e, usage comments).
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-compute-export/e2e-compute-export-10-SUMMARY.md`
</output>
