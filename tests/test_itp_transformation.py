"""Tests for ITP transformation pipeline.

Validates that transform_guest_itp() correctly:
1. Comments out [ atomtypes ] section
2. Appends suffix to moleculetype name (e.g., CH4 → CH4_H)
3. Preserves nrexcl and other content
4. Raises ValueError for overlong names
5. Works with custom suffixes (_L for liquid solutes)
"""

import pytest

from quickice.output.gromacs_writer import (
    comment_out_atomtypes_in_itp,
    transform_guest_itp,
)


# ---------------------------------------------------------------------------
# Sample ITP content fixtures
# ---------------------------------------------------------------------------

CH4_ITP = """\
[ atomtypes ]
; name  at.num  mass       charge   ptype  sigma (nm)    epsilon (kJ/mol)
c3           6    12.010736    0.000000    A      3.397710E-01    4.510352E-01
hc           1     1.007941    0.000000    A      2.600177E-01    8.702720E-02

[ moleculetype ]
; name          nrexcl
CH4           3

[ atoms ]
;  Index   type   residue  resname   atom         cgnr     charge       mass
     1     c3         1      CH4    C              1   -0.46580968   12.010736
     2     hc         1      CH4    H              2    0.11645242    1.007941
"""

THF_ITP = """\
[ atomtypes ]
; name  at.num  mass       charge   ptype  sigma (nm)    epsilon (kJ/mol)
os           8    15.999405    0.000000    A      3.156098E-01    3.037584E-01

[ moleculetype ]
; Name          nrexcl
THF           3

[ atoms ]
     1     os         1      THF    O              1   -0.46306291   15.999405
"""

ITP_NO_ATOMTYPES = """\
[ moleculetype ]
; name          nrexcl
CH4           3

[ atoms ]
     1     c3         1      CH4    C              1   -0.46580968   12.010736
"""

ITP_NO_MOLECULETYPE = """\
[ atomtypes ]
c3           6    12.010736    0.000000    A      3.397710E-01    4.510352E-01

[ atoms ]
     1     c3         1      CH4    C              1   -0.46580968   12.010736
"""

# A realistic untransformed ITP with atomtypes NOT commented out
UNTRANSFORMED_ITP = """\
[ atomtypes ]
; name  at.num  mass       charge   ptype  sigma (nm)    epsilon (kJ/mol)
c3           6    12.010736    0.000000    A      3.397710E-01    4.510352E-01
hc           1     1.007941    0.000000    A      2.600177E-01    8.702720E-02

[ moleculetype ]
; name          nrexcl
CH4           3

[ atoms ]
;  Index   type   residue  resname   atom         cgnr     charge       mass
     1     c3         1      CH4    C              1   -0.46580968   12.010736
     2     hc         1      CH4    H              2    0.11645242    1.007941
     3     hc         1      CH4    H              3    0.11645242    1.007941
     4     hc         1      CH4    H              4    0.11645242    1.007941
     5     hc         1      CH4    H              5    0.11645242    1.007941
"""


# ---------------------------------------------------------------------------
# Test: transform_guest_itp with CH4
# ---------------------------------------------------------------------------

