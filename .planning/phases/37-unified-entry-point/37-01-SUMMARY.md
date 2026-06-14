---
phase: 37-unified-entry-point
plan: 01
subsystem: cli
tags: [argparse, entry-point, routing, importlib, pyside6]

# Dependency graph
requires:
  - phase: 36-cli-feature-parity
    provides: CLI parser (create_parser, get_arguments) and CLIPipeline
  - phase: 34.6-custom-molecule-complete
    provides: GUI run_app() entry point
provides:
  - "quickice/entry.py: Unified entry point routing (main, _is_pyside6_available, _has_display, _has_pipeline_flags, _get_install_hint)"
  - "Lazy import pattern: quickice.main, quickice.gui.main_window, quickice.cli.parser imported only inside routing branches"
  - "Pre-parser pattern: argparse.ArgumentParser(add_help=False) with parse_known_args for --cli/--gui detection"
affects: [37-02, 37-03, __main__.py, quickice.py]

# Tech tracking
tech-stack:
  added: []
  patterns: [lazy-import-routing, pre-parser-flag-detection, importlib-find-spec-availability]

key-files:
  created: [quickice/entry.py]
  modified: []

key-decisions:
  - "argv parameter accepts full list (argv[0] included) not argv[1:]; None default uses sys.argv"
  - "effective_args = argv[1:] used for routing decisions and sys.argv reconstruction in CLI branches"
  - "remaining from parse_known_args includes argv[0] as positional; use effective_args instead for clean_argv"

patterns-established:
  - "Lazy import routing: All quickice.main, quickice.gui, quickice.cli.parser imports inside function branches"
  - "Pre-parser with parse_known_args: Detects --cli/--gui without consuming pipeline flags"
  - "importlib.util.find_spec for PySide6 detection: Avoids Qt crash in headless environments"

# Metrics
duration: 3min
completed: 2026-06-14
---

# Phase 37 Plan 01: Unified Entry Point Summary

**Unified entry point routing module with lazy imports, pre-parser flag detection, and PySide6 availability check via importlib.util.find_spec**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-14T18:56:21Z
- **Completed:** 2026-06-14T18:59:43Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created quickice/entry.py with complete routing logic for CLI/GUI/help modes
- All 5 functions implemented: main(), _is_pyside6_available(), _has_display(), _has_pipeline_flags(), _get_install_hint()
- No PySide6 import at module level (lazy imports only)
- Pre-parser correctly handles --cli/--gui detection alongside pipeline flags

## Task Commits

Each task was committed atomically:

1. **Task 1: Create quickice/entry.py with full routing logic** - `917b4f4` (feat)

## Files Created/Modified
- `quickice/entry.py` - Unified entry point with main() router and 4 helper functions (201 lines)

## Decisions Made
- **argv parameter design:** `main(argv=None)` accepts full argv list (including argv[0]), not just argv[1:]. This matches how argparse.parse_known_args works and allows proper sys.argv reconstruction for CLI mode.
- **effective_args over remaining:** When `parse_known_args(argv)` processes argv, `remaining` includes argv[0] as a positional argument. Using `effective_args = argv[1:]` for building clean_argv avoids double program name in sys.argv.
- **Router flags as frozenset:** `_ROUTER_FLAGS` is a module-level frozenset for O(1) membership testing and immutability.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed argv[0] duplication in CLI routing**
- **Found during:** Task 1 (initial implementation testing)
- **Issue:** `parse_known_args(argv)` returns `remaining` that includes argv[0] as a positional. When building `sys.argv = [sys.argv[0]] + clean_argv` from `remaining`, the program name appeared twice, causing "unrecognized arguments" error from the CLI parser.
- **Fix:** Used `effective_args = argv[1:]` (filtered for --cli/--gui) instead of `remaining` for building clean_argv. This correctly produces `sys.argv = [sys.argv[0]] + ['-T', '300', '-P', '0.1', '-N', '256']`.
- **Files modified:** quickice/entry.py (lines 180-195)
- **Verification:** `main(['quickice', '-T', '300', '-P', '0.1', '-N', '256'])` correctly routes to CLI parser without "unrecognized arguments" error
- **Committed in:** 917b4f4 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed docstring inconsistency for argv default**
- **Found during:** Task 1 (code review after implementation)
- **Issue:** Module docstring and main() docstring said "uses sys.argv[1:]" but code uses `sys.argv` (full list). The code is correct; docstrings were misleading.
- **Fix:** Updated both docstrings to say "uses sys.argv" instead of "uses sys.argv[1:]".
- **Files modified:** quickice/entry.py (lines 8, 110)
- **Verification:** Code and docstrings now consistent
- **Committed in:** 917b4f4 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep.

## Issues Encountered
- PySide6 not installed in current environment, so `_is_pyside6_available()` returns False. This is correct behavior — the function works as designed, just the environment doesn't have PySide6. Verified the error message path for `--gui` without PySide6.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- entry.py ready for integration by __main__.py and quickice.py stubs (Plan 37-02)
- Unit tests for entry.py routing logic can be added in Plan 37-03
- All lazy import paths verified: quickice.main.main, quickice.gui.main_window.run_app, quickice.cli.parser.create_parser

---
*Phase: 37-unified-entry-point*
*Completed: 2026-06-14*
