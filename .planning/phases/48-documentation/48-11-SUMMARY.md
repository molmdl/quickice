---
phase: 48-documentation
plan: 11
subsystem: testing
tags: [pyside6, qt, headless, pytest, help-dialog, smoke-test, qstackedwidget]

# Dependency graph
requires:
  - phase: 48-documentation (plan 48-10)
    provides: help_dialog.py v4.7 content pages (11 TOC entries / 11 pages, all 10 lattice keys, GUI-only custom guest, deprecated flags note)
provides:
  - Headless smoke test (tests/test_help_dialog.py) verifying the restructured QuickReferenceDialog
  - 11 passing tests asserting TOC/pages count, content correctness, and TOC navigation
affects: [future GUI test refactors, help_dialog content changes requiring regression coverage]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Singleton QApplication fixture inside function-scoped pytest fixture (conftest.py has no qapp fixture)"
    - "findChildren(QLabel) recursive text collection for grep-style content assertions across QStackedWidget pages"

key-files:
  created:
    - tests/test_help_dialog.py
  modified: []

key-decisions:
  - "Used singleton QApplication pattern inside the dialog fixture (matching test_hydrate_panel.py) since tests/conftest.py provides no qapp fixture and is API-only"
  - "Kept os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen') as a safety net before importing help_dialog (per plan), while the test runner also sets it via env var"

patterns-established:
  - "Headless smoke test pattern for QStackedWidget+QListWidget dialogs: assert toc.count()==pages.count(), findChildren(QLabel) for content grep, setCurrentRow(N)->pages.currentIndex()==N for navigation"

# Metrics
duration: 1min
completed: 2026-07-14
---

# Phase 48 Plan 11: Help Dialog Headless Smoke Test Summary

**11 headless PySide6 smoke tests verifying the restructured QuickReferenceDialog TOC/pages structure, v4.7 content correctness, and TOC navigation**

## Performance

- **Duration:** 1 min
- **Started:** 2026-07-14T06:08:40Z
- **Completed:** 2026-07-14T06:09:40Z
- **Tasks:** 1
- **Files modified:** 1 (created)

## Accomplishments
- Created tests/test_help_dialog.py with 11 passing tests under QT_QPA_PLATFORM=offscreen
- Verified the 48-09/48-10 help dialog restructure: toc.count()==11, pages.count()==11, TOC/pages in sync
- Verified v4.7 content correctness: no stale v4.5 string, all 10 lattice keys present, custom guest marked GUI-only, deprecated --guest/--cage-occupancy-* flags mentioned
- Verified TOC navigation: setCurrentRow(3) switches pages to Extended Lattice Types, first row selected on construction
- Established headless smoke-test pattern for QStackedWidget+QListWidget dialogs using findChildren(QLabel) recursive text collection

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tests/test_help_dialog.py headless smoke test** - `03d7976` (test)

**Plan metadata:** (pending — created after this SUMMARY is committed)

## Files Created/Modified
- `tests/test_help_dialog.py` - 11 headless smoke tests for QuickReferenceDialog (Structure: 5 tests, Content: 4 tests, Navigation: 2 tests) asserting TOC/pages count==11, no v4.5, all 10 lattice keys, GUI-only marking, deprecated flags mention, and TOC navigation

## Decisions Made
- Used the singleton QApplication pattern (`if not QApplication.instance(): QApplication(sys.argv)`) inside the `dialog` fixture, matching the established convention in tests/test_hydrate_panel.py, because tests/conftest.py provides no QApplication fixture (it is API-only per its docstring). The plan explicitly anticipated this: "Check if tests/conftest.py already provides one... If not, add a @pytest.fixture for QApplication in this test file or use the existing conftest pattern."
- Kept `os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")` before importing help_dialog as a safety net (per the plan's test template), while the test runner also sets the env var explicitly.
- Used `page.findChildren(QLabel)` (recursive) to collect all QLabel text from each QStackedWidget page for content assertions — this correctly handles both the _make_page pages (QScrollArea > QWidget > QLabel) and the combined "More Information & Notes" page (QScrollArea > QWidget > [refs_label, notes_label]).

## Deviations from Plan

None - plan executed exactly as written. The QApplication singleton setup was explicitly anticipated by the plan ("IMPORTANT: You may need a QApplication fixture... If not, add a @pytest.fixture for QApplication in this test file or use the existing conftest pattern"), so adding it is following the plan's instruction rather than a deviation.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Help dialog (DOCS-02 in-app) now has automated regression coverage: any future content change that drops a lattice key, reintroduces a v4.5 string, removes the GUI-only marking, or drops the deprecated-flags note will fail the smoke test.
- The test pattern (findChildren(QLabel) + setCurrentRow navigation) is reusable for other QStackedWidget+QListWidget dialogs.
- Phase 48 (Documentation) remaining: 48-05 and 48-14 by parallel agents; 48-11 complete.

---
*Phase: 48-documentation*
*Completed: 2026-07-14*
