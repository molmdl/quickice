"""GUI tests for the HydratePanel per-cage guest+occupancy rows (Phase 42-06).

Verifies the per-cage-type row rendering driven by the selected lattice's
``cage_type_map`` and the ``get_configuration`` round-trip into
``HydrateConfig.cage_guest_assignments``:

- sI -> 2 rows (small + large)
- sH -> 3 rows (small + medium + large)
- c0te (filled ice) -> 1 row (small)
- sTprime (water-only) -> 0 rows
- get_configuration builds cage_guest_assignments from the per-cage rows
- Changing the lattice rebuilds the rows (no stale widgets)

Tests run headless via ``QT_QPA_PLATFORM=offscreen`` (monkeypatched) so they
work on machines without a display. Follows the singleton-QApplication pattern
from tests/test_custom_molecule_panel_34_6.py.
"""

import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from quickice.gui.hydrate_panel import HydratePanel


def _select_lattice(panel: HydratePanel, lattice_id: str) -> None:
    """Select the given lattice id in the panel's lattice combo."""
    idx = panel.lattice_combo.findData(lattice_id)
    assert idx >= 0, f"lattice {lattice_id!r} not in combo"
    panel.lattice_combo.setCurrentIndex(idx)


def _set_guest(panel: HydratePanel, cage_key: str, guest_id: str) -> None:
    """Select the given guest id in a per-cage row's combo."""
    combo = panel._cage_guest_combos[cage_key]
    idx = combo.findData(guest_id)
    assert idx >= 0, f"guest {guest_id!r} not in cage {cage_key!r} combo"
    combo.setCurrentIndex(idx)


def _set_occupancy(panel: HydratePanel, cage_key: str, value: float) -> None:
    """Set the occupancy spinbox value for a per-cage row."""
    panel._cage_occupancy_spins[cage_key].setValue(value)


class TestHydratePanelCageRows:
    """Per-cage guest+occupancy rows driven by cage_type_map (Phase 42-06)."""

    @pytest.fixture
    def panel(self, monkeypatch):
        """Provide a headless HydratePanel instance for each test."""
        monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
        if not QApplication.instance():
            QApplication(sys.argv)
        return HydratePanel()

    def test_si_has_two_cage_rows(self, panel):
        """sI -> 2 rows with keys {small, large}."""
        _select_lattice(panel, "sI")
        assert len(panel._cage_guest_combos) == 2
        assert set(panel._cage_guest_combos.keys()) == {"small", "large"}

    def test_sh_has_three_cage_rows(self, panel):
        """sH -> 3 rows with keys {small, medium, large}."""
        _select_lattice(panel, "sH")
        assert len(panel._cage_guest_combos) == 3
        assert set(panel._cage_guest_combos.keys()) == {"small", "medium", "large"}

    def test_filled_ice_has_one_row(self, panel):
        """c0te (filled ice) -> 1 row with key {small}."""
        _select_lattice(panel, "c0te")
        assert len(panel._cage_guest_combos) == 1
        assert set(panel._cage_guest_combos.keys()) == {"small"}

    def test_water_only_has_no_rows(self, panel):
        """sTprime (water-only) -> 0 rows."""
        _select_lattice(panel, "sTprime")
        assert len(panel._cage_guest_combos) == 0
        assert len(panel._cage_occupancy_spins) == 0

    def test_get_configuration_builds_assignments(self, panel):
        """get_configuration builds cage_guest_assignments from the per-cage rows.

        sI: small=CH4@60%, large=THF@100% -> HydrateConfig.cage_guest_assignments
        with the per-cage guest_type + occupancy. Built-in metadata
        (guest_atom_labels/guest_atom_count) is auto-populated by
        HydrateConfig.__post_init__ (42-01 single source of truth).
        """
        _select_lattice(panel, "sI")
        _set_guest(panel, "small", "ch4")
        _set_occupancy(panel, "small", 60.0)
        _set_guest(panel, "large", "thf")
        _set_occupancy(panel, "large", 100.0)

        cfg = panel.get_configuration()
        # lattice + supercell round-trip
        assert cfg.lattice_type == "sI"
        # per-cage assignments
        assert cfg.cage_guest_assignments["small"].guest_type == "ch4"
        assert cfg.cage_guest_assignments["small"].occupancy == 60.0
        assert cfg.cage_guest_assignments["large"].guest_type == "thf"
        assert cfg.cage_guest_assignments["large"].occupancy == 100.0
        # built-in metadata auto-populated by __post_init__ (42-01)
        assert cfg.cage_guest_assignments["small"].guest_atom_count == 5  # CH4
        assert cfg.cage_guest_assignments["large"].guest_atom_count == 13  # THF

    def test_lattice_change_rebuilds_rows(self, panel):
        """Changing the lattice rebuilds the rows (no stale widgets)."""
        # Start with sI (2 rows).
        _select_lattice(panel, "sI")
        assert len(panel._cage_guest_combos) == 2
        old_small_combo = panel._cage_guest_combos["small"]
        old_small_spin = panel._cage_occupancy_spins["small"]

        # Change to sH (3 rows).
        _select_lattice(panel, "sH")
        assert len(panel._cage_guest_combos) == 3
        assert set(panel._cage_guest_combos.keys()) == {"small", "medium", "large"}

        # Old widgets replaced (new instances, not the same objects).
        assert panel._cage_guest_combos["small"] is not old_small_combo
        assert panel._cage_occupancy_spins["small"] is not old_small_spin

        # Change back to water-only (0 rows) — rows cleared.
        _select_lattice(panel, "sTprime")
        assert len(panel._cage_guest_combos) == 0


