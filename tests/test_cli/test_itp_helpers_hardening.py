"""Unit hardening tests for the 48.4 ITP-staging catch narrowing.

48.4 hardening (audit Finding 1, Level-1 correctness): the four broad
``except Exception`` warn-and-skip sites in ``quickice/cli/itp_helpers.py``
are narrowed to ``except (OSError, ValueError) as e: logger.error(...); raise``
so a required ITP staging failure propagates as the original typed exception
into ``_run_export_step``'s existing ``except (OSError, ValueError)`` catch
(``pipeline.py:1006``) -> rc=1 with ``[PROGRESS] Export step failed:`` on
stderr, instead of a silent partial export with rc=0.

The four sites pinned here:
  1. ``copy_itp_files_for_structure`` step 1 (tip4p) — logistics failure of the
     ALWAYS-required ``tip4p-ice.itp`` staging now raises (pre-fix: warned and
     returned ``[]``).
  2. ``_copy_hydrate_guest_itp`` second catch — a transform/IO failure (e.g.
     ``transform_guest_itp`` raising ``ValueError``) now raises (pre-fix:
     returned ``None``). The sibling FIRST catch (``FileNotFoundError`` ->
     warn + ``None`` for a missing bundled source) is intentionally preserved
     and pinned by ``test_hydrate_guest_missing_source_still_returns_none``.
  3. ``_copy_itp_with_atomtypes_commented`` — a malformed/undecodable ITP
     raises ``UnicodeDecodeError`` (⊂ ``ValueError``, so the narrow catch
     still catches it, logs, and re-raises) instead of warn-and-``None``.
  4. ``copy_itp_files_for_structure`` ion branch — ``write_ion_itp`` failure
     now raises (pre-fix: warned, ``ion.itp`` skipped silently).

``copy_custom_guest_itp``'s return-``None`` contract is intentionally NOT
re-contracted (3 pinned tests in ``test_itp_helpers_custom_guest.py``); the
audit scenario it covers is closed at the transaction level by the
``_run_export_step`` #include reconciliation (plan 48.4-01 Task 2).

Monkeypatching note: all four symbols resolve through the CALL-SITE module
namespace ``quickice.cli.itp_helpers.<name>`` for ``get_tip4p_itp_path`` /
``get_hydrate_guest_itp_path``, and through the SOURCE module
(``quickice.output.gromacs_writer.transform_guest_itp``,
``quickice.structure_generation.gromacs_ion_export.write_ion_itp``) for the
two helpers that do function-local imports at call time.

Pure pytest — no ``gmx``, no GenIce2, no Qt.
"""

from types import SimpleNamespace

import pytest

from quickice.cli.itp_helpers import (
    _copy_hydrate_guest_itp,
    _copy_itp_with_atomtypes_commented,
    copy_itp_files_for_structure,
)


def test_tip4p_staging_failure_raises_through(monkeypatch, tmp_path):
    """tip4p-ice.itp staging failure raises the typed exception (site :317).

    Pre-fix the ``except Exception`` at itp_helpers.py:317 warned and the
    function returned ``[]`` even though every .top #includes tip4p-ice.itp
    — a guaranteed-broken export. Post-fix the original ``OSError``
    (``FileNotFoundError`` ⊂ ``OSError``) propagates.
    """
    def _missing_tip4p():
        raise FileNotFoundError("no bundled tip4p-ice.itp")

    monkeypatch.setattr(
        "quickice.cli.itp_helpers.get_tip4p_itp_path", _missing_tip4p
    )

    with pytest.raises(OSError):
        copy_itp_files_for_structure(tmp_path, SimpleNamespace(), "ice")


def test_hydrate_guest_itp_transform_failure_raises(monkeypatch, tmp_path):
    """Hydrate guest ITP transform failure raises (site :196-198).

    Pre-fix the ``except Exception`` at itp_helpers.py:196 warned and returned
    ``None``; the caller's ``if itp_name:`` then silently skipped the required
    ``{guest}_hydrate.itp``. Post-fix the ``ValueError`` from
    ``transform_guest_itp`` propagates. The helper does a function-local
    ``from quickice.output.gromacs_writer import transform_guest_itp``, so the
    patch targets the SOURCE module attribute (resolved at call time).
    """
    def _boom(content, name, suffix="_H"):
        raise ValueError("boom")

    monkeypatch.setattr(
        "quickice.output.gromacs_writer.transform_guest_itp", _boom
    )

    with pytest.raises(ValueError):
        # "ch4" has a real bundled ch4_hydrate.itp source — the failure is
        # injected purely at the transform step, not at source resolution.
        _copy_hydrate_guest_itp(tmp_path, "ch4")


def test_atomtypes_commented_undecodable_itp_raises(tmp_path):
    """A malformed/undecodable ITP raises UnicodeDecodeError (site :162-164).

    This pins the audit's literal 'malformed user-supplied ITP' scenario AND
    the ``UnicodeDecodeError`` ⊂ ``ValueError`` subset relation: the narrow
    ``except (OSError, ValueError)`` must still catch the decode error (log at
    error level) and then RE-RAISE it, not warn-and-return-``None``. Pre-fix
    this returned ``None`` and nothing surfaced.
    """
    src = tmp_path / "bad.itp"
    src.write_bytes(b"\xff\xfe not-utf8 \x80\x81")
    dest = tmp_path / "bad.itp.staged.itp"

    with pytest.raises(UnicodeDecodeError):
        _copy_itp_with_atomtypes_commented(src, dest)

    # Nothing was written to the destination on failure.
    assert not dest.exists(), (
        f"destination {dest} must not be written when the source is undecodable"
    )


def test_ion_itp_write_failure_raises_through(monkeypatch, tmp_path):
    """ion.itp generation failure raises (site :528-529).

    Pre-fix the ``except Exception`` at itp_helpers.py:528 warned and the
    export proceeded WITHOUT the required ion.itp (the .top #includes it when
    na/cl > 0). Post-fix the ``OSError`` from ``write_ion_itp`` propagates.
    The ion branch does a function-local
    ``from quickice.structure_generation.gromacs_ion_export import
    write_ion_itp``, so the patch targets the SOURCE module attribute. The
    structure passes the :524 count gate (na=1, cl=1); the tip4p step-1 runs
    first UNPATCHED (real bundled source) so the ion branch is reached.
    """
    def _boom(path, na, cl):
        raise OSError("disk full")

    monkeypatch.setattr(
        "quickice.structure_generation.gromacs_ion_export.write_ion_itp", _boom
    )

    structure = SimpleNamespace(na_count=1, cl_count=1)
    with pytest.raises(OSError):
        copy_itp_files_for_structure(tmp_path, structure, "ion")


def test_hydrate_guest_missing_source_still_returns_none(monkeypatch, tmp_path):
    """PIN of the preserved first catch at :193-195 — missing bundled source.

    The ``except FileNotFoundError`` -> warn + ``return None`` contract for a
    MISSING bundled hydrate guest ITP is intentionally untouched by the 48.4
    hardening (only the SECOND catch was narrowed). This test passes pre- and
    post-fix — a regression guard against over-narrowing.
    """
    def _missing_guest(guest_type):
        raise FileNotFoundError(f"no bundled ITP for {guest_type}")

    monkeypatch.setattr(
        "quickice.cli.itp_helpers.get_hydrate_guest_itp_path", _missing_guest
    )

    result = _copy_hydrate_guest_itp(tmp_path, "ch4")
    assert result is None, (
        "Missing bundled hydrate guest ITP source must still return None "
        "(preserved first catch), not raise"
    )
