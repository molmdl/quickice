"""Unit tests for [ atoms ] resname rewrite in transform_guest_itp (Phase 40-02).

Validates the Step 3 extension to ``transform_guest_itp`` that rewrites the
resname column (4th field, 0-indexed 3) in the ``[ atoms ]`` section to
``{guest_name}{suffix}`` (e.g. ``"MOL"`` -> ``"MOL_H"``), completing the
deferred Phase 38-04 item so custom guest ITPs are internally consistent
(``[ moleculetype ] etoh_custom_H`` ... ``[ atoms ] ... MOL_H ...``).

Coverage:
  1. Custom guest (etoh.itp, resname "MOL") rewritten to "MOL_H"
  2. All 9 atom data lines rewritten consistently
  3. Comment lines inside [ atoms ] preserved verbatim
  4. Graceful no-op when [ atoms ] section is absent (no crash)
  5. Built-in CH4 backward compatibility (CH4 -> CH4_H)
  6. Step 1 (atomtypes comment-out) still works
  7. Rewrite scoped to [ atoms ] only (no leakage to other sections)
"""

import re
from pathlib import Path

from quickice.output.gromacs_writer import transform_guest_itp


ETOH_ITP_PATH = Path(__file__).parent.parent / "quickice" / "data" / "custom" / "etoh.itp"

# Regex matching the [ atoms ] section header + body (up to the next [ section ]
# header or end of string).  Mirrors the pattern used by the implementation.
_ATOMS_RE = re.compile(r'\[\s*atoms\s*\](.*?)(?=\[\s*\w+\s*\]|$)', re.DOTALL | re.IGNORECASE)


def _atoms_body(content: str) -> str:
    """Return the body text of the [ atoms ] section (text after the header)."""
    m = _ATOMS_RE.search(content)
    assert m is not None, "no [ atoms ] section found in content"
    return m.group(1)


def _atoms_data_lines(content: str) -> list:
    """Return the data lines (non-comment, non-blank) of the [ atoms ] section."""
    body = _atoms_body(content)
    return [
        line for line in body.split('\n')
        if line.strip()
        and not line.strip().startswith(';')
        and not line.strip().startswith('#')
    ]


def _moleculetype_name(content: str) -> str:
    """Return the moleculetype name (first field of the name line)."""
    m = re.search(r'\[\s*moleculetype\s*\]\s*\n[^\n]*\n\s*(\S+)', content, re.IGNORECASE)
    assert m is not None, "no [ moleculetype ] section found"
    return m.group(1)


