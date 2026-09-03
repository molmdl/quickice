"""Headless GUI e2e safety infrastructure for MainWindow-driven tests.

This module institutionalizes the hang/crash safety mechanics discovered and
probe-verified in ``.planning/phases/48.3-revise-tests-true-e2e/
48.3-RESEARCH-GUI-TESTING.md`` §3 (Blockers 1-5). Every helper below is backed
by a reproduced probe failure; omitting any one of them has empirically hung
or SIGABRT'd a pytest session:

- Blocker 1 (Qt XCB C-level hang): ``QT_QPA_PLATFORM=offscreen`` must be set
  before any Qt import. pytest-timeout's SIGALRM cannot interrupt C-level
  hangs, so prevention is the only cure.
- Blocker 2 (modal dialogs): a missed ``QMessageBox`` namespace hangs the test
  forever (``exec()`` blocks in C code, unkillable by SIGALRM). The COMPLETE
  catalog is patchable via :func:`patch_gui_modals` — the
  ``main_window.QMessageBox.information`` "Export Complete" modal fires on
  EVERY successful export through a real menu handler and was the dialog that
  hung the research probe.
- Blocker 3 (VTK headless crash): with an EMPTY/absent DISPLAY,
  ``is_vtk_available()`` returns True → real-structure rendering →
  ``std::bad_array_new_length`` core dump. Setting ``DISPLAY=localhost:11.0``
  is PROTECTIVE: it makes ``is_vtk_available()`` return False so MainWindow
  takes its documented no-VTK branches.
- Blocker 4 (thread teardown SIGABRT): a live QThread at interpreter exit
  raises ``QThread: Destroyed while thread is still running`` → SIGABRT (exit
  134) → poisons the whole pytest session. :func:`teardown_threads` MUST run
  in fixture teardown (try/finally or finalizer) so assertion failures still
  clean up.
- Blocker 5 (handler-created workers): ``_hydrate_worker``/``_ion_worker``
  are created INSIDE click handlers, so signals cannot be pre-connected.
  :func:`wait_for_mainwindow_state` polls the ``_current_*`` state attribute
  with a QEventLoop + QTimer instead.

NOT collected by pytest (no ``test_`` prefix — AGENTS.md non-collected-helper
convention). Import the fixtures/functions into a GUI test module to use them.
"""

import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import pytest

# ── Blocker 1 + Blocker 3 env guards (MUST run before ANY Qt import) ────────
# Force offscreen: MainWindow-level tests require it (XCB C-level hang with
# SSH-forwarded X11 + unset platform; 48.1-14/48.2-01/48.2-03 precedent).
os.environ["QT_QPA_PLATFORM"] = "offscreen"
# PROTECTIVE DISPLAY: if DISPLAY is empty/unset (or a non-forwarded local
# display like ":0"), is_vtk_available() returns True and rendering real
# structures headless crashes (std::bad_array_new_length). Any "localhost"
# DISPLAY flips the heuristic to False → MainWindow takes its no-VTK branches.
if not os.environ.get("DISPLAY", "").startswith("localhost"):
    os.environ["DISPLAY"] = "localhost:11.0"


@dataclass
class ModalMocks:
    """Handles to the patched modal classes, for per-test assertions.

    Attributes:
        main_window: MagicMock replacing ``quickice.gui.main_window.QMessageBox``
            (information / warning / critical capture calls; question → Yes).
        export: MagicMock replacing ``quickice.gui.export.QMessageBox``
            (whole class — overwrite prompts, export error dialogs).
        export_file_dialog: MagicMock replacing
            ``quickice.gui.export.QFileDialog.getSaveFileName``. Set
            ``.return_value = (path, filter)`` per export to route the save
            dialog; default ``("", "")`` = user cancelled.
        panel: MagicMock replacing
            ``quickice.gui.custom_molecule_panel.QMessageBox`` (question → Yes
            for the generic-residue proceed path; warning captured).
    """

    main_window: MagicMock = field(default_factory=MagicMock)
    export: MagicMock = field(default_factory=MagicMock)
    export_file_dialog: MagicMock = field(default_factory=MagicMock)
    panel: MagicMock = field(default_factory=MagicMock)


