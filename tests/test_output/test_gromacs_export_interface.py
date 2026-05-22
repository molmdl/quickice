"""E2E tests for InterfaceGROMACSExporter (Tab 2 — Interface).

Tests the interface exporter with conditional guest ITP logic:
- No guests → no guest ITP file (only tip4p-ice.itp)
- CH4 guests → ch4_hydrate.itp copied
- THF guests → thf_hydrate.itp copied
- Cancelled dialog → False

The interface exporter is the GATEWAY for the chain dependency — Tab 3 (Custom),
Tab 4 (Solute), and Tab 5 (Ion) all depend on InterfaceStructure. Testing the
guest detection logic here validates the pattern used by all downstream exporters.

Key difference from Ice exporter:
- Ice: ITP named {stem}.itp (stem from .gro filename)
- Interface: Water ITP always named tip4p-ice.itp (hardcoded)
- Guest ITP named {guest_type}_hydrate.itp (e.g., ch4_hydrate.itp)

Fixtures from conftest.py:
    - simple_interface: 2 ice + 2 water, no guests
    - interface_with_ch4_guests: extends simple_interface with CH4 guests
    - interface_with_thf_guests: variant with THF guests
    - mock_save_dialog: factory -> (save_path, dialog_patch, mb_patch)
    - mock_cancel_dialog: factory -> (dialog_patch, mb_patch)
"""

from pathlib import Path

import pytest

from quickice.gui.export import InterfaceGROMACSExporter


class TestInterfaceGROMACSExporter:
    """End-to-end tests for interface GROMACS export (Tab 2)."""

    def test_export_no_guests_creates_files(self, simple_interface, mock_save_dialog):
        """Export creates .gro, .top, and tip4p-ice.itp files.

        With no guests, only the water ITP (tip4p-ice.itp) is copied.
        No guest ITP (ch4_hydrate.itp) should exist.
        """
        save_path, dialog_p, mb_p = mock_save_dialog("interface_slab.gro")
        exporter = InterfaceGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_interface_gromacs(simple_interface)

        assert result is True
        tmp_path = Path(save_path).parent
        assert (tmp_path / "interface_slab.gro").exists()
        assert (tmp_path / "interface_slab.top").exists()
        assert (tmp_path / "tip4p-ice.itp").exists()
        # No guests → no guest ITP file
        assert not (tmp_path / "ch4_hydrate.itp").exists()

    def test_export_cancelled_returns_false(self, simple_interface, mock_cancel_dialog):
        """Cancelled QFileDialog returns False without creating files."""
        dialog_p, mb_p = mock_cancel_dialog(module_path="quickice.gui.export")
        exporter = InterfaceGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_interface_gromacs(simple_interface)

        assert result is False

    def test_export_with_ch4_guests_creates_guest_itp(
        self, interface_with_ch4_guests, mock_save_dialog
    ):
        """CH4 guests cause ch4_hydrate.itp to be copied alongside tip4p-ice.itp.

        The guest detection logic requires BOTH guest_nmolecules > 0 AND
        guest_atom_count > 0 to trigger the guest ITP copy.
        """
        save_path, dialog_p, mb_p = mock_save_dialog("iface_ch4.gro")
        exporter = InterfaceGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_interface_gromacs(interface_with_ch4_guests)

        assert result is True
        tmp_path = Path(save_path).parent
        assert (tmp_path / "iface_ch4.gro").exists()
        assert (tmp_path / "iface_ch4.top").exists()
        assert (tmp_path / "tip4p-ice.itp").exists()
        assert (tmp_path / "ch4_hydrate.itp").exists()

        # Verify ch4_hydrate.itp contains [ moleculetype ] section
        ch4_itp = (tmp_path / "ch4_hydrate.itp").read_text()
        assert "[ moleculetype ]" in ch4_itp

    def test_export_with_thf_guests_creates_guest_itp(
        self, interface_with_thf_guests, mock_save_dialog
    ):
        """THF guests cause thf_hydrate.itp to be copied alongside tip4p-ice.itp.

        The guest type is detected from atom names (THF has O and CA/CB atoms).
        """
        save_path, dialog_p, mb_p = mock_save_dialog("iface_thf.gro")
        exporter = InterfaceGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_interface_gromacs(interface_with_thf_guests)

        assert result is True
        tmp_path = Path(save_path).parent
        assert (tmp_path / "iface_thf.gro").exists()
        assert (tmp_path / "iface_thf.top").exists()
        assert (tmp_path / "tip4p-ice.itp").exists()
        assert (tmp_path / "thf_hydrate.itp").exists()

    def test_no_guest_itp_when_guest_count_zero(self, simple_interface, mock_save_dialog):
        """When guest_atom_count=0 and guest_nmolecules=0, no guest ITPs are copied.

        The output directory should contain only: .gro, .top, tip4p-ice.itp.
        Neither ch4_hydrate.itp nor thf_hydrate.itp should exist.
        """
        save_path, dialog_p, mb_p = mock_save_dialog("interface_slab.gro")
        exporter = InterfaceGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_interface_gromacs(simple_interface)

        assert result is True
        tmp_path = Path(save_path).parent

        # Expected files
        assert (tmp_path / "interface_slab.gro").exists()
        assert (tmp_path / "interface_slab.top").exists()
        assert (tmp_path / "tip4p-ice.itp").exists()

        # Guest ITP files must NOT exist
        assert not (tmp_path / "ch4_hydrate.itp").exists()
        assert not (tmp_path / "thf_hydrate.itp").exists()

    def test_gro_file_has_ice_and_water_atoms(self, simple_interface, mock_save_dialog):
        """.gro file has correct atom count after 3→4 expansion.

        simple_interface has:
        - 2 ice molecules (3 atoms each → expanded to 4 atoms each = 8)
        - 2 water molecules (already 4 atoms each = 8)
        - Total: 2*4 (ice expanded) + 2*4 (water) = 16 atoms

        Ice molecules are expanded from 3→4 atoms at write time
        (O,H,H → OW,HW1,HW2,MW) by write_interface_gro_file.
        Water molecules are already 4 atoms (OW,HW1,HW2,MW).
        """
        save_path, dialog_p, mb_p = mock_save_dialog("interface_slab.gro")
        exporter = InterfaceGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_interface_gromacs(simple_interface)

        assert result is True
        gro_path = Path(save_path)
        lines = gro_path.read_text().splitlines()
        # Line 2 of .gro file (index 1) contains the atom count
        atom_count = int(lines[1].strip())
        # 2 ice * 4 atoms (expanded) + 2 water * 4 atoms = 16
        assert atom_count == 16
