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


class TestSAFE07NanInfConcentration:
    """SAFE-07: NaN/Inf/None concentration must be rejected before round().

    The old ``if concentration <= 0`` guard missed NaN (NaN <= 0 is False) and
    Inf, so they reached ``int(round(concentration))`` inside
    ``ion_inserter.py:calculate_ion_pairs`` (line 222) and crashed with an
    unhelpful ``ValueError: cannot convert float NaN to integer``. The
    hardened guard rejects None/NaN/Inf/<=0 with a clear
    ``QMessageBox.warning`` BEFORE any worker construction or round() call.

    These tests use ``MagicMock`` for the config (so NaN/Inf/None can be held
    without ``IonConfig.__post_init__`` raising) and call ``_on_insert_ions``
    directly on a MagicMock self — no MainWindow construction (matches the
    SAFE-01 runtime-test approach).
    """

    def test_concentration_check_rejects_nan_inf_none_in_source(self):
        """_on_insert_ions source must guard against None/NaN/Inf."""
        src = inspect.getsource(MainWindow._on_insert_ions)
        assert "math.isnan" in src, "must check math.isnan(concentration)"
        assert "math.isinf" in src, "must check math.isinf(concentration)"
        assert "concentration is None" in src, "must check concentration is None"

    def test_math_imported_at_module_level(self):
        """main_window must import math (for the isnan/isinf checks)."""
        import quickice.gui.main_window as mw
        assert hasattr(mw, "math"), "main_window module must import math"

    def test_guard_precedes_worker_construction(self):
        """The NaN/Inf guard must come before IonInsertionWorker construction.

        The guard must fire BEFORE the worker is constructed/started; otherwise
        NaN/Inf would reach insert_ions -> int(round(...)) on the worker thread
        and crash with an unhelpful ValueError instead of a clean warning.
        """
        src = inspect.getsource(MainWindow._on_insert_ions)
        guard_idx = src.find("math.isnan")
        worker_idx = src.find("IonInsertionWorker(")
        assert guard_idx != -1, "must have math.isnan guard"
        assert worker_idx != -1, "must construct IonInsertionWorker"
        assert guard_idx < worker_idx, \
            "NaN/Inf guard must come before IonInsertionWorker construction"

    def _make_fake_self(self, concentration):
        """Build a MagicMock self with ion_panel returning the given concentration.

        Uses a MagicMock config so NaN/Inf/None can be held without
        IonConfig.__post_init__ raising (None < 0 raises TypeError; NaN/Inf
        pass __post_init__ but the GUI check must still catch them).
        """
        fake_button = MagicMock()
        fake_panel = MagicMock()
        fake_panel.get_configuration.return_value = MagicMock(
            concentration_molar=concentration
        )
        fake_panel.get_current_source.return_value = "Interface"
        fake_panel.get_liquid_volume.return_value = 10.0
        fake_panel.insert_button = fake_button
        fake_self = MagicMock()
        fake_self.ion_panel = fake_panel
        fake_self._current_interface_result = MagicMock()  # non-None interface
        return fake_self, fake_button

    def test_nan_concentration_triggers_warning_and_returns_early(self):
        """NaN concentration: QMessageBox.warning shown, no worker constructed.

        Core SAFE-07 runtime guarantee: NaN must NOT reach insert_ions (which
        would crash int(round(NaN))). The hardened guard shows a clear warning
        and returns before constructing the worker.
        """
        _ensure_qapp()
        fake_self, fake_button = self._make_fake_self(float("nan"))
        with patch("quickice.gui.main_window.QMessageBox") as mock_qmb:
            with patch("quickice.gui.main_window.IonInsertionWorker") as mock_worker_cls:
                MainWindow._on_insert_ions(fake_self)
        mock_qmb.warning.assert_called_once()
        mock_worker_cls.assert_not_called()
        # Button NOT disabled (early return before the disable/start lines)
        fake_button.setEnabled.assert_not_called()

    def test_inf_concentration_triggers_warning_and_returns_early(self):
        """Inf concentration: QMessageBox.warning shown, no worker constructed."""
        _ensure_qapp()
        fake_self, fake_button = self._make_fake_self(float("inf"))
        with patch("quickice.gui.main_window.QMessageBox") as mock_qmb:
            with patch("quickice.gui.main_window.IonInsertionWorker") as mock_worker_cls:
                MainWindow._on_insert_ions(fake_self)
        mock_qmb.warning.assert_called_once()
        mock_worker_cls.assert_not_called()
        fake_button.setEnabled.assert_not_called()

    def test_negative_inf_concentration_triggers_warning_and_returns_early(self):
        """-Inf concentration: QMessageBox.warning shown (caught by math.isinf)."""
        _ensure_qapp()
        fake_self, fake_button = self._make_fake_self(float("-inf"))
        with patch("quickice.gui.main_window.QMessageBox") as mock_qmb:
            with patch("quickice.gui.main_window.IonInsertionWorker") as mock_worker_cls:
                MainWindow._on_insert_ions(fake_self)
        mock_qmb.warning.assert_called_once()
        mock_worker_cls.assert_not_called()

    def test_none_concentration_triggers_warning_and_returns_early(self):
        """None concentration: QMessageBox.warning shown, no worker constructed.

        Uses a MagicMock config (a real IonConfig cannot hold None — its
        __post_init__ ``if concentration_molar < 0`` would raise TypeError on
        None). The GUI handler's ``concentration is None`` short-circuits
        before ``math.isnan(None)`` (which would also raise TypeError).
        """
        _ensure_qapp()
        fake_self, fake_button = self._make_fake_self(None)
        with patch("quickice.gui.main_window.QMessageBox") as mock_qmb:
            with patch("quickice.gui.main_window.IonInsertionWorker") as mock_worker_cls:
                MainWindow._on_insert_ions(fake_self)
        mock_qmb.warning.assert_called_once()
        mock_worker_cls.assert_not_called()
        fake_button.setEnabled.assert_not_called()

    def test_zero_concentration_triggers_warning_and_returns_early(self):
        """Zero concentration: still rejected by the `<= 0` part of the guard."""
        _ensure_qapp()
        fake_self, fake_button = self._make_fake_self(0.0)
        with patch("quickice.gui.main_window.QMessageBox") as mock_qmb:
            with patch("quickice.gui.main_window.IonInsertionWorker") as mock_worker_cls:
                MainWindow._on_insert_ions(fake_self)
        mock_qmb.warning.assert_called_once()
        mock_worker_cls.assert_not_called()

    def test_valid_concentration_still_passes(self):
        """A valid positive concentration must still proceed to worker construction.

        Regression guard: the hardened check must NOT over-reject valid inputs.
        A valid 0.5 M concentration should pass the guard and construct +
        start the IonInsertionWorker (mocked so start() is a no-op), with the
        button disabled during work.
        """
        _ensure_qapp()
        fake_self, fake_button = self._make_fake_self(0.5)
        mock_worker = MagicMock()
        with patch("quickice.gui.main_window.IonInsertionWorker",
                   return_value=mock_worker) as mock_worker_cls:
            with patch("quickice.gui.main_window.QMessageBox") as mock_qmb:
                MainWindow._on_insert_ions(fake_self)
        # No warning shown for valid concentration
        mock_qmb.warning.assert_not_called()
        # Worker constructed and started (valid input proceeds)
        mock_worker_cls.assert_called_once()
        mock_worker.start.assert_called_once()
        # Button disabled during work
        fake_button.setEnabled.assert_any_call(False)

    def test_int_round_nan_raises_valueerror_documents_bug(self):
        """Document the crash SAFE-07 prevents: int(round(nan/inf)) crashes.

        Without the GUI-level guard, NaN/Inf would reach
        ``ion_inserter.py:222 int(round(n_formula_units))`` and crash with an
        unhelpful exception (ValueError for NaN, OverflowError for Inf) and no
        guided user message. This test documents WHY the pre-check is needed.
        """
        # NaN raises ValueError
        with pytest.raises((ValueError, OverflowError)):
            int(round(float("nan")))
        # Inf / -Inf raise OverflowError
        with pytest.raises((ValueError, OverflowError)):
            int(round(float("inf")))
        with pytest.raises((ValueError, OverflowError)):
            int(round(float("-inf")))

    def test_nan_comparison_returns_false_documents_old_guard_gap(self):
        """Document WHY the old `<= 0` guard missed NaN: NaN comparisons return False.

        ``float('nan') <= 0`` is False, so NaN slipped past the old guard.
        ``float('inf') <= 0`` is also False, so Inf slipped past too. The
        hardened guard uses ``math.isnan``/``math.isinf`` to catch these
        explicitly (NaN is unordered — all comparisons with NaN return False).
        """
        import math
        assert not (float("nan") <= 0), "NaN <= 0 is False (old guard missed NaN)"
        assert not (float("inf") <= 0), "Inf <= 0 is False (old guard missed Inf)"
        assert not (float("nan") > 0), "NaN is unordered — all comparisons False"
        assert math.isnan(float("nan")), "math.isnan correctly identifies NaN"
        assert math.isinf(float("inf")), "math.isinf correctly identifies Inf"

    def test_ionconfig_post_init_misses_nan_documents_defense_in_depth(self):
        """IonConfig.__post_init__ ALSO misses NaN — GUI check is the real guard.

        IonConfig.__post_init__ uses ``if self.concentration_molar < 0``, which
        also returns False for NaN (NaN is unordered). So
        ``IonConfig(concentration_molar=float('nan'))`` constructs successfully —
        the NaN is only caught by the GUI handler's hardened check. This is why
        the SAFE-07 fix lives in main_window.py (the GUI boundary) rather than
        relying on IonConfig's own validation.
        """
        import math
        from quickice.structure_generation.types import IonConfig
        # IonConfig.__post_init__ does NOT reject NaN (NaN < 0 is False)
        config = IonConfig(concentration_molar=float("nan"))
        assert math.isnan(config.concentration_molar), (
            "IonConfig holds NaN (its __post_init__ misses it — the GUI "
            "handler's hardened check is the real guard)"
        )
