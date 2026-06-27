"""Tests for HydrateConfig guest metadata and HydrateStructure metadata propagation.

Validates:
- GUEST_MOLECULES dict has atom_labels for built-in types
- HydrateConfig auto-populates metadata for built-in guest types
- Explicit values override auto-population
- from_dict is backward-compatible
- HydrateStructure carries guest metadata from config (added in Task 2)
"""

import numpy as np
import pytest

from quickice.structure_generation.types import (
    GUEST_MOLECULES,
    HydrateConfig,
    HydrateStructure,
    HydrateLatticeInfo,
    MoleculeIndex,
)


# ── GUEST_MOLECULES dict ──────────────────────────────────────────────────

class TestGuestMoleculesDict:
    """Tests for GUEST_MOLECULES dict having atom_labels."""

    def test_ch4_has_atom_labels(self):
        assert "atom_labels" in GUEST_MOLECULES["ch4"]

    def test_thf_has_atom_labels(self):
        assert "atom_labels" in GUEST_MOLECULES["thf"]

    def test_ch4_atom_labels_content(self):
        labels = GUEST_MOLECULES["ch4"]["atom_labels"]
        assert labels == ["C", "H", "H", "H", "H"]

    def test_thf_atom_labels_content(self):
        labels = GUEST_MOLECULES["thf"]["atom_labels"]
        assert labels == ["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"]

    def test_ch4_atom_labels_length_matches_atoms(self):
        assert len(GUEST_MOLECULES["ch4"]["atom_labels"]) == GUEST_MOLECULES["ch4"]["atoms"]

    def test_thf_atom_labels_length_matches_atoms(self):
        assert len(GUEST_MOLECULES["thf"]["atom_labels"]) == GUEST_MOLECULES["thf"]["atoms"]


# ── HydrateConfig auto-population ────────────────────────────────────────

class TestHydrateConfigAutoPopulation:
    """Tests for HydrateConfig auto-population of guest metadata from GUEST_MOLECULES."""

    def test_ch4_auto_populates_guest_name(self):
        config = HydrateConfig(guest_type="ch4")
        assert config.guest_name == "Methane"

    def test_ch4_auto_populates_guest_atom_labels(self):
        config = HydrateConfig(guest_type="ch4")
        assert config.guest_atom_labels == ["C", "H", "H", "H", "H"]

    def test_ch4_auto_populates_guest_atom_count(self):
        config = HydrateConfig(guest_type="ch4")
        assert config.guest_atom_count == 5

    def test_thf_auto_populates_guest_name(self):
        config = HydrateConfig(guest_type="thf")
        assert config.guest_name == "Tetrahydrofuran"

    def test_thf_auto_populates_guest_atom_labels(self):
        config = HydrateConfig(guest_type="thf")
        assert config.guest_atom_labels == ["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"]

    def test_thf_auto_populates_guest_atom_count(self):
        config = HydrateConfig(guest_type="thf")
        assert config.guest_atom_count == 13


# ── HydrateConfig explicit override ───────────────────────────────────────

class TestHydrateConfigExplicitOverride:
    """Tests that explicit values override auto-population."""

    def test_explicit_guest_name_overrides(self):
        config = HydrateConfig(guest_type="ch4", guest_name="Custom Name")
        assert config.guest_name == "Custom Name"

    def test_explicit_guest_atom_labels_overrides(self):
        custom_labels = ["C", "H1", "H2", "H3", "H4"]
        config = HydrateConfig(guest_type="ch4", guest_atom_labels=custom_labels)
        assert config.guest_atom_labels == custom_labels

    def test_explicit_guest_atom_count_overrides(self):
        config = HydrateConfig(guest_type="ch4", guest_atom_count=10)
        assert config.guest_atom_count == 10

    def test_explicit_guest_itp_path(self):
        config = HydrateConfig(guest_type="ch4", guest_itp_path="/path/to/guest.itp")
        assert config.guest_itp_path == "/path/to/guest.itp"

    def test_guest_itp_path_default_empty(self):
        config = HydrateConfig(guest_type="ch4")
        assert config.guest_itp_path == ""

    def test_guest_name_default_empty_custom_type(self):
        """For a hypothetical custom type (not in GUEST_MOLECULES), it would raise.
        But explicit name with a known type shows override behavior."""
        # Use explicit name with known type to test override
        config = HydrateConfig(guest_type="thf", guest_name="My THF")
        assert config.guest_name == "My THF"


# ── HydrateConfig.from_dict backward compatibility ────────────────────────

