"""Tests for MoleculetypeRegistry with _H suffix for hydrate guests."""

import pytest
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry


class TestHydrateGuestNaming:
    """Test that hydrate guests use _H suffix (not _HYD)."""

    def test_register_hydrate_guest_ch4(self):
        """CH4 hydrate guest registers as CH4_H."""
        registry = MoleculetypeRegistry()
        result = registry.register_hydrate_guest('CH4')
        assert result == 'CH4_H', f"Expected 'CH4_H', got '{result}'"

    def test_register_hydrate_guest_thf(self):
        """THF hydrate guest registers as THF_H."""
        registry = MoleculetypeRegistry()
        result = registry.register_hydrate_guest('THF')
        assert result == 'THF_H', f"Expected 'THF_H', got '{result}'"

    def test_get_gromacs_name_hydrate(self):
        """get_gromacs_name returns CH4_H for hydrate_CH4 key."""
        registry = MoleculetypeRegistry()
        registry.register_hydrate_guest('CH4')
        result = registry.get_gromacs_name('hydrate_CH4')
        assert result == 'CH4_H', f"Expected 'CH4_H', got '{result}'"

    def test_reserved_names_include_h_suffix(self):
        """RESERVED_NAMES includes CH4_H and THF_H."""
        assert 'CH4_H' in MoleculetypeRegistry.RESERVED_NAMES, "CH4_H not in RESERVED_NAMES"
        assert 'THF_H' in MoleculetypeRegistry.RESERVED_NAMES, "THF_H not in RESERVED_NAMES"

    def test_reserved_names_exclude_old_suffix(self):
        """RESERVED_NAMES does NOT include CH4_HYD or THF_HYD (old suffix)."""
        assert 'CH4_HYD' not in MoleculetypeRegistry.RESERVED_NAMES, "CH4_HYD should not be in RESERVED_NAMES"
        assert 'THF_HYD' not in MoleculetypeRegistry.RESERVED_NAMES, "THF_HYD should not be in RESERVED_NAMES"

    def test_liquid_solute_still_uses_l_suffix(self):
        """Liquid solutes still use _L suffix (unchanged)."""
        registry = MoleculetypeRegistry()
        result = registry.register_liquid_solute('CH4')
        assert result == 'CH4_L', f"Expected 'CH4_L', got '{result}'"

    def test_hydrate_and_liquid_both_registered(self):
        """Hydrate CH4_H and liquid CH4_L can both be registered."""
        registry = MoleculetypeRegistry()
        hydrate_name = registry.register_hydrate_guest('CH4')
        liquid_name = registry.register_liquid_solute('CH4')
        assert hydrate_name == 'CH4_H'
        assert liquid_name == 'CH4_L'
        assert hydrate_name != liquid_name
