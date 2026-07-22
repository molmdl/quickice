"""Tests for ice_nmolecules/water_nmolecules fields on CustomMoleculeStructure and SoluteStructure.

Verifies that the ROOT FIX (adding these fields to the dataclasses) correctly
populates them and that downstream consumers (ion_inserter, CLI pipeline)
can access them without falling back to 0.

Background: CustomMoleculeStructure and SoluteStructure historically lacked
ice_nmolecules and water_nmolecules fields. Downstream code using
getattr(structure, 'ice_nmolecules', 0) would silently get 0, causing:
- Wrong molecule_index in ion_inserter._build_molecule_index_from_structure
- Zero liquid volume in CLI pipeline volume calculations
- Zero ion/molecule counts from concentration calculations

The root fix adds these fields directly to the dataclasses, eliminating
the need for _resolve_ice_nmolecules-style workarounds.
"""

import numpy as np
import pytest
from pathlib import Path

from quickice.structure_generation.ion_inserter import IonInserter
from quickice.structure_generation.solute_inserter import SoluteInserter
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
from quickice.structure_generation.types import (
    IonConfig,
    SoluteConfig,
    CustomMoleculeConfig,
    CustomMoleculeStructure,
    SoluteStructure,
    WATER_VOLUME_NM3,
    WATER_ATOMS_PER_MOLECULE,
)


# ── Test data paths ──────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent / "quickice" / "data" / "custom"
ETOH_GRO = DATA_DIR / "etoh.gro"
ETOH_ITP = DATA_DIR / "etoh.itp"


# ── CustomMoleculeStructure field tests ──────────────────────────────────────


class TestCustomMoleculeStructureNmolecules:
    """Verify ice_nmolecules and water_nmolecules on CustomMoleculeStructure."""

    def test_custom_molecule_structure_has_ice_nmolecules(self, interface_slab):
        """CustomMoleculeStructure.ice_nmolecules should match source interface."""
        config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            molecule_count=3,
        )
        inserter = CustomMoleculeInserter(config)
        custom = inserter.place_random(interface_slab, 3)

        assert isinstance(custom, CustomMoleculeStructure)
        assert custom.ice_nmolecules > 0, (
            f"ice_nmolecules should be > 0, got {custom.ice_nmolecules}"
        )
        # Should match the source interface's ice_nmolecules
        # (custom molecule insertion doesn't change ice count)
        assert custom.ice_nmolecules == interface_slab.ice_nmolecules, (
            f"ice_nmolecules mismatch: CustomMoleculeStructure has {custom.ice_nmolecules}, "
            f"source interface has {interface_slab.ice_nmolecules}"
        )

    def test_custom_molecule_structure_has_water_nmolecules(self, interface_slab):
        """CustomMoleculeStructure.water_nmolecules should reflect water after removal."""
        config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            molecule_count=3,
        )
        inserter = CustomMoleculeInserter(config)
        custom = inserter.place_random(interface_slab, 3)

        assert isinstance(custom, CustomMoleculeStructure)
        assert custom.water_nmolecules > 0, (
            f"water_nmolecules should be > 0, got {custom.water_nmolecules}"
        )
        # water_nmolecules should equal water_atom_count / WATER_ATOMS_PER_MOLECULE
        expected = custom.water_atom_count // WATER_ATOMS_PER_MOLECULE
        assert custom.water_nmolecules == expected, (
            f"water_nmolecules mismatch: {custom.water_nmolecules} != "
            f"water_atom_count({custom.water_atom_count}) / {WATER_ATOMS_PER_MOLECULE} = {expected}"
        )

    def test_custom_molecule_structure_nmolecules_consistent_with_interface(self, interface_slab):
        """CustomMoleculeStructure nmolecules should match interface_structure values."""
        config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            molecule_count=3,
        )
        inserter = CustomMoleculeInserter(config)
        custom = inserter.place_random(interface_slab, 3)

        # The interface_structure stored in CustomMoleculeStructure is the
        # modified InterfaceStructure after water removal
        interface = custom.interface_structure
        assert custom.ice_nmolecules == interface.ice_nmolecules, (
            f"ice_nmolecules: custom={custom.ice_nmolecules} vs interface={interface.ice_nmolecules}"
        )
        assert custom.water_nmolecules == interface.water_nmolecules, (
            f"water_nmolecules: custom={custom.water_nmolecules} vs interface={interface.water_nmolecules}"
        )

    def test_getattr_ice_nmolecules_no_longer_defaults_to_zero(self, interface_slab):
        """getattr(custom, 'ice_nmolecules', 0) should NOT return 0."""
        config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            molecule_count=3,
        )
        inserter = CustomMoleculeInserter(config)
        custom = inserter.place_random(interface_slab, 3)

        # Before the fix, this would return 0 (the default) because
        # CustomMoleculeStructure lacked the field
        ice_nmols = getattr(custom, 'ice_nmolecules', 0)
        assert ice_nmols > 0, (
            f"getattr(custom, 'ice_nmolecules', 0) returned 0 — "
            f"field is missing or not populated"
        )

        water_nmols = getattr(custom, 'water_nmolecules', 0)
        assert water_nmols > 0, (
            f"getattr(custom, 'water_nmolecules', 0) returned 0 — "
            f"field is missing or not populated"
        )