class TestDepolCombo:
    """Depol mode QComboBox wiring (Phase 43-02)."""

    @pytest.fixture
    def panel(self, monkeypatch):
        """Provide a headless HydratePanel instance for each test."""
        monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
        if not QApplication.instance():
            QApplication(sys.argv)
        return HydratePanel()

    def test_depol_combo_default_is_strict(self, panel):
        """depol_combo defaults to index 0 / data "strict"."""
        assert hasattr(panel, "depol_combo")
        assert panel.depol_combo.currentIndex() == 0
        assert panel.depol_combo.currentData() == "strict"

    def test_depol_combo_has_two_items(self, panel):
        """depol_combo has exactly 2 items with data {"strict", "optimal"}."""
        assert panel.depol_combo.count() == 2
        data_values = {panel.depol_combo.itemData(i) for i in range(2)}
        assert data_values == {"strict", "optimal"}

    def test_get_configuration_default_depol_is_strict(self, panel):
        """get_configuration round-trips strict->strict and optimal->optimal."""
        cfg = panel.get_configuration()
        assert cfg.depol_mode == "strict"

        idx = panel.depol_combo.findData("optimal")
        assert idx >= 0
        panel.depol_combo.setCurrentIndex(idx)
        cfg2 = panel.get_configuration()
        assert cfg2.depol_mode == "optimal"

    def test_depol_combo_change_emits_configuration_changed(self, panel):
        """Changing the depol combo emits configuration_changed at least once per change."""
        emitted = []
        panel.configuration_changed.connect(lambda: emitted.append(True))
        idx = panel.depol_combo.findData("optimal")
        assert idx >= 0
        panel.depol_combo.setCurrentIndex(idx)
        assert len(emitted) >= 1  # changing to optimal emits at least once
        # Change back to strict
        idx0 = panel.depol_combo.findData("strict")
        panel.depol_combo.setCurrentIndex(idx0)
        assert len(emitted) >= 2  # second change emits again


