"""Regression tests for scancode-verified GUI bugs (SAFE-01, SAFE-07).

SAFE-01 (MEDIUM): Ion insertion ran synchronously on the main GUI thread at
``main_window.py`` (old line ~935), freezing the UI. Fixed by introducing
``IonInsertionWorker(QThread)`` mirroring the existing ``HydrateWorker``
pattern (direct QThread subclass per AGENTS.md — NOT QObject+moveToThread),
moving ``insert_ions()`` into the worker's ``run()`` with a lazy import, and
delivering the result via signals to main-thread handlers that disable the
Insert Ions button before ``start()`` and re-enable it on completion/error.

SAFE-07 (LOW): NaN/Inf concentration passed the ``if concentration <= 0``
guard (NaN comparisons return False) and crashed ``int(round(NaN))`` inside
``ion_inserter.py:calculate_ion_pairs`` with an unhelpful ``ValueError``.
Fixed by hardening the guard to reject ``None``/``NaN``/``Inf``/``<=0`` with a
clear user-facing ``QMessageBox.warning`` before any ``round()`` call.

Per AGENTS.md: ``QT_QPA_PLATFORM=offscreen`` for headless; mock/skip VTK.
MainWindow is heavy (viewmodel + exporters + VTK panels), so these tests use
``inspect.getsource`` (matches the existing
``tests/test_hydrate_panel.py::test_export_*_handler_passes_hydrate_config``
pattern) plus targeted runtime checks that construct only the lightweight
``IonInsertionWorker`` (QApplication only, no VTK) or call handler methods on
a ``MagicMock`` self (no MainWindow construction).
"""

import os
import sys
import inspect
import threading
from unittest.mock import patch, MagicMock

import pytest

# Headless Qt (AGENTS.md headless constraint / ROADMAP TEST-06)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtCore import QThread  # noqa: E402

from quickice.gui.main_window import MainWindow, IonInsertionWorker  # noqa: E402


def _ensure_qapp():
    """Ensure a QApplication exists (singleton pattern, headless)."""
    if not QApplication.instance():
        QApplication(sys.argv)


