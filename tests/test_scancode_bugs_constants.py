"""Regression tests for scancode Group 5: module constants cleanup.

Covers UNIT-02, UNIT-03, UNIT-04, UNIT-05 from
``.planning/scancode-fixes/RESEARCH.md`` (all CONFIRMED). These are PURE
REFACTOR commits — NO numeric value may change.

This file grows across the four atomic commits (one per UNIT). The tests
present at each commit exercise ONLY the constants introduced by that commit
and the cumulative byte-equivalence guard. The final commit (UNIT-05)
contains all test classes.

Common invariants tested at every commit:
  - **Byte-equivalence** — The produced ``.top`` (via ``write_top_file`` on a
    real ice_ih candidate) and ``.itp`` (via ``generate_ion_itp``) are
    BYTE-IDENTICAL to the pre-refactor baseline (MD5 snapshot). This is the
    primary guard that the refactor changed NO numeric value.
  - **GROMACS-level** (when ``gmx`` is on PATH) — ``gmx grompp`` dry-run on a
    real ice_ih export confirms the topology is still simulation-ready.

Baseline MD5 captured BEFORE the refactor (ice_ih 96-target → 128 actual
mols, phase_id="ice_ih"):
  - ``write_top_file`` → ``bb3df33e131a5d18c5f5439eaa0c29b2``
  - ``generate_ion_itp(2, 3)`` → ``bb6d3d1ec3a5bc97bea20b5a70bee663``
"""

import hashlib
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

# Make tests/ importable for e2e_export_helpers (conftest import is unreliable).
sys.path.insert(0, str(Path(__file__).parent))

from tests.conftest import gmx_skipif

from quickice.output import gromacs_writer as gwm
from quickice.output.gromacs_writer import (
    ION_ATOMTYPES,
    TIP4P_ICE_ALPHA,
    TIP4P_ICE_HW_CHARGE,
    TIP4P_ICE_MW_CHARGE,
    TIP4P_ICE_OW_EPSILON,
    TIP4P_ICE_OW_SIGMA,
    TIP4P_ICE_SETTLE_DHH,
    TIP4P_ICE_SETTLE_DOH,
    write_gro_file,
    write_top_file,
)
from quickice.structure_generation.gromacs_ion_export import (
    CL_CHARGE,
    NA_CHARGE,
    generate_ion_itp,
)
from quickice.structure_generation.solute_inserter import (
    CH4_CH_BOND_LENGTH_NM,
    SoluteInserter,
)
from quickice.structure_generation.types import SoluteConfig


# ── Baseline MD5 (captured pre-refactor) ─────────────────────────────────────

TOP_MD5_BASELINE = "bb3df33e131a5d18c5f5439eaa0c29b2"
ITP_MD5_BASELINE = "bb6d3d1ec3a5bc97bea20b5a70bee663"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _data_dir() -> Path:
    """Locate quickice/data/ (the bundled ITP source of truth)."""
    import quickice
    return Path(quickice.__file__).parent / "data"


def _all_output_sources() -> str:
    """Concatenate all quickice/output/*.py source files for source-text grep.

    After the Phase 48.1 Wave 1 split, the constants (TIP4P_ICE_ALPHA,
    ION_ATOMTYPES, etc.) live in _constants.py (re-exported through _shared.py),
    not in gromacs_writer.py. Scanning ALL sibling .py files ensures the
    UNIT-03/UNIT-05 source-text invariants hold regardless of which file the
    constants live in. Uses Path("quickice/output").glob("*.py") so future
    waves that add more sibling modules are automatically covered.
    """
    output_dir = Path("quickice/output")
    return "\n".join(p.read_text() for p in sorted(output_dir.glob("*.py")))


def _count_tip4p_ice_alpha_defs() -> int:
    """Count ``TIP4P_ICE_ALPHA = <value>`` assignments across quickice/output/*.py.

    UNIT-03 requires EXACTLY ONE definition. (Pre-refactor there were two in
    gromacs_writer.py.) After the Phase 48.1 Wave 1 split, the single
    definition lives in _constants.py; the re-exports in _shared.py and
    gromacs_writer.py use ``import`` syntax (no ``=``), so they don't match.
    """
    src = _all_output_sources()
    return len(re.findall(r"^TIP4P_ICE_ALPHA\s*=\s*", src, re.M))


