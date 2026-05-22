"""E2E tests for CustomMoleculeGROMACSExporter (Tab 3 — Custom Molecule).

Tests the custom-molecule-specific GROMACS exporter which differs from other
exporters in two key ways:

1. ITP modification: The custom .itp file is read, processed through
   comment_out_atomtypes_in_itp(), and written to the output directory
   with [ atomtypes ] section commented out. The source file is NOT modified.
2. itp_path must point to an existing file: The exporter calls
   custom_structure.itp_path.read_text() directly (line 221 of export.py),
   so itp_path must be a real Path pointing to an existing file.

The custom exporter also has conditional guest ITP logic: if
guest_atom_count > 0 AND molecule_index has mol_type="guest" entries,
a guest ITP (ch4_hydrate.itp or thf_hydrate.itp) is copied to output.

Output files:
    - custom_etoh.gro     (GROMACS coordinates)
    - custom_etoh.top     (GROMACS topology)
    - tip4p-ice.itp       (water ITP, always copied)
    - etoh.itp            (custom ITP, with atomtypes commented out)
    - ch4_hydrate.itp     (guest ITP, only if guests present)

Fixtures from conftest.py:
    - custom_structure: CustomMoleculeStructure with etoh.itp, no guests
    - mock_save_dialog: factory -> (save_path, dialog_patch, mb_patch)
    - mock_cancel_dialog: factory -> (dialog_patch, mb_patch)
"""

from pathlib import Path

import numpy as np
import pytest

from quickice.gui.export import CustomMoleculeGROMACSExporter
from quickice.structure_generation.types import (
    CustomMoleculeStructure,
    MoleculeIndex,
)


