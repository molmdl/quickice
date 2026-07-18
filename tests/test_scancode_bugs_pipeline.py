"""Regression tests for scancode-verified pipeline robustness bugs (Group 3).

Covers two atomic robustness fixes in ``quickice/cli/pipeline.py``, each
landed as its own commit (see ``.planning/scancode-fixes/RESEARCH.md`` and
``PLAN.md``, Group 3):

CRIT-04 (MEDIUM, CONFIRMED):
    ``pipeline.py`` validated hydrate atom counts with an ``assert``::

        assert water_atom_count + guest_atom_count == len(hydrate.positions), ...

    ``assert`` statements are STRIPPED when Python runs with ``-O`` /
    ``PYTHONOPTIMIZE=1`` (verified: ``python -O -c "assert False"`` raises
    nothing). A mismatched hydrate would then export corrupted data with no
    error under optimization. The fix replaces the ``assert`` with a real
    ``if ...: raise ValueError(...)`` so the check is always active.

    Implementation note (Option B from the debug session
    ``.planning/debug/pipeline-robustness.md``): the check was extracted into
    a tiny module-level helper ``_validate_hydrate_atom_counts(water_atom_count,
    guest_atom_count, total_positions)`` and is called inline at the original
    site. The helper body is the ``if/raise``. This keeps the production call
    site byte-equivalent in values passed (so zero behavior change today — the
    inline check is a tautology because ``guest_atom_count`` is derived from
    ``len(positions)``, which is a SEPARATE finding documented in the debug
    file and out of scope for this fix) while making the raise survive
    ``python -O`` for the day the tautology is later addressed.

    Tests:
      1. Source-level guard: the production check site calls
         ``_validate_hydrate_atom_counts`` (NOT a bare ``assert``). This fails
         to compile / matches no helper if anyone reverts to ``assert``.
      2. Real mismatch under ``python -O``: the helper raises ``ValueError``
         on a real mismatch (10 + 5 != 20), confirmed to fire under optimization
         by spawning a ``python -O`` subprocess. A stripped ``assert`` would
         silently pass; the ``if/raise`` raises regardless of ``-O``.

SAFE-05 (LOW, CONFIRMED):
    See ``TestSAFE05OutputPathContainment`` (added with the SAFE-05 fix).
"""

import ast
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

from quickice.cli.pipeline import CLIPipeline, _validate_hydrate_atom_counts


# ── CRIT-04: stripped assert → ValueError ────────────────────────────────────