# ---------------------------------------------------------------------------
# Bundled fixture paths (Phase 44-02 custom guest upload tests).
# ---------------------------------------------------------------------------
_ETOH_GRO = "quickice/data/custom/etoh.gro"
_ETOH_ITP = "quickice/data/custom/etoh.itp"
_COMBRULE1_ITP = "quickice/data/custom/test_invalid/etoh_combrule1.itp"
_NOT_A_GRO = "quickice/data/custom/test_invalid/not_a_gro.txt"
_NO_ATOMTYPES_ITP = "quickice/data/custom/test_invalid/etoh_no_atomtypes.itp"


def _upload_valid_pair(panel, gro_path, itp_path):
    """Bypass QFileDialog: set paths directly + trigger validation.

    QFileDialog cannot run headless, so tests set ``_cg_gro_path`` /
    ``_cg_itp_path`` directly and call ``_try_validate_custom_guest`` to
    exercise the same validation + descriptor-population path the handlers
    use after a real file pick.
    """
    panel._cg_gro_path = Path(gro_path)
    panel._cg_itp_path = Path(itp_path)
    panel._try_validate_custom_guest()


def _make_long_resname_gro(tmp_path):
    """Create a GRO with a 5-char residue name (>3 chars, invalid).

    Replaces the residue-name field (fixed-width columns 5-9, 0-indexed —
    5 chars wide) in every atom line with ``"ETHAN"`` so the GRO parser's
    fixed-width column slicing still sees correctly-aligned atom-name and
    coordinate columns. A naive ``src.replace("MOL", "ETHAN")`` would shift
    every subsequent column by 2 chars and make the GRO unparseable
    (``"could not convert string to float"``) before the validator's
    ``exceeds 3 chars`` check (step 4) could fire — so the field-slice
    replacement is required to actually exercise the intended validation
    path.
    """
    src = Path(_ETOH_GRO).read_text()
    lines = src.split("\n")
    n = int(lines[1])
    for i in range(n):
        atom_line = lines[2 + i]
        # Residue-name field is columns 5-9 (0-indexed), 5 chars wide.
        lines[2 + i] = atom_line[:5] + "ETHAN" + atom_line[10:]
    bad = "\n".join(lines)
    p = tmp_path / "etoh_long.gro"
    p.write_text(bad)
    return p


