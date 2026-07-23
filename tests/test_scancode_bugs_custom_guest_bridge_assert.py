"""Regression test for scancode issue F5 / TCG3: bare ``assert`` stripped by -O.

``quickice/structure_generation/custom_guest_bridge.py`` used a bare
``assert key not in sys.modules, ...`` as the stale-state guard inside the
``custom_guest_module`` context manager. Under ``python -O`` (or
``PYTHONOPTIMIZE=1``) bare ``assert`` statements are STRIPPED, silently
disabling the guard — a stale ``sys.modules`` entry would then be silently
overwritten instead of raising. This is the same class of defect as the
CRIT-04 assert already converted in ``cli/pipeline.py``.

The fix converts the ``assert`` to an explicit
``if key in sys.modules: raise RuntimeError(...)`` so the guard survives
optimization. ``import logging`` and the module ``logger`` already existed
(used just below at the ``logger.debug("Registered ...")`` line), so no
import change was needed.

Tests:
  * ``test_stale_state_raises_runtime_error_not_assertion_error`` — the
    required core: pre-register the key in ``sys.modules`` and enter the
    context manager; it must raise ``RuntimeError`` (not ``AssertionError``).
  * ``test_raise_survives_python_optimize`` — runs the same scenario in a
    subprocess with ``PYTHONOPTIMIZE=1`` to prove the ``raise`` is NOT
    stripped (closes TCG3). With the old bare ``assert``, this subprocess
    would NOT raise and would exit with the "no exception" sentinel; with
    the fix it raises ``RuntimeError`` and exits 0.
"""

import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

from quickice.structure_generation.custom_guest_bridge import custom_guest_module

# Project root (tests/ -> project root) so the -O subprocess can import quickice.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _cleanup_stale_keys(prefix: str = "genice2.molecules.etoh_stale") -> None:
    """Remove any stale custom-guest keys leaked into sys.modules by a test."""
    for k in [k for k in list(sys.modules) if k.startswith(prefix)]:
        sys.modules.pop(k, None)


def test_stale_state_raises_runtime_error_not_assertion_error():
    """Pre-registering the key makes custom_guest_module raise RuntimeError.

    This is the exact stale-state guard that used to be a bare ``assert``.
    It must now raise ``RuntimeError`` (the converted form), and crucially
    must NOT raise ``AssertionError`` (the old form, which would also be
    stripped under ``python -O``).
    """
    guest_type = "etoh_stale_runtime"
    key = f"genice2.molecules.{guest_type}"
    _cleanup_stale_keys()
    # Pre-register a stale entry — the guard must catch this.
    sys.modules[key] = types.ModuleType("stale_dummy")
    try:
        with pytest.raises(RuntimeError, match="already registered"):
            with custom_guest_module(guest_type, types.ModuleType("dummy")):
                pass
    finally:
        _cleanup_stale_keys()


def test_raise_survives_python_optimize():
    """The RuntimeError is NOT stripped under PYTHONOPTIMIZE=1 (closes TCG3).

    Runs the stale-state scenario in a subprocess with optimization enabled.
    With the old bare ``assert``, -O would strip it → no exception → the
    subprocess prints the "no exception" sentinel and exits 2. With the fix
    (explicit ``raise RuntimeError``), the raise survives → subprocess
    catches RuntimeError and exits 0.
    """
    guest_type = "etoh_stale_opt"
    key = f"genice2.molecules.{guest_type}"
    script = (
        "import sys, types\n"
        f"from quickice.structure_generation.custom_guest_bridge import custom_guest_module\n"
        f"key = {key!r}\n"
        "sys.modules[key] = types.ModuleType('stale_dummy')\n"
        "try:\n"
        f"    with custom_guest_module({guest_type!r}, types.ModuleType('dummy')):\n"
        "        pass\n"
        "except RuntimeError as e:\n"
        "    print('RuntimeError raised:', e)\n"
        "    sys.exit(0)\n"
        "except AssertionError as e:\n"
        "    print('FAIL: AssertionError (assert not stripped under -O?)', e)\n"
        "    sys.exit(1)\n"
        "print('FAIL: no exception raised (guard stripped under -O)')\n"
        "sys.exit(2)\n"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PROJECT_ROOT) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    env["PYTHONOPTIMIZE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Also clean up any key the subprocess may have left (it shouldn't, but be safe).
    _cleanup_stale_keys()
    assert result.returncode == 0, (
        f"subprocess (python -O) did not raise RuntimeError; "
        f"returncode={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "RuntimeError raised" in result.stdout, (
        f"expected RuntimeError confirmation on stdout; got:\n{result.stdout}\n{result.stderr}"
    )


if __name__ == "__main__":
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.main([__file__, "-v"])
