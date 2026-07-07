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

import pytest
from PySide6.QtWidgets import QApplication

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