@contextmanager
def patch_gui_modals():
    """Patch the COMPLETE Blocker-2 modal catalog (research §3, table).

    Patch the USING module's namespace, never ``PySide6.QtWidgets`` directly
    (repo Pattern B — e.g. tests/test_e2e_custom_guest_cross_tab_gui.py).

    Catalog (each entry = a probe-verified hang source if missed):
    - ``quickice.gui.main_window.QMessageBox``: ``information`` is the
      "Export Complete" modal that fires on EVERY successful export via a
      real ``_on_export_*_gromacs`` handler — the one that hung the research
      probe; ``warning`` (No Interface / No Hydrate / No Config / NaN guard);
      ``critical`` (generation/insertion error slots — captured so failures
      are observable instead of silent); ``question`` → Yes ("Previous
      Custom Molecules Found" re-insertion path).
    - ``quickice.gui.export.QMessageBox``: whole class (exporter-side
      dialogs; question → Yes for overwrite prompts).
    - ``quickice.gui.export.QFileDialog.getSaveFileName``: exactly one call
      per export (the ``.gro``); ``.top``/``.itp`` paths derive from the stem.
      Parametrize via the returned mock's ``return_value``.
    - ``quickice.gui.custom_molecule_panel.QMessageBox``: ``question`` → Yes
      (generic-residue-name dialog for the realistic unrenamed etoh upload —
      the D1 proceed path); ``warning`` captured.

    Yields:
        ModalMocks with all four mocks for call assertions.

    NOTE: the two remaining QMessageBox sites outside this catalog
    (quickice/gui/hydrate_panel.py:383 and its QFileDialog) belong to the
    custom-GUEST upload dialog flow, which the fullchain e2e does not
    exercise (research §3: "only 2 usages total ... rare paths").
    """
    # Lazy imports: keep module import cheap for pytest --collect-only gates
    # (GATE-COUNT/GATE-IDS); PySide6 + main_window cost ~5s (Blocker 7) and
    # must only be paid when a GUI test actually runs.
    import quickice.gui.custom_molecule_panel as custom_molecule_panel_mod
    import quickice.gui.export as export_mod
    import quickice.gui.main_window as main_window_mod
    from PySide6.QtWidgets import QMessageBox as _RealQMessageBox

    yes = _RealQMessageBox.StandardButton.Yes

    mocks = ModalMocks()
    with patch.object(main_window_mod, "QMessageBox") as mw_qmb, \
            patch.object(export_mod, "QMessageBox") as export_qmb, \
            patch.object(custom_molecule_panel_mod, "QMessageBox") as panel_qmb, \
            patch.object(export_mod.QFileDialog, "getSaveFileName") as export_fd:
        # question → Yes: the flow-under-test must always proceed
        # (overwrite prompts, residue-mismatch proceed, re-insertion prompt).
        mw_qmb.question.return_value = yes
        export_qmb.question.return_value = yes
        panel_qmb.question.return_value = yes
        # Default save dialog = user cancelled ("", "") so an unparametrized
        # export fails fast with "no files exported" instead of writing to a
        # surprise location. Tests set .return_value per export case.
        export_fd.return_value = ("", "")

        mocks.main_window = mw_qmb
        mocks.export = export_qmb
        mocks.export_file_dialog = export_fd
        mocks.panel = panel_qmb
        yield mocks


