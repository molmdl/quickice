"""Regression test for TIP4P-ICE LJ parameter magnitudes in generated .top files.

Prevents recurrence of Bug P16: sigma was 1000x too small (0.31668e-3 instead of
3.16680e-1 nm) and epsilon was 10^6x too small (0.88216e-6 instead of 8.82110e-1
kJ/mol) in all 6 TOP-writing functions.

References:
    Abascal et al. 2005, DOI: 10.1063/1.1931662
    sigma_O = 3.1668 A = 0.31668 nm
    epsilon_O/k_B = 106.1 K -> 106.1 * 0.00831446 = 0.88211 kJ/mol
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pytest

from quickice.output.gromacs_writer import (
    TIP4P_ICE_OW_EPSILON,
    TIP4P_ICE_OW_SIGMA,
    write_top_file,
    write_interface_top_file,
    write_ion_top_file,
    write_multi_molecule_top_file,
    write_custom_molecule_top_file,
    write_solute_top_file,
)
from quickice.structure_generation.types import (
    Candidate,
    InterfaceStructure,
    IonStructure,
    MoleculeIndex,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_atomtypes(top_text: str) -> dict[str, dict[str, float]]:
    """Parse [atomtypes] section from .top text into {name: {sigma, epsilon}}."""
    atomtypes: dict[str, dict[str, float]] = {}
    in_section = False
    for line in top_text.splitlines():
        stripped = line.strip()
        if stripped == "[ atomtypes ]":
            in_section = True
            continue
        if in_section and stripped.startswith("["):
            # New section — stop parsing
            break
        if in_section and (stripped.startswith(";") or stripped == ""):
            continue
        if in_section:
            parts = stripped.split()
            if len(parts) >= 8:
                name = parts[0]
                try:
                    sigma = float(parts[6])
                    epsilon = float(parts[7])
                    atomtypes[name] = {"sigma": sigma, "epsilon": epsilon}
                except (ValueError, IndexError):
                    continue
    return atomtypes


def _parse_defaults(top_text: str) -> dict:
    """Parse [defaults] section from .top text."""
    defaults = {}
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
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_top(tmp_path):
    """Provide a temporary .top file path."""
    return str(tmp_path / "test.top")


@pytest.fixture
def simple_candidate():
    """Minimal Candidate for write_top_file (ice-only)."""
    positions = np.array([
        [0.0, 0.0, 0.0],   # O
        [0.06, 0.09, 0.0],  # H1
        [-0.06, 0.09, 0.0],  # H2
    ])
    atom_names = ["O", "H", "H"]
    cell = np.eye(3) * 2.0
    return Candidate(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        nmolecules=1,
        phase_id="ice_ih",
        seed=42,
        metadata={},
    )


@pytest.fixture
def simple_interface():
    """Minimal InterfaceStructure for write_interface_top_file."""
    positions = np.zeros((4, 3))
    atom_names = ["OW", "HW1", "HW2", "MW"]
    cell = np.eye(3) * 2.0
    return InterfaceStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        ice_atom_count=4,
        water_atom_count=0,
        ice_nmolecules=1,
        water_nmolecules=0,
        mode="standard",
        report="test interface",
        guest_nmolecules=0,
        guest_atom_count=0,
    )


# ---------------------------------------------------------------------------
# Tests: Module-level constants
# ---------------------------------------------------------------------------

class TestTIP4PIceConstants:
    """Verify module-level LJ constants are physically correct."""

    def test_sigma_magnitude(self):
        """OW sigma must be ~0.317 nm (not 0.000317 nm or 316 nm)."""
        assert 0.01 < TIP4P_ICE_OW_SIGMA < 1.0, (
            f"sigma={TIP4P_ICE_OW_SIGMA} nm is outside physical range [0.01, 1.0] nm"
        )

    def test_sigma_close_to_abascal2005(self):
        """OW sigma must be close to Abascal 2005 value: 0.31668 nm."""
        assert abs(TIP4P_ICE_OW_SIGMA - 0.31668) < 0.001, (
            f"sigma={TIP4P_ICE_OW_SIGMA} deviates from Abascal 2005 value 0.31668 nm"
        )

    def test_epsilon_magnitude(self):
        """OW epsilon must be ~0.882 kJ/mol (not 0.000000882 or 882000)."""
        assert 0.001 < TIP4P_ICE_OW_EPSILON < 10.0, (
            f"epsilon={TIP4P_ICE_OW_EPSILON} kJ/mol is outside physical range [0.001, 10.0]"
        )

    def test_epsilon_close_to_abascal2005(self):
        """OW epsilon must be close to Abascal 2005 value: 0.88211 kJ/mol."""
        assert abs(TIP4P_ICE_OW_EPSILON - 0.88211) < 0.01, (
            f"epsilon={TIP4P_ICE_OW_EPSILON} deviates from Abascal 2005 value 0.88211 kJ/mol"
        )


# ---------------------------------------------------------------------------
# Tests: write_top_file output (ice candidate)
# ---------------------------------------------------------------------------

class TestWriteTopFileLJValues:
    """Regression test: LJ values in write_top_file output."""

    def test_ow_sigma_in_output(self, simple_candidate, tmp_top):
        write_top_file(simple_candidate, tmp_top)
        top_text = Path(tmp_top).read_text()
        atomtypes = _parse_atomtypes(top_text)
        assert "OW_ice" in atomtypes, "OW_ice not found in [atomtypes]"
        sigma = atomtypes["OW_ice"]["sigma"]
        # Must be > 0.01 nm (catches 1000x error: 0.000317 nm)
        # Must be < 1.0 nm (catches unit errors)
        assert 0.01 < sigma < 1.0, f"OW_ice sigma={sigma} nm outside physical range"

    def test_ow_epsilon_in_output(self, simple_candidate, tmp_top):
        write_top_file(simple_candidate, tmp_top)
        top_text = Path(tmp_top).read_text()
        atomtypes = _parse_atomtypes(top_text)
        epsilon = atomtypes["OW_ice"]["epsilon"]
        # Must be > 0.001 kJ/mol (catches 10^6x error: 8.8e-7)
        # Must be < 10.0 kJ/mol (catches unit errors)
        assert 0.001 < epsilon < 10.0, f"OW_ice epsilon={epsilon} kJ/mol outside physical range"

    def test_hw_no_lj(self, simple_candidate, tmp_top):
        """Hydrogen atoms have zero LJ parameters."""
        write_top_file(simple_candidate, tmp_top)
        top_text = Path(tmp_top).read_text()
        atomtypes = _parse_atomtypes(top_text)
        if "HW_ice" in atomtypes:
            assert atomtypes["HW_ice"]["sigma"] == 0.0
            assert atomtypes["HW_ice"]["epsilon"] == 0.0

    def test_defaults_comb_rule_2(self, simple_candidate, tmp_top):
        """comb-rule must be 2 (Lorentz-Berthelot, AMBER/GAFF2 convention)."""
        write_top_file(simple_candidate, tmp_top)
        top_text = Path(tmp_top).read_text()
        defaults = _parse_defaults(top_text)
        assert defaults.get("comb_rule") == 2, (
            f"comb_rule={defaults.get('comb_rule')} must be 2 (Lorentz-Berthelot, AMBER convention)"
        )

    def test_defaults_fudge_values(self, simple_candidate, tmp_top):
        """fudgeLJ=0.5, fudgeQQ=0.8333 (Amber defaults)."""
        write_top_file(simple_candidate, tmp_top)
        top_text = Path(tmp_top).read_text()
        defaults = _parse_defaults(top_text)
        assert abs(defaults.get("fudgeLJ", 0) - 0.5) < 0.001
        assert abs(defaults.get("fudgeQQ", 0) - 0.8333) < 0.001


# ---------------------------------------------------------------------------
# Tests: write_interface_top_file output
# ---------------------------------------------------------------------------

class TestWriteInterfaceTopFileLJValues:
    """Regression test: LJ values in write_interface_top_file output."""

    def test_ow_sigma_in_interface_top(self, simple_interface, tmp_top):
        write_interface_top_file(simple_interface, tmp_top)
        top_text = Path(tmp_top).read_text()
        atomtypes = _parse_atomtypes(top_text)
        assert "OW_ice" in atomtypes
        assert 0.01 < atomtypes["OW_ice"]["sigma"] < 1.0

    def test_ow_epsilon_in_interface_top(self, simple_interface, tmp_top):
        write_interface_top_file(simple_interface, tmp_top)
        top_text = Path(tmp_top).read_text()
        atomtypes = _parse_atomtypes(top_text)
        assert 0.001 < atomtypes["OW_ice"]["epsilon"] < 10.0

    def test_comb_rule_2_in_interface_top(self, simple_interface, tmp_top):
        """comb-rule must be 2 (Lorentz-Berthelot, AMBER/GAFF2 convention)."""
        write_interface_top_file(simple_interface, tmp_top)
        top_text = Path(tmp_top).read_text()
        defaults = _parse_defaults(top_text)
        assert defaults.get("comb_rule") == 2, (
            f"comb_rule={defaults.get('comb_rule')} must be 2 (Lorentz-Berthelot, AMBER convention)"
        )


# ---------------------------------------------------------------------------
# Tests: No hardcoded buggy values remain in source
# ---------------------------------------------------------------------------

class TestNoBuggyHardcodedValues:
    """Verify no traces of the catastrophic exponent errors remain in source."""

    def test_no_31668e_minus3(self):
        """0.31668e-3 (1000x too small sigma) must not appear in gromacs_writer.py."""
        source = Path("quickice/output/gromacs_writer.py").read_text()
        assert "0.31668e-3" not in source, "Buggy sigma value 0.31668e-3 found in source"

    def test_no_88216e_minus6(self):
        """0.88216e-6 (10^6x too small epsilon) must not appear in gromacs_writer.py."""
        source = Path("quickice/output/gromacs_writer.py").read_text()
        assert "0.88216e-6" not in source, "Buggy epsilon value 0.88216e-6 found in source"

    def test_no_comb_rule_1(self):
        """comb-rule 1 must not appear in gromacs_writer.py defaults (must use comb-rule=2 for AMBER convention)."""
        source = Path("quickice/output/gromacs_writer.py").read_text()
        # Check that no line has "1               1" (nbfunc=1 comb-rule=1)
        # or "1  1" patterns in [defaults] sections
        buggy_pattern = re.compile(r'1\s+1\s+yes\s+0\.5\s+0\.8333')
        matches = buggy_pattern.findall(source)
        assert len(matches) == 0, f"Found {len(matches)} lines with comb-rule=1 in defaults"