class TestHydrateConfigFromDict:
    """Tests for HydrateConfig.from_dict backward compatibility."""

    def test_from_dict_without_new_fields(self):
        """from_dict without new fields should use defaults (then auto-populate)."""
        d = {"lattice_type": "sI", "guest_type": "ch4"}
        config = HydrateConfig.from_dict(d)
        assert config.guest_name == "Methane"
        assert config.guest_atom_labels == ["C", "H", "H", "H", "H"]
        assert config.guest_atom_count == 5
        assert config.guest_itp_path == ""

    def test_from_dict_with_new_fields(self):
        """from_dict with new fields should pass them through."""
        d = {
            "lattice_type": "sI",
            "guest_type": "ch4",
            "guest_name": "Custom Methane",
            "guest_atom_labels": ["C", "H1", "H2", "H3", "H4"],
            "guest_atom_count": 5,
            "guest_itp_path": "/custom/guest.itp",
        }
        config = HydrateConfig.from_dict(d)
        assert config.guest_name == "Custom Methane"
        assert config.guest_atom_labels == ["C", "H1", "H2", "H3", "H4"]
        assert config.guest_atom_count == 5
        assert config.guest_itp_path == "/custom/guest.itp"

    def test_from_dict_partial_new_fields(self):
        """from_dict with only some new fields."""
        d = {"lattice_type": "sII", "guest_type": "thf", "guest_name": "My THF"}
        config = HydrateConfig.from_dict(d)
        # Explicit guest_name overrides
        assert config.guest_name == "My THF"
        # Others auto-populate since they were empty/default
        assert config.guest_atom_labels == ["O", "CA", "CA", "CB", "CB", "H", "H", "H", "H", "H", "H", "H", "H"]
        assert config.guest_atom_count == 13

    def test_from_dict_thf_without_new_fields(self):
        """THF from_dict without new fields should auto-populate."""
        d = {"lattice_type": "sII", "guest_type": "thf"}
        config = HydrateConfig.from_dict(d)
        assert config.guest_name == "Tetrahydrofuran"
        assert config.guest_atom_count == 13


# ── HydrateStructure guest metadata propagation ──────────────────────────

class TestHydrateStructureMetadata:
    """Tests for HydrateStructure carrying guest metadata from HydrateConfig."""

    def _make_config(self, **kwargs) -> HydrateConfig:
        """Create a HydrateConfig with defaults for testing."""
        defaults = {"lattice_type": "sI", "guest_type": "ch4"}
        defaults.update(kwargs)
        return HydrateConfig(**defaults)

    def _make_structure(self, config: HydrateConfig, **overrides) -> HydrateStructure:
        """Create a minimal HydrateStructure for testing (no GenIce2 needed)."""
        n_atoms = 10
        defaults = dict(
            positions=np.zeros((n_atoms, 3)),
            atom_names=["OW", "HW1", "HW2", "MW"] * 2 + ["C", "H"],
            cell=np.eye(3) * 3.0,
            molecule_index=[MoleculeIndex(0, 4, "water"), MoleculeIndex(4, 4, "water")],
            config=config,
            lattice_info=HydrateLatticeInfo.from_lattice_type(config.lattice_type),
            report="Test report",
            guest_count=0,
            water_count=2,
        )
        defaults.update(overrides)
        # Add guest metadata from config
        defaults.setdefault("guest_name", config.guest_name)
        defaults.setdefault("guest_atom_labels", config.guest_atom_labels)
        defaults.setdefault("guest_atom_count", config.guest_atom_count)
        defaults.setdefault("guest_itp_path", config.guest_itp_path)
        return HydrateStructure(**defaults)

    def test_hydrate_structure_has_guest_name(self):
        config = self._make_config(guest_type="ch4")
        structure = self._make_structure(config)
        assert structure.guest_name == "Methane"

    def test_hydrate_structure_has_guest_atom_labels(self):
        config = self._make_config(guest_type="ch4")
        structure = self._make_structure(config)
        assert structure.guest_atom_labels == ["C", "H", "H", "H", "H"]

    def test_hydrate_structure_has_guest_atom_count(self):
        config = self._make_config(guest_type="thf")
        structure = self._make_structure(config)
        assert structure.guest_atom_count == 13

    def test_hydrate_structure_has_guest_itp_path_default(self):
        config = self._make_config(guest_type="ch4")
        structure = self._make_structure(config)
        assert structure.guest_itp_path == ""

    def test_hydrate_structure_custom_itp_path(self):
        config = self._make_config(guest_type="ch4", guest_itp_path="/custom/guest.itp")
        structure = self._make_structure(config)
        assert structure.guest_itp_path == "/custom/guest.itp"

    def test_metadata_round_trip_ch4(self):
        """Config metadata propagates through to structure unchanged (ch4)."""
        config = self._make_config(guest_type="ch4")
        structure = self._make_structure(config)
        assert structure.guest_name == config.guest_name
        assert structure.guest_atom_labels == config.guest_atom_labels
        assert structure.guest_atom_count == config.guest_atom_count
        assert structure.guest_itp_path == config.guest_itp_path

    def test_metadata_round_trip_thf(self):
        """Config metadata propagates through to structure unchanged (thf)."""
        config = self._make_config(guest_type="thf")
        structure = self._make_structure(config)
        assert structure.guest_name == config.guest_name
        assert structure.guest_atom_labels == config.guest_atom_labels
        assert structure.guest_atom_count == config.guest_atom_count
        assert structure.guest_itp_path == config.guest_itp_path

    def test_metadata_round_trip_custom(self):
        """Config with explicit overrides propagates through to structure."""
        config = self._make_config(
            guest_type="ch4",
            guest_name="Custom",
            guest_atom_labels=["C", "H1", "H2", "H3", "H4"],
            guest_atom_count=5,
            guest_itp_path="/path/to/custom.itp",
        )
        structure = self._make_structure(config)
        assert structure.guest_name == "Custom"
        assert structure.guest_atom_labels == ["C", "H1", "H2", "H3", "H4"]
        assert structure.guest_atom_count == 5
        assert structure.guest_itp_path == "/path/to/custom.itp"
