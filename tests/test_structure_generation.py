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

    def test_ice1h_has_16_molecules(self):
        """Ice 1h unit cell should have 16 molecules."""
        assert UNIT_CELL_MOLECULES["ice1h"] == 16

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

    def test_ice8_has_64_molecules(self):
        """Ice 8 unit cell should have 64 molecules."""
        assert UNIT_CELL_MOLECULES["ice8"] == 64

    def test_all_genice_lattices_have_molecule_counts(self):
        """All GenIce lattice names should have corresponding molecule counts."""
        for genice_name in PHASE_TO_GENICE.values():
            assert genice_name in UNIT_CELL_MOLECULES


class TestCalculateSupercell:
    """Tests for supercell calculation."""

    def test_supercell_100_molecules_ice1h(self):
        """Target 100 molecules with ice1h (16 per unit cell) should return 2x2x2 with 128 molecules."""
        supercell, actual = calculate_supercell(100, 16)
        expected_matrix = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 128

    def test_supercell_50_molecules_ice1h(self):
        """Target 50 molecules with ice1h (16 per unit cell) should return 2x2x2 with 128 molecules."""
        supercell, actual = calculate_supercell(50, 16)
        expected_matrix = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 128

    def test_supercell_10_molecules_ice1h(self):
        """Target 10 molecules with ice1h (16 per unit cell) should return 1x1x1 with 16 molecules."""
        supercell, actual = calculate_supercell(10, 16)
        expected_matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 16

    def test_supercell_exact_multiple(self):
        """Target exactly 128 molecules should return 2x2x2."""
        supercell, actual = calculate_supercell(128, 16)
        expected_matrix = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 128

    def test_supercell_just_over_threshold(self):
        """Target 129 molecules should round up to 3x3x3."""
        supercell, actual = calculate_supercell(129, 16)
        expected_matrix = np.array([[3, 0, 0], [0, 3, 0], [0, 0, 3]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 432

    def test_supercell_minimum(self):
        """Target 1 molecule should return 1x1x1."""
        supercell, actual = calculate_supercell(1, 16)
        expected_matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        np.testing.assert_array_equal(supercell, expected_matrix)
        assert actual == 16

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


class TestIceStructureGenerator:
    """Tests for IceStructureGenerator class."""

    @pytest.fixture
    def phase_info_ice_ih(self):
        """Phase info for Ice Ih at 273K, 0MPa."""
        return {
            "phase_id": "ice_ih",
            "phase_name": "Ice Ih",
            "density": 0.9167,
            "temperature": 273,
            "pressure": 0,
        }

    def test_generator_initialization(self, phase_info_ice_ih):
        """Generator should initialize with correct attributes."""
        from quickice.structure_generation.generator import IceStructureGenerator

        gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)

        assert gen.phase_id == "ice_ih"
        assert gen.phase_name == "Ice Ih"
        assert gen.density == 0.9167
        assert gen.nmolecules == 100
        assert gen.lattice_name == "ice1h"
        assert gen.molecules_per_unit_cell == 16
        # 100 molecules with 16 per unit cell should give 2x2x2 supercell = 128 molecules
        assert gen.actual_nmolecules == 128

    def test_generator_supercell_calculation(self, phase_info_ice_ih):
        """Generator should calculate correct supercell matrix."""
        from quickice.structure_generation.generator import IceStructureGenerator

        gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)

        expected_matrix = np.array([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
        np.testing.assert_array_equal(gen.supercell_matrix, expected_matrix)

    def test_generate_single_returns_candidate(self, phase_info_ice_ih):
        """_generate_single should return a Candidate object."""
        from quickice.structure_generation.generator import IceStructureGenerator

        gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)
        candidate = gen._generate_single(seed=1000)

        assert isinstance(candidate, Candidate)
        assert candidate.phase_id == "ice_ih"
        assert candidate.seed == 1000
        assert candidate.nmolecules == 128

    def test_generate_single_has_valid_positions(self, phase_info_ice_ih):
        """Generated candidate should have valid numpy positions."""
        from quickice.structure_generation.generator import IceStructureGenerator

        gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)
        candidate = gen._generate_single(seed=1000)

        # Check positions array
        assert isinstance(candidate.positions, np.ndarray)
        assert candidate.positions.shape[1] == 3  # 3D coordinates
        # 128 molecules * 3 atoms per molecule = 384 atoms
        assert candidate.positions.shape[0] == 384

        # Check that positions are finite
        assert np.all(np.isfinite(candidate.positions))
        # Cell should be around 1-3 nm
        assert np.all(np.abs(candidate.positions) < 10)

    def test_generate_single_has_atom_names(self, phase_info_ice_ih):
        """Generated candidate should have correct atom names."""
        from quickice.structure_generation.generator import IceStructureGenerator

        gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)
        candidate = gen._generate_single(seed=1000)

        # Check atom names
        assert isinstance(candidate.atom_names, list)
        assert len(candidate.atom_names) == 384  # 128 molecules * 3 atoms

        # Check OHH pattern
        for i in range(0, len(candidate.atom_names), 3):
            assert candidate.atom_names[i] == "O"
            assert candidate.atom_names[i + 1] == "H"
            assert candidate.atom_names[i + 2] == "H"

    def test_generate_single_has_cell(self, phase_info_ice_ih):
        """Generated candidate should have valid cell dimensions."""
        from quickice.structure_generation.generator import IceStructureGenerator

        gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)
        candidate = gen._generate_single(seed=1000)

        # Check cell array
        assert isinstance(candidate.cell, np.ndarray)
        assert candidate.cell.shape == (3, 3)

        # Cell dimensions should be reasonable for 128 molecules at 0.9167 g/cm³
        # Volume ≈ (128 * 18 g/mol) / (0.9167 g/cm³ * 6.022e23) ≈ 4.18 nm³
        # Side length ≈ 1.6 nm
        volume = np.abs(np.linalg.det(candidate.cell))
        assert 2.0 < volume < 25.0  # Reasonable volume in nm³

    def test_generate_single_positions_within_cell(self, phase_info_ice_ih):
        """All atom positions should be within cell bounds."""
        from quickice.structure_generation.generator import IceStructureGenerator

        gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)
        candidate = gen._generate_single(seed=1000)

        # Get cell dimensions (assuming orthogonal box for ice1h)
        cell_x = candidate.cell[0, 0]
        cell_y = candidate.cell[1, 1]
        cell_z = candidate.cell[2, 2]

        # All positions should be within cell bounds
        # (GRO coordinates are in fractional coordinates, so 0 to cell_dim)
        assert np.all(candidate.positions[:, 0] <= cell_x * 1.01)  # Small tolerance
        assert np.all(candidate.positions[:, 1] <= cell_y * 1.01)
        assert np.all(candidate.positions[:, 2] <= cell_z * 1.01)

    def test_generate_all_returns_10_candidates(self, phase_info_ice_ih):
        """generate_all should return 10 candidates by default."""
        from quickice.structure_generation.generator import IceStructureGenerator

        gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)
        candidates = gen.generate_all()

        assert len(candidates) == 10

    def test_generate_all_has_different_seeds(self, phase_info_ice_ih):
        """Each candidate should have sequential seeds starting from base_seed."""
        from quickice.structure_generation.generator import IceStructureGenerator

        gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)
        candidates = gen.generate_all(base_seed=1000)

        seeds = [c.seed for c in candidates]
        assert seeds == list(range(1000, 1010))

    def test_generate_all_random_seeds(self, phase_info_ice_ih):
        """With no base_seed, each batch should have different seeds."""
        import time
        from quickice.structure_generation.generator import IceStructureGenerator

        gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)

        # Generate two batches with time gap
        candidates1 = gen.generate_all()
        time.sleep(0.1)  # Small delay to ensure different time-based seed
        candidates2 = gen.generate_all()

        seeds1 = [c.seed for c in candidates1]
        seeds2 = [c.seed for c in candidates2]

        # Seeds within each batch should be sequential
        assert seeds1 == list(range(seeds1[0], seeds1[0] + 10))
        assert seeds2 == list(range(seeds2[0], seeds2[0] + 10))

        # Different batches should have different seed ranges (with high probability)
        assert seeds1 != seeds2

    def test_generate_all_reproducible_with_seed(self, phase_info_ice_ih):
        """Same base_seed should produce identical candidates across batches."""
        from quickice.structure_generation.generator import IceStructureGenerator

        gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)

        # Generate with same seed
        candidates1 = gen.generate_all(base_seed=42)
        candidates2 = gen.generate_all(base_seed=42)

        # Should have same seeds
        seeds1 = [c.seed for c in candidates1]
        seeds2 = [c.seed for c in candidates2]
        assert seeds1 == seeds2

        # Should have identical positions
        for c1, c2 in zip(candidates1, candidates2):
            np.testing.assert_array_equal(c1.positions, c2.positions)

    def test_generate_all_candidates_are_diverse(self, phase_info_ice_ih):
        """Different seeds should produce different hydrogen bond networks."""
        from quickice.structure_generation.generator import IceStructureGenerator

        gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)
        candidates = gen.generate_all(n_candidates=2)

        # Check that positions are different
        # (different random hydrogen orientations)
        assert not np.allclose(candidates[0].positions, candidates[1].positions)

    def test_generate_single_is_reproducible(self, phase_info_ice_ih):
        """Same seed should produce identical structures."""
        from quickice.structure_generation.generator import IceStructureGenerator

        gen = IceStructureGenerator(phase_info_ice_ih, nmolecules=100)

        candidate1 = gen._generate_single(seed=1000)
        candidate2 = gen._generate_single(seed=1000)

        np.testing.assert_array_equal(candidate1.positions, candidate2.positions)

    def test_generator_unsupported_phase(self):
        """Generator should raise UnsupportedPhaseError for unsupported phases."""
        from quickice.structure_generation.generator import IceStructureGenerator

        phase_info = {
            "phase_id": "ice_xxx",
            "phase_name": "Unknown",
            "density": 1.0,
        }

        with pytest.raises(UnsupportedPhaseError):
            IceStructureGenerator(phase_info, nmolecules=100)


