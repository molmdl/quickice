"""End-to-end tests for triclinic ice phase interface generation.

Ice II (rhombohedral, space group R-3) is NOT supported for interface generation
because it cannot have an orthogonal supercell - this is a fundamental crystallographic
constraint. These tests verify that Ice II is properly rejected with a clear error.

Ice V interfaces work correctly with rectangular XY projections.
"""

import numpy as np
import pytest

from quickice.phase_mapping import lookup_phase
from quickice.structure_generation import generate_candidates
from quickice.structure_generation.types import InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.errors import InterfaceGenerationError


class TestIceIIInterface:
    """Tests for Ice II interface generation."""

    @pytest.fixture
    def ice_ii_candidate(self):
        """Generate Ice II candidate for testing."""
        phase_info = {
            "phase_id": "ice_ii",
            "phase_name": "Ice II",
            "density": 1.18,
            "temperature": 238,
            "pressure": 300,
        }
        result = generate_candidates(phase_info, nmolecules=50, n_candidates=1)
        return result.candidates[0]

    def test_ice_ii_slab_interface(self, ice_ii_candidate):
        """Ice II should be rejected in slab mode with clear error message."""
        config = InterfaceConfig(
            mode="slab",
            box_x=3.0,
            box_y=3.0,
            box_z=8.0,
            seed=42,
            ice_thickness=2.0,
            water_thickness=4.0,
        )

        with pytest.raises(InterfaceGenerationError) as exc_info:
            generate_interface(ice_ii_candidate, config)

        assert "Ice II" in str(exc_info.value)
        assert "rhombohedral" in str(exc_info.value).lower()
        assert "not supported" in str(exc_info.value).lower()

    def test_ice_ii_piece_interface(self, ice_ii_candidate):
        """Ice II should be rejected in piece mode with clear error message."""
        # Get ice dimensions using bounding box extent
        cell = ice_ii_candidate.cell
        corners = np.array([
            [0, 0, 0], cell[0], cell[1], cell[2],
            cell[0] + cell[1], cell[0] + cell[2],
            cell[1] + cell[2], cell[0] + cell[1] + cell[2]
        ])
        ice_dims = corners.max(axis=0) - corners.min(axis=0)

        config = InterfaceConfig(
            mode="piece",
            box_x=ice_dims[0] + 2.0,
            box_y=ice_dims[1] + 2.0,
            box_z=ice_dims[2] + 2.0,
            seed=42,
        )

        with pytest.raises(InterfaceGenerationError) as exc_info:
            generate_interface(ice_ii_candidate, config)

        assert "Ice II" in str(exc_info.value)
        assert "rhombohedral" in str(exc_info.value).lower()
        assert "not supported" in str(exc_info.value).lower()

    def test_ice_ii_pocket_interface(self, ice_ii_candidate):
        """Ice II should be rejected in pocket mode with clear error message."""
        config = InterfaceConfig(
            mode="pocket",
            box_x=4.0,
            box_y=4.0,
            box_z=4.0,
            seed=42,
            pocket_diameter=2.0,
            pocket_shape="sphere",
        )

        with pytest.raises(InterfaceGenerationError) as exc_info:
            generate_interface(ice_ii_candidate, config)

        assert "Ice II" in str(exc_info.value)
        assert "rhombohedral" in str(exc_info.value).lower()
        assert "not supported" in str(exc_info.value).lower()


class TestIceVInterface:
    """Tests for Ice V interface generation."""

    @pytest.fixture
    def ice_v_candidate(self):
        """Generate Ice V candidate for testing."""
        phase_info = {
            "phase_id": "ice_v",
            "phase_name": "Ice V",
            "density": 1.24,
            "temperature": 253,
            "pressure": 500,
        }
        result = generate_candidates(phase_info, nmolecules=50, n_candidates=1)
        return result.candidates[0]

    def test_ice_v_slab_interface(self, ice_v_candidate):
        """Ice V should work in slab mode."""
        config = InterfaceConfig(
            mode="slab",
            box_x=3.0,
            box_y=3.0,
            box_z=8.0,
            seed=42,
            ice_thickness=2.0,
            water_thickness=4.0,
        )

        interface = generate_interface(ice_v_candidate, config)

        assert interface.ice_nmolecules > 0
        assert interface.water_nmolecules > 0

    def test_ice_v_piece_interface(self, ice_v_candidate):
        """Ice V should work in piece mode."""
        # Get ice dimensions using bounding box extent
        cell = ice_v_candidate.cell
        corners = np.array([
            [0, 0, 0], cell[0], cell[1], cell[2],
            cell[0] + cell[1], cell[0] + cell[2],
            cell[1] + cell[2], cell[0] + cell[1] + cell[2]
        ])
        ice_dims = corners.max(axis=0) - corners.min(axis=0)

        config = InterfaceConfig(
            mode="piece",
            box_x=ice_dims[0] + 2.0,
            box_y=ice_dims[1] + 2.0,
            box_z=ice_dims[2] + 2.0,
            seed=42,
        )

        interface = generate_interface(ice_v_candidate, config)

        assert interface.ice_nmolecules > 0
        assert interface.water_nmolecules > 0


class TestOrthogonalPhasesStillWork:
    """Verify orthogonal phases still work after changes."""

    @pytest.fixture
    def ice_ih_candidate(self):
        """Generate Ice Ih candidate."""
        phase_info = lookup_phase(273, 0)  # Ice Ih
        result = generate_candidates(phase_info, nmolecules=50, n_candidates=1)
        return result.candidates[0]

    def test_ice_ih_still_works(self, ice_ih_candidate):
        """Ice Ih should still work in all modes."""
        # Slab mode
        config = InterfaceConfig(
            mode="slab",
            box_x=3.0, box_y=3.0, box_z=8.0,
            seed=42, ice_thickness=2.0, water_thickness=4.0
        )
        interface = generate_interface(ice_ih_candidate, config)
        assert interface.ice_nmolecules > 0

        # Piece mode
        # Get ice dimensions using bounding box extent
        cell = ice_ih_candidate.cell
        corners = np.array([
            [0, 0, 0], cell[0], cell[1], cell[2],
            cell[0] + cell[1], cell[0] + cell[2],
            cell[1] + cell[2], cell[0] + cell[1] + cell[2]
        ])
        ice_dims = corners.max(axis=0) - corners.min(axis=0)

        config = InterfaceConfig(
            mode="piece",
            box_x=ice_dims[0] + 2.0,
            box_y=ice_dims[1] + 2.0,
            box_z=ice_dims[2] + 2.0,
            seed=42,
        )
        interface = generate_interface(ice_ih_candidate, config)
        assert interface.ice_nmolecules > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