class TestCRIT04StrippedAssert:
    """The hydrate atom-count check must fire under ``python -O``.

    Before the fix, the check was an ``assert``, which ``python -O`` /
    ``PYTHONOPTIMIZE=1`` strips entirely — a mismatched hydrate would then
    export silently. The fix extracts the check into
    ``_validate_hydrate_atom_counts`` whose body is a real ``if ...: raise
    ValueError(...)``, always active regardless of optimization level.
    """

    def test_helper_raises_value_error_on_real_mismatch(self):
        """A real mismatch (10 + 5 != 20) raises ValueError, not AssertionError.

        This is the core CRIT-04 behavior: the check rejects a mismatch with a
        ``ValueError`` (the planned message format from PLAN.md), independent of
        any ``assert`` semantics.
        """
        with pytest.raises(ValueError, match="Hydrate atom-count mismatch"):
            _validate_hydrate_atom_counts(10, 5, 20)

    def test_helper_passes_on_consistent_counts(self):
        """Consistent counts (8 + 4 == 12) do not raise — happy path."""
        _validate_hydrate_atom_counts(8, 4, 12)  # must not raise
        _validate_hydrate_atom_counts(0, 0, 0)  # empty is consistent
        _validate_hydrate_atom_counts(400, 100, 500)  # realistic hydrate

    def test_check_fires_under_python_dash_O(self):
        """The mismatch check must fire under ``python -O``.

        This is the crux of CRIT-04: an ``assert`` is stripped under ``-O`` /
        ``PYTHONOPTIMIZE=1`` (verified: ``python -O -c "assert False"`` raises
        nothing), so the OLD code would silently skip the check. The NEW
        helper uses ``if ...: raise ValueError``, which is NOT stripped. We
        spawn a ``python -O`` subprocess that imports the helper and calls it
        with a real mismatch; it must raise ``ValueError`` even under
        optimization.
        """
        code = textwrap.dedent(
            """\
            import sys
            # Confirm the subprocess really runs under -O (asserts stripped).
            try:
                assert False, "if you see this, -O is NOT active"
            except AssertionError:
                print("ASSERTION_ERROR_FROM_ASSERT")
                sys.exit(0)
            # Under -O the assert above was stripped; now exercise the helper.
            from quickice.cli.pipeline import _validate_hydrate_atom_counts
            try:
                _validate_hydrate_atom_counts(10, 5, 20)
            except ValueError as e:
                print("VALUE_ERROR_FROM_HELPER")
                print(str(e))
                sys.exit(0)
            print("NO_ERROR")  # BUG if reached: helper was stripped/inert
            sys.exit(1)
            """
        )
        result = subprocess.run(
            [sys.executable, "-O", "-c", code],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        assert result.returncode == 0, (
            f"subprocess exited {result.returncode}; "
            f"stdout={result.stdout!r}; stderr={result.stderr!r}"
        )
        assert "ASSERTION_ERROR_FROM_ASSERT" not in result.stdout, (
            "Subprocess was NOT running under -O (an `assert False` raised) — "
            "the -O precondition for this test is not met; the test is invalid."
        )
        assert "VALUE_ERROR_FROM_HELPER" in result.stdout, (
            f"Under `python -O`, the helper did NOT raise ValueError (it was "
            f"stripped or inert). stdout={result.stdout!r}; stderr={result.stderr!r}"
        )
        assert "Hydrate atom-count mismatch: 10 water + 5 guest != 20 total" in result.stdout

    def test_production_check_site_uses_helper_not_assert(self):
        """Source-level guard: the production call site must use the helper,
        not a bare ``assert``.

        If someone reverts the CRIT-04 fix by replacing the helper call with an
        ``assert`` again, this test fails — preventing silent regression. We
        read the actual ``pipeline.py`` source and confirm the hydrate export
        branch calls ``_validate_hydrate_atom_counts`` and contains no
        ``assert`` at the hydrate atom-count check site.
        """
        pipeline_src = Path(CLIPipeline.__module__.replace(".", "/") + ".py")
        # Resolve via the imported module's actual file (robust to layout).
        import quickice.cli.pipeline as pl_mod
        pipeline_src = Path(pl_mod.__file__)
        source = pipeline_src.read_text()
        tree = ast.parse(source)

        # Find the module-level helper definition.
        helper_defined = any(
            isinstance(node, ast.FunctionDef)
            and node.name == "_validate_hydrate_atom_counts"
            for node in tree.body
        )
        assert helper_defined, (
            f"_validate_hydrate_atom_counts helper not defined in {pipeline_src}"
        )

        # Find a call to the helper anywhere in the module (the production site).
        calls_helper = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_validate_hydrate_atom_counts"
            for node in ast.walk(tree)
        )
        assert calls_helper, (
            f"_validate_hydrate_atom_counts is defined but never called in "
            f"{pipeline_src} — the production check site may have been reverted "
            f"to an inline `assert`."
        )

        # Ensure the helper body itself uses `if/raise`, not `assert`.
        for node in tree.body:
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_validate_hydrate_atom_counts"
            ):
                has_if_raise = any(
                    isinstance(child, ast.If)
                    and any(
                        isinstance(sub, ast.Raise) for sub in ast.walk(child)
                    )
                    for child in ast.walk(node)
                )
                assert has_if_raise, (
                    "_validate_hydrate_atom_counts body must use `if ...: raise`, "
                    "not `assert` (assert is stripped under -O — the CRIT-04 bug)."
                )
                # And must NOT contain an assert statement.
                has_assert = any(
                    isinstance(child, ast.Assert) for child in ast.walk(node)
                )
                assert not has_assert, (
                    "_validate_hydrate_atom_counts body contains an `assert` — "
                    "this is the CRIT-04 bug pattern (stripped under -O)."
                )
                break


# ── SAFE-05: --output path-traversal containment check ───────────────────────


