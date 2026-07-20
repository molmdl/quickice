"""Phase 48.1-07 (Wave 2e): Unit tests for ``_shared._write_top_defaults``.

Verifies the ``[defaults]`` block helper produces byte-identical output for all
3 format variants used by the 6 TOP writers (research §3 had an error: it
claimed "byte-identical across all 6 TOP writers" but the actual source has 3
distinct formats — see ``_shared._write_top_defaults`` docstring + 48.1-07
SUMMARY Deviations section for the correction).

Format variants (all comb-rule=2 — Lorentz-Berthelot, AMBER/GAFF2 convention):

- **Format A** (write_top_file, write_interface_top_file): 6 lines, includes
  ``; Defaults compatible with the Amber forcefield`` + compact ``; nbfunc``
  comment (single-space separators). Default helper invocation
  ``_write_top_defaults(f)``.
- **Format B** (write_multi_molecule_top_file): 5 lines, NO ``; Defaults``
  header, compact ``; nbfunc`` comment. ``_write_top_defaults(f,
  include_amber_header=False)``.
- **Format C** (write_ion_top_file, write_custom_molecule_top_file,
  write_solute_top_file): 5 lines, NO ``; Defaults`` header, aligned
  ``; nbfunc`` comment (multi-space tabular alignment).
  ``_write_top_defaults(f, include_amber_header=False,
  compact_nbfunc_comment=False)``.

The critical data line ``1               2               yes             0.5     0.8333``
(nbfunc=1, comb-rule=2) is byte-identical across all 3 variants — it lives in
ONE place (the helper body) and is the single source of truth for the AGENTS.md
comb-rule=2 constraint. The boolean flags only affect the 2 comment lines
above the data line, NOT the data line itself.

Coverage:

- ``TestWriteTopDefaults`` (5 tests — plan Task 2 spec): verify the default
  Format A invocation parses to comb-rule=2, nbfunc=1, fudgeLJ=0.5,
  fudgeQQ=0.8333, byte-identical to a hardcoded reference, and the helper is
  re-exported from ``quickice.output.gromacs_writer``.
- ``TestCombRule2Regression`` (1 test — plan Task 2 spec): verify the
  comb-rule=1 forbidden pattern is absent from the helper output.
- ``TestWriteTopDefaultsFormatVariants`` (8 tests — Rule 2 auto-added for the
  new parameterized functionality): verify all 3 format variants produce
  byte-identical output to the original inline blocks, the boolean flags
  correctly toggle the ``; Defaults`` header + ``; nbfunc`` comment style,
  and comb-rule=2 is preserved across all 3 variants.

References:
- AGENTS.md: "comb-rule=2 (Lorentz-Berthelot) in ALL GROMACS .top files —
  AMBER/GAFF2 convention. Never use comb-rule=1."
- Plan 48.1-07: extract TOP [defaults] block to ``_shared._write_top_defaults``
- Plan 48.1-07 SUMMARY Deviations: research §3 "byte-identical across all 6"
  error corrected (3 distinct formats discovered + parameterized helper)
"""

import io
import re

import pytest

from quickice.output._shared import _write_top_defaults
from quickice.output.gromacs_writer import _write_top_defaults as _re_exported


# ---------------------------------------------------------------------------
# Reference byte strings (the 3 format variants — locked for byte-identity)
# ---------------------------------------------------------------------------

# Format A: write_top_file + write_interface_top_file (default invocation).
# 6 lines: '; Defaults compatible' header + compact '; nbfunc' comment +
# comb-rule=2 data line + trailing blank line.
_FORMAT_A_EXPECTED = (
    "; Defaults compatible with the Amber forcefield\n"
    "[ defaults ]\n"
    "; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n"
    "; comb-rule=2 (Lorentz-Berthelot): sigma_ij=(sigma_i+sigma_j)/2, "
    "epsilon_ij=sqrt(eps_i*eps_j)\n"
    "; Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields\n"
    "1               2               yes             0.5     0.8333\n\n"
)

# Format B: write_multi_molecule_top_file (include_amber_header=False).
# 5 lines: NO '; Defaults compatible' header + compact '; nbfunc' comment +
# comb-rule=2 data line + trailing blank line.
_FORMAT_B_EXPECTED = (
    "[ defaults ]\n"
    "; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n"
    "; comb-rule=2 (Lorentz-Berthelot): sigma_ij=(sigma_i+sigma_j)/2, "
    "epsilon_ij=sqrt(eps_i*eps_j)\n"
    "; Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields\n"
    "1               2               yes             0.5     0.8333\n\n"
)

