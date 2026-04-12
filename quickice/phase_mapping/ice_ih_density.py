"""
Ice Ih density calculation using IAPWS R10-06(2009).

This module provides density calculations for Ice Ih (hexagonal ice) using
the IAPWS R10-06(2009) Revised Release on the Equation of State 2006 for H2O Ice Ih.

The underlying implementation is provided by the iapws library's _Ice function,
which implements the full IAPWS formulation for Ice Ih thermodynamic properties.

Reference:
    IAPWS R10-06(2009): Revised Release on the Equation of State 2006 for H2O Ice Ih
    https://www.iapws.org/release/Ice-2009.html

Note:
    The IAPWS formulation is valid for Ice Ih in its stability region:
    - T ≤ 273.16 K (Ih-Liquid-Vapor triple point)
    - P ≤ 208.566 MPa (Ih-II-III triple point pressure)
    - Below the melting and sublimation lines
    
    For conditions outside this range, the module returns a fallback density.
"""

import warnings
from functools import lru_cache

from iapws._iapws import _Ice

# Fallback density when IAPWS calculation fails or is out of range
# This is the density at 273.15 K, 1 atm (0.101325 MPa)
FALLBACK_DENSITY_GCM3 = 0.9167


@lru_cache(maxsize=256)
def ice_ih_density_kgm3(T_K: float, P_MPa: float) -> float:
    """
    Calculate Ice Ih density in kg/m³ using IAPWS R10-06(2009).
    
    This function wraps the iapws._iapws._Ice() function with caching for
    performance and error handling with fallback.
    
    Args:
        T_K: Temperature in Kelvin
        P_MPa: Pressure in MPa
    
    Returns:
        Density in kg/m³. Returns FALLBACK_DENSITY_GCM3 * 1000 if the
        IAPWS calculation fails or is outside the valid range.
    
    Note:
        The IAPWS formulation issues warnings for metastable ice conditions
        (ice in liquid region). These warnings are suppressed.
        
    Example:
        >>> ice_ih_density_kgm3(273.15, 0.101325)
        916.72...  # Approximately 916.72 kg/m³ at 0°C, 1 atm
        
        >>> ice_ih_density_kgm3(100, 0.101325)
        933.05...  # Higher density at lower temperature
    """
    try:
        # Suppress metastable ice warnings from iapws
        # _Ice issues warnings like "Metastable ice in liquid region"
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Metastable ice")
            props = _Ice(T_K, P_MPa)
            return props["rho"]
    except (NotImplementedError, ValueError, OverflowError):
        # NotImplementedError: P > 208.566 MPa or T > 273.16 K (out of IAPWS range)
        # ValueError: Invalid input values
        # OverflowError: Numerical overflow in extreme conditions
        return FALLBACK_DENSITY_GCM3 * 1000


def ice_ih_density_gcm3(T_K: float, P_MPa: float) -> float:
    """
    Calculate Ice Ih density in g/cm³ using IAPWS R10-06(2009).
    
    This is a convenience wrapper that converts the result from kg/m³ to g/cm³.
    
    Args:
        T_K: Temperature in Kelvin
        P_MPa: Pressure in MPa
    
    Returns:
        Density in g/cm³. Returns FALLBACK_DENSITY_GCM3 if the
        IAPWS calculation fails or is outside the valid range.
    
    Example:
        >>> ice_ih_density_gcm3(273.15, 0.101325)
        0.9167...  # Approximately 0.9167 g/cm³ at 0°C, 1 atm
        
        >>> ice_ih_density_gcm3(100, 0.101325)
        0.9330...  # Higher density at lower temperature
    """
    return ice_ih_density_kgm3(T_K, P_MPa) / 1000.0
