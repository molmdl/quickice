"""
Curve-based ice phase lookup.

Determines ice phase by evaluating boundary curves, not polygon containment.
Uses IAPWS R14-08 melting curves and linear interpolation for solid-solid boundaries.

This approach eliminates polygon overlap errors by directly evaluating which
boundary curves the (T,P) point is above or below.
"""

import math
from quickice.phase_mapping.melting_curves import melting_pressure
from quickice.phase_mapping.solid_boundaries import (
    solid_boundary, ih_ii_boundary, ii_iii_boundary, iii_v_boundary,
    ii_v_boundary, v_vi_boundary, vi_vii_boundary, VII_VIII_ORDERING_TEMP
)
from quickice.phase_mapping.triple_points import TRIPLE_POINTS
from quickice.phase_mapping.errors import UnknownPhaseError

# Phase metadata (from IAPWS R14-08 and LSBU Water Phase Data)
PHASE_METADATA = {
    "ice_ih": {"name": "Ice Ih", "density": 0.9167},
    "ice_ic": {"name": "Ice Ic", "density": 0.92},
    "ice_ii": {"name": "Ice II", "density": 1.18},
    "ice_iii": {"name": "Ice III", "density": 1.16},
    "ice_v": {"name": "Ice V", "density": 1.24},
    "ice_vi": {"name": "Ice VI", "density": 1.31},
    "ice_vii": {"name": "Ice VII", "density": 1.65},
    "ice_viii": {"name": "Ice VIII", "density": 1.65},
}


def _build_result(phase_id: str, T: float, P: float) -> dict:
    """Build result dictionary for a matched phase.
    
    Args:
        phase_id: Phase identifier (e.g., "ice_ih")
        T: Temperature in Kelvin
        P: Pressure in MPa
    
    Returns:
        Dict with phase_id, phase_name, density, temperature, pressure
    """
    meta = PHASE_METADATA[phase_id]
    return {
        "phase_id": phase_id,
        "phase_name": meta["name"],
        "density": meta["density"],
        "temperature": T,
        "pressure": P,
    }


