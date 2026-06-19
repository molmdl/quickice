"""End-to-end tests for solute insertion pipeline (Workflow 6).

Tests the solute insertion pipeline end-to-end: insertion from Interface source,
insertion from Custom Molecule source, CH4 and THF solutes, CH4_H/CH4_L
coexistence (P0 critical test S3), zero concentration handling, and attribute
propagation through the workflow chain.

Uses shared conftest.py fixtures (interface_slab, interface_hydrate_slab)
and builds CustomMoleculeStructure inline for custom-source tests.
"""

import numpy as np
import pytest
from pathlib import Path
from scipy.spatial import cKDTree

from quickice.structure_generation.solute_inserter import SoluteInserter, AVOGADRO
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.types import (
    SoluteConfig,
    SoluteStructure,
    CustomMoleculeConfig,
    CustomMoleculeStructure,
    InterfaceConfig,
    InterfaceStructure,
    HydrateConfig,
    WATER_VOLUME_NM3,
)
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry


# ── Test data paths ──────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent / "quickice" / "data" / "custom"
ETOH_GRO = DATA_DIR / "etoh.gro"
ETOH_ITP = DATA_DIR / "etoh.itp"
ETOH_ATOM_COUNT = 9  # Ethanol has 9 atoms

# Atoms per solute type (from ITP files)
CH4_ATOMS_PER_MOLECULE = 5
THF_ATOMS_PER_MOLECULE = 13


# ════════════════════════════════════════════════════════════════════════════
# Basic insertion tests (Workflow 6b — from Interface source)
# ════════════════════════════════════════════════════════════════════════════


