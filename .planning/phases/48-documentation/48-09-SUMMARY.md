---
phase: 48-documentation
plan: 09
subsystem: ui
tags: [pyside6, qstackedwidget, qlistwidget, help-dialog, toc, gui]

# Dependency graph
requires:
  - phase: 48-documentation (RESEARCH)
    provides: "Pattern 1 (QStackedWidget+QListWidget TOC) verified against PySide6 6.10.2; 8 existing sections enumerated; OK-button-in-outer-layout pitfall documented"
provides:
  - "Restructured help_dialog.py skeleton: QStackedWidget+QListWidget TOC layout with 8 verbatim-migrated pages, widened dialog (600-800px), OK button in outer layout, per-page independent QScrollArea scrolling"
  - "_on_section_changed handler + _add_section helper + _make_page helper on QuickReferenceDialog"
affects: [48-10 (adds 4 v4.7 content pages onto this skeleton), 48-11..14 (remaining doc plans may reference help_dialog structure)]

# Tech tracking
tech-stack:
  added: []
  patterns: ["QStackedWidget + QListWidget TOC for multi-section modal help dialog (Pattern 1 from 48-RESEARCH §4, verified PySide6 6.10.2)", "Per-page QScrollArea for independent scrolling (OK button stays fixed in outer layout)"]

key-files:
  created: []
  modified: ["quickice/gui/help_dialog.py"]

key-decisions:
  - "Skeleton swap only — all 8 existing sections migrated byte-identical (no content changes); v4.7 content deferred to plan 48-10"
  - "Per-page QScrollArea (each page scrolls independently) replaces the single outer QScrollArea; OK button kept in outer QVBoxLayout outside the QStackedWidget"
  - "Task 2 (handler+helper) satisfied by verification — _on_section_changed + _add_section were written inline in Task 1 (the restructure cannot function without them); no separate commit needed"

patterns-established:
  - "Pattern: QStackedWidget+QListWidget TOC for help dialog — currentRowChanged -> setCurrentIndex; TOC row N == page index N; OK button in outer layout"
  - "Pattern: verbatim content migration verified programmatically (extract QLabel.text() per page, compare against original strings)"

# Metrics
duration: 5min
completed: 2026-07-12
---

# Phase 48 Plan 09: Help Dialog Skeleton Restructure Summary

**QStackedWidget+QListWidget TOC restructure of help_dialog.py with all 8 existing sections migrated byte-identical and the OK button kept in the outer layout**

## Performance

- **Duration:** ~5 min active compute (140 min wall-clock includes inter-turn continuation gap)
- **Started:** 2026-07-12T12:07:57Z
- **Completed:** 2026-07-12T14:28:17Z
- **Tasks:** 2 (Task 1 = restructure+commit; Task 2 = verify handler/helper, no code change)
- **Files modified:** 1 (`quickice/gui/help_dialog.py`)

## Accomplishments
- Replaced the single `QScrollArea`+`QVBoxLayout` skeleton with a `QStackedWidget` + `QListWidget` TOC layout (left 160px nav column, right stacked pages) following Pattern 1 from 48-RESEARCH §4
- Migrated all 8 existing sections (Introduction, Keyboard Shortcuts, Workflow, Dimension Relationships, Best Practices, Custom Molecule Preparation, More Information, Important Notes) to individual stacked pages with **byte-identical** content (verified programmatically — extracted `QLabel.text()` per page and compared against the original strings)
- Widened the dialog from `setMinimumWidth(450)`/`setMaximumWidth(600)` to `setMinimumWidth(600)`/`setMaximumWidth(800)`; kept `setMinimumHeight(400)`/`setMaximumHeight(700)`
- Kept the `QDialogButtonBox(Ok)` in the OUTER `QVBoxLayout` (added after the `QHBoxLayout` body), so the OK button is always visible regardless of the selected page (confirmed structurally: outer layout has 2 items — body layout at index 0, button widget at index 1)
- Each page wraps its content in its own `QScrollArea` (via the new `_make_page` helper) so long pages scroll independently without affecting the TOC or OK button
- Connected `toc.currentRowChanged` → `_on_section_changed` → `pages.setCurrentIndex(row)`; call `toc.setCurrentRow(0)` at the end of `_setup_ui` so the first section is visible when the dialog opens
- Preserved all per-label behaviors: `setWordWrap(True)`, `setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)` on all 8 pages, and `setOpenExternalLinks(True)` on the More Information page
- Kept the `QuickReferenceDialog` class name and `__init__(parent=None)` signature; `main_window.py:1913` constructs/execs the dialog unchanged
- Removed the now-unused `_create_section_label` helper (section headers are now TOC rows, not inline bold labels)

## Task Commits

Each task was committed atomically:

1. **Task 1: Restructure help_dialog.py to QStackedWidget+QListWidget TOC with 8 migrated pages** — `808d107` (docs)
2. **Task 2: Add _on_section_changed handler and _add_section helper** — no commit (satisfied by verification; handler + helper were written inline in Task 1 — see Decisions Made)

**Plan metadata:** (pending — created after this SUMMARY is committed)

