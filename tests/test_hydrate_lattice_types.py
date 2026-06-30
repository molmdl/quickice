"""Tests for extended HYDRATE_LATTICES data model and HydrateLatticeInfo/Config validation.

Validates:
- All 10 HYDRATE_LATTICES entries have correct structure
- cage_type_map values are consistent with cages dict
- HydrateLatticeInfo.from_lattice_type returns correct data for all 10 types
- HydrateConfig accepts all 10 lattice types without ValueError
"""

import pytest

from quickice.structure_generation.types import (
    GUEST_MOLECULES,
    HYDRATE_LATTICES,
    HydrateConfig,
    HydrateLatticeInfo,
)


# ── Structural validation tests for HYDRATE_LATTICES entries ────────────


class TestHydrateLatticesStructure:
    """Tests for HYDRATE_LATTICES dict structure and field validity."""

    # 1. Entry count
    def test_hydrate_lattices_has_10_entries(self):
        assert len(HYDRATE_LATTICES) == 10

    # 2. Required keys
    @pytest.mark.parametrize("lattice_type", list(HYDRATE_LATTICES.keys()))
    def test_all_required_keys_present(self, lattice_type):
        entry = HYDRATE_LATTICES[lattice_type]
        required_keys = {
            "genice_name", "description", "cages",
            "unit_cell_molecules", "cage_type_map",
            "is_triclinic", "is_water_only",
        }
        assert required_keys <= set(entry.keys())

    # 3. genice_name is non-empty string
    @pytest.mark.parametrize("lattice_type", list(HYDRATE_LATTICES.keys()))
    def test_genice_name_is_string(self, lattice_type):
        entry = HYDRATE_LATTICES[lattice_type]
        assert isinstance(entry["genice_name"], str)
        assert len(entry["genice_name"]) > 0

    # 4. description is non-empty string
    @pytest.mark.parametrize("lattice_type", list(HYDRATE_LATTICES.keys()))
    def test_description_is_string(self, lattice_type):
        entry = HYDRATE_LATTICES[lattice_type]
        assert isinstance(entry["description"], str)
        assert len(entry["description"]) > 0

    # 5. unit_cell_molecules is positive
    @pytest.mark.parametrize("lattice_type", list(HYDRATE_LATTICES.keys()))
    def test_unit_cell_molecules_positive(self, lattice_type):
        entry = HYDRATE_LATTICES[lattice_type]
        assert entry["unit_cell_molecules"] > 0

    # 6. cage_type_map is dict
    @pytest.mark.parametrize("lattice_type", list(HYDRATE_LATTICES.keys()))
    def test_cage_type_map_is_dict(self, lattice_type):
        entry = HYDRATE_LATTICES[lattice_type]
        assert isinstance(entry["cage_type_map"], dict)

    # 7. cage_type_map values are non-empty strings
    @pytest.mark.parametrize("lattice_type", list(HYDRATE_LATTICES.keys()))
    def test_cage_type_map_values_are_strings(self, lattice_type):
        entry = HYDRATE_LATTICES[lattice_type]
        for value in entry["cage_type_map"].values():
            assert isinstance(value, str)
            assert len(value) > 0

    # 8. cage_type_map keys are small or large
    @pytest.mark.parametrize("lattice_type", list(HYDRATE_LATTICES.keys()))
    def test_cage_type_map_keys_are_small_or_large(self, lattice_type):
        entry = HYDRATE_LATTICES[lattice_type]
        valid_keys = {"small", "large"}
        for key in entry["cage_type_map"].keys():
            assert key in valid_keys, f"cage_type_map key '{key}' not in {valid_keys}"

    # 9. Water-only lattices have empty cage_type_map
    def test_water_only_lattices_have_empty_cage_type_map(self):
        for lattice_type, entry in HYDRATE_LATTICES.items():
            if entry["is_water_only"]:
                assert entry["cage_type_map"] == {}, (
                    f"Water-only lattice '{lattice_type}' should have empty cage_type_map"
                )

    # 10. Water-only lattices have empty cages
    def test_water_only_lattices_have_empty_cages(self):
        for lattice_type, entry in HYDRATE_LATTICES.items():
            if entry["is_water_only"]:
                assert entry["cages"] == {}, (
                    f"Water-only lattice '{lattice_type}' should have empty cages"
                )

    # 11. Non-water-only lattices have cages
    def test_non_water_only_lattices_have_cages(self):
        for lattice_type, entry in HYDRATE_LATTICES.items():
            if not entry["is_water_only"]:
                assert len(entry["cages"]) > 0, (
                    f"Non-water-only lattice '{lattice_type}' should have cages"
                )

    # 12. is_triclinic is bool
    @pytest.mark.parametrize("lattice_type", list(HYDRATE_LATTICES.keys()))
    def test_is_triclinic_is_bool(self, lattice_type):
        entry = HYDRATE_LATTICES[lattice_type]
        assert isinstance(entry["is_triclinic"], bool)

    # 13. is_water_only is bool
    @pytest.mark.parametrize("lattice_type", list(HYDRATE_LATTICES.keys()))
    def test_is_water_only_is_bool(self, lattice_type):
        entry = HYDRATE_LATTICES[lattice_type]
        assert isinstance(entry["is_water_only"], bool)

    # 14. Triclinic lattices
    def test_triclinic_lattices(self):
        assert HYDRATE_LATTICES["c0te"]["is_triclinic"] is True
        assert HYDRATE_LATTICES["c1te"]["is_triclinic"] is True
        assert HYDRATE_LATTICES["sH"]["is_triclinic"] is True

    # 15. Non-triclinic lattices
    def test_non_triclinic_lattices(self):
        for lattice_type in ("sI", "sII", "c2te", "ice1hte", "sTprime", "16", "17"):
            assert HYDRATE_LATTICES[lattice_type]["is_triclinic"] is False, (
                f"Lattice '{lattice_type}' should not be triclinic"
            )

    # 16. Filled ice single cage type
    @pytest.mark.parametrize("lattice_type", ["c0te", "c1te", "c2te", "ice1hte"])
    def test_filled_ice_single_cage_type(self, lattice_type):
        entry = HYDRATE_LATTICES[lattice_type]
        assert "large" not in entry["cage_type_map"], (
            f"Filled ice '{lattice_type}' should not have 'large' in cage_type_map"
        )
        assert entry["cage_type_map"]["small"] == "Ne1", (
            f"Filled ice '{lattice_type}' cage_type_map['small'] should be 'Ne1'"
        )

    # 17. Ice XVI same cage_type_map as sII
    def test_ice_xvi_same_cage_types_as_sii(self):
        assert HYDRATE_LATTICES["16"]["cage_type_map"] == HYDRATE_LATTICES["sII"]["cage_type_map"]

    # 18. Standard lattices have both cage types
    @pytest.mark.parametrize("lattice_type", ["sI", "sII"])
    def test_standard_lattices_have_both_cage_types(self, lattice_type):
        entry = HYDRATE_LATTICES[lattice_type]
        assert "small" in entry["cage_type_map"]
        assert "large" in entry["cage_type_map"]

    # 19. Cages dict has valid structure
    def test_cages_dict_has_valid_structure(self):
        for lattice_type, entry in HYDRATE_LATTICES.items():
            if not entry["cages"]:
                continue  # Skip empty cages (water-only)
            for cage_key, cage_info in entry["cages"].items():
                assert "name" in cage_info, (
                    f"Lattice '{lattice_type}' cage '{cage_key}' missing 'name'"
                )
                assert "count_per_unit_cell" in cage_info, (
                    f"Lattice '{lattice_type}' cage '{cage_key}' missing 'count_per_unit_cell'"
                )
                assert "guest_fits" in cage_info, (
                    f"Lattice '{lattice_type}' cage '{cage_key}' missing 'guest_fits'"
                )
                assert cage_info["count_per_unit_cell"] > 0, (
                    f"Lattice '{lattice_type}' cage '{cage_key}' count_per_unit_cell must be > 0"
                )

    # 20. Specific lattice data values
    def test_specific_lattice_data(self):
        # c0te
        assert HYDRATE_LATTICES["c0te"]["unit_cell_molecules"] == 6
        assert HYDRATE_LATTICES["c0te"]["cages"]["guest"]["count_per_unit_cell"] == 3

        # c1te
        assert HYDRATE_LATTICES["c1te"]["unit_cell_molecules"] == 36
        assert HYDRATE_LATTICES["c1te"]["cages"]["guest"]["count_per_unit_cell"] == 6

        # c2te
        assert HYDRATE_LATTICES["c2te"]["unit_cell_molecules"] == 32
        assert HYDRATE_LATTICES["c2te"]["cages"]["guest"]["count_per_unit_cell"] == 32

        # ice1hte
        assert HYDRATE_LATTICES["ice1hte"]["unit_cell_molecules"] == 16
        assert HYDRATE_LATTICES["ice1hte"]["cages"]["guest"]["count_per_unit_cell"] == 8

        # sTprime
        assert HYDRATE_LATTICES["sTprime"]["unit_cell_molecules"] == 24

        # 16 (Ice XVI)
        assert HYDRATE_LATTICES["16"]["unit_cell_molecules"] == 136

        # 17 (Ice XVII)
        assert HYDRATE_LATTICES["17"]["unit_cell_molecules"] == 12


