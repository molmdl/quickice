"""
Water density calculation using IAPWS-95 formulation.

This module provides density calculations for liquid water (including supercooled
water) using the IAPWS-95 formulation. Unlike IAPWS-97, IAPWS-95 supports
extrapolation to metastable states including supercooled water at temperatures
below the freezing point.

The underlying implementation is provided by the iapws library's IAPWS95 class,
which implements the full IAPWS-95 formulation for water thermodynamic properties.

Reference:
    IAPWS-95: Revised Release on the IAPWS Formulation 1995 for the
    Thermodynamic Properties of Ordinary Water Substance for General and
    Scientific Use
    https://www.iapws.org/release/IAPWS-95.html

Note:
    IAPWS-95 supports supercooled water (T < 273.15 K) via extrapolation,
    which is essential for ice-water interfaces at sub-freezing temperatures.
    The formulation issues warnings for extrapolated states.
    
    For conditions where IAPWS calculation fails, the module returns a fallback
    density of 0.9998 g/cm³ (water density at 0°C, 1 atm - the melting point).
"""

import warnings
from functools import lru_cache

from iapws import IAPWS95

# Fallback density when IAPWS calculation fails or is out of range
# This is the density at 273.15 K (0°C), 0.101325 MPa (1 atm) - the melting point
FALLBACK_DENSITY_GCM3 = 0.9998


@lru_cache(maxsize=256)
def water_density_kgm3(T_K: float, P_MPa: float) -> float:
    """
    Calculate liquid water density in kg/m³ using IAPWS-95.
    
    This function wraps the iapws.IAPWS95() class with caching for
    performance and error handling with fallback.
    
    IAPWS-95 supports supercooled water (T < 273.15 K) via extrapolation,
    unlike IAPWS-97 which raises NotImplementedError at sub-freezing temperatures.
    
    Args:
        T_K: Temperature in Kelvin
        P_MPa: Pressure in MPa
    
    Returns:
        Density in kg/m³. Returns FALLBACK_DENSITY_GCM3 * 1000 if the
        IAPWS calculation fails, returns NaN, or is outside reasonable range.
    
    Note:
        The IAPWS-95 formulation issues warnings for extrapolated states
        (supercooled water). These warnings are suppressed.
        
    Example:
        >>> water_density_kgm3(273.15, 0.101325)
        999.84...  # Approximately 999.84 kg/m³ at 0°C, 1 atm
        
        >>> water_density_kgm3(253.15, 0.101325)  # Supercooled at -20°C
        993.7...  # Extrapolated value for supercooled water
    """
    try:
        # Suppress extrapolation warnings for supercooled water
        # IAPWS95 issues warnings like "extrapolated value" for T < 273.15 K
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="extrapolated")
            water = IAPWS95(T=T_K, P=P_MPa)
            rho = water.rho
            
            # Sanity check: density should be positive and reasonable
            # Water density at extreme conditions: < 2000 kg/m³
            if rho > 0 and rho < 2000:
                return rho
            else:
                return FALLBACK_DENSITY_GCM3 * 1000
    except (NotImplementedError, ValueError, OverflowError):
        # NotImplementedError: Conditions outside formulation range
        # ValueError: Invalid input values (e.g., negative T or P)
        # OverflowError: Numerical overflow in extreme conditions
        return FALLBACK_DENSITY_GCM3 * 1000


def water_density_gcm3(T_K: float, P_MPa: float) -> float:
    """
    Calculate liquid water density in g/cm³ using IAPWS-95.
    
    This is a convenience wrapper that converts the result from kg/m³ to g/cm³.
    
    Args:
        T_K: Temperature in Kelvin
        P_MPa: Pressure in MPa
    
    Returns:
        Density in g/cm³. Returns FALLBACK_DENSITY_GCM3 if the
        IAPWS calculation fails or is outside reasonable range.
    
    Example:
        >>> water_density_gcm3(273.15, 0.101325)
        0.9998...  # Approximately 0.9998 g/cm³ at 0°C, 1 atm
        
        >>> water_density_gcm3(253.15, 0.101325)  # Supercooled at -20°C
        0.9937...  # Extrapolated value for supercooled water
    """
    return water_density_kgm3(T_K, P_MPa) / 1000.0
