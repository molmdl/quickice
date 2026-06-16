"""E2E tests for SoluteGROMACSExporter (Tab 4 — Solute).

Tests the solute exporter with conditional ITP logic:
- Base files: .gro, .top, tip4p-ice.itp, {solute}_liquid.itp (atomtypes commented)
- Guest ITP: copied when interface_structure has guests (guest_nmolecules > 0)
- No guest ITP: when interface_structure has no guests
- Custom molecule ITP: copied when custom_molecule_count > 0 and positions + itp_path exist

SoluteGROMACSExporter is the FIRST exporter that accesses a nested structure
(solute_structure.interface_structure) for guest detection and molecule_index.
If interface_structure is None, the export crashes with AttributeError.
These tests validate that the chain dependency works correctly.

Fixtures from conftest.py:
    - solute_structure: SoluteStructure with CH4 solute + interface_with_ch4_guests
    - simple_interface: 2 ice + 2 water, no guests
    - interface_with_ch4_guests: extends simple_interface with CH4 guests
    - mock_save_dialog: factory -> (save_path, dialog_patch, mb_patch)
"""

from pathlib import Path

import numpy as np
import pytest

from quickice.gui.export import SoluteGROMACSExporter, _detect_guest_type_from_structure
from quickice.structure_generation.types import SoluteStructure, InterfaceStructure, MoleculeIndex
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry


