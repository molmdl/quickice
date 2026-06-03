"""End-to-end tests for ion insertion (Workflow 7).

Tests the ion insertion pipeline: Na+/Cl- insertion from Interface, Custom
Molecule, and Solute sources, the CRITICAL SoluteStructure→IonInserter
AttributeError bug (P0 I5), charge neutrality verification, attribute
propagation, and ion count correctness.

Uses shared conftest.py fixtures (interface_slab, interface_hydrate_slab)
and builds CustomMoleculeStructure/SoluteStructure inline for source-variant
tests.

IMPORTANT: test_solute_structure_attribute_error_bug exposes a known P0 bug
where SoluteStructure.molecule_indices (tuples) vs IonInserter expecting
molecule_index (list of MoleculeIndex) causes AttributeError.
"""

import numpy as np
import pytest
from pathlib import Path

from quickice.structure_generation.ion_inserter import IonInserter, AVOGADRO
from quickice.structure_generation.solute_inserter import SoluteInserter
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
from quickice.structure_generation.types import (
    IonConfig,
    IonStructure,
    SoluteConfig,
    SoluteStructure,
    CustomMoleculeConfig,
    CustomMoleculeStructure,
)


# ── Test data paths ──────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent / "quickice" / "data" / "custom"
ETOH_GRO = DATA_DIR / "etoh.gro"
ETOH_ITP = DATA_DIR / "etoh.itp"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _liquid_volume_nm3(structure) -> float:
    """Estimate liquid volume from water molecule count (TIP4P: 0.0299 nm³/mol)."""
    water_nmolecules = getattr(structure, 'water_nmolecules', 0)
    if water_nmolecules == 0:
        water_atom_count = getattr(structure, 'water_atom_count', 0)
        water_nmolecules = water_atom_count // 4 if water_atom_count > 0 else 0
    return water_nmolecules * 0.0299


def _insert_custom_molecules(interface, n_molecules=3, seed=42):
    """Helper: place custom ethanol molecules on interface."""
    config = CustomMoleculeConfig(
        placement_mode="random",
        gro_path=ETOH_GRO,
        itp_path=ETOH_ITP,
        molecule_count=n_molecules,
    )
    inserter = CustomMoleculeInserter(config)
    return inserter.place_random(interface, n_molecules)


# ══════════════════════════════════════════════════════════════════════════════
# Basic ion insertion tests (I1–I4)
# ══════════════════════════════════════════════════════════════════════════════


class TestIonFromInterfaceSource:
    """Tests for ion insertion from Interface source (I1)."""

    def test_ion_from_interface_source(self, interface_slab):
        """Ion insertion from Interface source produces charge-neutral Na+/Cl- pairs.

        Uses IonInserter with 0.15 M concentration. Verifies:
        - na_count > 0, cl_count > 0
        - na_count == cl_count (charge neutrality, invariant #16)
        - IonStructure is returned with valid positions and cell
        """
        config = IonConfig(concentration_molar=0.15)
        inserter = IonInserter(config=config, seed=42)

        volume = _liquid_volume_nm3(interface_slab)
        ion_pairs = inserter.calculate_ion_pairs(0.15, volume)

        ion = inserter.replace_water_with_ions(interface_slab, ion_pairs)

        assert isinstance(ion, IonStructure)
        assert ion.na_count > 0, "Should have Na+ ions at 0.15 M"
        assert ion.cl_count > 0, "Should have Cl- ions at 0.15 M"
        assert ion.na_count == ion.cl_count, (
            f"Charge neutrality violated: na={ion.na_count}, cl={ion.cl_count}"
        )
        assert ion.positions.shape[1] == 3, "Positions should be (N, 3)"
        assert np.all(np.isfinite(ion.positions)), "No NaN/Inf in positions"
        assert ion.cell.shape == (3, 3), "Cell should be (3, 3)"


class TestIonChargeNeutrality:
    """Tests for charge neutrality across multiple concentrations (invariant #16)."""

    @pytest.mark.parametrize("concentration", [0.05, 0.15, 0.5])
    def test_ion_charge_neutrality(self, interface_slab, concentration):
        """Charge neutrality: na_count == cl_count for any concentration.

        This is structural invariant #16. It must hold regardless of
        concentration value, ion count, or overlap checking outcomes.
        """
        config = IonConfig(concentration_molar=concentration)
        inserter = IonInserter(config=config, seed=42)

        volume = _liquid_volume_nm3(interface_slab)
        ion_pairs = inserter.calculate_ion_pairs(concentration, volume)

        ion = inserter.replace_water_with_ions(interface_slab, ion_pairs)

        assert ion.na_count == ion.cl_count, (
            f"Charge neutrality violated at {concentration} M: "
            f"na={ion.na_count}, cl={ion.cl_count}"
        )