class TestCustomGuestUpload:
    """Custom guest upload panel wiring (Phase 44-02).

    Covers the upload QGroupBox (two QFileDialog buttons + status labels +
    validation label), the ``_try_validate_custom_guest`` -> engine
    validator -> ``parse_gro_file`` flow, the "Custom: {residue}" per-cage
    combo option, the ``get_configuration`` custom CageGuestAssignment
    branch, and the Pitfall 6 mitigation (auto-clear second cage).
    """

    @pytest.fixture
    def panel(self, monkeypatch):
        """Provide a headless HydratePanel instance for each test."""
        monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
        if not QApplication.instance():
            QApplication(sys.argv)
        return HydratePanel()

    def test_valid_upload_populates_custom_guest_and_adds_combo_option(self, panel):
        """Valid upload populates _custom_guest + adds 'Custom: MOL' to every combo."""
        _upload_valid_pair(panel, _ETOH_GRO, _ETOH_ITP)
        assert panel._custom_guest is not None
        assert panel._custom_guest['residue_name'] == 'MOL'
        assert panel._custom_guest['atom_count'] == 9
        assert panel._custom_guest['atom_labels'] == ['H', 'C', 'H', 'H', 'C', 'H', 'H', 'O', 'H']
        assert panel._custom_guest['guest_type'] == 'custom_gui'
        # Selecting sI rebuilds the rows; the custom option must appear in
        # every per-cage combo.
        _select_lattice(panel, "sI")
        for combo in panel._cage_guest_combos.values():
            assert combo.findData(panel._custom_guest['guest_type']) >= 0
            # Item text starts with "Custom: MOL"
            custom_idx = combo.findData(panel._custom_guest['guest_type'])
            assert combo.itemText(custom_idx).startswith("Custom: MOL")
        # Validation label is green with the success message.
        assert "✓" in panel.cg_validation_label.text()
        assert "MOL" in panel.cg_validation_label.text()
        assert "9 atoms" in panel.cg_validation_label.text()

    def test_invalid_combrule1_shows_specific_error_and_keeps_none(self, panel):
        """comb-rule=1 -> specific red error mentioning 'must be 2' and 'comb-rule=1'; _custom_guest stays None."""
        _upload_valid_pair(panel, _ETOH_GRO, _COMBRULE1_ITP)
        assert panel._custom_guest is None
        text = panel.cg_validation_label.text()
        assert "comb-rule must be 2" in text
        assert "got comb-rule=1" in text
        assert "red" in panel.cg_validation_label.styleSheet()

    def test_invalid_not_a_gro_shows_parse_error(self, panel):
        """Unparseable GRO -> red 'Failed to parse GRO file' error; _custom_guest stays None."""
        _upload_valid_pair(panel, _NOT_A_GRO, _ETOH_ITP)
        assert panel._custom_guest is None
        text = panel.cg_validation_label.text()
        assert "Failed to parse GRO file" in text
        assert "red" in panel.cg_validation_label.styleSheet()

    def test_invalid_long_resname_shows_specific_error(self, panel, tmp_path):
        """5-char residue name -> red 'exceeds 3 chars' error mentioning 'ETHAN'; _custom_guest stays None."""
        long_gro = _make_long_resname_gro(tmp_path)
        _upload_valid_pair(panel, str(long_gro), _ETOH_ITP)
        assert panel._custom_guest is None
        text = panel.cg_validation_label.text()
        assert "exceeds 3 chars" in text
        assert "ETHAN" in text
        assert "red" in panel.cg_validation_label.styleSheet()

    def test_no_atomtypes_warning_shown_but_upload_succeeds(self, panel, monkeypatch):
        """Missing [ atomtypes ] is a WARNING: QMessageBox.warning fires (monkeypatched to no-op) + upload succeeds."""
        # The QMessageBox.warning is modal — monkeypatch to a no-op so the
        # headless test does not hang waiting for a dialog dismissal.
        monkeypatch.setattr(QMessageBox, "warning", lambda *a, **kw: QMessageBox.Ok)
        _upload_valid_pair(panel, _ETOH_GRO, _NO_ATOMTYPES_ITP)
        # Warning is non-blocking — upload still succeeds.
        assert panel._custom_guest is not None
        assert panel._custom_guest['residue_name'] == 'MOL'
        assert "✓" in panel.cg_validation_label.text()
        assert "green" in panel.cg_validation_label.styleSheet()

    def test_get_configuration_round_trips_custom_in_one_cage(self, panel):
        """get_configuration builds a fully-populated custom CageGuestAssignment for one cage; the other cage stays built-in.

        This also proves mixed 1-custom + 1-builtin does NOT raise
        HydrateConfig.__post_init__'s Pitfall 6 ValueError (Pitfall 6 only
        fires when the SAME custom guest is in 2 cages).
        """
        _upload_valid_pair(panel, _ETOH_GRO, _ETOH_ITP)
        _select_lattice(panel, "sI")
        _set_guest(panel, "small", panel._custom_guest['guest_type'])
        _set_occupancy(panel, "small", 80.0)
        # large cage keeps the default built-in (ch4)
        cfg = panel.get_configuration()
        small = cfg.cage_guest_assignments['small']
        assert small.guest_type == 'custom_gui'
        assert small.guest_residue_name == 'MOL'
        assert small.guest_atom_count == 9
        assert small.guest_atom_labels == ['H', 'C', 'H', 'H', 'C', 'H', 'H', 'O', 'H']
        assert small.guest_gro_path.endswith('etoh.gro')
        assert small.guest_itp_path.endswith('etoh.itp')
        assert small.occupancy == 80.0
        assert small.is_custom_guest is True
        # large cage is still built-in
        large = cfg.cage_guest_assignments['large']
        assert large.is_custom_guest is False

    def test_same_custom_in_two_cages_gui_kept(self, panel):
        """Same custom guest in 2 cages is allowed by the engine (44.1-01); both kept.

        After 44.1-01 relaxed the engine (``residue_name``→``guest_type``
        check in ``HydrateConfig.__post_init__`` only rejects genuine
        collisions — a DIFFERENT ``guest_type`` claiming an already-seen
        residue name) and 44.1-18 removed the 44-02 GUI auto-clear
        mitigation, BOTH cages keep the custom guest (same ``guest_type``
        aggregates into one ``_H`` moleculetype exactly like ``ch4``).
        """
        _upload_valid_pair(panel, _ETOH_GRO, _ETOH_ITP)
        _select_lattice(panel, "sI")
        _set_guest(panel, "small", panel._custom_guest['guest_type'])
        _set_guest(panel, "large", panel._custom_guest['guest_type'])
        # After 44.1-01 engine relaxation + 44.1-18 removal of auto-clear,
        # BOTH cages keep the custom guest (same guest_type aggregates like ch4).
        custom_type = panel._custom_guest['guest_type']
        n_custom = sum(
            1 for c in panel._cage_guest_combos.values()
            if c.currentData() == custom_type
        )
        assert n_custom == 2
        # get_configuration must NOT raise (engine allows same guest_type in 2 cages).
        cfg = panel.get_configuration()
        # Both assignments are custom.
        custom_count = sum(
            1 for a in cfg.cage_guest_assignments.values() if a.is_custom_guest
        )
        assert custom_count == 2