# Format C: write_ion_top_file + write_custom_molecule_top_file +
# write_solute_top_file (include_amber_header=False, compact_nbfunc_comment=False).
# 5 lines: NO '; Defaults compatible' header + multi-space aligned '; nbfunc'
# comment + comb-rule=2 data line + trailing blank line.
_FORMAT_C_EXPECTED = (
    "[ defaults ]\n"
    "; nbfunc        comb-rule       gen-pairs       fudgeLJ fudgeQQ\n"
    "; comb-rule=2 (Lorentz-Berthelot): sigma_ij=(sigma_i+sigma_j)/2, "
    "epsilon_ij=sqrt(eps_i*eps_j)\n"
    "; Matches AMBER/GAFF2 convention used by GROMACS-bundled AMBER force fields\n"
    "1               2               yes             0.5     0.8333\n\n"
)


def _parse_defaults(top_text: str) -> dict:
    """Parse the [defaults] section from .top text into a dict.

    Mirrors ``tests.test_tip4p_ice_lj_values._parse_defaults`` so the parsing
    contract is consistent across the LJ regression suite and this helper
    unit test.
    """
    defaults: dict = {}
    in_section = False
    for line in top_text.splitlines():
        stripped = line.strip()
        if stripped == "[ defaults ]":
            in_section = True
            continue
        if in_section and stripped.startswith("["):
            break
        if in_section and (stripped.startswith(";") or stripped == ""):
            continue
        if in_section:
            parts = stripped.split()
            if len(parts) >= 5:
                try:
                    defaults["nbfunc"] = int(parts[0])
                    defaults["comb_rule"] = int(parts[1])
                    defaults["gen_pairs"] = parts[2]
                    defaults["fudgeLJ"] = float(parts[3])
                    defaults["fudgeQQ"] = float(parts[4])
                except (ValueError, IndexError):
                    pass
                break
    return defaults


# ---------------------------------------------------------------------------
# Tests: TestWriteTopDefaults (plan Task 2 spec — 5 tests on default Format A)
# ---------------------------------------------------------------------------

class TestWriteTopDefaults:
    """Plan Task 2 spec: 5 unit tests verifying _write_top_defaults (default
    Format A invocation) produces the comb-rule=2 [defaults] block
    byte-identically with the correct AMBER/GAFF2 convention.
    """

    def test_comb_rule_is_2(self):
        """``comb_rule`` must parse to 2 (Lorentz-Berthelot, AMBER convention).

        AGENTS.md: "comb-rule=2 (Lorentz-Berthelot) in ALL GROMACS .top files —
        AMBER/GAFF2 convention. Never use comb-rule=1."
        """
        f = io.StringIO()
        _write_top_defaults(f)
        defaults = _parse_defaults(f.getvalue())
        assert defaults.get("comb_rule") == 2, (
            f"comb_rule={defaults.get('comb_rule')} must be 2 "
            "(Lorentz-Berthelot, AMBER/GAFF2 convention per AGENTS.md)"
        )

    def test_nbfunc_is_1(self):
        """``nbfunc`` must parse to 1 (Lennard-Jones + Coulomb — GROMACS standard
        for atomistic force fields)."""
        f = io.StringIO()
        _write_top_defaults(f)
        defaults = _parse_defaults(f.getvalue())
        assert defaults.get("nbfunc") == 1, (
            f"nbfunc={defaults.get('nbfunc')} must be 1 (LJ + Coulomb)"
        )

    def test_fudge_values(self):
        """``fudgeLJ=0.5`` and ``fudgeQQ=0.8333`` (Amber defaults —
        1-4 scaling factors for LJ + Coulomb interactions)."""
        f = io.StringIO()
        _write_top_defaults(f)
        defaults = _parse_defaults(f.getvalue())
        assert abs(defaults.get("fudgeLJ", 0) - 0.5) < 0.001, (
            f"fudgeLJ={defaults.get('fudgeLJ')} must be 0.5 (Amber default)"
        )
        assert abs(defaults.get("fudgeQQ", 0) - 0.8333) < 0.001, (
            f"fudgeQQ={defaults.get('fudgeQQ')} must be 0.8333 (Amber default)"
        )

    def test_byte_identical_to_reference(self):
        """Default invocation output must be byte-identical to the hardcoded
        Format A reference (locks the format — any whitespace/comment change
        would be caught here)."""
        f = io.StringIO()
        _write_top_defaults(f)
        assert f.getvalue() == _FORMAT_A_EXPECTED, (
            "Default _write_top_defaults(f) output drifted from Format A "
            "reference. Expected (repr):\n"
            f"{repr(_FORMAT_A_EXPECTED)}\n"
            "Actual (repr):\n"
            f"{repr(f.getvalue())}"
        )

    def test_re_exported_from_gromacs_writer(self):
        """``_write_top_defaults`` must be re-exported from
        ``quickice.output.gromacs_writer`` so all 6 TOP writers (which import
        from gromacs_writer) can call it. Verifies the re-export points to the
        SAME function object (not a copy)."""
        assert _re_exported is _write_top_defaults, (
            "_write_top_defaults re-exported from gromacs_writer must be the "
            "same function object as the one defined in _shared — got different "
            f"objects ({_re_exported!r} vs {_write_top_defaults!r})"
        )


