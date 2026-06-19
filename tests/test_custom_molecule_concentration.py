"""Unit tests for CustomMoleculeInserter concentration calculation methods.

Tests the calculate_molecule_count() and calculate_concentration() static methods
to ensure correct conversion between molecule count and concentration.
"""

import pytest
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
from quickice.structure_generation.types import WATER_VOLUME_NM3


class TestConcentrationCalculations:
    """Test concentration ↔ molecule count conversion methods."""
    
    def test_calculate_molecule_count_basic(self):
        """Test basic molecule count calculation from concentration."""
        # 0.1 M in 100 nm³ should give ~6 molecules
        count = CustomMoleculeInserter.calculate_molecule_count(0.1, 100.0)
        assert count == 6
    
    def test_calculate_molecule_count_zero_concentration(self):
        """Test that zero concentration gives zero molecules."""
        count = CustomMoleculeInserter.calculate_molecule_count(0.0, 100.0)
        assert count == 0
    
    def test_calculate_molecule_count_zero_volume(self):
        """Test that zero volume gives zero molecules."""
        count = CustomMoleculeInserter.calculate_molecule_count(0.1, 0.0)
        assert count == 0
    
    def test_calculate_molecule_count_high_concentration(self):
        """Test high concentration calculation."""
        # 1.0 M in 100 nm³ should give ~60 molecules
        count = CustomMoleculeInserter.calculate_molecule_count(1.0, 100.0)
        assert 55 <= count <= 65  # Allow for rounding
    
    def test_calculate_concentration_basic(self):
        """Test basic concentration calculation from molecule count."""
        # 6 molecules in 100 nm³ should give ~0.1 M
        concentration = CustomMoleculeInserter.calculate_concentration(6, 100.0)
        assert abs(concentration - 0.1) < 0.01
    
    def test_calculate_concentration_zero_count(self):
        """Test that zero molecule count gives zero concentration."""
        concentration = CustomMoleculeInserter.calculate_concentration(0, 100.0)
        assert concentration == 0.0
    
    def test_calculate_concentration_zero_volume(self):
        """Test that zero volume gives zero concentration (edge case)."""
        concentration = CustomMoleculeInserter.calculate_concentration(10, 0.0)
        assert concentration == 0.0
    
    def test_calculate_concentration_negative_count(self):
        """Test that negative count gives zero concentration (edge case)."""
        concentration = CustomMoleculeInserter.calculate_concentration(-5, 100.0)
        assert concentration == 0.0
    
    def test_calculate_concentration_negative_volume(self):
        """Test that negative volume gives zero concentration (edge case)."""
        concentration = CustomMoleculeInserter.calculate_concentration(10, -100.0)
        assert concentration == 0.0
    
    def test_roundtrip_conversion(self):
        """Test that count → concentration → count gives consistent results."""
        # Start with 6 molecules in 100 nm³
        original_count = 6
        volume = 100.0
        
        # Convert to concentration
        concentration = CustomMoleculeInserter.calculate_concentration(original_count, volume)
        
        # Convert back to count
        final_count = CustomMoleculeInserter.calculate_molecule_count(concentration, volume)
        
        # Should get the same count back (within rounding)
        assert abs(final_count - original_count) <= 1
    
    def test_multiple_volumes(self):
        """Test calculations across different volumes."""
        concentration = 0.1  # M
        
        # Test various volumes
        volumes_and_expected_counts = [
            (10.0, 1),    # Small volume
            (50.0, 3),    # Medium volume
            (100.0, 6),   # Reference volume
            (500.0, 30),  # Large volume
        ]
        
        for volume, expected_count in volumes_and_expected_counts:
            count = CustomMoleculeInserter.calculate_molecule_count(concentration, volume)
            # Allow for rounding
            assert abs(count - expected_count) <= 1, \
                f"Volume {volume} nm³: expected ~{expected_count} molecules, got {count}"
    
    def test_multiple_concentrations(self):
        """Test calculations across different concentrations."""
        volume = 100.0  # nm³
        
        # Test various concentrations
        concentrations_and_expected_counts = [
            (0.05, 3),   # Low concentration
            (0.1, 6),    # Reference concentration
            (0.5, 30),   # Medium concentration
            (1.0, 60),   # High concentration
        ]
        
        for concentration, expected_count in concentrations_and_expected_counts:
            count = CustomMoleculeInserter.calculate_molecule_count(concentration, volume)
            # Allow for rounding
            assert abs(count - expected_count) <= 2, \
                f"Concentration {concentration} M: expected ~{expected_count} molecules, got {count}"
    
    def test_realistic_system(self):
        """Test with realistic liquid region volume."""
        # Typical liquid region: ~1000 water molecules = ~30 nm³
        # At 0.1 M, expect ~2 molecules
        volume = 1000 * WATER_VOLUME_NM3  # nm³
        count = CustomMoleculeInserter.calculate_molecule_count(0.1, volume)
        assert 1 <= count <= 3  # Allow for rounding
        
        # Reverse: 2 molecules in 30 nm³ → ~0.1 M
        concentration = CustomMoleculeInserter.calculate_concentration(2, volume)
        assert abs(concentration - 0.1) < 0.1
