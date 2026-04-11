"""Tests for Ice Ih density calculation using IAPWS R10-06(2009).

Reference values verified against IAPWS R10-06(2009) formulation.
"""

import pytest

from quickice.phase_mapping.ice_ih_density import (
    ice_ih_density_kgm3,
    ice_ih_density_gcm3,
    FALLBACK_DENSITY_GCM3,
)


class TestIceIhDensity:
    """Tests for Ice Ih density calculations."""

    def test_reference_values_at_1atm(self):
        """Verify density at 1 atm (0.101325 MPa) matches IAPWS reference values.
        
        Reference: IAPWS R10-06(2009) - Ice Ih density decreases with
        increasing temperature due to thermal expansion.
        """
        # At 1 atm, density decreases with increasing temperature
        test_cases = [
            (100, 0.101325, 0.93305),   # 100K: 0.93305 g/cm³
            (150, 0.101325, 0.93061),   # 150K: 0.93061 g/cm³
            (200, 0.101325, 0.92613),   # 200K: 0.92613 g/cm³
            (250, 0.101325, 0.92000),   # 250K: 0.92000 g/cm³
            (270, 0.101325, 0.91718),   # 270K: 0.91718 g/cm³
            (273.15, 0.101325, 0.91672), # 273.15K (0°C): 0.91672 g/cm³
        ]
        
        for T, P, expected_gcm3 in test_cases:
            actual = ice_ih_density_gcm3(T, P)
            assert actual == pytest.approx(expected_gcm3, abs=0.0001), (
                f"Density at T={T}K, P={P}MPa should be {expected_gcm3} g/cm³, "
                f"got {actual:.5f} g/cm³"
            )

    def test_reference_values_at_high_pressure(self):
        """Verify density at high pressure matches IAPWS reference values.
        
        Higher pressure compresses the ice, increasing density.
        """
        test_cases = [
            (251, 200, 0.93983),    # 251K, 200 MPa: 0.93983 g/cm³
            (273.15, 200, 0.93737), # 273.15K, 200 MPa: 0.93737 g/cm³
        ]
        
        for T, P, expected_gcm3 in test_cases:
            actual = ice_ih_density_gcm3(T, P)
            assert actual == pytest.approx(expected_gcm3, abs=0.0001), (
                f"Density at T={T}K, P={P}MPa should be {expected_gcm3} g/cm³, "
                f"got {actual:.5f} g/cm³"
            )

    def test_fallback_for_pressure_out_of_range(self):
        """Verify fallback density for P > 208.566 MPa (IAPWS limit).
        
        The IAPWS formulation for Ice Ih is valid up to P=208.566 MPa
        (the Ih-II-III triple point pressure). Above this, Ice Ih is
        not the stable phase.
        
        The function should return the fallback density (0.9167 g/cm³)
        rather than raising an error.
        """
        # P > 208.566 MPa should return fallback
        result = ice_ih_density_gcm3(251, 209)
        assert result == pytest.approx(FALLBACK_DENSITY_GCM3, abs=0.0001), (
            f"Density at P=209 MPa (above IAPWS limit) should return fallback "
            f"{FALLBACK_DENSITY_GCM3} g/cm³, got {result:.5f} g/cm³"
        )
        
        # Even higher pressure should also return fallback
        result = ice_ih_density_gcm3(200, 300)
        assert result == pytest.approx(FALLBACK_DENSITY_GCM3, abs=0.0001)

    def test_density_increases_with_decreasing_temperature(self):
        """Verify that density increases as temperature decreases.
        
        Ice Ih has negative thermal expansion coefficient at low T,
        but generally density increases with decreasing temperature
        due to reduced molecular vibration.
        """
        P = 0.101325  # 1 atm
        
        # Density at 100K should be higher than at 273K
        rho_100K = ice_ih_density_gcm3(100, P)
        rho_273K = ice_ih_density_gcm3(273, P)
        
        assert rho_100K > rho_273K, (
            f"Density at 100K ({rho_100K:.5f} g/cm³) should be higher than "
            f"at 273K ({rho_273K:.5f} g/cm³)"
        )

    def test_caching_works(self):
        """Verify that lru_cache is working for density calculations.
        
        The ice_ih_density_kgm3 function uses @lru_cache(maxsize=256)
        to avoid recalculating the same (T, P) conditions.
        """
        # Clear cache first
        ice_ih_density_kgm3.cache_clear()
        
        # First call - should be a cache miss
        result1 = ice_ih_density_kgm3(200, 50)
        info1 = ice_ih_density_kgm3.cache_info()
        assert info1.misses == 1
        assert info1.hits == 0
        
        # Second call with same arguments - should be a cache hit
        result2 = ice_ih_density_kgm3(200, 50)
        info2 = ice_ih_density_kgm3.cache_info()
        assert info2.hits == 1
        
        # Cached result should be the exact same object
        assert result1 is result2

    def test_kgm3_gcm3_consistency(self):
        """Verify that kg/m³ and g/cm³ functions are consistent.
        
        ice_ih_density_gcm3 should equal ice_ih_density_kgm3 / 1000.
        """
        T, P = 273.15, 0.101325
        
        kgm3 = ice_ih_density_kgm3(T, P)
        gcm3 = ice_ih_density_gcm3(T, P)
        
        # g/cm³ * 1000 should equal kg/m³
        assert kgm3 == pytest.approx(gcm3 * 1000, abs=0.001), (
            f"kg/m³ ({kgm3}) should equal g/cm³ * 1000 ({gcm3 * 1000})"
        )

    def test_pressure_increases_density(self):
        """Verify that higher pressure results in higher density.
        
        Ice Ih is compressible, so higher pressure should increase density.
        """
        T = 273.15
        
        rho_low_P = ice_ih_density_gcm3(T, 0.1)    # Low pressure
        rho_high_P = ice_ih_density_gcm3(T, 100)   # High pressure
        
        assert rho_high_P > rho_low_P, (
            f"Density at P=100 MPa ({rho_high_P:.5f} g/cm³) should be higher than "
            f"at P=0.1 MPa ({rho_low_P:.5f} g/cm³)"
        )

    def test_fallback_constant_value(self):
        """Verify the fallback density constant matches documentation.
        
        FALLBACK_DENSITY_GCM3 should be 0.9167 g/cm³, which is the
        density of Ice Ih at 273.15K, 1 atm.
        """
        assert FALLBACK_DENSITY_GCM3 == 0.9167

    def test_temperature_edge_case_very_low(self):
        """Test density at very low temperature (50K).
        
        IAPWS formulation should work at very low temperatures.
        """
        # Very low temperature should still work
        result = ice_ih_density_gcm3(50, 0.101325)
        assert result > 0.93  # Should be higher than at 100K
        assert result < 1.0   # But still reasonable for Ice Ih

    def test_returns_float(self):
        """Verify that both functions return float."""
        result_kgm3 = ice_ih_density_kgm3(273.15, 0.101325)
        result_gcm3 = ice_ih_density_gcm3(273.15, 0.101325)
        
        assert isinstance(result_kgm3, float)
        assert isinstance(result_gcm3, float)