class TestSAFE01IonInsertionWorker:
    """SAFE-01: ion insertion must run off the GUI thread via IonInsertionWorker.

    These tests guard against reversion of the SAFE-01 fix. If the ion
    insertion handler is reverted to call ``insert_ions()`` synchronously on
    the main thread, the thread-identity and source-inspection tests below
    will fail.
    """

    def test_ion_insertion_worker_is_qthread_subclass(self):
        """IonInsertionWorker must subclass QThread directly (AGENTS.md pattern).

        AGENTS.md: HydrateWorker subclasses QThread directly (NOT
        QObject+moveToThread). IonInsertionWorker must follow the SAME
        direct-subclass pattern for consistency.
        """
        assert issubclass(IonInsertionWorker, QThread)

    def test_ion_insertion_worker_has_required_signals(self):
        """IonInsertionWorker must declare progress/complete/error signals.

        Mirrors HydrateWorker's three signals (progress_updated,
        generation_complete, generation_error). The worker MUST NOT mutate
        GUI widgets from run() — it emits signals that MainWindow connects to.
        """
        src = inspect.getsource(IonInsertionWorker)
        assert "progress_updated = Signal" in src, \
            "IonInsertionWorker must declare progress_updated signal"
        assert "insertion_complete = Signal" in src, \
            "IonInsertionWorker must declare insertion_complete signal"
        assert "insertion_error = Signal" in src, \
            "IonInsertionWorker must declare insertion_error signal"

    def test_insert_ions_runs_off_main_thread(self):
        """insert_ions must be called on the worker thread, not the main thread.

        Constructs IonInsertionWorker (QApplication only — no VTK, no
        MainWindow), mocks ``insert_ions`` at its lazy-import source to
        capture the calling thread, starts the worker, blocks on
        ``worker.wait()`` until ``run()`` finishes, and asserts the captured
        thread is not the main thread. This is the core SAFE-01 guarantee.
        """
        _ensure_qapp()
        main_thread = threading.current_thread()
        captured = []

        def fake_insert_ions(interface, concentration, volume_arg):
            captured.append(threading.current_thread())
            # Return a lightweight IonStructure-like object (na_count/cl_count
            # are read by the worker for its progress message)
            return MagicMock(na_count=0, cl_count=0)

        # Patch the lazy import target inside IonInsertionWorker.run()
        # (run() does: from quickice.structure_generation.ion_inserter import insert_ions)
        with patch(
            "quickice.structure_generation.ion_inserter.insert_ions",
            fake_insert_ions,
        ):
            worker = IonInsertionWorker(
                interface=MagicMock(),
                concentration_molar=0.5,
                liquid_volume_nm3=None,
            )
            worker.start()
            # Block until run() finishes (no event loop needed for thread-side
            # execution; signal emissions to the main thread are queued and
            # irrelevant to this thread-identity assertion).
            finished = worker.wait(10000)  # 10s timeout

        assert finished, "IonInsertionWorker.run() did not finish within 10s"
        assert len(captured) == 1, (
            f"insert_ions should be called exactly once, got {len(captured)} calls"
        )
        assert captured[0] is not main_thread, (
            "insert_ions must NOT run on the main thread (SAFE-01). "
            f"Called on {captured[0]}, main is {main_thread}"
        )

    def test_on_insert_ions_disables_button_and_starts_worker(self):
        """_on_insert_ions disables insert_button and starts IonInsertionWorker.

        Runtime check (no MainWindow construction): calls ``_on_insert_ions``
        on a MagicMock self with a valid concentration and a non-None interface,
        mocks ``IonInsertionWorker`` so ``start()`` is a no-op, and asserts the
        button was disabled (``setEnabled(False)``) and the worker's
        ``start()`` was called. Mirrors the HydrateWorker button lifecycle
        (disabled before ``start()``, re-enabled in complete/error handlers).
        """
        _ensure_qapp()
        from quickice.structure_generation.types import IonConfig

        fake_button = MagicMock()
        fake_panel = MagicMock()
        fake_panel.get_configuration.return_value = IonConfig(concentration_molar=0.5)
        fake_panel.get_current_source.return_value = "Interface"
        fake_panel.get_liquid_volume.return_value = 10.0
        fake_panel.insert_button = fake_button

        fake_self = MagicMock()
        fake_self.ion_panel = fake_panel
        # non-None interface so the Interface-source None check passes
        fake_self._current_interface_result = MagicMock()

        mock_worker = MagicMock()
        with patch("quickice.gui.main_window.IonInsertionWorker", return_value=mock_worker) \
                as mock_worker_cls:
            with patch("quickice.gui.main_window.QMessageBox"):
                MainWindow._on_insert_ions(fake_self)

        # Worker constructed and started
        mock_worker_cls.assert_called_once()
        mock_worker.start.assert_called_once()
        # Button disabled (before start — the handler disables then starts)
        fake_button.setEnabled.assert_any_call(False)

    def test_on_insert_ions_does_not_call_insert_ions_directly(self):
        """_on_insert_ions must NOT call insert_ions() synchronously (SAFE-01).

        The synchronous call must be gone from the handler; the worker calls
        it lazily inside run() instead. This catches reversion to the old
        ``ion_structure = insert_ions(...)`` pattern.

        The method name ``_on_insert_ions`` itself contains the substring
        ``insert_ions``, so the assertion uses a negative lookbehind for
        ``_on_`` to exclude the method definition and targets only real
        call sites of ``insert_ions(``.
        """
        import re
        src = inspect.getsource(MainWindow._on_insert_ions)
        # Match "insert_ions(" that is NOT part of "_on_insert_ions(" (the
        # method name). A real synchronous call would appear as
        # "insert_ions(" not preceded by "_on_".
        matches = re.findall(r'(?<!_on_)insert_ions\s*\(', src)
        assert matches == [], (
            "_on_insert_ions must not call insert_ions() directly; "
            "IonInsertionWorker.run() should call it instead (SAFE-01). "
            f"Found direct call(s): {matches}"
        )

    def test_on_ion_insertion_complete_reenables_button(self):
        """_on_ion_insertion_complete re-enables insert_button and stores result.

        Runtime check: calls the complete handler on a MagicMock self with a
        mock IonStructure and asserts the button was re-enabled
        (``setEnabled(True)``) and the result was stored on
        ``_current_ion_result``.
        """
        _ensure_qapp()
        fake_button = MagicMock()
        fake_panel = MagicMock()
        fake_panel.insert_button = fake_button
        fake_panel.ion_viewer = MagicMock()

        fake_self = MagicMock()
        fake_self.ion_panel = fake_panel
        fake_self._ion_pending_interface = MagicMock()
        fake_self._ion_pending_source = "Interface"
        fake_self._current_ion_result = None

        mock_ion_structure = MagicMock()
        mock_ion_structure.na_count = 2
        mock_ion_structure.cl_count = 2

        MainWindow._on_ion_insertion_complete(fake_self, mock_ion_structure)

        fake_button.setEnabled.assert_any_call(True)
        assert fake_self._current_ion_result is mock_ion_structure, (
            "complete handler must store the ion_structure on _current_ion_result"
        )

    def test_on_ion_insertion_error_reenables_button(self):
        """_on_ion_insertion_error re-enables insert_button and shows an error.

        Runtime check: calls the error handler on a MagicMock self and asserts
        the button was re-enabled (``setEnabled(True)``) so the UI is not left
        in a stuck-disabled state after a worker failure.
        """
        _ensure_qapp()
        fake_button = MagicMock()
        fake_panel = MagicMock()
        fake_panel.insert_button = fake_button

        fake_self = MagicMock()
        fake_self.ion_panel = fake_panel

        with patch("quickice.gui.main_window.QMessageBox"):
            MainWindow._on_ion_insertion_error(fake_self, "test error")

        fake_button.setEnabled.assert_any_call(True)

    def test_worker_run_does_not_mutate_gui_widgets(self):
        """IonInsertionWorker.run() must not touch GUI widgets (AGENTS.md).

        run() runs on the worker thread; touching widgets from a non-GUI
        thread is unsafe in Qt. The worker must emit signals instead; the
        main-thread handlers perform all widget mutations.
        """
        src = inspect.getsource(IonInsertionWorker.run)
        assert ".setEnabled(" not in src, \
            "run() must not mutate widget enabled state (emit signals instead)"
        assert ".setText(" not in src, \
            "run() must not mutate widget text (emit signals instead)"
        assert "QMessageBox" not in src, \
            "run() must not show dialogs (emit signals instead)"
        # Must emit signals rather than mutating self.* widgets
        assert "self.insertion_complete.emit" in src or \
               "self.insertion_error.emit" in src, \
            "run() must emit insertion_complete or insertion_error signals"

    def test_worker_run_lazy_imports_insert_ions(self):
        """IonInsertionWorker.run() must lazy-import insert_ions (mirror HydrateWorker).

        HydrateWorker.run() imports HydrateStructureGenerator INSIDE run() to
        avoid blocking the main thread during import. IonInsertionWorker must
        do the same with insert_ions.
        """
        src = inspect.getsource(IonInsertionWorker.run)
        assert "from quickice.structure_generation.ion_inserter import" in src, \
            "run() must lazy-import insert_ions (mirror HydrateWorker lazy import)"