def wait_for_mainwindow_state(mw, attr, timeout_ms=120000):
    """Poll ``getattr(mw, attr)`` until non-None (Blocker 5 workaround).

    Handler-created workers (``HydrateWorker``/``IonInsertionWorker``) cannot
    be pre-connected — they are constructed INSIDE the click handlers
    (main_window.py ``_on_hydrate_generate_clicked`` / ``_on_insert_ions``),
    so connect-then-trigger races. State polling is the verified workaround:
    run a QEventLoop, poll the ``_current_*`` attribute every 80 ms, with a
    hard single-shot QTimer backstop so a never-arriving result times out
    instead of hanging forever (SIGALRM cannot break a stuck event loop).

    Args:
        mw: MainWindow instance.
        attr: Attribute name to poll (e.g. ``"_current_hydrate_result"``).
        timeout_ms: Hard backstop timeout in milliseconds.

    Returns:
        The attribute value once non-None, or None on timeout (callers
        assert on it with a helpful message).
    """
    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()

    def poll():
        if getattr(mw, attr, None) is not None:
            loop.quit()

    def hard_timeout():
        loop.quit()

    poll_timer = QTimer()
    poll_timer.setInterval(80)
    poll_timer.timeout.connect(poll)

    backstop = QTimer()
    backstop.setSingleShot(True)
    backstop.timeout.connect(hard_timeout)

    poll_timer.start()
    backstop.start(timeout_ms)
    try:
        loop.exec()
    finally:
        poll_timer.stop()
        backstop.stop()
    return getattr(mw, attr, None)


def teardown_threads(mw):
    """quit()+wait() every QThread the driven flow created (Blocker 4).

    A live QThread at interpreter exit → ``QThread: Destroyed while thread is
    still running`` → SIGABRT (exit 134) → poisons the entire pytest session
    (probe-verified: happens even on mid-test assertion failures, because
    cleanup after the assert never runs). This helper is exception-safe per
    thread (RuntimeError if the underlying C++ object is already deleted) and
    MUST be called from fixture teardown via try/finally or finalizer so
    assertion failures still clean up.

    Threads quit()+wait(5000): ``_viewmodel._interface_thread``,
    ``_viewmodel._thread`` (viewmodel-owned QThreads),
    ``mw._custom_worker_thread`` (thread hosting CustomMoleculeWorker).
    QThread workers wait(5000): ``_hydrate_worker``, ``_ion_worker``
    (direct QThread subclasses — AGENTS.md forbids migrating them).

    All attributes are getattr-guarded: legs the fixture did not drive leave
    the attribute unset/None, and that must not raise.
    """
    from PySide6.QtCore import QThread

    def _quit_and_wait(thread_obj):
        try:
            thread_obj.quit()
            thread_obj.wait(5000)
        except RuntimeError:
            # C++ object already deleted (deleteLater chain) — done.
            pass

    def _wait(worker_obj):
        try:
            worker_obj.wait(5000)
        except RuntimeError:
            pass

    # Viewmodel-owned threads (interface generation + ice generation)
    viewmodel = getattr(mw, "_viewmodel", None)
    if viewmodel is not None:
        for attr in ("_interface_thread", "_thread"):
            thread_obj = getattr(viewmodel, attr, None)
            if thread_obj is not None:
                _quit_and_wait(thread_obj)

    # Thread hosting the CustomMoleculeWorker (QObject moved into it)
    custom_thread = getattr(mw, "_custom_worker_thread", None)
    if custom_thread is not None:
        _quit_and_wait(custom_thread)

    # Direct QThread workers. NOTE: mw._custom_worker is a plain QObject
    # (CustomMoleculeWorker, moved to _custom_worker_thread) — it has no
    # wait(); its lifetime is covered by quitting the hosting thread above.
    for attr in ("_hydrate_worker", "_ion_worker"):
        worker = getattr(mw, attr, None)
        if worker is not None and isinstance(worker, QThread):
            _wait(worker)


__all__ = [
    "ModalMocks",
    "patch_gui_modals",
    "qapp_session",
    "teardown_threads",
    "wait_for_mainwindow_state",
]


@pytest.fixture(scope="module")
def qapp_session():
    """Module-scoped QApplication with the headless env guards applied.

    The env forcing happened at MODULE IMPORT time (top of this file), i.e.
    strictly BEFORE any Qt import this module (or its importers) performs —
    Blocker 1. The DISPLAY guard (Blocker 3) makes ``is_vtk_available()``
    return False so MainWindow takes its no-VTK branches instead of rendering
    real structures headless (std::bad_array_new_length core dump).

    Reuses the QApplication singleton when one already exists (repo Pattern A
    — pytest may run multiple GUI files in one process).
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    yield app