def _parse_tip4p_ice_itp() -> dict:
    """Parse quickice/data/tip4p-ice.itp and return the TIP4P-ICE values.

    The bundled .itp is the source of truth per AGENTS.md. Used by UNIT-02
    to cross-check the extracted charge/settle constants against the ITP.
    """
    text = (_data_dir() / "tip4p-ice.itp").read_text()
    hw = re.search(
        r"^\s*\d+\s+HW_ice\s+\d+\s+SOL\s+HW\d+\s+\d+\s+(\S+)\s+\S+\s*$",
        text, re.M,
    )
    mw = re.search(
        r"^\s*\d+\s+MW\s+\d+\s+SOL\s+MW\s+\d+\s+(\S+)\s+\S+\s*$",
        text, re.M,
    )
    doh = re.search(r"^\s*1\s+2\s+1\s+(\S+)\s*$", text, re.M)
    dhh = re.search(r"^\s*2\s+3\s+1\s+(\S+)\s*$", text, re.M)
    return {
        "hw_charge": float(hw.group(1)),
        "mw_charge": float(mw.group(1)),
        "settle_doh": float(doh.group(1)),
        "settle_dhh": float(dhh.group(1)),
    }


def _parse_ch4_itp_bond() -> float:
    """Parse quickice/data/ch4.itp [bonds] and return the C-H bond length (nm).

    Used by UNIT-04 to cross-check the extracted CH4_CH_BOND_LENGTH_NM constant
    against the bundled ITP (the source of truth).
    """
    text = (_data_dir() / "ch4.itp").read_text()
    bond = re.search(r"^\s*1\s+2\s+1\s+(\S+)\s+", text, re.M)
    return float(bond.group(1))


def _ion_atomtypes_has_clarifying_comment() -> bool:
    """UNIT-05: ION_ATOMTYPES must carry a comment explaining the [atomtypes]
    charge=0.0 placeholder convention (vs the real ±0.85 in [moleculetype]
    [atoms])."""
    src = _all_output_sources()
    # Find the ION_ATOMTYPES block and check for the convention explanation.
    block = re.search(
        r"# Madrid2019 ion atomtype parameters.*?ION_ATOMTYPES\s*[:=].*?\}",
        src, re.S,
    )
    if block is None:
        return False
    comment = block.group(0)
    return (
        "charge" in comment.lower()
        and "0.0" in comment
        and "moleculetype" in comment.lower()
        and "NOT" in comment  # "NOT duplicates"
    )


def _ion_export_has_clarifying_comment() -> bool:
    """UNIT-05: gromacs_ion_export.py NA_CHARGE/CL_CHARGE must carry a comment
    cross-referencing the [moleculetype] [atoms] vs [atomtypes] convention."""
    import quickice.structure_generation.gromacs_ion_export as gie
    src = Path(gie.__file__).read_text()
    block = re.search(r"# Partial charges.*?CL_CHARGE\s*=\s*-?[\d.]+", src, re.S)
    if block is None:
        return False
    comment = block.group(0)
    return (
        "moleculetype" in comment.lower()
        and ("[atoms]" in comment or "[ atoms ]" in comment)
        and "atomtypes" in comment.lower()
    )


# ══════════════════════════════════════════════════════════════════════════════
# UNIT-03: dedup TIP4P_ICE_ALPHA
# ══════════════════════════════════════════════════════════════════════════════