class TestIonFromHydrateInterface:
    """Tests for ion insertion from hydrate interface (I2)."""

    def test_ion_from_hydrate_interface_source(self, interface_hydrate_slab):
        """Ion insertion from hydrate interface preserves guest molecules.

        The interface_hydrate_slab has CH4 guest molecules from hydrate.
        After ion insertion, guest molecules should still be present.
        """
        config = IonConfig(concentration_molar=0.15)
        inserter = IonInserter(config=config, seed=42)

        volume = _liquid_volume_nm3(interface_hydrate_slab)
        ion_pairs = inserter.calculate_ion_pairs(0.15, volume)

        ion = inserter.replace_water_with_ions(interface_hydrate_slab, ion_pairs)

        assert ion.guest_nmolecules > 0, (
            "Guest molecules from hydrate should be preserved after ion insertion"
        )
        assert ion.na_count == ion.cl_count, "Charge neutrality must hold"
        assert ion.guest_atom_count > 0, "Guest atoms should be preserved"


class TestIonFromCustomMoleculeSource:
    """Tests for ion insertion from Custom Molecule source (I3, I4)."""

    def test_ion_from_custom_molecule_source(self, interface_slab):
        """Ion insertion from CustomMoleculeSource preserves custom attributes (I3).

        CustomMoleculeStructure has molecule_index (list of MoleculeIndex),
        so IonInserter works directly. Custom molecule attributes should
        propagate through to IonStructure.
        """
        # First place custom molecules
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)

        # Insert ions into the CustomMoleculeStructure
        config = IonConfig(concentration_molar=0.15)
        inserter = IonInserter(config=config, seed=42)

        volume = _liquid_volume_nm3(custom)
        ion_pairs = inserter.calculate_ion_pairs(0.15, volume)

        ion = inserter.replace_water_with_ions(custom, ion_pairs)

        assert isinstance(ion, IonStructure)
        assert ion.na_count > 0, "Should have Na+ ions"
        assert ion.cl_count > 0, "Should have Cl- ions"
        assert ion.na_count == ion.cl_count, "Charge neutrality must hold"
        # Custom molecule attributes should propagate
        assert ion.custom_molecule_count > 0, (
            "Custom molecule count should propagate through ion insertion"
        )
        assert ion.custom_molecule_atom_count > 0, (
            "Custom molecule atom count should propagate through ion insertion"
        )


class TestIonPositions:
    """Tests for ion position validity (I1 positional test)."""

    def test_ion_positions_within_cell(self, interface_slab):
        """All ion positions should be within the cell boundaries.

        Ions replace water molecules, so they should fall within the
        simulation box defined by the cell vectors.
        """
        config = IonConfig(concentration_molar=0.15)
        inserter = IonInserter(config=config, seed=42)

        volume = _liquid_volume_nm3(interface_slab)
        ion_pairs = inserter.calculate_ion_pairs(0.15, volume)

        ion = inserter.replace_water_with_ions(interface_slab, ion_pairs)

        # Get cell box dimensions (diagonal for orthorhombic)
        box_diag = np.abs(np.diag(ion.cell))
        # Fractional coordinates check — ions should be within [0, L)
        for pos in ion.positions:
            frac = pos / box_diag
            # Allow small tolerance for numerical precision
            assert np.all(frac >= -0.01), (
                f"Ion position {pos} outside cell lower bound"
            )
            assert np.all(frac <= 1.01), (
                f"Ion position {pos} outside cell upper bound"
            )


# ══════════════════════════════════════════════════════════════════════════════
# P0 CRITICAL: SoluteStructure bug (I5)
# ══════════════════════════════════════════════════════════════════════════════


