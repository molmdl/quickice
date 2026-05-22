"""Test ITP parser edge cases: BOM, line endings, whitespace, missing comment.

Verifies that parse_itp_file() correctly handles:
- UTF-8 BOM (Byte Order Mark) prefix
- Windows line endings (\\r\\n)
- Old-style Mac line endings (\\r)
- Extra whitespace around [ moleculetype ] section
- Missing comment line between [ moleculetype ] and molecule name
"""

import tempfile
from pathlib import Path

import pytest

from quickice.structure_generation.itp_parser import ITPMoleculeInfo, parse_itp_file


# --- Canonical ITP content (no edge-case encoding) ---

CANONICAL_ITP = """\
; Standard ITP file for testing
[ moleculetype ]
; name          nrexcl
ch4       3

[ atoms ]
;  Index   type   residue  resname   atom         cgnr     charge       mass
     1     c3         1      CH4    C              1   -0.46   12.01
     2     hc         1      CH4    H              2    0.11    1.008
     3     hc         1      CH4    H              3    0.11    1.008
     4     hc         1      CH4    H              4    0.11    1.008
     5     hc         1      CH4    H              5    0.11    1.008
"""


def _write_and_parse(content: str) -> ITPMoleculeInfo:
    """Write ITP content to a temp file, parse it, and return the result."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".itp", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        tmp_path = Path(f.name)
    try:
        return parse_itp_file(tmp_path)
    finally:
        tmp_path.unlink()


class TestBOMHandling:
    """Tests for UTF-8 BOM (Byte Order Mark) handling."""

    def test_bom_prefix_still_parses(self):
        """ITP file with UTF-8 BOM should parse correctly.

        Some text editors (especially on Windows) save files with a BOM
        prefix (\\ufeff). The parser must strip it before regex matching.
        """
        content = "\ufeff" + CANONICAL_ITP
        info = _write_and_parse(content)

        assert info.molecule_name == "ch4"
        assert info.atom_count == 5
        assert info.atom_types == ["c3", "hc", "hc", "hc", "hc"]
        assert info.atom_names == ["C", "H", "H", "H", "H"]

    def test_bom_with_missing_comment_line(self):
        """BOM combined with missing comment line should still parse.

        Tests both BOM stripping AND the fallback regex (no comment line).
        """
        content = "\ufeff" + """\
[ moleculetype ]
ch4       3

[ atoms ]
;  Index   type   residue  resname   atom         cgnr     charge       mass
     1     c3         1      CH4    C              1   -0.46   12.01
     2     hc         1      CH4    H              2    0.11    1.008
     3     hc         1      CH4    H              3    0.11    1.008
     4     hc         1      CH4    H              4    0.11    1.008
     5     hc         1      CH4    H              5    0.11    1.008
"""
        info = _write_and_parse(content)
        assert info.molecule_name == "ch4"


class TestWindowsLineEndings:
    """Tests for Windows-style \\r\\n line endings."""

    def test_crlf_line_endings_parse(self):
        """ITP file with \\r\\n line endings should parse correctly.

        Windows-generated files commonly use CRLF. The parser normalizes
        these to \\n before regex matching.
        """
        content = CANONICAL_ITP.replace("\n", "\r\n")
        info = _write_and_parse(content)

        assert info.molecule_name == "ch4"
        assert info.atom_count == 5
        assert info.atom_names == ["C", "H", "H", "H", "H"]

    def test_crlf_with_extra_whitespace(self):
        """CRLF line endings combined with extra whitespace should parse."""
        content = """\
[  moleculetype  ]\r\n\
; name          nrexcl\r\n\
ch4       3\r\n\
\r\n\
[ atoms ]\r\n\
;  Index   type   residue  resname   atom         cgnr     charge       mass\r\n\
     1     c3         1      CH4    C              1   -0.46   12.01\r\n\
     2     hc         1      CH4    H              2    0.11    1.008\r\n\
     3     hc         1      CH4    H              3    0.11    1.008\r\n\
     4     hc         1      CH4    H              4    0.11    1.008\r\n\
     5     hc         1      CH4    H              5    0.11    1.008\r\n\
"""
        info = _write_and_parse(content)
        assert info.molecule_name == "ch4"
        assert info.atom_count == 5


class TestOldMacLineEndings:
    """Tests for old-style Mac \\r-only line endings."""

    def test_cr_only_line_endings_parse(self):
        """ITP file with \\r-only (classic Mac) line endings should parse.

        Very old Mac files use \\r instead of \\n or \\r\\n.
        The parser normalizes \\r -> \\n after handling \\r\\n first.
        """
        content = CANONICAL_ITP.replace("\n", "\r")
        info = _write_and_parse(content)

        assert info.molecule_name == "ch4"
        assert info.atom_count == 5
        assert info.atom_types == ["c3", "hc", "hc", "hc", "hc"]


class TestExtraWhitespaceAroundMoleculetype:
    """Tests for extra whitespace around [ moleculetype ] section header."""

    def test_extra_spaces_inside_brackets(self):
        """Extra spaces inside brackets like [  moleculetype  ] should parse."""
        content = """\
; ITP with extra whitespace
[  moleculetype  ]
; name          nrexcl
ch4       3

[ atoms ]
;  Index   type   residue  resname   atom         cgnr     charge       mass
     1     c3         1      CH4    C              1   -0.46   12.01
     2     hc         1      CH4    H              2    0.11    1.008
     3     hc         1      CH4    H              3    0.11    1.008
     4     hc         1      CH4    H              4    0.11    1.008
     5     hc         1      CH4    H              5    0.11    1.008
