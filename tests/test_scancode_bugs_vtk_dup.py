"""Regression tests for scancode VTK-DUP: shared VTK availability helper.

VTK-DUP (TECH-DEBT, M): The ``_VTK_AVAILABLE = False`` detection block
was copy-pasted across 6 GUI viewer files (custom_molecule_viewer,
hydrate_viewer, interface_panel, ion_viewer, solute_viewer, view). The
fix centralizes the detection logic in ``quickice.gui.vtk_utils.is_vtk_available``
and updates all 6 viewers to import and use the shared helper.

The detection result must be IDENTICAL to the old inline detection in
all environments (headless/offscreen, with/without VTK installed, SSH
X11 forwarding, local display). These tests verify:

1. ``is_vtk_available()`` returns the same value as the old inline
   detection across all env-var combinations (DISPLAY, QUICKICE_FORCE_VTK).
2. The result is cached after the first call.
3. All 6 viewers import ``is_vtk_available`` from ``quickice.gui.vtk_utils``
   (source-level check).
4. All 6 viewers still define ``_VTK_AVAILABLE`` (backward compat).
"""

import importlib
import os
from pathlib import Path
from unittest.mock import patch

import pytest

import quickice


REPO_ROOT = Path(quickice.__file__).resolve().parent.parent
GUI_DIR = Path(quickice.__file__).parent / "gui"

# The 6 viewer files that previously copy-pasted the _VTK_AVAILABLE block.
VIEWER_FILES = [
    "custom_molecule_viewer.py",
    "hydrate_viewer.py",
    "interface_panel.py",
    "ion_viewer.py",
    "solute_viewer.py",
    "view.py",
]


# ── is_vtk_available matches the old inline detection ─────────────────────────


def _old_inline_detection(display: str, force_vtk: str) -> bool:
    """Re-implement the OLD inline detection logic (the copy-pasted block).

    This is the exact code that lived in every viewer before VTK-DUP:
    ``_VTK_AVAILABLE = False; try: if DISPLAY and 'localhost' in DISPLAY:
    _VTK_AVAILABLE = (FORCE_VTK == 'true'); else: _VTK_AVAILABLE = True;
    except Exception: _VTK_AVAILABLE = False``.

    Kept here as the byte-equivalence oracle.
    """
    _vtk_available = False
    try:
        if display and 'localhost' in display:
            _vtk_available = force_vtk.lower() == 'true'
        else:
            _vtk_available = True
    except Exception:
        _vtk_available = False
    return _vtk_available


class TestIsVtkAvailableMatchesOldInline:
    """``is_vtk_available()`` must return the same value as the old inline
    detection across all env-var combinations."""

    @pytest.mark.parametrize(
        "display, force_vtk, expected",
        [
            # No DISPLAY (headless / QT_QPA_PLATFORM=offscreen) -> True
            ("", "", True),
            (None, "", True),
            # Local display (no 'localhost') -> True
            (":0", "", True),
            (":1", "", True),
            ("/tmp/.X11-unix/X0", "", True),
            # SSH X11 forwarding (DISPLAY contains 'localhost') -> False
            ("localhost:11.0", "", False),
            ("localhost:10.0", "", False),
            ("localhost:0", "", False),
            # SSH X11 forwarding + QUICKICE_FORCE_VTK=true -> True
            ("localhost:11.0", "true", True),
            ("localhost:11.0", "True", True),
            ("localhost:11.0", "TRUE", True),
            # SSH X11 forwarding + QUICKICE_FORCE_VTK != 'true' -> False
            ("localhost:11.0", "false", False),
            ("localhost:11.0", "yes", False),
            ("localhost:11.0", "1", False),
            ("localhost:11.0", "anything", False),
        ],
    )
    def test_matches_old_inline(self, display, force_vtk, expected):
        """``is_vtk_available()`` matches the old inline detection for each
        env-var combination."""
        from quickice.gui.vtk_utils import is_vtk_available, reset_vtk_available_cache

        reset_vtk_available_cache()
        env = {}
        if display is not None:
            env['DISPLAY'] = display
        if force_vtk:
            env['QUICKICE_FORCE_VTK'] = force_vtk
        with patch.dict(os.environ, env, clear=True):
            actual = is_vtk_available()
            old = _old_inline_detection(display or "", force_vtk)
        # Must match the old inline detection.
        assert actual == old == expected, (
            f"DISPLAY={display!r}, FORCE_VTK={force_vtk!r}: "
            f"is_vtk_available()={actual}, old_inline={old}, expected={expected}"
        )
        reset_vtk_available_cache()