class TestSoluteStructureAttributeErrorBug:
    """P0 bug exposure: SoluteStructure → IonInserter raises AttributeError (I5).

    SoluteStructure has molecule_indices (list of tuples) but NOT molecule_index
    (list of MoleculeIndex). IonInserter.replace_water_with_ions checks
    structure.molecule_index on line 192, causing AttributeError when passed
    a SoluteStructure directly.

    The GUI works around this by passing solute.interface_structure instead.
    This test EXPOSES the bug so it can be tracked and fixed.
    """

    def test_solute_structure_attribute_error_bug(self, interface_slab):
        """P0: SoluteStructure → IonInserter raises AttributeError (BUG I5).

        SoluteStructure has molecule_indices (list of tuples) but NOT
        molecule_index (list of MoleculeIndex). IonInserter.replace_water_with_ions
        checks structure.molecule_index first, causing AttributeError.
        """
        # Insert solutes into interface
        solute_config = SoluteConfig(concentration_molar=0.3, solute_type='CH4')
        solute_inserter = SoluteInserter(config=solute_config, seed=42)
        solute = solute_inserter.insert_solutes(interface_slab, solute_config)

        # Confirm solute is a SoluteStructure
        assert isinstance(solute, SoluteStructure)

        # Try to insert ions into SoluteStructure directly
        ion_config = IonConfig(concentration_molar=0.15)
        ion_inserter = IonInserter(config=ion_config, seed=42)
        volume = _liquid_volume_nm3(solute.interface_structure)
        ion_pairs = ion_inserter.calculate_ion_pairs(0.15, volume)

        # This should raise AttributeError because SoluteStructure lacks molecule_index
        with pytest.raises(AttributeError, match="molecule_index"):
            ion_inserter.replace_water_with_ions(solute, ion_pairs)