# ---------------------------------------------------------------------------
# Tests: TestCombRule2Regression (plan Task 2 spec — comb-rule=1 forbidden)
# ---------------------------------------------------------------------------

class TestCombRule2Regression:
    """Plan Task 2 spec: regression test ensuring the forbidden comb-rule=1
    pattern (``1   1   yes   0.5   0.8333``) never appears in the helper
    output. Mirrors ``tests.test_tip4p_ice_lj_values.TestNoBuggyHardcodedValues
    ::test_no_comb_rule_1`` but scoped to the helper's runtime output rather
    than source-text grep.
    """

    def test_no_comb_rule_1_in_defaults_output(self):
        """The forbidden comb-rule=1 pattern must NOT appear in the helper
        output for any of the 3 format variants (AGENTS.md: "Never use
        comb-rule=1")."""
        buggy_pattern = re.compile(r'1\s+1\s+yes\s+0\.5\s+0\.8333')
        for variant_name, kwargs in [
            ("Format A (default)", {}),
            ("Format B (include_amber_header=False)",
             {"include_amber_header": False}),
            ("Format C (include_amber_header=False, "
             "compact_nbfunc_comment=False)",
             {"include_amber_header": False,
              "compact_nbfunc_comment": False}),
        ]:
            f = io.StringIO()
            _write_top_defaults(f, **kwargs)
            output = f.getvalue()
            matches = buggy_pattern.findall(output)
            assert len(matches) == 0, (
                f"{variant_name}: found {len(matches)} comb-rule=1 matches in "
                f"_write_top_defaults output — comb-rule=1 is forbidden per "
                "AGENTS.md (must use comb-rule=2 Lorentz-Berthelot). "
                f"Output:\n{output}"
            )


# ---------------------------------------------------------------------------
# Tests: TestWriteTopDefaultsFormatVariants (Rule 2 auto-added — tests for
# the new parameterized Format B + Format C variants)
# ---------------------------------------------------------------------------

