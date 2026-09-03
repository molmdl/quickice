"""Headless tests for the custom-molecule residue-name reconciliation (48.3-02 D1).

Scenario (UAT Issue 2 class): a user uploads UNRENAMED ``etoh.gro``
(residue ``MOL``) + ``etoh.itp`` (moleculetype ``etoh``) as a liquid
custom molecule. The CustomMoleculePanel residue-mismatch dialog offers
to use the ITP moleculetype name; on "Yes" (proceed) the flow previously
only updated a label, so the exported ``.top`` said ``etoh`` while the
``.gro`` residues stayed ``MOL`` — a FATAL ``assert_gro_top_consistent``
mismatch (grompp still passed by atom counts, which is exactly the
fixture-sanitization blind spot that let UAT Issue 2 ship).

Fix (48.3-02 D1 = option-a "fix the flow"): CustomMoleculeInserter now
registers the custom molecule under the ITP ``[moleculetype]`` name
(when usable as a GRO residue name, i.e. <=5 chars and not reserved), so
the structure's residues and the emitted ``.top [molecules]`` name AGREE.
User files are never mutated; the dialog's "No" path still blocks
progress, so by insertion time the ITP name is the accepted name.

These tests exercise the REAL panel proceed path (dialog mocked per the
48.3-03 pattern — modal exec() deadlocks headless) and assert the strict
repo gate ``assert_gro_top_consistent`` on the actual export. No gmx
required (the gate parses files only).

Headless: QT_QPA_PLATFORM=offscreen (also session-set in tests/conftest.py
since 48.3-03); panel construction is safe under offscreen.
"""

import sys
import unittest.mock
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from quickice.structure_generation.custom_molecule_inserter import (
    CustomMoleculeInserter,
)
from quickice.structure_generation.itp_parser import parse_itp_file
from quickice.structure_generation.types import CustomMoleculeConfig, InterfaceStructure

from tests.e2e_export_helpers import (
    assert_gro_top_consistent,
    parse_gro_residue_names,
    parse_top_molecules,
)

DATA_DIR = Path("quickice/data/custom")
ETOH_GRO = DATA_DIR / "etoh.gro"  # residue name: MOL (generic placeholder)
ETOH_ITP = DATA_DIR / "etoh.itp"  # [moleculetype] name: etoh


