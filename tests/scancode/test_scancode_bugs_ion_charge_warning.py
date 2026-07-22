"""Regression test for ion charge warning with non-neutral custom molecules.

Bug: IonPanel._update_charge_warning() never triggered for non-neutral custom
molecules because get_total_charge() always returned 0.0 (ion pairs are neutral
by design, and custom molecule charge calculation was deferred).

Fix: get_total_charge() now computes custom molecule charge as
molecule_charge * custom_molecule_count when source is "Custom Molecule".
ITPMoleculeInfo now includes a charges field parsed from the [ atoms ] section.
CustomMoleculeStructure now includes a molecule_charge field.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

from quickice.structure_generation.itp_parser import ITPMoleculeInfo, parse_itp_file
from quickice.structure_generation.types import CustomMoleculeStructure


# --- ITP Parser charge extraction tests ---

class TestITPChargeParsing:
    """Tests for charge extraction from ITP [ atoms ] section."""

    def test_itp_info_has_charges_field(self):
        """ITPMoleculeInfo dataclass must have a charges field."""
        info = ITPMoleculeInfo(
            molecule_name="test",
            atom_count=1,
            atom_types=["NA"],
            atom_names=["NA"],
            charges=[0.85],
            has_atomtypes_section=True,
        )
        assert info.charges == [0.85]

    def test_na_single_itp_parses_charge(self):
        """na_single.itp (single Na+ ion) should have charge +0.85."""
        na_itp = Path(__file__).resolve().parents[2] / "quickice" / "data" / "custom" / "test_invalid" / "na_single.itp"
        if not na_itp.exists():
            pytest.skip("na_single.itp data file not found")

        info = parse_itp_file(na_itp)
        assert info.charges == [0.85]
        assert sum(info.charges) == 0.85

    def test_ch4_itp_parses_neutral_charge(self):
        """ch4.itp (methane) should have net charge ~0.0."""
        ch4_itp = Path(__file__).resolve().parents[2] / "quickice" / "data" / "ch4.itp"
        if not ch4_itp.exists():
            pytest.skip("ch4.itp data file not found")

        info = parse_itp_file(ch4_itp)
        assert len(info.charges) == 5
        assert abs(sum(info.charges)) < 0.01  # Neutral molecule

    def test_tip4p_ice_itp_parses_neutral_charge(self):
        """tip4p-ice.itp should have net charge ~0.0."""
        tip4p_itp = Path(__file__).resolve().parents[2] / "quickice" / "data" / "tip4p-ice.itp"
        if not tip4p_itp.exists():
            pytest.skip("tip4p-ice.itp data file not found")

        info = parse_itp_file(tip4p_itp)
        assert len(info.charges) == 4
        assert abs(sum(info.charges)) < 0.01  # Neutral molecule

    def test_itp_with_fewer_columns_defaults_charge_to_zero(self):
        """ITP atoms with <7 columns should default charge to 0.0."""
        import tempfile

        content = """\
[ moleculetype ]
; name  nrexcl
TEST  3

[ atoms ]
;  nr  type  resi  res  atom  cgnr
     1    XX      1    TST    A1     1
     2    XX      1    TST    A2     2
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".itp", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            tmp_path = Path(f.name)
        try:
            info = parse_itp_file(tmp_path)
            assert info.charges == [0.0, 0.0]
        finally:
            tmp_path.unlink()


# --- CustomMoleculeStructure charge propagation tests ---

class TestCustomMoleculeCharge:
    """Tests for molecule_charge field in CustomMoleculeStructure."""

    def test_molecule_charge_default_is_zero(self):
        """CustomMoleculeStructure with default molecule_charge should be 0.0."""
        struct = CustomMoleculeStructure(
            positions=np.zeros((1, 3)),
            atom_names=["NA"],
            cell=np.eye(3) * 5.0,
            molecule_index=[],
            ice_atom_count=0,
            water_atom_count=0,
            custom_molecule_atom_count=1,
            custom_molecule_count=1,
        )
        assert struct.molecule_charge == 0.0

    def test_molecule_charge_propagates(self):
        """CustomMoleculeStructure with molecule_charge=0.85 should preserve it."""
        struct = CustomMoleculeStructure(
            positions=np.zeros((1, 3)),
            atom_names=["NA"],
            cell=np.eye(3) * 5.0,
            molecule_index=[],
            ice_atom_count=0,
            water_atom_count=0,
            custom_molecule_atom_count=1,
            custom_molecule_count=5,
            molecule_charge=0.85,
        )
        assert struct.molecule_charge == 0.85
        total = struct.molecule_charge * struct.custom_molecule_count
        assert total == 4.25

    def test_neutral_molecule_zero_total_charge(self):
        """Neutral custom molecule should have total_charge = 0.0."""
        struct = CustomMoleculeStructure(
            positions=np.zeros((5, 3)),
            atom_names=["C", "H", "H", "H", "H"],
            cell=np.eye(3) * 5.0,
            molecule_index=[],
            ice_atom_count=0,
            water_atom_count=0,
            custom_molecule_atom_count=5,
            custom_molecule_count=10,
            molecule_charge=0.0,
        )
        assert struct.molecule_charge * struct.custom_molecule_count == 0.0


