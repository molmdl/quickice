"""
Curve-based ice phase lookup.

Determines ice phase by evaluating boundary curves, not polygon containment.
Uses IAPWS R14-08(2011) melting curves and linear interpolation for solid-solid boundaries.

Triple point data sources:
- IAPWS R14-08(2011) for melting curve reference points
- Journaux et al. (2019, 2020) for II-III-V and II-V-VI triple points
- LSBU Water Phase Data for additional triple point values

This approach eliminates polygon overlap errors by directly evaluating which
boundary curves the (T,P) point is above or below.
"""

from quickice.phase_mapping.melting_curves import melting_pressure
from quickice.phase_mapping.solid_boundaries import (
    solid_boundary, ih_ii_boundary, ii_iii_boundary, iii_v_boundary,
    ii_v_boundary, v_vi_boundary, vi_vii_boundary, vii_viii_boundary,
    VII_VIII_ORDERING_TEMP,
    xi_boundary, ix_boundary, x_boundary, xv_boundary,
)
from quickice.phase_mapping.triple_points import TRIPLE_POINTS
from quickice.phase_mapping.errors import UnknownPhaseError

# Phase metadata (from IAPWS R14-08 and LSBU Water Phase Data)
PHASE_METADATA = {
    "ice_ih": {
        "name": "Ice Ih",
        "density": 0.9167,
        "density_note": "Density varies with temperature and pressure. Value shown is at reference conditions (273.15 K, 0.101325 MPa). See IAPWS R10-06(2009): Revised Release on the Equation of State 2006 for H2O Ice Ih for complete equation of state (https://www.iapws.org/release/Ice-2009.html)."
    },
    "ice_ic": {"name": "Ice Ic", "density": 0.92},
    "ice_ii": {"name": "Ice II", "density": 1.18},
    "ice_iii": {"name": "Ice III", "density": 1.16},
    "ice_v": {"name": "Ice V", "density": 1.24},
    "ice_vi": {"name": "Ice VI", "density": 1.31},
    "ice_vii": {"name": "Ice VII", "density": 1.65},
    "ice_viii": {"name": "Ice VIII", "density": 1.65},
    # Proton-ordered phases
    "ice_xi": {"name": "Ice XI", "density": 0.92},   # Proton-ordered Ih
    "ice_ix": {"name": "Ice IX", "density": 1.16},   # Proton-ordered III
    "ice_xv": {"name": "Ice XV", "density": 1.31},   # Proton-ordered VI
    # Symmetric hydrogen bond phase
    "ice_x": {"name": "Ice X", "density": 2.79},    # Symmetric H bonds
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
    
    Unlike polygon-based approaches, this method:
    - Directly evaluates boundary curves (no geometric containment)
    - Eliminates overlap errors between phase regions
    - Uses IAPWS R14-08 certified melting curves (HIGH confidence)
    - Uses linear interpolation for solid-solid boundaries (MEDIUM confidence)
    
    Args:
        temperature: Temperature in Kelvin
        pressure: Pressure in MPa
    
    Returns:
        Dict with phase_id, phase_name, density, temperature, pressure
    
    Raises:
        UnknownPhaseError: If no phase matches the given conditions
    
    Algorithm (evaluated in order, first match wins):
        0. Ice X (extreme pressure phase)
           - P > 30 GPa (30000 MPa)
           - Symmetric hydrogen bonds at extreme pressure
           
        1. High pressure phases (VII/VIII at P > 2100 MPa)
           - VIII if T < 278K (ordered proton structure)
           - VII if T >= 278K (disordered proton structure)
        
        1b. Ice XV (proton-ordered Ice VI)
           - T = 80-108K
           - P ≈ 1.1 GPa (1000-1200 MPa)
           
        2. Ice VI region (between V-VI and VI-VII boundaries)
           - T >= 218.95K (extends from II-V-VI triple point)
           - P > 620 MPa (approximately, varies with T)
           - Check VI-VII boundary for T > 278K
           
        3. Ice V region (between II-V and V-VI boundaries)
           - T in [218.95, 273.31]K
           - P > 344 MPa
           - Below V-VI boundary, above II-V boundary
           
        3b. Ice IX (proton-ordered Ice III)
           - T < 140K
           - P = 200-400 MPa
           - Ordered form of Ice III
           - Checked before Ice II since conditions overlap
           
        4. Ice II region (below Ih-II-III triple point)
           - T < 249.4K (max temp at II-III-V triple point)
           - P > 200 MPa
           - Above Ih-II boundary (T < 238.45K) or
           - Above II-III boundary (T >= 238.45K)
           
        5. Ice III region (narrow wedge)
           - T in [238.45, 256.164]K (narrow wedge)
           - P > 200 MPa
           - Between II-III and III-V boundaries
           
        5c. Ice XI (proton-ordered Ice Ih)
           - T < 72K
           - P < 200 MPa
           - Ordered form of Ice Ih at very low temperatures
           
        6. Ice Ih region (below melting curve)
           - T <= 273.16K (Ih-Liquid-Vapor triple point)
           - P < melting pressure at T
           
        7. Ice Ic (metastable, low T low P)
           - T < 150K, P < 100 MPa
           - Only if no other phase matched
    
    Phase boundaries reference:
        - Ih-II: Linear approximation from Ih-II-III triple point
        - II-III: Linear interpolation from Ih-II-III to II-III-V triple points
        - III-V: Linear interpolation from II-III-V to III-V-Liquid triple points
        - II-V: Linear interpolation from II-V-VI to II-III-V triple points
        - V-VI: Linear interpolation from II-V-VI to V-VI-Liquid triple points
        - VI-VII: Linear interpolation from VI-VII-VIII to VI-VII-Liquid triple points
        - Ih melting: IAPWS R14-08 equation (HIGH confidence)
        - VII-VIII ordering: Fixed at T=278K, P=2100 MPa
        - Ice X boundary: P > x_boundary(T), interpolates through VII_VIII_X (62 GPa at 100K),
                         VII_X_Transition (30 GPa at 300K), and VII_X_Liquid (43 GPa at 1000K)
        - Ice XV boundary: P ≈ 1.1 GPa at T=80-108K
        - Ice IX boundary: P decreases from 200 MPa at T=140K
        - Ice XI boundary: T < 72K at low P
    """
    T, P = temperature, pressure
    phase_id = None
    
    # 0. Ice X region (symmetric hydrogen bonds at extreme pressure)
    # Ice X: P > x_boundary(T) where boundary varies from 30-62 GPa depending on T
    # Quick filter: P > 30000 MPa to avoid computing x_boundary for low-P cases
    if P > 30000:
        P_x = x_boundary(T)
        if P > P_x:
            phase_id = "ice_x"
            return _build_result(phase_id, T, P)
    
    # 1. High pressure phases (VII/VIII at P > 2100 MPa)
    # These phases exist at very high pressures
    if P > 2100:
        # VII-VIII boundary: curved from (278K, 2100 MPa) to (100K, 62000 MPa)
        # Above this boundary: Ice VIII (low-T form) or Ice X (at very high P)
        # Below this boundary: Ice VII (high-T form) or Ice VI (at lower P)
        #
        # For T <= 100K: the boundary meets X at 62 GPa
        # - Below 62 GPa: Ice VIII (the low-T form is stable)
        # - Above 62 GPa: Ice X
        #
        # For 100K < T < 278K:
        # - Above VII-VIII boundary: Ice VIII
        # - Below VII-VIII boundary: Ice VII
        #
        # For T >= 278K: Ice VII OR Liquid (must check melting curve for T > 354.75K)
        if T > 354.75:
            # Above VI-VII-Liquid triple point: check VII melting curve
            # VII melting curve valid for 355K < T <= 715K
            # For Ice VII: P > P_melt(T) means solid, P < P_melt(T) means liquid
            # (Unlike Ice Ih where lower P = solid; Ice VII needs high P to stay solid)
            try:
                P_melt_vii = melting_pressure(T, "VII")
                if P > P_melt_vii:
                    # Above melting curve = solid Ice VII (high pressure keeps it solid)
                    phase_id = "ice_vii"
                else:
                    # Below melting curve = liquid water
                    raise UnknownPhaseError(
                        "Liquid water region (below Ice VII melting curve)",
                        temperature=T,
                        pressure=P,
                    )
            except ValueError:
                # T outside VII melting curve range (T > 715K)
                # At very high T, likely liquid or supercritical
                raise UnknownPhaseError(
                    f"Temperature {T}K outside Ice VII melting curve range",
                    temperature=T,
                    pressure=P,
                )
        elif T >= 278:
            # T in [278, 354.75]: solid Ice VII, below the melting curve boundary
            phase_id = "ice_vii"
        elif T <= 100:
            # At T <= 100K, all pressures below X boundary are Ice VIII
            phase_id = "ice_viii"
        else:
            # For 100K < T < 278K: use the boundary
            P_vii_viii = vii_viii_boundary(T)
            phase_id = "ice_viii" if P > P_vii_viii else "ice_vii"
        return _build_result(phase_id, T, P)
    
    # 1b. Ice XV region (ordered Ice VI at T=80-108K, P≈0.95-2.1 GPa)
    # Ice XV is the proton-ordered form of Ice VI, stable across a pressure band
    if 80.0 <= T <= 108.0 and 950 <= P <= 2100:
        phase_id = "ice_xv"
        return _build_result(phase_id, T, P)
    
    # 2. Ice VI region (between V-VI and VI-VII boundaries)
    # Ice VI: T(273.31-355K at high P), P(626-2200 MPa)
    # Note: At lower temperatures, Ice VI extends down to T=218.95K (II-V-VI TP)
    # For T > 354.75K (VI-VII-Liquid TP): Ice VI doesn't exist, boundary is VII melting curve
    if T >= 218.95 and P > 620:
        if T > 354.75:
            # Above VI-VII-Liquid TP: Ice VI doesn't exist
            # Must check VII melting curve to determine VII vs Liquid
            # For Ice VII: P > P_melt(T) means solid, P < P_melt(T) means liquid
            try:
                P_melt_vii = melting_pressure(T, "VII")
                if P > P_melt_vii:
                    # High pressure keeps Ice VII solid
                    phase_id = "ice_vii"
                else:
                    raise UnknownPhaseError(
                        "Liquid water region (below Ice VII melting curve)",
                        temperature=T,
                        pressure=P,
                    )
            except ValueError:
                raise UnknownPhaseError(
                    f"Temperature {T}K outside Ice VII melting curve range",
                    temperature=T,
                    pressure=P,
                )
        elif T > 278:
            # T in (278, 354.75]: check VI-VII boundary
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
    
    # 3b. Ice IX region: T < 140K, P = 200-400 MPa (ordered Ice III)
    # Ice IX is the proton-ordered form of Ice III, stable at low T
    # Must check BEFORE Ice II since conditions overlap
    if T < 140.0 and 200 <= P <= 400:
        P_ix = ix_boundary(T)
        if P > P_ix:
            phase_id = "ice_ix"
            return _build_result(phase_id, T, P)
    
    # 4. Ice II region
    # Ice II: T(100-249.4K at high P), P(200-670 MPa)
    # The II region has two parts: above and below the Ih-II-III triple point
    if T < 249.4 and P > 200:
        if T >= 238.45:
            # Above Ih-II-III triple point
            # Check II-III boundary
            P_ii_iii = ii_iii_boundary(T)
            if P > P_ii_iii:
                # Above II-III boundary = Ice II
                phase_id = "ice_ii"
                return _build_result(phase_id, T, P)
        else:
            # Below Ih-II-III triple point (T < 238.45K)
            # Check Ih-II boundary
            P_ih_ii = ih_ii_boundary(T)
            if P > P_ih_ii:
                # Above Ih-II boundary = Ice II
                phase_id = "ice_ii"
                return _build_result(phase_id, T, P)
    
    # 5. Ice III region (narrow wedge)
    # Ice III: T(238.45-256.164K), P(~210-350 MPa)
    # This is a narrow region between II-III and III-V boundaries
    if 238.45 <= T <= 256.164 and P > 200:
        # Check boundaries to determine if in Ice III region
        if T <= 249.4:
            # Check II-III boundary (lower P boundary of Ice III)
            P_ii_iii = ii_iii_boundary(T)
            if P < P_ii_iii:
                # Below II-III boundary = Ice III
                phase_id = "ice_iii"
                return _build_result(phase_id, T, P)
        if T >= 249.4:
            # Check III-V boundary (upper P boundary of Ice III)
            P_iii_v = iii_v_boundary(T)
            if P < P_iii_v:
                # Below III-V boundary = Ice III
                phase_id = "ice_iii"
                return _build_result(phase_id, T, P)
    
    # 5c. Ice XI region: T < 72K at low P (ordered Ice Ih)
    # Ice XI is the proton-ordered form of Ice Ih, stable at very low T
    # Must check BEFORE Ice Ih since it's a more specific condition
    if T < 72.0 and P < 200:
        phase_id = "ice_xi"
        return _build_result(phase_id, T, P)
    
    # 6. Ice Ih region
    # Ice Ih: T(100-273.16K), P(0-209.9 MPa at T=251.165K)
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
            # Check Ice Ic first (metastable, T < 150K, low P)
            if T < 150 and P < 100:
                phase_id = "ice_ic"
                return _build_result(phase_id, T, P)
            # Default fallback to Ice Ih for other low-T, low-P conditions
            if P < 200:
                phase_id = "ice_ih"
                return _build_result(phase_id, T, P)
    
    # 7. No match - unknown region
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