@pytest.fixture
def panel(monkeypatch):
    """Provide a headless CustomMoleculePanel (offscreen pattern per
    tests/test_hydrate_panel.py:51-57)."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    if not QApplication.instance():
        QApplication(sys.argv)
    from quickice.gui.custom_molecule_panel import CustomMoleculePanel

    return CustomMoleculePanel()


@pytest.fixture
def mock_interface() -> InterfaceStructure:
    """Small mock InterfaceStructure with an ice region and a liquid region.

    Mirrors the helper in tests/test_custom_molecule_panel_34_6.py.
    """
    n_ice, n_water = 30, 60
    positions = np.zeros((n_ice + n_water, 3))
    positions[:n_ice] = np.random.rand(n_ice, 3) * 2.0
    positions[n_ice:] = np.random.rand(n_water, 3)
    positions[n_ice:, 2] = positions[n_ice:, 2] * 1.5 + 2.0  # liquid Z in [2, 3.5]
    return InterfaceStructure(
        positions=positions,
        atom_names=["O", "H", "H"] * ((n_ice + n_water) // 3),
        cell=np.diag([10.0, 10.0, 6.0]),
        ice_atom_count=n_ice,
        water_atom_count=n_water,
        guest_atom_count=0,
        ice_nmolecules=n_ice // 3,
        water_nmolecules=n_water // 3,
        mode="slab",
        report="Mock interface for reconciliation test",
    )


class TestResidueMismatchProceedPath:
    """The dialog proceed path must yield internally consistent exports."""

    def test_proceed_path_export_passes_gro_top_consistent(
        self, panel, mock_interface, tmp_path
    ):
        """Yes on the MOL-vs-etoh dialog -> export passes assert_gro_top_consistent.

        Full proceed flow with the RAW unrenamed fixtures (the exact UAT
        Issue 2 input): upload -> validate (dialog offered, "Yes") ->
        get_configuration() -> CustomMoleculeInserter.place_random ->
        write .gro + .top -> strict consistency gate.

        Before the 48.3-02 fix this exported .gro residues "MOL" with
        .top [molecules] "etoh" and FAILED this gate.
        """
        assert ETOH_GRO.exists() and ETOH_ITP.exists()

        # Upload both files (attributes set directly — QFileDialog is modal;
        # same pattern as tests/test_custom_molecule_panel_34_6.py)
        panel.gro_path = ETOH_GRO
        panel.itp_path = ETOH_ITP
        panel.itp_info = parse_itp_file(ETOH_ITP)

        # Validate: the mismatch dialog MUST be offered; user clicks "Yes".
        with unittest.mock.patch(
            "quickice.gui.custom_molecule_panel.QMessageBox.question",
            return_value=QMessageBox.Yes,
        ) as mock_question:
            panel._validate_files()

        assert mock_question.called, (
            "Residue mismatch dialog (QMessageBox.question) should have been "
            "offered for MOL vs etoh"
        )
        assert panel.validation_result is not None
        assert panel.validation_result.is_valid, panel.validation_result.errors
        assert panel.generate_button.isEnabled(), (
            "Proceed path should enable generation"
        )

        # The dialog offered the ITP moleculetype name "etoh"
        assert panel.validation_result.itp_residue_name == "etoh"
        assert panel.validation_result.gro_residue_name == "MOL"

        # Proceed: build the config from the panel (Random / By Count, 1 molecule)
        panel.molecule_count_spin.setValue(1)
        config = panel.get_configuration()
        assert isinstance(config, CustomMoleculeConfig)
        assert config.molecule_count == 1

        # Insert (fresh registry per run, same as CustomMoleculeWorker)
        inserter = CustomMoleculeInserter(config)
        result = inserter.place_random(mock_interface, 1)

        # THE FIX: the structure carries the accepted ITP moleculetype name
        assert result.moleculetype_name == "etoh", (
            f"Proceed path should register the ITP moleculetype name 'etoh', "
            f"got '{result.moleculetype_name}' (pre-48.3-02 this was 'MOL')"
        )

        # Export .gro + .top through the real writers
        gro_path = tmp_path / "custom_system.gro"
        top_path = tmp_path / "custom_system.top"
        from quickice.output.gromacs_writer import (
            write_custom_molecule_gro_file,
            write_custom_molecule_top_file,
        )

        write_custom_molecule_gro_file(result, str(gro_path))
        write_custom_molecule_top_file(result, str(top_path))

        # STRICT gate: .gro residues and .top [molecules] must agree
        assert_gro_top_consistent(str(gro_path), str(top_path))

        # Strict DIRECT match (not the case-insensitive fallback):
        # the .top name appears verbatim as a .gro residue name.
        top_molecules = parse_top_molecules(str(top_path))
        gro_residues = set(parse_gro_residue_names(str(gro_path)))
        assert "etoh" in top_molecules, (
            f".top [molecules] should contain 'etoh', got {top_molecules}"
        )
        assert "etoh" in gro_residues, (
            f".gro residues should contain 'etoh' (verbatim match with .top), "
            f"got {sorted(gro_residues)} — a MOL-vs-etoh divergence here is "
            f"the UAT Issue 2 bug class this test guards against"
        )
        assert "MOL" not in gro_residues, (
            f"The pre-fix placeholder residue 'MOL' must not appear in .gro, "
            f"got {sorted(gro_residues)}"
        )
        assert top_molecules["etoh"] == result.custom_molecule_count

    def test_reject_path_blocks_progress(self, panel):
        """"No" on the mismatch dialog still blocks generation.

        This is what makes the inserter's unconditional adoption of the ITP
        name sound: insertion is unreachable unless the user accepted the
        ITP name (Yes) or the names already matched.
        """
        panel.gro_path = ETOH_GRO
        panel.itp_path = ETOH_ITP
        panel.itp_info = parse_itp_file(ETOH_ITP)

        with unittest.mock.patch(
            "quickice.gui.custom_molecule_panel.QMessageBox.question",
            return_value=QMessageBox.No,
        ) as mock_question:
            panel._validate_files()

        assert mock_question.called, "Dialog should have been offered"
        assert not panel.generate_button.isEnabled(), (
            "Reject path must keep generation disabled until files match"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