class TestGenerateCandidates:
    """Tests for generate_candidates convenience function."""

    @pytest.fixture
    def phase_info_ice_ih(self):
        """Phase info for Ice Ih at 273K, 0MPa."""
        return {
            "phase_id": "ice_ih",
            "phase_name": "Ice Ih",
            "density": 0.9167,
            "temperature": 273,
            "pressure": 0,
        }

    def test_generate_candidates_returns_result(self, phase_info_ice_ih):
        """generate_candidates should return GenerationResult."""
        from quickice.structure_generation import generate_candidates

        result = generate_candidates(phase_info_ice_ih, nmolecules=100)

        assert isinstance(result, GenerationResult)
        assert len(result.candidates) == 10

    def test_generate_candidates_has_correct_metadata(self, phase_info_ice_ih):
        """Result should have correct phase and molecule count metadata."""
        from quickice.structure_generation import generate_candidates

        result = generate_candidates(phase_info_ice_ih, nmolecules=100)

        assert result.phase_id == "ice_ih"
        assert result.phase_name == "Ice Ih"
        assert result.density == 0.9167
        assert result.requested_nmolecules == 100
        assert result.actual_nmolecules == 128
        assert result.was_rounded is True

    def test_generate_candidates_no_rounding(self, phase_info_ice_ih):
        """Result should indicate no rounding when exact count is achieved."""
        from quickice.structure_generation import generate_candidates

        # 128 = 16 * 8 = 16 * 2^3, so should be exact
        result = generate_candidates(phase_info_ice_ih, nmolecules=128)

        assert result.requested_nmolecules == 128
        assert result.actual_nmolecules == 128
        assert result.was_rounded is False

    def test_generate_candidates_custom_count(self, phase_info_ice_ih):
        """generate_candidates should respect n_candidates parameter."""
        from quickice.structure_generation import generate_candidates

        result = generate_candidates(phase_info_ice_ih, nmolecules=100, n_candidates=5)

        assert len(result.candidates) == 5

    def test_generate_candidates_with_seed(self, phase_info_ice_ih):
        """generate_candidates should accept base_seed for reproducibility."""
        from quickice.structure_generation import generate_candidates

        # Generate with same seed
        result1 = generate_candidates(phase_info_ice_ih, nmolecules=100, base_seed=42)
        result2 = generate_candidates(phase_info_ice_ih, nmolecules=100, base_seed=42)

        # Should have same seeds
        seeds1 = [c.seed for c in result1.candidates]
        seeds2 = [c.seed for c in result2.candidates]
        assert seeds1 == seeds2

        # Should have identical positions
        for c1, c2 in zip(result1.candidates, result2.candidates):
            np.testing.assert_array_equal(c1.positions, c2.positions)

    def test_generate_candidates_valid_coordinates(self, phase_info_ice_ih):
        """All candidates should have valid parseable coordinates."""
        from quickice.structure_generation import generate_candidates

        result = generate_candidates(phase_info_ice_ih, nmolecules=100)

        for candidate in result.candidates:
            assert isinstance(candidate.positions, np.ndarray)
            assert candidate.positions.shape[1] == 3
            assert len(candidate.atom_names) == candidate.positions.shape[0]
            assert candidate.cell.shape == (3, 3)


