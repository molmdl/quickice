"""Test for MED-03 minimum box size validation fix."""

import numpy as np
import pytest

from quickice.structure_generation.types import Candidate, InterfaceConfig
from quickice.structure_generation.interface_builder import (
    validate_interface_config,
    MINIMUM_BOX_DIMENSION,
)
from quickice.structure_generation.errors import InterfaceGenerationError


@pytest.fixture
def valid_candidate():
    """Create a valid candidate for testing."""
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


class TestMinimumBoxSize:
    """Tests for minimum box size validation."""

    def test_rejects_extremely_small_box_x(self, valid_candidate):
        """Box X of 0.001 nm should be rejected."""
        config = InterfaceConfig(
            mode="slab",
            box_x=0.001,
            box_y=3.0,
            box_z=3.0,
            seed=42,
            ice_thickness=1.0,
            water_thickness=1.0
        )
        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(config, valid_candidate)

        error_msg = str(exc_info.value)
        assert "too small" in error_msg.lower()
        assert "0.001" in error_msg
        assert f"{MINIMUM_BOX_DIMENSION:.1f}" in error_msg
        assert "water molecules" in error_msg.lower()

    def test_rejects_extremely_small_box_y(self, valid_candidate):
        """Box Y of 0.001 nm should be rejected."""
        config = InterfaceConfig(
            mode="slab",
            box_x=3.0,
            box_y=0.001,
            box_z=3.0,
            seed=42,
            ice_thickness=1.0,
            water_thickness=1.0
        )
        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(config, valid_candidate)

        error_msg = str(exc_info.value)
        assert "too small" in error_msg.lower()
        assert "box y" in error_msg.lower()

    def test_rejects_extremely_small_box_z(self, valid_candidate):
        """Box Z of 0.001 nm should be rejected."""
        config = InterfaceConfig(
            mode="slab",
            box_x=3.0,
            box_y=3.0,
            box_z=0.001,
            seed=42,
            ice_thickness=1.0,
            water_thickness=1.0
        )
        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(config, valid_candidate)

        error_msg = str(exc_info.value)
        assert "too small" in error_msg.lower()
        assert "box z" in error_msg.lower()

    def test_rejects_box_just_below_minimum(self, valid_candidate):
        """Box of 0.999 nm should be rejected."""
        config = InterfaceConfig(
            mode="slab",
            box_x=0.999,
            box_y=3.0,
            box_z=3.0,
            seed=42,
            ice_thickness=1.0,
            water_thickness=1.0
        )
        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(config, valid_candidate)

        assert "too small" in str(exc_info.value).lower()

    def test_accepts_minimum_boundary_box(self, valid_candidate):
        """Box of exactly 1.0 nm should be accepted (boundary case)."""
        # Note: For slab mode, box_z must match ice_thickness + water_thickness
        # So we test with box_x and box_y at minimum
        config = InterfaceConfig(
            mode="slab",
            box_x=MINIMUM_BOX_DIMENSION,  # 1.0 nm
            box_y=MINIMUM_BOX_DIMENSION,  # 1.0 nm
            box_z=4.0,  # Valid for ice_thickness=1.0, water_thickness=2.0
            seed=42,
            ice_thickness=1.0,
            water_thickness=2.0
        )
        # Should not raise
        validate_interface_config(config, valid_candidate)

    def test_accepts_reasonable_box_sizes(self, valid_candidate):
        """Box sizes above minimum should be accepted."""
        config = InterfaceConfig(
            mode="slab",
            box_x=3.0,
            box_y=5.0,
            box_z=10.0,
            seed=42,
            ice_thickness=2.0,
            water_thickness=6.0
        )
        # Should not raise
        validate_interface_config(config, valid_candidate)

    def test_rejects_small_box_in_pocket_mode(self, valid_candidate):
        """Small boxes should be rejected in pocket mode too."""
        config = InterfaceConfig(
            mode="pocket",
            box_x=0.5,
            box_y=0.5,
            box_z=0.5,
            seed=42,
            pocket_diameter=0.3
        )
        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(config, valid_candidate)

        assert "too small" in str(exc_info.value).lower()

    def test_rejects_small_box_in_piece_mode(self, valid_candidate):
        """Small boxes should be rejected in piece mode too.

        Note: piece mode has additional checks for water layer thickness,
        but the minimum box size check should still apply.
        """
        # Create a candidate with small cell dimensions
        small_candidate = Candidate(
            positions=np.array([[0.0, 0.0, 0.0], [0.1, 0.1, 0.1], [0.2, 0.2, 0.2]]),
            atom_names=["O", "H", "H"],
            cell=np.array([
                [0.5, 0.0, 0.0],
                [0.0, 0.5, 0.0],
                [0.0, 0.0, 0.5]
            ]),
            nmolecules=1,
            phase_id="ice_ih",
            seed=42
        )

        # Box smaller than 1.0 nm should fail minimum check
        # even if it's larger than the ice piece
        config = InterfaceConfig(
            mode="piece",
            box_x=0.8,  # > ice_dims[0] (0.5) but < MINIMUM_BOX_DIMENSION (1.0)
            box_y=0.8,
            box_z=0.8,
            seed=42
        )
        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(config, small_candidate)

        assert "too small" in str(exc_info.value).lower()

    def test_error_message_is_informative(self, valid_candidate):
        """Error message should explain the physical basis."""
        config = InterfaceConfig(
            mode="slab",
            box_x=0.001,
            box_y=3.0,
            box_z=3.0,
            seed=42,
            ice_thickness=1.0,
            water_thickness=1.0
        )
        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(config, valid_candidate)

        error_msg = str(exc_info.value)
        # Should mention the actual value
        assert "0.001" in error_msg
        # Should mention the minimum
        assert f"{MINIMUM_BOX_DIMENSION:.1f}" in error_msg
        # Should explain the physical basis
        assert "0.28" in error_msg  # Water molecule diameter
        assert "numerical issues" in error_msg.lower()


class TestMinimumBoxDimensionConstant:
    """Tests for the MINIMUM_BOX_DIMENSION constant."""

    def test_constant_exists(self):
        """MINIMUM_BOX_DIMENSION should be defined."""
        assert MINIMUM_BOX_DIMENSION is not None

    def test_constant_value(self):
        """MINIMUM_BOX_DIMENSION should be 1.0 nm."""
        assert MINIMUM_BOX_DIMENSION == 1.0

    def test_constant_is_reasonable(self):
        """MINIMUM_BOX_DIMENSION should be reasonable for physical validity."""
        # Should be larger than water molecule diameter (~0.28 nm)
        assert MINIMUM_BOX_DIMENSION > 0.28
        # Should be small enough to not be overly restrictive
        assert MINIMUM_BOX_DIMENSION < 10.0
