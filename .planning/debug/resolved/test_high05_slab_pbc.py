"""Test for HIGH-05 slab mode PBC boundary check.

This test verifies that atoms in slab mode don't end up at exactly
the box boundary, which could cause PBC wrap-around overlap.
"""

import numpy as np
import pytest

from quickice.structure_generation.types import Candidate, InterfaceConfig
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.modes.slab import assemble_slab


class TestSlabPBCBoundary:
    """Tests for PBC boundary issues in slab mode."""

    @pytest.fixture
    def minimal_ice_candidate(self):
        """Create a minimal ice candidate for testing."""
        # Create a simple orthogonal cell with ice-like structure
        # Use a larger cell to get enough molecules
        positions = []
        atom_names = []
        
        # Create a 2x2x2 pattern of water molecules (OHH pattern)
        # Each molecule at a different Z position to test boundary
        for ix in range(4):
            for iy in range(4):
                for iz in range(8):
                    # Base position for this molecule
                    x = ix * 0.25 + 0.1
                    y = iy * 0.25 + 0.1
                    z = iz * 0.125 + 0.05  # Distribute across Z
                    
                    # O atom
                    positions.append([x, y, z])
                    atom_names.append("O")
                    
                    # H atoms (small offset)
                    positions.append([x + 0.05, y + 0.05, z + 0.05])
                    atom_names.append("H")
                    positions.append([x - 0.05, y + 0.05, z + 0.05])
                    atom_names.append("H")
        
        return Candidate(
            positions=np.array(positions),
            atom_names=atom_names,
            cell=np.array([
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0]
            ]),
            nmolecules=len(positions) // 3,
            phase_id="ice_ih",
            seed=42
        )

    def test_atoms_within_box_bounds_after_generation(self, minimal_ice_candidate):
        """All atoms should be strictly within [0, box_z) after generation."""
        config = InterfaceConfig(
            mode="slab",
            box_x=2.0,
            box_y=2.0,
            box_z=2.0,  # 2*ice_thickness + water_thickness = 2*0.8 + 0.4
            seed=42,
            ice_thickness=0.8,
            water_thickness=0.4
        )
        
        result = generate_interface(minimal_ice_candidate, config)
        
        # Check that all Z positions are strictly within [0, box_z)
        z_positions = result.positions[:, 2]
        
        # Atoms should be in [0, box_z), not [0, box_z]
        assert np.all(z_positions >= 0.0), \
            f"Found atoms with Z < 0: min Z = {z_positions.min()}"
        
        # This is the critical check - atoms should be STRICTLY less than box_z
        # Due to PBC, Z == box_z wraps to Z == 0, causing overlap with bottom ice
        assert np.all(z_positions < config.box_z), \
            f"Found atoms with Z >= box_z: max Z = {z_positions.max()}, box_z = {config.box_z}"
    
    def test_thin_water_layer_no_pbc_overlap(self, minimal_ice_candidate):
        """Thin water layer should not cause PBC wrap-around overlap."""
        # This is the scenario from the issue report
        config = InterfaceConfig(
            mode="slab",
            box_x=2.0,
            box_y=2.0,
            box_z=4.1,  # 2*2.0 + 0.1 = 4.1
            seed=42,
            ice_thickness=2.0,
            water_thickness=0.1  # Very thin water layer
        )
        
        result = generate_interface(minimal_ice_candidate, config)
        
        z_positions = result.positions[:, 2]
        
        # All atoms must be in [0, box_z)
        assert np.all(z_positions >= 0.0), \
            f"Found atoms with Z < 0: min Z = {z_positions.min()}"
        assert np.all(z_positions < config.box_z), \
            f"Found atoms with Z >= box_z: max Z = {z_positions.max()}, box_z = {config.box_z}"
        
        # Additional check: no atoms should be at exactly box_z
        at_boundary = np.isclose(z_positions, config.box_z, atol=1e-10)
        assert not np.any(at_boundary), \
            f"Found {at_boundary.sum()} atoms at exactly Z = box_z (PBC wrap risk)"

    def test_top_ice_positions_not_at_boundary(self, minimal_ice_candidate):
        """Top ice layer atoms should not be positioned at box boundary."""
        config = InterfaceConfig(
            mode="slab",
            box_x=2.0,
            box_y=2.0,
            box_z=2.0,
            seed=42,
            ice_thickness=0.8,
            water_thickness=0.4
        )
        
        result = generate_interface(minimal_ice_candidate, config)
        
        # Get ice atom positions (ice atoms come first)
        ice_atom_count = result.ice_atom_count
        ice_positions = result.positions[:ice_atom_count]
        
        # Total ice molecules = bottom + top
        total_ice_molecules = result.ice_nmolecules
        bottom_ice_molecules = total_ice_molecules // 2
        atoms_per_molecule = 3  # GenIce: O, H, H
        
        # Top ice atoms are the second half
        top_ice_start = bottom_ice_molecules * atoms_per_molecule
        top_ice_positions = ice_positions[top_ice_start:]
        
        # Top ice should be in range [ice_thickness + water_thickness, box_z)
        # NOT at exactly box_z
        z_top = top_ice_positions[:, 2]
        
        expected_min_z = config.ice_thickness + config.water_thickness
        
        assert np.all(z_top >= expected_min_z - 0.01), \
            f"Top ice atoms below expected minimum: min Z = {z_top.min()}, expected >= {expected_min_z}"
        
        assert np.all(z_top < config.box_z), \
            f"Top ice atoms at or above box_z: max Z = {z_top.max()}, box_z = {config.box_z}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
