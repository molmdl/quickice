"""Test for HIGH-04 triclinic cell handling fix."""

import numpy as np
import pytest

from quickice.structure_generation.types import Candidate, InterfaceConfig
from quickice.structure_generation.interface_builder import (
    is_cell_orthogonal,
    validate_interface_config,
    generate_interface,
)
from quickice.structure_generation.errors import InterfaceGenerationError


class TestIsCellOrthogonal:
    """Tests for the is_cell_orthogonal function."""

    def test_orthogonal_cell_returns_true(self):
        """Orthogonal cell (diagonal only) should return True."""
        cell = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
            [0.0, 0.0, 3.0]
        ])
        assert is_cell_orthogonal(cell) is True

    def test_orthogonal_cell_with_small_numerical_noise(self):
        """Orthogonal cell with small numerical noise should return True."""
        cell = np.array([
            [1.0, 1e-12, 1e-12],
            [1e-12, 2.0, 1e-12],
            [1e-12, 1e-12, 3.0]
        ])
        assert is_cell_orthogonal(cell) is True

    def test_triclinic_cell_returns_false(self):
        """Triclinic cell (with off-diagonal) should return False."""
        cell = np.array([
            [1.0, 0.0, 0.0],
            [0.5, 2.0, 0.0],
            [0.5, 0.3, 3.0]
        ])
        assert is_cell_orthogonal(cell) is False

    def test_ice2_cell_returns_false(self):
        """Ice 2 cell (actual triclinic) should return False."""
        # Actual cell from GenIce ice2 lattice
        cell = np.array([
            [0.778, 0.0, 0.0],
            [-0.305238, 0.715621, 0.0],
            [-0.305238, -0.462040, 0.546473]
        ])
        assert is_cell_orthogonal(cell) is False

    def test_ice5_cell_returns_false(self):
        """Ice 5 cell (actual triclinic) should return False."""
        # Actual cell from GenIce ice5 lattice
        cell = np.array([
            [9.199778, 0.0, 0.0],
            [0.0, 7.523463, 0.0],
            [-3.396304, 0.0, 9.752858]
        ])
        assert is_cell_orthogonal(cell) is False

    def test_ice1h_cell_returns_true(self):
        """Ice 1h cell (orthogonal) should return True."""
        # Actual cell from GenIce ice1h lattice
        cell = np.array([
            [7.848134, 0.0, 0.0],
            [0.0, 7.377351, 0.0],
            [0.0, 0.0, 9.065738]
        ])
        assert is_cell_orthogonal(cell) is True