# ── SoluteStructure field tests ──────────────────────────────────────────────


class TestSoluteStructureNmolecules:
    """Verify ice_nmolecules and water_nmolecules on SoluteStructure."""

    def test_solute_structure_has_ice_nmolecules(self, interface_slab):
        """SoluteStructure.ice_nmolecules should match source interface."""
        config = SoluteConfig(concentration_molar=0.3, solute_type='CH4')
        inserter = SoluteInserter(config=config, seed=42)
        solute = inserter.insert_solutes(interface_slab, config)

        assert isinstance(solute, SoluteStructure)
        assert solute.ice_nmolecules > 0, (
            f"ice_nmolecules should be > 0, got {solute.ice_nmolecules}"
        )
        assert solute.ice_nmolecules == interface_slab.ice_nmolecules, (
            f"ice_nmolecules mismatch: SoluteStructure has {solute.ice_nmolecules}, "
            f"source interface has {interface_slab.ice_nmolecules}"
        )

    def test_solute_structure_has_water_nmolecules(self, interface_slab):
        """SoluteStructure.water_nmolecules should reflect water after removal."""
        config = SoluteConfig(concentration_molar=0.3, solute_type='CH4')
        inserter = SoluteInserter(config=config, seed=42)
        solute = inserter.insert_solutes(interface_slab, config)

        assert isinstance(solute, SoluteStructure)
        assert solute.water_nmolecules > 0, (
            f"water_nmolecules should be > 0, got {solute.water_nmolecules}"
        )
        # water_nmolecules should match the modified interface
        assert solute.water_nmolecules == solute.interface_structure.water_nmolecules, (
            f"water_nmolecules mismatch: SoluteStructure has {solute.water_nmolecules}, "
            f"interface has {solute.interface_structure.water_nmolecules}"
        )

    def test_solute_structure_from_custom_molecule_has_nmolecules(self, interface_slab):
        """SoluteStructure created from CustomMoleculeStructure should have correct nmolecules."""
        # First create custom molecule structure
        custom_config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            molecule_count=3,
        )
        custom_inserter = CustomMoleculeInserter(custom_config)
        custom = custom_inserter.place_random(interface_slab, 3)

        # Then insert solutes using custom as source
        solute_config = SoluteConfig(concentration_molar=0.3, solute_type='CH4')
        solute_inserter = SoluteInserter(config=solute_config, seed=42)
        solute = solute_inserter.insert_solutes(custom, solute_config)

        assert isinstance(solute, SoluteStructure)
        assert solute.ice_nmolecules > 0, (
            f"ice_nmolecules should be > 0, got {solute.ice_nmolecules}"
        )
        assert solute.water_nmolecules > 0, (
            f"water_nmolecules should be > 0, got {solute.water_nmolecules}"
        )

    def test_solute_zero_molecules_has_nmolecules(self, interface_slab):
        """SoluteStructure with 0 molecules (low concentration) should still have nmolecules."""
        # Very low concentration → 0 molecules
        config = SoluteConfig(concentration_molar=0.0001, solute_type='CH4')
        inserter = SoluteInserter(config=config, seed=42)
        solute = inserter.insert_solutes(interface_slab, config)

        assert isinstance(solute, SoluteStructure)
        assert solute.n_molecules == 0, "Should have 0 solute molecules at low concentration"
        # But ice_nmolecules and water_nmolecules should still be populated
        assert solute.ice_nmolecules > 0, (
            f"ice_nmolecules should be > 0 even with 0 solutes, got {solute.ice_nmolecules}"
        )
        assert solute.water_nmolecules > 0, (
            f"water_nmolecules should be > 0 even with 0 solutes, got {solute.water_nmolecules}"
        )


# ── IonInserter robustness tests ────────────────────────────────────────────