class TestUNIT03:
    """UNIT-03: TIP4P_ICE_ALPHA defined exactly once; inline uses the constant."""

    def test_tip4p_ice_alpha_defined_exactly_once(self):
        """TIP4P_ICE_ALPHA must be assigned exactly once in gromacs_writer.py.

        Pre-refactor it was defined twice (line ~53 and ~444, same value).
        UNIT-03 removes the duplicate.
        """
        n = _count_tip4p_ice_alpha_defs()
        assert n == 1, (
            f"TIP4P_ICE_ALPHA should be defined exactly ONCE, found {n} "
            f"definitions in gromacs_writer.py (UNIT-03 regression: duplicate "
            f"definition reintroduced?)"
        )

    def test_tip4p_ice_alpha_value(self):
        """TIP4P_ICE_ALPHA == 0.13458335 (Abascal 2005, TIP4P-ICE)."""
        assert TIP4P_ICE_ALPHA == 0.13458335
        # The bundled .itp rounds to 5 decimals (0.13458); the writer uses the
        # full 8-decimal value. Both represent the same alpha.
        assert abs(TIP4P_ICE_ALPHA - 0.13458) < 1e-4

    def test_no_inline_alpha_magic_number_in_top_writer(self):
        """The virtual_sites3 line in write_top_file must use the constant,
        not the inline 0.13458335 magic number.

        The literal may still appear in the constant definition and in
        docstrings/comments (documentation) — those are fine. It must NOT
        appear inside any f.write(...) string literal (that's the inline
        magic number UNIT-03 removed)."""
        src = Path(gwm.__file__).read_text()
        # Extract every f.write(...) string literal's content.
        write_strings = re.findall(r'f?write\(\s*(?:f)?"([^"]*)"', src)
        write_strings += re.findall(r"f?write\(\s*(?:f)?'([^']*)'", src)
        for s in write_strings:
            assert "0.13458335" not in s, (
                "Inline '0.13458335' found in an f.write string — UNIT-03 "
                "regression: the virtual_sites3 line should use "
                "{TIP4P_ICE_ALPHA}, not the literal."
            )


# ══════════════════════════════════════════════════════════════════════════════
# UNIT-02: TIP4P-ICE charges/settle/alpha constants
# ══════════════════════════════════════════════════════════════════════════════

class TestUNIT02:
    """UNIT-02: TIP4P-ICE charges/settle distances extracted to constants."""

    def test_constants_exist_with_correct_values(self):
        """All four UNIT-02 constants exist and match the bundled ITP."""
        itp = _parse_tip4p_ice_itp()
        assert TIP4P_ICE_HW_CHARGE == 0.5897
        assert TIP4P_ICE_MW_CHARGE == -1.1794
        assert TIP4P_ICE_SETTLE_DOH == 0.09572
        assert TIP4P_ICE_SETTLE_DHH == 0.15139
        # Cross-check against the bundled tip4p-ice.itp (source of truth).
        assert TIP4P_ICE_HW_CHARGE == itp["hw_charge"]
        assert TIP4P_ICE_MW_CHARGE == itp["mw_charge"]
        assert TIP4P_ICE_SETTLE_DOH == itp["settle_doh"]
        assert TIP4P_ICE_SETTLE_DHH == itp["settle_dhh"]

    def test_water_charge_neutrality(self):
        """TIP4P-ICE water is charge-neutral: OW=0, 2*HW=+1.1794, MW=-1.1794."""
        assert 2 * TIP4P_ICE_HW_CHARGE + TIP4P_ICE_MW_CHARGE == 0.0
        assert TIP4P_ICE_MW_CHARGE == -(2 * TIP4P_ICE_HW_CHARGE)

    def test_lj_constants_still_present(self):
        """The pre-existing LJ constants (TIP4P_ICE_OW_SIGMA/EPSILON) are
        unchanged by UNIT-02 (they were already constants)."""
        assert TIP4P_ICE_OW_SIGMA == 3.16680e-1
        assert TIP4P_ICE_OW_EPSILON == 8.82110e-1

    def test_no_inline_charge_magic_numbers_in_top_writer(self):
        """The [atoms]/[settles] lines in write_top_file must use the constants,
        not inline 0.5897 / -1.1794 / 0.09572 / 0.15139 magic numbers.

        The literals may still appear in the constant definitions and in
        comments (documentation) — those are fine. They must NOT appear inside
        any f.write(...) string literal (those are the inline magic numbers
        UNIT-02 removed)."""
        src = Path(gwm.__file__).read_text()
        write_strings = re.findall(r'f?write\(\s*(?:f)?"([^"]*)"', src)
        write_strings += re.findall(r"f?write\(\s*(?:f)?'([^']*)'", src)
        for literal in ["0.5897", "-1.1794", "0.09572", "0.15139"]:
            for s in write_strings:
                assert literal not in s, (
                    f"Inline {literal!r} found in an f.write string — "
                    f"UNIT-02 regression: the [atoms]/[settles] lines should "
                    f"use named constants, not the literal."
                )


# ══════════════════════════════════════════════════════════════════════════════
# UNIT-04: CH4 C-H bond length constant
# ══════════════════════════════════════════════════════════════════════════════

