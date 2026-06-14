---
phase: 37-unified-entry-point
plan: 15
subsystem: documentation
tags: [readme, unified-entry-point, documentation]
requires: [37-01, 37-03, 37-04, 37-05, 37-06]
provides: [updated-README-unified-entry-point]
affects: []
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified: [README.md]
---

# Phase 37 Plan 15: README Update Summary

## One-Liner

Updated README.md with unified entry point invocation, project structure additions, and routing explanation

## Changes Made

### Task 1: Update README.md invocation references and project structure

**Change 1 — Quick Start sections (lines 66, 78):**
- Line 66 (Verify installation): `python -m quickice.gui` → `python -m quickice --help`
- Line 78 (Launch the GUI): `python -m quickice.gui` → `python -m quickice --gui` (primary) + `python -m quickice.gui` (direct access note)

**Change 2 — Project Structure (line 378):**
- `quickice.py  # CLI entry point` → `quickice.py  # Backward-compat entry wrapper` + `__main__.py  # Unified entry point` + `entry.py  # Entry router`

**Change 3 — Entry Point section (after Quick Start):**
- Added brief section explaining 5 routing behaviors (no args, computation flags, --cli, --gui, quickice.py)

**Bonus fix (Rule 1 - Bug):**
- Known Issues: "CLI support for v4.5 features (Tabs 3-5) pending future release" → "CLI support for v4.5 features (Tabs 3-5) is available via `python -m quickice`" — Phase 36 already implemented this

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| `python -m quickice --help` for verify | Shows router works + provides useful info (not just GUI window) |
| `python -m quickice.gui` mentioned as "direct access (bypasses router)" | Preserves discoverability while promoting unified entry point |
| Known Issues CLI line updated | Phase 36 CLI implementation made this statement factually incorrect |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed outdated Known Issues line**

- **Found during:** Task 1
- **Issue:** README stated "CLI support for v4.5 features (Tabs 3-5) pending future release" but Phase 36 already implemented full CLI pipeline support
- **Fix:** Updated to "CLI support for v4.5 features (Tabs 3-5) is available via `python -m quickice`"
- **Files modified:** README.md
- **Commit:** 54addc0

## Verification Results

| Check | Result |
|-------|--------|
| `grep -c "python -m quickice" README.md` | 6 (≥3 ✓) |
| `grep "__main__.py" README.md` | Present in project structure ✓ |
| `grep "entry.py" README.md` | Present in project structure ✓ |

## Next Phase Readiness

No blockers. README reflects unified entry point architecture.

---

*Duration: ~1 minute*
*Completed: 2026-06-15*