class TestTransformGuestItpCH4:
    """Tests for transform_guest_itp with CH4 ITP content."""

    def test_atomtypes_commented_out(self):
        """[ atomtypes ] section should be commented out after transformation."""
        result = transform_guest_itp(UNTRANSFORMED_ITP, "CH4")
        # The atomtypes data lines should now start with ';'
        assert "; c3" in result or ";c3" in result
        # The [ atomtypes ] header itself should be commented
        assert "; [ atomtypes ]" in result

    def test_moleculetype_name_gets_suffix(self):
        """Moleculetype name 'CH4' should become 'CH4_H'."""
        result = transform_guest_itp(UNTRANSFORMED_ITP, "CH4")
        # Find the moleculetype name line (after [ moleculetype ] header)
        lines = result.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('[') and 'moleculetype' in line.lower():
                # Next non-comment, non-empty line should have CH4_H
                for j in range(i + 1, len(lines)):
                    stripped = lines[j].strip()
                    if stripped and not stripped.startswith(';') and not stripped.startswith('#'):
                        assert stripped.startswith("CH4_H"), f"Expected 'CH4_H' but got '{stripped}'"
                        break
                break

    def test_nrexcl_preserved(self):
        """nrexcl number should be preserved after transformation."""
        result = transform_guest_itp(UNTRANSFORMED_ITP, "CH4")
        # The moleculetype name line should still have '3' as nrexcl
        lines = result.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('[') and 'moleculetype' in line.lower():
                for j in range(i + 1, len(lines)):
                    stripped = lines[j].strip()
                    if stripped and not stripped.startswith(';') and not stripped.startswith('#'):
                        parts = stripped.split()
                        assert parts[-1] == "3", f"Expected nrexcl=3 but got '{parts[-1]}'"
                        break
                break

    def test_atoms_section_unchanged(self):
        """[ atoms ] section residue names should NOT be modified."""
        result = transform_guest_itp(UNTRANSFORMED_ITP, "CH4")
        # The [ atoms ] section should still have "CH4" as residue name
        assert "1      CH4    C" in result


# ---------------------------------------------------------------------------
# Test: transform_guest_itp with THF
# ---------------------------------------------------------------------------

class TestTransformGuestItpTHF:
    """Tests for transform_guest_itp with THF ITP content."""

    def test_thf_gets_h_suffix(self):
        """THF moleculetype name should become 'THF_H'."""
        result = transform_guest_itp(THF_ITP, "THF")
        lines = result.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('[') and 'moleculetype' in line.lower():
                for j in range(i + 1, len(lines)):
                    stripped = lines[j].strip()
                    if stripped and not stripped.startswith(';') and not stripped.startswith('#'):
                        assert stripped.startswith("THF_H"), f"Expected 'THF_H' but got '{stripped}'"
                        break
                break

    def test_thf_h_is_five_chars(self):
        """THF_H (5 chars) should pass GRO format validation."""
        # If this test passes, no ValueError was raised
        result = transform_guest_itp(THF_ITP, "THF")
        assert "THF_H" in result


# ---------------------------------------------------------------------------
# Test: overlong base name raises ValueError
# ---------------------------------------------------------------------------

class TestTransformGuestItpOverlong:
    """Tests that overlong base names + suffix raise ValueError."""

    def test_ethan_base_raises(self):
        """'ETHAN' (5 chars) + '_H' = 'ETHAN_H' (7 chars) → ValueError."""
        with pytest.raises(ValueError, match="5-character GRO format limit"):
            transform_guest_itp(UNTRANSFORMED_ITP, "ETHAN")

    def test_etha_base_raises(self):
        """'ETHA' (4 chars) + '_H' = 'ETHA_H' (6 chars) → ValueError."""
        with pytest.raises(ValueError, match="5-character GRO format limit"):
            transform_guest_itp(UNTRANSFORMED_ITP, "ETHA")

    def test_error_message_mentions_name(self):
        """Error message should mention the offending name."""
        with pytest.raises(ValueError, match="ETHAN_H"):
            transform_guest_itp(UNTRANSFORMED_ITP, "ETHAN")


# ---------------------------------------------------------------------------
# Test: internal call to comment_out_atomtypes_in_itp
# ---------------------------------------------------------------------------

class TestTransformGuestItpAtomtypes:
    """Tests that transform_guest_itp delegates to comment_out_atomtypes_in_itp."""

    def test_calls_comment_out_atomtypes(self):
        """transform_guest_itp should comment out atomtypes like comment_out_atomtypes_in_itp."""
        # The result from transform_guest_itp should have the same
        # atomtypes transformations as comment_out_atomtypes_in_itp
        atomtypes_result = comment_out_atomtypes_in_itp(UNTRANSFORMED_ITP)
        full_result = transform_guest_itp(UNTRANSFORMED_ITP, "CH4")

        # Both should have atomtypes header commented out
        assert "; [ atomtypes ]" in atomtypes_result
        assert "; [ atomtypes ]" in full_result

        # Both should have atomtypes data lines commented
        assert "; c3" in atomtypes_result or ";c3" in atomtypes_result
        assert "; c3" in full_result or ";c3" in full_result

    def test_already_commented_atomtypes_still_works(self):
        """If atomtypes are already commented out, transformation still works."""
        # CH4_ITP has atomtypes section that comment_out_atomtypes will process
        result = transform_guest_itp(CH4_ITP, "CH4")
        assert "CH4_H" in result