class TestIonInserterBuildMoleculeIndexRobustness:
    """Verify _build_molecule_index_from_structure handles missing nmolecules fields."""

    def test_build_molecule_index_uses_atom_count_fallback(self, interface_hydrate_slab):
        """_build_molecule_index_from_structure should fall back to atom count when nmolecules is 0.

        This tests the defense-in-depth fix: even if a structure somehow has
        ice_nmolecules=0 but ice_atom_count>0, the method should compute
        ice_nmolecules from atom counts instead of producing 0 entries.

        NOTE (SUSP-01): the fallback now only computes for confirmed 4-atom
        TIP4P-family ice (first atom "OW"). For 3-atom GenIce ice it raises
        ValueError rather than silently miscounting with the 4-atom divisor
        (e.g. 300 atoms -> 75 mols instead of 100); that 3-atom raise is
        covered by tests/scancode/test_scancode_bugs_ion_alternation.py. This test
        therefore uses a 4-atom TIP4P-family interface (hydrate slab, atom
        names start with "OW") to exercise the PRESERVED 4-atom compute
        fallback path.
        """
        # Create a minimal structure that simulates the old CustomMoleculeStructure
        # (has ice_atom_count and water_atom_count but ice_nmolecules=0/water_nmolecules=0)
        from quickice.structure_generation.types import MoleculeIndex

        # Build molecule_index from the 4-atom TIP4P-family hydrate interface
        interface = interface_hydrate_slab
        n_ice_mols = interface.ice_nmolecules
        n_water_mols = interface.water_nmolecules
        ice_atoms_per_mol = interface.ice_atom_count // n_ice_mols if n_ice_mols > 0 else 4
        water_atoms_per_mol = interface.water_atom_count // n_water_mols if n_water_mols > 0 else 4

        # Create a structure with empty molecule_index and zero nmolecules
        # but with valid ice_atom_count and water_atom_count
        # This simulates the pre-fix CustomMoleculeStructure scenario
        from types import SimpleNamespace
        buggy_structure = SimpleNamespace(
            positions=interface.positions,
            atom_names=interface.atom_names,
            cell=interface.cell,
            molecule_index=[],  # Empty — triggers _build_molecule_index_from_structure
            ice_atom_count=interface.ice_atom_count,
            water_atom_count=interface.water_atom_count,
            guest_atom_count=0,
            ice_nmolecules=0,  # Bug: should be > 0 but is 0
            water_nmolecules=0,  # Bug: should be > 0 but is 0
            guest_nmolecules=0,
            interface_structure=None,  # No fallback
        )

        inserter = IonInserter(config=IonConfig(concentration_molar=0.15), seed=42)
        mol_index = inserter._build_molecule_index_from_structure(buggy_structure)

        # With the defense-in-depth fix, the method should compute nmolecules
        # from atom counts instead of returning None
        assert mol_index is not None, (
            "_build_molecule_index_from_structure should not return None when "
            "ice_atom_count > 0 but ice_nmolecules = 0 (should fall back to atom count)"
        )
        assert len(mol_index) > 0, (
            "molecule_index should have entries even when ice_nmolecules was 0"
        )

        # Verify ice entries were created
        ice_entries = [m for m in mol_index if m.mol_type == "ice"]
        assert len(ice_entries) > 0, (
            f"Should have ice entries in molecule_index, got {mol_index}"
        )

        # Verify water entries were created
        water_entries = [m for m in mol_index if m.mol_type == "water"]
        assert len(water_entries) > 0, (
            f"Should have water entries in molecule_index, got {mol_index}"
        )


# ── Liquid volume calculation tests ──────────────────────────────────────────


class TestLiquidVolumeFromStructureNmolecules:
    """Verify liquid volume can be computed directly from structure.nmolecules fields."""

    def test_liquid_volume_from_custom_molecule_structure(self, interface_slab):
        """Liquid volume should be computable from CustomMoleculeStructure.water_nmolecules."""
        config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            molecule_count=3,
        )
        inserter = CustomMoleculeInserter(config)
        custom = inserter.place_random(interface_slab, 3)

        # Before fix: getattr(custom, 'water_nmolecules', 0) → 0 → volume=0
        # After fix: getattr(custom, 'water_nmolecules', 0) → correct count → volume > 0
        water_nmols = getattr(custom, 'water_nmolecules', 0)
        assert water_nmols > 0, "water_nmolecules should not be 0"

        liquid_volume = water_nmols * WATER_VOLUME_NM3
        assert liquid_volume > 0, "Liquid volume should be positive"

        # Should match the volume computed from the interface structure
        interface_volume = custom.interface_structure.water_nmolecules * WATER_VOLUME_NM3
        assert abs(liquid_volume - interface_volume) < 1e-10, (
            f"Volume mismatch: {liquid_volume} vs {interface_volume}"
        )

    def test_liquid_volume_from_solute_structure(self, interface_slab):
        """Liquid volume should be computable from SoluteStructure.water_nmolecules."""
        config = SoluteConfig(concentration_molar=0.3, solute_type='CH4')
        inserter = SoluteInserter(config=config, seed=42)
        solute = inserter.insert_solutes(interface_slab, config)

        # Before fix: getattr(solute, 'water_nmolecules', 0) → 0 → volume=0
        # After fix: getattr(solute, 'water_nmolecules', 0) → correct count → volume > 0
        water_nmols = getattr(solute, 'water_nmolecules', 0)
        assert water_nmols > 0, "water_nmolecules should not be 0"

        liquid_volume = water_nmols * WATER_VOLUME_NM3
        assert liquid_volume > 0, "Liquid volume should be positive"