class TestTriclinicCellValidation:
    """Tests for triclinic cell validation in interface generation."""

    @pytest.fixture
    def orthogonal_candidate(self):
        """Create an orthogonal cell candidate."""
        return Candidate(
            positions=np.array([[0.0, 0.0, 0.0], [0.1, 0.1, 0.1], [0.2, 0.2, 0.2]]),
            atom_names=["O", "H", "H"],
            cell=np.array([
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0]
            ]),
            nmolecules=1,
            phase_id="ice_ih",
            seed=42
        )

    @pytest.fixture
    def triclinic_candidate(self):
        """Create a triclinic cell candidate (like ice_ii)."""
        return Candidate(
            positions=np.array([[0.0, 0.0, 0.0], [0.1, 0.1, 0.1], [0.2, 0.2, 0.2]]),
            atom_names=["O", "H", "H"],
            cell=np.array([
                [1.0, 0.0, 0.0],
                [0.5, 1.0, 0.0],
                [0.3, 0.2, 1.0]
            ]),
            nmolecules=1,
            phase_id="ice_ii",
            seed=42
        )

    @pytest.fixture
    def slab_config(self):
        """Create a valid slab config."""
        return InterfaceConfig(
            mode="slab",
            box_x=3.0,
            box_y=3.0,
            box_z=3.0,
            seed=42,
            ice_thickness=1.0,
            water_thickness=1.0
        )

    @pytest.fixture
    def piece_config(self):
        """Create a valid piece config."""
        return InterfaceConfig(
            mode="piece",
            box_x=3.0,
            box_y=3.0,
            box_z=3.0,
            seed=42
        )

    def test_orthogonal_cell_passes_validation(self, orthogonal_candidate, slab_config):
        """Orthogonal cell should pass validation."""
        # Should not raise
        validate_interface_config(slab_config, orthogonal_candidate)

    def test_triclinic_cell_fails_validation(self, triclinic_candidate, piece_config):
        """Triclinic cell should fail validation with clear error."""
        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(piece_config, triclinic_candidate)

        error_msg = str(exc_info.value)
        assert "Triclinic" in error_msg
        assert "non-orthogonal" in error_msg
        assert "ice_ii" in error_msg
        assert "orthogonal cells" in error_msg

    def test_triclinic_cell_fails_generate_interface(self, triclinic_candidate, piece_config):
        """generate_interface should fail for triclinic cells."""
        with pytest.raises(InterfaceGenerationError) as exc_info:
            generate_interface(triclinic_candidate, piece_config)

        error_msg = str(exc_info.value)
        assert "Triclinic" in error_msg

    def test_error_message_mentions_affected_phases(self, triclinic_candidate, piece_config):
        """Error message should mention affected phases."""
        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(piece_config, triclinic_candidate)

        error_msg = str(exc_info.value)
        assert "ice_ii" in error_msg or "ice_v" in error_msg


class TestIntegrationWithRealGenIce:
    """Integration tests with actual GenIce-generated structures."""

    def test_ice_ii_rejected(self):
        """Ice II (triclinic) should be rejected with clear error."""
        from quickice.structure_generation.generator import IceStructureGenerator

        phase_info = {
            "phase_id": "ice_ii",
            "phase_name": "Ice II",
            "density": 1.17,
        }

        gen = IceStructureGenerator(phase_info, nmolecules=50)
        candidate = gen._generate_single(seed=1000)

        config = InterfaceConfig(
            mode="piece",
            box_x=5.0,
            box_y=5.0,
            box_z=5.0,
            seed=42
        )

        with pytest.raises(InterfaceGenerationError) as exc_info:
            generate_interface(candidate, config)

        error_msg = str(exc_info.value)
        assert "Triclinic" in error_msg
        assert "ice_ii" in error_msg

    def test_ice_v_rejected(self):
        """Ice V (triclinic) should be rejected with clear error."""
        from quickice.structure_generation.generator import IceStructureGenerator

        phase_info = {
            "phase_id": "ice_v",
            "phase_name": "Ice V",
            "density": 1.24,
        }

        gen = IceStructureGenerator(phase_info, nmolecules=100)
        candidate = gen._generate_single(seed=1000)

        config = InterfaceConfig(
            mode="piece",
            box_x=10.0,
            box_y=10.0,
            box_z=10.0,
            seed=42
        )

        with pytest.raises(InterfaceGenerationError) as exc_info:
            generate_interface(candidate, config)

        error_msg = str(exc_info.value)
        assert "Triclinic" in error_msg
        assert "ice_v" in error_msg

    def test_ice_ih_accepted(self):
        """Ice Ih (orthogonal) should be accepted."""
        from quickice.structure_generation.generator import IceStructureGenerator

        phase_info = {
            "phase_id": "ice_ih",
            "phase_name": "Ice Ih",
            "density": 0.9167,
        }

        gen = IceStructureGenerator(phase_info, nmolecules=100)
        candidate = gen._generate_single(seed=1000)

        # Verify the cell is orthogonal
        assert is_cell_orthogonal(candidate.cell)

        config = InterfaceConfig(
            mode="piece",
            box_x=5.0,
            box_y=5.0,
            box_z=5.0,
            seed=42
        )

        # Should not raise
        validate_interface_config(config, candidate)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
