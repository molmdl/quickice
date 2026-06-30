"""Unit tests for parse_itp_defaults_comb_rule (GUEST-07 foundation).

Validates that the comb-rule parser correctly handles:
- valid comb-rule=2 and comb-rule=1 inputs
- absent [ defaults ] section (returns None — valid, main .top supplies comb-rule=2)
- real fixture files (etoh.itp absent, etoh.top present, etoh_combrule1.itp reject path)
- comment lines (; and #) and blank lines ignored
- malformed comb-rule values (returns None)
- section boundaries (stops at next [ section ] header)
- empty [ defaults ] section with only comments (returns None)
"""

from pathlib import Path

import pytest

from quickice.structure_generation.itp_parser import parse_itp_defaults_comb_rule

# Project root (tests/ -> project root)
PROJECT_ROOT = Path(__file__).parent.parent
CUSTOM_DIR = PROJECT_ROOT / "quickice" / "data" / "custom"


def test_comb_rule_2():
    """[ defaults ] with comb-rule=2 returns 2."""
    content = "[ defaults ]\n; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n1 2 yes 0.5 0.8333\n"
    assert parse_itp_defaults_comb_rule(content) == 2


def test_comb_rule_1():
    """[ defaults ] with comb-rule=1 returns 1 (reject path)."""
    content = "[ defaults ]\n; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n1 1 yes 0.5 0.8333\n"
    assert parse_itp_defaults_comb_rule(content) == 1


def test_defaults_absent_returns_none():
    """Content without [ defaults ] section returns None (etoh.itp has none)."""
    etoh_itp = CUSTOM_DIR / "etoh.itp"
    content = etoh_itp.read_text()
    assert parse_itp_defaults_comb_rule(content) is None


def test_etoh_top_returns_2():
    """etoh.top has [ defaults ] with comb-rule=2 -> returns 2."""
    etoh_top = CUSTOM_DIR / "etoh.top"
    content = etoh_top.read_text()
    assert parse_itp_defaults_comb_rule(content) == 2


def test_etoh_combrule1_fixture_returns_1():
    """etoh_combrule1.itp fixture has [ defaults ] comb-rule=1 -> returns 1."""
    fixture = CUSTOM_DIR / "test_invalid" / "etoh_combrule1.itp"
    content = fixture.read_text()
    assert parse_itp_defaults_comb_rule(content) == 1


def test_comment_lines_ignored():
    """Semicolon comment lines after [ defaults ] header are skipped."""
    content = (
        "[ defaults ]\n"
        "; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n"
        "; another comment line\n"
        "1 2 yes 0.5 0.8333\n"
    )
    assert parse_itp_defaults_comb_rule(content) == 2


def test_hash_comments_ignored():
    """Hash (#) comment lines after [ defaults ] header are skipped."""
    content = (
        "[ defaults ]\n"
        "# a hash-style comment\n"
        "# another hash comment\n"
        "1 2 yes 0.5 0.8333\n"
    )
    assert parse_itp_defaults_comb_rule(content) == 2


def test_malformed_comb_rule_returns_none():
    """Non-integer comb-rule value returns None."""
    content = "[ defaults ]\n1 abc yes 0.5 0.8333\n"
    assert parse_itp_defaults_comb_rule(content) is None


def test_defaults_followed_by_another_section():
    """Section boundary handled: stops at next [ section ] header."""
    content = (
        "[ defaults ]\n"
        "; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n"
        "1 2 yes 0.5 0.8333\n"
        "[ atomtypes ]\n"
        "; name  at.num  mass  charge  ptype  sigma  epsilon\n"
        "hc  1  1.007941  0.0  A  2.6e-01  8.7e-02\n"
    )
    assert parse_itp_defaults_comb_rule(content) == 2


def test_empty_defaults_section_returns_none():
    """[ defaults ] with only comments (no data line) returns None."""
    content = (
        "[ defaults ]\n"
        "; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ\n"
        "; only comments here, no data\n"
    )
    assert parse_itp_defaults_comb_rule(content) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