class TestSoluteFromInterfaceSource:
    """Tests for solute insertion from Interface source (Workflow 6b)."""

    def test_solute_ch4_from_interface_source(self, interface_slab):
        """CH4 solute insertion from Interface source should produce SoluteStructure.

        SoluteInserter with 0.5 M CH4 should place molecules in the liquid
        region, producing n_molecules > 0 and positions with 5 atoms per CH4.
        """
        config = SoluteConfig(concentration_molar=0.5, solute_type="CH4")
        inserter = SoluteInserter(config=config, seed=42)
        solute = inserter.insert_solutes(interface_slab)

        assert isinstance(solute, SoluteStructure)
        assert solute.n_molecules > 0, (
            f"Expected >0 CH4 molecules at 0.5 M, got {solute.n_molecules}"
        )
        assert solute.solute_type == "CH4", (
            f"solute_type should be 'CH4', got '{solute.solute_type}'"
        )
        assert solute.positions.shape[0] == solute.n_molecules * CH4_ATOMS_PER_MOLECULE, (
            f"Expected {solute.n_molecules * CH4_ATOMS_PER_MOLECULE} atoms, "
            f"got {solute.positions.shape[0]}"
        )

    def test_solute_thf_from_interface_source(self, interface_slab):
        """THF solute insertion from Interface source should produce 13-atom molecules.

        THF has 13 atoms per molecule (5 heavy atoms + 8 hydrogens).
        This is the P1 test S2 from the plan.
        """
        config = SoluteConfig(concentration_molar=0.5, solute_type="THF")
        inserter = SoluteInserter(config=config, seed=42)
        solute = inserter.insert_solutes(interface_slab)

        assert isinstance(solute, SoluteStructure)
        assert solute.n_molecules > 0, (
            f"Expected >0 THF molecules at 0.5 M, got {solute.n_molecules}"
        )
        assert solute.solute_type == "THF", (
            f"solute_type should be 'THF', got '{solute.solute_type}'"
        )
        assert solute.positions.shape[0] == solute.n_molecules * THF_ATOMS_PER_MOLECULE, (
            f"Expected {solute.n_molecules * THF_ATOMS_PER_MOLECULE} atoms for THF, "
            f"got {solute.positions.shape[0]}"
        )

    def test_solutes_in_liquid_region_only(self, interface_slab):
        """Each solute molecule's center of mass should be within liquid region bounds.

        Solute molecules must be placed in the liquid (water) region, not in
        the ice region or outside the simulation box.
        """
        config = SoluteConfig(concentration_molar=0.5, solute_type="CH4")
        inserter = SoluteInserter(config=config, seed=42)
        solute = inserter.insert_solutes(interface_slab)

        if solute.n_molecules == 0:
            pytest.skip("No molecules placed — volume may be too small")

        # Get liquid region bounds from original interface
        ice_count = interface_slab.ice_atom_count
        water_count = interface_slab.water_atom_count
        liquid_positions = interface_slab.positions[ice_count:ice_count + water_count]
        liquid_min = liquid_positions.min(axis=0)
        liquid_max = liquid_positions.max(axis=0)

        # Check each molecule's center of mass
        tolerance = 0.2  # nm — molecules extend beyond COM
        for start, end in solute.molecule_indices:
            mol_positions = solute.positions[start:end]
            com = mol_positions.mean(axis=0)

            for dim in range(3):
                assert com[dim] >= liquid_min[dim] - tolerance, (
                    f"Molecule COM[{dim}] = {com[dim]:.3f} below liquid min "
                    f"{liquid_min[dim]:.3f} - {tolerance}"
                )
                assert com[dim] <= liquid_max[dim] + tolerance, (
                    f"Molecule COM[{dim}] = {com[dim]:.3f} above liquid max "
                    f"{liquid_max[dim]:.3f} + {tolerance}"
                )

    def test_no_solute_solute_overlap(self, interface_slab):
        """No two solute molecules should overlap beyond min_separation.

        Uses cKDTree to check minimum pairwise distance between molecules
        (center-of-mass distance), ensuring the minimum separation constraint
        is satisfied between different molecules, not just atoms within one.
        """
        min_sep = 0.3  # nm (default SoluteConfig.min_separation)
        config = SoluteConfig(concentration_molar=0.5, solute_type="CH4", min_separation=min_sep)
        inserter = SoluteInserter(config=config, seed=42)
        solute = inserter.insert_solutes(interface_slab)

        if solute.n_molecules <= 1:
            pytest.skip("Need at least 2 molecules for overlap check")

        # Compute center-of-mass for each molecule
        molecule_coms = []
        for start, end in solute.molecule_indices:
            mol_positions = solute.positions[start:end]
            molecule_coms.append(mol_positions.mean(axis=0))

        com_array = np.array(molecule_coms)
        com_tree = cKDTree(com_array)

        # Check minimum pairwise distance between different molecules
        for i, com in enumerate(molecule_coms):
            dist, idx = com_tree.query(com, k=2)  # k=2: self + nearest
            # dist[0] = 0 (self), dist[1] = nearest neighbor
            if len(molecule_coms) > 1:
                nearest_dist = dist[1] if len(dist) > 1 else dist[0]
                assert nearest_dist >= min_sep * 0.5, (
                    f"Molecule {i} COM too close to molecule {idx[1]}: "
                    f"distance = {nearest_dist:.4f} nm < {min_sep * 0.5} nm"
                )

    def test_zero_concentration_no_solutes(self, interface_slab):
        """Zero concentration should produce zero solutes without crash.

        SoluteConfig(concentration_molar=0.0) should result in
        n_molecules == 0 and empty positions, not an exception.
        """
        config = SoluteConfig(concentration_molar=0.0, solute_type="CH4")
        inserter = SoluteInserter(config=config, seed=42)
        solute = inserter.insert_solutes(interface_slab)

        assert solute.n_molecules == 0, (
            f"Zero concentration should give 0 molecules, got {solute.n_molecules}"
        )
        assert solute.positions.shape == (0, 3), (
            f"Zero molecules should have (0, 3) positions, got {solute.positions.shape}"
        )
        assert solute.molecule_indices == [], (
            f"Zero molecules should have empty molecule_indices, got {solute.molecule_indices}"
        )