# --- IonPanel charge calculation tests (headless) ---

class TestIonPanelChargeCalculation:
    """Tests for IonPanel.get_total_charge() with custom molecule source.

    Note: These tests create IonPanel without QApplication, so isVisible()
    checks won't work (parent not shown). We test the logic, not Qt visibility.
    """

    def test_get_total_charge_interface_source(self):
        """get_total_charge() should return 0.0 for Interface source."""
        from quickice.gui.ion_panel import IonPanel

        panel = IonPanel.__new__(IonPanel)
        panel._current_source = "Interface"
        panel._custom_molecule_structure = None
        result = IonPanel.get_total_charge(panel)
        assert result == 0.0

    def test_get_total_charge_custom_molecule_nonneutral(self):
        """get_total_charge() should return non-zero for non-neutral custom molecules."""
        from quickice.gui.ion_panel import IonPanel

        panel = IonPanel.__new__(IonPanel)
        panel._current_source = "Custom Molecule"
        panel._custom_molecule_structure = CustomMoleculeStructure(
            positions=np.zeros((1, 3)),
            atom_names=["NA"],
            cell=np.eye(3) * 5.0,
            molecule_index=[],
            ice_atom_count=0,
            water_atom_count=0,
            custom_molecule_atom_count=1,
            custom_molecule_count=5,
            molecule_charge=0.85,
        )
        result = IonPanel.get_total_charge(panel)
        assert result == 4.25

    def test_get_total_charge_custom_molecule_neutral(self):
        """get_total_charge() should return 0.0 for neutral custom molecules."""
        from quickice.gui.ion_panel import IonPanel

        panel = IonPanel.__new__(IonPanel)
        panel._current_source = "Custom Molecule"
        panel._custom_molecule_structure = CustomMoleculeStructure(
            positions=np.zeros((5, 3)),
            atom_names=["C", "H", "H", "H", "H"],
            cell=np.eye(3) * 5.0,
            molecule_index=[],
            ice_atom_count=0,
            water_atom_count=0,
            custom_molecule_atom_count=5,
            custom_molecule_count=10,
            molecule_charge=0.0,
        )
        result = IonPanel.get_total_charge(panel)
        assert result == 0.0

    def test_get_total_charge_solute_source(self):
        """get_total_charge() should return 0.0 for Solute source."""
        from quickice.gui.ion_panel import IonPanel

        panel = IonPanel.__new__(IonPanel)
        panel._current_source = "Solute"
        panel._custom_molecule_structure = None
        result = IonPanel.get_total_charge(panel)
        assert result == 0.0

    def test_get_total_charge_custom_source_no_structure(self):
        """get_total_charge() should return 0.0 when Custom source has no structure."""
        from quickice.gui.ion_panel import IonPanel

        panel = IonPanel.__new__(IonPanel)
        panel._current_source = "Custom Molecule"
        panel._custom_molecule_structure = None
        result = IonPanel.get_total_charge(panel)
        assert result == 0.0

    def test_get_total_charge_negative_molecule_charge(self):
        """get_total_charge() should return negative for anionic molecules."""
        from quickice.gui.ion_panel import IonPanel

        panel = IonPanel.__new__(IonPanel)
        panel._current_source = "Custom Molecule"
        panel._custom_molecule_structure = CustomMoleculeStructure(
            positions=np.zeros((1, 3)),
            atom_names=["CL"],
            cell=np.eye(3) * 5.0,
            molecule_index=[],
            ice_atom_count=0,
            water_atom_count=0,
            custom_molecule_atom_count=1,
            custom_molecule_count=3,
            molecule_charge=-0.85,
        )
        result = IonPanel.get_total_charge(panel)
        assert result == -2.55