def lookup_phase(temperature: float, pressure: float) -> dict:
    """
    Determine ice phase using curve-based boundary evaluation.
    
    This function uses hierarchical curve evaluation to determine which ice
    polymorph is stable at the given temperature and pressure. It checks
    boundaries in order from highest pressure phases to lowest, eliminating
    the ambiguity of polygon containment methods.
    
    Args:
        temperature: Temperature in Kelvin
        pressure: Pressure in MPa
    
    Returns:
        Dict with phase_id, phase_name, density, temperature, pressure
    
    Raises:
        UnknownPhaseError: If no phase matches the given conditions
    
    Algorithm:
        1. High pressure phases (VII/VIII at P > 2100 MPa)
        2. Ice VI region (between V-VI and VI-VII boundaries)
        3. Ice V region (check V-VI and II-V boundaries)
        4. Ice II region (check Ih-II and II-III boundaries)
        5. Ice III region (narrow wedge, check II-III and III-V boundaries)
        6. Ice Ih region (check Ih melting curve)
        7. Ice Ic (metastable, low T low P)
    """
    T, P = temperature, pressure
    phase_id = None
    
    # 1. High pressure phases (VII/VIII at P > 2100 MPa)
    # These phases exist at very high pressures
    if P > 2100:
        # VII-VIII transition at 278K (ordering transition)
        phase_id = "ice_viii" if T < VII_VIII_ORDERING_TEMP else "ice_vii"
        return _build_result(phase_id, T, P)
    
    # 2. Ice VI region (between V-VI and VI-VII boundaries)
    # Ice VI: T(273.31-355K at high P), P(626-2200 MPa)
    # Note: At lower temperatures, Ice VI extends down to T=218.95K (II-V-VI TP)
    if T >= 218.95 and P > 620:
        # Check if above VI-VII boundary for T > 278K
        if T > 278:
            P_vi_vii = vi_vii_boundary(T)
            phase_id = "ice_vii" if P > P_vi_vii else "ice_vi"
        else:
            # Below VI-VII-VIII triple point, all high P is Ice VI
            phase_id = "ice_vi"
        return _build_result(phase_id, T, P)
    
    # 3. Ice V region
    # Ice V: T(218.95-273.31K), P(344-626 MPa)
    if 218.95 <= T <= 273.31 and P > 344:
        P_v_vi = v_vi_boundary(T)
        if P < P_v_vi:
            # Below V-VI boundary, check lower boundary (II-V)
            P_ii_v = ii_v_boundary(T)
            if P > P_ii_v:
                # Above II-V boundary and below V-VI boundary
                phase_id = "ice_v"
                return _build_result(phase_id, T, P)
    
    # 4. Ice II region
    # Ice II: T(100-248.85K at high P), P(200-620 MPa)
    # The II region has two parts: above and below the Ih-II-III triple point
    if T < 248.85 and P > 200:
        if T >= 238.55:
            # Above Ih-II-III triple point
            # Check II-III boundary
            P_ii_iii = ii_iii_boundary(T)
            if P > P_ii_iii:
                # Above II-III boundary = Ice II
                phase_id = "ice_ii"
                return _build_result(phase_id, T, P)
        else:
            # Below Ih-II-III triple point (T < 238.55K)
            # Check Ih-II boundary
            P_ih_ii = ih_ii_boundary(T)
            if P > P_ih_ii:
                # Above Ih-II boundary = Ice II
                phase_id = "ice_ii"
                return _build_result(phase_id, T, P)
    
    # 5. Ice III region (narrow wedge)
    # Ice III: T(238.55-256.165K), P(207.5-346.3 MPa)
    # This is a narrow region between II-III and III-V boundaries
    if 238.55 <= T <= 256.165 and P > 200:
        # Check boundaries to determine if in Ice III region
        if T <= 248.85:
            # Check II-III boundary (lower P boundary of Ice III)
            P_ii_iii = ii_iii_boundary(T)
            if P < P_ii_iii:
                # Below II-III boundary = Ice III
                phase_id = "ice_iii"
                return _build_result(phase_id, T, P)
        if T >= 248.85:
            # Check III-V boundary (upper P boundary of Ice III)
            P_iii_v = iii_v_boundary(T)
            if P < P_iii_v:
                # Below III-V boundary = Ice III
                phase_id = "ice_iii"
                return _build_result(phase_id, T, P)
    
    # 6. Ice Ih region
    # Ice Ih: T(100-273.16K), P(0-207.5 MPa at T=251.165K)
    # The Ih melting curve is the upper P boundary
    if T <= 273.16:
        try:
            P_melt = melting_pressure(T, "Ih")
            if P < P_melt:
                # Below melting curve = solid Ice Ih
                phase_id = "ice_ih"
                return _build_result(phase_id, T, P)
        except ValueError:
            # Outside Ih melting curve range (T < 251.165K)
            # At low T and moderate P, still Ice Ih
            if P < 200:
                phase_id = "ice_ih"
                return _build_result(phase_id, T, P)
    
    # 7. Ice Ic (metastable, low T low P)
    # Ice Ic: T(100-150K), P(0-100 MPa)
    # This is a metastable phase at very low temperatures and pressures
    if T < 150 and P < 100:
        phase_id = "ice_ic"
        return _build_result(phase_id, T, P)
    
    # 8. No match - unknown region
    # This could be:
    # - Liquid water region (above melting curves)
    # - Outside all known phase regions
    raise UnknownPhaseError(
        "No ice phase found for given conditions",
        temperature=T,
        pressure=P,
    )


class IcePhaseLookup:
    """Backward-compatible class wrapper for lookup_phase.
    
    This class provides the same interface as the old polygon-based lookup,
    but uses curve-based evaluation internally.
    """
    
    def __init__(self, data_path=None):
        """Initialize the phase lookup.
        
        Args:
            data_path: Ignored (kept for backward compatibility).
                      Curve-based lookup doesn't need external data files.
        """
        # No longer needs data file - curve functions are built-in
        pass
    
    def lookup(self, temperature: float, pressure: float) -> dict:
        """Find the ice phase at given T,P conditions.
        
        Args:
            temperature: Temperature in Kelvin
            pressure: Pressure in MPa
        
        Returns:
            Dict with phase_id, phase_name, density, temperature, pressure
        """
        return lookup_phase(temperature, pressure)