# ── HydrateLatticeInfo tests ─────────────────────────────────────────────


class TestHydrateLatticeInfoExtended:
    """Tests for HydrateLatticeInfo.from_lattice_type with all 10 lattice types."""

    # 1. All 10 types work
    @pytest.mark.parametrize("lattice_type", list(HYDRATE_LATTICES.keys()))
    def test_from_lattice_type_all_10_types(self, lattice_type):
        info = HydrateLatticeInfo.from_lattice_type(lattice_type)
        assert info.lattice_type == lattice_type

    # 2. Unknown type raises ValueError
    def test_from_lattice_type_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown lattice type"):
            HydrateLatticeInfo.from_lattice_type("unknown")

    # 3. Water-only lattice info
    @pytest.mark.parametrize("lattice_type", ["sTprime", "17"])
    def test_water_only_lattice_info(self, lattice_type):
        info = HydrateLatticeInfo.from_lattice_type(lattice_type)
        assert info.total_cages == 0
        assert info.is_water_only is True
        assert info.cage_types == []
        assert info.cage_counts == {}

    # 4. c0te lattice info
    def test_filled_ice_c0te_lattice_info(self):
        info = HydrateLatticeInfo.from_lattice_type("c0te")
        assert info.cage_types == ["Ne1"]
        assert info.cage_counts == {"Ne1": 3}
        assert info.total_cages == 3
        assert info.is_water_only is False
        assert info.is_triclinic is True
        assert info.cage_type_map == {"small": "Ne1"}

    # 5. c1te lattice info
    def test_c1te_lattice_info(self):
        info = HydrateLatticeInfo.from_lattice_type("c1te")
        assert info.cage_counts == {"Ne1": 6}
        assert info.total_cages == 6
        assert info.is_triclinic is True

    # 6. c2te lattice info
    def test_c2te_lattice_info(self):
        info = HydrateLatticeInfo.from_lattice_type("c2te")
        assert info.total_cages == 32
        assert info.is_triclinic is False

    # 7. ice1hte lattice info
    def test_ice1hte_lattice_info(self):
        info = HydrateLatticeInfo.from_lattice_type("ice1hte")
        assert info.cage_types == ["Ne1"]
        assert info.total_cages == 8
        assert info.is_triclinic is False

    # 8. Ice XVI (16) lattice info
    def test_ice_xvi_lattice_info(self):
        info = HydrateLatticeInfo.from_lattice_type("16")
        # sII has 16 small + 8 large = 24 total cages
        assert info.total_cages == 24
        assert info.cage_type_map == {"small": "12", "large": "16"}
        assert info.is_water_only is False

    # 9. Ice XVII (17) lattice info
    def test_ice_xvii_lattice_info(self):
        info = HydrateLatticeInfo.from_lattice_type("17")
        assert info.total_cages == 0
        assert info.is_water_only is True

    # 10. sH lattice info
    def test_sH_lattice_info(self):
        info = HydrateLatticeInfo.from_lattice_type("sH")
        assert info.is_triclinic is True
        assert info.is_water_only is False


