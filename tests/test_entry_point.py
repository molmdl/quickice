"""Tests for the unified entry point (python -m quickice).

Validates routing behavior per Phase 37 CONTEXT.md:
- No args → help message (like git)
- --help → full argparse help
- --version → version string
- --cli alone → argparse error (required --temperature)
- --cli + pipeline flags → CLI mode
- Pipeline flags (implicit CLI) → CLI mode
- --gui + missing PySide6 → error with install hint
- --gui + no display → error
- Backward compat: quickice.py still works
"""

import subprocess
import sys
import unittest.mock

import pytest

from tests.conftest import run_quickice


# ── No arguments → help ───────────────────────────────────────────────────────


class TestNoArgs:
    """python -m quickice with no arguments shows help."""

    def test_no_args_exit_zero(self):
        """No args → exit code 0."""
        rc, stdout, stderr = run_quickice()
        assert rc == 0

    def test_no_args_shows_usage(self):
        """No args → usage/help text in stdout."""
        rc, stdout, stderr = run_quickice()
        assert "python -m quickice" in stdout
        assert "--temperature" in stdout


# ── --help and --version ──────────────────────────────────────────────────────


class TestHelpAndVersion:
    """--help and --version flags."""

    def test_help_exit_zero(self):
        """--help → exit code 0."""
        rc, stdout, stderr = run_quickice("--help")
        assert rc == 0

    def test_help_shows_usage(self):
        """--help → full argparse help with all options."""
        rc, stdout, stderr = run_quickice("--help")
        assert "python -m quickice" in stdout
        assert "--temperature" in stdout

    def test_version_exit_zero(self):
        """--version → exit code 0."""
        rc, stdout, stderr = run_quickice("--version")
        assert rc == 0

    def test_version_shows_version(self):
        """--version → version string in stdout."""
        rc, stdout, stderr = run_quickice("--version")
        assert "4.5.0" in stdout


# ── --cli and pipeline flags → CLI mode ───────────────────────────────────────


class TestCLIMode:
    """--cli and pipeline flags trigger CLI mode."""

    def test_cli_alone_exits_error(self):
        """--cli alone → argparse error (required --temperature), exit 2."""
        rc, stdout, stderr = run_quickice("--cli")
        assert rc == 2
        assert "required" in stderr.lower() or "temperature" in stderr.lower()

    def test_cli_with_pipeline_flags(self):
        """--cli + pipeline flags → CLI mode, exit 0."""
        rc, stdout, stderr = run_quickice(
            "--cli", "-T", "250", "-P", "0.1", "-N", "96",
            "--no-diagram",
            timeout=60,
        )
        assert rc == 0
        assert "Temperature: 250.0K" in stdout

    def test_pipeline_flags_implicit_cli(self):
        """Pipeline flags without --cli → implicit CLI mode, exit 0."""
        rc, stdout, stderr = run_quickice(
            "-T", "250", "-P", "0.1", "-N", "96",
            "--no-diagram",
            timeout=60,
        )
        assert rc == 0
        assert "Temperature: 250.0K" in stdout


# ── --gui flag behavior ───────────────────────────────────────────────────────


class TestGUIMode:
    """--gui flag behavior (tested via direct function call, not subprocess).

    Mock-based tests cannot use subprocess (mocks don't propagate to child
    processes), so we call entry.main() directly with controlled argv.
    """

    def test_gui_missing_pyside6_error(self, capsys):
        """--gui + PySide6 missing → error message, exit 1."""
        from quickice.entry import main
        with unittest.mock.patch(
            'quickice.entry._is_pyside6_available', return_value=False
        ):
            rc = main(['quickice', '--gui'])
        assert rc == 1
        captured = capsys.readouterr()
        assert "PySide6 is not installed" in captured.err

    def test_gui_no_display_error(self, capsys):
        """--gui + no display available → error message, exit 1."""
        from quickice.entry import main
        with unittest.mock.patch(
            'quickice.entry._is_pyside6_available', return_value=True
        ):
            with unittest.mock.patch(
                'quickice.entry._has_display', return_value=False
            ):
                rc = main(['quickice', '--gui'])
        assert rc == 1
        captured = capsys.readouterr()
        assert "no display is available" in captured.err


# ── Backward compatibility ────────────────────────────────────────────────────


class TestBackwardCompat:
    """quickice.py backward compatibility."""

    def test_quickice_py_still_works(self):
        """python quickice.py with pipeline flags → CLI mode, exit 0."""
        cmd = [
            sys.executable, "quickice.py",
            "-T", "250", "-P", "0.1", "-N", "96",
            "--no-diagram",
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0
        assert "Temperature: 250.0K" in result.stdout