class TestIonFromSoluteWorkaround:
    """Tests for the GUI workaround for SoluteStructure → IonInserter (I5 workaround).

    The GUI passes solute.interface_structure to IonInserter with solute attrs
    attached. This workaround produces valid IonStructure with all solute info.
    """

    def test_ion_from_solute_workaround(self, interface_slab):
        """Workaround: pass solute.interface_structure with solute attrs set.

        The GUI sets solute attributes on the interface_structure before
        passing to IonInserter. This should produce a valid IonStructure
        with solute information preserved.
        """
        # Insert solutes
        solute_config = SoluteConfig(concentration_molar=0.3, solute_type='CH4')
        solute_inserter = SoluteInserter(config=solute_config, seed=42)
        solute = solute_inserter.insert_solutes(interface_slab, solute_config)

        # Workaround: use solute.interface_structure with solute attrs attached
        interface_for_ions = solute.interface_structure
        interface_for_ions.solute_type = solute.solute_type
        interface_for_ions.solute_positions = solute.positions
        interface_for_ions.solute_atom_names = solute.atom_names
        interface_for_ions.solute_n_molecules = solute.n_molecules
        interface_for_ions.solute_molecule_indices = solute.molecule_indices
        interface_for_ions.solute_registry = solute.registry

        # Insert ions using the workaround structure
        ion_config = IonConfig(concentration_molar=0.15)
        ion_inserter = IonInserter(config=ion_config, seed=42)
        volume = _liquid_volume_nm3(interface_for_ions)
        ion_pairs = ion_inserter.calculate_ion_pairs(0.15, volume)

        ion = ion_inserter.replace_water_with_ions(interface_for_ions, ion_pairs)

        assert isinstance(ion, IonStructure)
        assert ion.na_count > 0, "Should have Na+ ions"
        assert ion.cl_count > 0, "Should have Cl- ions"
        assert ion.na_count == ion.cl_count, "Charge neutrality must hold"
        # Solute information should be preserved
        assert ion.solute_type == "CH4", (
            f"Solute type should be preserved: got '{ion.solute_type}'"
        )
        assert ion.solute_n_molecules > 0, (
            "Solute molecule count should be preserved"
        )
        assert ion.solute_positions is not None, (
            "Solute positions should be preserved"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Ion count and volume tests
# ══════════════════════════════════════════════════════════════════════════════


class TestIonCountCorrectness:
    """Tests for ion count correctness relative to concentration and volume."""

    def test_ion_count_approximately_correct(self, interface_slab):
        """Ion count should approximately match concentration × volume × NA.

        For 0.15 M NaCl, the expected ion pairs ≈ 0.15 × V_L × NA.
        Allow ±1 tolerance for rounding to nearest integer.
        """
        concentration = 0.15
        volume_nm3 = _liquid_volume_nm3(interface_slab)
        volume_liters = volume_nm3 * 1e-24
        expected_pairs = int(round(concentration * volume_liters * AVOGADRO))

        config = IonConfig(concentration_molar=concentration)
        inserter = IonInserter(config=config, seed=42)
        ion_pairs = inserter.calculate_ion_pairs(concentration, volume_nm3)

        assert ion_pairs == expected_pairs, (
            f"Expected {expected_pairs} ion pairs, got {ion_pairs}"
        )

        ion = inserter.replace_water_with_ions(interface_slab, ion_pairs)

        # Actual placed ions may be less due to overlap checking, but should be > 0
        actual_pairs = (ion.na_count + ion.cl_count) // 2
        assert actual_pairs > 0, "Should place at least one ion pair"

    def test_zero_concentration_no_ions(self, interface_slab):
        """Zero concentration should produce zero ions.

        IonConfig(concentration_molar=0.0) should yield na_count == 0
        and cl_count == 0.
        """
        config = IonConfig(concentration_molar=0.0)
        inserter = IonInserter(config=config, seed=42)

        volume = _liquid_volume_nm3(interface_slab)
        ion_pairs = inserter.calculate_ion_pairs(0.0, volume)

        ion = inserter.replace_water_with_ions(interface_slab, ion_pairs)

        assert ion.na_count == 0, "Zero concentration should give no Na+ ions"
        assert ion.cl_count == 0, "Zero concentration should give no Cl- ions"
        assert ion.na_count == ion.cl_count, "Charge neutrality even at zero"


# ══════════════════════════════════════════════════════════════════════════════
# Attribute propagation tests (I3, I4, I6, I7)
# ══════════════════════════════════════════════════════════════════════════════


class TestAttributePropagation:
    """Tests for attribute propagation through ion insertion."""

    def test_custom_attrs_propagate_through_ion(self, interface_slab):
        """Custom molecule attributes must propagate through ion insertion (I3).

        After ion insertion from CustomMoleculeStructure, the IonStructure
        should carry forward custom_molecule_count and
        custom_molecule_atom_count. Custom molecules are also tracked in
        molecule_index entries with mol_type='custom'.

        NOTE: custom_molecule_positions is None because CustomMoleculeStructure
        stores all positions in a combined array (not separate custom-only
        positions). The molecule_index tracks which entries are custom molecules.
        """
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)

        config = IonConfig(concentration_molar=0.15)
        inserter = IonInserter(config=config, seed=42)

        volume = _liquid_volume_nm3(custom)
        ion_pairs = inserter.calculate_ion_pairs(0.15, volume)

        ion = inserter.replace_water_with_ions(custom, ion_pairs)

        assert ion.custom_molecule_count > 0, (
            "Custom molecule count should propagate"
        )
        assert ion.custom_molecule_atom_count > 0, (
            "Custom molecule atom count should propagate"
        )
        # Verify custom molecules tracked in molecule_index
        custom_mols = [m for m in ion.molecule_index if m.mol_type == "custom"]
        assert len(custom_mols) > 0, (
            "Custom molecules should appear in molecule_index"
        )

    def test_guest_attrs_propagate_through_ion(self, interface_hydrate_slab):
        """Guest molecule attributes must propagate through ion insertion (I4).

        After ion insertion into hydrate interface, IonStructure should
        carry forward guest_nmolecules and guest_atom_count.
        """
        config = IonConfig(concentration_molar=0.15)
        inserter = IonInserter(config=config, seed=42)

        volume = _liquid_volume_nm3(interface_hydrate_slab)
        ion_pairs = inserter.calculate_ion_pairs(0.15, volume)

        ion = inserter.replace_water_with_ions(interface_hydrate_slab, ion_pairs)

        assert ion.guest_nmolecules > 0, (
            "Guest molecule count should propagate"
        )
        assert ion.guest_atom_count > 0, (
            "Guest atom count should propagate"
        )

    def test_solute_attrs_propagate_through_ion_workaround(self, interface_slab):
        """Solute attributes propagate through ion insertion via workaround (I6, I7).

        After ion insertion via workaround (using interface_structure with
        solute attrs set), verify solute_type, solute_n_molecules, and
        solute_positions are preserved.
        """
        # Insert solutes
        solute_config = SoluteConfig(concentration_molar=0.3, solute_type='CH4')
        solute_inserter = SoluteInserter(config=solute_config, seed=42)
        solute = solute_inserter.insert_solutes(interface_slab, solute_config)

        # Workaround: attach solute attrs to interface_structure
        interface_for_ions = solute.interface_structure
        interface_for_ions.solute_type = solute.solute_type
        interface_for_ions.solute_positions = solute.positions
        interface_for_ions.solute_atom_names = solute.atom_names
        interface_for_ions.solute_n_molecules = solute.n_molecules
        interface_for_ions.solute_molecule_indices = solute.molecule_indices
        interface_for_ions.solute_registry = solute.registry

        # Insert ions
        ion_config = IonConfig(concentration_molar=0.15)
        ion_inserter = IonInserter(config=ion_config, seed=42)
        volume = _liquid_volume_nm3(interface_for_ions)
        ion_pairs = ion_inserter.calculate_ion_pairs(0.15, volume)
        ion = ion_inserter.replace_water_with_ions(interface_for_ions, ion_pairs)

        assert ion.solute_type != "", (
            f"Solute type should be set, got '{ion.solute_type}'"
        )
        assert ion.solute_n_molecules > 0, (
            "Solute molecule count should be preserved"
        )
        assert ion.solute_positions is not None, (
            "Solute positions should be preserved"
        )