# ── HydrateConfig tests for all 10 lattice types ──────────────────────────


class TestHydrateConfigExtendedTypes:
    """Tests for HydrateConfig accepting all 10 lattice types."""

    # 1. All 10 types accepted
    @pytest.mark.parametrize("lattice_type", list(HYDRATE_LATTICES.keys()))
    def test_config_all_10_lattice_types(self, lattice_type):
        config = HydrateConfig(lattice_type=lattice_type)
        assert config.lattice_type == lattice_type

    # 2. c0te with ch4 succeeds
    def test_config_c0te_with_ch4(self):
        config = HydrateConfig(lattice_type="c0te", guest_type="ch4")
        assert config.lattice_type == "c0te"
        assert config.guest_type == "ch4"

    # 3. c0te with thf succeeds
    def test_config_c0te_with_thf(self):
        config = HydrateConfig(lattice_type="c0te", guest_type="thf")
        assert config.lattice_type == "c0te"
        assert config.guest_type == "thf"

    # 4. sTprime with guest (guest accepted but ignored by generator)
    def test_config_sTprime_with_guest(self):
        config = HydrateConfig(lattice_type="sTprime", guest_type="ch4")
        assert config.lattice_type == "sTprime"
        # guest_type is accepted at config level; generator will ignore
        assert config.guest_type == "ch4"

    # 5. Unknown lattice type raises ValueError
    def test_config_unknown_lattice_raises(self):
        with pytest.raises(ValueError, match="Unknown lattice type"):
            HydrateConfig(lattice_type="unknown")

    # 6. get_genice_lattice_name matches HYDRATE_LATTICES for all types
    @pytest.mark.parametrize("lattice_type", list(HYDRATE_LATTICES.keys()))
    def test_config_get_genice_lattice_name_all_types(self, lattice_type):
        config = HydrateConfig(lattice_type=lattice_type)
        expected = HYDRATE_LATTICES[lattice_type]["genice_name"]
        assert config.get_genice_lattice_name() == expected

    # 7. Ice XVI genice_name
    def test_config_ice_xvi_genice_name(self):
        config = HydrateConfig(lattice_type="16")
        assert config.get_genice_lattice_name() == "16"

    # 8. Ice XVII genice_name
    def test_config_ice_xvii_genice_name(self):
        config = HydrateConfig(lattice_type="17")
        assert config.get_genice_lattice_name() == "17"