# ════════════════════════════════════════════════════════════════════════════
# P0 Critical: CH4_H/CH4_L coexistence (S3)
# ════════════════════════════════════════════════════════════════════════════


class TestCH4HCH4LCoexistence:
    """P0 critical tests for CH4_H (hydrate) and CH4_L (liquid) coexistence (S3)."""

    def test_ch4_h_ch4_l_coexistence_in_registry(self, interface_hydrate_slab):
        """CH4_H and CH4_L should coexist with distinct names in MoleculetypeRegistry.

        This is the P0 S3 test. When a hydrate interface has CH4 guests
        (registered as CH4_H) and CH4 liquid solutes are inserted (registered
        as CH4_L), the registry must distinguish both with unique names.
        """
        config = SoluteConfig(concentration_molar=0.3, solute_type="CH4")
        inserter = SoluteInserter(config=config, seed=42)

        # Register hydrate guest first (simulating hydrate export workflow)
        inserter.registry.register_hydrate_guest("CH4")

        # Insert solutes
        solute = inserter.insert_solutes(interface_hydrate_slab)

        # Verify BOTH hydrate guest AND liquid solute are in registry
        registry = solute.registry
        assert "hydrate_CH4" in registry._registered, (
            f"hydrate_CH4 should be registered, keys: {list(registry._registered.keys())}"
        )
        assert "liquid_CH4" in registry._registered, (
            f"liquid_CH4 should be registered, keys: {list(registry._registered.keys())}"
        )

        # Verify DISTINCT names
        ch4_h_name = registry.get_gromacs_name("hydrate_CH4")
        ch4_l_name = registry.get_gromacs_name("liquid_CH4")

        assert ch4_h_name == "CH4_H", (
            f"Expected 'CH4_H', got '{ch4_h_name}'"
        )
        assert ch4_l_name == "CH4_L", (
            f"Expected 'CH4_L', got '{ch4_l_name}'"
        )
        assert ch4_h_name != ch4_l_name, (
            f"CH4_H and CH4_L must be distinct: both '{ch4_h_name}'"
        )

    def test_hydrate_guests_preserved_after_solute_insertion(self, interface_hydrate_slab):
        """After inserting CH4 solutes, hydrate guests should still be present.

        The solute insertion modifies the interface structure (water removal)
        but must NOT remove hydrate guest molecules from the cage positions.
        """
        config = SoluteConfig(concentration_molar=0.3, solute_type="CH4")
        inserter = SoluteInserter(config=config, seed=42)
        solute = inserter.insert_solutes(interface_hydrate_slab)

        # Verify guest molecules are still present in the modified interface
        assert solute.interface_structure.guest_nmolecules > 0, (
            f"Guest molecules should be preserved after solute insertion, "
            f"got guest_nmolecules={solute.interface_structure.guest_nmolecules}"
        )
        assert solute.interface_structure.guest_atom_count > 0, (
            f"Guest atoms should be present after solute insertion, "
            f"got guest_atom_count={solute.interface_structure.guest_atom_count}"
        )


# ════════════════════════════════════════════════════════════════════════════
# From Custom Molecule source (Workflow 6c)
# ════════════════════════════════════════════════════════════════════════════