"""
        info = _write_and_parse(content)
        assert info.molecule_name == "ch4"
        assert info.atom_count == 5

    def test_leading_whitespace_on_section_line(self):
        """Leading whitespace before [ moleculetype ] should still parse."""
        content = """\
; ITP with leading whitespace on section line
  [ moleculetype ]
; name          nrexcl
ch4       3

[ atoms ]
;  Index   type   residue  resname   atom         cgnr     charge       mass
     1     c3         1      CH4    C              1   -0.46   12.01
     2     hc         1      CH4    H              2    0.11    1.008
     3     hc         1      CH4    H              3    0.11    1.008
     4     hc         1      CH4    H              4    0.11    1.008
     5     hc         1      CH4    H              5    0.11    1.008
"""
        info = _write_and_parse(content)
        assert info.molecule_name == "ch4"

    def test_extra_whitespace_on_molecule_name_line(self):
        """Molecule name with leading/trailing whitespace should parse.

        The regex captures (\\w+), so whitespace is excluded from the match.
        """
        content = """\
; ITP with extra whitespace on name line
[ moleculetype ]
; name          nrexcl
   ch4       3

[ atoms ]
;  Index   type   residue  resname   atom         cgnr     charge       mass
     1     c3         1      CH4    C              1   -0.46   12.01
     2     hc         1      CH4    H              2    0.11    1.008
     3     hc         1      CH4    H              3    0.11    1.008
     4     hc         1      CH4    H              4    0.11    1.008
     5     hc         1      CH4    H              5    0.11    1.008
"""
        info = _write_and_parse(content)
        assert info.molecule_name == "ch4"


class TestMissingCommentLine:
    """Tests for ITP files missing the comment line between [ moleculetype ] and name."""

    def test_no_comment_line_parses_via_fallback_regex(self):
        """ITP file without comment line between section and name should parse.

        The parser has a fallback regex that matches [ moleculetype ] followed
        directly by the molecule name (no comment line starting with ';').
        This pattern appears in some auto-generated ITP files.
        """
        content = """\
[ moleculetype ]
ch4       3

[ atoms ]
;  Index   type   residue  resname   atom         cgnr     charge       mass
     1     c3         1      CH4    C              1   -0.46   12.01
     2     hc         1      CH4    H              2    0.11    1.008
     3     hc         1      CH4    H              3    0.11    1.008
     4     hc         1      CH4    H              4    0.11    1.008
     5     hc         1      CH4    H              5    0.11    1.008
"""
        info = _write_and_parse(content)
        assert info.molecule_name == "ch4"
        assert info.atom_count == 5

    def test_no_comment_with_whitespace_indent(self):
        """No comment line with indented molecule name should parse."""
        content = """\
[ moleculetype ]
  ch4       3

[ atoms ]
;  Index   type   residue  resname   atom         cgnr     charge       mass
     1     c3         1      CH4    C              1   -0.46   12.01
     2     hc         1      CH4    H              2    0.11    1.008
     3     hc         1      CH4    H              3    0.11    1.008
     4     hc         1      CH4    H              4    0.11    1.008
     5     hc         1      CH4    H              5    0.11    1.008
"""
        info = _write_and_parse(content)
        assert info.molecule_name == "ch4"

    def test_different_molecule_name_without_comment(self):
        """Fallback regex should capture different molecule names (e.g., SOL)."""
        content = """\
[ moleculetype ]
SOL		2

[ atoms ]
; nr type resnr residu atom cgnr charge
  1   OW_ice  1       SOL       OW       1       0        15.994
  2   HW_ice  1       SOL       HW1      1       0.5897   1.008
  3   HW_ice  1       SOL       HW2      1       0.5897   1.008
  4   MW      1       SOL       MW       1      -1.1794   0.0
"""
        info = _write_and_parse(content)
        assert info.molecule_name == "SOL"
        assert info.atom_count == 4
        assert info.atom_names == ["OW", "HW1", "HW2", "MW"]


class TestCanonicalITP:
    """Baseline: canonical ITP file should parse correctly (regression guard)."""

    def test_canonical_ch4_itp(self):
        """Standard ITP with comment line should parse to expected values."""
        info = _write_and_parse(CANONICAL_ITP)

        assert isinstance(info, ITPMoleculeInfo)
        assert info.molecule_name == "ch4"
        assert info.atom_count == 5
        assert info.atom_types == ["c3", "hc", "hc", "hc", "hc"]
        assert info.atom_names == ["C", "H", "H", "H", "H"]
        assert info.has_atomtypes_section is False

    def test_real_ch4_itp_file(self):
        """Parse the actual ch4.itp data file bundled with QuickIce."""
        data_path = Path(__file__).resolve().parent.parent / "quickice" / "data" / "ch4.itp"
        if not data_path.exists():
            pytest.skip("ch4.itp data file not found")

        info = parse_itp_file(data_path)
        assert info.molecule_name == "ch4"
        assert info.atom_count == 5
        assert "C" in info.atom_names

    def test_real_tip4p_ice_itp_file(self):
        """Parse the actual tip4p-ice.itp data file bundled with QuickIce."""
        data_path = Path(__file__).resolve().parent.parent / "quickice" / "data" / "tip4p-ice.itp"
        if not data_path.exists():
            pytest.skip("tip4p-ice.itp data file not found")

        info = parse_itp_file(data_path)
        assert info.molecule_name == "SOL"
        assert info.atom_count == 4
        assert info.atom_names == ["OW", "HW1", "HW2", "MW"]
