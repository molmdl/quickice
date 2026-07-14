"""Headless smoke test for the restructured QuickReferenceDialog.

Covers DOCS-02 (in-app): asserts the help dialog is restructured to
QStackedWidget + QListWidget TOC with 11 pages, no stale v4.5 strings,
and all 10 lattice types in the Extended Lattice Types page.

Per AGENTS.md: use QT_QPA_PLATFORM=offscreen on headless machines.
help_dialog.py has NO VTK imports, so it is safe to run headless.
"""

import os
import sys

# Ensure offscreen platform for headless environments.
# This is set via QT_QPA_PLATFORM=offscreen env var at runtime;
# the import below is a safety net if the env var is not set.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from quickice.gui.help_dialog import QuickReferenceDialog


# 10 HYDRATE_LATTICES keys (sourced from types.py:84-199)
ALL_LATTICE_KEYS = [
    "sI", "sII", "sH", "c0te", "c1te", "c2te",
    "ice1hte", "sTprime", "16", "17",
]


@pytest.fixture
def dialog():
    """Construct a QuickReferenceDialog for testing (no show/exec needed).

    QApplication is required for any QWidget construction in PySide6 headless
    mode. tests/conftest.py provides no QApplication fixture (it is API-only),
    so the singleton pattern from tests/test_hydrate_panel.py is used here:
    create QApplication once if it does not already exist.
    """
    if not QApplication.instance():
        QApplication(sys.argv)
    return QuickReferenceDialog()


class TestHelpDialogStructure:
    """Test the restructured help dialog has the correct TOC + pages."""

    def test_dialog_constructs_without_error(self, dialog):
        """Dialog can be constructed under offscreen platform."""
        assert dialog is not None

    def test_toc_has_11_entries(self, dialog):
        """TOC should have exactly 11 entries (8 migrated + 3 new - 1 combined)."""
        assert dialog.toc.count() == 11

    def test_pages_has_11_pages(self, dialog):
        """QStackedWidget should have exactly 11 pages matching TOC."""
        assert dialog.pages.count() == 11

    def test_toc_and_pages_in_sync(self, dialog):
        """TOC count and pages count should match."""
        assert dialog.toc.count() == dialog.pages.count()

    def test_toc_entries_present(self, dialog):
        """All 4 new v4.7 section titles should be in the TOC."""
        titles = [dialog.toc.item(i).text() for i in range(dialog.toc.count())]
        title_text = " ".join(titles)
        assert "Extended Lattice Types" in title_text, f"Missing Extended Lattice Types in {titles}"
        assert "Custom Guest" in title_text, f"Missing Custom Guest in {titles}"
        assert "Mixed Cage Occupancy" in title_text, f"Missing Mixed Cage Occupancy in {titles}"
        assert "Depol" in title_text, f"Missing Depol in {titles}"


class TestHelpDialogContent:
    """Test the help dialog content is v4.7-correct."""

    def _all_page_text(self, dialog):
        """Collect all text from all pages for grep-style assertions."""
        texts = []
        for i in range(dialog.pages.count()):
            page = dialog.pages.widget(i)
            if page is not None:
                # Find all QLabels in the page (recursively)
                labels = page.findChildren(QLabel)
                for label in labels:
                    texts.append(label.text())
        return " ".join(texts)

    def test_no_stale_v45_string(self, dialog):
        """No page should contain the stale 'v4.5' version string."""
        all_text = self._all_page_text(dialog)
        assert "v4.5" not in all_text, f"Stale v4.5 string found in help dialog: {all_text[:200]}"

    def test_all_10_lattice_keys_present(self, dialog):
        """All 10 lattice keys should appear in the help dialog (Extended Lattice Types page)."""
        all_text = self._all_page_text(dialog)
        for key in ALL_LATTICE_KEYS:
            assert key in all_text, f"Lattice key '{key}' not found in help dialog text"

    def test_custom_guest_marked_gui_only(self, dialog):
        """Custom guest in hydrate should be marked as GUI-only."""
        all_text = self._all_page_text(dialog)
        assert "GUI-only" in all_text or "GUI only" in all_text, \
            "Custom guest in hydrate not marked GUI-only"

    def test_deprecated_flags_mentioned(self, dialog):
        """The help dialog should mention that --guest/--cage-occupancy-* are deprecated."""
        all_text = self._all_page_text(dialog)
        assert "deprecated" in all_text.lower() or "DEPRECATED" in all_text, \
            "Deprecated flags not mentioned in help dialog"


class TestHelpDialogNavigation:
    """Test TOC navigation switches pages."""

    def test_set_current_row_changes_page(self, dialog):
        """Setting a TOC row should switch the stacked widget page."""
        dialog.toc.setCurrentRow(3)  # Extended Lattice Types (position 4, 0-indexed 3)
        assert dialog.pages.currentIndex() == 3

    def test_first_row_selected_on_construction(self, dialog):
        """First TOC row should be selected (Introduction) on construction."""
        # The dialog sets setCurrentRow(0) in _setup_ui
        assert dialog.toc.currentRow() == 0
        assert dialog.pages.currentIndex() == 0