class TestIsVtkAvailableCaching:
    """``is_vtk_available()`` caches the result after the first call."""

    def test_result_cached(self):
        """The second call returns the cached result without re-checking env."""
        from quickice.gui.vtk_utils import is_vtk_available, reset_vtk_available_cache

        reset_vtk_available_cache()
        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True):
            first = is_vtk_available()
            # Change env AFTER the first call — the cached result should NOT change.
            with patch.dict(os.environ, {"DISPLAY": "localhost:11.0"}, clear=True):
                second = is_vtk_available()
        assert first == second, (
            f"Caching broken: first={first}, second={second} after env change. "
            f"The result should be cached after the first call."
        )
        reset_vtk_available_cache()

    def test_reset_cache_re_evaluates(self):
        """``reset_vtk_available_cache()`` forces re-evaluation on next call."""
        from quickice.gui.vtk_utils import is_vtk_available, reset_vtk_available_cache

        reset_vtk_available_cache()
        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True):
            first = is_vtk_available()
        reset_vtk_available_cache()
        with patch.dict(os.environ, {"DISPLAY": "localhost:11.0"}, clear=True):
            second = is_vtk_available()
        assert first != second, (
            f"reset_cache broken: first={first} (DISPLAY=:0), "
            f"second={second} (DISPLAY=localhost:11.0). After reset, the "
            f"result should re-evaluate."
        )
        reset_vtk_available_cache()


# ── All 6 viewers import the shared helper ────────────────────────────────────


class TestViewersImportSharedHelper:
    """All 6 viewers must import ``is_vtk_available`` from
    ``quickice.gui.vtk_utils`` and use it for the ``_VTK_AVAILABLE`` check.
    This guards against re-introducing the copy-pasted detection block."""

    @pytest.mark.parametrize("viewer_file", VIEWER_FILES)
    def test_viewer_imports_is_vtk_available(self, viewer_file):
        """Source-level check: the viewer imports ``is_vtk_available`` from
        ``quickice.gui.vtk_utils``."""
        viewer_path = GUI_DIR / viewer_file
        content = viewer_path.read_text()
        assert "from quickice.gui.vtk_utils import is_vtk_available" in content, (
            f"{viewer_file} must import is_vtk_available from "
            f"quickice.gui.vtk_utils (VTK-DUP fix). Found no such import."
        )

    @pytest.mark.parametrize("viewer_file", VIEWER_FILES)
    def test_viewer_uses_is_vtk_available(self, viewer_file):
        """Source-level check: the viewer uses ``is_vtk_available()`` in the
        ``_VTK_AVAILABLE`` detection block."""
        viewer_path = GUI_DIR / viewer_file
        content = viewer_path.read_text()
        assert "if is_vtk_available():" in content, (
            f"{viewer_file} must use `if is_vtk_available():` for the "
            f"_VTK_AVAILABLE check (VTK-DUP fix). Found no such call."
        )

    @pytest.mark.parametrize("viewer_file", VIEWER_FILES)
    def test_viewer_defines_vtk_available(self, viewer_file):
        """Source-level check: the viewer still defines ``_VTK_AVAILABLE``
        (backward compat — downstream code reads this module-level variable)."""
        viewer_path = GUI_DIR / viewer_file
        content = viewer_path.read_text()
        assert "_VTK_AVAILABLE = False" in content, (
            f"{viewer_file} must still define _VTK_AVAILABLE (backward compat)."
        )

    @pytest.mark.parametrize("viewer_file", VIEWER_FILES)
    def test_viewer_no_old_inline_detection(self, viewer_file):
        """Source-level check: the viewer does NOT contain the old
        copy-pasted inline detection block (the ``os.environ.get('DISPLAY')``
        and ``'localhost' in`` heuristics). These now live in vtk_utils."""
        viewer_path = GUI_DIR / viewer_file
        content = viewer_path.read_text()
        # The old inline detection checked 'localhost' in DISPLAY. This
        # heuristic should NOT appear in the viewer anymore (it's in
        # vtk_utils.is_vtk_available now).
        assert "'localhost' in os.environ.get('DISPLAY'" not in content, (
            f"{viewer_file} still contains the old inline VTK detection "
            f"heuristic ('localhost' in DISPLAY). This should be removed — "
            f"use is_vtk_available() from quickice.gui.vtk_utils instead."
        )


# ── vtk_utils.py hosts the helper ─────────────────────────────────────────────


class TestVtkUtilsHostsHelper:
    """``quickice.gui.vtk_utils`` must define ``is_vtk_available`` and
    ``reset_vtk_available_cache``."""

    def test_is_vtk_available_defined(self):
        from quickice.gui.vtk_utils import is_vtk_available
        assert callable(is_vtk_available), "is_vtk_available must be callable"

    def test_reset_cache_defined(self):
        from quickice.gui.vtk_utils import reset_vtk_available_cache
        assert callable(reset_vtk_available_cache), (
            "reset_vtk_available_cache must be callable (for tests)"
        )

    def test_vtk_utils_preserves_existing_functions(self):
        """VTK-DUP must NOT remove the existing functions in vtk_utils
        (candidate_to_vtk_molecule, create_hbond_actor, etc.). The helper is
        APPENDED, not a replacement."""
        from quickice.gui import vtk_utils
        # Check a few key functions that viewers import.
        assert hasattr(vtk_utils, 'candidate_to_vtk_molecule'), (
            "VTK-DUP must not remove candidate_to_vtk_molecule from vtk_utils"
        )
        assert hasattr(vtk_utils, 'create_hbond_actor'), (
            "VTK-DUP must not remove create_hbond_actor from vtk_utils"
        )