# ---------------------------------------------------------------------------
# Test: suffix="_L" for liquid solutes
# ---------------------------------------------------------------------------

class TestTransformGuestItpSuffixL:
    """Tests for transform_guest_itp with suffix='_L' (liquid solutes)."""

    def test_ch4_liquid_suffix(self):
        """'CH4' with suffix='_L' should become 'CH4_L'."""
        result = transform_guest_itp(UNTRANSFORMED_ITP, "CH4", suffix="_L")
        lines = result.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('[') and 'moleculetype' in line.lower():
                for j in range(i + 1, len(lines)):
                    stripped = lines[j].strip()
                    if stripped and not stripped.startswith(';') and not stripped.startswith('#'):
                        assert stripped.startswith("CH4_L"), f"Expected 'CH4_L' but got '{stripped}'"
                        break
                break

    def test_thf_liquid_suffix(self):
        """'THF' with suffix='_L' should become 'THF_L'."""
        result = transform_guest_itp(THF_ITP, "THF", suffix="_L")
        assert "THF_L" in result

    def test_overlong_base_name_l_suffix_raises(self):
        """Overlong base name + '_L' should also raise ValueError."""
        with pytest.raises(ValueError, match="5-character GRO format limit"):
            transform_guest_itp(UNTRANSFORMED_ITP, "ETHAN", suffix="_L")


# ---------------------------------------------------------------------------
# Test: edge cases
# ---------------------------------------------------------------------------

class TestTransformGuestItpEdgeCases:
    """Edge case tests for transform_guest_itp."""

    def test_no_moleculetype_section(self):
        """ITP with no [ moleculetype ] section returns atomtypes-commented content."""
        result = transform_guest_itp(ITP_NO_MOLECULETYPE, "CH4")
        # atomtypes should be commented out
        assert "; [ atomtypes ]" in result
        # No CH4_H should appear (no moleculetype section to transform)
        assert "CH4_H" not in result

    def test_no_atomtypes_section(self):
        """ITP with no [ atomtypes ] section still transforms moleculetype name."""
        result = transform_guest_itp(ITP_NO_ATOMTYPES, "CH4")
        assert "CH4_H" in result

    def test_pretransformed_itp_is_noop(self):
        """Already-transformed ITP (like bundled ch4_hydrate.itp) should remain valid."""
        # Simulate a pre-transformed ITP (atomtypes already commented, name already has _H)
        pretransformed = """\
; [ atomtypes ]  ; COMMENTED - types defined in main .top file

[ moleculetype ]
; name          nrexcl
CH4_H         3

[ atoms ]
     1     c3         1      CH4_H    C              1   -0.46580968   12.010736
"""
        result = transform_guest_itp(pretransformed, "CH4")
        # Should still have CH4_H (no double-suffix)
        assert "CH4_H" in result
        assert "CH4_H_H" not in result

    def test_lowercase_moleculetype_name(self):
        """Lowercase moleculetype name gets replaced with uppercase+suffix."""
        # Some ITP files use lowercase moleculetype names (e.g., ch4.itp has 'ch4')
        lowercase_itp = """\
[ moleculetype ]
; name          nrexcl
ch4           3

[ atoms ]
     1     c3         1      CH4    C              1   -0.46580968   12.010736
"""
        result = transform_guest_itp(lowercase_itp, "CH4")
        # The moleculetype name should become CH4_H
        lines = result.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('[') and 'moleculetype' in line.lower():
                for j in range(i + 1, len(lines)):
                    stripped = lines[j].strip()
                    if stripped and not stripped.startswith(';') and not stripped.startswith('#'):
                        assert stripped.startswith("CH4_H"), f"Expected 'CH4_H' but got '{stripped}'"
                        break
                break

    def test_empty_content(self):
        """Empty string input should return empty string."""
        result = transform_guest_itp("", "CH4")
        assert result == ""