class TestSoluteFromCustomMoleculeSource:
    """Tests for solute insertion from Custom Molecule source (Workflow 6c)."""

    def test_solute_from_custom_molecule_source(self, interface_slab):
        """Solute insertion from CustomMoleculeStructure should preserve custom attributes.

        Workflow: Interface → Custom Molecule → Solute. The SoluteInserter
        receives a CustomMoleculeStructure (not a plain InterfaceStructure)
        and must propagate custom molecule attributes through.
        """
        # First, place custom molecules on interface
        custom_config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            molecule_count=3,
        )
        custom_inserter = CustomMoleculeInserter(custom_config)
        custom = custom_inserter.place_random(interface_slab, 3)

        # Then, insert solutes from the custom molecule structure
        solute_config = SoluteConfig(concentration_molar=0.5, solute_type="CH4")
        solute_inserter = SoluteInserter(config=solute_config, seed=42)
        solute = solute_inserter.insert_solutes(custom)

        assert isinstance(solute, SoluteStructure)
        assert solute.custom_molecule_count > 0, (
            f"Custom molecule count should be preserved, "
            f"got {solute.custom_molecule_count}"
        )
        assert solute.n_molecules > 0, (
            f"Solute molecules should be placed, got {solute.n_molecules}"
        )

    def test_solute_custom_attrs_preserved(self, interface_slab):
        """Custom molecule attributes should propagate through SoluteStructure.

        After inserting solutes from a CustomMoleculeStructure, the
        SoluteStructure should carry forward the custom molecule metadata:
        positions, atom names, moleculetype name, and file paths.
        """
        # Place custom molecules first
        custom_config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=ETOH_GRO,
            itp_path=ETOH_ITP,
            molecule_count=3,
        )
        custom_inserter = CustomMoleculeInserter(custom_config)
        custom = custom_inserter.place_random(interface_slab, 3)

        # Insert solutes
        solute_config = SoluteConfig(concentration_molar=0.5, solute_type="CH4")
        solute_inserter = SoluteInserter(config=solute_config, seed=42)
        solute = solute_inserter.insert_solutes(custom)

        # Verify custom molecule attributes are propagated
        assert solute.custom_molecule_atom_count > 0, (
            f"custom_molecule_atom_count should be > 0, got {solute.custom_molecule_atom_count}"
        )
        assert solute.custom_molecule_positions is not None, (
            "custom_molecule_positions should not be None"
        )
        assert solute.custom_molecule_atom_names is not None, (
            "custom_molecule_atom_names should not be None"
        )
        assert len(solute.custom_molecule_atom_names) == solute.custom_molecule_atom_count, (
            f"Atom names count ({len(solute.custom_molecule_atom_names)}) != "
            f"atom count ({solute.custom_molecule_atom_count})"
        )
        assert solute.custom_molecule_moleculetype != "", (
            f"custom_molecule_moleculetype should not be empty, "
            f"got '{solute.custom_molecule_moleculetype}'"
        )
        assert solute.custom_gro_path is not None, (
            "custom_gro_path should not be None"
        )
        assert solute.custom_itp_path is not None, (
            "custom_itp_path should not be None"
        )


# ════════════════════════════════════════════════════════════════════════════
# Molecule count calculation
# ════════════════════════════════════════════════════════════════════════════


class TestSoluteMoleculeCount:
    """Tests for solute molecule count calculation from concentration."""

    def test_solute_molecule_count_from_concentration(self, interface_slab):
        """calculate_molecule_count(C, V) should return a positive integer.

        For a reasonable concentration (1.0 M) and liquid volume, the
        molecule count should be a positive integer.
        """
        liquid_volume_nm3 = interface_slab.water_nmolecules * WATER_VOLUME_NM3
        inserter = SoluteInserter(seed=42)

        count = inserter.calculate_molecule_count(1.0, liquid_volume_nm3)

        assert isinstance(count, int), f"Should return int, got {type(count)}"
        assert count > 0, (
            f"At 1.0 M with {liquid_volume_nm3:.1f} nm³, count should be > 0"
        )

    def test_solute_molecule_count_approximately_correct(self, interface_slab):
        """For 0.5 M concentration, molecule count should match N = C × V × NA.

        The calculated molecule count should be within ±1 of the expected
        value from the formula N = C_M × V_L × NA, where V_L = V_nm3 × 1e-24.
        """
        concentration = 0.5  # mol/L
        liquid_volume_nm3 = interface_slab.water_nmolecules * WATER_VOLUME_NM3
        volume_liters = liquid_volume_nm3 * 1e-24
        expected_count = int(round(concentration * volume_liters * AVOGADRO))

        inserter = SoluteInserter(
            config=SoluteConfig(concentration_molar=concentration, solute_type="CH4"),
            seed=42,
        )
        actual_count = inserter.calculate_molecule_count(concentration, liquid_volume_nm3)

        assert abs(actual_count - expected_count) <= 1, (
            f"Molecule count off by more than ±1: "
            f"actual={actual_count}, expected={expected_count}"
        )