class TestAtomsResnameRewrite:
    """Tests for the [ atoms ] resname rewrite (Step 3) in transform_guest_itp."""

    def test_custom_guest_resname_rewritten(self):
        """Custom guest etoh.itp: moleculetype and [ atoms ] resname both become MOL_H."""
        content = ETOH_ITP_PATH.read_text()
        result = transform_guest_itp(content, "MOL", "_H")
        # Step 2: moleculetype name -> MOL_H
        assert _moleculetype_name(result) == "MOL_H"
        # Step 3: every [ atoms ] data line has resname MOL_H; none have bare MOL
        for line in _atoms_data_lines(result):
            fields = line.split()
            assert len(fields) >= 4, f"atom line has <4 fields: {line!r}"
            assert fields[3] == "MOL_H", (
                f"expected resname 'MOL_H', got {fields[3]!r} in line: {line!r}"
            )
            assert fields[3] != "MOL", f"bare 'MOL' resname leaked: {line!r}"

    def test_all_atom_lines_rewritten(self):
        """All 9 atom data lines in etoh.itp [ atoms ] get resname MOL_H."""
        content = ETOH_ITP_PATH.read_text()
        result = transform_guest_itp(content, "MOL", "_H")
        data_lines = _atoms_data_lines(result)
        assert len(data_lines) == 9, (
            f"etoh.itp defines 9 atoms, found {len(data_lines)} data lines"
        )
        mol_h_count = sum(1 for line in data_lines if line.split()[3] == "MOL_H")
        assert mol_h_count == 9, (
            f"expected 9 MOL_H resnames, found {mol_h_count}"
        )

    def test_comment_lines_preserved(self):
        """Comment lines (starting with ;) inside [ atoms ] are preserved verbatim."""
        content = ETOH_ITP_PATH.read_text()
        result = transform_guest_itp(content, "MOL", "_H")
        # Collect original [ atoms ] comment lines and assert each is preserved
        orig_comments = [
            line for line in _atoms_body(content).split('\n')
            if line.strip().startswith(';')
        ]
        assert len(orig_comments) >= 1, "etoh.itp [ atoms ] has no comment lines"
        for comment in orig_comments:
            assert comment in result, (
                f"[ atoms ] comment line not preserved verbatim: {comment!r}"
            )
        # Specifically, the descriptive header comment must still be present
        assert ";  Index   type   residue  resname   atom" in result

    def test_no_atoms_section_no_crash(self):
        """ITP with [ moleculetype ] but no [ atoms ] does not crash (graceful no-op)."""
        itp = (
            "[ moleculetype ]\n"
            "; name  nrexcl\n"
            "CH4 3\n"
            "\n"
            "[ bonds ]\n"
            ";  atom_i  atom_j  functype  r0\n"
            "1 2 1 0.1\n"
        )
        # Must not raise; Step 3 is a no-op because there is no [ atoms ] section
        result = transform_guest_itp(itp, "CH4", "_H")
        # Step 2 still renames the moleculetype
        assert "CH4_H" in result
        # No [ atoms ] section was introduced
        assert _ATOMS_RE.search(result) is None

    def test_builtin_ch4_backward_compat(self):
        """Built-in CH4 ITP: moleculetype ch4 -> CH4_H, [ atoms ] resname CH4 -> CH4_H."""
        itp = (
            "[ moleculetype ]\n"
            "; name  nrexcl\n"
            "ch4 3\n"
            "\n"
            "[ atoms ]\n"
            ";  Index  type  residue  resname  atom  cgnr  charge  mass\n"
            "1 c3 1 CH4 C 1 -0.4 12.0\n"
        )
        result = transform_guest_itp(itp, "CH4", "_H")
        # Step 2: moleculetype name (lowercase 'ch4') -> CH4_H
        assert _moleculetype_name(result) == "CH4_H"
        # Step 3: [ atoms ] resname -> CH4_H
        data_lines = _atoms_data_lines(result)
        assert len(data_lines) == 1
        assert data_lines[0].split()[3] == "CH4_H", (
            f"expected CH4_H resname, got {data_lines[0].split()[3]!r}"
        )

    def test_atomtypes_still_commented(self):
        """Step 1 still works: [ atomtypes ] header and data lines are commented out."""
        content = ETOH_ITP_PATH.read_text()
        result = transform_guest_itp(content, "MOL", "_H")
        # The [ atomtypes ] header itself must be commented
        assert "; [ atomtypes ]" in result
        # etoh.itp defines 5 atomtypes: hc, c3, h1, oh, ho
        # After Step 1 each appears in a line starting with ';' (commented out)
        lines = result.split('\n')
        for name in ("hc", "c3", "h1", "oh", "ho"):
            found_commented = any(
                line.strip().startswith(';') and line.strip().split()[1:2] == [name]
                for line in lines
            )
            assert found_commented, (
                f"atomtype {name!r} not found in a commented [ atomtypes ] line"
            )

    def test_resname_does_not_leak_outside_atoms(self):
        """Resname rewrite is scoped to [ atoms ] — other sections are untouched.

        A [ bonds ] comment that mentions 'MOL' must remain 'MOL' (not become
        'MOL_H'); only the [ atoms ] resname column is rewritten.
        """
        itp = (
            "[ moleculetype ]\n"
            "MOL 3\n"
            "\n"
            "[ atoms ]\n"
            "1 c3 1 MOL C 1 0 12\n"
            "\n"
            "[ bonds ]\n"
            "; comment about MOL residue\n"
            "1 2 1 0.1\n"
        )
        result = transform_guest_itp(itp, "MOL", "_H")
        # [ atoms ] resname rewritten to MOL_H
        assert "MOL_H" in result
        data_lines = _atoms_data_lines(result)
        assert data_lines[0].split()[3] == "MOL_H"
        # [ bonds ] comment mentioning MOL is preserved verbatim (NOT rewritten)
        assert "; comment about MOL residue" in result
        assert "; comment about MOL_H residue" not in result