## Files Created/Modified
- `quickice/gui/help_dialog.py` — Restructured from single QScrollArea+QVBoxLayout to QStackedWidget+QListWidget TOC layout with 8 verbatim-migrated pages; widened to 600-800px; OK button in outer layout; per-page independent QScrollArea scrolling; added `_on_section_changed`, `_add_section`, `_make_page` helpers; removed `_create_section_label`

## Decisions Made
- **Skeleton swap only — no content changes.** All 8 sections migrated byte-identical (verified programmatically). v4.7 content (Extended Lattice Types, Custom Guest in Hydrate, Mixed Cage Occupancy, Depol Mode) and the "sI, sII, sH" line fix are deferred to plan 48-10 (Wave 2, depends on this plan) per the plan's explicit scope. The Workflow page still says "Select lattice type (sI, sII, sH)" verbatim — intentionally NOT fixed here.
- **Per-page QScrollArea (not a single outer scroll).** Each page wraps its QLabel in its own `QScrollArea` via `_make_page` so long content scrolls independently without moving the TOC or OK button. The outer-level `QScrollArea` was removed (per plan: "Remove QScrollArea (no longer needed at the outer level); each page may wrap its content in a QScrollArea for independent scrolling").
- **Task 2 satisfied by verification — no separate commit.** The plan anticipated this: "This may already be done as part of Task 1 if you wrote it inline — in that case, verify the handler and helper exist and are correctly wired." The `_on_section_changed` handler and `_add_section` helper are integral to the restructure (without them the TOC wouldn't switch pages and sections wouldn't be added), so they were written inline in Task 1's commit (`808d107`). Forcing a separate empty commit for Task 2 would violate AGENTS.md's atomic-commit rule ("Each commit should represent one logical change"). Task 2's done criteria (`_on_section_changed` switches pages, `_add_section` adds sections, `setCurrentRow(0)` opens first section, `toc.count()==8`, `pages.count()==8`) were all verified.
- **OK button placement confirmed structurally.** The outer `QVBoxLayout` has exactly 2 items: the body `QHBoxLayout` (TOC + pages) at index 0, and the `QDialogButtonBox` widget at index 1. The button is therefore outside the `QStackedWidget` and always visible.
- **Text-interaction flags + openExternalLinks preserved.** All 8 pages set `Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard` (the original only set this on the shortcuts label; the plan's per-page spec called for it on all pages — applied uniformly). The More Information page retains `setOpenExternalLinks(True)` from the original.

## Deviations from Plan

None — plan executed exactly as written. The only adjustment was Task 2 producing no separate commit (anticipated by the plan itself; see Decisions Made).

## Issues Encountered
- **QApplication required for headless construction.** The plan's verification command `QT_QPA_PLATFORM=offscreen python -c "from quickice.gui.help_dialog import QuickReferenceDialog; d = QuickReferenceDialog(); ..."` initially failed with "QWidget: Must construct the QApplication before a QWidget" and hung. Resolved by prepending `from PySide6.QtWidgets import QApplication; app = QApplication([])` before constructing the dialog. This is a standard PySide6 headless requirement (any QWidget construction needs a QApplication first), not a defect in help_dialog.py. The final verification (`toc: 8 pages: 8`) passes with the QApplication present.
- **Pre-existing version-string test failures (unrelated).** `tests/test_cli_integration.py::TestHelpAndVersion::test_version_shows_version` and `tests/test_entry_point.py::TestHelpAndVersion::test_version_shows_version` fail because they assert `"4.5.0"` in stdout but the version is now `"4.7.0"` (bumped in an earlier phase-48 plan). Confirmed pre-existing by reproducing with no uncommitted changes. Not caused by this plan (which only touches `help_dialog.py`, a GUI module with no CLI/version involvement).
- **Heavy GUI panel tests timed out in headless environment.** `tests/test_hydrate_panel.py` + `tests/test_custom_molecule_panel_34_6.py` import PySide6/VTK and run GenIce2, which exceeded the 240s timeout in this headless environment (a known issue per AGENTS.md: "VTK rendering may still crash in some headless environments"). My change only touches `help_dialog.py` (a standalone dialog module with no VTK/GenIce2 dependencies), so these tests are out of scope for regression here. The targeted help-keyword sweep (17 passed) + direct dialog construction + main_window import confirm no regression from the restructure.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- **Ready for 48-10 (Wave 2).** The skeleton is in place: 8 verbatim-migrated pages in a QStackedWidget+QListWidget TOC. Plan 48-10 will add 4 new v4.7 content pages (Extended Lattice Types, Custom Guest in Hydrate, Mixed Cage Occupancy, Depol Mode) onto this skeleton using the existing `_add_section` + `_make_page` helpers, and fix the "sI, sII, sH" line on the Workflow page.
- **No blockers.** The `_add_section(title, content_widget)` + `_make_page(label)` helpers make adding a new page a 2-line operation (build a QLabel, call `_add_section(title, self._make_page(label))`), so 48-10's content work is decoupled from this skeleton work.
- **Verification recipe established.** The byte-identical content verification (extract `QLabel.text()` per page, compare against original strings) can be reused/extended by 48-10 to verify new v4.7 page content.

---
*Phase: 48-documentation*
*Completed: 2026-07-12*
