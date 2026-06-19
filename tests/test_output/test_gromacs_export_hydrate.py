"""E2E tests for HydrateGROMACSExporter (Tab 1 — Hydrate).

Tests the hydrate-specific GROMACS exporter which differs from all other
exporters in two key ways:

1. Mock path: QFileDialog is in quickice.gui.hydrate_export (NOT quickice.gui.export)
2. Method signature: export_hydrate(structure, config) takes a HydrateConfig argument

The hydrate exporter uses write_multi_molecule_gro_file and
write_multi_molecule_top_file (multi-molecule writers), and the
MoleculetypeRegistry produces _H suffix names for hydrate guests
(e.g. CH4 → CH4_H).

Water ITP is always "tip4p-ice.itp" (not stem-based like Ice exporter).
Guest ITP uses its original filename (e.g. ch4_hydrate.itp).

Fixtures from conftest.py:
    - simple_hydrate_structure: 2 water + 1 CH4 guest HydrateStructure
    - simple_hydrate_config: minimal HydrateConfig (sI, ch4, 1x1x1)
    - mock_hydrate_save_dialog: factory → (save_path, dialog_patch, mb_patch)
    - mock_cancel_dialog: factory → (dialog_patch, mb_patch)
"""

import sys
from pathlib import Path

import pytest

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quickice.gui.hydrate_export import HydrateGROMACSExporter

from e2e_export_helpers import (
    parse_gro_residue_names,
    parse_gro_atom_count,
    parse_top_molecules,
    assert_gro_top_consistent,
)


