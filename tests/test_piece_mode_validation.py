"""Test for MED-02 water layer validation in piece mode."""

import numpy as np
import pytest

from quickice.structure_generation.types import Candidate, InterfaceConfig
from quickice.structure_generation.interface_builder import validate_interface_config
from quickice.structure_generation.errors import InterfaceGenerationError


class TestPieceModeWaterLayerValidation:
    """Tests for minimum water layer thickness validation in piece mode."""

    @pytest.fixture
    def candidate_2nm(self):
        """Create a candidate with 2.0 nm ice piece."""
        return Candidate(
            positions=np.array([[0.0, 0.0, 0.0], [0.1, 0.1, 0.1], [0.2, 0.2, 0.2]]),
            atom_names=["O", "H", "H"],
            cell=np.array([
                [2.0, 0.0, 0.0],
                [0.0, 2.0, 0.0],
                [0.0, 0.0, 2.0]
            ]),
            nmolecules=1,
            phase_id="ice_ih",
            seed=42
        )

    def test_valid_water_layer_passes_validation(self, candidate_2nm):
        """Box with sufficient water layer should pass validation."""
        # Box = 2.0 + 0.5 nm = 2.5 nm (well above overlap_threshold of 0.25 nm)
        config = InterfaceConfig(
            mode="piece",
            box_x=2.5,
            box_y=2.5,
            box_z=2.5,
            seed=42
        )
        # Should not raise
        validate_interface_config(config, candidate_2nm)

    def test_thin_water_layer_fails_validation(self, candidate_2nm):
        """Box with thin water layer should fail validation."""
        # Box X = 2.0 + 0.1 nm = 2.1 nm (below overlap_threshold of 0.25 nm)
        config = InterfaceConfig(
            mode="piece",
            box_x=2.1,  # Thin layer in X
            box_y=2.5,
            box_z=2.5,
            seed=42
        )

        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(config, candidate_2nm)

        error_msg = str(exc_info.value)
        assert "Water layer too thin" in error_msg
        assert "X dimension" in error_msg
        assert "0.100 nm" in error_msg  # Actual water layer
        assert "0.25 nm" in error_msg   # Minimum required

    def test_water_layer_exactly_at_threshold_passes(self, candidate_2nm):
        """Water layer exactly at overlap_threshold should pass."""
        # Box = 2.0 + 0.25 nm = 2.25 nm (exactly at threshold)
        config = InterfaceConfig(
            mode="piece",
            box_x=2.25,
            box_y=2.5,
            box_z=2.5,
            seed=42
        )
        # Should not raise (>= threshold)
        validate_interface_config(config, candidate_2nm)

    def test_box_smaller_than_ice_fails_with_original_error(self, candidate_2nm):
        """Box smaller than ice should fail with original error message."""
        config = InterfaceConfig(
            mode="piece",
            box_x=1.5,  # Smaller than ice (2.0 nm)
            box_y=2.5,
            box_z=2.5,
            seed=42
        )

        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(config, candidate_2nm)

        error_msg = str(exc_info.value)
        assert "must be larger than ice piece" in error_msg
        assert "Water layer too thin" not in error_msg

    def test_all_dimensions_validated(self, candidate_2nm):
        """All three dimensions should be validated for water layer."""
        # Test Y dimension thin
        config_y = InterfaceConfig(
            mode="piece",
            box_x=2.5,
            box_y=2.1,  # Thin in Y
            box_z=2.5,
            seed=42
        )
        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(config_y, candidate_2nm)
        assert "Y dimension" in str(exc_info.value)

        # Test Z dimension thin
        config_z = InterfaceConfig(
            mode="piece",
            box_x=2.5,
            box_y=2.5,
            box_z=2.1,  # Thin in Z
            seed=42
        )
        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(config_z, candidate_2nm)
        assert "Z dimension" in str(exc_info.value)

    def test_custom_overlap_threshold(self, candidate_2nm):
        """Validation should respect custom overlap_threshold."""
        # With default threshold 0.25 nm, 2.2 nm box should fail (0.2 nm layer)
        config_default = InterfaceConfig(
            mode="piece",
            box_x=2.2,
            box_y=2.5,
            box_z=2.5,
            seed=42,
            overlap_threshold=0.25
        )
        with pytest.raises(InterfaceGenerationError):
            validate_interface_config(config_default, candidate_2nm)

        # With smaller threshold 0.15 nm, same box should pass
        config_small_threshold = InterfaceConfig(
            mode="piece",
            box_x=2.2,
            box_y=2.5,
            box_z=2.5,
            seed=42,
            overlap_threshold=0.15
        )
        # Should not raise
        validate_interface_config(config_small_threshold, candidate_2nm)

    def test_error_message_explains_problem(self, candidate_2nm):
        """Error message should explain why thin water layers are problematic."""
        config = InterfaceConfig(
            mode="piece",
            box_x=2.1,
            box_y=2.5,
            box_z=2.5,
            seed=42
        )

        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(config, candidate_2nm)

        error_msg = str(exc_info.value)
        # Should explain the consequence
        assert "removed as overlapping" in error_msg or "overlap" in error_msg.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