class TestUNIT04:
    """UNIT-04: CH4_CH_BOND_LENGTH_NM named constant in solute_inserter.py."""

    def test_constant_exists_with_correct_value(self):
        """CH4_CH_BOND_LENGTH_NM == 0.109620, cross-checked against ch4.itp."""
        assert CH4_CH_BOND_LENGTH_NM == 0.109620
        assert CH4_CH_BOND_LENGTH_NM == _parse_ch4_itp_bond()

    def test_no_inline_r_ch_magic_number(self):
        """The inline ``r_ch = 0.109620`` must be replaced by the constant.

        The literal may still appear in the constant definition and in
        docstrings/comments (documentation) — those are fine. The assignment
        ``r_ch = <literal>`` must NOT exist; it should be
        ``r_ch = CH4_CH_BOND_LENGTH_NM``."""
        import quickice.structure_generation.solute_inserter as si
        src = Path(si.__file__).read_text()
        # An assignment of the literal to r_ch is the UNIT-04 bug.
        bad_assignment = re.search(r"r_ch\s*=\s*0\.109620\b", src)
        assert bad_assignment is None, (
            f"Inline 'r_ch = 0.109620' found — UNIT-04 regression: should "
            f"be 'r_ch = CH4_CH_BOND_LENGTH_NM'."
        )
        # The constant reference must be present.
        assert re.search(r"r_ch\s*=\s*CH4_CH_BOND_LENGTH_NM\b", src), (
            "r_ch = CH4_CH_BOND_LENGTH_NM not found — UNIT-04 not applied."
        )

    def test_ch4_geometry_preserves_bond_length(self):
        """_generate_ch4_coordinates must still produce 0.109620 nm C-H bonds."""
        inserter = SoluteInserter(
            config=SoluteConfig(solute_type="CH4", concentration_molar=0.1),
            seed=42,
        )
        coords = inserter._generate_ch4_coordinates()
        assert coords.shape == (5, 3)
        c = coords[0]
        for i, h in enumerate(coords[1:], 1):
            d = float(np.linalg.norm(h - c))
            assert abs(d - 0.109620) < 1e-9, (
                f"C-H{i} bond length {d!r} != 0.109620 (UNIT-04 regression)"
            )


# ══════════════════════════════════════════════════════════════════════════════
# UNIT-05: GROMACS [atomtypes] vs [moleculetype] [atoms] convention
# ══════════════════════════════════════════════════════════════════════════════