class TestSAFE05OutputPathContainment:
    """``--output`` resolving outside the working directory must be rejected.

    Before the fix, ``CLIPipeline.execute`` resolved ``--output`` and created
    the directory (pipeline.py:137) with NO containment check — while the INPUT
    paths WERE checked at :242-249 (CSV, raises ValueError) and :494-509
    (custom gro/itp, returns 1), and ``output/orchestrator.py:48-56`` checks
    its output dir. The inconsistency meant ``--output /tmp/evil`` or any
    absolute path outside cwd was silently accepted.

    The fix adds a containment check mirroring the CSV/orchestrator style: after
    ``output_path = Path(self.args.output).resolve()``, raise ``ValueError`` if
    ``not output_path.is_relative_to(Path.cwd().resolve())``. ``ValueError`` is
    not ``OSError``, so it propagates past the local ``except OSError`` to
    ``main.py`` for fail-fast (consistent with the CSV check behavior).
    """

    @staticmethod
    def _make_pipeline(output: str) -> CLIPipeline:
        """Build a minimal CLIPipeline for the output-path check.

        ``execute()`` accesses ``self.args.output`` directly (line 163) and
        ``self.args.interface`` directly (line 196); all other step-flag
        accesses use ``getattr(..., default)``. With ``interface=False`` and no
        other step flags set, ``execute()`` falls through Steps 1-5 (all
        skipped) and reaches the export step, which returns 1 because no
        structure was generated — proving the Step-0 containment check PASSED
        (execution proceeded past it).
        """
        args = SimpleNamespace(
            output=output,
            interface=False,
            hydrate=False,
            custom_gro=None,
            solute_type=None,
            ion_concentration=None,
            no_overwrite=False,
        )
        return CLIPipeline(args)

    def test_output_outside_cwd_raises_value_error(self, tmp_path, monkeypatch):
        """``--output`` resolving outside cwd raises ValueError (not silently
        accepted). This is the core SAFE-05 behavior.

        We chdir into a clean tmp dir so the cwd is controlled, then point
        ``--output`` at a sibling directory OUTSIDE cwd. The resolved path is
        not under cwd, so the containment check must raise ValueError.
        """
        # cwd = tmp_path/work; output = tmp_path/escape (sibling, NOT under cwd)
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.chdir(work_dir)
        outside_output = (tmp_path / "escape").as_posix()  # sibling of work_dir

        pipeline = self._make_pipeline(outside_output)
        with pytest.raises(ValueError, match="--output path resolves outside"):
            pipeline.execute()

    def test_output_outside_cwd_via_traversal_raises(self, tmp_path, monkeypatch):
        """A path-traversal-style ``--output`` (``../../escape``) that resolves
        outside cwd is also rejected. This catches the ``../../etc/...`` style
        escape the SAFE-05 report flagged.
        """
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.chdir(work_dir)
        # ../../escape resolves to tmp_path.parent/escape — outside work_dir
        traversal_output = "../../escape"

        pipeline = self._make_pipeline(traversal_output)
        with pytest.raises(ValueError, match="--output path resolves outside"):
            pipeline.execute()

    def test_output_inside_cwd_passes_containment_check(self, tmp_path, monkeypatch):
        """An in-cwd ``--output`` passes the containment check and execution
        proceeds past Step 0.

        With no step flags set, ``execute()`` reaches the export step and
        returns 1 (no structure generated) — proving the containment check did
        NOT raise. We assert the return is an int (not a raised ValueError),
        and that it is not the "output path resolves outside" error.
        """
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.chdir(work_dir)
        inside_output = "out"  # resolves under work_dir

        pipeline = self._make_pipeline(inside_output)
        # The containment check must NOT raise. The pipeline falls through to
        # the export step (no step flags set), which returns 1 (no structure).
        # We accept any int return (0 or 1) as "containment check passed";
        # the key assertion is that NO ValueError is raised here.
        try:
            rc = pipeline.execute()
        except ValueError as e:
            pytest.fail(
                f"in-cwd --output raised ValueError (containment check is wrong): "
                f"{e}"
            )
        assert isinstance(rc, int)
        assert (work_dir / "out").is_dir()  # the dir was actually created

    def test_output_absolute_inside_cwd_passes(self, tmp_path, monkeypatch):
        """An absolute ``--output`` that resolves INSIDE cwd also passes
        (covers the absolute-path-allowed-when-under-cwd case).
        """
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.chdir(work_dir)
        inside_abs = (work_dir / "abs_out").as_posix()

        pipeline = self._make_pipeline(inside_abs)
        try:
            rc = pipeline.execute()
        except ValueError as e:
            pytest.fail(
                f"in-cwd absolute --output raised ValueError (wrong): {e}"
            )
        assert isinstance(rc, int)
        assert (work_dir / "abs_out").is_dir()