class TestCustomMoleculeGROMACSExporter:
    """End-to-end tests for custom molecule GROMACS export (Tab 3)."""

    def test_export_creates_all_files(self, custom_structure, mock_save_dialog):
        """Export creates .gro, .top, tip4p-ice.itp, and custom ITP files.

        The custom ITP keeps its original name (etoh.itp) in the output
        directory, not a stem-based name. The water ITP is always named
        tip4p-ice.itp (same as interface/hydrate exporters).
        """
        save_path, dialog_p, mb_p = mock_save_dialog("custom_etoh.gro")
        exporter = CustomMoleculeGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_custom_molecule_gromacs(custom_structure)

        assert result is True
        tmp_path = Path(save_path).parent
        assert (tmp_path / "custom_etoh.gro").exists()
        assert (tmp_path / "custom_etoh.top").exists()
        assert (tmp_path / "tip4p-ice.itp").exists()
        # Custom ITP keeps its original filename (etoh.itp)
        assert (tmp_path / "etoh.itp").exists()

    def test_custom_itp_has_atomtypes_commented_out(
        self, custom_structure, mock_save_dialog
    ):
        """comment_out_atomtypes_in_itp() comments out [atomtypes] section.

        The output etoh.itp must have:
        - "; Modified for QuickIce: [atomtypes] commented" header
        - "; [ atomtypes ]" (commented section header)
        - Data lines prefixed with "; "

        The ORIGINAL etoh.itp source file must remain UNCHANGED
        (read-only access, no modification).
        """
        save_path, dialog_p, mb_p = mock_save_dialog("custom_etoh.gro")
        exporter = CustomMoleculeGROMACSExporter(parent_widget=None)

        # Read the original file BEFORE export to verify it stays unchanged
        original_itp_path = Path("quickice/data/custom/etoh.itp")
        original_content_before = original_itp_path.read_text()

        with dialog_p, mb_p:
            result = exporter.export_custom_molecule_gromacs(custom_structure)

        assert result is True
        tmp_path = Path(save_path).parent

        # Read the output etoh.itp
        output_itp = tmp_path / "etoh.itp"
        assert output_itp.exists()
        output_content = output_itp.read_text()

        # The output must have the atomtypes section commented out
        # The comment_out_atomtypes_in_itp() function adds:
        # 1. "; Modified for QuickIce: [atomtypes] commented - types defined in main .top file"
        # 2. "; [ atomtypes ]" (commented header)
        # 3. Data lines prefixed with "; "
        assert "; Modified for QuickIce: [atomtypes] commented" in output_content
        assert "; [ atomtypes ]" in output_content

        # Data lines in atomtypes section should be prefixed with "; "
        # Original has: "hc           1     1.007941" etc.
        # Modified should have: "; hc           1     1.007941" etc.
        # Check that at least one atomtype data line is commented
        assert "; hc" in output_content or "; c3" in output_content

        # Verify the ORIGINAL source file is NOT modified
        original_content_after = original_itp_path.read_text()
        assert original_content_before == original_content_after, (
            "Original etoh.itp source file was modified — "
            "exporter should only READ the source, never modify it"
        )

        # Also verify the source still has the unmodified [ atomtypes ] section
        assert "[ atomtypes ]" in original_content_after

    def test_tip4p_ice_itp_copied(self, custom_structure, mock_save_dialog):
        """tip4p-ice.itp is copied to output directory with [ moleculetype ] section.

        The water ITP is always named tip4p-ice.itp (not stem-based)
        and is copied (not generated) from the bundled data directory.
        """
        save_path, dialog_p, mb_p = mock_save_dialog("custom_etoh.gro")
        exporter = CustomMoleculeGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_custom_molecule_gromacs(custom_structure)

        assert result is True
        tmp_path = Path(save_path).parent
        water_itp = tmp_path / "tip4p-ice.itp"
        assert water_itp.exists()

        content = water_itp.read_text()
        assert "[ moleculetype ]" in content

    def test_export_with_guests_creates_guest_itp(self, simple_interface, mock_save_dialog):
        """Guest ITP is copied when guest_atom_count > 0 and molecule_index has guest entries.

        The exporter requires BOTH:
        - custom_structure.guest_atom_count > 0
        - sum(1 for m in molecule_index if m.mol_type == "guest") > 0

        When both conditions are met, detect_guest_type_from_atoms()
        determines the guest type and the corresponding
        {guest_type}_hydrate.itp file is copied.
        """
        # Build a CustomMoleculeStructure with CH4 guests
        # Atom ordering: ice (6) + water (8) + guest (5 CH4) + custom (9 ethanol)
        # This matches the exporter's expectation that guest atoms start at
        # ice_atom_count + water_atom_count

        # CH4 guest positions (5 atoms: C, H, H, H, H)
        guest_positions = np.array([
            [1.5, 1.0, 2.5],
            [1.55, 1.02, 2.5],
            [1.48, 1.02, 2.5],
            [1.50, 1.05, 2.5],
            [1.50, 0.98, 2.5],
        ])

        # Ethanol positions (9 atoms)
        custom_positions = np.zeros((9, 3))
        for i in range(9):
            custom_positions[i] = [1.8 + 0.02 * i, 1.0, 2.5]

        # Assemble: ice + water + guest + custom
        positions = np.vstack([
            simple_interface.positions,
            guest_positions,
            custom_positions,
        ])

        atom_names = (
            simple_interface.atom_names
            + ["C", "H", "H", "H", "H"]   # CH4 guest
            + ["H", "C", "H", "H", "C", "H", "H", "O", "H"]  # ethanol
        )

        molecule_index = simple_interface.molecule_index + [
            MoleculeIndex(14, 5, "guest"),   # CH4 at position 14
            MoleculeIndex(19, 9, "custom"),   # ethanol at position 19
        ]

        itp_path = Path("quickice/data/custom/etoh.itp")

        custom_with_guests = CustomMoleculeStructure(
            positions=positions,
            atom_names=atom_names,
            cell=simple_interface.cell.copy(),
            molecule_index=molecule_index,
            ice_atom_count=6,
            water_atom_count=8,
            custom_molecule_atom_count=9,
            guest_atom_count=5,
            moleculetype_name="ETOH",
            itp_path=itp_path,
            custom_molecule_count=1,
            interface_structure=simple_interface,
        )

        save_path, dialog_p, mb_p = mock_save_dialog("custom_with_ch4.gro")
        exporter = CustomMoleculeGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_custom_molecule_gromacs(custom_with_guests)

        assert result is True
        tmp_path = Path(save_path).parent

        # Expected files (including guest ITP)
        assert (tmp_path / "custom_with_ch4.gro").exists()
        assert (tmp_path / "custom_with_ch4.top").exists()
        assert (tmp_path / "tip4p-ice.itp").exists()
        assert (tmp_path / "etoh.itp").exists()
        # Guest ITP for CH4 must exist
        assert (tmp_path / "ch4_hydrate.itp").exists()

    def test_export_no_guests_no_guest_itp(
        self, custom_structure, mock_save_dialog
    ):
        """When guest_atom_count=0, no guest ITP files are in output directory.

        The custom_structure fixture has guest_atom_count=0 and no
        mol_type="guest" entries in molecule_index. The output should
        only contain: .gro, .top, tip4p-ice.itp, etoh.itp.
        Neither ch4_hydrate.itp nor thf_hydrate.itp should exist.
        """
        save_path, dialog_p, mb_p = mock_save_dialog("custom_etoh.gro")
        exporter = CustomMoleculeGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_custom_molecule_gromacs(custom_structure)

        assert result is True
        tmp_path = Path(save_path).parent

        # Expected files
        assert (tmp_path / "custom_etoh.gro").exists()
        assert (tmp_path / "custom_etoh.top").exists()
        assert (tmp_path / "tip4p-ice.itp").exists()
        assert (tmp_path / "etoh.itp").exists()

        # Guest ITP files must NOT exist
        assert not (tmp_path / "ch4_hydrate.itp").exists()
        assert not (tmp_path / "thf_hydrate.itp").exists()
