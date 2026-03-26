"""Tests for structure generation mapping layer."""

import numpy as np
import pytest

# These imports will fail until we implement the modules
from quickice.structure_generation.types import Candidate, GenerationResult
from quickice.structure_generation.mapper import (
    PHASE_TO_GENICE,
    UNIT_CELL_MOLECULES,
    get_genice_lattice_name,
    calculate_supercell,
)
from quickice.structure_generation.errors import UnsupportedPhaseError


class TestPhaseToGenIceMapping:
    """Tests for phase ID to GenIce lattice name mapping."""

    def test_ice_ih_maps_to_ice1h(self):
        """Phase ID 'ice_ih' should map to GenIce lattice 'ice1h'."""
        assert get_genice_lattice_name("ice_ih") == "ice1h"

    def test_ice_ic_maps_to_ice1c(self):
        """Phase ID 'ice_ic' should map to GenIce lattice 'ice1c'."""
        assert get_genice_lattice_name("ice_ic") == "ice1c"

    def test_ice_ii_maps_to_ice2(self):
        """Phase ID 'ice_ii' should map to GenIce lattice 'ice2'."""
        assert get_genice_lattice_name("ice_ii") == "ice2"

    def test_ice_iii_maps_to_ice3(self):
        """Phase ID 'ice_iii' should map to GenIce lattice 'ice3'."""
        assert get_genice_lattice_name("ice_iii") == "ice3"

    def test_ice_v_maps_to_ice5(self):
        """Phase ID 'ice_v' should map to GenIce lattice 'ice5'."""
        assert get_genice_lattice_name("ice_v") == "ice5"

    def test_ice_vi_maps_to_ice6(self):
        """Phase ID 'ice_vi' should map to GenIce lattice 'ice6'."""
        assert get_genice_lattice_name("ice_vi") == "ice6"

    def test_ice_vii_maps_to_ice7(self):
        """Phase ID 'ice_vii' should map to GenIce lattice 'ice7'."""
        assert get_genice_lattice_name("ice_vii") == "ice7"

    def test_ice_viii_maps_to_ice8(self):
        """Phase ID 'ice_viii' should map to GenIce lattice 'ice8'."""
        assert get_genice_lattice_name("ice_viii") == "ice8"

    def test_unsupported_phase_raises_error(self):
        """Unsupported phase ID should raise UnsupportedPhaseError."""
        with pytest.raises(UnsupportedPhaseError) as exc_info:
            get_genice_lattice_name("ice_xxx")
        assert exc_info.value.phase_id == "ice_xxx"


class TestPhaseToGenIceDictionary:
    """Tests for the PHASE_TO_GENICE constant."""

    def test_has_all_8_phases(self):
        """PHASE_TO_GENICE should have all 8 supported phases."""
        expected_phases = {
            "ice_ih", "ice_ic", "ice_ii", "ice_iii",
            "ice_v", "ice_vi", "ice_vii", "ice_viii"
        }
        assert set(PHASE_TO_GENICE.keys()) == expected_phases

    def test_all_values_are_strings(self):
        """All GenIce lattice names should be strings."""
        for value in PHASE_TO_GENICE.values():
            assert isinstance(value, str)


class TestUnitCellMolecules:
    """Tests for the UNIT_CELL_MOLECULES constant."""

    def test_ice1h_has_4_molecules(self):
        """Ice 1h unit cell should have 4 molecules."""
        assert UNIT_CELL_MOLECULES["ice1h"] == 4

    def test_ice1c_has_8_molecules(self):
        """Ice 1c unit cell should have 8 molecules."""
        assert UNIT_CELL_MOLECULES["ice1c"] == 8

    def test_ice2_has_12_molecules(self):
        """Ice 2 unit cell should have 12 molecules."""
        assert UNIT_CELL_MOLECULES["ice2"] == 12

    def test_ice3_has_12_molecules(self):
        """Ice 3 unit cell should have 12 molecules."""
        assert UNIT_CELL_MOLECULES["ice3"] == 12

    def test_ice5_has_28_molecules(self):
        """Ice 5 unit cell should have 28 molecules."""
        assert UNIT_CELL_MOLECULES["ice5"] == 28

    def test_ice6_has_10_molecules(self):
        """Ice 6 unit cell should have 10 molecules (double network)."""
        assert UNIT_CELL_MOLECULES["ice6"] == 10

    def test_ice7_has_16_molecules(self):
        """Ice 7 unit cell should have 16 molecules (double network)."""
        assert UNIT_CELL_MOLECULES["ice7"] == 16

    def test_ice8_has_16_molecules(self):
        """Ice 8 unit cell should have 16 molecules (double network)."""
        assert UNIT_CELL_MOLECULES["ice8"] == 16

    def test_all_genice_lattices_have_molecule_counts(self):
        """All GenIce lattice names should have corresponding molecule counts."""
        for genice_name in PHASE_TO_GENICE.values():
            assert genice_name in UNIT_CELL_MOLECULES