# ════════════════════════════════════════════════════════════════════════════
# S4/S5 combinations (P2)
# ════════════════════════════════════════════════════════════════════════════


class TestS4S5Combinations:
    """P2 tests for hydrate/liquid coexistence combinations (S4, S5)."""

    def test_hydrate_thf_thf_liquid_coexistence(self, interface_hydrate_slab):
        """THF hydrate guests and THF liquid solutes should be distinct in registry.

        This is S4: Hydrate sI+THF interface → insert THF liquid solutes.
        THF_H (hydrate) and THF_L (liquid) must be registered with distinct
        names in MoleculetypeRegistry.

        Note: The shared interface_hydrate_slab fixture uses CH4 hydrate.
        We generate a THF hydrate interface inline for this test.
        """
        # Generate THF hydrate interface inline
        from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator

        gen = HydrateStructureGenerator()
        thf_config = HydrateConfig(
            lattice_type="sI",
            guest_type="thf",
            supercell_x=1,
            supercell_y=1,
            supercell_z=1,
        )
        thf_struct = gen.generate(thf_config)
        thf_candidate = thf_struct.to_candidate()

        iface_config = InterfaceConfig(
            mode="slab",
            box_x=3.0,
            box_y=3.0,
            box_z=8.0,
            seed=42,
            ice_thickness=2.0,
            water_thickness=4.0,
        )
        thf_interface = generate_interface(thf_candidate, iface_config)

        # Register THF hydrate guest first
        solute_config = SoluteConfig(concentration_molar=0.3, solute_type="THF")
        inserter = SoluteInserter(config=solute_config, seed=42)
        inserter.registry.register_hydrate_guest("THF")

        # Insert THF liquid solutes
        solute = inserter.insert_solutes(thf_interface)

        # Verify THF_H and THF_L are both in registry with distinct names
        registry = solute.registry
        assert "hydrate_THF" in registry._registered, (
            f"hydrate_THF should be registered, keys: {list(registry._registered.keys())}"
        )
        assert "liquid_THF" in registry._registered, (
            f"liquid_THF should be registered, keys: {list(registry._registered.keys())}"
        )

        thf_h_name = registry.get_gromacs_name("hydrate_THF")
        thf_l_name = registry.get_gromacs_name("liquid_THF")

        assert thf_h_name == "THF_H", f"Expected 'THF_H', got '{thf_h_name}'"
        assert thf_l_name == "THF_L", f"Expected 'THF_L', got '{thf_l_name}'"
        assert thf_h_name != thf_l_name, (
            f"THF_H and THF_L must be distinct: both '{thf_h_name}'"
        )

    def test_hydrate_ch4_thf_liquid_mixed(self, interface_hydrate_slab):
        """CH4 hydrate + THF liquid solutes should have both molecule types.

        This is S5: Hydrate sI+CH4 interface → insert THF liquid solutes.
        Both CH4 (from hydrate) and THF (from solute) should be present.
        """
        # Insert THF solutes into CH4 hydrate interface
        solute_config = SoluteConfig(concentration_molar=0.3, solute_type="THF")
        inserter = SoluteInserter(config=solute_config, seed=42)

        # Register CH4 hydrate guest
        inserter.registry.register_hydrate_guest("CH4")

        solute = inserter.insert_solutes(interface_hydrate_slab)

        # Verify CH4 hydrate guest in registry
        registry = solute.registry
        assert "hydrate_CH4" in registry._registered, (
            f"hydrate_CH4 should be registered, keys: {list(registry._registered.keys())}"
        )

        # Verify THF liquid solute in registry
        assert "liquid_THF" in registry._registered, (
            f"liquid_THF should be registered, keys: {list(registry._registered.keys())}"
        )

        # Verify solute is THF type
        assert solute.solute_type == "THF", (
            f"solute_type should be 'THF', got '{solute.solute_type}'"
        )
        assert solute.n_molecules > 0, (
            f"Should have placed THF molecules, got {solute.n_molecules}"
        )

        # Verify hydrate guests are preserved
        assert solute.interface_structure.guest_nmolecules > 0, (
            "CH4 guests should be preserved after THF solute insertion"
        )


