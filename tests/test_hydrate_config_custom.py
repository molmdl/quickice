"""Unit tests for custom guest HydrateConfig validation (Phase 40-03).

Validates:
- Custom guest types (not in GUEST_MOLECULES) pass with explicit metadata
- Custom guests require guest_residue_name, guest_atom_labels, guest_atom_count,
  guest_gro_path (no auto-populate, per decision [38-01])
- is_custom_guest property distinguishes custom (True) from built-in (False)
- Built-in guests (ch4, thf) still auto-populate metadata (backward compat)
- from_dict passes new fields through; old dicts without new fields still work
- Explicit guest_name override is respected for custom guests
"""

import pytest

from quickice.structure_generation.types import HydrateConfig, GUEST_MOLECULES


# ── Custom guest valid construction ───────────────────────────────────────

class TestCustomGuestValid:
    """Tests for valid custom guest HydrateConfig construction."""

    def test_custom_guest_valid(self):
        """Custom guest with all explicit metadata constructs successfully."""
        config = HydrateConfig(
            lattice_type="sI",
            guest_type="etoh_custom",
            guest_residue_name="MOL",
            guest_gro_path="quickice/data/custom/etoh.gro",
            guest_itp_path="quickice/data/custom/etoh.itp",
            guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
            guest_atom_count=9,
        )
        assert config.is_custom_guest is True
        assert config.guest_name == "MOL"  # defaults to residue name
        assert config.guest_residue_name == "MOL"
        assert config.guest_gro_path == "quickice/data/custom/etoh.gro"

    def test_custom_guest_name_override(self):
        """Explicit guest_name is respected (not replaced by residue name)."""
        config = HydrateConfig(
            lattice_type="sI",
            guest_type="etoh_custom",
            guest_residue_name="MOL",
            guest_name="Ethanol",
            guest_gro_path="x.gro",
            guest_itp_path="x.itp",
            guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
            guest_atom_count=9,
        )
        assert config.guest_name == "Ethanol"  # explicit override respected
        assert config.guest_residue_name == "MOL"


# ── Custom guest validation (missing required fields) ─────────────────────

class TestCustomGuestValidation:
    """Tests that custom guests missing required metadata raise ValueError."""

    def test_custom_guest_without_residue_name_raises(self):
        """Custom guest without guest_residue_name raises ValueError."""
        with pytest.raises(ValueError, match="guest_residue_name"):
            HydrateConfig(
                guest_type="etoh_custom",
                guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
                guest_atom_count=9,
                guest_gro_path="x.gro",
                guest_itp_path="x.itp",
            )

    def test_custom_guest_without_atom_labels_raises(self):
        """Custom guest without guest_atom_labels raises ValueError."""
        with pytest.raises(ValueError, match="guest_atom_labels"):
            HydrateConfig(
                guest_type="etoh_custom",
                guest_residue_name="MOL",
                guest_atom_count=9,
                guest_gro_path="x.gro",
                guest_itp_path="x.itp",
            )

    def test_custom_guest_without_atom_count_raises(self):
        """Custom guest without guest_atom_count raises ValueError."""
        with pytest.raises(ValueError, match="guest_atom_count"):
            HydrateConfig(
                guest_type="etoh_custom",
                guest_residue_name="MOL",
                guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
                guest_gro_path="x.gro",
                guest_itp_path="x.itp",
            )

    def test_custom_guest_without_gro_path_raises(self):
        """Custom guest without guest_gro_path raises ValueError."""
        with pytest.raises(ValueError, match="guest_gro_path"):
            HydrateConfig(
                guest_type="etoh_custom",
                guest_residue_name="MOL",
                guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
                guest_atom_count=9,
                guest_itp_path="x.itp",
            )


# ── Built-in guest backward compatibility ─────────────────────────────────

class TestBuiltinGuestBackwardCompat:
    """Tests that built-in guests still auto-populate metadata (backward compat)."""

    def test_builtin_ch4_still_works(self):
        """Built-in ch4 auto-populates metadata; is_custom_guest False."""
        config = HydrateConfig(guest_type="ch4")
        assert config.is_custom_guest is False
        assert config.guest_name == "Methane"
        assert config.guest_atom_count == 5
        assert config.guest_atom_labels == ["C", "H", "H", "H", "H"]

    def test_builtin_thf_still_works(self):
        """Built-in thf auto-populates metadata; is_custom_guest False."""
        config = HydrateConfig(guest_type="thf")
        assert config.is_custom_guest is False
        assert config.guest_name == "Tetrahydrofuran"
        assert config.guest_atom_count == 13


# ── from_dict passthrough ─────────────────────────────────────────────────

class TestFromDictCustomFields:
    """Tests for from_dict passing new fields and backward compatibility."""

    def test_from_dict_passes_custom_fields(self):
        """from_dict passes guest_residue_name and guest_gro_path through."""
        config = HydrateConfig.from_dict({
            "lattice_type": "sI",
            "guest_type": "etoh_custom",
            "guest_residue_name": "MOL",
            "guest_gro_path": "x.gro",
            "guest_itp_path": "x.itp",
            "guest_atom_labels": ["H"],
            "guest_atom_count": 1,
        })
        assert config.guest_residue_name == "MOL"
        assert config.guest_gro_path == "x.gro"
        assert config.is_custom_guest is True

    def test_from_dict_backward_compat(self):
        """Old dicts without new fields still work; new fields default empty."""
        config = HydrateConfig.from_dict({"lattice_type": "sI", "guest_type": "ch4"})
        assert config.is_custom_guest is False
        assert config.guest_residue_name == ""  # default
        assert config.guest_gro_path == ""  # default