class TestSoluteGROMACSExporter:
    """End-to-end tests for solute GROMACS export (Tab 4)."""

    def test_export_creates_base_files(self, solute_structure, mock_save_dialog):
        """Export creates .gro, .top, tip4p-ice.itp, ch4_liquid.itp, and ch4_hydrate.itp.

        The solute_structure fixture uses interface_with_ch4_guests, which has
        guest_nmolecules=1 and guest_atom_count=5, so the guest ITP (ch4_hydrate.itp)
        should also be copied.
        """
        save_path, dialog_p, mb_p = mock_save_dialog("solute_ch4_1.gro")
        exporter = SoluteGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_solute_gromacs(solute_structure)

        assert result is True
        tmp_path = Path(save_path).parent
        # Base files
        assert (tmp_path / "solute_ch4_1.gro").exists()
        assert (tmp_path / "solute_ch4_1.top").exists()
        assert (tmp_path / "tip4p-ice.itp").exists()
        # Solute liquid ITP
        assert (tmp_path / "ch4_liquid.itp").exists()
        # Guest ITP (interface has CH4 guests)
        assert (tmp_path / "ch4_hydrate.itp").exists()

    def test_solute_itp_has_atomtypes_commented_out(self, solute_structure, mock_save_dialog):
        """Solute liquid ITP has atomtypes section commented out.

        The comment_out_atomtypes_in_itp() function is applied to solute ITP files
        before writing. The output file should contain the QuickIce comment header
        and/or atomtypes lines prefixed with ';'.
        """
        save_path, dialog_p, mb_p = mock_save_dialog("solute_ch4_1.gro")
        exporter = SoluteGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_solute_gromacs(solute_structure)

        assert result is True
        tmp_path = Path(save_path).parent
        itp_content = (tmp_path / "ch4_liquid.itp").read_text()

        # Either the QuickIce modification header is present, or atomtypes lines
        # are commented out with ';'
        assert (
            "Modified for QuickIce" in itp_content
            or "; [ atomtypes ]" in itp_content
        ), "Solute ITP should have atomtypes commented out"

    def test_guest_itp_copied_when_interface_has_guests(
        self, solute_structure, mock_save_dialog
    ):
        """Guest ITP is copied when interface_structure has guests.

        The solute_structure fixture uses interface_with_ch4_guests, which has
        guest_nmolecules=1 and guest_atom_count=5. The exporter detects the guest
        type through interface.molecule_index and copies the hydrate guest ITP.
        The .top file should include a #include directive for the guest ITP.
        """
        save_path, dialog_p, mb_p = mock_save_dialog("solute_ch4_1.gro")
        exporter = SoluteGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_solute_gromacs(solute_structure)

        assert result is True
        tmp_path = Path(save_path).parent
        # Guest ITP should exist in output directory
        assert (tmp_path / "ch4_hydrate.itp").exists()

        # .top file should reference the guest ITP
        top_content = (tmp_path / "solute_ch4_1.top").read_text()
        assert '#include "ch4_hydrate.itp"' in top_content

    def test_no_guest_itp_when_no_guests(self, simple_interface, mock_save_dialog):
        """No guest ITP files when interface_structure has no guests.

        When interface_structure has guest_nmolecules=0 and guest_atom_count=0,
        no guest ITP files should be copied to the output directory.
        """
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")

        solute = SoluteStructure(
            positions=np.array([
                [0.5, 0.5, 0.5],
                [0.55, 0.5, 0.5],
                [0.45, 0.5, 0.5],
                [0.55, 0.45, 0.5],
                [0.45, 0.45, 0.5],
            ]),
            atom_names=["C", "H", "H", "H", "H"],
            cell=simple_interface.cell,
            solute_type="CH4",
            n_molecules=1,
            molecule_indices=[(0, 5)],
            registry=registry,
            interface_structure=simple_interface,  # NO guests
        )

        save_path, dialog_p, mb_p = mock_save_dialog("solute_noguest.gro")
        exporter = SoluteGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_solute_gromacs(solute)

        assert result is True
        tmp_path = Path(save_path).parent
        assert not (tmp_path / "ch4_hydrate.itp").exists()
        assert not (tmp_path / "thf_hydrate.itp").exists()

    def test_custom_itp_copied_when_custom_molecules_present(
        self, interface_with_ch4_guests, mock_save_dialog
    ):
        """Custom molecule ITP is copied when custom_molecule_count > 0.

        The exporter requires ALL THREE conditions for custom ITP copy:
        - custom_molecule_count > 0
        - custom_molecule_positions is not None
        - custom_itp_path exists as a file

        The copied custom ITP should have atomtypes commented out.
        """
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")

        solute = SoluteStructure(
            positions=np.array([
                [0.5, 0.5, 0.5],
                [0.55, 0.5, 0.5],
                [0.45, 0.5, 0.5],
                [0.55, 0.45, 0.5],
                [0.45, 0.45, 0.5],
            ]),
            atom_names=["C", "H", "H", "H", "H"],
            cell=interface_with_ch4_guests.cell,
            solute_type="CH4",
            n_molecules=1,
            molecule_indices=[(0, 5)],
            registry=registry,
            interface_structure=interface_with_ch4_guests,
            custom_molecule_count=1,
            custom_molecule_positions=np.zeros((9, 3)),
            custom_molecule_moleculetype="ETOH",
            custom_itp_path=Path("quickice/data/custom/etoh.itp"),
        )

        save_path, dialog_p, mb_p = mock_save_dialog("solute_custom.gro")
        exporter = SoluteGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_solute_gromacs(solute)

        assert result is True
        tmp_path = Path(save_path).parent
        assert (tmp_path / "etoh.itp").exists()

        # Verify atomtypes are commented out in the copied custom ITP
        custom_itp_content = (tmp_path / "etoh.itp").read_text()
        assert (
            "Modified for QuickIce" in custom_itp_content
            or "; [ atomtypes ]" in custom_itp_content
        ), "Custom ITP should have atomtypes commented out"

    def test_guest_itp_copied_when_guest_nmolecules_zero_but_molecule_index_has_guests(
        self, mock_save_dialog
    ):
        """REGRESSION: Guest ITP is copied even when guest_nmolecules=0.

        Bug: When the workflow chain passes through CustomMoleculeStructure
        (which historically lacked guest_nmolecules), the interface_structure
        on the SoluteStructure may have guest_nmolecules=0 even though
        molecule_index has guest entries and guest_atom_count > 0.
        The exporter should detect guests via molecule_index (consistent with
        write_ion_top_file) so the guest ITP is copied.
        """
        # Create interface with guest_nmolecules=0 but molecule_index has guest
        interface = InterfaceStructure(
            positions=np.zeros((21, 3)),
            atom_names=[
                "OW", "HW1", "HW2", "MW",  # ice mol 1
                "OW", "HW1", "HW2", "MW",  # ice mol 2
                "OW", "HW1", "HW2", "MW",  # water mol 1
                "OW", "HW1", "HW2", "MW",  # water mol 2
                "C", "H", "H", "H", "H",   # CH4 guest
            ],
            cell=np.eye(3) * 3.0,
            ice_atom_count=8,
            water_atom_count=8,
            ice_nmolecules=2,
            water_nmolecules=2,
            mode="slab",
            report="test",
            guest_atom_count=5,
            guest_nmolecules=0,  # BUG CONDITION: 0 but molecule_index has guest!
            molecule_index=[
                MoleculeIndex(0, 4, "ice"),
                MoleculeIndex(4, 4, "ice"),
                MoleculeIndex(8, 4, "water"),
                MoleculeIndex(12, 4, "water"),
                MoleculeIndex(16, 5, "guest"),
            ],
        )

        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")

        solute = SoluteStructure(
            positions=np.array([
                [0.5, 0.5, 0.5],
                [0.55, 0.5, 0.5],
                [0.45, 0.5, 0.5],
                [0.55, 0.45, 0.5],
                [0.45, 0.45, 0.5],
            ]),
            atom_names=["C", "H", "H", "H", "H"],
            cell=interface.cell,
            solute_type="CH4",
            n_molecules=1,
            molecule_indices=[(0, 5)],
            registry=registry,
            interface_structure=interface,
        )

        save_path, dialog_p, mb_p = mock_save_dialog("solute_regression.gro")
        exporter = SoluteGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_solute_gromacs(solute)

        assert result is True
        tmp_path = Path(save_path).parent
        # Guest ITP should exist even when guest_nmolecules=0
        assert (tmp_path / "ch4_hydrate.itp").exists(), (
            "ch4_hydrate.itp should be copied when molecule_index has guest entries, "
            "even if guest_nmolecules=0 (regression from CustomMoleculeStructure chain)"
        )