# ════════════════════════════════════════════════════════════════════════════
# Attribute propagation
# ════════════════════════════════════════════════════════════════════════════


class TestSoluteAttributePropagation:
    """Tests for attribute propagation through solute insertion workflow."""

    def test_water_removal_after_solute_insertion(self, interface_slab):
        """Water atom count should decrease after solute insertion.

        The _remove_overlapping_water() logic removes water molecules that
        overlap with placed solutes, so the interface structure within
        SoluteStructure should have fewer water atoms than the original.
        """
        config = SoluteConfig(concentration_molar=0.5, solute_type="CH4")
        inserter = SoluteInserter(config=config, seed=42)
        solute = inserter.insert_solutes(interface_slab)

        assert solute.interface_structure.water_atom_count < interface_slab.water_atom_count, (
            f"Water atoms should decrease after solute insertion: "
            f"{solute.interface_structure.water_atom_count} >= {interface_slab.water_atom_count}"
        )

    def test_solute_molecule_indices_valid(self, interface_slab):
        """Each (start, end) in molecule_indices should map to correct atom range.

        For CH4 solutes, each molecule index pair (start, end) should satisfy
        end - start == 5 (5 atoms per CH4 molecule).
        """
        config = SoluteConfig(concentration_molar=0.5, solute_type="CH4")
        inserter = SoluteInserter(config=config, seed=42)
        solute = inserter.insert_solutes(interface_slab)

        if solute.n_molecules == 0:
            pytest.skip("No molecules placed")

        expected_atoms = CH4_ATOMS_PER_MOLECULE  # 5 for CH4
        for i, (start, end) in enumerate(solute.molecule_indices):
            assert end - start == expected_atoms, (
                f"Molecule {i}: expected {expected_atoms} atoms, "
                f"got {end - start} (indices [{start}, {end}))"
            )
            # Verify positions slice is valid
            mol_positions = solute.positions[start:end]
            assert mol_positions.shape == (expected_atoms, 3), (
                f"Molecule {i} positions shape: expected ({expected_atoms}, 3), "
                f"got {mol_positions.shape}"
            )

    def test_thf_molecule_indices_valid(self, interface_slab):
        """THF molecule indices should have 13 atoms per molecule.

        THF has 13 atoms (5 heavy + 8 hydrogens), so each molecule index
        pair should satisfy end - start == 13.
        """
        config = SoluteConfig(concentration_molar=0.5, solute_type="THF")
        inserter = SoluteInserter(config=config, seed=42)
        solute = inserter.insert_solutes(interface_slab)

        if solute.n_molecules == 0:
            pytest.skip("No molecules placed")

        expected_atoms = THF_ATOMS_PER_MOLECULE  # 13 for THF
        for i, (start, end) in enumerate(solute.molecule_indices):
            assert end - start == expected_atoms, (
                f"THF molecule {i}: expected {expected_atoms} atoms, "
                f"got {end - start} (indices [{start}, {end}))"
            )

    def test_solute_cell_matches_interface(self, interface_slab):
        """SoluteStructure.cell should match the source InterfaceStructure.cell.

        The solute inherits the simulation box from the interface structure.
        """
        config = SoluteConfig(concentration_molar=0.5, solute_type="CH4")
        inserter = SoluteInserter(config=config, seed=42)
        solute = inserter.insert_solutes(interface_slab)

        np.testing.assert_array_equal(
            solute.cell, interface_slab.cell,
            err_msg="Solute cell should match interface cell"
        )
