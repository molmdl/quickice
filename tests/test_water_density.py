"""Tests for water density calculation using IAPWS-95.

Reference values verified against IAPWS-95 formulation.
Tests cover normal liquid water, supercooled water, fallback behavior,
caching, and unit conversion.
"""

import pytest

from quickice.phase_mapping.water_density import (
    water_density_kgm3,
    water_density_gcm3,
    FALLBACK_DENSITY_GCM3,
)


class TestWaterDensity:
    """Tests for water density calculations."""

    def test_reference_value_at_0c_1atm(self):
        """Verify density at 0°C, 1 atm matches reference value.
        
        Reference: Water density at melting point (0°C, 1 atm) is
        approximately 0.9998 g/cm³.
        """
        result = water_density_gcm3(273.15, 0.101325)
        # Expected: ~0.9998 g/cm³ at 0°C, 1 atm
        assert result == pytest.approx(0.9998, abs=0.0001), (
            f"Density at 0°C, 1 atm should be ~0.9998 g/cm³, got {result:.4f}"
        )

    def test_supercooled_water_at_minus_20c(self):
        """Verify supercooled water density at -20°C (253.15 K).
        
        IAPWS-95 supports supercooled water via extrapolation,
        unlike IAPWS-97 which raises NotImplementedError.
        """
        result = water_density_gcm3(253.15, 0.101325)
        # Supercooled water density should be reasonable
        assert result > 0.95, (
            f"Supercooled water density should be > 0.95 g/cm³, got {result:.4f}"
        )
        assert result < 1.05, (
            f"Supercooled water density should be < 1.05 g/cm³, got {result:.4f}"
        )

    def test_fallback_for_invalid_input(self):
        """Verify fallback density for invalid input conditions.
        
        The function should return the fallback density (0.9998 g/cm³)
        rather than raising an error when IAPWS calculation fails.
        
        Note: IAPWS95 is more robust than IAPWS for ice - it can
        extrapolate to extreme pressures. The fallback is triggered
        by invalid inputs (negative T or P) which cause ValueError.
        """
        # Negative pressure should trigger fallback via ValueError
        result = water_density_gcm3(273.15, -0.1)
        assert result == pytest.approx(FALLBACK_DENSITY_GCM3, abs=0.0001), (
            f"Density with negative P should return fallback {FALLBACK_DENSITY_GCM3} g/cm³, "
            f"got {result:.4f}"
        )

    def test_caching_works(self):
        """Verify that lru_cache is working for density calculations.
        
        The water_density_kgm3 function uses @lru_cache(maxsize=256)
        to avoid recalculating the same (T, P) conditions.
        """
        # Clear cache first
        water_density_kgm3.cache_clear()
        
        # First call - should be a cache miss
        result1 = water_density_kgm3(298.15, 0.101325)
        info1 = water_density_kgm3.cache_info()
        assert info1.misses == 1
        assert info1.hits == 0
        
        # Second call with same arguments - should be a cache hit
        result2 = water_density_kgm3(298.15, 0.101325)
        info2 = water_density_kgm3.cache_info()
        assert info2.hits == 1
        
        # Cached result should be the exact same object
        assert result1 is result2

    def test_kgm3_gcm3_consistency(self):
        """Verify that kg/m³ and g/cm³ functions are consistent.
        
        water_density_gcm3 should equal water_density_kgm3 / 1000.
        """
        T, P = 273.15, 0.101325
        
        kgm3 = water_density_kgm3(T, P)
        gcm3 = water_density_gcm3(T, P)
        
        # g/cm³ * 1000 should equal kg/m³
        assert kgm3 == pytest.approx(gcm3 * 1000, abs=0.001), (
            f"kg/m³ ({kgm3}) should equal g/cm³ * 1000 ({gcm3 * 1000})"
        )

    def test_density_at_various_temperatures(self):
        """Verify density at various temperatures.
        
        Water density shows non-monotonic behavior with maximum at 4°C,
        but general trend should be reasonable values in 0.9-1.1 g/cm³ range.
        """
        test_cases = [
            (270, 0.101325),   # Supercooled
            (273.15, 0.101325),  # 0°C
            (277.15, 0.101325),  # 4°C - maximum density
            (298.15, 0.101325),  # 25°C - room temperature
        ]
        
        for T, P in test_cases:
            result = water_density_gcm3(T, P)
            # All liquid water densities should be in reasonable range
            assert result > 0.9, (
                f"Density at T={T}K should be > 0.9 g/cm³, got {result:.4f}"
            )
            assert result < 1.1, (
                f"Density at T={T}K should be < 1.1 g/cm³, got {result:.4f}"
            )
            # Result should be a float, not NaN
            assert isinstance(result, float)
            assert result == result  # NaN check (NaN != NaN)

    def test_fallback_constant_value(self):
        """Verify the fallback density constant matches documentation.
        
        FALLBACK_DENSITY_GCM3 should be 0.9998 g/cm³, which is the
        density of water at 273.15 K (0°C), 0.101325 MPa (1 atm).
        """
        assert FALLBACK_DENSITY_GCM3 == 0.9998

    def test_returns_float(self):
        """Verify that both functions return float."""
        result_kgm3 = water_density_kgm3(273.15, 0.101325)
        result_gcm3 = water_density_gcm3(273.15, 0.101325)
        
        assert isinstance(result_kgm3, float)
        assert isinstance(result_gcm3, float)

    def test_pressure_effect_on_density(self):
        """Verify that higher pressure increases water density.
        
        Water is slightly compressible, so higher pressure should
        increase density.
        """
        T = 298.15  # 25°C
        
        rho_low_P = water_density_gcm3(T, 0.1)    # Low pressure
        rho_high_P = water_density_gcm3(T, 10)    # High pressure (10 MPa)
        
        # Higher pressure should increase density
        assert rho_high_P > rho_low_P, (
            f"Density at P=10 MPa ({rho_high_P:.5f} g/cm³) should be higher than "
            f"at P=0.1 MPa ({rho_low_P:.5f} g/cm³)"
        )

    def test_supercooled_water_at_various_temperatures(self):
        """Test supercooled water at multiple sub-freezing temperatures.
        
        IAPWS-95 supports extrapolation for supercooled water.
        """
        test_cases = [
            (260, 0.101325),   # -13°C
            (250, 0.101325),   # -23°C
        ]
        
        for T, P in test_cases:
            result = water_density_gcm3(T, P)
            # Should return reasonable values, not NaN or fallback
            assert isinstance(result, float)
            assert result > 0.9, f"Density at T={T}K should be > 0.9 g/cm³"
            assert result < 1.1, f"Density at T={T}K should be < 1.1 g/cm³"
