"""Unit tests for `_merge_custom_atomtypes` helper in quickice.output.gromacs_writer.

Tests verify the four contract behaviors:
  1. New atomtypes (not already in *written*) are written and recorded.
  2. Atomtypes already in *written* with MATCHING LJ params are silently deduped
     (not re-written, no ValueError).
  3. Atomtypes already in *written* with DIFFERENT LJ params raise ValueError
     ("different LJ" in the message).
  4. An ITP with no [ atomtypes ] section is a no-op (nothing written, nothing
     mutated).

Plus a real-fixture integration test using quickice/data/custom/etoh.itp that
dedups the GAFF2 atomtypes (hc, c3, h1) and writes the ethanol-only ones (oh, ho).
"""

import io
from pathlib import Path

import pytest

from quickice.output.gromacs_writer import (
    GAFF2_ATOMTYPES,
    _merge_custom_atomtypes,
    parse_itp_atomtypes,
)


# Real fixture (cwd-independent absolute path).
_ETOH_ITP = Path(__file__).parent.parent / "quickice" / "data" / "custom" / "etoh.itp"


def _write_temp_itp(path: Path, body: str) -> Path:
    """Write *body* to *path* and return it (small helper to keep tests DRY)."""
    path.write_text(body)
    return path


# ---------------------------------------------------------------------------
# 1. New atomtypes are written and recorded
# ---------------------------------------------------------------------------
def test_writes_new_atomtypes(tmp_path):
    """An ITP with oh/ho atomtypes is fully merged into an empty *written* dict."""
    itp = _write_temp_itp(
        tmp_path / "new.itp",
        "[ atomtypes ]\n"
        "; name   at.num      mass       charge   ptype     sigma (nm)    epsilon (kJ/mol)\n"
        "oh           8    15.999405    0.000000    A      3.242871E-01    3.891120E-01\n"
        "ho           1     1.007941    0.000000    A      5.379246E-02    1.966480E-02\n",
    )

    f = io.StringIO()
    written = {}

    _merge_custom_atomtypes(f, str(itp), written, "test")

    lines = f.getvalue().splitlines()
    assert any(line.startswith("oh") for line in lines), (
        f"expected an 'oh' atomtype line, got {lines!r}"
    )
    assert any(line.startswith("ho") for line in lines), (
        f"expected an 'ho' atomtype line, got {lines!r}"
    )
    assert "oh" in written, f"oh not recorded in written={written!r}"
    assert "ho" in written, f"ho not recorded in written={written!r}"


# ---------------------------------------------------------------------------
# 2. Dedup when LJ params match (within rtol=1e-4)
# ---------------------------------------------------------------------------
def test_dedup_when_params_match(tmp_path):
    """An atomtype whose LJ params already match an entry in *written* is skipped."""
    # Pre-seed hc with GAFF2-matching sigma/epsilon.
    written = {"hc": ("hc", 1, 1.0079, 0.0, "A", 2.60018e-01, 8.70272e-02)}
    itp = _write_temp_itp(
        tmp_path / "dup.itp",
        "[ atomtypes ]\n"
        "; name   at.num      mass       charge   ptype     sigma (nm)    epsilon (kJ/mol)\n"
        "hc           1     1.007941    0.000000    A      2.600177E-01    8.702720E-02\n",
    )

    f = io.StringIO()

    # Must not raise — params match within rtol=1e-4.
    _merge_custom_atomtypes(f, str(itp), written, "test")

    lines = f.getvalue().splitlines()
    # The comment header "; test" is written because parse returns a non-empty list,
    # but no hc atomtype line should be re-emitted.
    assert not any(line.startswith("hc") for line in lines), (
        f"dedup should suppress the hc atomtype line, got {lines!r}"
    )


# ---------------------------------------------------------------------------
# 3. Conflict raises ValueError on LJ mismatch
# ---------------------------------------------------------------------------
def test_conflict_raises_on_lj_mismatch(tmp_path):
    """An atomtype already in *written* with different LJ params raises ValueError."""
    written = {"hc": ("hc", 1, 12.011, 0.0, "A", 2.60018e-01, 6.5689e-02)}
    itp = _write_temp_itp(
        tmp_path / "conflict.itp",
        "[ atomtypes ]\n"
        "; name   at.num      mass       charge   ptype     sigma (nm)    epsilon (kJ/mol)\n"
        "hc           1     1.007941    0.000000    A      2.600177E-01    9.999E-01\n",
    )

    f = io.StringIO()
    with pytest.raises(ValueError, match="different LJ"):
        _merge_custom_atomtypes(f, str(itp), written, "test")


# ---------------------------------------------------------------------------
# 4. No [ atomtypes ] section is a no-op
# ---------------------------------------------------------------------------
def test_no_atomtypes_section_is_noop(tmp_path):
    """An ITP lacking an [ atomtypes ] section writes nothing and mutates nothing."""
    itp = _write_temp_itp(
        tmp_path / "no_atomtypes.itp",
        "[ moleculetype ]\n"
        "; name          nrexcl\n"
        "mol         3\n"
        "\n"
        "[ atoms ]\n"
        ";  Index   type   residue  resname   atom   cgnr   charge   mass\n"
        "     1     hc         1      MOL     H        1   0.0577   1.0079\n",
    )

    f = io.StringIO()
    written = {"hc": ("hc", 1, 1.0079, 0.0, "A", 2.6e-01, 8.7e-02)}

    _merge_custom_atomtypes(f, str(itp), written, "test")

    assert f.getvalue() == "", (
        f"no-op should write nothing, got {f.getvalue()!r}"
    )
    assert written == {"hc": ("hc", 1, 1.0079, 0.0, "A", 2.6e-01, 8.7e-02)}, (
        f"no-op should not mutate written, got {written!r}"
    )


# ---------------------------------------------------------------------------
# 5. Real etoh.itp integration: dedup GAFF2 types, write ethanol-only types
# ---------------------------------------------------------------------------
def test_real_etoh_itp_merges_oh_ho_only():
    """The real etoh.itp dedups hc/c3/h1 (matching GAFF2) and writes oh/ho."""
    assert _ETOH_ITP.exists(), f"etoh.itp fixture not found at {_ETOH_ITP}"

    # Pre-seed with the GAFF2 types that etoh.itp shares (matching LJ params).
    written = {name: GAFF2_ATOMTYPES[name] for name in ("hc", "c3", "h1")}

    f = io.StringIO()
    _merge_custom_atomtypes(f, str(_ETOH_ITP), written, "custom guest etoh atom types")

    lines = f.getvalue().splitlines()

    # oh and ho are ethanol-specific (NOT in GAFF2_ATOMTYPES) → must be written.
    assert any(line.startswith("oh") for line in lines), (
        f"expected an 'oh' atomtype line, got {lines!r}"
    )
    assert any(line.startswith("ho") for line in lines), (
        f"expected an 'ho' atomtype line, got {lines!r}"
    )

    # hc/c3/h1 already in written with matching LJ → deduped, not re-written.
    for name in ("hc", "c3", "h1"):
        assert not any(line.startswith(name) for line in lines), (
            f"{name} should be deduped (not re-written), got {lines!r}"
        )

    # written should now also contain the ethanol-only types.
    assert "oh" in written, f"oh not recorded in written={written!r}"
    assert "ho" in written, f"ho not recorded in written={written!r}"