class TestHydrateGROMACSExporter:
    """End-to-end tests for hydrate GROMACS export (Tab 1)."""

    def test_export_creates_all_files(
        self, simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog
    ):
        """Export creates .gro, .top, tip4p-ice.itp, and guest .itp files.

        Unlike Ice exporter, the water ITP is always named "tip4p-ice.itp"
        (not stem-based), and the guest ITP uses its original name
        (ch4_hydrate.itp).
        """
        save_path, dialog_p, mb_p = mock_hydrate_save_dialog("hydrate_test.gro")
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                simple_hydrate_structure, simple_hydrate_config
            )

        assert result is True
        tmp_path = Path(save_path).parent
        assert (tmp_path / "hydrate_test.gro").exists()
        assert (tmp_path / "hydrate_test.top").exists()
        assert (tmp_path / "tip4p-ice.itp").exists()
        assert (tmp_path / "ch4_hydrate.itp").exists()

    def test_export_cancelled_returns_false(
        self, simple_hydrate_structure, simple_hydrate_config, mock_cancel_dialog
    ):
        """Cancelled QFileDialog returns False.

        This test validates the CRITICAL mock path difference:
        HydrateGROMACSExporter is in quickice.gui.hydrate_export,
        NOT quickice.gui.export. Using the wrong path would cause
        the real QFileDialog to appear (hanging the test).
        """
        dialog_p, mb_p = mock_cancel_dialog(
            module_path="quickice.gui.hydrate_export"
        )
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                simple_hydrate_structure, simple_hydrate_config
            )

        assert result is False

    def test_guest_itp_copied(
        self, simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog
    ):
        """Guest ITP file (ch4_hydrate.itp) is copied to output directory.

        The copied ITP file must contain a [ moleculetype ] section
        with the CH4_H suffix used for hydrate cage guests.
        """
        save_path, dialog_p, mb_p = mock_hydrate_save_dialog("hydrate_test.gro")
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                simple_hydrate_structure, simple_hydrate_config
            )

        assert result is True
        tmp_path = Path(save_path).parent
        guest_itp = tmp_path / "ch4_hydrate.itp"
        assert guest_itp.exists()

        content = guest_itp.read_text()
        assert "[ moleculetype ]" in content

    def test_top_file_references_guest_itp(
        self, simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog
    ):
        """.top file references the guest ITP and uses MoleculetypeRegistry _H suffix.

        The .top file must:
        - Include #include "ch4_hydrate.itp" (guest ITP reference)
        - Use CH4_H in the [ molecules ] section (registry-registered name
          for hydrate guest, NOT the plain "CH4" name)
        """
        save_path, dialog_p, mb_p = mock_hydrate_save_dialog("hydrate_test.gro")
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                simple_hydrate_structure, simple_hydrate_config
            )

        assert result is True
        top_path = Path(save_path).with_suffix(".top")
        content = top_path.read_text()

        # The .top must include the guest ITP file
        assert '#include "ch4_hydrate.itp"' in content

        # The [ molecules ] section must use CH4_H (registry suffix)
        assert "CH4_H" in content

    def test_top_file_references_tip4p_ice(
        self, simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog
    ):
        """.top file references tip4p-ice.itp and includes SOL water molecule count.

        The .top file must:
        - Include #include "tip4p-ice.itp"
        - Use SOL with the correct water molecule count in [ molecules ]
        """
        save_path, dialog_p, mb_p = mock_hydrate_save_dialog("hydrate_test.gro")
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                simple_hydrate_structure, simple_hydrate_config
            )

        assert result is True
        top_path = Path(save_path).with_suffix(".top")
        content = top_path.read_text()

        # The .top must include the TIP4P-ICE ITP
        assert '#include "tip4p-ice.itp"' in content

        # The [ molecules ] section must have SOL with water molecule count
        import re

        water_count = simple_hydrate_structure.water_count
        pattern = rf"SOL\s+{water_count}\b"
        assert re.search(pattern, content), (
            f"Expected 'SOL' with count {water_count} in [ molecules ] section. "
            f"Content:\n{content}"
        )

    def test_gro_file_guest_residue_name_has_h_suffix(
        self, simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog
    ):
        """.gro file uses CH4_H residue name for hydrate cage guests.

        The .gro file residue names MUST match the .top [ molecules ] section
        and the guest .itp [ moleculetype ] name. For hydrate guests, this
        means the _H suffix (e.g. "CH4_H", not "CH4").

        This is critical because GROMACS matches .gro residue names against
        .top [ molecules ] entries — a mismatch causes a fatal error.
        """
        save_path, dialog_p, mb_p = mock_hydrate_save_dialog("hydrate_test.gro")
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                simple_hydrate_structure, simple_hydrate_config
            )

        assert result is True
        gro_path = Path(save_path)
        content = gro_path.read_text()

        # The .gro must have CH4_H as residue name for hydrate cage guests
        # (NOT plain "CH4" which would mismatch the .top [ molecules ] entry)
        assert "CH4_H" in content, (
            f"Expected 'CH4_H' residue name in .gro file for hydrate guest. "
            f"Content:\n{content}"
        )

        # Verify the plain "CH4" residue name (without _H) does NOT appear
        # in residue name columns (5-char field at positions 5-10 in each line)
        # Check that no line has "  CH4" as residue name (5-char padded)
        for line in content.splitlines()[2:]:  # Skip title and atom count
            if line and not line.startswith("#") and len(line) >= 10:
                res_name_field = line[5:10].strip()
                if res_name_field == "CH4":
                    pytest.fail(
                        f"Found plain 'CH4' residue name in .gro file (should be 'CH4_H'). "
                        f"Line: {line!r}"
                    )

    def test_gro_top_cross_validation(
        self, simple_hydrate_structure, simple_hydrate_config, mock_hydrate_save_dialog
    ):
        """Cross-validate .gro and .top consistency for hydrate export.

        Uses assert_gro_top_consistent() which checks:
        1. GRO header atom count == actual atom lines
        2. Every molecule in .top [molecules] appears in .gro residues

        This catches the _H suffix bug: if .gro uses "CH4" but .top
        lists "CH4_H", GROMACS fatal-errors on the mismatch.
        """
        save_path, dialog_p, mb_p = mock_hydrate_save_dialog("hydrate_xval.gro")
        exporter = HydrateGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_hydrate(
                simple_hydrate_structure, simple_hydrate_config
            )

        assert result is True
        gro_path = save_path
        top_path = str(Path(save_path).with_suffix(".top"))

        # Run cross-validation
        assert_gro_top_consistent(gro_path, top_path)