class TestWriteTopDefaultsFormatVariants:
    """Rule 2 auto-added tests for the parameterized format variants (the
    plan's 5-test spec only covered the default Format A; the new
    ``include_amber_header`` + ``compact_nbfunc_comment`` flags needed test
    coverage to lock in byte-identity for Formats B and C).

    These tests verify:
    - Each of the 3 format variants produces byte-identical output to its
      hardcoded reference (locks the format).
    - The ``include_amber_header`` flag correctly toggles the
      ``; Defaults compatible with the Amber forcefield`` header line.
    - The ``compact_nbfunc_comment`` flag correctly toggles between the
      compact (single-space) and aligned (multi-space) ``; nbfunc`` comment.
    - comb-rule=2 is preserved across all 3 variants (AGENTS.md constraint
      holds regardless of comment-style variant).
    """

    def test_format_a_byte_identical(self):
        """Format A (default invocation) byte-identical to the reference
        (write_top_file + write_interface_top_file inline blocks)."""
        f = io.StringIO()
        _write_top_defaults(f)
        assert f.getvalue() == _FORMAT_A_EXPECTED

    def test_format_b_byte_identical(self):
        """Format B (include_amber_header=False) byte-identical to the
        reference (write_multi_molecule_top_file inline block)."""
        f = io.StringIO()
        _write_top_defaults(f, include_amber_header=False)
        assert f.getvalue() == _FORMAT_B_EXPECTED, (
            "Format B (include_amber_header=False) output drifted from "
            "write_multi_molecule_top_file reference.\n"
            f"Expected (repr):\n{repr(_FORMAT_B_EXPECTED)}\n"
            f"Actual (repr):\n{repr(f.getvalue())}"
        )

    def test_format_c_byte_identical(self):
        """Format C (include_amber_header=False, compact_nbfunc_comment=False)
        byte-identical to the reference (write_ion_top_file +
        write_custom_molecule_top_file + write_solute_top_file inline
        blocks)."""
        f = io.StringIO()
        _write_top_defaults(
            f,
            include_amber_header=False,
            compact_nbfunc_comment=False,
        )
        assert f.getvalue() == _FORMAT_C_EXPECTED, (
            "Format C (include_amber_header=False, "
            "compact_nbfunc_comment=False) output drifted from "
            "write_ion/custom_molecule/solute_top_file reference.\n"
            f"Expected (repr):\n{repr(_FORMAT_C_EXPECTED)}\n"
            f"Actual (repr):\n{repr(f.getvalue())}"
        )

    def test_format_a_has_amber_header(self):
        """Format A output includes the
        ``; Defaults compatible with the Amber forcefield`` header line."""
        f = io.StringIO()
        _write_top_defaults(f)
        assert "; Defaults compatible with the Amber forcefield\n" in f.getvalue()

    def test_format_b_no_amber_header(self):
        """Format B output does NOT include the ``; Defaults compatible``
        header (preserves byte-identity with write_multi_molecule_top_file
        which lacks the line)."""
        f = io.StringIO()
        _write_top_defaults(f, include_amber_header=False)
        assert "; Defaults compatible with the Amber forcefield" not in f.getvalue(), (
            "Format B (include_amber_header=False) must NOT emit the "
            "'; Defaults compatible' header — write_multi_molecule_top_file "
            "lacks this line byte-identically."
        )

    def test_format_c_no_amber_header(self):
        """Format C output does NOT include the ``; Defaults compatible``
        header (preserves byte-identity with write_ion/custom_molecule/
        solute_top_file which lack the line)."""
        f = io.StringIO()
        _write_top_defaults(
            f, include_amber_header=False, compact_nbfunc_comment=False,
        )
        assert "; Defaults compatible with the Amber forcefield" not in f.getvalue()

    def test_format_a_compact_nbfunc_comment(self):
        """Format A uses the compact ``; nbfunc  comb-rule  gen-pairs  fudgeLJ
        fudgeQQ`` comment (single-space separators)."""
        f = io.StringIO()
        _write_top_defaults(f)
        assert "; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n" in f.getvalue()
        # The aligned (multi-space) variant must NOT appear in Format A.
        assert (
            "; nbfunc        comb-rule       gen-pairs       fudgeLJ fudgeQQ\n"
            not in f.getvalue()
        )

    def test_format_c_aligned_nbfunc_comment(self):
        """Format C uses the aligned
        ``; nbfunc        comb-rule       gen-pairs       fudgeLJ fudgeQQ``
        comment (multi-space tabular alignment — different from Format A/B)."""
        f = io.StringIO()
        _write_top_defaults(
            f, include_amber_header=False, compact_nbfunc_comment=False,
        )
        assert (
            "; nbfunc        comb-rule       gen-pairs       fudgeLJ fudgeQQ\n"
            in f.getvalue()
        )
        # The compact (single-space) variant must NOT appear in Format C.
        assert "; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n" not in f.getvalue()

    def test_comb_rule_2_in_all_variants(self):
        """All 3 format variants must parse to comb_rule=2 (AGENTS.md
        constraint enforced from the single source of truth — the data line
        is byte-identical across variants; only the 2 comment lines above
        differ)."""
        for variant_name, kwargs in [
            ("Format A", {}),
            ("Format B", {"include_amber_header": False}),
            ("Format C", {"include_amber_header": False,
                          "compact_nbfunc_comment": False}),
        ]:
            f = io.StringIO()
            _write_top_defaults(f, **kwargs)
            defaults = _parse_defaults(f.getvalue())
            assert defaults.get("comb_rule") == 2, (
                f"{variant_name}: comb_rule={defaults.get('comb_rule')} "
                "must be 2 (Lorentz-Berthelot — AGENTS.md constraint enforced "
                "from _write_top_defaults single source of truth)"
            )

    def test_data_line_byte_identical_across_variants(self):
        """The critical data line
        ``1               2               yes             0.5     0.8333``
        must be byte-identical across all 3 format variants — it's the
        single source of truth for comb-rule=2 (AGENTS.md). The boolean flags
        only affect the 2 comment lines above the data line, NOT the data
        line itself."""
        data_line = "1               2               yes             0.5     0.8333\n\n"
        for variant_name, kwargs in [
            ("Format A", {}),
            ("Format B", {"include_amber_header": False}),
            ("Format C", {"include_amber_header": False,
                          "compact_nbfunc_comment": False}),
        ]:
            f = io.StringIO()
            _write_top_defaults(f, **kwargs)
            output = f.getvalue()
            assert output.endswith(data_line), (
                f"{variant_name}: output must end with the byte-identical "
                f"comb-rule=2 data line. Expected tail (repr): {repr(data_line)}\n"
                f"Actual output (repr): {repr(output)}"
            )