def test_export_interface_handler_passes_hydrate_config():
    """MainWindow._on_export_interface_gromacs passes self._current_hydrate_config
    to the exporter so the config-driven custom guest path (44.1-09) activates
    through the actual GUI export action (44.1-10).
    """
    import inspect
    from quickice.gui.main_window import MainWindow
    src = inspect.getsource(MainWindow._on_export_interface_gromacs)
    assert 'hydrate_config=self._current_hydrate_config' in src, \
        'handler must pass self._current_hydrate_config to the exporter'


def test_export_solute_handler_passes_hydrate_config():
    """MainWindow._on_export_solute_gromacs passes self._current_hydrate_config
    to the exporter so the config-driven custom guest path (44.1-11) activates
    through the actual GUI export action (44.1-12).
    """
    import inspect
    from quickice.gui.main_window import MainWindow
    src = inspect.getsource(MainWindow._on_export_solute_gromacs)
    assert 'hydrate_config=self._current_hydrate_config' in src, \
        'handler must pass self._current_hydrate_config to the exporter'


def test_export_custom_molecule_handler_passes_hydrate_config():
    """MainWindow._on_export_custom_molecule_gromacs passes self._current_hydrate_config
    to the exporter so the config-driven custom guest path (44.1-13) activates
    through the actual GUI export action (44.1-14).
    """
    import inspect
    from quickice.gui.main_window import MainWindow
    src = inspect.getsource(MainWindow._on_export_custom_molecule_gromacs)
    assert 'hydrate_config=self._current_hydrate_config' in src, \
        'handler must pass self._current_hydrate_config to the exporter'


def test_export_ion_handler_passes_hydrate_config():
    """MainWindow._on_export_ion_gromacs passes self._current_hydrate_config
    to the exporter so the config-driven custom guest path (44.1-15) activates
    through the actual GUI export action (44.1-16).
    """
    import inspect
    from quickice.gui.main_window import MainWindow
    src = inspect.getsource(MainWindow._on_export_ion_gromacs)
    assert 'hydrate_config=self._current_hydrate_config' in src, \
        'handler must pass self._current_hydrate_config to the exporter'

