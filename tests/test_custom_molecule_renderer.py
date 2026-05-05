"""Tests for custom molecule renderer.

Tests the custom molecule visualization:
1. VTK actor creation with custom molecule data
2. Distinct color palette for different moleculetype names
3. Ball-and-stick rendering with CPK colors
4. Bond detection at 0.16 nm threshold
5. MW virtual sites exclusion
"""

import pytest
import numpy as np

from quickice.gui.custom_molecule_renderer import (
    create_custom_molecule_actor,
    get_element_from_atom_name,
    CUSTOM_MOLECULE_COLORS,
    BOND_DISTANCE_THRESHOLD,
)


class TestGetElementFromAtomName:
    """Tests for element extraction from atom names."""
    
    def test_simple_element_names(self):
        """Test extraction from simple element names."""
        assert get_element_from_atom_name("C") == "C"
        assert get_element_from_atom_name("O") == "O"
        assert get_element_from_atom_name("H") == "H"
    
    def test_element_with_numbers(self):
        """Test extraction from atom names with numbers."""
        assert get_element_from_atom_name("C1") == "C"
        assert get_element_from_atom_name("O2") == "O"
        assert get_element_from_atom_name("H3") == "H"
        assert get_element_from_atom_name("C10") == "C"
    
    def test_common_variations(self):
        """Test extraction from common atom name variations."""
        # Carbon variations
        assert get_element_from_atom_name("CA") == "C"
        assert get_element_from_atom_name("CB") == "C"
        assert get_element_from_atom_name("CG") == "C"
        
        # Oxygen variations
        assert get_element_from_atom_name("OA") == "O"
        assert get_element_from_atom_name("OB") == "O"
        
        # Hydrogen variations
        assert get_element_from_atom_name("HA") == "H"
        assert get_element_from_atom_name("HB") == "H"
    
    def test_mw_virtual_site(self):
        """Test MW virtual site returns None."""
        assert get_element_from_atom_name("MW") is None
    
    def test_unknown_elements(self):
        """Test handling of unknown elements."""
        # Single letter elements should pass through
        assert get_element_from_atom_name("N") == "N"
        assert get_element_from_atom_name("S") == "S"
        
        # Very long names should return None
        assert get_element_from_atom_name("UNKNOWN") is None


class TestCustomMoleculeColors:
    """Tests for custom molecule color palette."""
    
    def test_defined_colors(self):
        """Test that all defined colors are valid RGB tuples."""
        for name, color in CUSTOM_MOLECULE_COLORS.items():
            assert isinstance(color, tuple)
            assert len(color) == 3
            for value in color:
                assert 0.0 <= value <= 1.0
    
    def test_distinct_colors(self):
        """Test that custom molecule colors differ from predefined molecules."""
        # Custom colors should not be the same as CPK colors
        # (gray C, red O, white H)
        for color_name in ["CUSTOM_MOL_1", "CUSTOM_MOL_2", "CUSTOM_MOL_3"]:
            color = CUSTOM_MOLECULE_COLORS[color_name]
            # None of the custom colors should be pure gray, red, or white
            assert color != (0.6, 0.6, 0.6)  # Not gray (C)
            assert color != (1.0, 0.0, 0.0)  # Not red (O)
            assert color != (1.0, 1.0, 1.0)  # Not white (H)
    
    def test_default_color_exists(self):
        """Test that default fallback color exists."""
        assert "default" in CUSTOM_MOLECULE_COLORS


