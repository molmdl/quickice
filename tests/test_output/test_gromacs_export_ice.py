"""E2E tests for GROMACSExporter (Tab 0 — Ice).

Tests the simplest exporter to validate the QFileDialog/QMessageBox mock
pattern that all subsequent export tests will follow.

Also validates the 3→4 atom expansion (O,H,H → OW,HW1,HW2,MW) which is
unique to ice structures: the input Candidate has 3 atoms per molecule
but the output .gro file has 4 atoms per molecule (TIP4P-ICE).

Fixtures from conftest.py:
    - ranked_candidate: 1-molecule ice RankedCandidate
    - mock_save_dialog: factory → (save_path, dialog_patch, mb_patch)
    - mock_cancel_dialog: factory → (dialog_patch, mb_patch)
"""

from pathlib import Path

import pytest

from quickice.gui.export import GROMACSExporter


class TestIceGROMACSExporter:
    """End-to-end tests for ice GROMACS export (Tab 0)."""

    def test_export_creates_gro_top_itp(self, ranked_candidate, mock_save_dialog):
        """Export creates .gro, .top, and .itp files in output directory.

        The ITP filename uses the .gro stem (e.g. ice_test.itp),
        NOT the source filename (tip4p-ice.itp).
        """
        save_path, dialog_p, mb_p = mock_save_dialog("ice_test.gro")
        exporter = GROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_gromacs(ranked_candidate, T=195, P=1.36)

        assert result is True
        tmp_path = Path(save_path).parent
        assert (tmp_path / "ice_test.gro").exists()
        assert (tmp_path / "ice_test.top").exists()
        # ITP filename matches .gro stem, NOT "tip4p-ice.itp"
        assert (tmp_path / "ice_test.itp").exists()

    def test_export_cancelled_returns_false(self, ranked_candidate, mock_cancel_dialog):
        """Cancelled QFileDialog returns False without creating files."""
        dialog_p, mb_p = mock_cancel_dialog(module_path="quickice.gui.export")
        exporter = GROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_gromacs(ranked_candidate, T=195, P=1.36)

        assert result is False

    def test_gro_file_has_correct_atom_count(self, ranked_candidate, mock_save_dialog):
        """.gro file contains nmolecules * 4 atoms (TIP4P-ICE expansion).

        For nmolecules=1, expect n_atoms = 1 * 4 = 4.
        The input Candidate has O,H,H (3 atoms) but TIP4P-ICE adds the
        MW virtual site, producing OW,HW1,HW2,MW (4 atoms).
        """
        save_path, dialog_p, mb_p = mock_save_dialog("ice_test.gro")
        exporter = GROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_gromacs(ranked_candidate, T=195, P=1.36)

        assert result is True
        gro_path = Path(save_path)
        lines = gro_path.read_text().splitlines()
        # Line 2 of .gro file (index 1) contains the atom count
        atom_count = int(lines[1].strip())
        assert atom_count == 4  # 1 molecule * 4 atoms (TIP4P-ICE)

    def test_gro_file_has_tip4p_atom_names(self, ranked_candidate, mock_save_dialog):
        """.gro atom names are OW, HW1, HW2, MW (TIP4P-ICE 3→4 expansion).

        The input candidate has O,H,H but the output has OW,HW1,HW2,MW.
        Atom name is at positions 10:15 (0-indexed) in each GRO atom line.
        """
        save_path, dialog_p, mb_p = mock_save_dialog("ice_test.gro")
        exporter = GROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_gromacs(ranked_candidate, T=195, P=1.36)

        assert result is True
        gro_path = Path(save_path)
        lines = gro_path.read_text().splitlines()
        # Lines 3-6 (indices 2-5) are the 4 atoms for 1 molecule
        expected_names = ["OW", "HW1", "HW2", "MW"]
        for i, expected_name in enumerate(expected_names):
            atom_line = lines[2 + i]
            # Atom name is at positions 10:15 (0-indexed) in GRO format
            actual_name = atom_line[10:15].strip()
            assert actual_name == expected_name, (
                f"Atom {i+1}: expected '{expected_name}', "
                f"got '{actual_name}' from line '{atom_line}'"
            )

    def test_top_file_has_molecules_section(self, ranked_candidate, mock_save_dialog):
        """.top file contains [ molecules ] section with SOL count.

        For 1 molecule: expect 'SOL' with count 1.
        """
        save_path, dialog_p, mb_p = mock_save_dialog("ice_test.gro")
        exporter = GROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_gromacs(ranked_candidate, T=195, P=1.36)

        assert result is True
        top_path = Path(save_path).with_suffix(".top")
        content = top_path.read_text()
        # Verify [ molecules ] section exists
        assert "[ molecules ]" in content
        # Verify SOL molecule count matches nmolecules
        nmolecules = ranked_candidate.candidate.nmolecules
        # Match "SOL" followed by whitespace and the count
        # e.g. "SOL          1" or "SOL    1"
        import re
        pattern = rf"SOL\s+{nmolecules}\b"
        assert re.search(pattern, content), (
            f"Expected 'SOL' with count {nmolecules} in [ molecules ] section. "
            f"Content:\n{content}"
        )