class TestIntegrationWithPhase2:
    """Integration tests with Phase 2 lookup."""

    def test_integration_with_phase_lookup(self):
        """generate_candidates should work with Phase 2 lookup_phase output."""
        from quickice.phase_mapping import lookup_phase
        from quickice.structure_generation import generate_candidates

        # Get phase info from Phase 2
        phase_info = lookup_phase(273, 0)  # Ice Ih

        # Generate structures
        result = generate_candidates(phase_info, nmolecules=100)

        assert result.phase_id == "ice_ih"
        assert len(result.candidates) == 10

    def test_integration_different_phases(self):
        """Should work with different ice phases."""
        from quickice.phase_mapping import lookup_phase
        from quickice.structure_generation import generate_candidates

        # Test Ice Ic (cubic ice)
        phase_info = lookup_phase(150, 0)  # Ice Ic at low temperature
        result = generate_candidates(phase_info, nmolecules=50)

        assert result.phase_id == "ice_ic"
        assert len(result.candidates) == 10
        assert result.actual_nmolecules >= 50

    def test_integration_high_pressure_phase(self):
        """Should work with high-pressure phases."""
        from quickice.phase_mapping import lookup_phase
        from quickice.structure_generation import generate_candidates

        # Test Ice VI at high pressure (need higher pressure to get ice_vi)
        phase_info = lookup_phase(273, 1500)  # Ice VI at 1.5 GPa
        result = generate_candidates(phase_info, nmolecules=50)

        assert result.phase_id == "ice_vi"
        assert len(result.candidates) == 10
        assert result.actual_nmolecules >= 50
