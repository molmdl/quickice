"""Unit tests for the _stage_custom_guest_itp transformed-ITP staging helper.

Validates that staging a custom guest ITP (etoh.itp) via
``_stage_custom_guest_itp`` applies the FULL ``transform_guest_itp`` pipeline:

    comment_out_atomtypes_in_itp  →  rename moleculetype '{name}_H'
                                    →  rewrite [ atoms ] resname '{name}_H'

so the staged ITP is internally consistent with a ``.top [ molecules ] MOL_H``
entry — the prerequisite for ``gmx grompp`` to succeed on custom-guest hydrate
exports (plans 41-10 / 41-11).

These are pure-Python unit tests (no ``gmx`` dependency); they prove the
transform/overwrite contract that the grompp e2e tests rely on.
"""

import re
import sys
from pathlib import Path

import pytest

# Make the sibling e2e_export_helpers module importable (it is NOT a package).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from e2e_export_helpers import (  # noqa: E402
    ETOH_ITP,
    _stage_custom_guest_itp,
    _stage_itp_files,
)

# Absolute path to the custom ethanol guest ITP fixture.  Using the exported
# ETOH_ITP constant (rather than a cwd-relative path) keeps the tests robust
# regardless of pytest's invocation directory.
_ETOH_ITP = ETOH_ITP


def _moleculetype_name(text: str) -> str | None:
    """Return the [ moleculetype ] name declared in ``text``.

    Scans for the ``[ moleculetype ]`` header and returns the first non-comment,
    non-blank line's first whitespace token.  Returns ``None`` if absent.
    """
    in_molt = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_molt = "moleculetype" in stripped.lower()
            continue
        if in_molt and stripped and not stripped.startswith(";") and not stripped.startswith("#"):
            return stripped.split()[0]
    return None


def test_stages_transformed_mol_h(tmp_path):
    """Staged etoh.itp has moleculetype MOL_H, [atomtypes] commented, [atoms] resname MOL_H."""
    staged_name = _stage_custom_guest_itp(tmp_path, _ETOH_ITP, "MOL")

    # Returns the basename and writes it to the workspace.
    assert staged_name == "etoh.itp"
    staged_path = tmp_path / "etoh.itp"
    assert staged_path.exists()
    text = staged_path.read_text()

    # [ moleculetype ] name is now MOL_H.
    assert re.search(r"\[\s*moleculetype\s*\][\s\S]*?MOL_H\s+\d", text) is not None, (
        "Staged ITP [ moleculetype ] name should be 'MOL_H'"
    )

    # [ atoms ] block contains a data line whose resname column (4th
    # whitespace field, 0-based index 3) is MOL_H.
    assert re.search(r"(?m)^\s*\d+\s+\S+\s+\d+\s+MOL_H\s", text) is not None, (
        "Staged ITP [ atoms ] resname column should be 'MOL_H'"
    )

    # Original [ atomtypes ] header is commented out.
    assert "; [ atomtypes ]" in text, "Staged ITP should have [ atomtypes ] header commented"

    # No uncommented [ atomtypes ] header remains (the section was commented out).
    uncommented_atomtypes = [l for l in text.splitlines() if l.strip() == "[ atomtypes ]"]
    assert uncommented_atomtypes == [], (
        "Staged ITP must NOT contain an uncommented [ atomtypes ] header; "
        f"found: {uncommented_atomtypes}"
    )


def test_overwrites_under_transformed_copy(tmp_path):
    """Calling _stage_custom_guest_itp AFTER _stage_itp_files overwrites the
    under-transformed copy (moleculetype 'etoh') with the renamed one (MOL_H)."""
    # Stage via _stage_itp_files first: write a tiny .top whose only #include is
    # etoh.itp.  This stages etoh.itp with [atomtypes] commented but moleculetype
    # still 'etoh' (no _H rename).
    top_path = tmp_path / "x.top"
    top_path.write_text('#include "etoh.itp"\n')
    result = _stage_itp_files(str(top_path), tmp_path)
    assert result.staged == ["etoh.itp"], f"_stage_itp_files should stage etoh.itp; got {result}"
    assert (tmp_path / "etoh.itp").exists()

    # Under-transformed: moleculetype name is still 'etoh'.
    under_text = (tmp_path / "etoh.itp").read_text()
    assert _moleculetype_name(under_text) == "etoh", (
        "After _stage_itp_files the staged etoh.itp moleculetype should be 'etoh' "
        "(under-transformed, no _H rename)"
    )

    # Now overwrite with the fully-transformed copy.
    _stage_custom_guest_itp(tmp_path, _ETOH_ITP, "MOL")

    # Overwritten: moleculetype name is now 'MOL_H'.
    over_text = (tmp_path / "etoh.itp").read_text()
    assert _moleculetype_name(over_text) == "MOL_H", (
        "After _stage_custom_guest_itp the overwritten etoh.itp moleculetype "
        "should be 'MOL_H'"
    )


def test_name_too_long_raises(tmp_path):
    """A base name that pushes '{name}_H' over the 5-char GRO limit raises ValueError."""
    # 'ETHAN' (5) + '_H' = 'ETHAN_H' (7 chars) > 5 → transform_guest_itp validates
    # and raises ValueError.
    with pytest.raises(ValueError):
        _stage_custom_guest_itp(tmp_path, _ETOH_ITP, "ETHAN")