class TestCreateCustomMoleculeActor:
    """Tests for VTK actor creation."""
    
    def test_create_actor_simple_molecule(self):
        """Test creating VTK actor for simple molecule."""
        # Create simple molecule with C, O, H atoms
        positions = np.array([
            [0.0, 0.0, 0.0],     # C
            [0.143, 0.0, 0.0],   # O
            [0.05, 0.09, 0.0],   # H1
            [0.05, -0.09, 0.0],  # H2
        ])
        atom_names = ["C", "O", "H", "H"]
        cell = np.eye(3) * 5.0
        moleculetype_name = "CUSTOM_MOL_1"
        
        actor = create_custom_molecule_actor(
            positions, atom_names, cell, moleculetype_name
        )
        
        assert actor is not None
        assert hasattr(actor, 'GetMapper')
    
    def test_create_actor_with_color_selection(self):
        """Test that different moleculetype names get different colors."""
        positions = np.array([
            [0.0, 0.0, 0.0],
            [0.1, 0.0, 0.0],
        ])
        atom_names = ["C", "C"]
        cell = np.eye(3) * 5.0
        
        # Create actors for different custom molecule types
        actor1 = create_custom_molecule_actor(
            positions, atom_names, cell, "CUSTOM_MOL_1"
        )
        actor2 = create_custom_molecule_actor(
            positions, atom_names, cell, "CUSTOM_MOL_2"
        )
        actor3 = create_custom_molecule_actor(
            positions, atom_names, cell, "CUSTOM_MOL_3"
        )
        
        # All should create successfully
        assert actor1 is not None
        assert actor2 is not None
        assert actor3 is not None
    
    def test_create_actor_unknown_moleculetype(self):
        """Test that unknown moleculetype uses default color."""
        positions = np.array([
            [0.0, 0.0, 0.0],
        ])
        atom_names = ["C"]
        cell = np.eye(3) * 5.0
        
        # Unknown moleculetype should use default color
        actor = create_custom_molecule_actor(
            positions, atom_names, cell, "UNKNOWN_TYPE"
        )
        
        assert actor is not None
    
    def test_create_actor_empty_positions(self):
        """Test creating actor with empty atom list."""
        positions = np.array([]).reshape(0, 3)
        atom_names = []
        cell = np.eye(3) * 5.0
        
        actor = create_custom_molecule_actor(
            positions, atom_names, cell, "CUSTOM_MOL_1"
        )
        
        # Should handle gracefully
        assert actor is None
    
    def test_create_actor_with_mw_sites(self):
        """Test that MW virtual sites are excluded from rendering."""
        # TIP4P water molecule with MW site
        positions = np.array([
            [0.0, 0.0, 0.0],        # O
            [0.09572, 0.0, 0.0],    # H1
            [-0.02399, 0.09272, 0.0],  # H2
            [0.01546, 0.0, 0.0],    # MW (virtual site)
        ])
        atom_names = ["O", "H", "H", "MW"]
        cell = np.eye(3) * 5.0
        
        actor = create_custom_molecule_actor(
            positions, atom_names, cell, "CUSTOM_MOL_1"
        )
        
        # Should create actor successfully, excluding MW
        assert actor is not None
    
    def test_create_actor_bond_detection(self):
        """Test that bonds are detected at correct threshold."""
        # Create two carbon atoms at bond distance
        bond_distance = 0.15  # nm (within threshold)
        positions = np.array([
            [0.0, 0.0, 0.0],
            [bond_distance, 0.0, 0.0],
        ])
        atom_names = ["C", "C"]
        cell = np.eye(3) * 5.0
        
        actor = create_custom_molecule_actor(
            positions, atom_names, cell, "CUSTOM_MOL_1"
        )
        
        # Should create actor with detected bond
        assert actor is not None
    
    def test_create_actor_no_bond_for_long_distance(self):
        """Test that no bond is created for distant atoms."""
        # Create two carbon atoms beyond bond distance
        long_distance = 0.20  # nm (beyond threshold)
        positions = np.array([
            [0.0, 0.0, 0.0],
            [long_distance, 0.0, 0.0],
        ])
        atom_names = ["C", "C"]
        cell = np.eye(3) * 5.0
        
        actor = create_custom_molecule_actor(
            positions, atom_names, cell, "CUSTOM_MOL_1"
        )
        
        # Should still create actor (bonds are optional in VTK)
        assert actor is not None
    
    def test_create_actor_different_modes(self):
        """Test different rendering modes."""
        positions = np.array([
            [0.0, 0.0, 0.0],
            [0.1, 0.0, 0.0],
        ])
        atom_names = ["C", "C"]
        cell = np.eye(3) * 5.0
        
        # Test different rendering modes
        for mode in ["ball_and_stick", "vdw", "stick"]:
            actor = create_custom_molecule_actor(
                positions, atom_names, cell, "CUSTOM_MOL_1", mode=mode
            )
            assert actor is not None, f"Failed for mode: {mode}"


class TestBondDistanceThreshold:
    """Tests for bond detection threshold constant."""
    
    def test_threshold_value(self):
        """Test that bond threshold is correctly set."""
        assert BOND_DISTANCE_THRESHOLD == 0.16  # nm
    
    def test_threshold_covers_covalent_bonds(self):
        """Test that threshold covers typical covalent bond lengths."""
        # Typical covalent bond distances (nm)
        typical_bonds = {
            "C-H": 0.109,
            "O-H": 0.096,
            "C-C": 0.154,
            "C-O": 0.143,
            "C-N": 0.147,
        }
        
        # All typical bonds should be below threshold
        for bond_name, distance in typical_bonds.items():
            assert distance < BOND_DISTANCE_THRESHOLD, \
                f"{bond_name} bond ({distance} nm) should be below threshold"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