class TestCalculateSupercell:
    """Tests for supercell calculation."""

    def test_supercell_100_molecules_ice1h(self):
        """Target 100 molecules with ice1h (4 per unit cell) should return 3x3x3 with 108 molecules."""
        supercell, actual = calculate_supercell(100, 4)
        expected_matrix = np.array([[3, 0, 0], [0, 3, 0], [0, 0, 3]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 108

    def test_supercell_50_molecules_ice1h(self):
        """Target 50 molecules with ice1h (4 per unit cell) should return 3x3x3 with 108 molecules."""
        supercell, actual = calculate_supercell(50, 4)
        expected_matrix = np.array([[3, 0, 0], [0, 3, 0], [0, 0, 3]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 108

    def test_supercell_10_molecules_ice1h(self):
        """Target 10 molecules with ice1h (4 per unit cell) should return 2x2x2 with 32 molecules."""
        supercell, actual = calculate_supercell(10, 4)
        expected_matrix = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 32

    def test_supercell_exact_multiple(self):
        """Target exactly 108 molecules (27*4) should return 3x3x3."""
        supercell, actual = calculate_supercell(108, 4)
        expected_matrix = np.array([[3, 0, 0], [0, 3, 0], [0, 0, 3]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 108

    def test_supercell_just_over_threshold(self):
        """Target 109 molecules should round up to 4x4x4."""
        supercell, actual = calculate_supercell(109, 4)
        expected_matrix = np.array([[4, 0, 0], [0, 4, 0], [0, 0, 4]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 256

    def test_supercell_minimum(self):
        """Target 1 molecule should return 1x1x1."""
        supercell, actual = calculate_supercell(1, 4)
        expected_matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 4

    def test_supercell_large_molecule_count(self):
        """Test with ice5 (28 molecules per unit cell)."""
        supercell, actual = calculate_supercell(100, 28)
        # 28 * 2^3 = 224 molecules
        expected_matrix = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 224


class TestCandidateDataclass:
    """Tests for Candidate dataclass."""

    def test_candidate_creation(self):
        """Candidate should be creatable with all required fields."""
        positions = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])
        atom_names = ["O", "H"]
        cell = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])

        candidate = Candidate(
            positions=positions,
            atom_names=atom_names,
            cell=cell,
            nmolecules=1,
            phase_id="ice_ih",
            seed=42
        )

        assert candidate.nmolecules == 1
        assert candidate.phase_id == "ice_ih"
        assert candidate.seed == 42
        np.testing.assert_array_equal(candidate.positions, positions)
        np.testing.assert_array_equal(candidate.cell, cell)

    def test_candidate_has_default_metadata(self):
        """Candidate should have default empty metadata dict."""
        candidate = Candidate(
            positions=np.array([[0.0, 0.0, 0.0]]),
            atom_names=["O"],
            cell=np.eye(3),
            nmolecules=1,
            phase_id="ice_ih",
            seed=0
        )
        assert candidate.metadata == {}

    def test_candidate_can_have_metadata(self):
        """Candidate can store metadata from Phase 2."""
        candidate = Candidate(
            positions=np.array([[0.0, 0.0, 0.0]]),
            atom_names=["O"],
            cell=np.eye(3),
            nmolecules=1,
            phase_id="ice_ih",
            seed=0,
            metadata={"density": 0.9167, "temperature": 273, "pressure": 0}
        )
        assert candidate.metadata["density"] == 0.9167
        assert candidate.metadata["temperature"] == 273


class TestGenerationResultDataclass:
    """Tests for GenerationResult dataclass."""

    def test_generation_result_creation(self):
        """GenerationResult should store candidate list and metadata."""
        candidates = [
            Candidate(
                positions=np.array([[0.0, 0.0, 0.0]]),
                atom_names=["O"],
                cell=np.eye(3),
                nmolecules=1,
                phase_id="ice_ih",
                seed=0
            )
        ]

        result = GenerationResult(
            candidates=candidates,
            requested_nmolecules=100,
            actual_nmolecules=108,
            phase_id="ice_ih",
            phase_name="Ice Ih",
            density=0.9167,
            was_rounded=True
        )

        assert len(result.candidates) == 1
        assert result.requested_nmolecules == 100
        assert result.actual_nmolecules == 108
        assert result.was_rounded is True

    def test_generation_result_no_rounding(self):
        """GenerationResult should indicate when no rounding occurred."""
        result = GenerationResult(
            candidates=[],
            requested_nmolecules=108,
            actual_nmolecules=108,
            phase_id="ice_ih",
            phase_name="Ice Ih",
            density=0.9167,
            was_rounded=False
        )
        assert result.was_rounded is False


class TestUnsupportedPhaseError:
    """Tests for UnsupportedPhaseError exception."""

    def test_error_message_contains_phase_id(self):
        """Error should include the phase ID in the message."""
        error = UnsupportedPhaseError("Phase 'ice_xxx' is not supported", "ice_xxx")
        assert "ice_xxx" in str(error)
        assert error.phase_id == "ice_xxx"

    def test_error_inherits_from_structure_generation_error(self):
        """UnsupportedPhaseError should inherit from StructureGenerationError."""
        from quickice.structure_generation.errors import StructureGenerationError
        error = UnsupportedPhaseError("Test", "ice_xxx")
        assert isinstance(error, StructureGenerationError)