class TestUNIT05:
    """UNIT-05: [atomtypes] charge=0.0 placeholder vs [moleculetype] [atoms]
    real ion charge — DIFFERENT fields, NOT duplicates. Clarifying comment
    must be present; no consolidation."""

    def test_ion_atomtypes_charge_is_zero_placeholder(self):
        """ION_ATOMTYPES carries charge=0.0 (GROMACS [atomtypes] convention:
        nonbonded params only; charge column is a placeholder)."""
        for name in ("NA", "CL"):
            params = ION_ATOMTYPES[name]
            # params = (name, anum, mass, charge, ptype, sigma, epsilon)
            charge = params[3]
            assert charge == 0.0, (
                f"ION_ATOMTYPES[{name!r}].charge = {charge!r}, expected 0.0 "
                f"(GROMACS [atomtypes] convention — nonbonded params only). "
                f"If this is non-zero, the [atomtypes] convention was broken."
            )

    def test_real_ion_charges_in_gromacs_ion_export(self):
        """The REAL ion charges (±0.85) live in gromacs_ion_export.py
        (written to [moleculetype] [atoms] section of ion.itp)."""
        assert NA_CHARGE == 0.85
        assert CL_CHARGE == -0.85

    def test_ion_itp_contains_real_charges(self):
        """generate_ion_itp writes the REAL ±0.85 charges to [moleculetype]
        [atoms] (distinct from the [atomtypes] placeholder)."""
        itp = generate_ion_itp(2, 3)
        assert "0.85" in itp, f"Real NA charge 0.85 missing from ion.itp:\n{itp}"
        assert "-0.85" in itp, f"Real CL charge -0.85 missing from ion.itp:\n{itp}"

    def test_clarifying_comment_in_gromacs_writer(self):
        """gromacs_writer.py ION_ATOMTYPES must document the [atomtypes]
        charge=0.0 placeholder convention (UNIT-05 clarifying comment)."""
        assert _ion_atomtypes_has_clarifying_comment(), (
            "ION_ATOMTYPES in gromacs_writer.py is missing the UNIT-05 "
            "clarifying comment explaining the [atomtypes] charge=0.0 "
            "placeholder convention vs [moleculetype] [atoms] real charge."
        )

    def test_clarifying_comment_in_gromacs_ion_export(self):
        """gromacs_ion_export.py NA_CHARGE/CL_CHARGE must cross-reference the
        [moleculetype] [atoms] vs [atomtypes] convention (UNIT-05)."""
        assert _ion_export_has_clarifying_comment(), (
            "NA_CHARGE/CL_CHARGE in gromacs_ion_export.py is missing the "
            "UNIT-05 cross-reference comment to the [atomtypes] convention."
        )

    def test_charges_not_consolidated(self):
        """UNIT-05 decision: the [atomtypes] 0.0 and [atoms] ±0.85 are NOT
        consolidated into a single shared constant (they are different
        fields). ION_ATOMTYPES charge must remain 0.0, NOT reference
        NA_CHARGE/CL_CHARGE."""
        # If someone "consolidated" them, ION_ATOMTYPES would reference
        # NA_CHARGE/CL_CHARGE. Verify it does NOT.
        src = _all_output_sources()
        # Extract the ION_ATOMTYPES block.
        block = re.search(
            r"ION_ATOMTYPES\s*[:=].*?\{[^}]*\}",
            src, re.S,
        )
        assert block is not None
        block_text = block.group(0)
        assert "NA_CHARGE" not in block_text, (
            "UNIT-05 violation: ION_ATOMTYPES references NA_CHARGE — the "
            "[atomtypes] 0.0 placeholder was incorrectly consolidated with "
            "the [moleculetype] [atoms] real charge. These are DIFFERENT "
            "GROMACS fields and MUST NOT be merged."
        )
        assert "CL_CHARGE" not in block_text, (
            "UNIT-05 violation: ION_ATOMTYPES references CL_CHARGE — the "
            "[atomtypes] 0.0 placeholder was incorrectly consolidated with "
            "the [moleculetype] [atoms] real charge."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Byte-equivalence: produced .top/.itp unchanged by the refactor
# ══════════════════════════════════════════════════════════════════════════════

class TestByteEquivalence:
    """The refactor must NOT change any numeric value in the produced output.

    Baseline MD5 captured pre-refactor on a real ice_ih candidate (96 target
    → 128 actual mols, phase_id='ice_ih'):
      - write_top_file  → bb3df33e131a5d18c5f5439eaa0c29b2
      - generate_ion_itp(2,3) → bb6d3d1ec3a5bc97bea20b5a70bee663
    """

    def test_top_byte_equivalence(self, ice_ih_candidate, tmp_path):
        """write_top_file output MD5 must match the pre-refactor baseline."""
        top_path = str(tmp_path / "ice_ih.top")
        write_top_file(ice_ih_candidate, top_path)
        content = Path(top_path).read_text()
        md5 = hashlib.md5(content.encode()).hexdigest()
        assert md5 == TOP_MD5_BASELINE, (
            f"write_top_file output MD5 changed:\n"
            f"  baseline: {TOP_MD5_BASELINE}\n"
            f"  current:  {md5}\n"
            f"UNIT-02/03 refactor must be byte-equivalent. If the candidate "
            f"nmol changed (GenIce2 drift), check the semantic tests "
            f"(TestUNIT02/03) — if those pass, the TIP4P-ICE values are "
            f"correct and only the nmol/phase_id drifted."
        )

    def test_top_contains_expected_tip4p_ice_values(self, ice_ih_candidate, tmp_path):
        """The .top must contain the exact expected TIP4P-ICE [atoms]/
        [settles]/[virtual_sites3] lines (robust to GenIce2 nmol drift)."""
        top_path = str(tmp_path / "ice_ih.top")
        write_top_file(ice_ih_candidate, top_path)
        content = Path(top_path).read_text()
        expected_lines = [
            "   2   HW_ice    1  SOL   HW1     1     0.5897   1.00800",
            "   3   HW_ice    1  SOL   HW2     1     0.5897   1.00800",
            "   4   MW        1  SOL    MW     1    -1.1794   0.00000",
            "  1    1    0.09572  0.15139",
            "   4     1       2       3       1      0.13458335 0.13458335",
        ]
        for line in expected_lines:
            assert line in content, (
                f"Expected TIP4P-ICE line missing from .top:\n  {line!r}\n"
                f"UNIT-02/03 byte-equivalence regression."
            )

    def test_top_comb_rule_2(self, ice_ih_candidate, tmp_path):
        """comb-rule=2 (Lorentz-Berthelot, AMBER/GAFF2) must remain in the
        produced .top (AGENTS.md hard requirement)."""
        top_path = str(tmp_path / "ice_ih.top")
        write_top_file(ice_ih_candidate, top_path)
        content = Path(top_path).read_text()
        # The [defaults] line: "1               2               yes..."
        defaults = re.search(r"^\s*1\s+2\s+yes\s+0\.5\s+0\.8333\s*$", content, re.M)
        assert defaults is not None, (
            f"comb-rule=2 [defaults] line missing from .top:\n{content}"
        )

    def test_ion_itp_byte_equivalence(self):
        """generate_ion_itp(2, 3) MD5 must match the pre-refactor baseline."""
        itp = generate_ion_itp(2, 3)
        md5 = hashlib.md5(itp.encode()).hexdigest()
        assert md5 == ITP_MD5_BASELINE, (
            f"generate_ion_itp output MD5 changed:\n"
            f"  baseline: {ITP_MD5_BASELINE}\n"
            f"  current:  {md5}\n"
            f"UNIT-05 must be a no-value-change refactor."
        )


# ══════════════════════════════════════════════════════════════════════════════
# GROMACS-level byte-equivalence (gmx grompp dry-run)
# ══════════════════════════════════════════════════════════════════════════════

@gmx_skipif
def test_gmx_grompp_constants_refactor(ice_ih_candidate, tmp_path):
    """gmx grompp exits 0 on a real ice_ih export after the constants refactor
    — confirms the topology is still simulation-ready at the GROMACS level
    (byte-equivalence beyond Python string comparison).

    Stages tip4p-ice.itp + a small-cutoff em.mdp (the 96-mol ice_ih cell has a
    ~1.47 nm minimum box vector, too small for the 1.0 nm cutoff in the shared
    tests/em.mdp — so we use a 0.65 nm cutoff here, which fits and still
    exercises the full [atoms]/[settles]/[virtual_sites3] parse path), then
    runs ``gmx grompp -maxwarn 5``. A clean exit (0) means GROMACS successfully
    parsed the topology and the TIP4P-ICE [atoms]/[settles]/[virtual_sites3]
    sections are internally consistent (no value drift introduced by the
    constants extraction).
    """
    from e2e_export_helpers import run_gmx_grompp

    # Custom small-cutoff em.mdp — the ice_ih 96-mol cell min box is ~1.47 nm,
    # so a 0.65 nm cutoff (needs box >= 1.3 nm) fits and exercises the full
    # topology parse. This is a grompp DRY-RUN for topology validation, not a
    # physics-meaningful EM run.
    (tmp_path / "em.mdp").write_text(
        "integrator = steep\n"
        "nsteps = 0\n"
        "emtol  = 100.0\n"
        "emstep = 0.01\n"
        "pbc = xyz\n"
        "cutoff-scheme = Verlet\n"
        "coulombtype   = PME\n"
        "rcoulomb      = 0.65\n"
        "vdwtype       = Cut-off\n"
        "rvdw          = 0.65\n"
        "DispCorr      = EnerPres\n"
        "constraints   = none\n"
    )
    # Stage the bundled tip4p-ice.itp (the .top #includes it).
    tip4p_src = _data_dir() / "tip4p-ice.itp"
    assert tip4p_src.exists(), f"tip4p-ice.itp missing: {tip4p_src}"
    shutil.copy(tip4p_src, tmp_path / "tip4p-ice.itp")

    gro_path = str(tmp_path / "ice_ih.gro")
    top_path = str(tmp_path / "ice_ih.top")
    write_gro_file(ice_ih_candidate, gro_path)
    write_top_file(ice_ih_candidate, top_path)

    exit_code, stderr = run_gmx_grompp(
        tmp_path,
        gro_file="ice_ih.gro",
        top_file="ice_ih.top",
        tpr_file="ice_ih.tpr",
        maxwarn=5,
    )
    assert exit_code == 0, (
        f"gmx grompp failed after constants refactor:\n{stderr}"
    )
